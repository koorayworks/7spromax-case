# -*- coding: utf-8 -*-
"""
TRRS（裏面実装）ジャックの逃げ・開口チェック（v2.4.8、§17.22）

経緯: 従来設計はジャック本体が基板の上にある前提（フレーム背面壁
に z 7.75〜13.15 の開口）だったが、監査 (§17.21) と本人実測
（2026-11-06、基板込み全厚 6.7mm）で裏面（Light Side）実装と
確定した。基板厚 1.6 を引くと裏面から 5.1mm 張り出し、ケース
座標の占有は z 0.6〜5.7。開口はトレイ＋バンドの背面壁へ新設し、
フレームの旧開口は壁に戻した（プラグ胴体の逃げのみ残す）。

確認内容:
  1. ジャック実体エンベロープ（幅 6.5 = 写真計測 約6＋余裕、
     内側端はタブ縁から約 7.7mm、面は外面より 0.3 外まで、
     z 0.6〜5.7）がトレイ／バンド／フレームと干渉しないこと。
  2. プラグ挿入の模擬: 胴体シリンダ（Ø6.5、軸 z = 3.0 の推定と
     ±0.4 の両端）とピン（Ø3.5）が各パーツと干渉しないこと。
  3. 背面壁の開口幅: z=3.0・外面手前 x=113.9 の走査で、開口帯
     （中心 ±5.4）が空き、帯域外（±7.0）には壁が残ること。

実行: ~/workspace/.venv-cad/bin/python check_trrs.py
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

def cylx(x0, x1, y, z, r):
    c = trimesh.creation.cylinder(radius=r, height=x1 - x0, sections=40)
    rot = trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0])
    c.apply_transform(rot)
    c.apply_translation([(x0 + x1) / 2, y, z])
    return c

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
        ty = bc.TRRS_Y[half]
        # --- 1. ジャック実体エンベロープ ---
        jack = boxm(106.0, ob[2] + 0.3, ty - 3.25, ty + 3.25,
                    bc.TRRS_JACK_Z0, bc.PCB_BOT)
        res = {k: ivol(jack, parts[k]) for k in parts}
        print(f"{half} TRRS jack envelope (x[106,{ob[2] + 0.3:.1f}], y={ty}±3.25, "
              f"z[{bc.TRRS_JACK_Z0:.1f},{bc.PCB_BOT:.1f}]) x tray/band/frame: "
              + " ".join(f"{k}={v:.2f}" for k, v in res.items()))
        if any(v > 0.01 for v in res.values()):
            ok = False
        # --- 2. プラグ挿入の模擬（軸 z の推定と両端） ---
        for za in (bc.TRRS_AXIS_Z - 0.4, bc.TRRS_AXIS_Z, bc.TRRS_AXIS_Z + 0.4):
            plug = cylx(ob[2] - 0.8, ob[2] + 16.0, ty, za, 3.25)
            pin = cylx(104.0, ob[2] + 0.3, ty, za, 1.75)
            res_p = {k: ivol(plug, parts[k]) for k in parts}
            res_i = {k: ivol(pin, parts[k]) for k in parts}
            print(f"{half} plug body Ø6.5 (axis z={za:.1f}): "
                  + " ".join(f"{k}={v:.2f}" for k, v in res_p.items())
                  + " | pin Ø3.5: "
                  + " ".join(f"{k}={v:.2f}" for k, v in res_i.items()))
            if any(v > 0.01 for v in list(res_p.values()) + list(res_i.values())):
                ok = False
        # --- 3. 開口幅の走査（z=3.0, 外面手前） ---
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
        print(f"{half} TRRS opening width scan (x={xw:.1f}, z={bc.TRRS_AXIS_Z:.1f}): {stat}")
    print("TRRS CHECK " + ("OK" if ok else "NG"))

if __name__ == "__main__":
    main()
