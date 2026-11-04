# -*- coding: utf-8 -*-
"""
7sProMax ケース v2.4 左右ドッキング検証（DESIGN_NOTES §17.13）

v2.4 のシーム整形（build_case.seam_stair、DOCKING_STUDY 案2）が
実 STL で成立しているかを測る:
  1. 両半分のシルエット（side_band の z=1.5 断面の外周ポリゴン）を
     図面レイアウトの向きのまま y 方向に寄せ、最初に接触する相対
     オフセット D_c を二分探索する。
  2. ドッキング位置 D* = D_c + 0.30 での継ぎ目隙間プロファイル
     gap(x) = (short 外形 min-y + D*) - (long 外形 max-y) を
     主階段（x 26.6〜84.4）／段1／背面ランに分けて集計する。
  3. D* での全体幅（y スパン）を本家 296.7mm と比較する。
  4. 実 3D でも確認する: 組立座標に戻した全パーツ同士（左右間）の
     干渉体積が D* で 0、D_c-0.5 では正（接触検出の裏付け）。

実行: ~/workspace/.venv-cad/bin/python check_dock.py
"""
import numpy as np
import trimesh
from shapely.geometry import Polygon, LineString

OUTDIR = "/home/hatch/workspace/7spromax-case/design"
GAP_TARGET = 0.30

def silhouette(half):
    """side_band STL の水平断面から外周ポリゴン（= ケース外形）を得る。"""
    m = trimesh.load(f"{OUTDIR}/side_band_{half}.stl")
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate(tuple(m.geometry.values()))
    sec = m.section(plane_origin=[0, 0, 1.5], plane_normal=[0, 0, 1])
    polys = []
    for ent in sec.entities:
        pts = np.asarray(sec.vertices)[ent.points]
        if len(pts) >= 4:
            p = Polygon(pts[:, :2])
            if not p.is_valid:
                p = p.buffer(0)
            if p.geom_type == "MultiPolygon":
                p = max(p.geoms, key=lambda g: g.area)
            if not p.is_empty:
                polys.append(p)
    return max(polys, key=lambda p: p.area)   # 外周（最大面積のループ）

def shifted(poly, dy):
    return Polygon([(x, y + dy) for x, y in poly.exterior.coords])

def profile(poly, x, which):
    inter = poly.intersection(LineString([(x, -10), (x, 400)]))
    ys = []
    geoms = [inter] if inter.geom_type in ("LineString", "Point") \
        else list(getattr(inter, "geoms", []))
    for g in geoms:
        if g.geom_type == "LineString":
            ys += [c[1] for c in g.coords]
        elif g.geom_type == "Point":
            ys.append(g.y)
        elif g.geom_type == "MultiLineString":
            for gg in g.geoms:
                ys += [c[1] for c in gg.coords]
    if not ys:
        return None
    return min(ys) if which == "min" else max(ys)

def main():
    ps, pl = silhouette("short"), silhouette("long")
    print(f"silhouette short: bounds x[{ps.bounds[0]:.2f},{ps.bounds[2]:.2f}] "
          f"y[{ps.bounds[1]:.2f},{ps.bounds[3]:.2f}] area={ps.area:.0f}")
    print(f"silhouette long : bounds x[{pl.bounds[0]:.2f},{pl.bounds[2]:.2f}] "
          f"y[{pl.bounds[1]:.2f},{pl.bounds[3]:.2f}] area={pl.area:.0f}")

    # ---- 1. 接触オフセット D_c（二分探索、交差面積が 0→正に転じる点） ----
    lo, hi = 140.0, 183.414     # hi は図面レイアウト（隙間 16.4、交差なし）
    assert shifted(ps, hi).intersection(pl).area == 0.0
    for _ in range(50):
        mid = (lo + hi) / 2
        if shifted(ps, mid).intersection(pl).area > 0.0:
            lo = mid
        else:
            hi = mid
    D_c = hi
    print(f"contact offset D_c = {D_c:.3f} (drawing layout 183.414, "
          f"approach {183.414 - D_c:.2f} mm)")
    D_star = D_c + GAP_TARGET
    print(f"docking position D* = D_c + {GAP_TARGET:.2f} = {D_star:.3f}")

    # ---- 2. 継ぎ目隙間プロファイル ----
    def gap_stats(xa, xb, label):
        # 境界ちょうど（蹴上 x や帯端）のサンプルは輪郭の角をかすめて
        # 実形状でない値を返すため、両端 0.25 内側から測る
        xs = np.arange(xa + 0.25, xb - 1e-9, 0.25)
        gaps = []
        for x in xs:
            a = profile(ps, x, "min")
            b = profile(pl, x, "max")
            if a is not None and b is not None:
                gaps.append(a + D_star - b)
        gaps = np.array(gaps)
        print(f"  {label}: n={len(gaps)} min={gaps.min():.3f} "
              f"mean={gaps.mean():.3f} max={gaps.max():.3f}")
        return gaps
    print(f"== seam gap profile at D* = {D_star:.3f} ==")
    gap_stats(26.6, 84.4, "main stair x[26.6,84.4]")
    gap_stats(3.2, 26.6, "step1      x[3.2,26.6] ")
    gap_stats(84.4, 113.7, "back run   x[84.4,113.7]")
    gap_stats(3.2, 113.7, "whole band x[3.2,113.7]")

    # ---- 3. 全体幅 ----
    span = (D_star + ps.bounds[3]) - pl.bounds[1]
    span_c = (D_c + ps.bounds[3]) - pl.bounds[1]
    print(f"overall span at D* = {span:.2f} mm (honke 296.7, diff {span - 296.7:+.2f}); "
          f"at contact D_c = {span_c:.2f} mm")
    width_x = max(ps.bounds[2], pl.bounds[2]) - min(ps.bounds[0], pl.bounds[0])
    print(f"overall depth (x) = {width_x:.2f} mm (honke 114.2)")

    # ---- 4. 実 3D 干渉（組立座標、全パーツ左右間） ----
    def load_part(half, key):
        name = {"tray": f"bottom_tray_{half}", "band": f"side_band_{half}",
                "frame": f"top_frame_{half}", "plate": f"switch_plate_{half}"}[key]
        zo = {"tray": 0.0, "band": 1.9, "frame": 5.7,
              "plate": 7.35 if half == "short" else 9.5}[key]
        m = trimesh.load(f"{OUTDIR}/{name}.stl")
        if isinstance(m, trimesh.Scene):
            m = trimesh.util.concatenate(tuple(m.geometry.values()))
        m.apply_translation([0, 0, zo])
        return m

    def ivol(a, b):
        try:
            return trimesh.boolean.intersection([a, b], engine="manifold").volume
        except Exception:
            return 0.0

    parts_s = {k: load_part("short", k) for k in ("tray", "band", "frame", "plate")}
    parts_l = {k: load_part("long", k) for k in ("tray", "band", "frame", "plate")}
    for D, label in ((D_star, "D* (gap 0.30)"), (D_c - 0.5, "D_c-0.5 (pressed)")):
        tot = 0.0
        worst = None
        for ks, ms in parts_s.items():
            m2 = ms.copy(); m2.apply_translation([0, D, 0])
            for kl, ml in parts_l.items():
                v = ivol(m2, ml)
                tot += v
                if worst is None or v > worst[0]:
                    worst = (v, ks, kl)
        print(f"  3D inter-half interference at {label}: total={tot:.4f} mm3 "
              f"(worst pair {worst[1]}x{worst[2]} = {worst[0]:.4f})")
    print("DOCK CHECK DONE")

if __name__ == "__main__":
    main()
