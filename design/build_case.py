# -*- coding: utf-8 -*-
"""
7sProMax 3Dプリントケース 立体設計 v2

v1 の実物合わせで判明した3不適合（階段キャビティ干渉／スイッチプレート穴
14.95mm ではパチ留めできない／パドルポケットが羽根込み幅 8.7mm に不足）を、
分割済み基板スキャンの実測（PCB_SCAN2_NOTES）とパドル実測で作り直した版。

v2 の要点:
  - 白FR4ボトムプレートは廃止。構成は トップフレーム／スイッチプレート／
    基板／ボトムケース。基板下面〜ボトム床の空間は 3.2mm（v1 の FR4上面〜
    基板下面と同等）を確保し、総高 16.1mm・外形は v1 のまま維持。
  - ボトムケースのキャビティ壁は、図面外形の一律 inset ではなく
    実測基板外形（pcb_outline2）+ 0.5mm オフセットで全周生成する。
  - スイッチプレート穴は MX パチ留め標準 14.0mm角 + FDM補正 0.15
    = モデル 14.15mm角。位置は実測で正しいと確認された DXF 中心のまま。
    横長スロット（15.71x7.45、計6か所）はスイッチ穴ではないので図面形状のまま。
  - パドルまわりは実測エンベロープ（羽根込み幅 8.7／全長 27.3／ブロック
    高さ約8.5／バー厚 2.7）で作り直し: タクト中心基準の窓（幅 9.9）を
    ボトムに、同じ帯をフレーム背面に全高で開けた。
  - ネジ計画 v2: FR4穴基準を廃止。背面リムのケース同士締結（M3×3/半分）
    ＋ 基板ネジ穴（pcb_screw_holes の HIGH/MEDIUM）のうち吊りボスが
    成立する位置だけスイッチプレート裏の吊りボスで受ける（基板穴を通す）。

座標系: DXFテンプレートの半分ローカル座標をそのまま使う。
  X = 奥行方向（0..114.29, x=114側が背面＝マイコン/パドル側）
  Y = 長さ方向（short: y=0が階段（中央）側, y=143.36が外側端
               long : y=0が外側端, y=177.23が階段（中央）側）
  Z = ケース底面を 0 とする高さ。

入力:
  ../work_design/dxf_polys.json  （template DXFの抽出ポリゴン: OUTLINE/POCKET/SWITCH_HOLES）
  ../template/pcb_outline2_short.csv / pcb_outline2_long.csv （実測基板外形・階段実測版）
  ../template/pcb_screw_holes.csv （基板ネジ穴候補, 信頼度つき）

未確定（パラメータ化して試作片で当てる）:
  - USB開口位置（外側端の壁, マイコン角）: 基板写真からの推定。実装後の実測推奨。
  - TRRS開口位置（背面壁, 外側端から TRRS_OFFSET）: 写真からの推定 ±10mm級。
"""

import json, csv, math
import numpy as np
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union, nearest_points
import build123d as bd

BASE = "/home/hatch/workspace/7spromax-case"
OUTDIR = f"{BASE}/design"

# ============================= パラメータ =============================
# --- Z 積み上げ（ケース底面 z=0）根拠は DESIGN_NOTES §16 参照 ---
FLOOR_T        = 2.5    # ボトムケース床の厚み（床上面 z）。FR4廃止に伴い
                        # 床上面を旧FR4上面（2.5）に合わせ、基板下面までの
                        # 3.2mm（部品逃げ）をそのまま確保する
PCB_BOT        = 5.7    # 基板下面（ボトムケース壁天端＋支持レッジで受ける）
PCB_T          = 1.6    # 基板厚（実測）
PCB_TOP        = PCB_BOT + PCB_T                      # 7.3
FRAME_TOP      = 16.1   # ケース総高（本家側面図の 16.1 と一致させた）
PLATE_T        = 1.5    # 別体スイッチプレートの厚み（MXパチ留め標準板厚）
PLATE_BOT      = PCB_TOP + 2.2   # 9.5（ソケット上面 +2.0 の上に 0.2 逃げ）
PLATE_TOP      = PLATE_BOT + PLATE_T                  # 11.0

# --- キャビティ（実測基板外形ベース） ---
CAV_CLR        = 0.5    # 基板外形→キャビティ壁の片側クリアランス（全周・階段含む）。
                        # FDM収縮 0.3〜0.6% + 押出ばらつきを吸収する公称値
                        # （PCB_SCAN2_NOTES §5 の推奨: 直線部 0.5 以上）
MIN_WALL       = 0.8    # キャビティがケース外形へ食い出すのを防ぐ最小壁厚ガード。
                        # 階段の歯・背面タブ先端など、実測基板が外形に 1.7mm 未満まで
                        # 迫る箇所ではこのガードが効いてクリアランスが 0.5 を下回る
                        # （該当箇所と最小値はビルド時に表示し DESIGN_NOTES に記録）
LEDGE_UNDER    = 1.5    # 基板支持レッジが基板縁の下へ潜る量
LEDGE_EMBED    = 0.3    # レッジ外周をキャビティ壁側へ食い込ませる量（融合確保）
LEDGE_Z0       = 4.4    # レッジ下端（グロー帯上端と一致させ干渉を避ける）

# --- プレート外周・フレーム内壁（v1 から不変） ---
PLATE_UNDERLAP = 3.0    # プレート外周がポケット開口より外へ出る量（リップに隠れる分）
PLATE_CLR      = 0.25   # プレート外周とフレーム内壁の隙間
POCKET_CLR     = 0.25   # フレーム天面開口（ポケット）への追加クリアランス
PLATE_CAP_INSET = 2.25  # プレート外周の上限（外形からの inset、v1 の WALL-0.35 相当）

# --- スイッチプレート穴（v2 で変更） ---
SW_HOLE        = 14.0   # MX プレートパチ留め標準（mm角）
SW_HOLE_FDM    = 0.15   # FDM 印刷補正（穴は小さく出るためモデル側で拡大）
SW_HOLE_MODEL  = SW_HOLE + SW_HOLE_FDM   # 14.15mm角でモデリングする

# --- パドル（エクストラスイッチ）まわり: 実測エンベロープで作り直し ---
# 実測（PADDLE_MEASUREMENTS + 本人再読）: 羽根込み幅 8.7 / ブロック幅 4.8 /
# 全長 27.3 / ブロック高さ約 8.5 / バー厚 2.7（本人が実物で再読した値を正とする）
PADDLE_WING_W  = 8.7    # 羽根込み幅（幅方向の最大寸法）
PADDLE_CLR     = 0.6    # 羽根に対する片側クリアランス → 窓幅 9.9
PADDLE_WIN_X0  = 97.0   # 窓の x 開始（背面側）。ブロック占有 x≈101..111 に余裕を持たせた値
TACT_CENTERS   = {      # タクト中心 y（ケース座標, PCB_SCAN2_NOTES §8 の実測）
    "short": [102.6, 110.9, 121.7],
    "long":  [14.0, 23.5, 35.9],
}

# --- 開口（推定位置・要実物確認、v1 から不変） ---
USB_XC   = 97.0         # USB開口中心 x（マイコン帯域 85..110 の中央付近）
USB_W    = 10.0         # USB開口幅（x方向）
USB_Z0, USB_Z1 = PCB_TOP + 3.0, PCB_TOP + 8.0
TRRS_OFFSET = 55.0      # TRRS開口中心の「外側端から」の距離（写真推定）
TRRS_W   = 9.0          # TRRS開口幅（y方向）
TRRS_Z0, TRRS_Z1 = PCB_TOP + 0.45, PCB_TOP + 5.85   # ジャック中心 = 基板表面+3.0

# --- アンダーグロー（本家アクリル層の代替案、v1 から不変） ---
GLOW_ENABLE = True
GLOW_T      = 1.0     # 帯部分の壁厚（推奨下限 0.8mm: ノズル0.4で2ペリメータ相当）
GLOW_Z0     = 2.8     # 帯の下端 z（床上面 2.5 の少し上）
GLOW_Z1     = 4.4     # 帯の上端 z（基板支持レッジ下端と一致）

# --- ネジ計画 v2 ---
# 背面締結（ケース同士）: 実測基板の背面縁はケース外形に 1.7〜2.9mm まで迫る
# ため、背面リムに一律にネジは置けない。基板縁が後退する「湾」状の区間
# （外形−キャビティの壁区間のうち背面側で十分な幅がある場所）を y 方向に
# 走査して自動検出し、階段側／中央／外側の3帯域から最大3本を選ぶ。
# M3 で置けない帯域は M2 で再走査する。y の除外帯: パドル帯±2、TRRS±7、両端6mm。
BACK_SCREW_SPECS = {  # サイズ別の寸法
    "M3": dict(tap=2.8, clr=3.4, cb=6.5, tap_depth=6.6),
    "M2": dict(tap=1.7, clr=2.4, cb=4.5, tap_depth=5.6),
}
# 基板ネジ穴を使う吊りボス（スイッチプレート裏面, M3）: pcb_screw_holes の
# HIGH/MEDIUM 候補のうち、ボス（Ø7）がスイッチ開口・マイコン域と干渉せず
# プレート上に載る位置だけを自動採用する（不採用理由は標準出力に出る）。
HANG_BOT  = PCB_TOP + 0.05   # 7.35: 基板表面すれすれ
HANG_OVERLAP = 0.5           # 吊りボス上端をプレートスラブへ食い込ませる量（融合確保）
HANG_DIA  = 7.0              # M3 用ボス外径
HANG_TAP_DIA = 2.8
HANG_TAP_DEPTH = 3.3         # 推奨ネジ M3x10（床2.5+隙間3.2+基板1.6+かかり約2.7）
MCU_ZONE = {  # マイコン実装域（吊りボス禁止）: 外側角・背面寄り（v1 から不変）
    "short": (82.0, 114.3, 106.0, 143.4),
    "long":  (82.0, 114.3, 0.0, 37.0),
}
CB_DEPTH  = 1.3         # 頭ザグリ深さ（底面から, 低頭ネジ前提）

FEET_EXTRA = {  # ゴム足逃げ（Ø11x1.0）を追加する位置（背面ネジ位置には自動で付く）
    "short": [(100.0, 18.0)],
    "long":  [(100.0, 160.0)],
}

# --- STL書き出しの正規化（v1 から不変） ---
DROP_VOL    = 10.0      # mm3: これ未満の独立ソリッドは書き出し時に除去する
FIN_EPS     = 0.15      # スイッチ穴がプレート外周にこれ未満の距離で接する場合、その穴の
                        # 周囲この量を外形から除いて開口を外形の notch として取り込む
                        # （フィン・接線接触による non-manifold 防止）

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
def outset(poly, d, round_join=False):  # 外側へ d
    return largest(poly.buffer(d, join_style=1 if round_join else 2))

halves = {}
for half in ("short", "long"):
    outline = shp(loc(dxf["OUTLINE"][IDX[half]]["pts"], half)).simplify(SIMPLIFY)
    pocket  = shp(loc(dxf["POCKET"][IDX[half]]["pts"], half)).simplify(SIMPLIFY)
    sw_holes, slots = [], []
    for hp in dxf["SWITCH_HOLES"]:
        pts = hp["pts"]
        cy = float(np.mean([q[1] for q in pts]))
        if (cy > 183.41) == (half == "short"):
            poly = shp(loc(pts, half))
            b = poly.bounds
            w, h = b[2] - b[0], b[3] - b[1]
            if w > 15.5 and h < 8.0:
                slots.append(poly)            # 横長スロット（タクト用開口等）: 図面形状のまま
            else:
                c = poly.centroid
                sw_holes.append(dict(cx=c.x, cy=c.y, poly=poly))  # 中心は実測検証済み
    pcb_pts = np.loadtxt(f"{BASE}/template/pcb_outline2_{half}.csv", delimiter=",", skiprows=1)
    pcb = shp([tuple(r) for r in pcb_pts])
    halves[half] = dict(outline=outline, pocket=pocket, sw=sw_holes, slots=slots, pcb=pcb)
    print(f"[{half}] outline area={outline.area:.0f} pocket area={pocket.area:.0f} "
          f"switch holes={len(sw_holes)} slots={len(slots)} pcb2 bbox={pcb.bounds}")

# 基板ネジ穴候補（HIGH/MEDIUM のみ使う）
screw_candidates = {"short": [], "long": []}
for row in csv.DictReader(open(f"{BASE}/template/pcb_screw_holes.csv")):
    if row["confidence"] in ("high", "medium"):
        screw_candidates[row["half"]].append(
            dict(x=float(row["case_x_mm"]), y=float(row["case_y_mm"]),
                 dia=float(row["diameter_mm_est"]), conf=row["confidence"]))
for half in ("short", "long"):
    print(f"[{half}] pcb screw candidates (high/medium): "
          f"{[(round(c['x'],1), round(c['y'],1), c['conf']) for c in screw_candidates[half]]}")

# パドル窓の帯（タクト中心 ±（羽根込み幅/2 + クリアランス））をマージした区間
def merged_spans(half):
    hw = PADDLE_WING_W / 2 + PADDLE_CLR
    spans = sorted((c - hw, c + hw) for c in TACT_CENTERS[half])
    out = []
    for a, b in spans:
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out

for half in ("short", "long"):
    halves[half]["paddle_spans"] = merged_spans(half)
    print(f"[{half}] paddle spans: {[(round(a,1), round(b,1)) for a,b in halves[half]['paddle_spans']]}")

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

def square_poly(cx, cy, size):
    h = size / 2
    return Polygon([(cx - h, cy - h), (cx + h, cy - h), (cx + h, cy + h), (cx - h, cy + h)])

# ============================= ネジ計画の確定 =============================
def _line_max_x(poly, line):
    """水平線とポリゴンの交差の最大 x（無ければ -1e9）。"""
    inter = poly.intersection(line)
    m = -1e9
    geoms = [inter] if inter.geom_type == "LineString" else list(getattr(inter, "geoms", []))
    for g in geoms:
        if g.geom_type == "LineString" and len(g.coords) > 1:
            m = max(m, max(c[0] for c in g.coords))
        elif g.geom_type == "Point":
            m = max(m, g.x)
    return m

def _line_segments(poly, line):
    inter = poly.intersection(line)
    segs = []
    geoms = [inter] if inter.geom_type == "LineString" else list(getattr(inter, "geoms", []))
    for g in geoms:
        if g.geom_type == "LineString" and len(g.coords) > 1:
            xs = [c[0] for c in g.coords]
            segs.append((min(xs), max(xs)))
    return segs

def plan_screws(half, plate_bnd, cavity):
    """背面締結（走査で「湾」を検出）と吊りボス候補の可否を決める。
    戻り値: (back, hangs) — 各要素は dict(x, y, size) / dict(x, y, ear)。"""
    H = halves[half]
    outline, pocket = H["outline"], H["pocket"]
    ch = outset(plate_bnd, PLATE_CLR)
    well = outset(pocket, POCKET_CLR)
    xmax, ymax = outline.bounds[2], outline.bounds[3]
    wall = outline.difference(cavity)
    outer_end_y = ymax if half == "short" else outline.bounds[1]
    trrs_y = (outer_end_y - TRRS_OFFSET) if half == "short" else (outer_end_y + TRRS_OFFSET)

    def y_excluded(y):
        if y < 6.0 or y > ymax - 6.0:
            return True
        if abs(y - trrs_y) < 7.0:
            return True
        return any(a - 2.0 <= y <= b + 2.0 for a, b in H["paddle_spans"])

    def scan(size):
        spec = BACK_SCREW_SPECS[size]
        tr = spec["tap"] / 2
        found = []  # (y, bx, slack)
        y = 6.0
        while y <= ymax - 6.0:
            if not y_excluded(y):
                line = LineString([(-1, y), (xmax + 1, y)])
                lo_base = max(_line_max_x(ch, line), _line_max_x(well, line)) + tr + 1.6
                for (x0, x1) in _line_segments(wall, line):
                    if x0 < 90.0:
                        continue  # 背面側の区間だけを対象にする
                    lo = max(x0 + tr + 0.3, lo_base)
                    hi = x1 - tr - 0.3
                    if hi >= lo:
                        found.append((y, (lo + hi) / 2, hi - lo))
            y += 1.0
        return found

    # 帯域ごとに最も余裕のある候補を選ぶ（M3 優先、無ければ M2）
    y_lo, y_hi = 6.0, ymax - 6.0
    bands = [(y_lo + (y_hi - y_lo) * i / 3, y_lo + (y_hi - y_lo) * (i + 1) / 3) for i in range(3)]
    back = []
    for size in ("M3", "M2"):
        found = scan(size)
        for (b0, b1) in bands:
            if any(b0 <= e["y"] < b1 for e in back):
                continue
            cand = [f for f in found if b0 <= f[0] < b1]
            if cand:
                y, bx, slack = max(cand, key=lambda f: f[2])
                back.append(dict(x=bx, y=y, size=size))
                print(f"[{half}] back screw {size} band y[{b0:.0f},{b1:.0f}): "
                      f"-> ({bx:.2f},{y:.0f}) slack={slack:.2f}")
    if not back:
        print(f"[{half}] WARNING: no back screw position found")
    back.sort(key=lambda e: e["y"])

    # --- 吊りボス候補（基板ネジ穴, M3） ---
    hangs = []
    mx0, mx1, my0, my1 = MCU_ZONE[half]
    frame_zone = inset(outline, PLATE_CAP_INSET)
    sw_polys = [s["poly"] for s in H["sw"]] + H["slots"]
    for c in screw_candidates[half]:
        pt = Point(c["x"], c["y"])
        r = HANG_DIA / 2
        d_sw = min(pt.distance(sp) for sp in sw_polys)
        d_plate = pt.distance(plate_bnd)
        in_mcu = (mx0 <= c["x"] <= mx1) and (my0 <= c["y"] <= my1)
        in_plate = pt.within(plate_bnd.buffer(-(r + 0.3)))
        ear_r = r + 1.5
        ear_ok = (d_sw >= ear_r + 0.3 and d_plate <= ear_r - 0.5
                  and pt.within(frame_zone.buffer(-ear_r)))
        if in_mcu:
            verdict = "rejected (MCU zone)"
        elif d_sw < r + 0.3:
            verdict = f"rejected (switch opening too close: d={d_sw:.2f} < {r + 0.3:.2f})"
        elif in_plate:
            verdict = "ACCEPTED"
        elif ear_ok:
            verdict = "ACCEPTED (ear)"
        else:
            verdict = (f"rejected (boss off plate: dist to plate boundary={d_plate:.2f}, "
                       f"ear reach={ear_r - 0.5:.2f})")
        print(f"[{half}] hang candidate ({c['x']:.2f},{c['y']:.2f}) dia~{c['dia']} "
              f"{c['conf']}: d_sw={d_sw:.2f} -> {verdict}")
        if verdict.startswith("ACCEPTED"):
            hangs.append(dict(x=c["x"], y=c["y"], ear=verdict.endswith("(ear)")))
    return back, hangs

# ============================= パーツ構築 =============================
def build_half(half):
    H = halves[half]
    outline, pocket, pcb = H["outline"], H["pocket"], H["pcb"]
    cavity = largest(outset(pcb, CAV_CLR, round_join=True).intersection(inset(outline, MIN_WALL)))
    # クリアランス実績の診断（基板輪郭を 0.5mm 刻みでサンプル）
    bnd = pcb.boundary
    samples = [bnd.interpolate(s).distance(cavity.boundary)
               for s in np.arange(0, bnd.length, 0.5)]
    samples = np.array(samples)
    print(f"[{half}] cavity: area={cavity.area:.0f} clearance min={samples.min():.3f} "
          f"p1={np.percentile(samples, 1):.3f} median={np.median(samples):.3f} "
          f"samples<0.3: {(samples < 0.3).sum()}/{len(samples)}")
    H["cavity"] = cavity

    plate_bnd = largest(outset(pocket, PLATE_UNDERLAP).intersection(inset(outline, PLATE_CAP_INSET)))
    back_screws, hangs = plan_screws(half, plate_bnd, cavity)
    H["back_screws"], H["hangs"] = back_screws, hangs
    # 吊りボス用の耳をプレート外周へ追加し、最終外周を確定
    ears = [Point(e["x"], e["y"]).buffer(HANG_DIA / 2 + 1.5) for e in hangs if e.get("ear")]
    if ears:
        plate_bnd = largest(unary_union([plate_bnd] + ears))
    H["plate_bnd"] = plate_bnd
    xmax = outline.bounds[2]
    ymax = outline.bounds[3]
    outer_end_y = ymax if half == "short" else outline.bounds[1]  # 外側端の y
    trrs_y = (outer_end_y - TRRS_OFFSET) if half == "short" else (outer_end_y + TRRS_OFFSET)

    # ---------- スイッチプレート（別体） ----------
    hole_polys = [square_poly(s["cx"], s["cy"], SW_HOLE_MODEL) for s in H["sw"]] + list(H["slots"])
    fin_holes = [hp for hp in hole_polys if hp.boundary.distance(plate_bnd.boundary) < FIN_EPS]
    plate_bnd_p = plate_bnd
    if fin_holes:
        moat = unary_union([h.buffer(FIN_EPS) for h in fin_holes])
        plate_bnd_p = shp(ring_pts(largest(plate_bnd.difference(moat))))
        print(f"[{half}] plate fin-fix: {len(fin_holes)} hole(s) near outline, "
              f"outline area {plate_bnd.area:.0f} -> {plate_bnd_p.area:.0f}")
    plate = prism(plate_bnd_p, PLATE_BOT, PLATE_TOP)
    for hp in hole_polys:
        plate = plate - prism(hp, PLATE_BOT - 0.2, PLATE_TOP + 0.2)
    # 吊りボス（プレート裏面に一体化, 基板ネジ穴用。上端はスラブへ食い込ませて融合）
    for e in hangs:
        plate = plate + cyl(e["x"], e["y"], HANG_BOT, HANG_DIA,
                            PLATE_BOT - HANG_BOT + HANG_OVERLAP)
        plate = plate - cyl(e["x"], e["y"], HANG_BOT - 0.1, HANG_TAP_DIA, HANG_TAP_DEPTH)

    # ---------- トップフレーム（枠） ----------
    ch = outset(plate_bnd, PLATE_CLR)     # プレート帯域の内壁
    well = outset(pocket, POCKET_CLR)     # 天面開口
    frame = (prism(outline, PCB_BOT, FRAME_TOP)
             - prism(ch, PCB_BOT - 0.1, PLATE_TOP)
             - prism(well, PLATE_TOP, FRAME_TOP + 0.1))
    # 背面締結のタッピング穴（サイズ別）
    for e in back_screws:
        spec = BACK_SCREW_SPECS[e["size"]]
        frame = frame - cyl(e["x"], e["y"], PCB_BOT - 0.1, spec["tap"], spec["tap_depth"] + 0.1)
    # パドル通路（背面, 基板上面から天面まで全高で開ける。羽根込み幅 8.7 の
    # ブロックが壁を乗り越える通り道。帯と帯の間の「歯」を残すと、両側を
    # 切り取られて浮きソリッドになるため、フレーム側は帯全体を1区間で開ける）
    span_all = (min(a for a, _ in H["paddle_spans"]), max(b for _, b in H["paddle_spans"]))
    frame = frame - box(100.0, xmax + 1, span_all[0], span_all[1], PCB_BOT - 0.1, FRAME_TOP + 0.1)
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
    # 基板支持レッジ（キャビティ壁から基板縁の下へ LEDGE_UNDER 潜る帯。
    # 外周はキャビティ壁の外へ食い込ませて融合させる）
    ledge = (prism(outset(cavity, LEDGE_EMBED, round_join=True), LEDGE_Z0, PCB_BOT)
             - prism(inset(pcb, LEDGE_UNDER), LEDGE_Z0 - 0.1, PCB_BOT + 0.1))
    bottom = bottom + ledge
    # パドル／タクト逃げ窓（背面, パドル帯は床から基板下面まで全て抜く。
    # 裏面タクトのボタン（基板裏面-5.0）とパドルの巻き込み・羽根の逃げ）
    for (sy0, sy1) in H["paddle_spans"]:
        bottom = bottom - box(PADDLE_WIN_X0, xmax + 1, sy0, sy1, -0.1, PCB_BOT)
    # ネジ通し穴＋頭ザグリ（背面締結はサイズ別、吊りボスは M3）
    all_screws = [(e["x"], e["y"], BACK_SCREW_SPECS[e["size"]]) for e in back_screws]
    all_screws += [(e["x"], e["y"], BACK_SCREW_SPECS["M3"]) for e in hangs]
    for (sx, sy, spec) in all_screws:
        bottom = bottom - cyl(sx, sy, -0.1, spec["clr"], PCB_BOT + 0.2)
        bottom = bottom - cyl(sx, sy, -0.1, spec["cb"], CB_DEPTH + 0.1)
    # ゴム足逃げ
    for (fx, fy, _) in all_screws:
        bottom = bottom - cyl(fx, fy, -0.1, 11.0, 1.0)
    for (fx, fy) in FEET_EXTRA[half]:
        bottom = bottom - cyl(fx, fy, -0.1, 11.0, 1.0)

    return dict(plate=plate, frame=frame, bottom=bottom)

def fuse_solids(solids):
    out = solids[0]
    for s in solids[1:]:
        out = out + s
    return out

def normalize(part, name):
    """微小ソリッド（残骸）を除き、残りを融合して単一ソリッド化する。"""
    solids = list(part.solids())
    kept = []
    for s in solids:
        if s.volume >= DROP_VOL:
            kept.append(s)
        else:
            print(f"  [normalize] {name}: micro solid removed (vol={s.volume:.2f} mm3)")
    if not kept:
        raise RuntimeError(f"{name}: no solid left after normalize")
    return fuse_solids(kept)

def export(part, name):
    fused = normalize(part, name)
    ns = len(fused.solids())
    zmin = fused.bounding_box().min.Z
    fused = fused.moved(bd.Location((0, 0, -zmin)))
    path = f"{OUTDIR}/{name}.stl"
    bd.export_stl(fused, path)
    bb = fused.bounding_box()
    print(f"exported {path} solids={ns} vol={fused.volume:.0f} "
          f"bbox x[{bb.min.X:.1f},{bb.max.X:.1f}] y[{bb.min.Y:.1f},{bb.max.Y:.1f}] "
          f"z[{bb.min.Z:.2f},{bb.max.Z:.2f}]")
    if ns > 1:
        for s in fused.solids():
            sb = s.bounding_box()
            print(f"  [export] {name}: solid vol={s.volume:.0f} "
                  f"bbox x[{sb.min.X:.1f},{sb.max.X:.1f}] y[{sb.min.Y:.1f},{sb.max.Y:.1f}] "
                  f"z[{sb.min.Z:.2f},{sb.max.Z:.2f}]")
    return path

def clip(part, xr, yr):
    tool = box(xr[0], xr[1], yr[0], yr[1], -1, FRAME_TOP + 1)
    res = part.intersect(tool)
    solids = []
    for s in res:
        solids.extend(s.solids() if hasattr(s, "solids") else [s])
    solids = [s for s in solids if s.volume >= DROP_VOL]
    if not solids:
        raise RuntimeError("clip produced no solid")
    return fuse_solids(solids)

def trial_compose(pieces, xr, yr, name):
    """積層試作片: 各パーツの切り出しを重ねて融合する。
    面接触だけでは融合しない場合は、フレームを -0.05 / プレートを +0.05 に
    ずらして体積的に重ねてから融合し直す（試作片の当たり確認には影響しない量）。
    pieces: [(part, nudge_z), ...]"""
    fused = None
    for use_nudge in (False, True):
        solids = []
        for part, nz in pieces:
            c = clip(part, xr, yr)
            if use_nudge and nz:
                c = c.moved(bd.Location((0, 0, nz)))
            solids.extend(c.solids())
        kept = [s for s in solids if s.volume >= DROP_VOL]
        fused = fuse_solids(kept)
        if len(fused.solids()) == 1:
            if use_nudge:
                print(f"  [trial] {name}: fused with z-nudge")
            return fused
    print(f"  [trial] {name}: WARNING still {len(fused.solids())} solids")
    return fused

results = {}
for half in ("short", "long"):
    print(f"===== build {half} =====")
    parts = build_half(half)
    results[half] = parts
    export(parts["plate"], f"switch_plate_{half}")
    export(parts["frame"], f"top_frame_{half}")
    export(parts["bottom"], f"bottom_case_{half}")

# ============================= 試作片 =============================
# 1) 階段境界（両半分）: 階段側 50mm 帯をフル積層で切り出し（新キャビティの当たり確認）
for half, yr in (("short", (-3, 50)), ("long", (127.2, 180.2))):
    P = results[half]
    comp = trial_compose([(P["bottom"], 0.0), (P["plate"], 0.05), (P["frame"], -0.05)],
                         (-3, 117.3), yr, f"trial_stair_{half}")
    export(comp, f"trial_stair_{half}")

# 2) 背面-外側角（short）: パドルポケット×3 + タクト窓 + TRRS開口 + USB開口
P = results["short"]
comp = trial_compose([(P["bottom"], 0.0), (P["frame"], -0.05)],
                     (80, 117.3), (80, 146.4), "trial_corner_short")
export(comp, "trial_corner_short")

# 3) ネジまわり（v2 計画の確認）: 背面リム締結 + 吊りボス候補帯をフル積層で切り出し
P = results["short"]
comp = trial_compose([(P["bottom"], 0.0), (P["plate"], 0.05), (P["frame"], -0.05)],
                     (-3, 117.3), (118, 146.4), "trial_screw_short")
export(comp, "trial_screw_short")
P = results["long"]
comp = trial_compose([(P["bottom"], 0.0), (P["plate"], 0.05), (P["frame"], -0.05)],
                     (-3, 117.3), (100, 180.2), "trial_screw_long")
export(comp, "trial_screw_long")

# 4) プレート穴のパチ留め確認片（新規）: 実寸の穴 2x2（ピッチ 19.05）だけの小片。
#    厚みは実プレートと同じ 1.5。スイッチを差して保持されるかだけを見る。
tp = box(0, 47.6, 0, 38.1, 0, PLATE_T)
for hx in (14.275, 33.325):
    for hy in (9.525, 28.575):
        sq = square_poly(hx, hy, SW_HOLE_MODEL)
        tp = tp - prism(sq, -0.2, PLATE_T + 0.2)
export(tp, "trial_plate_holes")

print("DONE")
