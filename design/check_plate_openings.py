# -*- coding: utf-8 -*-
"""
スイッチプレート全穴の開口幅チェック（v2.4.3、§17.16 の回帰防止）

各スイッチ穴について、プレート板厚中央の断面で中心を通る開口幅
（x 方向・y 方向の void ラン長）を測り、設計値 SW_HOLE_MODEL=14.15
±0.6 に収まることを確認する。v2.4.2 では long の角穴 (93.72, 167.44)
だけ fin-fix の堀で壁が断たれ、開口が x 15.0 / y 22.5 に広がって
いた（MX のパチ留めタブが掛からない）。その再発防止用。

実行: ~/workspace/.venv-cad/bin/python check_plate_openings.py
"""
import numpy as np
import trimesh
from shapely.geometry import Polygon, LineString
import build_case as bc
import check_plate_ring as cpr

TOL = 0.6
REACH = 12.0

def section_polys(mesh, z):
    """板厚中央断面の材料領域（閉ループ群を even-odd で合成した
    Polygon/MultiPolygon を1要素のリストで返す）。"""
    sec = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if sec is None:
        return []
    loops = []
    for ent in sec.entities:
        pts = np.asarray(sec.vertices)[ent.points]
        if len(pts) >= 4:
            p = Polygon(pts[:, :2])
            if not p.is_valid:
                p = p.buffer(0)
            if p.geom_type == "MultiPolygon":
                p = max(p.geoms, key=lambda g: g.area)
            if not p.is_empty and p.area > 0.01:
                loops.append(p)
    if not loops:
        return []
    mat = loops[0]
    for p in loops[1:]:
        mat = mat.symmetric_difference(p)
    return [mat]

def void_width(polys, c, horizontal, cyx):
    """中心座標 c を通る直線上で、材料区間に挟まれた void の幅。
    horizontal=True なら x 方向のラン (直線 y=cyx)、False なら y 方向。"""
    if horizontal:
        line = LineString([(c - REACH, cyx), (c + REACH, cyx)])
    else:
        line = LineString([(cyx, c - REACH), (cyx, c + REACH)])
    ivs = []
    for p in polys:
        inter = line.intersection(p)
        if inter.is_empty:
            continue
        geoms = [inter] if inter.geom_type in ("LineString", "Point") else \
            [g for g in inter.geoms if g.geom_type in ("LineString", "Point")]
        for g in geoms:
            cs = list(g.coords)
            vals = [q[0] if horizontal else q[1] for q in cs]
            if vals:
                ivs.append((min(vals), max(vals)))
    ivs.sort()
    lo, hi = c - REACH, c + REACH
    prev = lo
    for (s, e) in ivs:
        if s <= c <= e:
            return 0.0
        if e <= c:
            prev = max(prev, e)
        elif s > c:
            return s - prev
    return hi - prev

def main():
    bad = 0
    for half in ("short", "long"):
        m = trimesh.load(f"{bc.OUTDIR}/switch_plate_{half}.stl")
        if isinstance(m, trimesh.Scene):
            m = trimesh.util.concatenate(tuple(m.geometry.values()))
        z, _amax = cpr.slab_mid_z(m)
        polys = section_polys(m, z)
        print(f"== {half}: {len(polys)} section polys at local z={z:.2f}")
        worst = []
        for (cx, cy) in cpr.SW[half]:
            ow = void_width(polys, cx, True, cy)
            oh = void_width(polys, cy, False, cx)
            dev = max(abs(ow - bc.SW_HOLE_MODEL), abs(oh - bc.SW_HOLE_MODEL))
            worst.append((dev, cx, cy, ow, oh))
            if dev > TOL:
                bad += 1
                print(f"  NG ({cx:.2f},{cy:.2f}): opening x={ow:.2f} y={oh:.2f} "
                      f"(design {bc.SW_HOLE_MODEL} ±{TOL})")
        worst.sort(reverse=True)
        t = worst[0]
        print(f"  {half}: {len(cpr.SW[half])} holes, worst dev {t[0]:.2f} "
              f"at ({t[1]:.2f},{t[2]:.2f}) x={t[3]:.2f} y={t[4]:.2f}")
    print("OPENINGS CHECK " +
          (f"NG: {bad} hole(s) out of tol" if bad else "OK: all 63 holes within tol"))

if __name__ == "__main__":
    main()
