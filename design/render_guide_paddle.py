# -*- coding: utf-8 -*-
"""
7sProMax ケース v2.1 パドルガイド図の生成（描画専用。設計データは変更しない）

出力:
  guide_paddle_short.png     : y=110.9（short タクト2中心）の x-z 断面。
                               トレイ／バンド／フレームの実断面（STL から取得）に、
                               配置B のパドルエンベロープ・フレームスロット
                               （z 6.2〜10.1）・タクト・基板を重ねる。
  guide_paddle_top_short.png : 上面図。外形・キャビティ・トレイ／バンド窓・
                               フレームスロット・パドル占有範囲を示す。
座標は build_case.py と同じケース座標（組立座標）。
STL はパーツごとに最小 z=0 へ平行移動されているため、バンドは +1.9、
フレームは +5.7 して描く。
"""
import json
import numpy as np
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon, Rectangle
from shapely.geometry import Polygon, LineString

plt.rcParams["font.family"] = "Noto Sans CJK JP"

BASE = "/home/hatch/workspace/7spromax-case"
DES = f"{BASE}/design"
Y_SEC = 110.9           # short タクト2の中心
TACT_SHORT = [102.6, 110.9, 121.7]
SLOT = dict(x0=104.0, z0=6.2, z1=10.1, hw=3.0)
WIN_SPAN = (97.65, 126.65)   # v2.1 トレイ／バンド窓（連結後）
WIN_X0 = 97.0

def load(name):
    m = trimesh.load(f"{DES}/{name}.stl")
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate(tuple(m.geometry.values()))
    return m

def section_xz(mesh, y, zoff):
    segs = trimesh.intersections.mesh_plane(mesh, [0, 1, 0], [0, y, 0], return_faces=False)
    return [((s[0][0], s[0][2] + zoff), (s[1][0], s[1][2] + zoff)) for s in segs]

# 基板外形（実測）とキャビティ
pcb_pts = np.loadtxt(f"{BASE}/template/pcb_outline2_short.csv", delimiter=",", skiprows=1)
pcb = Polygon([tuple(r) for r in pcb_pts])
cavity = pcb.buffer(0.5, join_style=1)
line = LineString([(-1, Y_SEC), (200, Y_SEC)])
ix = pcb.intersection(line)
pcb_xr = (min(c[0] for c in ix.coords), max(c[0] for c in ix.coords))

# ================= 断面図 =================
fig, ax = plt.subplots(figsize=(11, 6.4))
for (ax0, az0), (ax1, az1) in section_xz(load("bottom_tray_short"), Y_SEC, 0.0):
    ax.plot([ax0, ax1], [az0, az1], color="#555555", lw=1.1)
for (ax0, az0), (ax1, az1) in section_xz(load("side_band_short"), Y_SEC, 1.9):
    ax.plot([ax0, ax1], [az0, az1], color="#e8912d", lw=1.1)
for (ax0, az0), (ax1, az1) in section_xz(load("top_frame_short"), Y_SEC, 5.7):
    ax.plot([ax0, ax1], [az0, az1], color="#2166e0", lw=1.1)
# 基板
ax.add_patch(Rectangle((pcb_xr[0], 5.7), pcb_xr[1] - pcb_xr[0], 1.6,
                       facecolor="#2ca02c", alpha=0.45, edgecolor="#2ca02c"))
ax.text(pcb_xr[0] + 1, 6.0, "基板 (z 5.7〜7.3)", color="#1e7a1e", fontsize=10)
# タクト（裏面実装、本体 4.5x4.5x3.3 を基板下面から）
ax.add_patch(Rectangle((103.75, 2.4), 4.5, 3.3, facecolor="none",
                       edgecolor="#9467bd", lw=1.4, linestyle="--"))
ax.text(96.5, 3.4, "タクト", color="#9467bd", fontsize=10)
# パドルエンベロープ（配置B、この断面ではブロック上部とバーが見える）
ax.add_patch(Rectangle((101, 7.7), 10, 1.8, facecolor="#e03131", alpha=0.35,
                       edgecolor="#e03131", lw=1.4))
ax.add_patch(Rectangle((111, 6.8), 17.3, 2.7, facecolor="#e03131", alpha=0.35,
                       edgecolor="#e03131", lw=1.4))
ax.text(112.5, 12.6, "パドル（配置B）: ブロック x101〜111 / バー x111〜128.3, z 6.8〜9.5",
        color="#e03131", fontsize=10.5)
# スロット
xmax = 114.29
ax.add_patch(Rectangle((SLOT["x0"], SLOT["z0"]), xmax - SLOT["x0"], SLOT["z1"] - SLOT["z0"],
                       facecolor="#2166e0", alpha=0.13, edgecolor="#2166e0", lw=1.6, linestyle="--"))
ax.text(95.5, 10.6, "フレームスロット z 6.2〜10.1（x は 104 から壁内）",
        color="#2166e0", fontsize=10.5)
ax.text(60, 15.2, "灰=トレイ / 橙=バンド（白） / 青=フレーム実断面", color="#333333", fontsize=10)
ax.set_xlim(88, 132); ax.set_ylim(0, 17.5)
ax.set_aspect("equal"); ax.grid(True, alpha=0.3)
ax.set_xlabel("X: 奥行 mm（右が背面・ケース外）")
ax.set_ylabel("Z: 高さ mm（組立座標）")
ax.set_title("パドル断面（short, y=110.9 タクト中心）― v2.1 スロット形状", fontsize=12)
plt.tight_layout(); plt.savefig(f"{DES}/guide_paddle_short.png", dpi=110); plt.close()
print("saved guide_paddle_short.png")

# ================= 上面図 =================
dxf = json.load(open(f"{BASE}/work_design/dxf_polys.json"))
ox, oy = 0.0, 183.414
outline_pts = [(x - ox, y - oy) for x, y in dxf["OUTLINE"][0]["pts"]]
fig, ax = plt.subplots(figsize=(8.6, 10.4))
ax.add_patch(MplPolygon(outline_pts, closed=True, facecolor="#d9d9d9",
                        edgecolor="#555555", lw=1.2, zorder=1))
ax.add_patch(MplPolygon(list(cavity.exterior.coords), closed=True, facecolor="none",
                        edgecolor="#2ca02c", lw=1.2, zorder=2))
ax.text(30, 60, "緑=キャビティ（基板+0.5）", color="#1e7a1e", fontsize=10, zorder=6)
# トレイ／バンド窓
ax.add_patch(Rectangle((WIN_X0, WIN_SPAN[0]), xmax + 1 - WIN_X0, WIN_SPAN[1] - WIN_SPAN[0],
                       facecolor="#e03131", alpha=0.16, edgecolor="#e03131", lw=1.2, zorder=3))
ax.text(45, 131, "赤=トレイ／バンド窓（v2.1 で連結した1区間）", color="#e03131", fontsize=10, zorder=6)
# フレームスロットとパドル占有
for c in TACT_SHORT:
    ax.add_patch(Rectangle((SLOT["x0"], c - SLOT["hw"]), xmax - SLOT["x0"], SLOT["hw"] * 2,
                           facecolor="#2166e0", alpha=0.30, edgecolor="#2166e0", lw=1.2, zorder=4))
    ax.add_patch(Rectangle((101, c - 4.35), 10, 8.7, facecolor="none",
                           edgecolor="#e03131", lw=1.3, zorder=5))
    ax.add_patch(Rectangle((111, c - 2.4), 17.3, 4.8, facecolor="#e03131", alpha=0.25,
                           edgecolor="#e03131", lw=1.0, zorder=4))
    ax.plot([106], [c], marker="x", color="#000000", ms=7, zorder=6)
ax.text(45, 136.5, "青=フレームスロット（中心±3.0）/ 赤枠=パドルブロック（幅8.7）",
        color="#2166e0", fontsize=10, zorder=6)
ax.text(45, 141.5, "×=タクト中心（実測）", color="#000000", fontsize=10, zorder=6)
ax.set_xlim(-4, 136); ax.set_ylim(88, 150)
ax.set_aspect("equal"); ax.grid(True, alpha=0.3)
ax.set_xlabel("X: 奥行 mm（右端が背面）")
ax.set_ylabel("Y: 長さ mm")
ax.set_title("パドルまわり上面図（short 背面帯）― v2.1", fontsize=12)
plt.tight_layout(); plt.savefig(f"{DES}/guide_paddle_top_short.png", dpi=110); plt.close()
print("saved guide_paddle_top_short.png")
