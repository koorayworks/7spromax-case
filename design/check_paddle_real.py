# -*- coding: utf-8 -*-
"""
パドル実モデル（PADDLE_MEASUREMENTS 実測ベース）× ケース各部の干渉チェック。
配置Bエンベロープ（check_v21 §3）との比較用に、実形状で再測する。
実行: ~/workspace/.venv-cad/bin/python check_paddle_real.py

実モデル（装着姿勢、ケース座標、タクト中心 y=c、軸配置は配置Bと同じ
ブロック後端 x=101.0）:
  - ブロック芯: x[101.0,110.75]（長さ 9.75）× y c±2.4（幅 4.8）× z[1.0,9.5]
    （高さ 8.5）。窪みは基板タブ＋タクト専用でケース部品は入らないため
    ソリッドで保守的に扱う。後端下面の面取りも省略（保守側）。
  - 羽根: x[108.25,110.75]（軸厚 2.5、ブロック前面＝バー付け根に flush、
    写真 7328/7330）× y c±(2.4..4.35)（羽根込み幅 8.7）× z[3.75,6.25]
    （高さ方向は写真 7332 の目視で中央帯。感度確認として z[5.0,7.5] も測る）
  - バー: x[110.75,128.35]（露出 17.6、全長 27.35）× y c±2.4 × z[6.8,9.5]
    （厚 2.7 = 本人再読確定値）
状態: 静止 / 押下 (-0.5z) / 押下スイング (バー付け根 (110.75,c,8.15) を
軸に y 回転 +0.5..+4°、先端が下がる向き) / ロール ±2.5° (軸 (106.3,c,5.0)) /
挿入・垂直 (Δz +5..0, フレーム無し想定で tray/band のみ) /
挿入・軸方向 (Δx -6..0, tray/band のみ + 参考に frame も)
"""
import numpy as np
import trimesh
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_case as bc

HALVES = ("short", "long")

def load_part(half, key):
    name = {"tray": f"bottom_tray_{half}", "band": f"side_band_{half}",
            "frame": f"top_frame_{half}", "plate": f"switch_plate_{half}"}[key]
    zo = {"tray": 0.0, "band": 1.9, "frame": 5.7,
          "plate": 7.35 if half == "short" else 9.5}[key]
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

def boxm(x0, x1, y0, y1, z0, z1):
    return trimesh.creation.box(
        extents=[x1 - x0, y1 - y0, z1 - z0],
        transform=trimesh.transformations.translation_matrix(
            [(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2]))

def paddle_real(c, wing_z=(3.75, 6.25)):
    core = boxm(101.0, 110.75, c - 2.4, c + 2.4, 1.0, 9.5)
    w1 = boxm(108.25, 110.75, c - 4.35, c - 2.4, wing_z[0], wing_z[1])
    w2 = boxm(108.25, 110.75, c + 2.4, c + 4.35, wing_z[0], wing_z[1])
    bar = boxm(110.75, 128.35, c - 2.4, c + 2.4, 6.8, 9.5)
    return trimesh.boolean.union([core, w1, w2, bar], engine="manifold")

def rot_about(mesh, pivot, axis, deg):
    m = mesh.copy()
    T = trimesh.transformations.translation_matrix(pivot)
    R = trimesh.transformations.rotation_matrix(np.radians(deg), axis)
    Ti = trimesh.transformations.translation_matrix([-p for p in pivot])
    m.apply_transform(T @ R @ Ti)
    return m

for half in HALVES:
    parts = {k: load_part(half, k) for k in ("tray", "band", "frame")}
    for ci, c in enumerate(bc.TACT_CENTERS[half]):
        pad = paddle_real(c)
        states = {}
        states["rest"] = pad
        p2 = pad.copy(); p2.apply_translation([0, 0, -0.5]); states["press-0.5z"] = p2
        for ang in (1.0, 2.0, 3.0, 4.0):
            states[f"swing+{ang:.0f}"] = rot_about(pad, (110.75, c, 8.15), [0, 1, 0], ang)
        for ang in (2.5, -2.5):
            states[f"roll{ang:+.1f}"] = rot_about(pad, (106.3, c, 5.0), [1, 0, 0], ang)
        print(f"== {half} tact{ci+1} (c={c}) real model, wing z 3.75-6.25 ==")
        for sname, e in states.items():
            cells = " ".join(f"{pn}={ivol(e, parts[pn]):.2f}" for pn in ("tray", "band", "frame"))
            print(f"   {sname:11s}: {cells}")
        # 挿入: 垂直降下 (frame 無し想定)
        worst = {"tray": 0.0, "band": 0.0}
        for dz in (5.0, 4.0, 3.0, 2.0, 1.0, 0.5):
            e = pad.copy(); e.apply_translation([0, 0, dz])
            for pn in ("tray", "band"):
                worst[pn] = max(worst[pn], ivol(e, parts[pn]))
        print(f"   insert-drop (max over dz, vs tray/band): tray={worst['tray']:.2f} band={worst['band']:.2f}")
        # 挿入: 軸方向スライド
        worst = {"tray": 0.0, "band": 0.0, "frame": 0.0}
        for dx in (-6.0, -5.0, -4.0, -3.0, -2.0, -1.0, -0.5):
            e = pad.copy(); e.apply_translation([dx, 0, 0])
            for pn in ("tray", "band", "frame"):
                worst[pn] = max(worst[pn], ivol(e, parts[pn]))
        print(f"   insert-slide (max over dx): tray={worst['tray']:.2f} band={worst['band']:.2f} frame={worst['frame']:.2f}")
        # 感度: 羽根 z を上げた variant (静止のみ)
        pad2 = paddle_real(c, wing_z=(5.0, 7.5))
        cells = " ".join(f"{pn}={ivol(pad2, parts[pn]):.2f}" for pn in ("tray", "band", "frame"))
        print(f"   rest, wing z 5.0-7.5 (sensitivity): {cells}")
print("PADDLE REAL CHECK DONE")
