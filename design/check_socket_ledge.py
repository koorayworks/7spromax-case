# -*- coding: utf-8 -*-
"""
7sProMax: バンドのレッジ（基板支持レッジ、z 4.4〜5.7、基板ふちから
1.5mm 潜り）× 基板裏キーソケット（Kailh）の全数干渉チェック。

本人の指摘（2026-11-06）: 「バンドを下から当てるやり方だと、ロング側は
キーソケットが基板のフチぎりぎりに来ているのでできない」への検証。

ソケット外形（基板裏面のハウジング包絡）は基板裏スキャン（7346）の
接点計測に基づく（オルソ画像・スケール 6.9px/mm、設計の基準データ）:
  - 金属接点は中心から対角配置: 実測 (+4.4, +6.5) / (+5.3, -6.4) 前後
    （L21・L29・S27 のスキャンプロファイルで確認）＝ Cherry MX 標準
    ピン配置。両半分ともバーは +x 側が標準向きとみなす。
  - 包絡 A（主判定）: 接点列を結ぶバー x ∈ [+1.5, +7.5]、y ∈ [-7.8, +7.8]
    （接点中心 ±6.2 + ハウジング余裕 ~1.6）に中央ドーム（半径 2.75）を加えた形。
  - 180° 回転向き（rot）は x 鏡像。両方を評価し悪い方を採る。
  - 基板裏面からの張り出し高さ: 3.0mm を仮定（z 2.7〜5.7）。
    レッジ帯（4.4〜5.7）との重なりはこの仮定の 2.0〜3.5mm の範囲で不変。
感度参考として、写真（42e3...jpg）の bbox 計測に基づく攻撃的包絡 B
（y を階段側に +9.7 まで伸ばした形）と、従来の 14mm 角プロキシも併記する。
B のみ／14mm のみで当たるものは「計測不確かさの範囲」として分けて報告する。

実行: ~/workspace/.venv-cad/bin/python check_socket_ledge.py
"""
import csv
import numpy as np
from shapely.geometry import Polygon, Point
from shapely.affinity import translate
import build_case as bc

BASE = bc.BASE
PCB_BOT = bc.PCB_BOT            # 5.7
LEDGE_Z0, LEDGE_Z1 = bc.LEDGE_Z0, bc.PCB_BOT   # 4.4 .. 5.7
SOCK_Z0 = PCB_BOT - 3.0         # ソケット下面（張り出し 3.0 仮定）
STAIR = {"short": lambda y: y < 55.0, "long": lambda y: y > 120.0}


def envelope(kind):
    """ソケット中心を原点とした基板裏ハウジング包絡 A（主判定）。
    kind: 'std' = バーが +x 側（実測の標準向き）、'rot' = x 鏡像。"""
    dome = Point(0, 0).buffer(2.75, resolution=48)
    if kind == "std":
        bar = Polygon([(1.5, -7.8), (7.5, -7.8), (7.5, 7.8), (1.5, 7.8)])
    else:
        bar = Polygon([(-7.5, -7.8), (-1.5, -7.8), (-1.5, 7.8), (-7.5, 7.8)])
    from shapely.ops import unary_union
    return unary_union([bar, dome])


def envelope_b(kind):
    """包絡 B（写真 bbox 由来の攻撃形、感度参考）。"""
    dome = Point(0, 0).buffer(2.75, resolution=48)
    if kind == "std":
        bar = Polygon([(0.75, -8.0), (6.9, -8.0), (6.9, 9.7), (0.75, 9.7)])
    else:
        bar = Polygon([(-6.9, -9.7), (-0.75, -9.7), (-0.75, 8.0), (-6.9, 8.0)])
    from shapely.ops import unary_union
    return unary_union([bar, dome])


def square_proxy():
    h = 7.0
    return Polygon([(-h, -h), (h, -h), (h, h), (-h, h)])


def load_sockets(half):
    out = []
    for row in csv.DictReader(open(f"{BASE}/template/pcb_sockets.csv")):
        if row["half"] != half or row["kind"] not in ("square", "tall"):
            continue
        if row["method"] == "dome_centroid" and row["meas_x_mm"]:
            x, y = float(row["meas_x_mm"]), float(row["meas_y_mm"])
            src = "meas"
        else:
            x, y = float(row["dxf_x_mm"]), float(row["dxf_y_mm"])
            src = "dxf"
        out.append(dict(id=row["hole_id"], x=x, y=y, src=src))
    return out


def solid_of(poly, z0, z1):
    return bc.prism(poly, z0, z1)


def vol(shape):
    try:
        return float(shape.volume)
    except Exception:
        return 0.0


for half in ("short", "long"):
    H = bc.halves[half]
    pcb = H["pcb"]
    band = bc.results[half]["band"]
    ledge_ring = pcb.difference(bc.inset(pcb, bc.LEDGE_UNDER))
    socks = load_sockets(half)
    print(f"\n===== {half}: {len(socks)} sockets vs band ledge =====")
    print(f"ledge ring area = {ledge_ring.area:.1f} mm^2, "
          f"slab z {LEDGE_Z0}..{LEDGE_Z1}")
    slab = bc.box(-60, 200, -60, 260, LEDGE_Z0, LEDGE_Z1)
    rows = []
    for s in socks:
        cx, cy = s["x"], s["y"]
        rec = dict(id=s["id"], x=cx, y=cy, src=s["src"],
                   stair=bool(STAIR[half](cy)),
                   d_center_edge=float(pcb.boundary.distance(Point(cx, cy))))
        for kind in ("std", "rot"):
            env = translate(envelope(kind), cx, cy)
            rec[f"env_inside_{kind}"] = bool(pcb.contains(env))
            rec[f"gap_edge_{kind}"] = float(env.distance(pcb.boundary)) \
                if pcb.contains(env) else -float(env.difference(pcb).area) ** 0.5
            rec[f"ring_area_{kind}"] = float(env.intersection(ledge_ring).area)
            envb = translate(envelope_b(kind), cx, cy)
            rec[f"ring_areaB_{kind}"] = float(envb.intersection(ledge_ring).area)
        # 14mm 角プロキシ
        env14 = translate(square_proxy(), cx, cy)
        rec["ring_area_14"] = float(env14.intersection(ledge_ring).area)
        rows.append((s, rec))
    # 3D は 2D で重なりがあるものだけ（包絡 A・B・14mm）
    for s, rec in rows:
        for kind in ("std", "rot"):
            for tag, fn in (("", envelope), ("B", envelope_b)):
                key = f"ring_area{tag}_{kind}"
                if rec[key] > 0:
                    env = translate(fn(kind), rec["x"], rec["y"])
                    raw = solid_of(env, SOCK_Z0, PCB_BOT)
                    inter = (raw & band) if raw is not None else None
                    rec[f"vol3d{tag}_{kind}"] = vol(inter) if inter is not None else 0.0
                    rec[f"vol3d_ledge{tag}_{kind}"] = \
                        vol(inter & slab) if inter is not None else 0.0
                else:
                    rec[f"vol3d{tag}_{kind}"] = 0.0
                    rec[f"vol3d_ledge{tag}_{kind}"] = 0.0
        if rec["ring_area_14"] > 0:
            env14 = translate(square_proxy(), rec["x"], rec["y"])
            raw14 = solid_of(env14, SOCK_Z0, PCB_BOT)
            inter14 = (raw14 & band) if raw14 is not None else None
            rec["vol3d_14"] = vol(inter14) if inter14 is not None else 0.0
            rec["vol3d_ledge_14"] = vol(inter14 & slab) if inter14 is not None else 0.0
        else:
            rec["vol3d_14"] = 0.0
            rec["vol3d_ledge_14"] = 0.0
    def flag(rec, tag=""):
        return max(rec[f"vol3d{tag}_std"], rec[f"vol3d{tag}_rot"])
    print("-- HIT-A: interference with envelope A (scan-based, primary) --")
    any_hit = False
    for s, rec in sorted(rows, key=lambda t: -flag(t[1])):
        v = flag(rec)
        if v > 0.01:
            any_hit = True
            kind = "std" if rec["vol3d_std"] >= rec["vol3d_rot"] else "rot"
            print(f"  HIT {rec['id']} ({rec['x']:.2f},{rec['y']:.2f}) {rec['src']}"
                  f" stair={rec['stair']} kind={kind}"
                  f" vol={v:.2f} mm^3 (ledge slab {rec[f'vol3d_ledge_{kind}']:.2f})"
                  f" ring_area={rec[f'ring_area_{kind}']:.2f} mm^2"
                  f" env_inside={rec[f'env_inside_{kind}']}"
                  f" d_center_edge={rec['d_center_edge']:.2f}"
                  f" | B vol={flag(rec, 'B'):.2f} | 14sq vol={rec['vol3d_14']:.2f}")
    if not any_hit:
        print("  none")
    print("-- B-only (aggressive envelope only; metrology uncertainty zone) --")
    for s, rec in rows:
        if flag(rec) <= 0.01 and flag(rec, "B") > 0.01:
            print(f"  B-only {rec['id']} ({rec['x']:.2f},{rec['y']:.2f})"
                  f" stair={rec['stair']} B vol={flag(rec, 'B'):.2f}")
    print("-- 14sq-only --")
    for s, rec in rows:
        if flag(rec) <= 0.01 and flag(rec, "B") <= 0.01 and rec["vol3d_14"] > 0.01:
            print(f"  14-only {rec['id']} ({rec['x']:.2f},{rec['y']:.2f})"
                  f" stair={rec['stair']} 14sq vol={rec['vol3d_14']:.2f}")
    print("-- stair-zone sockets detail (incl. no-hit) --")
    for s, rec in rows:
        if rec["stair"]:
            print(f"  {rec['id']} ({rec['x']:.2f},{rec['y']:.2f}) {rec['src']}"
                  f" d_center_edge={rec['d_center_edge']:.2f}"
                  f" gap_edge std={rec['gap_edge_std']:.2f} rot={rec['gap_edge_rot']:.2f}"
                  f" ringA std={rec['ring_area_std']:.2f} rot={rec['ring_area_rot']:.2f}"
                  f" volA std={rec['vol3d_std']:.2f} rot={rec['vol3d_rot']:.2f}"
                  f" volB std={rec['vol3dB_std']:.2f} rot={rec['vol3dB_rot']:.2f}")
    print("-- non-stair sockets with any A/B ring overlap (2D) --")
    for s, rec in rows:
        if not rec["stair"] and (rec["ring_area_std"] > 0 or rec["ring_area_rot"] > 0
                                 or rec["ring_areaB_std"] > 0 or rec["ring_areaB_rot"] > 0):
            print(f"  {rec['id']} ({rec['x']:.2f},{rec['y']:.2f})"
                  f" ringA std={rec['ring_area_std']:.2f} rot={rec['ring_area_rot']:.2f}"
                  f" volA std={rec['vol3d_std']:.2f} rot={rec['vol3d_rot']:.2f}"
                  f" volB std={rec['vol3dB_std']:.2f} rot={rec['vol3dB_rot']:.2f}")
print("\nDONE")
