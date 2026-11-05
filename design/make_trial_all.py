#!/usr/bin/env python3
"""trial_all_v22.stl を作り直す: 試作9ファイル（11ピース）を
180x180 ベッド内に再レイアウトした統合 STL。

レイアウトは v2.2 版 trial_all（design/v22_backup/）の配置スロットを
再利用する: クリップ範囲が同じなので各ピースの外形寸法はほぼ同一で、
(w, d, z高さ) でスロットと新ピースを対応付け、回転・平行移動だけを
コピーする。各ピースの体積一致・ベッド内・間隔 3mm 以上・z=0 着座・
watertight を検証してから書き出す。
"""
import numpy as np
import trimesh
from shapely.geometry import Polygon

BASE = "/home/hatch/workspace/7spromax-case/design"
FILES = ["trial_plate_holes",
         "trial_stair_band_short", "trial_stair_band_long",
         "trial_corner_tray_short", "trial_corner_band_short",
         "trial_corner_frame_short",
         "trial_corner_tray_long", "trial_corner_band_long",
         "trial_corner_frame_long"]
BED = 180.0


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


def key_of(mesh):
    b = mesh.bounds
    return (round(b[1, 0] - b[0, 0]), round(b[1, 1] - b[0, 1]),
            round(b[1, 2] - b[0, 2]))


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


def main():
    pieces = []
    for name in FILES:
        for i, s in enumerate(load_solids(f"{BASE}/{name}.stl")):
            pieces.append((f"{name}#{i}", s))
    # v2.4.5 (§17.19): プランジャ（小ボタン）を 6 個追加する
    # （左右 3 タクトずつ、共通部品 plunger.stl の複製）。
    plungers = load_solids(f"{BASE}/plunger.stl")
    assert len(plungers) == 1, f"plunger.stl solids: {len(plungers)}"
    for i in range(6):
        pieces.append((f"plunger#{i}", plungers[0].copy()))
    print(f"{len(pieces)} pieces")
    # v2.4.4: v2.2 スロット再利用はバンド角フラグメントの寸法変化
    # （窓位置の移動）で破綻したため、棚置きパッキングに切り替えた。
    # bbox 矩形で棚（行）に並べ、行内・行間とも 3mm 以上の間隔を
    # 空ける。配置後の検証（体積・watertight・間隔・ベッド内）は従来
    # どおり下流のアサーションで行う。
    # v2.4.10 (§17.24): 階段バンド long の奥行き増（51.5）で棚置き
    # グリーディが溢れたため、MaxRects（空き矩形のベストフィット
    # 分割）に変更。ピース間隔は各ピースを GAP 分膨らませて確保する
    # （ベッド端だけは実寸で判定）。
    GAP = 3.0
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
            mind = min(mind, placed[i][2].distance(placed[j][2]))
    print(f"min gap between pieces: {mind:.2f}")
    assert mind >= 3.0
    allm = trimesh.util.concatenate([m for _, m, _ in placed])
    bb = allm.bounds
    print(f"combined bbox x[{bb[0,0]:.1f},{bb[1,0]:.1f}] "
          f"y[{bb[0,1]:.1f},{bb[1,1]:.1f}] z[{bb[0,2]:.2f},{bb[1,2]:.1f}]")
    assert bb[0, 0] >= 0 and bb[0, 1] >= 0
    assert bb[1, 0] <= BED and bb[1, 1] <= BED
    assert abs(bb[0, 2]) < 1e-6
    allm.export(f"{BASE}/trial_all_v22.stl")
    print("saved trial_all_v22.stl")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 9))
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
    ax.set_title("trial_all_v22 layout (v2.4 pieces, v2.2 arrangement)")
    fig.tight_layout()
    fig.savefig(f"{BASE}/guide_trial_all_v22.png", dpi=110)
    print("saved guide_trial_all_v22.png")


if __name__ == "__main__":
    main()
