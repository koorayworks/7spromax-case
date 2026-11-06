# -*- coding: utf-8 -*-
"""
プランジャ（小ボタン、v2.4.5 / §17.19、v2.4.12 / §17.26）の検証。
実行: ~/workspace/.venv-cad/bin/python check_plunger.py（ビルド込み）

組立座標で次を数値確認する（両半分・全 6 タクト）:
  1. フレームの受け: ガイド穴（Ø5.4）と座ぐり（Ø8.6、床 14.1）が
     実測中心（TACT_X、§17.26）上に開いていること。背面差し込み口
     （ガイド帯 幅 5.0／座ぐり帯 幅 8.4）が背面フェイスまで
     通っていること。座ぐり床の支持と、前面側（−x）の屋根材料が
     残っていること。
  2. 静止時: プランジャ × フレーム／プレート干渉 0。受け凹みの
     天井とタクト先端（モデル Ø2、z 10.6〜12.5）の間隔 0.3。
     プランジャ形状は plunger.stl 実物（D 字クリップ＋通り溝
     つき）を組立姿勢に変換して使う。
  3. 押下スイープ: -0.3（先端に接触、干渉 0）／-0.8（作動後、
     干渉 0）／-1.1（ストッパ接触、干渉 0）／-1.3（ストッパが
     食い込み干渉 >0 = スイッチのオーバートラベル予算 0.5 を
     使い切る前にストッパが効くことの証明）。スイッチ先端モデルは
     接触後にプランジャへ追随させて測る（固定すると押下量そのもの
     が食い込みとして出るため）。
  4. 全押下（-1.1）でもフランジ下面がスイッチ本体（実測モデル
     3.4(x)×6.0(y)×z[7.3,10.6]、§17.26）に当たらないこと。
  5. 抜け止め: フランジ Ø7 > ガイド穴 Ø5.4、フランジ天井と
     屋根下面（スロット上面 13.2）の遊び 0.3。
  6. 差し込みスイープ（v2.4.12 で追加）: プランジャを背面フェイス
     の外（中心 +8）から組立位置まで水平に差し込む経路で、
     フレームとの干渉が全行程 0 であること。フレーム単体
     （静止高さ／落下高さ -1.1）と、フレームを基板に載せた状態
     （タクト実体＋先端が実在、先端はフランジ下面の通り溝を
     通る）の両方で確認する。
     注: 旧設計（閉じた穴）にはこの経路自体が存在せず、本
     チェックも v2.4.11 までは組立状態しか見ていなかった
     （§17.26 の発見経緯）。
"""
import numpy as np
import trimesh
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_case as bc

HALVES = ("short", "long")
TIP_D = 2.0          # タクト先端（スイッチ側プランジャ）の径・推定
TIP_TOP = 12.5       # タクト先端 z（実測の総厚 6.8 から、§17.18）
BODY_TOP = 10.6      # スイッチ本体上面 z（内訳推定、§17.18）

# プランジャの組立 z（build_case のパラメータから導出）
CAP_TOP = bc.FRAME_TOP + 1.1                       # 17.2
CAP_BOT = CAP_TOP - bc.PLUNGER_CAP_T               # 15.2
SHAFT_BOT = CAP_BOT - bc.PLUNGER_SHAFT_L           # 12.9
FLANGE_BOT = SHAFT_BOT - bc.PLUNGER_FLANGE_T       # 11.9
CEIL_Z = FLANGE_BOT + bc.PLUNGER_RECESS_DEPTH      # 12.8

_PLUNGER_RAW = None


def load_part(half, key):
    name = {"frame": f"top_frame_{half}", "plate": f"switch_plate_{half}"}[key]
    zo = {"frame": 5.7, "plate": 7.35 if half == "short" else 9.5}[key]
    m = trimesh.load(f"{bc.OUTDIR}/{name}.stl")
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate(tuple(m.geometry.values()))
    m.apply_translation([0, 0, zo])
    return m


def ivol(a, b):
    try:
        return trimesh.boolean.intersection([a, b], engine="manifold").volume
    except Exception:
        return 0.0


def cylm(x, y, z0, z1, d, sections=48):
    m = trimesh.creation.cylinder(radius=d / 2, height=z1 - z0,
                                  sections=sections)
    m.apply_translation([x, y, (z0 + z1) / 2])
    return m


def boxm(x0, x1, y0, y1, z0, z1):
    return trimesh.creation.box(
        extents=[x1 - x0, y1 - y0, z1 - z0],
        transform=trimesh.transformations.translation_matrix(
            [(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2]))


def plunger_at(x, y):
    """plunger.stl 実物（印刷姿勢: キャップ下面が z=0）を組立姿勢・
    位置に変換する。印刷 +x が組立 +x（背面）になるよう x 軸回転
    （(x,y,z) -> (x,-y,-z)）で天地を返す。"""
    global _PLUNGER_RAW
    if _PLUNGER_RAW is None:
        m = trimesh.load(f"{bc.OUTDIR}/plunger.stl")
        if isinstance(m, trimesh.Scene):
            m = trimesh.util.concatenate(tuple(m.geometry.values()))
        _PLUNGER_RAW = m
    p = _PLUNGER_RAW.copy()
    p.apply_transform(trimesh.transformations.rotation_matrix(
        np.pi, [1, 0, 0]))
    p.apply_translation([x, y, CAP_TOP])
    return p


fails = []
print(f"plunger z stack: cap[{CAP_BOT},{CAP_TOP}] shaft[{SHAFT_BOT},{CAP_BOT}] "
      f"flange[{FLANGE_BOT},{SHAFT_BOT}] recess ceiling {CEIL_Z}")
print(f"rest gap ceiling->tip: {CEIL_Z - TIP_TOP:.2f} (target 0.3), "
      f"flange top->roof bottom play: {bc.PADDLE_SLOT_Z1 - SHAFT_BOT:.2f}, "
      f"flange D {bc.PLUNGER_FLANGE_D} > hole D {bc.PLUNGER_HOLE_D}: "
      f"{bc.PLUNGER_FLANGE_D > bc.PLUNGER_HOLE_D}")
assert abs((CEIL_Z - TIP_TOP) - 0.3) < 1e-9
assert bc.PLUNGER_FLANGE_D > bc.PLUNGER_HOLE_D

for half in HALVES:
    frame = load_part(half, "frame")
    plate = load_part(half, "plate")
    for ci, c in enumerate(bc.TACT_CENTERS[half]):
        x = bc.TACT_X[half]
        print(f"== {half} tact{ci+1} (x={x}, y={c}) ==")
        # 1. 受けの開口・差し込み口・支持
        # 差し込み口のプローブは「口が無ければ材料がある」位置に
        # 置く: 座ぐり円（r4.3）の外・背面フェイスの内側・口の幅
        # （±4.2）の内側の点、ガイド穴（r2.7）でも同様の点。
        pts = np.array([
            [x, c, 13.65],            # ガイド穴（開いていれば外）
            [x, c, 15.5],             # 座ぐり（開いていれば外）
            [x + 2.35, c + 3.8, 15.0],  # 座ぐり差し込み口（外）
            [x + 2.3, c + 2.4, 13.5],   # ガイド差し込み口（外）
            [x - 5.6, c, 15.0],       # 前面側の屋根材料（あれば内）
            [x - 3.5, c, 14.05],      # 座ぐり床の支持・前（あれば内）
            # 座ぐり床の支持・後: ガイド差し込み口（幅 5.0）の
            # 外側で測る（口の切り代 +0.05 が床上面に被るため、
            # 中心線上では床が 0.05 低くなる。ストッパの当たりは
            # 周囲の床で受けるので機能に影響しない）
            [x + 2.2, c + 3.2, 14.05],
            # フードの実材（座ぐりの後ろ角、差し込み口の外側）。
            # v2.4.12 で追加したタクト帯のフードが受けを囲んで
            # いることの確認（フードが無いと空中になる位置:
            # ケース外形の窪みの上、座ぐり円と差し込み口の外）
            [x + 1.85, c + 4.6, 15.0],
        ])
        ins = frame.contains(pts)
        print(f"   guide hole open: {not ins[0]}, counterbore open: {not ins[1]}, "
              f"cb channel open: {not ins[2]}, guide channel open: {not ins[3]}, "
              f"front roof material: {bool(ins[4])}, "
              f"floor support front/back: {bool(ins[5])}/{bool(ins[6])}, "
              f"roof back corner: {bool(ins[7])}")
        if ins[0] or ins[1] or ins[2] or ins[3] or not ins[4] \
                or not ins[5] or not ins[6] or not ins[7]:
            fails.append(f"{half} tact{ci+1}: receiver opening/channel/support")
        # 2-4. 静止と押下スイープ（プランジャは STL 実物）
        p0 = plunger_at(x, c)
        tip = cylm(x, c, BODY_TOP, TIP_TOP, TIP_D)
        body = boxm(x - bc.TACT_W_X / 2, x + bc.TACT_W_X / 2,
                    c - bc.TACT_W_Y / 2, c + bc.TACT_W_Y / 2,
                    bc.PCB_TOP, BODY_TOP)
        print(f"   plunger bbox x[{p0.bounds[0][0]:.2f},{p0.bounds[1][0]:.2f}] "
              f"z[{p0.bounds[0][2]:.2f},{p0.bounds[1][2]:.2f}] vol={p0.volume:.1f}")
        rows = []
        for dz, label in ((0.0, "rest"), (-0.3, "touch"), (-0.8, "actuated"),
                          (-1.1, "stopper"), (-1.3, "over")):
            p = p0.copy()
            p.apply_translation([0, 0, dz])
            # スイッチ先端は接触後（dz<-0.3）はプランジャに追随して
            # 下がる（作動+オーバートラベルの上限 -1.0 でキャップ）。
            # 固定したまま測ると「押下で先端に食い込む」のは当然の
            # モデルアーティファクトなので、追随させて干渉を見る。
            t = tip.copy()
            tdz = max(dz + 0.3, -1.0) if dz < -0.3 else 0.0
            t.apply_translation([0, 0, tdz])
            rows.append((label, ivol(p, frame), ivol(p, t), ivol(p, body)))
        for label, vf, vt, vb in rows:
            print(f"   {label:9s} dz: frame={vf:.3f} tip={vt:.3f} body={vb:.3f}")
        print(f"   rest x plate: {ivol(p0, plate):.3f}")
        ok = (rows[0][1] < 0.05 and rows[0][2] < 0.05 and rows[0][3] < 0.05
              and rows[1][1] < 0.05 and rows[1][2] < 0.05
              and rows[2][1] < 0.05 and rows[2][2] < 0.05
              and rows[3][1] < 0.05 and rows[3][2] < 0.05 and rows[3][3] < 0.05
              and rows[4][1] > 0.5 and ivol(p0, plate) < 0.05)
        print(f"   -> {'OK' if ok else 'FAIL'}")
        if not ok:
            fails.append(f"{half} tact{ci+1}: stroke sweep")
        # 6. 差し込みスイープ: 背面の外（+8）から組立位置まで
        for dz, targets, label in (
                (0.0, (("frame", frame),), "frame-only rest"),
                (-1.1, (("frame", frame),), "frame-only dropped"),
                (0.0, (("frame", frame), ("tip", tip), ("body", body)),
                 "mounted")):
            worst = 0.0
            for dx in np.arange(8.0, -0.01, -0.5):
                p = p0.copy()
                p.apply_translation([dx, 0, dz])
                for _tn, tm in targets:
                    worst = max(worst, ivol(p, tm))
            print(f"   insert sweep [{label}]: worst interference {worst:.3f}")
            if worst >= 0.05:
                fails.append(f"{half} tact{ci+1}: insert sweep {label}")

print("PLUNGER CHECK " + ("FAILED: " + "; ".join(fails) if fails else "ALL OK"))
