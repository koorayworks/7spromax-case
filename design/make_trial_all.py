#!/usr/bin/env python3
"""試作ピース一式を 180x180 ベッド内に再レイアウトした統合 STL を
作り直す。

構成（v2.4.12／§17.26）: 全 14 ピースを 2 ファイルに分割する。
  - trial_all_1.stl: short 系 4 ピース＋プランジャ 3 個（計 7）
  - trial_all_2.stl: long 系 4 ピース＋プランジャ 3 個（計 7）
各系の内訳は、階段バンド 1＋背面帯ピース（トレイ／バンド／
フレーム）3。背面帯は、旧 corner クリップと TRRS クリップを
やめて、奥辺に沿ってタクトの角から TRRS 帯まで一続きにした
もの（本人の指示「つなげたやつじゃないとわからん」）。
バンドだけは背面壁が断片的なため幅いっぱいの切り出し。

番号（ガイド図と一致させる）:
  1=階段バンド(short) 2=帯トレイ(short) 3=帯バンド(short)
  4=帯フレーム(short) 5=階段バンド(long) 6=帯トレイ(long)
  7=帯バンド(long) 8=帯フレーム(long)。プランジャは無印。
v2.4.12 では全ピースに番号を浮き彫りで入れたが、v2.4.13
（§17.27）で 1・3・5・7（階段バンドと背面帯バンド）の
浮き彫りを撤回した。当てるときに 180 度回すと数字の
出っ張りが当て面に来て邪魔になる、との本人報告による。
この 4 ピースは無地で、ガイド図の並びと形で見分ける。
残りの浮き彫りは面を検証してから残す。フレーム（4・8）は
外側端面（当て面でもベッド面でもない）にあることを検証
した。トレイは床上面（基板裏面との間に隙間が残る面）で
ソケット包絡を避けた位置を探したが、long（6）は置けた
一方、short（2）は帯の床がソケット包絡で埋まり、数字の
天面（z=3.0）がソケット下面（z=2.7 仮定）に届く置き場が
無かったため外した（§17.27）。

サポートなし印刷のための向き（§17.26）:
  - 帯フレームは天地を逆にして並べる（天面をベッド側に付け、
    キャビティを上向きのポケットにする）。番号は反転後に
    正しく読める向きで彫る。
  - 他のピースは従来どおり底面を下にする。

配置は MaxRects（空き矩形のベストフィット分割）で、ピース間隔
3mm 以上・ベッド内・z=0 着座・watertight を検証してから書き出す。
"""
import numpy as np
import trimesh
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union

BASE = "/home/hatch/workspace/7spromax-case/design"
BED = 180.0
# 予約間隔は公称 3.0 に浮動小数点・ハル計算の余裕 0.05 を足した値に
# する（検証は実測で 3.0 以上を要求）。
GAP = 3.05

# (ピース名, 番号, 表示名, フレーム反転するか)
GROUPS = {
    # v2.4.14 (§17.28): 本人指示で試作はフレームのタクト角だけに
    # 絞る。各ファイル = 角フレーム 1 + プランジャ 3。
    "trial_all_1": ([("trial_tact_frame_short", 4, "タクト角フレーム（左）", True)], 3),
    "trial_all_2": ([("trial_tact_frame_long", 8, "タクト角フレーム（右）", True)], 3),
}
TRRS_Y = {"short": 67.2, "long": 80.3}

# v2.4.13 (§17.27): 浮き彫りを入れない番号（バンド類。
# 180 度回して当てると数字の出っ張りが邪魔になるため）
NO_DIGIT_NUMBERS = {1, 3, 5, 7}


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


# ---------------- 番号の浮き彫り ----------------

def digit_polygons(text, height):
    """数字の shapely ポリゴン（高さ height にスケール、中心原点）。"""
    from matplotlib.textpath import TextPath
    from matplotlib.font_manager import FontProperties
    tp = TextPath((0, 0), text,
                  prop=FontProperties(family="DejaVu Sans", weight="bold"),
                  size=1.0)
    polys = []
    for v in tp.to_polygons():
        if len(v) < 3:
            continue
        p = Polygon(v)
        if p.is_valid and p.area > 1e-6:
            polys.append(p)
    # 入れ子（穴）を差し引く
    result = []
    for p in sorted(polys, key=lambda q: -q.area):
        for i, q in enumerate(result):
            if q.contains(p):
                result[i] = q.difference(p)
                break
        else:
            result.append(p)
    u = unary_union(result)
    minx, miny, maxx, maxy = u.bounds
    s = height / (maxy - miny)
    from shapely.affinity import scale as shp_scale, translate as shp_tr
    u = shp_scale(u, xfact=s, yfact=s, origin=(0, 0))
    minx, miny, maxx, maxy = u.bounds
    u = shp_tr(u, xoff=-(minx + maxx) / 2, yoff=-(miny + maxy) / 2)
    if isinstance(u, Polygon):
        u = MultiPolygon([u])
    return u


def digit_mesh(text, height, depth=0.6):
    """数字のソリッド。ローカル座標: u=x, v=y,  extrude +z (0..depth)。"""
    parts = []
    for p in digit_polygons(text, height).geoms:
        parts.append(trimesh.creation.extrude_polygon(p, depth))
    m = trimesh.util.concatenate(parts)
    return m


def emboss(mesh, text, height, origin, u, v, n, depth=0.6, embed=0.1):
    """origin（面上の中心）から u/v 方向に数字を置き、n 方向へ
    depth 浮き出させる（根元 embed だけ埋め込む）。"""
    d = digit_mesh(text, height, depth)
    M = np.eye(4)
    M[:3, 0] = u
    M[:3, 1] = v
    M[:3, 2] = n
    M[:3, 3] = np.asarray(origin, float) - embed * np.asarray(n, float)
    d.apply_transform(M)
    out = trimesh.boolean.union([mesh, d], engine="manifold")
    if isinstance(out, trimesh.Scene):
        out = trimesh.util.concatenate(tuple(out.geometry.values()))
    dv = d.volume * (depth - embed) / depth
    gain = out.volume - mesh.volume
    solids = out.split(only_watertight=False)
    ok = (out.is_watertight and len(solids) == 1
          and 0.3 * dv < gain < 1.1 * dv)
    print(f"    emboss '{text}' h={height}: gain={gain:.1f} "
          f"(expect ~{dv:.1f}) solids={len(solids)} -> {'OK' if ok else 'NG'}")
    return out, ok


def top_z(mesh, pts):
    """各 (x, y) の上面 z（ヒットしなければ nan）。"""
    origins = np.column_stack([pts[:, 0], pts[:, 1],
                               np.full(len(pts), 200.0)])
    dirs = np.tile([0.0, 0.0, -1.0], (len(pts), 1))
    locs, idx, _ = mesh.ray.intersects_location(
        origins, dirs, multiple_hits=False)
    out = np.full(len(pts), np.nan)
    if len(idx):
        zz = {}
        for L, i in zip(locs, idx):
            zz.setdefault(i, []).append(L[2])
        for i, v in zz.items():
            out[i] = max(v)
    return out


def try_top_digit(mesh, text, z_target, tol=0.05, height=4.0,
                  preferred=None):
    """上面の平らな場所を探して数字を置く。成功したら mesh を返す。"""
    polys = digit_polygons(text, height)
    offs = []
    for p in polys.geoms:
        offs.extend(np.asarray(p.exterior.coords))
        offs.append(np.asarray(p.centroid.coords)[0])
    offs = np.array(offs)
    hw = max(abs(offs[:, 0].max()), abs(offs[:, 0].min())) + 1.2
    hh = max(abs(offs[:, 1].max()), abs(offs[:, 1].min())) + 1.2
    b = mesh.bounds
    cand = []
    xs = np.arange(b[0, 0] + hw, b[1, 0] - hw + 1e-9, 2.0)
    ys = np.arange(b[0, 1] + hh, b[1, 1] - hh + 1e-9, 2.0)
    for cx in xs:
        for cy in ys:
            d = 0.0 if preferred is None else \
                (cx - preferred[0]) ** 2 + (cy - preferred[1]) ** 2
            cand.append((d, cx, cy))
    cand.sort()
    for _, cx, cy in cand:
        pts = offs + np.array([cx, cy])
        tz = top_z(mesh, pts)
        if np.isnan(tz).any():
            continue
        if abs(tz - z_target).max() <= tol:
            out, ok = emboss(mesh, text, height, (cx, cy, z_target),
                             (-0.0, -1.0, 0.0), (1.0, 0.0, 0.0),
                             (0.0, 0.0, 1.0))
            if ok:
                return out
    return None


def try_face_digit(mesh, text, axis, side, v_center, height,
                   basis_override=None):
    """垂直面（axis 方向の bbox 端面）に数字を置く。
    axis: 0=x, 1=y。side: 0=min 側, 1=max 側。"""
    b = mesh.bounds
    plane = b[side, axis]
    n = np.zeros(3)
    n[axis] = 1.0 if side == 1 else -1.0
    other = 1 - axis
    # 面に沿って材料の連続区間を探す（v_center の高さで内側 0.3）
    scan = np.arange(b[0, other] + 0.5, b[1, other] - 0.4, 0.5)
    pts = np.zeros((len(scan), 3))
    pts[:, axis] = plane - n[axis] * 0.3
    pts[:, other] = scan
    pts[:, 2] = v_center
    ins = mesh.contains(pts)
    # 連続 run
    runs, s0 = [], None
    for i, v in enumerate(ins):
        if v and s0 is None:
            s0 = i
        if (not v or i == len(ins) - 1) and s0 is not None:
            e0 = i - 1 if not v else i
            runs.append((scan[s0], scan[e0]))
            s0 = None
    polys = digit_polygons(text, height)
    dw = polys.bounds[2] - polys.bounds[0]
    runs = [r for r in runs if r[1] - r[0] >= dw + 1.5]
    if not runs:
        return None
    runs.sort(key=lambda r: -(r[1] - r[0]))
    center_along = (runs[0][0] + runs[0][1]) / 2
    # 面の平らさ検証: 数字の範囲で内側 0.3 が材料、外側 0.12 が空
    offs = []
    for p in polys.geoms:
        offs.extend(np.asarray(p.exterior.coords))
    offs = np.array(offs)
    if basis_override is not None:
        u, v = basis_override
    else:
        u = np.cross(-n, np.array([0.0, 0.0, 1.0]))
        v = np.array([0.0, 0.0, 1.0])
    origin = np.zeros(3)
    origin[axis] = plane
    origin[other] = center_along
    origin[2] = v_center
    pts3 = origin + offs[:, 0:1] * u + offs[:, 1:2] * v
    f_in = mesh.contains(pts3 - 0.3 * n).mean()
    f_out = (~mesh.contains(pts3 + 0.12 * n)).mean()
    print(f"    face digit check: inside={f_in:.2f} outside={f_out:.2f}")
    if f_in < 0.95 or f_out < 0.8:
        return None
    out, ok = emboss(mesh, text, height, origin, u, v, n)
    return out if ok else None


def rotate_band_180(mesh):
    """バンド類を平面内で 180° 回す（v2.4.14 §17.28 の恒常ルール:
    本人がスライサーで毎回回している向きに合わせる）。z は変えない。"""
    b = mesh.bounds
    cx, cy = (b[0, 0] + b[1, 0]) / 2, (b[0, 1] + b[1, 1]) / 2
    m = mesh.copy()
    m.apply_translation([-cx, -cy, 0])
    m.apply_transform(trimesh.transformations.rotation_matrix(
        np.pi, [0, 0, 1]))
    m.apply_translation([cx, cy, 0])
    m.apply_translation([0, 0, -m.bounds[0, 2]])
    return m


def lay_plunger_side(mesh):
    """プランジャを 90° 横倒しにする（v2.4.14 §17.28 の恒常ルール）。
    下にする面は、背面クリップでできた平らな面（D 字の平面、
    キャップとフランジの背面側）。印刷座標 +x がその平面の
    法線なので、y 軸 +90° 回転で +x を下 (-z) に向ける。
    軸は水平 (x 方向) になり、丸い側が上になる。"""
    m = mesh.copy()
    m.apply_transform(trimesh.transformations.rotation_matrix(
        np.pi / 2, [0, 1, 0]))
    m.apply_translation([0, 0, -m.bounds[0, 2]])
    return m


def flip_frame(mesh):
    """帯フレームを天地逆にする（x 軸まわり 180°、bbox 中心）。"""
    b = mesh.bounds
    cy, cz = (b[0, 1] + b[1, 1]) / 2, (b[0, 2] + b[1, 2]) / 2
    m = mesh.copy()
    m.apply_translation([0, -cy, -cz])
    m.apply_transform(trimesh.transformations.rotation_matrix(
        np.pi, [1, 0, 0]))
    m.apply_translation([0, cy, cz])
    m.apply_translation([0, 0, -m.bounds[0, 2]])
    return m


# ---------------- 残す数字の面チェック（v2.4.13） ----------------

import csv as _csv
from shapely.geometry import box as _shp_box

SOCKET_CSV = "/home/hatch/workspace/7spromax-case/template/pcb_sockets.csv"
SOCK_Z0 = 2.7   # ソケット下面（基板裏面 5.7 − 張り出し 3.0 仮定、§17.23）


def socket_squares(half):
    """ソケット位置の 14mm 角プロキシ（§17.23 で使う最も
    保守的な包絡。check_socket_ledge.load_sockets と同じ読み）。"""
    out = []
    for row in _csv.DictReader(open(SOCKET_CSV)):
        if row["half"] != half or row["kind"] not in ("square", "tall"):
            continue
        if row["method"] == "dome_centroid" and row["meas_x_mm"]:
            x, y = float(row["meas_x_mm"]), float(row["meas_y_mm"])
        else:
            x, y = float(row["dxf_x_mm"]), float(row["dxf_y_mm"])
        out.append(_shp_box(x - 7.0, y - 7.0, x + 7.0, y + 7.0))
    return out


def digit_solid(orig, embossed):
    """浮き彫りで増えた分だけのソリッド（manifold 差分）。"""
    d = trimesh.boolean.difference([embossed, orig], engine="manifold")
    if isinstance(d, trimesh.Scene):
        d = trimesh.util.concatenate(tuple(d.geometry.values()))
    return d


def digit_hits_socket(diff, half, margin=0.3):
    """数字の xy 範囲（margin 拡大）がソケット包絡に触れるか。
    数字の天面 z=3.0 はソケット下面 z=2.7 より上なので、
    xy で重なれば実干渉になる。"""
    if diff is None or len(diff.faces) == 0:
        return True
    b = diff.bounds
    rect = _shp_box(b[0, 0] - margin, b[0, 1] - margin,
                    b[1, 0] + margin, b[1, 1] + margin)
    return any(rect.intersects(s) for s in socket_squares(half))


def _flip_rigid(mesh, ref_bounds):
    """flip_frame と同じ剛体変換だけを行う（z 再着座なし）。
    ref_bounds は変換中心を決める基準メッシュの bounds。"""
    cy = (ref_bounds[0, 1] + ref_bounds[1, 1]) / 2
    cz = (ref_bounds[0, 2] + ref_bounds[1, 2]) / 2
    m = mesh.copy()
    m.apply_translation([0, -cy, -cz])
    m.apply_transform(trimesh.transformations.rotation_matrix(
        np.pi, [1, 0, 0]))
    m.apply_translation([0, cy, cz])
    return m


def emboss_piece(name, mesh, number):
    """ピース種別ごとの方針で番号を入れる。
    トレイはソケットを避けられる置き場が無ければ None を返す。"""
    text = str(number)
    half = "short" if name.endswith("_short") else "long"
    if "tray" in name:
        # 床上面（z=2.5）に置く。既定位置がソケット包絡に
        # 触れる場合は候補点を変えて置き直す（v2.4.13）。
        prefs = [(95.0, TRRS_Y[half] + 30.0)]
        b = mesh.bounds
        for px in np.arange(b[0, 0] + 9, b[1, 0] - 8, 11.0):
            for py in np.arange(b[0, 1] + 9, b[1, 1] - 8, 11.0):
                prefs.append((float(px), float(py)))
        rejected = []
        tried = 0
        for pref in prefs:
            if tried >= 15:
                break
            out = try_top_digit(mesh, text, 2.5, preferred=pref)
            if out is None:
                continue
            tried += 1
            d = digit_solid(mesh, out)
            db = d.bounds
            key = tuple(np.round(db[:, :2].ravel(), 1))
            if key in rejected:
                continue
            print(f"    tray digit bbox x[{db[0,0]:.1f},{db[1,0]:.1f}] "
                  f"y[{db[0,1]:.1f},{db[1,1]:.1f}] "
                  f"z[{db[0,2]:.2f},{db[1,2]:.2f}] (socket bottom "
                  f"z={SOCK_Z0})")
            if not digit_hits_socket(d, half):
                print("    tray digit: clear of socket envelopes")
                return out
            rejected.append(key)
            print("    tray digit overlaps a socket envelope; retry")
        print(f"    tray digit: no socket-clear spot for {name}")
        return None
    if "band" in name:
        out = try_top_digit(mesh, text, 3.8)
        if out is not None:
            return out
        # 端面（外側の端壁）に 3.2mm で入れる
        if "stair" in name:
            side = 0 if half == "short" else 1
        else:
            side = 1 if half == "short" else 0
        out = try_face_digit(mesh, text, axis=1, side=side,
                             v_center=1.9, height=3.2)
        assert out is not None, f"{name}: band digit placement failed"
        return out
    if "frame" in name:
        # 端面に、反転後正しく読める向き（v=-z、u は反転後の
        # 視点の右方向を逆算）で彫ってから反転する
        side = 1 if half == "short" else 0
        u_pre = np.array([1.0, 0.0, 0.0]) if half == "short" \
            else np.array([-1.0, 0.0, 0.0])
        out = try_face_digit(
            mesh, text, axis=1, side=side, v_center=5.2, height=4.0,
            basis_override=(u_pre, np.array([0.0, 0.0, -1.0])))
        assert out is not None, f"{name}: frame digit placement failed"
        # v2.4.13: 数字が外側端面（y 端の垂直面）にあり、反転後も
        # ベッド面（z=0）に来ないことを、増分ソリッドで検証する
        d = digit_solid(mesh, out)
        db, b = d.bounds, mesh.bounds
        pro_hi = db[1, 1] - b[1, 1]   # +y 側への出っ張り
        pro_lo = b[0, 1] - db[0, 1]   # -y 側への出っ張り
        on_end = (0.25 <= pro_hi <= 0.7) != (0.25 <= pro_lo <= 0.7)
        z_in = db[0, 2] > b[0, 2] + 1.0 and db[1, 2] < b[1, 2] - 1.0
        fd = _flip_rigid(d, out.bounds)
        fo = _flip_rigid(out, out.bounds)
        fz = fd.bounds[0, 2] - fo.bounds[0, 2]   # 反転後の数字の下端 z
        fb = flip_frame(out).bounds
        fdb = fd.bounds
        end_after = min(abs(fdb[0, 1] - fb[0, 1]),
                        abs(fdb[1, 1] - fb[1, 1])) <= 0.75
        print(f"    frame digit: protrude +y={pro_hi:.2f} -y={pro_lo:.2f} "
              f"z[{db[0,2]:.1f},{db[1,2]:.1f}] on_end={on_end} "
              f"z_inside={z_in} flipped_zmin={fz:.2f} "
              f"end_after_flip={end_after}")
        assert on_end and z_in and fz > 0.5 and end_after, \
            f"{name}: frame digit face check failed"
        return flip_frame(out)
    raise ValueError(name)


# ---------------- パッキング（従来どおり MaxRects） ----------------

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
                if rot and "band" in label:
                    # バンド類は 180° 回転済みの向きを保つ
                    # （§17.28 の恒常ルール）。pack の 90° 回転はしない。
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


LABELS = {}   # label -> (番号 or None, 表示名, 下にする面の説明)
DIGIT_DROPPED = []   # 置き場が無くて浮き彫りを外したピース（v2.4.13）


def main():
    plungers = load_solids(f"{BASE}/plunger.stl")
    assert len(plungers) == 1, f"plunger.stl solids: {len(plungers)}"
    all_placed = {}
    for out_name, (specs, n_plunger) in GROUPS.items():
        pieces = []
        for name, number, disp, is_frame in specs:
            solids = load_solids(f"{BASE}/{name}.stl")
            assert len(solids) == 1, f"{name}: solids={len(solids)}"
            print(f"== {name} (#{number}) ==")
            if number in NO_DIGIT_NUMBERS:
                m = solids[0]
                print("   digit: none (v2.4.13 plain)")
            else:
                m = emboss_piece(name, solids[0], number)
                if m is None:
                    m = solids[0]
                    DIGIT_DROPPED.append(name)
                    print(f"   digit: DROPPED for {name} "
                          "(no socket-clear flat spot)")
            if "band" in name:
                m = rotate_band_180(m)
                print("   orientation: band rotated 180 deg (§17.28 rule)")
            label = f"{name}#0"
            LABELS[label] = (number, disp,
                             "天面を下に（逆さ）" if is_frame else "底面を下に")
            pieces.append((label, m))
        for i in range(n_plunger):
            label = f"plunger#{i}"
            LABELS[label] = (None, "小ボタン",
                             "横倒し（平らな背面を下に）")
            pieces.append((label, lay_plunger_side(plungers[0])))
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
    # ガイド図: 2 ファイル分の配置を並べて描く（番号を大きく）
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    for f in ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
              "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"):
        try:
            matplotlib.font_manager.fontManager.addfont(f)
        except Exception:
            pass
    plt.rcParams["font.family"] = "Noto Sans CJK JP"
    fig, axes = plt.subplots(1, 2, figsize=(15, 8.2))
    for ax, (out_name, placed) in zip(axes, all_placed.items()):
        plunger_pts = []
        for label, m, fp in placed:
            xs, ys = np.array(fp.exterior.coords).T
            ax.plot(xs, ys, lw=1.1)
            number, disp, bottom = LABELS[label]
            rp = fp.representative_point()
            if number is not None:
                ax.text(rp.x, rp.y + 7, str(number), ha="center",
                        va="center", fontsize=30, fontweight="bold",
                        color="#C0272D")
                ax.text(rp.x, rp.y - 6, disp, ha="center", va="center",
                        fontsize=10.5)
                ax.text(rp.x, rp.y - 13, bottom, ha="center", va="center",
                        fontsize=8.5, color="#245A9E")
            else:
                plunger_pts.append((rp.x, rp.y))
        if plunger_pts:
            px = sum(p[0] for p in plunger_pts) / len(plunger_pts)
            py = sum(p[1] for p in plunger_pts) / len(plunger_pts)
            ax.annotate(f"小ボタン ×{len(plunger_pts)}", xy=(px, py),
                        xytext=(px + 26, py - 16), fontsize=10.5,
                        ha="center", va="center",
                        arrowprops=dict(arrowstyle="->", lw=1.4,
                                        color="#333333"))
        ax.set_xlim(0, BED)
        ax.set_ylim(0, BED)
        ax.set_aspect("equal")
        ax.grid(alpha=0.25)
        ax.set_title(f"{out_name}.stl ({len(placed)} ピース)")
    fig.suptitle("試作ピースの並び方 v2.4.14"
                 "（タクト角フレームだけ。4・8 はピースに番号あり）",
                 fontsize=14)
    fig.text(0.5, 0.008,
             "今回の試作はフレームのタクト角まわりだけです。"
             "角フレーム（4・8）は天面を下に、小ボタンは横倒し"
             "（平らな背面を下に）で印刷します。\n"
             "当て方: バンドを先に基板へ正しく座らせ、その上から"
             "角フレームをかぶせて、タクトと穴の合いを見てください。\n"
             "小ボタンは、フレームをかぶせた後からでも、後ろ側の差し込み口へ"
             "横に差し込めます（平らに切れた面を後ろに向ける）。",
             ha="center", fontsize=10.5)
    fig.tight_layout(rect=(0, 0.09, 1, 0.96))
    fig.savefig(f"{BASE}/guide_trial_all_v22.png", dpi=110)
    print("saved guide_trial_all_v22.png")
    print(f"DIGIT_DROPPED: {DIGIT_DROPPED}")


if __name__ == "__main__":
    main()
