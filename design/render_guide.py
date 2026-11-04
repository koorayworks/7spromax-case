# -*- coding: utf-8 -*-
"""
7sProMax ケース v2.1 試作片ガイド図の生成（描画専用。設計データは変更しない）

組立プレビュー（斜視＋上面図）に、build_case.py の試作片クリップ範囲を
半透明の色枠で重ね、「試作片が全体のどの範囲の切り出しか」を示す。

クリップ定義は build_case.py の「試作片」セクションからそのまま転記:
  - 階段 (trial_stair_band_<half>):  short x(-3,117.3) y(-3,50) / long x(-3,117.3) y(127.2,180.2)
                           （v2.1 後半: 側面バンドだけのクリップ。バンドはレッジと
                             階段外形の両方を持つため、これで基板との当たりが分かる）
  - 角   (trial_corner_{tray,band,frame}_<half>): short x(80,117.3) y(80,146.4) /
                           long x(80,117.3) y(-3,50)
                           （トレイ／バンド／フレームのパーツ別クリップ。手で重ねて
                             パドルスロット・タクト逃げを確認する）
  ※ ネジ試作片（旧 trial_screw）は廃止（ネジ経路は仮想検証で確認）。
  ※ trial_plate_holes は全体からの切り出しではない（穴だけの単体小片）ため対象外。
  試作片は全9片で、1回の印刷セッションに集約する方針（DESIGN_NOTES §17）。
座標系は build_case.py と同じケース座標（mm）:
  X = 奥行（x=114 側が背面＝マイコン/パドル側）
  Y = 長さ（short: y=0 が階段側 / long: y=177.23 が階段側）
出力 STL はパーツごとに最小 z=0 へ平行移動されているため、組立表示では
  tray: +0（元 0..2.5）、band: +1.9（元 組立 1.9..5.7）、frame: +5.7（元 5.7..16.1）、
  plate short: +7.35（吊りボス下端 HANG_BOT=7.35 が最小）、plate long: +9.5（PLATE_BOT）
を加えて組立位置に戻す。
"""
import json
import numpy as np
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.patches import Polygon as MplPolygon, Rectangle

plt.rcParams["font.family"] = "Noto Sans CJK JP"

BASE = "/home/hatch/workspace/7spromax-case"
DES = f"{BASE}/design"

CLIPS = {
    "short": {
        "stair":  dict(xr=(-3.0, 117.3), yr=(-3.0, 50.0)),
        "corner": dict(xr=(80.0, 117.3), yr=(80.0, 146.4)),
    },
    "long": {
        "stair":  dict(xr=(-3.0, 117.3), yr=(127.2, 180.2)),
        "corner": dict(xr=(80.0, 117.3), yr=(-3.0, 50.0)),
    },
}
KINDS = [
    ("stair",  "#1faa4d", "階段試作片（緑）: trial_stair_band\n　側面バンド（白）の階段側50mm帯。基板の歯・レッジとの当たり確認"),
    ("corner", "#e03131", "角試作片（赤）: trial_corner_tray/band/frame\n　背面-外側の角をパーツ別に切り出し。手で重ねてパドル・タクト・開口まわりを確認"),
]
ZOFF = {"tray": 0.0, "band": 1.9, "frame": 5.7, "plate": {"short": 7.35, "long": 9.5}}
FRAME_TOP = 16.1

# ---- 外形ポリゴン（build_case.py と同じ読み方） ----
dxf = json.load(open(f"{BASE}/work_design/dxf_polys.json"))
ORIGIN = {"short": (0.0, 183.414), "long": (0.0, 0.0)}
IDX = {"short": 0, "long": 1}

def outline_pts(half):
    ox, oy = ORIGIN[half]
    return [(x - ox, y - oy) for x, y in dxf["OUTLINE"][IDX[half]]["pts"]]

def load(name):
    m = trimesh.load(f"{DES}/{name}.stl")
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate(tuple(m.geometry.values()))
    return m

def draw_mesh(ax, mesh, color, zoff, alpha=0.85):
    v = mesh.vertices.copy(); v[:, 2] += zoff
    tris = v[mesh.faces]
    ax.add_collection3d(Poly3DCollection(tris, facecolor=color, edgecolor="none", alpha=alpha))

def box_faces(xr, yr, z0, z1):
    x0, x1 = xr; y0, y1 = yr
    c = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    return [[c[0], c[1], c[2], c[3]], [c[4], c[5], c[6], c[7]],
            [c[0], c[1], c[5], c[4]], [c[2], c[3], c[7], c[6]],
            [c[1], c[2], c[6], c[5]], [c[4], c[0], c[3], c[7]]]

def draw_box(ax, xr, yr, color):
    faces = box_faces(xr, yr, 0.0, FRAME_TOP)
    ax.add_collection3d(Poly3DCollection(faces, facecolor=color, edgecolor=color, alpha=0.22, linewidths=0.8))

def make_guide(half):
    kinds = [(k, c, t) for k, c, t in KINDS if k in CLIPS[half]]
    fig = plt.figure(figsize=(16.5, 9.4))
    fig.suptitle(f"7sProMax ケース試作片ガイド ― {'短い半分（short）' if half=='short' else '長い半分（long）'}：色枠＝試作片の切り出し範囲",
                 fontsize=14)

    # ---- 左: 組立斜視 ----
    ax = fig.add_subplot(1, 2, 1, projection="3d")
    bot = load(f"bottom_tray_{half}")
    ban = load(f"side_band_{half}")
    pla = load(f"switch_plate_{half}")
    fra = load(f"top_frame_{half}")
    draw_mesh(ax, bot, "#6e6e6e", ZOFF["tray"])
    draw_mesh(ax, ban, "#e8c86a", ZOFF["band"])
    draw_mesh(ax, pla, "#9a9a9a", ZOFF["plate"][half])
    draw_mesh(ax, fra, "#c9c9c9", ZOFF["frame"])
    for k, col, _ in kinds:
        cl = CLIPS[half][k]
        draw_box(ax, cl["xr"], cl["yr"], col)
    allv = np.vstack([fra.vertices, bot.vertices])
    mn, mx = allv.min(axis=0), allv.max(axis=0)
    c = (mn + mx) / 2; r = (mx - mn).max() / 2
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(0, 2 * r)
    ax.view_init(elev=30, azim=-58)
    ax.set_box_aspect((mx[0] - mn[0], mx[1] - mn[1], 18))
    ax.set_xlabel("X: 奥行（+X が背面）"); ax.set_ylabel("Y: 長さ")
    ax.set_title("組立斜視（トレイ＋バンド（黄）＋プレート＋フレームを重ねた状態）", fontsize=11)

    # ---- 右: 上面図（mm目盛り付き） ----
    ax2 = fig.add_subplot(1, 2, 2)
    pts = outline_pts(half)
    ax2.add_patch(MplPolygon(pts, closed=True, facecolor="#d9d9d9", edgecolor="#555555", lw=1.2, zorder=1))
    labels = {"stair": "階段", "corner": "角"}
    for k, col, _ in kinds:
        cl = CLIPS[half][k]
        (x0, x1), (y0, y1) = cl["xr"], cl["yr"]
        ax2.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor=col, alpha=0.30,
                                edgecolor=col, lw=2.0, zorder=3))
        lx, ly = x0 + 2, y0 + 2.5
        if half == "long" and k == "stair":
            lx = 82.0  # ボス枠（x<=78）と重ならない位置にラベルを置く
        ax2.text(lx, ly, labels[k], color=col, fontsize=12, fontweight="bold", zorder=4)
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    ax2.set_xlim(min(xs) - 8, max(xs) + 8); ax2.set_ylim(min(ys) - 8, max(ys) + 8)
    ax2.set_aspect("equal"); ax2.grid(True, alpha=0.3)
    ax2.set_xlabel("X: 奥行 mm（右端 x=約114 が背面＝マイコン/パドル側）")
    ax2.set_ylabel("Y: 長さ mm")
    if half == "short":
        ax2.set_title("上面図（下端 y=0 が階段側、上端が外側端）", fontsize=11)
    else:
        ax2.set_title("上面図（上端 y=177 が階段側、下端が外側端）", fontsize=11)

    # ---- 凡例（日本語） ----
    handles = [mpatches.Patch(color=col, alpha=0.55, label=txt) for _, col, txt in kinds]
    fig.legend(handles=handles, loc="lower center", ncol=1, fontsize=10.5,
               frameon=True, bbox_to_anchor=(0.5, 0.005))
    plt.tight_layout(rect=(0, 0.145, 1, 0.94))
    out = f"{DES}/guide_trials_{half}.png"
    plt.savefig(out, dpi=110)
    plt.close()
    print("saved", out)

for half in ("short", "long"):
    make_guide(half)
print("guide done")
