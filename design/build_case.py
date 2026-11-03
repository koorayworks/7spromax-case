# -*- coding: utf-8 -*-
"""
7sProMax 3Dプリントケース 立体設計 v1（試作ラウンド用）

構成（本人の確定仕様）:
  - トップケース＝枠（ベゼル）のみ。スイッチプレートは別体の平板として印刷し、
    トップケース内側の段（リップ）で上から押さえ、スイッチのフランジで下から受ける
    「溝なし挟み込み」方式（プレート単体STLを別途出力）。
  - ボトムケース＝本家のアクリル積層（基板周囲のスペーサー層）に相当する壁＋床。
    白FR4ボトムプレート（厚1.2）は床の浅い凹みに収める（底側の層として再利用）。
  - 有線のみ／フラット／連結スロット無し。ただし背面縁のパドル用ポケット
    （図面外形に元々ある3か所/半分の凹み）は残す。
  - ネジはインサートなし。FR4プレートの実測穴（大=M3・小=M2）に合わせ、
    下から通してトップフレーム側ボスへタッピングする本家同様のサンドイッチ締結。
    キット実績: M3x8 x6, M2x12 x9, M2x7 x4（穴数 大6/小13 と一致）。

座標系: DXFテンプレートの半分ローカル座標をそのまま使う。
  X = 奥行方向（0..114.29, x=114側が背面＝マイコン/パドル側）
  Y = 長さ方向（short: y=0が階段（中央）側, y=143.36が外側端
               long : y=0が外側端, y=177.23が階段（中央）側）
  Z = ケース底面を 0 とする高さ。

入力:
  ../work_design/dxf_polys.json  （template DXFの抽出ポリゴン: OUTLINE/POCKET/SWITCH_HOLES）
  ../template/pcb_outline_short.csv / pcb_outline_long.csv （基板外形実測, DXFローカル座標）
  ../template/pcb_sockets.csv    （スイッチ中心, 参考）
  ../template/plate_holes_v2.csv （FR4プレート穴, プレート単体ローカル座標）

未確定（パラメータ化して試作片で当てる）:
  - PLATE_TF: FR4プレート単体座標→ケース座標の変換。共通基準点が写真に無いため
    「プレート外形を基板外形に概ね一致」からの推定値。ボス試作片で実物確認して補正する。
  - 階段境界: 基板輪郭CSVの階段部は信頼性が低い（PCB_NOTES参照）。
    ケース側は図面外形（信頼できる）を WALL 一定で内側オフセットした形状とし、
    クリアランスは STAIR_CLR で一括調整できるようにした（現状は壁一律）。
  - USB開口位置（外側端の壁, マイコン角）: 基板写真からの推定。実装後の実測推奨。
  - TRRS開口位置（背面壁, 外側端から TRRS_OFFSET）: 写真からの推定 ±10mm級。
"""

import json, csv, math, sys
import numpy as np
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
import build123d as bd

BASE = "/home/hatch/workspace/7spromax-case"
OUTDIR = f"{BASE}/design"

# ============================= パラメータ =============================
# --- Z 積み上げ（ケース底面 z=0）根拠は DESIGN_NOTES 参照 ---
FLOOR_T        = 2.6    # ボトムケース床の厚み（床上面 z）
FR4_RECESS_Z   = 1.3    # FR4収納凹みの底（FR4は 1.3..2.5。凹み下に 1.3 残し、
                        # 裏から入れるネジ頭（低頭 約1.2）の座グリ深さを確保する）
FR4_T          = 1.2    # FR4プレート厚（実測）
GAP_FR4_PCB    = 3.2    # FR4上面→基板裏面（実測 約3〜3.5 = 本家アクリル積層相当）
PCB_T          = 1.6    # 基板厚（実測）
PCB_BOT        = FR4_RECESS_Z + FR4_T + GAP_FR4_PCB   # 5.7
PCB_TOP        = PCB_BOT + PCB_T                      # 7.3
FRAME_TOP      = 16.1   # ケース総高（本家側面図の 16.1 と一致させた）
PLATE_T        = 1.5    # 別体スイッチプレートの厚み
PLATE_BOT      = PCB_TOP + 2.2   # 9.5（ソケット上面 +2.0 の上に 0.2 逃げ）
PLATE_TOP      = PLATE_BOT + PLATE_T                  # 11.0

# --- 平面クリアランス・壁 ---
WALL           = 2.6    # 外形→内腔の壁厚（基板は外形から約3〜3.9内側が実測中央値）
FR4_INSET      = 0.8    # FR4凹みの外形からの inset（FR4外形 141.1x103.1 がほぼ全面）
LEDGE_INSET    = 5.2    # 基板支持レッジの内側境界（外形から）: PCB端（約-3.5）を下から受ける
PLATE_UNDERLAP = 3.0    # プレート外周がポケット開口より外へ出る量（リップに隠れる分）
PLATE_CLR      = 0.25   # プレート外周とフレーム内壁の隙間
POCKET_CLR     = 0.25   # フレーム天面開口（ポケット）への追加クリアランス
STAIR_CLR      = 0.0    # 階段部の追加クリアランス（試作結果で調整するパラメータ）

# --- パドル（エクストラスイッチ）まわり ---
PADDLE_NOTCH_Z0 = PLATE_BOT + 0.1   # フレーム背面壁のパドル通しノッチ下端 z（これより上をポケット幅で開ける）
TACT_WIN_X0     = 98.0  # ボトム側タクト逃げ窓の x 開始（背面側）: 基板裏面タクトのボタン逃げ
TACT_WIN_MARGIN = 3.5   # 窓の y 方向マージン（ポケット範囲に対して）

# --- 開口（推定位置・要実物確認） ---
USB_XC   = 97.0         # USB開口中心 x（マイコン帯域 85..110 の中央付近）
USB_W    = 10.0         # USB開口幅（x方向）
USB_Z0, USB_Z1 = PCB_TOP + 3.0, PCB_TOP + 8.0
TRRS_OFFSET = 55.0      # TRRS開口中心の「外側端から」の距離（写真推定）
TRRS_W   = 9.0          # TRRS開口幅（y方向）
TRRS_Z0, TRRS_Z1 = PCB_TOP + 0.45, PCB_TOP + 5.85   # ジャック中心 = 基板表面+3.0

# --- アンダーグロー（本家アクリル層の代替案） ---
# 白フィラメント前提で、下側の壁の帯だけを薄くして基板裏面LEDの光を透過・拡散させる。
# 帯はボトムケース側（本家アクリル相当層）に入れる。帯の上下は通常壁厚が残り構造を保つ。
GLOW_ENABLE = True
GLOW_T      = 1.0     # 帯部分の壁厚（推奨下限 0.8mm: ノズル0.4で2ペリメータ相当）
GLOW_Z0     = FLOOR_T + 0.2   # 帯の下端 z = 2.8（床上面の少し上）
GLOW_Z1     = FLOOR_T + 1.8   # 帯の上端 z = 4.4（基板支持レッジ下端 4.5 の少し下）

# --- 基板深部のFR4穴用「吊りボス」（スイッチプレート裏面に一体化） ---
HANG_BOT  = PCB_TOP + 0.05   # 6.80: 基板表面すれすれ（基板に穴があればネジが通る）
HANG_DIA  = {"big": 7.0, "small": 5.5}
HANG_TAP_DEPTH = 3.3         # ネジは M3x10 / M2x10 想定（キットの x12 は長すぎる）
MCU_ZONE = {  # マイコン実装域（吊りボス禁止）: 外側角・背面寄り
    "short": (82.0, 114.3, 106.0, 143.4),
    "long":  (82.0, 114.3, 0.0, 37.0),
}

# --- ネジ（FR4穴: 大=M3, 小=M2） ---
TAP_DIA   = {"big": 2.8, "small": 1.7}    # タッピング下穴径
BOSS_DIA  = {"big": 8.0, "small": 6.0}    # フレーム側ボス外径
CLR_DIA   = {"big": 3.4, "small": 2.4}    # 床の通し穴径
CB_DIA    = {"big": 6.5, "small": 4.5}    # 頭ザグリ径（底面から）
BOSS_TOP_IN_PLATE  = PLATE_BOT - 0.05     # プレート帯域内ボスの天端（プレート裏面直下）
BOSS_TOP_FULL      = PLATE_TOP + 1.85     # プレート外ボスの天端
PIN_CLEAR = 0.15        # 位置決めピンの穴径に対する直径差
PIN_TOP   = FR4_RECESS_Z + FR4_T + 1.3    # 位置決めピン天端 z=3.8（基板裏面・裏面LED想定より下）

# --- FR4プレート座標変換（★暫定・試作片で確定する） ---
# case_x = plate_y + tx ; short: case_y = ty - plate_x（階段側が逆）, long: case_y = plate_x + ty
# tx=11 の根拠: 穴の列（plate_y=35.1/55.2/73.9）がスイッチ列（dxf_x=36.6/55.6/74.7）の
# 列間ストリート（46.1/65.1/84.2）に乗る値。tx=16 では全列が約+5.5 ずれて開口に重なる。
PLATE_TF = {
    "short": dict(tx=11.0, ty=134.2, mirror=True),
    "long":  dict(tx=11.0, ty=39.4,  mirror=False),
}

FEET_EXTRA = {  # ゴム足逃げ（Ø11x1.0）を追加する位置（大穴ボス位置には自動で付く）
    "short": [(100.0, 18.0)],
    "long":  [(100.0, 160.0)],
}

SIMPLIFY = 0.03  # 外形/ポケットの単純化トレランス（円弧の弦誤差として許容）

# ============================= データ読込 =============================
dxf = json.load(open(f"{BASE}/work_design/dxf_polys.json"))
ORIGIN = {"short": (0.0, 183.414), "long": (0.0, 0.0)}
IDX = {"short": 0, "long": 1}

def loc(pts, half):
    ox, oy = ORIGIN[half]
    return [(x - ox, y - oy) for x, y in pts]

def shp(pts):
    p = Polygon(pts)
    if not p.is_valid:
        p = p.buffer(0)
    return p

def largest(poly):
    if poly.geom_type == "MultiPolygon":
        return max(poly.geoms, key=lambda g: g.area)
    return poly

def inset(poly, d):   # 内側へ d
    return largest(poly.buffer(-d, join_style=2))
def outset(poly, d):  # 外側へ d
    return largest(poly.buffer(d, join_style=2))

halves = {}
for half in ("short", "long"):
    outline = shp(loc(dxf["OUTLINE"][IDX[half]]["pts"], half)).simplify(SIMPLIFY)
    pocket  = shp(loc(dxf["POCKET"][IDX[half]]["pts"], half)).simplify(SIMPLIFY)
    holes = []
    for hp in dxf["SWITCH_HOLES"]:
        pts = hp["pts"]
        cy = float(np.mean([q[1] for q in pts]))
        if (cy > 183.41) == (half == "short"):
            holes.append(loc(pts, half))
    pcb_pts = np.loadtxt(f"{BASE}/template/pcb_outline_{half}.csv", delimiter=",", skiprows=1)
    pcb = shp([tuple(r) for r in pcb_pts])
    halves[half] = dict(outline=outline, pocket=pocket, holes=holes, pcb=pcb)
    print(f"[{half}] outline area={outline.area:.0f} pocket area={pocket.area:.0f} "
          f"holes={len(holes)} pcb bbox={pcb.bounds}")

# FR4プレート穴（プレート単体ローカル → ケース座標へ変換）
plate_holes = {"short": [], "long": []}
for row in csv.DictReader(open(f"{BASE}/template/plate_holes_v2.csv")):
    hid = row["hole_id"]
    half = "short" if hid.startswith("L") else "long"
    tf = PLATE_TF[half]
    px, py = float(row["x_mm"]), float(row["y_mm"])
    cx = py + tf["tx"]
    cy = (tf["ty"] - px) if tf["mirror"] else (px + tf["ty"])
    plate_holes[half].append(dict(id=hid, x=cx, y=cy, cls=row["diameter_class"]))
    print(f"  hole {hid} -> case ({cx:.2f}, {cy:.2f}) class={row['diameter_class']}")

# パドルポケットの y 範囲を外形から抽出（背面 x=max 側の凹み3か所）
# y を細かく走査し、その y での外形最大 x が全体最大より 4mm 以上内側に
# 落ち込む区間をポケットとする（線分端点の有無に依存しない確実な方法）。
def paddle_pockets(outline):
    from shapely.geometry import LineString
    xmin, ymin, xmax, ymax = outline.bounds
    samples = []  # (y, depth) depth = その y での背面の落ち込み量
    y = ymin + 0.125
    while y <= ymax:
        line = LineString([(xmin - 1, y), (xmax + 1, y)])
        inter = outline.intersection(line)
        xs = []
        geoms = [inter] if inter.geom_type == "LineString" else list(getattr(inter, "geoms", []))
        for g in geoms:
            if g.geom_type == "LineString" and len(g.coords) > 0:
                xs.append(max(c[0] for c in g.coords))
        if xs:
            samples.append((y, xmax - max(xs)))
        y += 0.25
    ranges, cur = [], None
    for yy, dep in samples:
        if 6.5 < dep < 9.5:   # ポケット底の深さ ≈ 8.0（階段側の大きな落ち込みと区別）
            if cur is None:
                cur = [yy, yy]
            else:
                cur[1] = yy
        elif cur is not None:
            ranges.append(tuple(cur)); cur = None
    if cur is not None:
        ranges.append(tuple(cur))
    return [(a, b) for a, b in ranges if b - a > 3.0]

for half in ("short", "long"):
    pk = paddle_pockets(halves[half]["outline"])
    halves[half]["pockets_y"] = pk
    print(f"[{half}] paddle pockets y-ranges: {[(round(a,2), round(b,2)) for a,b in pk]}")

# ============================= 形状ヘルパ =============================
def ring_pts(poly):
    return [(float(x), float(y)) for x, y in poly.exterior.coords][:-1]

def prism(poly, z0, z1):
    return prism_pts(ring_pts(poly), z0, z1)

def prism_pts(pts, z0, z1):
    wire = bd.Wire.make_polygon([bd.Vector(x, y, z0) for x, y in pts])
    return bd.Solid.extrude(bd.Face(wire), bd.Vector(0, 0, z1 - z0))

def cyl(x, y, z0, dia, h):
    return bd.Solid.make_cylinder(dia / 2, h, bd.Plane(origin=(x, y, z0)))

def box(x0, x1, y0, y1, z0, z1):
    return bd.Solid.make_box(x1 - x0, y1 - y0, z1 - z0, bd.Plane(origin=(x0, y0, z0)))

def bbox_of(part):
    bb = part.bounding_box()
    return (bb.min.X, bb.max.X, bb.min.Y, bb.max.Y, bb.min.Z, bb.max.Z)

# ============================= パーツ構築 =============================
def classify_holes(half, plate_bnd0):
    """FR4穴を boss / hang / pin に分類する。
    - boss: 基板の外 or 基板端から 4mm 以内の帯 → フレーム側ボス（下からネジ）。
      本家キットが大穴6個すべてを M3x8 で使うことからの推定（端部帯は基板に
      切り欠き/取付穴がある前提。試作片で検証）。
    - hang: 基板深部だが、スイッチ開口・マイコン域から離れている → スイッチ
      プレート裏面の吊りボス（基板に取付穴があればネジが通る。無ければ未使用で無害）。
      プレート外周が届かない位置では、プレートに丸い耳（ear）を出して吊る。
    - pin : それ以外 → ボトムケースの位置決めピン（基板裏面には届かない高さ）。"""
    H = halves[half]
    pcb = H["pcb"]
    sw_polys = [Polygon(hp) for hp in H["holes"]]
    mx0, mx1, my0, my1 = MCU_ZONE[half]
    frame_zone = inset(H["outline"], WALL - 0.35)
    res = []
    for h in plate_holes[half]:
        pt = Point(h["x"], h["y"])
        inside = pt.within(pcb)
        d_edge = pt.distance(pcb.boundary) if inside else 0.0
        entry = dict(h, ear=False)
        if (not inside) or d_edge <= 4.0:
            entry["kind"] = "boss"
        else:
            r = HANG_DIA[h["cls"]] / 2
            d_sw = min(pt.distance(sp) for sp in sw_polys)
            in_mcu = (mx0 <= h["x"] <= mx1) and (my0 <= h["y"] <= my1)
            in_plate = pt.within(plate_bnd0.buffer(-(r + 0.3)))
            ear_r = r + 1.5
            ear_ok = (d_sw >= ear_r + 0.3) and pt.within(frame_zone.buffer(-ear_r))
            if d_sw >= r + 0.3 and not in_mcu and in_plate:
                entry["kind"] = "hang"
            elif d_sw >= r + 0.3 and not in_mcu and ear_ok:
                entry["kind"] = "hang"; entry["ear"] = True
            else:
                entry["kind"] = "pin"
        res.append(entry)
        print(f"[{half}] {h['id']} ({h['x']:.1f},{h['y']:.1f}) {h['cls']} inside_pcb={inside} "
              f"d_edge={d_edge:.1f} -> {entry['kind']}" + (" (ear)" if entry.get("ear") else ""))
    return res

def build_half(half):
    H = halves[half]
    outline, pocket, pcb = H["outline"], H["pocket"], H["pcb"]
    cavity = inset(outline, WALL)
    plate_bnd = largest(outset(pocket, PLATE_UNDERLAP).intersection(inset(outline, WALL - 0.35)))
    holes_cls = classify_holes(half, plate_bnd)
    # 吊りボス用の耳をプレート外周へ追加し、最終外周を確定
    ears = [Point(e["x"], e["y"]).buffer(HANG_DIA[e["cls"]] / 2 + 1.5)
            for e in holes_cls if e["kind"] == "hang" and e.get("ear")]
    if ears:
        plate_bnd = largest(unary_union([plate_bnd] + ears))
    H["plate_bnd"] = plate_bnd
    for e in holes_cls:
        if e["kind"] == "boss":
            e["full"] = not Point(e["x"], e["y"]).within(plate_bnd.buffer(PLATE_CLR + 0.3))
    H["holes_cls"] = holes_cls
    xmax = outline.bounds[2]
    ymax = outline.bounds[3]
    outer_end_y = ymax if half == "short" else outline.bounds[1]  # 外側端の y
    trrs_y = (outer_end_y - TRRS_OFFSET) if half == "short" else (outer_end_y + TRRS_OFFSET)

    # ---------- スイッチプレート（別体） ----------
    plate = prism(plate_bnd, PLATE_BOT, PLATE_TOP)
    for hp in H["holes"]:
        plate = plate - prism_pts(hp, PLATE_BOT - 0.2, PLATE_TOP + 0.2)
    # 吊りボス（プレート裏面に一体化, 基板深部のFR4穴用）
    for e in holes_cls:
        if e["kind"] == "hang":
            plate = plate + cyl(e["x"], e["y"], HANG_BOT, HANG_DIA[e["cls"]], PLATE_BOT - HANG_BOT)
            plate = plate - cyl(e["x"], e["y"], HANG_BOT - 0.1, TAP_DIA[e["cls"]], HANG_TAP_DEPTH)

    # ---------- トップフレーム（枠） ----------
    ch = outset(plate_bnd, PLATE_CLR)     # プレート帯域の内壁
    well = outset(pocket, POCKET_CLR)     # 天面開口
    frame = (prism(outline, PCB_BOT, FRAME_TOP)
             - prism(ch, PCB_BOT - 0.1, PLATE_TOP)
             - prism(well, PLATE_TOP, FRAME_TOP + 0.1))
    # ボス（フレームから下向きに充填: チャネル帯域の材料 + タッピング穴）
    for e in holes_cls:
        if e["kind"] != "boss":
            continue
        top = BOSS_TOP_FULL if e["full"] else BOSS_TOP_IN_PLATE
        frame = frame + cyl(e["x"], e["y"], PCB_BOT, BOSS_DIA[e["cls"]], top - PCB_BOT)
        depth = 7.0 if e["full"] else 5.0
        frame = frame - cyl(e["x"], e["y"], PCB_BOT - 0.1, TAP_DIA[e["cls"]], depth)
    # パドルノッチ（背面壁, ポケット位置で z=PADDLE_NOTCH_Z0..天面 を開ける）
    for (py0, py1) in H["pockets_y"]:
        frame = frame - box(103.0, xmax + 1, py0 - 0.2, py1 + 0.2, PADDLE_NOTCH_Z0, FRAME_TOP + 0.1)
    # USB開口（外側端の壁）
    if half == "short":
        frame = frame - box(USB_XC - USB_W / 2, USB_XC + USB_W / 2, ymax - 1, ymax + 2, USB_Z0, USB_Z1)
    else:
        frame = frame - box(USB_XC - USB_W / 2, USB_XC + USB_W / 2, -2, 1, USB_Z0, USB_Z1)
    # TRRS開口（背面壁）
    frame = frame - box(xmax - 6.5, xmax + 1, trrs_y - TRRS_W / 2, trrs_y + TRRS_W / 2, TRRS_Z0, TRRS_Z1)

    # ---------- ボトムケース ----------
    bottom = prism(outline, 0, PCB_BOT) - prism(cavity, FLOOR_T, PCB_BOT + 0.1)
    # アンダーグロー帯（壁を GLOW_T まで薄くする: 内腔を帯の高さだけ外へ広げる）
    if GLOW_ENABLE:
        bottom = bottom - prism(inset(outline, GLOW_T), GLOW_Z0, GLOW_Z1)
    # FR4凹み
    bottom = bottom - prism(inset(outline, FR4_INSET), FR4_RECESS_Z, FLOOR_T + 0.01)
    # 基板支持レッジ
    ledge = prism(cavity, FLOOR_T + 1.9, PCB_BOT) - prism(inset(outline, LEDGE_INSET), FLOOR_T + 1.8, PCB_BOT + 0.1)
    bottom = bottom + ledge
    # タクト逃げ窓（背面・ポケット位置の床〜レッジを抜く）
    for (py0, py1) in H["pockets_y"]:
        bottom = bottom - box(TACT_WIN_X0, xmax - 2.0, py0 - TACT_WIN_MARGIN, py1 + TACT_WIN_MARGIN, -0.1, PCB_BOT)
    # ネジ通し穴＋頭ザグリ / 位置決めピン
    for e in holes_cls:
        if e["kind"] in ("boss", "hang"):
            bottom = bottom - cyl(e["x"], e["y"], -0.1, CLR_DIA[e["cls"]], FLOOR_T + 0.2)
            # 頭ザグリ: FR4下面の直下まで（低頭ネジの頭が FR4 と干渉しない深さ）
            bottom = bottom - cyl(e["x"], e["y"], -0.1, CB_DIA[e["cls"]], FR4_RECESS_Z + 0.05)
        elif e["kind"] == "pin":
            dia = (2.85 if e["cls"] == "big" else 1.75) - PIN_CLEAR
            bottom = bottom + cyl(e["x"], e["y"], FR4_RECESS_Z, dia, PIN_TOP - FR4_RECESS_Z)
    # ゴム足逃げ
    feet = [(e["x"], e["y"]) for e in holes_cls if e["kind"] in ("boss", "hang") and e["cls"] == "big"] + FEET_EXTRA[half]
    for (fx, fy) in feet:
        bottom = bottom - cyl(fx, fy, -0.1, 11.0, 1.0)

    return dict(plate=plate, frame=frame, bottom=bottom)

def export(part, name):
    path = f"{OUTDIR}/{name}.stl"
    bd.export_stl(part, path)
    print("exported", path, "bbox", [round(v, 2) for v in bbox_of(part)])
    return path

def clip(part, xr, yr):
    tool = box(xr[0], xr[1], yr[0], yr[1], -1, FRAME_TOP + 1)
    res = part.intersect(tool)
    solids = []
    for s in res:
        solids.extend(s.solids() if hasattr(s, "solids") else [s])
    if not solids:
        raise RuntimeError("clip produced no solid")
    out = solids[0]
    for s in solids[1:]:
        out = out + s
    return out

results = {}
for half in ("short", "long"):
    print(f"===== build {half} =====")
    parts = build_half(half)
    results[half] = parts
    export(parts["plate"], f"switch_plate_{half}")
    export(parts["frame"], f"top_frame_{half}")
    export(parts["bottom"], f"bottom_case_{half}")

# ============================= 試作片 =============================
# 1) 階段境界（両半分）: 階段側 50mm 帯をフル積層で切り出し
for half, yr in (("short", (-3, 50)), ("long", (127.2, 180.2))):
    P = results[half]
    comp = (clip(P["bottom"], (-3, 117.3), yr)
            + clip(P["plate"], (-3, 117.3), yr)
            + clip(P["frame"], (-3, 117.3), yr))
    export(comp, f"trial_stair_{half}")

# 2) ネジ穴ボス部: FR4穴のある帯を切り出し（実物プレートを重ねて変換を当てる）
P = results["short"]
export(clip(P["bottom"], (-3, 62), (118, 146.4)), "trial_boss_bottom_short")
export(clip(P["frame"], (-3, 62), (118, 146.4)), "trial_boss_frame_short")
P = results["long"]
export(clip(P["bottom"], (-3, 78), (115, 180.2)), "trial_boss_bottom_long")
export(clip(P["frame"], (-3, 78), (115, 180.2)), "trial_boss_frame_long")

# 3) 背面-外側角（short）: パドルポケット×3 + タクト窓 + TRRS開口 + USB開口
P = results["short"]
comp = (clip(P["bottom"], (80, 117.3), (80, 146.4))
        + clip(P["frame"], (80, 117.3), (80, 146.4)))
export(comp, "trial_corner_short")

print("DONE")
