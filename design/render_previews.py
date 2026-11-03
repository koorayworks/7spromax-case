# -*- coding: utf-8 -*-
"""7sProMax ケース v1 プレビュー生成（出力済みSTLから描画する）"""
import numpy as np
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

BASE = "/home/hatch/workspace/7spromax-case/design"

def load(name):
    m = trimesh.load(f"{BASE}/{name}.stl")
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate(tuple(m.geometry.values()))
    return m

def draw_mesh(ax, mesh, color, alpha=0.95, zoff=0.0):
    v = mesh.vertices.copy(); v[:, 2] += zoff
    tris = v[mesh.faces]
    pc = Poly3DCollection(tris, facecolor=color, edgecolor="none", alpha=alpha)
    ax.add_collection3d(pc)

def set_view(ax, meshes, elev, azim):
    allv = np.vstack([m.vertices for m in meshes])
    mn, mx = allv.min(axis=0), allv.max(axis=0)
    c = (mn + mx) / 2; r = (mx - mn).max() / 2
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(0, 2 * r)
    ax.view_init(elev=elev, azim=azim)
    ax.set_box_aspect((mx[0] - mn[0], mx[1] - mn[1], 18))

# ---- 1) 分解斜視（short） ----
bot, pla, fra = load("bottom_case_short"), load("switch_plate_short"), load("top_frame_short")
fig = plt.figure(figsize=(11, 9))
ax = fig.add_subplot(111, projection="3d")
draw_mesh(ax, bot, "#555555", zoff=0)
draw_mesh(ax, pla, "#3a7bd5", zoff=16)
draw_mesh(ax, fra, "#b0b0b0", zoff=34)
allv = np.vstack([bot.vertices, pla.vertices + [0, 0, 16], fra.vertices + [0, 0, 34]])
mn, mx = allv.min(axis=0), allv.max(axis=0)
c = (mn + mx) / 2; r = (mx - mn).max() / 2
ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(0, 55)
ax.view_init(elev=32, azim=-58)
ax.set_title("7sProMax case v1 - short half, exploded\n(top: frame / middle: switch plate / bottom: bottom case)\nX=depth(back=+X) Y=length(stair at Y=0)")
plt.tight_layout(); plt.savefig(f"{BASE}/preview_assembly_short.png", dpi=95)
plt.close()

# ---- 1b) 単体斜視（short 3パーツ） ----
fig = plt.figure(figsize=(17, 6))
for i, (name, col, ttl) in enumerate((("bottom_case_short", "#555555", "bottom case (short)"),
                                      ("switch_plate_short", "#3a7bd5", "switch plate (short)"),
                                      ("top_frame_short", "#b0b0b0", "top frame (short)"))):
    ax = fig.add_subplot(1, 3, i + 1, projection="3d")
    m = load(name)
    draw_mesh(ax, m, col)
    set_view(ax, [m], elev=35, azim=-58)
    ax.set_title(ttl)
plt.tight_layout(); plt.savefig(f"{BASE}/preview_parts_short.png", dpi=95)
plt.close()

# ---- 2) 上面図（両半分: フレーム+プレート） ----
fig, axes = plt.subplots(1, 2, figsize=(17, 10))
for ax, half in zip(axes, ["short", "long"]):
    for name, col in ((f"top_frame_{half}", "#b0b0b0"), (f"switch_plate_{half}", "#3a7bd5")):
        m = load(name)
        v = m.vertices; tris = v[m.faces]
        pc = Poly3DCollection(tris, facecolor=col, edgecolor="none", alpha=0.9)
        ax2 = ax  # draw in 2d via projection of triangles at z max only is complex; use 3d inset instead
    ax.axis("off")
plt.close()
# 上面図は3Dを真上から見る方式で作り直す
fig = plt.figure(figsize=(17, 9))
for i, half in enumerate(["short", "long"]):
    ax = fig.add_subplot(1, 2, i + 1, projection="3d")
    fr, pl = load(f"top_frame_{half}"), load(f"switch_plate_{half}")
    draw_mesh(ax, fr, "#b0b0b0"); draw_mesh(ax, pl, "#3a7bd5")
    set_view(ax, [fr, pl], elev=90, azim=-90)
    ax.set_title(f"{half}: top view (frame + plate)")
plt.tight_layout(); plt.savefig(f"{BASE}/preview_top.png", dpi=95)
plt.close()

# ---- 3) 断面（short, y=116 の X-Z 断面: パドルポケット部） ----
fig, axes = plt.subplots(1, 2, figsize=(17, 6))
for ax, (y0, title) in zip(axes, [(116.0, "section at Y=116 (paddle pocket #2, short)"),
                                  (60.0, "section at Y=60 (normal field, short)")]):
    for name, col in (("bottom_case_short", "#555555"), ("switch_plate_short", "#3a7bd5"),
                      ("top_frame_short", "#b0b0b0")):
        m = load(name)
        sec = m.section(plane_origin=[0, y0, 0], plane_normal=[0, 1, 0])
        if sec is None:
            continue
        for ent in sec.entities:
            pts = sec.vertices[ent.points]
            ax.plot(pts[:, 0], pts[:, 2], color=col, lw=1.2)
    # 基板・FR4 の想定位置を破線で
    ax.axhspan(5.7, 7.3, color="green", alpha=0.10)
    ax.axhspan(1.3, 2.5, color="orange", alpha=0.15)
    ax.text(2, 6.4, "PCB (5.7-7.3)", fontsize=8, color="green")
    ax.text(2, 1.7, "FR4 plate (1.3-2.5)", fontsize=8, color="darkorange")
    ax.axhline(16.1, color="gray", ls=":", lw=0.8)
    ax.set_xlabel("X (depth, back = +X)"); ax.set_ylabel("Z")
    ax.set_title(title); ax.grid(True, alpha=0.3); ax.set_aspect("auto")
plt.tight_layout(); plt.savefig(f"{BASE}/preview_sections.png", dpi=95)
plt.close()

# ---- 4) Z積み上げ模式図 ----
fig, ax = plt.subplots(figsize=(9, 7))
layers = [
    (16.1, 12.85, "top frame well wall (pocket opening)", "#b0b0b0"),
    (12.85, 11.0, "frame lip (clamps plate edge)", "#c9c9c9"),
    (11.0, 9.5, "SWITCH PLATE 1.5 (separate part)", "#3a7bd5"),
    (9.5, 7.3, "gap: socket top +2.0 over PCB", "#eeeeee"),
    (7.3, 5.7, "PCB 1.6", "#2e7d32"),
    (5.7, 2.5, "gap 3.2 (ex-acrylic layer / bottom-case wall zone)", "#eeeeee"),
    (2.5, 1.3, "FR4 bottom plate 1.2 (in recess)", "#e8a33d"),
    (1.3, 0.0, "bottom case floor (under recess)", "#555555"),
]
import matplotlib.patches as mpatches
for top, bot_, label, col in layers:
    ax.add_patch(mpatches.Rectangle((0, bot_), 1, top - bot_, facecolor=col, edgecolor="k"))
    ax.text(1.05, (top + bot_) / 2, f"z {bot_:.2f}-{top:.2f}  {label}", va="center", fontsize=9)
ax.set_xlim(0, 3.2); ax.set_ylim(0, 17.0); ax.set_xticks([])
ax.set_ylabel("Z (mm)"); ax.set_title("Z stack (case bottom = 0, total height 16.1)")
plt.tight_layout(); plt.savefig(f"{BASE}/preview_stack.png", dpi=95)
plt.close()
print("previews done")
