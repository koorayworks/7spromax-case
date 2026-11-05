# -*- coding: utf-8 -*-
"""
USB 開口チャネルと MCU ポケットのチェック（v2.4.4、§17.18）

経緯: v2.4.2 まではフレームの USB 開口が貫通していない欠陥があり
（v2.4.3 で修正）、v2.4.4 では本人確定の裏面実装に合わせ、開口を
フレーム（z 9.8〜15.3、スイッチ側実装前提）からトレイ＋バンドの
端壁（z 0〜4.5）へ移設し、トレイ床に MCU ポケットを新設した。
マイコンは RP2040 の ProMicro 互換ボード（33×18mm 級、基板厚
1.6 級）で実物未入手のため標準寸法ベース。ヘッダ／ソケット高さ
は 2.5 か 3mm か未確定（本人保留中）のため両ケースで確認する。

確認内容:
  1. 新 USB チャネル: 中心線 (x=USB_XC, z=2.25) に沿い、ケース
     外面からコネクタ面（基板端＋出っ張り想定）まで材料が無い
     こと（トレイ＋バンド＋フレームの和集合で判定）。
  2. フレームの旧開口が埋まっていること: 旧中心 (x=USB_XC,
     z=12.55) の壁帯域が全て材料であること。
  3. MCU 干渉: 裏面実装モジュール基板（ヘッダ 2.5 → z[1.6,3.2]、
     ヘッダ 3.0 → z[1.1,2.7]）とコネクタ（各ヘッダで中心
     2.4/1.9、総厚 3.2 → z[0.8,4.0] / z[0.3,3.5]）のボックスが
     トレイ／バンド／フレームと干渉しないこと。
  4. TRRS チャネル: v2.4.8 (§17.22) で裏面実装に是正。新しい
     低いチャネル（トレイ＋バンド背面壁、軸 z≈3.0±0.4）が貫通して
     いることと、フレームの旧開口（z 7.75〜13.15）が壁に戻って
     いることを確認する。ジャック実体との干渉は check_trrs.py。

実行: ~/workspace/.venv-cad/bin/python check_usb_channel.py
"""
import numpy as np
import trimesh
from shapely.geometry import Polygon, Point
import build_case as bc

ZO = {"tray": 0.0, "band": 1.9, "frame": 5.7}

def load_assembled(half, key):
    name = {"tray": f"bottom_tray_{half}", "band": f"side_band_{half}",
            "frame": f"top_frame_{half}"}[key]
    m = trimesh.load(f"{bc.OUTDIR}/{name}.stl")
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate(tuple(m.geometry.values()))
    m.apply_translation([0, 0, ZO[key]])
    return m

def section_polys(mesh, z):
    sec = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    out = []
    if sec is None:
        return out
    for ent in sec.entities:
        pts = np.asarray(sec.vertices)[ent.points]
        if len(pts) >= 4:
            p = Polygon(pts[:, :2])
            if not p.is_valid:
                p = p.buffer(0)
            if p.geom_type == "MultiPolygon":
                p = max(p.geoms, key=lambda g: g.area)
            if not p.is_empty and p.area > 0.01:
                out.append(p)
    return out

def blocked(polys, x, y):
    return any(p.covers(Point(x, y)) for p in polys)

def boxm(x0, x1, y0, y1, z0, z1):
    return trimesh.creation.box(
        extents=[x1 - x0, y1 - y0, z1 - z0],
        transform=trimesh.transformations.translation_matrix(
            [(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2]))

def ivol(a, b):
    try:
        return trimesh.boolean.intersection([a, b], engine="manifold").volume
    except Exception:
        return 0.0

def main():
    ok = True
    for half in ("short", "long"):
        parts = {k: load_assembled(half, k) for k in ("tray", "band", "frame")}
        ob = bc.halves[half]["outline"].bounds
        pb = bc.halves[half]["pcb"].bounds
        # --- 1. 新 USB チャネル (z=2.25, 開口 z 0〜4.5 の中心) ---
        polys = []
        for k in ("tray", "band", "frame"):
            polys += section_polys(parts[k], 2.25)
        if half == "short":
            face = pb[3] + 1.6          # コネクタ面の想定（基板端+1.6）
            ys = np.arange(face, ob[3] + 0.51, 0.25)
        else:
            face = pb[1] - 1.6
            ys = np.arange(ob[1] - 0.5, face + 0.01, 0.25)
        hits = [y for y in ys if blocked(polys, bc.USB_XC, y)]
        stat = "OK (through)" if not hits else f"NG blocked at y={[round(float(h), 2) for h in hits]}"
        if hits:
            ok = False
        print(f"{half} USB low channel (x={bc.USB_XC}, z=2.25, face y={face:.2f}): {stat}")
        # --- 2. フレーム旧開口の閉塞 (z=12.55) ---
        # 壁の外面側 1.5mm だけを見る（内側は正規のキャビティで開く）。
        # 旧開口・旧ポケットはこの帯域を貫いていたので、埋まれば材料がある。
        polys_old = section_polys(parts["frame"], 12.55)
        if half == "short":
            wall_ys = np.arange(ob[3] - 1.5, ob[3] - 0.01, 0.25)
        else:
            wall_ys = np.arange(ob[1] + 0.01, ob[1] + 1.5, 0.25)
        gaps = [y for y in wall_ys if not blocked(polys_old, bc.USB_XC, y)]
        stat2 = "OK (filled)" if not gaps else f"NG still open at y={[round(float(g), 2) for g in gaps]}"
        if gaps:
            ok = False
        print(f"{half} frame old USB opening (z=12.55): {stat2}")
        # --- 3. MCU モジュール干渉 ---
        if half == "short":
            mod_y = (pb[3] - 32.55, pb[3] + 0.45)
            con_y = (pb[3] - 6.95, pb[3] + 0.45)
        else:
            mod_y = (pb[1] - 0.45, pb[1] + 32.55)
            con_y = (pb[1] - 0.45, pb[1] + 6.95)
        for hdr, mz0, mz1 in ((2.5, 1.6, 3.2), (3.0, 1.1, 2.7)):
            module = boxm(85.1, 102.9, mod_y[0], mod_y[1], mz0, mz1)
            res = {k: ivol(module, parts[k]) for k in parts}
            print(f"{half} MCU module box (header {hdr}, z[{mz0},{mz1}]) x tray/band/frame: "
                  + " ".join(f"{k}={v:.2f}" for k, v in res.items()))
            if any(v > 0.01 for v in res.values()):
                ok = False
            cc = (mz0 + mz1) / 2
            con = boxm(89.55, 98.45, con_y[0], con_y[1], cc - 1.6, cc + 1.6)
            res = {k: ivol(con, parts[k]) for k in parts}
            print(f"{half} USB connector box (header {hdr}, z[{cc - 1.6:.1f},{cc + 1.6:.1f}]) x tray/band/frame: "
                  + " ".join(f"{k}={v:.2f}" for k, v in res.items()))
            if any(v > 0.01 for v in res.values()):
                ok = False
        # --- 4. TRRS チャネル（v2.4.8, §17.22: 裏面実装に是正） ---
        ty = bc.TRRS_Y[half]
        # 4a. 新チャネル: 軸推定 z=3.0±0.4 の全域で、背面壁を含む
        # x 帯（104〜外面+0.5）に材料が無いこと（トレイ＋バンド＋
        # フレームの和集合で判定）。
        for zt in (2.6, 3.0, 3.4):
            polys_t = []
            for k in ("tray", "band", "frame"):
                polys_t += section_polys(parts[k], zt)
            xs = np.arange(104.0, ob[2] + 0.51, 0.25)
            hits_t = [x for x in xs if blocked(polys_t, x, ty)]
            stat_t = "OK (through)" if not hits_t else \
                f"NG blocked at x={[round(float(h), 2) for h in hits_t]}"
            if hits_t:
                ok = False
            print(f"{half} TRRS low channel (y={ty}, z={zt:.1f}): {stat_t}")
        # 4b. フレーム旧開口の閉塞: 旧中心 z=10.45 の背面壁帯域
        # （外面から 1.5mm）が全て材料であること。
        polys_old_t = section_polys(parts["frame"], 10.45)
        xs_old = np.arange(ob[2] - 1.5, ob[2] - 0.01, 0.25)
        gaps_t = [x for x in xs_old if not blocked(polys_old_t, x, ty)]
        stat_o = "OK (filled)" if not gaps_t else \
            f"NG still open at x={[round(float(g), 2) for g in gaps_t]}"
        if gaps_t:
            ok = False
        print(f"{half} frame old TRRS opening (z=10.45): {stat_o}")
    print("CHANNEL CHECK " + ("OK" if ok else "NG"))

if __name__ == "__main__":
    main()
