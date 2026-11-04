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
    # slots from the v2.2 combined file
    slots = []
    for s in load_solids(f"{BASE}/v22_backup/trial_all_v22.stl"):
        slots.append(dict(key=key_of(s), mesh=s))
    print(f"{len(slots)} slots from v2.2 layout")
    pieces = []
    for name in FILES:
        for i, s in enumerate(load_solids(f"{BASE}/{name}.stl")):
            pieces.append((f"{name}#{i}", s))
    print(f"{len(pieces)} new pieces")
    assert len(slots) == len(pieces)
    # match by (w, d, h) with tolerance (v2.3 pieces can be a few mm
    # shallower than their v2.2 slots); allow 90-degree rotation
    used = set()
    placed = []
    for label, s in pieces:
        k = key_of(s)
        best = None
        for j, sl in enumerate(slots):
            if j in used:
                continue
            sk = sl["key"]
            for rot in (False, True):
                kk = (k[1], k[0], k[2]) if rot else k
                if abs(sk[0] - kk[0]) <= 1 and abs(sk[2] - kk[2]) <= 1 \
                        and -1 <= sk[1] - kk[1] <= 6:
                    score = abs(sk[0] - kk[0]) + abs(sk[1] - kk[1])
                    if best is None or score < best[0]:
                        best = (score, j, rot)
        assert best is not None, f"no slot for {label} key={k}"
        _, j, rot = best
        used.add(j)
        sl = slots[j]
        m = s.copy()
        if rot:
            T = trimesh.transformations.rotation_matrix(np.pi / 2, [0, 0, 1])
            m.apply_transform(T)
        # translate: new bbox min -> slot bbox min (z to 0)
        d = sl["mesh"].bounds[0] - m.bounds[0]
        d[2] = -m.bounds[0, 2]
        m.apply_translation(d)
        assert abs(m.volume - s.volume) < 0.01, f"volume changed {label}"
        assert m.is_watertight, f"not watertight {label}"
        placed.append((label, m, footprint(m)))
        print(f"  {label}: vol={m.volume:.1f} rot={rot} -> "
              f"({sl['mesh'].bounds[0,0]:.1f},{sl['mesh'].bounds[0,1]:.1f})")
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
