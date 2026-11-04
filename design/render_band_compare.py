#!/usr/bin/env python3
"""guide_band_stair_compare.png — side band stair-zone wall, v2.2 vs v2.3.

Sections of side_band_<half>.stl at the ledge-zone height (STL-local
z=3.2, assembly z=5.1) where the inner boundary is the cavity: the wall
between the quantized outer steps and the cavity.  v2.2 (backup) used
outline2 + bridge; v2.3 uses outline3 + the stair wall cap.  Also
prints the erosion-sense wall thickness stats in the stair zone.
"""
import numpy as np
import trimesh
from shapely.geometry import Polygon, Point
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = "/home/hatch/workspace/7spromax-case/design"
ZLOC = 3.2          # STL-local z (ledge zone)
STAIR = {"short": (0, 114.3, -6, 55), "long": (0, 114.3, 118, 183)}


def section_material(path, z):
    m = trimesh.load(path)
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate(tuple(m.geometry.values()))
    sec = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
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
    outer = max(loops, key=lambda p: p.area)
    mat = outer
    for p in loops:
        if p is not outer:
            mat = mat.difference(p)
    return mat


def wall_stats(mat, half):
    x0, x1, y0, y1 = STAIR[half]
    zone = Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    w = mat.intersection(zone)
    if w.is_empty:
        return None
    outer_b = mat.boundary
    vals = []
    for x in np.arange(x0, x1, 0.3):
        for y in np.arange(y0, y1, 0.3):
            p = Point(x, y)
            if w.covers(p):
                vals.append(outer_b.distance(p))
    vals = np.array(vals)
    return vals.max(), np.percentile(vals, 99), len(vals)


fig, axes = plt.subplots(2, 2, figsize=(15, 9))
for row, half in enumerate(("short", "long")):
    for col, (tag, path) in enumerate((
            ("v2.2 (outline2+bridge)", f"{BASE}/v22_backup/side_band_{half}.stl"),
            ("v2.3 (outline3+cap)", f"{BASE}/side_band_{half}.stl"))):
        ax = axes[row][col]
        mat = section_material(path, ZLOC)
        polys = [mat] if mat.geom_type == "Polygon" else list(mat.geoms)
        for p in polys:
            x, y = np.array(p.exterior.coords).T
            ax.plot(x, y, color="#c33" if col == 0 else "#1a7", lw=1.0)
            for hole in p.interiors:
                hx, hy = np.array(hole.coords).T
                ax.plot(hx, hy, color="#c33" if col == 0 else "#1a7", lw=0.8)
        x0, x1, y0, y1 = STAIR[half]
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)
        ax.set_aspect("equal")
        ax.grid(alpha=0.25)
        ax.set_title(f"{half} band @ledge zone — {tag}")
        ax.set_xlabel("x (case mm)")
        ax.set_ylabel("y (case mm)")
        if half == "short" and col == 0:
            ax.annotate("groove-valley in cavity\n= thick triangular wall",
                        xy=(40, 33), xytext=(52, 44),
                        fontsize=9, color="#c33",
                        arrowprops=dict(arrowstyle="->", color="#c33"))
        if half == "short" and col == 1:
            ax.annotate("clean rectangular steps",
                        xy=(36, 6), xytext=(52, 44),
                        fontsize=9, color="#1a7",
                        arrowprops=dict(arrowstyle="->", color="#1a7"))
        if half == "long" and col == 0:
            ax.annotate("jagged inner boundary\n(bridge drag)",
                        xy=(47, 154), xytext=(58, 138),
                        fontsize=9, color="#c33",
                        arrowprops=dict(arrowstyle="->", color="#c33"))
        if half == "long" and col == 1:
            ax.annotate("clean rectangular steps",
                        xy=(36, 154), xytext=(58, 138),
                        fontsize=9, color="#1a7",
                        arrowprops=dict(arrowstyle="->", color="#1a7"))
fig.suptitle("Side band stair wall: v2.2 vs v2.3 (tab run x 26.6-46.2 "
             "was the thick triangle)", fontsize=12)
fig.tight_layout()
fig.savefig(f"{BASE}/guide_band_stair_compare.png", dpi=110)
print("saved design/guide_band_stair_compare.png")
