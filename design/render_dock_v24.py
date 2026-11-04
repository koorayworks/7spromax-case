# -*- coding: utf-8 -*-
"""
7sProMax ケース v2.4 ドッキング状態レンダリング（§17.13、描画専用）

v2.4 の実 STL を、ドッキング位置（相対 dy = 157.780、check_dock.py の
実測 D_c + 0.30）に寄せた状態で描く。基盤は render_assembled_v22.py
（matplotlib 3D + Poly3DCollection、床は2パス合成）。
配置は平行移動のみ（反転・鏡像・回転なし）: long を図面座標の低 y 側、
short を +157.780 側に置く。階段どうしが中央で噛み合い、継ぎ目は
主階段で約 0.3mm。全体幅は 301.14mm（本家 296.7）。

実行: ~/workspace/.venv-cad/bin/python render_dock_v24.py
出力: guide_dock_v24_3d.png（斜め図、1600 x 1100px）、
      guide_dock_v24_top.png（上面図: 図面レイアウト vs ドッキング位置）
"""
import csv
import hashlib
import json
import os
import tempfile

import numpy as np
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import proj3d
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from shapely.geometry import Polygon
from PIL import Image, ImageDraw, ImageFilter

plt.rcParams["font.family"] = "Noto Sans CJK JP"

DES = "/home/hatch/workspace/7spromax-case/design"
TPL = "/home/hatch/workspace/7spromax-case/template"
WRK = "/home/hatch/workspace/7spromax-case/work_design/dxf_polys.json"

FIG_W, FIG_H, DPI = 16.0, 11.0, 100  # → 1600 x 1100px

# 色（印刷色どおり: 黒系パーツ／白バンド／黒基板／銀パドル）
COL_TRAY = "#26262a"
COL_FRAME = "#1b1b1e"
COL_PLATE = "#2e2e33"
COL_BAND = "#f7f3e8"        # 白バンド
COL_PCB = "#101216"         # 黒基板
COL_KEY = "#333338"         # スロット位置のタクトキャップ（参考表現）
COL_PADDLE = "#c9ccd4"      # 銀（金属パドル）
COL_ACCENT = "#37c978"      # 本家アクセント（緑）カバー: 図面外の参考表現
LAYOUT_DY = 157.780         # ドッキング位置での short の y オフセット（check_dock 実測 D_c+0.30）
PAIR_CY = 150.570           # ドッキング時の全体 y 範囲（0..301.14）の中心

# ---------------------------------------------------------------- 基礎
def load(name):
    m = trimesh.load(f"{DES}/{name}.stl")
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate(tuple(m.geometry.values()))
    return m

def sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()

def shade_faces(normals, base_rgb, key=(0.42, 0.34, 0.84), fill=(-0.55, 0.28, 0.55),
                bounce=(0.0, 0.0, -1.0)):
    """簡易3光源シェーディング（ガイド図の flat 面色に陰影をつける）。
    黒系パーツでも穴や段差が読めるよう、ベース色を少し持ち上げて
    （ガンマ的に）陰影の階調を確保する。"""
    n = normals / np.linalg.norm(normals, axis=1, keepdims=True)
    k = np.array(key) / np.linalg.norm(key)
    f = np.array(fill) / np.linalg.norm(fill)
    b = np.array(bounce)
    inten = 0.30 + 0.62 * np.clip(n @ k, 0, 1) + 0.20 * np.clip(n @ f, 0, 1) \
        + 0.10 * np.clip(n @ b, 0, 1)
    base = np.array(matplotlib.colors.to_rgb(base_rgb))
    lift = base ** 0.62
    rgb = np.clip(lift[None, :] * (0.35 + 0.75 * inten[:, None]), 0, 1)
    if np.all(base < 0.35):
        # 黒系パーツ: パーツ内では圧縮せず、強度に対してガンマ 0.55 で
        # 持ち上げるだけにする。パーツ間で正規化すると、プレート上面と
        # 基板面が同じ白さになって穴が埋まって見えるため、絶対階層を保つ:
        #   プレート上面 ≈0.52 / 穴の底（基板上面）≈0.21 / 側面 ≈0.3
        rgb = np.clip((inten ** 0.55)[:, None] * base[None, :] ** 0.35
                      * np.array([1.06, 1.04, 1.0])[None, :], 0, 1)
    return np.hstack([rgb, np.ones((len(rgb), 1))])

# 全3D面を1つのコレクションにまとめて描くための蓄積リスト。
# matplotlib 3D はコレクション単位では「最も手前の頂点の深度」で描画順を
# 決める（do_3d_projection が min(pzs) を返す）ため、パーツごとに
# コレクションを分けると、手前側の半分では最下層のトレイのコレクション
# がプレートを丸ごと覆ってしまう。1コレクションにまとめれば、面ごとの
# 平均深度ソートがシーン全体に効き、前後関係が局所的に正しくなる。
PENDING = []  # (verts (N,3), faces (M,3), colors (M,4))

def flush_pending(ax):
    if not PENDING:
        return
    vs, fs, cs = [], [], []
    off = 0
    for v, f, c in PENDING:
        vs.append(v); fs.append(f + off); cs.append(c)
        off += len(v)
    PENDING.clear()
    ax.add_collection3d(Poly3DCollection(
        np.vstack(vs)[np.vstack(fs)], facecolors=np.vstack(cs),
        edgecolor="none", linewidths=0, shade=False))

def split_large_faces(mesh, max_area=250.0):
    """大きな面を扇状に分割する（描画専用、形状は変えない）。
    matplotlib 3D は面の平均深度で描画順を決めるため、トレイ床のような
    巨大な面（実測で最大 6839mm²）があると、その面の平均深度が広範囲を
    代表してしまい前後関係が崩れる。面を重心＋辺中点で6分割し、
    局所的にソートさせる。"""
    verts = [v for v in mesh.vertices]
    faces = [tuple(f) for f in mesh.faces]
    for _ in range(4):
        tris = np.array([verts[i] for f in faces for i in f]).reshape(-1, 3, 3)
        areas = 0.5 * np.linalg.norm(
            np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]), axis=1)
        if len(areas) == 0 or areas.max() <= max_area:
            break
        new_faces = []
        for f, a in zip(faces, areas):
            if a <= max_area:
                new_faces.append(f)
                continue
            p = [np.array(verts[i], float) for i in f]
            c = (p[0] + p[1] + p[2]) / 3.0
            ci = len(verts); verts.append(c)
            mid = []
            for i in range(3):
                mid.append(len(verts))
                verts.append((p[i] + p[(i + 1) % 3]) / 2.0)
            v0, v1, v2 = f
            m01, m12, m20 = mid
            new_faces += [(v0, m01, ci), (m01, v1, ci), (v1, m12, ci),
                          (m12, v2, ci), (v2, m20, ci), (m20, v0, ci)]
        faces = new_faces
    out = trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces),
                          process=False)
    return out

def add_mesh(ax, mesh, tmat4, base_color, alpha=1.0):
    mesh = split_large_faces(mesh)
    v = mesh.vertices @ tmat4[:3, :3].T + tmat4[:3, 3]
    n = mesh.face_normals @ tmat4[:3, :3].T
    fc = shade_faces(n, base_color)
    if alpha < 1.0:
        fc[:, 3] = alpha
    PENDING.append((v, np.asarray(mesh.faces), fc))

def add_box(ax, xr, yr, zr, tmat4, base_color, alpha=1.0):
    x0, x1 = xr; y0, y1 = yr; z0, z1 = zr
    c = np.array([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                  (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], float)
    quads = [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [2, 3, 7, 6],
             [1, 2, 6, 5], [4, 0, 3, 7]]
    w = c @ tmat4[:3, :3].T + tmat4[:3, 3]
    polys, cols = [], []
    for q in quads:
        p = w[q]
        n = np.cross(p[1] - p[0], p[2] - p[0])
        ln = np.linalg.norm(n)
        n = n / ln if ln > 0 else np.array([0.0, 0.0, 1.0])
        polys.append(p)
        cols.append(shade_faces(n[None, :], base_color)[0])
    cols = np.array(cols)
    if alpha < 1.0:
        cols[:, 3] = alpha
    v = np.vstack(polys)
    f = []
    for i in range(len(polys)):
        b = 4 * i
        f += [(b, b + 1, b + 2), (b, b + 2, b + 3)]
    PENDING.append((v, np.array(f), np.repeat(cols, 2, axis=0)))

def add_polys(ax, polys, normals, tmat4, base_color, alpha=1.0):
    w = [p @ tmat4[:3, :3].T + tmat4[:3, 3] for p in polys]
    n = normals @ tmat4[:3, :3].T
    fc = shade_faces(n, base_color)
    if alpha < 1.0:
        fc[:, 3] = alpha
    vs, fs, cs = [], [], []
    off = 0
    for p, c in zip(w, fc):
        vs.append(p)
        for i in range(1, len(p) - 1):
            fs.append((off, off + i, off + i + 1))
            cs.append(c)
        off += len(p)
    PENDING.append((np.vstack(vs), np.array(fs), np.array(cs)))

def extrude_z(polys_xy, z0, z1):
    """shapely ポリゴン群を z0→z1 で押し出した (polys, normals) を返す。"""
    polys, normals = [], []
    for poly in polys_xy:
        ext = np.asarray(poly.exterior.coords)
        top = np.column_stack([ext, np.full(len(ext), z1)])
        bot = np.column_stack([ext, np.full(len(ext), z0)])
        polys.append(top); normals.append((0.0, 0.0, 1.0))
        polys.append(bot[::-1]); normals.append((0.0, 0.0, -1.0))
        for (ax_, ay_), (bx, by) in zip(ext[:-1], ext[1:]):
            q = np.array([(ax_, ay_, z0), (bx, by, z0), (bx, by, z1), (ax_, ay_, z1)])
            d = np.array([bx - ax_, by - ay_, 0.0])
            n = np.cross((0, 0, 1), d)
            ln = np.linalg.norm(n)
            polys.append(q)
            normals.append(tuple(n / ln) if ln > 0 else (0.0, 0.0, 1.0))
    return polys, np.array(normals, float)

# スイッチ中心・横長スロット（DXF テンプレ抽出＝設計の正本、build_case と同じ振り分け）
_dx = json.load(open(WRK))
_ORIGIN = {"short": (0.0, 183.414), "long": (0.0, 0.0)}
SW, SLOTS = {}, {}
for half in ("short", "long"):
    ox, oy = _ORIGIN[half]
    sw, sl = [], []
    for hp in _dx["SWITCH_HOLES"]:
        pts = hp["pts"]
        cy = float(np.mean([q[1] for q in pts]))
        if (cy > 183.41) == (half == "short"):
            poly = Polygon([(x - ox, y - oy) for x, y in pts])
            b = poly.bounds
            if (b[2] - b[0]) > 15.5 and (b[3] - b[1]) < 8.0:
                sl.append(poly)
            else:
                c = poly.centroid
                sw.append((c.x, c.y))
    SW[half], SLOTS[half] = sw, sl

# パドル（配置B: バー幅4.8・厚2.7・z 6.8〜9.5、タクト中心は build_case と同じ）
TACT = {"short": [102.6, 110.9, 121.7], "long": [14.0, 23.5, 35.9]}

def pcb_polys(half):
    with open(f"{TPL}/pcb_outline2_{half}.csv") as f:
        pts = [(float(r["x_mm"]), float(r["y_mm"])) for r in csv.DictReader(f)]
    return [Polygon(pts)]

# 半分の配置変換（ケース座標 → 画像ワールド座標）
#   図面レイアウトの相対配置（long: dy=0、short: dy=+LAYOUT_DY）のまま
#   全体を y 中心 0 へ平行移動するだけ。反転・鏡像・回転はしない
#   （旧版は long を diag(1,-1,1) で鏡像化し、左右も入れ替わっていた）。
def half_T(half):
    T = np.eye(4)
    T[1, 3] = (LAYOUT_DY if half == "short" else 0.0) - PAIR_CY
    return T

ASM_Z = {"tray": 0.0, "band": 1.9, "frame": 5.7,
         "plate": {"short": 7.35, "long": 9.5}}
PARTS = [("bottom_tray", "tray", COL_TRAY), ("side_band", "band", COL_BAND),
         ("top_frame", "frame", COL_FRAME), ("switch_plate", "plate", COL_PLATE)]

def draw_half(ax, half):
    T = half_T(half)
    # パーツの登録順は見た目に影響しない（全3D面を1コレクションに
    # まとめて面ごとの深度ソートに任せる。PENDING のコメント参照）。
    for stem, key, col in PARTS:
        zo = ASM_Z[key] if key != "plate" else ASM_Z["plate"][half]
        m = load(f"{stem}_{half}")
        m.apply_translation([0, 0, zo])
        add_mesh(ax, m, T, col)
    # 基板（実測外形、厚さ1.6、z 5.7〜7.3、黒）。
    # 全面スラブで描くと、外形の三角分割にできる細長い面が平均深度の
    # ソートでプレートの上に被ってしまう（実測で筋状の乱れを確認）。
    # 実際に見えるのはスイッチ穴の底だけなので、穴位置に穴（14.15角）
    # より一回り小さい暗い四角を置く表現にする（プレートの面とは画面上で
    # 重ならないため、ソートの影響を受けない）。
    for (cx, cy) in SW[half]:
        add_box(ax, (cx - 6.5, cx + 6.5), (cy - 6.5, cy + 6.5), (5.7, 7.3), T, COL_PCB)
    # スイッチは描かない（キーキャップのモデルが無いため）。完成形は
    # フレーム開口とプレートのスイッチ穴（14.15角）から想像できる絵にする。
    # 横長スロット位置だけ、小さなタクトキャップの参考表現を置く。
    for poly in SLOTS[half]:
        b = poly.bounds
        add_box(ax, (b[0] + 0.6, b[2] - 0.6), (b[1] + 0.6, b[3] - 0.6), (11.0, 13.4), T, COL_KEY)
    # パドル: 銀バーが背面スロット（z 6.2〜10.1）を通って外へ出る
    for tc in TACT[half]:
        add_box(ax, (100.0, 128.3), (tc - 2.4, tc + 2.4), (6.8, 9.5), T, COL_PADDLE)
    # 本家アクセント風カバー（緑、背面×外側端の隅: 図面外の参考表現。
    # パドルの3連がその上に並ぶ位置に合わせる）
    if half == "short":
        cov = Polygon([(84, 99.5), (114.29, 99.5), (114.29, 143.36), (99, 143.36), (84, 121)])
    else:
        cov = Polygon([(84, 0.0), (114.28, 0.0), (114.28, 43.5), (99, 43.5), (84, 22)])
    # v2.4 ドッキング図では緑カバー（参考表現）は描かない（継ぎ目優先）

# ---------------------------------------------------------------- グロー帯
def draw_band_glow(ax):
    """白バンドの外面に沿って薄い光の帯を重ねる（外形輪郭の帯域だけ抽出）。"""
    for half in ("short", "long"):
        m = load(f"side_band_{half}")
        v = m.vertices + [0, 0, 1.9]
        n = m.face_normals
        tris = v[m.faces]
        cen = tris.mean(axis=1)
        # 外周の側面（水平法線）かつ光る帯の高さ（組立 z 2.5〜4.4）だけ
        mask = (np.abs(n[:, 2]) < 0.3) & (cen[:, 2] > 2.45) & (cen[:, 2] < 4.45)
        sel = tris[mask]
        if len(sel) == 0:
            continue
        bnd = load(f"bottom_tray_{half}").bounds
        cen_all = (bnd[0] + bnd[1])[:2] / 2
        d = sel[:, :, :2] - cen_all
        ln = np.linalg.norm(d, axis=2, keepdims=True)
        out = sel.copy()
        out[:, :, :2] = sel[:, :, :2] + d / np.maximum(ln, 1e-6) * 0.55
        T = half_T(half)
        w = out @ T[:3, :3].T + T[:3, 3]
        rgba = np.tile(np.array([0.55, 1.0, 0.95, 0.30]), (len(w), 1))
        vv = w.reshape(-1, 3)
        PENDING.append((vv, np.arange(len(vv)).reshape(-1, 3), rgba))

# ---------------------------------------------------------------- 床の合成
def footprint_ring(half, grow=0.0):
    """半分のフットプリント（ワールド XY の輪）を返す。grow>0 で外側へ膨張。"""
    T = half_T(half)
    xy = load(f"bottom_tray_{half}").vertices[:, :2] @ T[:2, :2].T + T[:2, 3]
    ys = np.linspace(xy[:, 1].min(), xy[:, 1].max(), 30)
    left, right = [], []
    for i in range(len(ys) - 1):
        sel = xy[(xy[:, 1] >= ys[i]) & (xy[:, 1] < ys[i + 1])]
        if len(sel) == 0:
            continue
        ym = (ys[i] + ys[i + 1]) / 2
        left.append((sel[:, 0].min(), ym))
        right.append((sel[:, 0].max(), ym))
    ring = np.array(left + right[::-1], float)
    if grow > 0:
        cen = ring.mean(axis=0)
        d = ring - cen
        ring = ring + d / np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-6) * grow
    return ring

def compose_floor(scene_png, proj, ax_pos, fig_w_px, fig_h_px, out_path):
    """透明背景のシーン画像の下に、机面（グラデーション）＋接地影＋
    アンダーグローの光だまりを合成する。proj は ax.get_proj() の行列。"""
    def to_px(ring):
        x2, y2, _ = proj3d.proj_transform(ring[:, 0], ring[:, 1],
                                          np.zeros(len(ring)), proj)
        px = (ax_pos.x0 + x2 * ax_pos.width) * fig_w_px
        py = (1.0 - (ax_pos.y0 + y2 * ax_pos.height)) * fig_h_px
        return list(zip(px, py))

    # 机面: 縦グラデーション（上=明るいクリーム、下=少し濃い木色）
    top = np.array([248, 243, 231], float)
    bot = np.array([232, 214, 183], float)
    grad = np.linspace(0, 1, fig_h_px)[:, None, None]
    bg = (top[None, None, :] * (1 - grad) + bot[None, None, :] * grad)
    bg = np.repeat(bg, fig_w_px, axis=1).astype(np.uint8)
    img = Image.fromarray(bg, "RGB").convert("RGBA")

    layer = Image.new("RGBA", (fig_w_px, fig_h_px), (0, 0, 0, 0))
    dr = ImageDraw.Draw(layer)
    # 光だまり（シアン）: フットプリントを膨らませた輪を2段
    for half in ("short", "long"):
        dr.polygon(to_px(footprint_ring(half, grow=10.0)), fill=(64, 224, 205, 46))
        dr.polygon(to_px(footprint_ring(half, grow=4.0)), fill=(64, 224, 205, 40))
    # 接地影: フットプリントそのもの＋少し膨らませた輪
    for half in ("short", "long"):
        dr.polygon(to_px(footprint_ring(half, grow=2.5)), fill=(52, 42, 30, 66))
        dr.polygon(to_px(footprint_ring(half)), fill=(52, 42, 30, 58))
    layer = layer.filter(ImageFilter.GaussianBlur(7))
    img = Image.alpha_composite(img, layer)

    scene = Image.open(scene_png).convert("RGBA")
    img = Image.alpha_composite(img, scene)
    img.convert("RGB").save(out_path)

# ---------------------------------------------------------------- 本画
fig = plt.figure(figsize=(FIG_W, FIG_H))
fig.patch.set_alpha(0)
ax = fig.add_axes([0, 0, 1, 0.93], projection="3d")
ax.set_facecolor((0, 0, 0, 0))

for half in ("short", "long"):
    draw_half(ax, half)
draw_band_glow(ax)
flush_pending(ax)

# 軸範囲は物体中心±r の正方（既存ガイド図の流儀）に寄せる。
# 実寸アスペクトのまま広い範囲を取ると、matplotlib の投影で物体が
# フレームの隅に小さく寄ってしまうため。
ax.set_xlim(57 - 80.0, 57 + 80.0)
ax.set_ylim(0 - 155.0, 0 + 155.0)
ax.set_zlim(0, 116.0)
ax.set_box_aspect((80.0, 155.0, 58.0))
ax.view_init(elev=31, azim=-124)
ax.set_axis_off()
for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
    axis.pane.set_visible(False)
ax.grid(False)

fig.text(0.5, 0.972, "7sProMax ケース v2.4 ドッキング状態（案2・磁石なし）",
         ha="center", fontsize=15.5)
fig.text(0.5, 0.945, "階段が噛み合い継ぎ目 約0.3mm ／ 全体幅 301.14mm（本家 296.7）",
         ha="center", fontsize=12.5)

tmp = os.path.join(tempfile.gettempdir(), "dock_v24_scene.png")
plt.savefig(tmp, dpi=DPI, transparent=True)
proj = ax.get_proj()
ax_pos = ax.get_position()
plt.close()

compose_floor(tmp, proj, ax_pos, int(FIG_W * DPI), int(FIG_H * DPI),
              f"{DES}/guide_dock_v24_3d.png")
os.remove(tmp)

for nm in ("bottom_tray_short", "side_band_short", "switch_plate_short", "top_frame_short",
           "bottom_tray_long", "side_band_long", "switch_plate_long", "top_frame_long"):
    print(nm, sha256(f"{DES}/{nm}.stl")[:12])
print("saved guide_dock_v24_3d.png")

# ---------------------------------------------------------------- 上面図
# 実 STL のシルエット（check_dock と同じ抽出）で、図面レイアウト
# （dy=183.414、破線）とドッキング位置（dy=157.780、実線）を重ね、
# 右に継ぎ目の拡大（階段帯 x 20〜90、隙間つき）を描く。
import check_dock as cd

def _ring(poly, dy=0.0):
    xs, ys = poly.exterior.xy
    return np.array(xs), np.array(ys) + dy

ps = cd.silhouette("short")
pl = cd.silhouette("long")
D_STAR = 157.780
fig, axes = plt.subplots(1, 2, figsize=(16, 8.6),
                         gridspec_kw=dict(width_ratios=[1.55, 1.0]))
ax = axes[0]
xs, ys = _ring(pl); ax.plot(xs, ys, color="#30518f", lw=1.4)
xs, ys = _ring(ps, D_STAR); ax.plot(xs, ys, color="#b03a3a", lw=1.4)
xs, ys = _ring(ps, 183.414); ax.plot(xs, ys, color="#b03a3a", lw=0.9, ls=(0, (4, 3)), alpha=0.55)
xs, ys = _ring(pl); ax.fill(xs, ys, color="#30518f", alpha=0.07)
xs, ys = _ring(ps, D_STAR); ax.fill(xs, ys, color="#b03a3a", alpha=0.07)
ax.annotate("long", (57, 92), ha="center", fontsize=11, color="#30518f")
ax.annotate("short: docked dy=157.78", (57, 235), ha="center", fontsize=10, color="#b03a3a")
ax.annotate("short: drawing layout dy=183.414", (57, 268), ha="center", fontsize=9,
            color="#b03a3a", alpha=0.7)
ax.set_title("top view: docked (solid) vs drawing layout (dashed)\noverall span 301.14 mm (honke 296.7)", fontsize=12)
ax.set_aspect("equal"); ax.grid(alpha=0.25); ax.set_xlabel("x (depth)"); ax.set_ylabel("y (length)")

ax = axes[1]
xs, ys = _ring(pl); ax.plot(xs, ys, color="#30518f", lw=1.6)
xs, ys = _ring(ps, D_STAR); ax.plot(xs, ys, color="#b03a3a", lw=1.6)
ax.set_xlim(18, 92); ax.set_ylim(148, 186)
ax.set_title("seam zoom: main stair gap 0.30-0.41 mm\nback run 0.31-0.72 / front tooth 3.33 (pcb inherent)", fontsize=12)
ax.set_aspect("equal"); ax.grid(alpha=0.25); ax.set_xlabel("x"); ax.set_ylabel("y (global)")
fig.tight_layout()
fig.savefig(f"{DES}/guide_dock_v24_top.png", dpi=110)
print("saved guide_dock_v24_top.png")
