# -*- coding: utf-8 -*-
"""
7sProMax ケース v2.1 の組立一括・仮想検証（DESIGN_NOTES §17 の根拠データ）

build_case を import して組立座標のソリッドを得て、次を厳密ブーリアン等で測る:
  1. フレーム下降スイープ × 基板プリズム（干渉 0 の確認、short/long）
  2. 階段帯の基板→フレーム内壁の平坦クリアランス（z=8.0 断面サンプリング）
  3. パドルエンベロープ（配置B）× トレイ／バンド／フレーム:
     静止／押下-0.5／傾き±2.5°、バー単独×フレーム（スロット通過）
  4. パーツ間干渉（トレイ／バンド／フレーム／プレート／基板の全ペア）
     ＋ バンド着座スイープ（スカート→溝）
  5. ネジ経路（クリアランス円柱が他部材に触れないこと、タップ側の通り）
  6. 階段の左右間クリアランス（図面座標での外形同士・基板と相手側外形）
  7. スロット保持（上壁の材料存在）とプレートのスリバー再発確認
実行: ~/workspace/.venv-cad/bin/python check_v21.py （ビルド込みで数分かかる）
"""
import numpy as np
import trimesh
from shapely.geometry import Polygon, Point as SPoint
import build_case as bc

HALVES = ("short", "long")
PCB_BOT, PCB_TOP = bc.PCB_BOT, bc.PCB_BOT + 1.6

def load_part(half, key):
    """書き出し済み STL を読み、組立 z へ戻した trimesh を返す。
    STL は最小 z=0 に落としてある: tray 0 / band +1.9（スカート下端が組立 1.9）/
    frame +5.7 / plate short +7.35（ボス下端）・long +9.5。"""
    name = {"tray": f"bottom_tray_{half}", "band": f"side_band_{half}",
            "frame": f"top_frame_{half}", "plate": f"switch_plate_{half}"}[key]
    zo = {"tray": 0.0, "band": 1.9, "frame": 5.7,
          "plate": 7.35 if half == "short" else 9.5}[key]
    m = trimesh.load(f"{bc.OUTDIR}/{name}.stl")
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate(tuple(m.geometry.values()))
    m.apply_translation([0, 0, zo])
    return m

def pcb_mesh(half):
    H = bc.halves[half]
    m = trimesh.creation.extrude_polygon(H["pcb"], PCB_TOP - PCB_BOT)
    m.apply_translation([0, 0, PCB_BOT])
    return m

def ivol(a, b):
    try:
        return trimesh.boolean.intersection([a, b], engine="manifold").volume
    except Exception:
        return 0.0

def cyl_mesh(x, y, z0, z1, d, sections=40):
    m = trimesh.creation.cylinder(radius=d / 2, height=z1 - z0, sections=sections)
    m.apply_translation([x, y, (z0 + z1) / 2])
    return m

def boxm(x0, x1, y0, y1, z0, z1):
    return trimesh.creation.box(
        extents=[x1 - x0, y1 - y0, z1 - z0],
        transform=trimesh.transformations.translation_matrix(
            [(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2]))

def section_polys(mesh, z):
    """z 断面の閉ループポリゴン群（shapely）を返す。"""
    sec = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    out = []
    if sec is None:
        return out
    for ent in sec.entities:
        pts = np.asarray(sec.vertices)[ent.points]
        if len(pts) >= 4:
            p = Polygon(pts[:, :2])
            if not p.is_valid:
                p = p.buffer(0)   # テッセレーション由来の自己交差を修復
            if p.geom_type == "MultiPolygon":
                p = max(p.geoms, key=lambda g: g.area)
            if not p.is_empty and p.area > 0.01:
                out.append(p)
    return out

# ================= 1. フレーム下降スイープ =================
print("== 1. frame descent sweep vs pcb ==")
for half in HALVES:
    frame = load_part(half, "frame")
    pcb = pcb_mesh(half)
    row = []
    for h in (2.0, 1.0, 0.5, 0.25, 0.0):
        f2 = frame.copy(); f2.apply_translation([0, 0, -h])
        row.append(f"h={h}: {ivol(f2, pcb):.3f}")
    print(f"  {half}: " + "  ".join(row))

# ================= 2. 平面クリアランス =================
# フレーム下帯（z 5.7〜9.5）の内壁は cavity_full そのもの（設計データで測る。
# メッシュ断面は外周＋内周が1本の鎖に連結されて返るため使わない）
print("== 2. pcb -> frame lower-band inner wall (cavity_full) clearance ==")
for half in HALVES:
    H = bc.halves[half]
    pcb, cf = H["pcb"], H["cavity_full"]
    bnd = pcb.boundary
    vals = np.array([bnd.interpolate(s).distance(cf.boundary)
                     for s in np.arange(0, bnd.length, 0.25)])
    print(f"  {half}: min={vals.min():.3f} p1={np.percentile(vals,1):.3f} "
          f"median={np.median(vals):.3f} <0.3: {(vals<0.3).sum()}/{len(vals)}")

# ================= 3. パドル × パーツ =================
print("== 3. paddle (arrangement B) vs tray/band/frame ==")
def paddle_meshes(half, ci):
    # 配置Bエンベロープ（2026-11-05 実測で更新, §17.18）: 全長 25.2 /
    # ブロック長さ 8.2 / 高さ 8.6（z 1.0〜9.6）/ 羽根込み幅は安全側に
    # 旧推定 8.7 / バー厚 2.8（z 6.8〜9.6、上面は天板と面一）
    H = bc.halves[half]
    c = bc.TACT_CENTERS[half][ci]
    upper = boxm(101, 109.2, c - 4.35, c + 4.35, 7.8, 9.6)
    legL = boxm(101, 109.2, c - 4.35, c - 2.4, 1.0, 7.8)
    legR = boxm(101, 109.2, c + 2.4, c + 4.35, 1.0, 7.8)
    bar = boxm(109.2, 126.2, c - 2.4, c + 2.4, 6.8, 9.6)
    env = trimesh.boolean.union([upper, legL, legR, bar], engine="manifold")
    return env, bar

for half in HALVES:
    parts = {k: load_part(half, k) for k in ("tray", "band", "frame")}
    n = len(bc.TACT_CENTERS[half])
    for ci in range(n):
        env, baronly = paddle_meshes(half, ci)
        states = {"rest": env}
        e2 = env.copy(); e2.apply_translation([0, 0, -0.5]); states["press"] = e2
        if ci == n // 2:
            c = bc.TACT_CENTERS[half][ci]
            for name, ang in (("tilt+", 2.5), ("tilt-", -2.5)):
                e3 = env.copy()
                T = trimesh.transformations.translation_matrix([109.2, c, 8.2])
                R = trimesh.transformations.rotation_matrix(np.radians(ang), [0, 1, 0])
                Ti = trimesh.transformations.translation_matrix([-111, -c, -8.15])
                e3.apply_transform(T @ R @ Ti)
                states[name] = e3
        for sname, e in states.items():
            cells = " ".join(f"{pn}={ivol(e, parts[pn]):.2f}" for pn in ("tray", "band", "frame"))
            print(f"  {half} tact{ci+1} {sname}: {cells}")
        print(f"  {half} tact{ci+1} bar-only x frame: {ivol(baronly, parts['frame']):.3f}")

# ================= 4. パーツ間干渉 + バンド着座 =================
print("== 4. part-part interference (assembled) + band seating ==")
for half in HALVES:
    pm = {k: load_part(half, k) for k in ("tray", "band", "frame", "plate")}
    pm["pcb"] = pcb_mesh(half)
    keys = ["tray", "band", "frame", "plate", "pcb"]
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            print(f"  {half} {keys[i]} x {keys[j]}: {ivol(pm[keys[i]], pm[keys[j]]):.3f}")
    band0 = load_part(half, "band")
    for h in (1.0, 0.5, 0.0):
        b2 = band0.copy(); b2.apply_translation([0, 0, h])
        print(f"  {half} band raised +{h} vs tray: {ivol(b2, pm['tray']):.3f}")

# ================= 5. ネジ経路 =================
print("== 5. screw paths ==")
for half in HALVES:
    H = bc.halves[half]
    tray, band, frame, plate = (load_part(half, k) for k in ("tray", "band", "frame", "plate"))
    tb = trimesh.boolean.union([tray, band], engine="manifold")
    for e in H["back_screws"]:
        spec = bc.BACK_SCREW_SPECS[e["size"]]
        path = cyl_mesh(e["x"], e["y"], -0.5, PCB_BOT, spec["clr"])
        tap = cyl_mesh(e["x"], e["y"], PCB_BOT, PCB_BOT + spec["tap_depth"], spec["tap"])
        print(f"  {half} back ({e['x']:.2f},{e['y']:.1f}) {e['size']}: "
              f"clr-path x tray+band={ivol(path, tb):.3f}  tap-d x frame={ivol(tap, frame):.3f}  "
              f"(screw reach into frame = {12 - PCB_BOT:.1f} <= tap_depth {spec['tap_depth']})")
    for e in H["hangs"]:
        path = cyl_mesh(e["x"], e["y"], -0.5, PCB_TOP, 3.4)
        tap = cyl_mesh(e["x"], e["y"], bc.HANG_BOT, bc.HANG_BOT + bc.HANG_TAP_DEPTH,
                       bc.HANG_TAP_DIA)
        print(f"  {half} hang ({e['x']:.2f},{e['y']:.1f}): "
              f"clr-path x tray+band={ivol(path, tb):.3f}  tap-d x plate={ivol(tap, plate):.3f}")

# ================= 6. 左右間クリアランス =================
print("== 6. inter-half clearance (drawing coords) ==")
# 図面レイアウト原点（build_case.ORIGIN と同じ: 両半分とも背面が揃い
# 相対 x オフセット 0、short は dy=183.414）。
# v2.2 までの記録で使ったスキャン fit 用原点（long +25.382 / short
# +36.934、相対 +11.552 の x ずれ）は原点混用で、左右間最接近を
# 11.74mm と誤らせた（正しくは 15.59mm、§17.11 訂正済み）。
ORIGIN = bc.ORIGIN
def shifted(poly, half):
    ox, oy = ORIGIN[half]
    return Polygon([(x + ox, y + oy) for x, y in poly.exterior.coords])
out_s = shifted(bc.halves["short"]["outline"], "short")
out_l = shifted(bc.halves["long"]["outline"], "long")
pcb_s = shifted(bc.halves["short"]["pcb"], "short")
pcb_l = shifted(bc.halves["long"]["pcb"], "long")
print(f"  outline <-> outline       : {out_s.distance(out_l):.2f}")
print(f"  short pcb <-> long outline: {pcb_s.distance(out_l):.2f}")
print(f"  long pcb <-> short outline: {pcb_l.distance(out_s):.2f}")
print(f"  pcb <-> pcb               : {pcb_s.distance(pcb_l):.2f}")

# ================= 7. スロット保持 + プレートスリバー =================
print("== 7. slot upper wall / plate sliver ==")
for half in HALVES:
    H = bc.halves[half]
    frame_m = load_part(half, "frame")
    xmax = H["outline"].bounds[2]
    for i, c in enumerate(bc.TACT_CENTERS[half]):
        wall = boxm(bc.PADDLE_SLOT_X0, xmax, c - bc.PADDLE_SLOT_HW, c + bc.PADDLE_SLOT_HW,
                    bc.PADDLE_SLOT_Z1, bc.PADDLE_SLOT_Z1 + 0.9)
        print(f"  {half} tact{i+1} upper-wall vol: {ivol(wall, frame_m):.2f}")
    plate_m = load_part(half, "plate")
    polys = section_polys(plate_m, bc.PLATE_BOT + 0.75)
    outer = max(polys, key=lambda p: p.area)
    mind = 1e9
    for p in polys:
        if p is outer:
            continue
        d = outer.exterior.distance(p.exterior)
        if d > 0.01:
            mind = min(mind, d)
    print(f"  {half} plate: min positive hole->outline distance = "
          f"{mind if mind < 1e8 else float('nan'):.2f} (notched holes are 0/merged)")

# ================= 8. 階段壁厚キャップの検証（v2.3、§17.12） =================
# 階段帯の壁（外形 − キャビティ）内の格子点について、外形境界までの
# 距離（＝侵食の意味での壁厚）の最大を測る。キャップにより STAIR_WALL
# 以下になるはず。フレーム下帯用 cavity_full とバンドレッジ帯用
# cavity の両方を見る。あわせて階段帯ソケット円盤の保険（中心から
# キャビティ面まで STAIR_DISK_R 以上）も確認する。
print("== 8. stair wall thickness in strip (cap check) + socket disks ==")
for half in HALVES:
    H = bc.halves[half]
    outline = H["outline"]
    strip = bc.stair_strip(H["chain"], outline)
    xs = np.arange(outline.bounds[0], outline.bounds[2], 0.25)
    ys = np.arange(outline.bounds[1], outline.bounds[3], 0.25)
    for label, cav in (("cavity_full", H["cavity_full"]),
                       ("cavity", H["cavity"])):
        wall = outline.difference(cav).intersection(strip)
        if wall.is_empty:
            print(f"  {half} {label}: no wall in strip")
            continue
        vals = []
        for x in xs:
            for y in ys:
                p = SPoint(x, y)
                if wall.covers(p):
                    vals.append(outline.boundary.distance(p))
        vals = np.array(vals)
        print(f"  {half} {label}: wall pts={len(vals)} "
              f"max={vals.max():.3f} p99={np.percentile(vals, 99):.3f} "
              f"(cap {bc.STAIR_WALL})")
    cf = H["cavity_full"]
    dsk = [SPoint(cx, cy).distance(cf.boundary)
           for (cx, cy) in bc.stair_disks(half)]
    print(f"  {half} stair socket disks: min center->cavity_full = "
          f"{min(dsk):.3f} (need >= {bc.STAIR_DISK_R})")
    # ネジ保持円盤の中は意図的に壁を残すので、キャップ検証からは除外
    from shapely.ops import unary_union as _uu
    keeps = [SPoint(e["x"], e["y"]).buffer(
                 bc.BACK_SCREW_SPECS[e["size"]]["tap"] / 2
                 + bc.CAP_SCREW_KEEP + 0.3)
             for e in H["back_screws"]]
    keeps += [SPoint(e["x"], e["y"]).buffer(
                  bc.HANG_TAP_DIA / 2 + bc.CAP_SCREW_KEEP + 0.3)
              for e in H["hangs"]]
    wall2 = outline.difference(cf).intersection(strip)
    if keeps:
        wall2 = wall2.difference(_uu(keeps))
    vals = []
    for x in xs:
        for y in ys:
            p = SPoint(x, y)
            if wall2.covers(p):
                vals.append(outline.boundary.distance(p))
    vals = np.array(vals)
    print(f"  {half} cap check excl. screw keeps: wall pts={len(vals)} "
          f"max={vals.max():.3f} p99={np.percentile(vals, 99):.3f} "
          f"(cap {bc.STAIR_WALL})")
print("CHECK DONE")
