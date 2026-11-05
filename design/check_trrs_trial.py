# -*- coding: utf-8 -*-
"""
TRRS 確認ピース（trial_trrs_{tray,band,frame}）の検証（v2.4.11、§17.25）

試作ピース単体で実物確認が成立するかを見る:
  1. 各ピースが単一ソリッド・watertight であること。
  2. ピースを組立座標に戻した状態で、ジャック実体エンベロープ
     （裏面から 5.1、下端 z 0.6、y ±3.25、x はタブふち＋0.3〜
     外面＋0.3）と干渉しないこと。
  3. プラグ模擬（胴体 Ø6.5・ピン Ø3.5、軸 z = 2.6／3.0／3.4）が
     ピースと干渉しないこと（＝ピース越しにプラグが挿せること）。
  4. 開口幅走査（z=3.0、外面手前 x）で中心 ±5.4 が空き、
     ±7.0 で壁（ピース材料）が残ること。

実行: ~/workspace/.venv-cad/bin/python check_trrs_trial.py
"""
import numpy as np
import trimesh
from shapely.geometry import Point
import build_case as bc
from check_trrs import section_polys, blocked, boxm, cylx, ivol

ZO = {"tray": 0.0, "band": 1.9, "frame": 5.7}

def load_piece(half, key):
    m = trimesh.load(f"{bc.OUTDIR}/trial_trrs_{key}_{half}.stl")
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate(tuple(m.geometry.values()))
    m.apply_translation([0, 0, ZO[key]])
    return m

def main():
    ok = True
    for half in ("short", "long"):
        parts = {k: load_piece(half, k) for k in ("tray", "band", "frame")}
        for k, m in parts.items():
            n = len(m.split(only_watertight=False))
            print(f"{half} trial_trrs_{k}: solids={n} watertight={m.is_watertight} "
                  f"vol={m.volume:.1f}")
            if n != 1 or not m.is_watertight:
                ok = False
        ob = bc.halves[half]["outline"].bounds
        ty = bc.TRRS_Y[half]
        # --- 2. ジャック実体エンベロープ ---
        jack = boxm(106.0, ob[2] + 0.3, ty - 3.25, ty + 3.25,
                    bc.TRRS_JACK_Z0, bc.PCB_BOT)
        res = {k: ivol(jack, parts[k]) for k in parts}
        print(f"{half} jack envelope x pieces: "
              + " ".join(f"{k}={v:.2f}" for k, v in res.items()))
        if any(v > 0.01 for v in res.values()):
            ok = False
        # --- 3. プラグ挿入の模擬 ---
        for za in (bc.TRRS_AXIS_Z - 0.4, bc.TRRS_AXIS_Z, bc.TRRS_AXIS_Z + 0.4):
            plug = cylx(ob[2] - 0.8, ob[2] + 16.0, ty, za, 3.25)
            pin = cylx(104.0, ob[2] + 0.3, ty, za, 1.75)
            res_p = {k: ivol(plug, parts[k]) for k in parts}
            res_i = {k: ivol(pin, parts[k]) for k in parts}
            print(f"{half} plug (axis z={za:.1f}) x pieces: "
                  + " ".join(f"{k}={v:.2f}" for k, v in res_p.items())
                  + " | pin: "
                  + " ".join(f"{k}={v:.2f}" for k, v in res_i.items()))
            if any(v > 0.01 for v in list(res_p.values()) + list(res_i.values())):
                ok = False
        # --- 4. 開口幅の走査（ピース断面のみ） ---
        polys = []
        for k in ("tray", "band", "frame"):
            polys += section_polys(parts[k], bc.TRRS_AXIS_Z)
        xw = ob[2] - 0.4
        ys_in = np.arange(ty - 5.4, ty + 5.41, 0.3)
        shut = [y for y in ys_in if blocked(polys, xw, y)]
        wall = {dy: blocked(polys, xw, ty + dy) for dy in (-7.0, 7.0)}
        stat = "OK" if not shut and all(wall.values()) else \
            f"NG shut={[round(float(s), 1) for s in shut]} wall={wall}"
        if shut or not all(wall.values()):
            ok = False
        print(f"{half} opening width scan on pieces (x={xw:.1f}): {stat}")
    print("TRRS TRIAL CHECK " + ("OK" if ok else "NG"))

if __name__ == "__main__":
    main()
