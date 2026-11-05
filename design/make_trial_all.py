#!/usr/bin/env python3
"""試作ピース一式を 180x180 ベッド内に再レイアウトした統合 STL を
作り直す。

構成（v2.4.11／§17.25）: 全 20 ピースを 2 ファイルに分割する。
  - trial_all_1.stl: short 系 7 ピース＋プランジャ 3 個（計 10）
  - trial_all_2.stl: long 系 7 ピース＋プランジャ 3 個（計 10）
各系の内訳は、階段バンド 1＋角ピース（トレイ／バンド／フレーム）3
＋TRRS ピース（トレイ／バンド／フレーム）3 ＝ 7。
スイッチ穴ピース（trial_plate_holes）はパチ留め確認済みのため
本人の指示で除外した。

分割の理由: 従来の単一 trial_all_v22.stl は ASCII 変換後に
約 5.68MB となり、GitHub push（push-files）のサイズ上限
（HTTP 413）に当たったため。各ファイルは ASCII で 4MB 以下を
目安に、系ごとに分けた（プランジャは 3 個ずつ分散）。

配置は MaxRects（空き矩形のベストフィット分割）で、ピース間隔
3mm 以上・ベッド内・z=0 着座・watertight を検証してから書き出す。
"""
import numpy as np
import trimesh
from shapely.geometry import Polygon

BASE = "/home/hatch/workspace/7spromax-case/design"
BED = 180.0
# 予約間隔は公称 3.0 に浮動小数点・ハル計算の余裕 0.05 を足した値に
# する（検証は実測で 3.0 以上を要求）。
GAP = 3.05

GROUPS = {
    "trial_all_1": (["trial_stair_band_short",
                     "trial_corner_tray_short", "trial_corner_band_short",
                     "trial_corner_frame_short",
                     "trial_trrs_tray_short", "trial_trrs_band_short",
                     "trial_trrs_frame_short"], 3),
    "trial_all_2": (["trial_stair_band_long",
                     "trial_corner_tray_long", "trial_corner_band_long",
                     "trial_corner_frame_long",
                     "trial_trrs_tray_long", "trial_trrs_band_long",
                     "trial_trrs_frame_long"], 3),
}


def load_solids(path):
    m = trimesh.load(path)
    if isinstance(m, trimesh.Scene):
        geoms = list(m.geometry.values())
    else:
        geoms = [m]
    solids = []
    for g in geoms:
        solids.extend(g.split(only_watertight=False))
    return [s for s in solids if s.volume > 1.0]


def footprint(mesh):
    v = mesh.vertices
    pts = np.unique(v[:, :2], axis=0)
    if len(pts) < 3:
        b = mesh.bounds
        return Polygon([(b[0, 0], b[0, 1]), (b[1, 0], b[0, 1]),
                        (b[1, 0], b[1, 1]), (b[0, 0], b[1, 1])])
    from scipy.spatial import ConvexHull
    hull = ConvexHull(pts)
    return Polygon(pts[hull.vertices])


def pack(pieces):
    """MaxRects で配置し、[(label, mesh, footprint)] を返す。"""
    items = []
    for label, s in pieces:
        b = s.bounds
        items.append((label, s, b[1, 0] - b[0, 0], b[1, 1] - b[0, 1]))
    items.sort(key=lambda t: -(t[2] * t[3]))   # 面積の大きい順
    placed = []
    free = [(0.0, 0.0, BED, BED)]   # (x, y, w, d) の空き矩形
    for label, s, w0, d0 in items:
        best = None   # (short_leftover, long_leftover, fi, rot, w, d)
        for fi, (fx, fy, fw, fd) in enumerate(free):
            for rot, (w, d) in enumerate(((w0, d0), (d0, w0))):
                if rot and w0 == d0:
                    continue
                if fx + w > BED or fy + d > BED:
                    continue
                if w <= fw and d <= fd and \
                   (w + GAP <= fw or fx + w >= BED - 1e-9) and \
                   (d + GAP <= fd or fy + d >= BED - 1e-9):
                    lo = (min(fw - w, fd - d), max(fw - w, fd - d))
                    if best is None or lo < best[0]:
                        best = (lo, fi, rot, w, d)
        assert best is not None, f"bed overflow at {label}"
        _, fi, rot, w, d = best
        fx, fy, fw, fd = free.pop(fi)
        x, y = fx, fy
        # 使用領域（GAP 込み）を差し引いて空き矩形を分割・ prune
        uw, ud = min(w + GAP, BED - fx), min(d + GAP, BED - fy)
        newfree = []
        for (ax, ay, aw, ad) in free + [(fx, fy, fw, fd)]:
            if ax >= fx + uw or ay >= fy + ud or \
               ax + aw <= fx or ay + ad <= fy:
                newfree.append((ax, ay, aw, ad))
                continue
            if ax < fx:
                newfree.append((ax, ay, fx - ax, ad))
            if ax + aw > fx + uw:
                newfree.append((fx + uw, ay, ax + aw - (fx + uw), ad))
            if ay < fy:
                newfree.append((ax, ay, aw, fy - ay))
            if ay + ad > fy + ud:
                newfree.append((ax, fy + ud, aw, ay + ad - (fy + ud)))
        free = []
        for r in newfree:
            if r[2] <= 0.01 or r[3] <= 0.01:
                continue
            if any(r != q and r[0] >= q[0] and r[1] >= q[1] and
                   r[0] + r[2] <= q[0] + q[2] and
                   r[1] + r[3] <= q[1] + q[3] for q in newfree):
                continue
            free.append(r)
        m = s.copy()
        if rot:
            T = trimesh.transformations.rotation_matrix(np.pi / 2, [0, 0, 1])
            m.apply_transform(T)
        mv = np.array([x, y, 0.0]) - m.bounds[0]
        m.apply_translation(mv)
        assert abs(m.volume - s.volume) < 0.01, f"volume changed {label}"
        assert m.is_watertight, f"not watertight {label}"
        placed.append((label, m, footprint(m)))
        print(f"  {label}: vol={m.volume:.1f} rot={bool(rot)} -> ({x:.1f},{y:.1f})")
    mind = 1e9
    for i in range(len(placed)):
        for j in range(i + 1, len(placed)):
            dij = placed[i][2].distance(placed[j][2])
            if dij < 3.0:
                print(f"  gap {dij:.3f} < 3.0: {placed[i][0]} vs {placed[j][0]}")
            mind = min(mind, dij)
    print(f"min gap between pieces: {mind:.2f}")
    assert mind >= 3.0
    return placed


def main():
    plungers = load_solids(f"{BASE}/plunger.stl")
    assert len(plungers) == 1, f"plunger.stl solids: {len(plungers)}"
    all_placed = {}
    for out_name, (files, n_plunger) in GROUPS.items():
        pieces = []
        for name in files:
            for i, s in enumerate(load_solids(f"{BASE}/{name}.stl")):
                pieces.append((f"{name}#{i}", s))
        for i in range(n_plunger):
            pieces.append((f"plunger#{i}", plungers[0].copy()))
        print(f"== {out_name}: {len(pieces)} pieces")
        placed = pack(pieces)
        allm = trimesh.util.concatenate([m for _, m, _ in placed])
        bb = allm.bounds
        print(f"combined bbox x[{bb[0,0]:.1f},{bb[1,0]:.1f}] "
              f"y[{bb[0,1]:.1f},{bb[1,1]:.1f}] z[{bb[0,2]:.2f},{bb[1,2]:.1f}]")
        assert bb[0, 0] >= 0 and bb[0, 1] >= 0
        assert bb[1, 0] <= BED and bb[1, 1] <= BED
        assert abs(bb[0, 2]) < 1e-6
        path = f"{BASE}/{out_name}.stl"
        allm.export(path)
        import os
        print(f"saved {path} ({os.path.getsize(path)} bytes)")
        all_placed[out_name] = placed
    # ガイド図: 2 ファイル分の配置を並べて描く
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(15, 7.5))
    for ax, (out_name, placed) in zip(axes, all_placed.items()):
        for label, m, fp in placed:
            xs, ys = np.array(fp.exterior.coords).T
            ax.plot(xs, ys, lw=0.9)
            c = fp.centroid
            ax.text(c.x, c.y, label.replace("_", "\n").replace("#", " #"),
                    ha="center", va="center", fontsize=6)
        ax.set_xlim(0, BED)
        ax.set_ylim(0, BED)
        ax.set_aspect("equal")
        ax.grid(alpha=0.25)
        ax.set_title(f"{out_name}.stl ({len(placed)} pieces)")
    fig.suptitle("trial_all layout (v2.4.11: split into 2 files, "
                 "20 pieces total, no plate-holes piece)")
    fig.tight_layout()
    fig.savefig(f"{BASE}/guide_trial_all_v22.png", dpi=110)
    print("saved guide_trial_all_v22.png")


if __name__ == "__main__":
    main()
