# -*- coding: utf-8 -*-
"""
パドル実モデル（2026-11-05 ノギス実測ベース）× ケース各部の干渉チェック。
実行: ~/workspace/.venv-cad/bin/python check_paddle_real.py

注: 2026-11-05 本人決定で金属パドルは使わないことになった
（高さ不一致 約3.4〜4.2mm、§17.18）。本チェックのパドル配置
スイープは不使用決定の数値根拠の記録として残す。現行の実務
チェックは冒頭のタクトスイッチ実体ボックス（上面 z 7.3〜12.5）
とプレート／フレーム／バンド／トレイの干渉確認。

実測（PADDLE_MEASUREMENTS 追記2）: 全長 25.2 / ブロック高さ 8.6 /
バー 4.8×2.8 / 羽根込み幅 8.2（7455 注記。旧推定 8.7 との食い違いが
残るため感度ケースとして 8.7 も測る）/ ブロック長さ 8.2（8.2 の
対応づけが羽根込み幅と競合するため未確定。感度として 9.75 も測る）。

モデル（装着姿勢、ケース座標、タクト中心 y=c）: 配置B型チャネル。
  - 脚（羽根込み幅の両側）: x[rx, rx+BL] × y c±(2.4..WING/2) × z[zb, zb+6.8]
  - 天板: x[rx, rx+BL] × y c±WING/2 × z[zb+6.8, zb+8.6]（厚 1.8）
  - バー: x[rx+BL, rx+25.2] × y c±2.4 × z[zb+5.8, zb+8.6]（厚 2.8、上面は天板と面一）
配置のばらつき（§17.18）:
  - zb（ブロック下端）: 1.0（従来配置B）/ 0.5（天板内面が基板上面
    7.3 に乗る）/ 0.2 / 0.0 かつ天板薄型（厚 1.0、バー下端 5.8）
  - y オフセット: 0 / ±1.2（タクト中心の実測精度 ±1〜2mm への感度）
  - rx（ブロック後端）: 101 を中心に ±1
状態: 静止 / 押下 (-0.5z) / 押下スイング（バー付け根を軸に先端が
下がる回転 +2°/+4°、代表配置のみ）
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

def paddle_real(c, zb=1.0, slab_t=1.8, wing=8.2, bl=8.2, rx=101.0, dy=0.0):
    leg_t = 8.6 - slab_t          # 脚の高さ（天板下面まで）
    hw = wing / 2
    legL = boxm(rx, rx + bl, c + dy - hw, c + dy - 2.4, zb, zb + leg_t)
    legR = boxm(rx, rx + bl, c + dy + 2.4, c + dy + hw, zb, zb + leg_t)
    slab = boxm(rx, rx + bl, c + dy - hw, c + dy + hw, zb + leg_t, zb + 8.6)
    bar = boxm(rx + bl, rx + 25.2, c + dy - 2.4, c + dy + 2.4, zb + 5.8, zb + 8.6)
    return trimesh.boolean.union([legL, legR, slab, bar], engine="manifold")

def rot_about(mesh, pivot, axis, deg):
    m = mesh.copy()
    T = trimesh.transformations.translation_matrix(pivot)
    R = trimesh.transformations.rotation_matrix(np.radians(deg), axis)
    Ti = trimesh.transformations.translation_matrix([-p for p in pivot])
    m.apply_transform(T @ R @ Ti)
    return m

# 配置スイープ: (ラベル, kwargs)
PLACEMENTS = [
    ("zb1.0/std",      dict(zb=1.0)),
    ("zb0.5/on-pcb",   dict(zb=0.5)),
    ("zb0.2",          dict(zb=0.2)),
    ("zb0.0/thin-slab", dict(zb=0.0, slab_t=1.0)),
    ("dy+1.2",         dict(zb=0.5, dy=1.2)),
    ("dy-1.2",         dict(zb=0.5, dy=-1.2)),
    ("rx100",          dict(zb=0.5, rx=100.0)),
    ("rx102",          dict(zb=0.5, rx=102.0)),
    ("wing8.7",        dict(zb=0.5, wing=8.7)),
    ("bl9.75",         dict(zb=0.5, bl=9.75)),
]

for half in HALVES:
    parts = {k: load_part(half, k) for k in ("tray", "band", "frame", "plate")}
    for ci, c in enumerate(bc.TACT_CENTERS[half]):
        print(f"== {half} tact{ci+1} (c={c}) measured model ==")
        # タクトスイッチ実体（2026-11-05 実測, 写真 7463＋本人確認）:
        # スイッチは基板上面（キースイッチ側）に付きボタン上向き。
        # 総厚 6.8（基板裏面→先端）= 基板 1.6 + 上面から突出 5.2 →
        # 先端 z = 7.3 + 5.2 = 12.5。本体・ボタンをまとめた保守
        # ボックスがケース各部（プレート含む）と干渉しないことを
        # 確認する。
        # v2.4.6 (§17.20): y 幅は実測 6.0（c±3.0）に更新。
        # v2.4.12 (§17.26): 平面形状を実測に是正。2026-11-06
        # 本人実測（写真 7488）: 奥行き x = 3.4、基板背面フチから
        # 近い側の端まで 0.5 → 中心は bc.TACT_X[half]（背面
        # プレーン −2.2）。ボックスは x 中心 ±1.7、y c±3.0
        # （= 3.4 × 6.0）。旧ボックス（x 103.5〜109.5 = 6.0 幅、
        # 中心 106.5 前提）は廃止。
        tx = bc.TACT_X[half]
        tact = boxm(tx - bc.TACT_W_X / 2, tx + bc.TACT_W_X / 2,
                    c - bc.TACT_W_Y / 2, c + bc.TACT_W_Y / 2, 7.3, 12.5)
        cells = " ".join(f"{pn}={ivol(tact, parts[pn]):.2f}" for pn in ("tray", "band", "frame", "plate"))
        print(f"   tact switch box (top z=12.5): {cells}")
        for label, kw in PLACEMENTS:
            pad = paddle_real(c, **kw)
            cells = " ".join(f"{pn}={ivol(pad, parts[pn]):.2f}" for pn in ("tray", "band", "frame"))
            print(f"   {label:15s} rest: {cells}")
        # 代表配置（zb0.5）で押下とスイング
        pad = paddle_real(c, zb=0.5)
        p2 = pad.copy(); p2.apply_translation([0, 0, -0.5])
        cells = " ".join(f"{pn}={ivol(p2, parts[pn]):.2f}" for pn in ("tray", "band", "frame"))
        print(f"   {'zb0.5 press':15s} -0.5z: {cells}")
        for ang in (2.0, 4.0):
            e = rot_about(pad, (101.0 + 8.2, c, 0.5 + 7.2), [0, 1, 0], ang)
            cells = " ".join(f"{pn}={ivol(e, parts[pn]):.2f}" for pn in ("tray", "band", "frame"))
            print(f"   {'zb0.5 swing':15s} +{ang:.0f}deg: {cells}")
print("PADDLE REAL CHECK DONE")
