# -*- coding: utf-8 -*-
"""
プランジャ（小ボタン、v2.4.5 / §17.19）の検証。
実行: ~/workspace/.venv-cad/bin/python check_plunger.py（ビルド込み）

組立座標で次を数値確認する（両半分・全 6 タクト）:
  1. フレームの受け: ガイド穴（Ø5.4、z 13.2〜14.1 帯）と座ぐり
     （Ø9.6、床 14.1）がタクト中心軸上に開いていること。座ぐり床の
     支持は背面側（x+）に存在すること（内側 x- は天面開口へ破れる
     ため支持なしが想定内。その旨を出力する）。
  2. 静止時: プランジャ × フレーム／プレート干渉 0。受け凹みの
     天井とタクト先端（モデル Ø2、z 10.6〜12.5、先端・径とも推定）
     の間隔 0.3。
  3. 押下スイープ: -0.3（先端に接触、干渉 0）／-0.8（作動後、
     干渉 0）／-1.1（ストッパ接触、干渉 0）／-1.3（ストッパが
     食い込み干渉 >0 = スイッチのオーバートラベル予算 0.5 を
     使い切る前にストッパが効くことの証明）。スイッチ先端モデルは
     接触後にプランジャへ追随させて測る（固定すると押下量そのもの
     が食い込みとして出るため）。
  4. 全押下（-1.1）でもフランジ下面がスイッチ本体（モデル
     5×4×z[7.3,10.6]、推定）に当たらないこと。
  5. 抜け止め: フランジ Ø7 > ガイド穴 Ø5.4、フランジ天井と
     屋根下面（スロット上面 13.2）の遊び 0.3。
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
    cap = cylm(x, y, CAP_BOT, CAP_TOP, bc.PLUNGER_CAP_D)
    shaft = cylm(x, y, SHAFT_BOT, CAP_BOT, bc.PLUNGER_SHAFT_D)
    flange = cylm(x, y, FLANGE_BOT, SHAFT_BOT, bc.PLUNGER_FLANGE_D)
    p = trimesh.boolean.union([cap, shaft, flange], engine="manifold")
    recess = cylm(x, y, FLANGE_BOT - 0.1, CEIL_Z, bc.PLUNGER_RECESS_D)
    return trimesh.boolean.difference([p, recess], engine="manifold")


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
        x = bc.TACT_X
        print(f"== {half} tact{ci+1} (x={x}, y={c}) ==")
        # 1. 受けの開口と支持
        pts = np.array([[x, c, 13.65], [x, c, 15.5],
                        [x + 5.6, c, 15.0], [x - 5.6, c, 15.0]])
        ins = frame.contains(pts)
        print(f"   guide hole open (z13.65): {not ins[0]}, "
              f"counterbore open (z15.5): {not ins[1]}, "
              f"floor support +x side: {bool(ins[2])}, "
              f"-x side (well side, expected open): {bool(ins[3])}")
        if ins[0] or ins[1] or not ins[2]:
            fails.append(f"{half} tact{ci+1}: receiver opening/support")
        # 2-4. 静止と押下スイープ
        p0 = plunger_at(x, c)
        tip = cylm(x, c, BODY_TOP, TIP_TOP, TIP_D)
        body = boxm(x - 2.5, x + 2.5, c - 2.0, c + 2.0, bc.PCB_TOP, BODY_TOP)
        print(f"   plunger bbox z: [{p0.bounds[0][2]:.2f}, {p0.bounds[1][2]:.2f}] "
              f"vol={p0.volume:.1f}")
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

print("PLUNGER CHECK " + ("FAILED: " + "; ".join(fails) if fails else "ALL OK"))
