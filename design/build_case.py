# -*- coding: utf-8 -*-
"""
7sProMax 3Dプリントケース 立体設計 v2.3

v2.3 の要点（詳細は DESIGN_NOTES §17.12）:
  - 基板外形を pcb_outline3 に切り替えた。outline2 の階段帯はスキャンの
    エッジ探索が基板表面の段差状グルーブを実縁と誤認した幻影（最大で
    約27mm内側への zigzag）を含んでいたため、実測ソケット中心・
    19.05mmピッチ・公式図面の段位置をアンカーに矩形ステップとして
    再構成した（template/OUTLINE3_NOTES.md）。非階段部は outline2 と同一。
  - 階段の壁厚に上限（STAIR_WALL=2.2）を導入した: 階段帯ではキャビティを
    「外形から 2.2mm より深い領域」との和集合まで広げ、壁が段差の形に
    沿って概ね均一な厚さになるようにした（三角形の厚い壁の除去、
    本人決定）。基板+0.5 のクリアランスはキャビティを広げる方向の変更
    なので割らない。

v2.1 の要点（詳細は DESIGN_NOTES §17）:
  - 積層は本家と同じ構成にした: 黒ボトムトレイ → 白い側面バンド（LED の
    光漏れ層、z 2.5〜5.7 の全周リング、薄壁部 1.2mm）→ 基板 → 黒プレート →
    黒フレーム。旧ボトムケースの外周壁（床上面〜基板下面）をバンドとして
    独立させ、トレイは床＋内側の造形だけの浅いトレイにした。バンドと
    トレイの位置決めはスカート＋溝（全周）。
  - トップフレーム下帯（z 5.7〜9.5）の内壁をプレート帯域（pocket+3.0）から
    キャビティ輪郭（基板+0.5、クリップなし）へ変更し、基板との干渉（v2 で約1,559mm3）を解消。
  - フレームのパドル通路を帯全高開放からタクト別スロット（中心±3.0、
    z 6.2〜10.1、内側端 x=104）へ変更し、パドルを保持できる形にした。
  - 階段外形をラン（踏面／蹴上）ごとの直線ブロックに量子化し、各ランで
    キャビティから壁厚 2.2mm を確保（内側のキャビティは基板+0.5 のまま）。
  - バンドのパドル窓は gap 3.0 未満の窓間を連結し、細い歯・孤立フィンを
    除去。short の窓端フィンは切り取り、long はウェブで接続。
  - スイッチ穴〜プレート外周のフィン取り込み閾値を 0.5mm に拡張
    （横長スロットは従来どおり 0.15mm）。
  - 試作片は1回の印刷セッションに集約（全9片、パーツ別クリップのみ）。

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
  ../template/pcb_outline3_short.csv / pcb_outline3_long.csv （実測基板外形・階段再構成版、v2.3）
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
# --- v2.1: フレームのパドルスロット（完成形 7354 準拠の横スロット） ---
# 配置Bのバー（z 6.8〜9.5、幅 4.8）に上下 0.6 のクリアランスを加えた開口。
# ブロック（羽根込み幅 8.7）はスロット幅 6.0 を通れないため保持が効く。
PADDLE_SLOT_HW   = 3.0    # スロット半幅（タクト中心 ±3.0 → 幅 6.0）
PADDLE_SLOT_Z0   = 6.2    # スロット下端（バー下端 6.8 - 0.6）
PADDLE_SLOT_Z1   = 10.1   # スロット上端（バー上端 9.5 + 0.6）
PADDLE_SLOT_X0   = 104.0  # スロット内側端 x（壁部中心に限定し内側は壁を残す）
WIN_MERGE_GAP    = 3.0    # ボトム窓どうしの間隔がこれ未満なら連結する
                          # （窓間に残る細い歯・孤立フィンの除去、v2.1）

# --- v2.1: 階段壁の塊化 ---
STAIR_WALL     = 2.2    # 階段ランごとの公称壁厚（キャビティ＝基板+0.5 から）
# --- v2.2: 階段内側のブリッジ化（§17.11） ---
STAIR_DISK_R   = 3.25   # 階段帯の実測ソケット中心からキャビティ面までの最小距離
                        # （ドーム半径 2.75 + クリアランス 0.5。v2.3 で輪郭は
                        # outline3（矩形ステップ再構成）になったため通常は
                        # 余裕があるが、保険として残す）
# --- v2.3: 階段壁厚の上限（§17.12、本人決定で三角形の厚い壁を除去） ---
STAIR_WALL_CAP = True   # 階段帯の壁厚を STAIR_WALL 以下に制限する
CAP_STRIP_EXTRA = 2.5   # キャップを効かせる帯 = 階段ラン列のセグメントを
                        # (STAIR_WALL + この値) だけ膨らませた範囲
CAP_SCREW_KEEP = 1.5    # キャップから除外するネジ周りの余裕
                        # （タップ半径 + この値 の円盤は壁を残す）

# --- 開口（v2.2 で実物写真計測により是正、§17.11） ---
# USB: 本人確認で「タブ先端＝ケース外側端面」向き。中心 x は 7378/7379 の
# ピン列（2列）と列間のスイッチ穴列（x=93.72）から計測し両半分とも約 93.7。
# 旧値 97.0/幅10 ではコネクタ（幅 8.9、中心 93.7）が片側 2.7mm 塞がれた。
USB_XC   = 94.0         # USB開口中心 x（実測 93.7、両半分共通）
USB_W    = 13.0         # USB開口幅（x方向。プラグ胴体の逃げ込み）
USB_Z0, USB_Z1 = PCB_TOP + 2.5, PCB_TOP + 8.0
# TRRS: 細いタブの中心 y を写真計測（short はタブ穴 (107.06,64.07) と整合、
# long はタブ穴2個 y≈83.4/83.6 と整合）。旧値（外側端から 55）は
# short で約 24mm、long で約 28mm ずれていた。
TRRS_Y   = {"short": 64.5, "long": 83.5}   # TRRS開口中心 y（ケース座標、実測）
TRRS_W   = 9.0          # TRRS開口幅（y方向）
TRRS_Z0, TRRS_Z1 = PCB_TOP + 0.45, PCB_TOP + 5.85   # ジャック中心 = 基板表面+3.0

# --- アンダーグロー（v2.1 で側面バンドへ統合・廃止） ---
# v1〜v2 の「壁を薄くする帯」は、v2.1 で独立パーツの側面バンド（白）に
# 置き換えた。パラメータは下の BAND_* を参照。

# --- v2.1: 側面バンド（白フィラメント、LED 光漏れ層。本家アクリル層相当） ---
# 積層: 黒ボトムトレイ（床）→ 白バンド（z 2.5〜5.7 の外周リング）→ 基板 →
# 黒プレート → 黒フレーム。外形はフレームと同一輪郭（階段の塊化を含む）で
# 全周を一周する閉じたリングにする。
BAND_T       = 1.2    # 薄壁部の壁厚（全周）。内側を inset(BAND_T) まで広げる。
                      # 基板下面より下は中央の部品が壁に届かないため広げてよいが、
                      # 背面はパドルブロック（x<=111）との間に 2.0 以上を確保
                      # （背面内側は x≈113.0 になる）
BAND_THIN_Z1 = LEDGE_Z0   # 薄壁部は床上面〜レッジ下端（4.4）まで。レッジ帯
                      # （4.4〜5.7）はレッジ支持のため内側をキャビティ輪郭に保つ
# 位置決め: バンド下面のスカート（リング状リブ）がトレイ上面の溝にはまる
SKIRT_IN0    = 0.9    # スカート外側の inset（バンド壁 1.2 の内側に食い込ませて融合）
SKIRT_IN1    = 1.7    # スカート内側の inset（スカート幅 0.8）
SKIRT_DROP   = 0.6    # スカートの突出量（z 2.5 → 1.9）
GROOVE_IN0   = 0.75   # トレイ溝の外側 inset
GROOVE_IN1   = 1.85   # トレイ溝の内側 inset（溝幅 1.1、スカートと片側 0.15 隙間）
GROOVE_DEPTH = 0.65   # 溝深さ（z 2.5 → 1.85、スカート底と 0.05 隙間）

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
FIN_EPS_OUT = 0.5       # v2.1: 角穴（スイッチ穴）については閾値を 0.5 に拡張し、
                        # 穴〜外形間で 0.5 未満の材料（スリバー）を開口側に吸収する。
                        # 横長スロットは従来どおり FIN_EPS（背面縁の notch 化を避ける）

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

# ============================= v2.1: 階段外形の量子化 =============================
def stair_chain(outline):
    """図面外形から階段チェーン（ラン列）を検出する。
    各ランは dict(kind, a, b, fixed, out, seg)。quantize_stair（外形側）と
    bridge_stair（キャビティ側、v2.2）で同じラン列を共有する。"""
    coords = [(float(x), float(y)) for x, y in outline.exterior.coords][:-1]
    n = len(coords)

    def seglen(i):
        a, b = coords[i], coords[(i + 1) % n]
        return math.hypot(b[0] - a[0], b[1] - a[1])

    def kind_of(i):
        a, b = coords[i], coords[(i + 1) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]
        if abs(dx) >= 12 and abs(dy) <= 0.35:
            return "T"   # 踏面（x 方向の長いラン）
        if abs(dy) >= 2 and abs(dx) <= 0.35:
            return "R"   # 蹴上（y 方向のラン）
        return None

    kinds = [kind_of(i) for i in range(n)]
    # 候補ラン抽出: 同種の候補が短い非候補（アーク、合計 2.6mm まで）を
    # 挟んでも同一ランとみなす
    runs = []
    i = 0
    while i < n:
        if kinds[i] is None:
            i += 1
            continue
        kind = kinds[i]
        j = i
        gap = 0.0
        last = i
        while j + 1 < n:
            nj = j + 1
            if kinds[nj] == kind:
                j = nj; last = nj; gap = 0.0
            elif kinds[nj] is None and gap + seglen(nj) <= 2.6:
                gap += seglen(nj); j = nj
            else:
                break
        runs.append(dict(kind=kind, i0=i, i1=last))
        i = last + 1
    # ラン間ギャップ 2.6mm 以下・異種交互でチェーン化し、最長チェーンを階段とする
    def gap_between(r1, r2):
        return sum(seglen(k) for k in range(r1["i1"] + 1, r2["i0"]))
    chains = []
    for r in runs:
        if (chains and chains[-1][-1]["kind"] != r["kind"]
                and gap_between(chains[-1][-1], r) <= 2.6):
            chains[-1].append(r)
        else:
            chains.append([r])
    chain = max(chains, key=len)
    # 背面エッジ等の長い垂直セグメントが両端に連結している場合は落とす
    # （階段チェーンは踏面で始まり踏面で終わる）
    while chain and chain[0]["kind"] == "R":
        chain.pop(0)
    while chain and chain[-1]["kind"] == "R":
        chain.pop()
    if len(chain) < 7:
        raise RuntimeError(f"stair chain not found (chains: {[len(c) for c in chains]})")
    # ラン形状: コアセグメント（最長の候補セグメント）で代表させる
    for r in chain:
        segs = [(coords[k], coords[(k + 1) % n]) for k in range(r["i0"], r["i1"] + 1)]
        if r["kind"] == "T":
            core = max(segs, key=lambda s: abs(s[1][0] - s[0][0]))
            r["fixed"] = (core[0][1] + core[1][1]) / 2
        else:
            core = max(segs, key=lambda s: abs(s[1][1] - s[0][1]))
            r["fixed"] = (core[0][0] + core[1][0]) / 2
        r["a"], r["b"] = core
        mx, my = (core[0][0] + core[1][0]) / 2, (core[0][1] + core[1][1]) / 2
        # 外向き符号: ラン中点から法線方向 0.8mm の点が外形の外ならそちらが外
        if r["kind"] == "T":
            r["out"] = -1 if outline.contains(Point(mx, my + 0.8)) else 1
        else:
            r["out"] = -1 if outline.contains(Point(mx + 0.8, my)) else 1
        r["seg"] = LineString([r["a"], r["b"]])
    return chain, coords

def quantize_stair(outline, pcb, half, cav0=None):
    """階段外形を「ラン（踏面／蹴上）ごとの直線ブロック」に量子化する。

    図面外形の階段は踏面・蹴上とも R≈1 のアークでつながるギザギザで、
    内側のキャビティ（基板+0.5）との間の壁が typ. 1.6mm・最小 0.8mm の皮に
    なる（v2 の stair 解析）。そこで各ランを 1 本の直線フェイスに置き換え、
    キャビティから STAIR_WALL を確保する位置までランごとに外形を
    押し出す（ラン内は最大値で統一）。
    cav0 は壁厚の基準にするキャビティ（v2.3 では outset(pcb3, 0.5)）。
    戻り値: (new_outline, report)  report はラン別の辞書リスト。
    """
    if cav0 is None:
        cav0 = largest(outset(pcb, CAV_CLR, round_join=True))
    chain, coords = stair_chain(outline)
    n = len(coords)

    def run_push(r):
        """コアセグメント上のサンプル（両端 1.0mm のアーク帯を除く）で
        キャビティまでの距離が STAIR_WALL になる押し出し量。"""
        a, b = r["a"], r["b"]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        steps = max(2, int(L / 0.5))
        need = 0.0
        for s in range(steps + 1):
            t = s / steps
            if min(t, 1 - t) * L < 1.0:
                continue
            p = Point(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            need = max(need, STAIR_WALL - p.distance(cav0))
        return max(0.0, need)

    pushes = [run_push(r) for r in chain]
    s_pt = coords[chain[0]["i0"]]
    e_pt = coords[(chain[-1]["i1"] + 1) % n]

    def face_seg(idx, faces):
        """押し出し後のフェイスセグメント（両端は隣接フェイス／チェーン端で決まる）。"""
        r = chain[idx]
        f = faces[idx]
        if r["kind"] == "T":
            xa = faces[idx - 1] if idx > 0 else s_pt[0]
            xb = faces[idx + 1] if idx < len(chain) - 1 else e_pt[0]
            return LineString([(xa, f), (xb, f)])
        ya, yb = faces[idx - 1], faces[idx + 1]
        return LineString([(f, ya), (f, yb)])

    def face_wall(idx, faces):
        """フェイスセグメント上（両端 1.2mm の継ぎ目帯を除く）の
        キャビティまでの距離の最小値。"""
        seg = face_seg(idx, faces)
        L = seg.length
        if L <= 2.4:
            return 1e9
        dmin = 1e9
        s = 1.2
        while s < L - 1.2:
            dmin = min(dmin, seg.interpolate(s).distance(cav0))
            s += 0.4
        return dmin

    new_outline = None
    worst_d = 1e9
    for _ in range(6):
        faces = [r["fixed"] + r["out"] * p for r, p in zip(chain, pushes)]
        rects = []
        for idx, r in enumerate(chain):
            f = faces[idx]
            inner = r["fixed"] - r["out"] * 2.0   # 外形の内側へ 2.0 潜らせる
            if r["kind"] == "T":
                # v2.3: 矩形の x 範囲は隣接蹴上の「フェイス位置と図面位置の
                # 外側いっぱい」まで広げる。フェイスだけに合わせると、図面の
                # 踏面／蹴上セグメントが矩形の間に残って「湾」になり、
                # キャビティがそこから外へはみ出す（v2.2 からの既存欠陥）。
                xa = faces[idx - 1] if idx > 0 else s_pt[0]
                xb = faces[idx + 1] if idx < len(chain) - 1 else e_pt[0]
                if idx > 0:
                    xa = min(xa, chain[idx - 1]["fixed"])
                if idx < len(chain) - 1:
                    xb = max(xb, chain[idx + 1]["fixed"])
                rects.append(Polygon([(min(xa, xb), min(f, inner)), (max(xa, xb), min(f, inner)),
                                      (max(xa, xb), max(f, inner)), (min(xa, xb), max(f, inner))]))
            else:
                ya, yb = faces[idx - 1], faces[idx + 1]
                if idx > 0:
                    ya = min(ya, chain[idx - 1]["fixed"])
                if idx < len(chain) - 1:
                    yb = max(yb, chain[idx + 1]["fixed"])
                rects.append(Polygon([(min(f, inner), min(ya, yb)), (max(f, inner), min(ya, yb)),
                                      (max(f, inner), max(ya, yb)), (min(f, inner), max(ya, yb))]))
        new_outline = largest(unary_union([outline] + rects))
        # 検証: ランごとにフェイス上の壁厚を測り、不足するランだけ押し増す
        walls = [face_wall(i, faces) for i in range(len(chain))]
        worst_i = min(range(len(chain)), key=lambda i: walls[i])
        worst_d = walls[worst_i]
        if worst_d >= STAIR_WALL - 0.03:
            break
        pushes[worst_i] += (STAIR_WALL - worst_d) + 0.15
    report = []
    nt = nr = 0
    for r, p in zip(chain, pushes):
        if r["kind"] == "T":
            nt += 1; name = f"T{nt}"
        else:
            nr += 1; name = f"R{nr}"
        face = r["fixed"] + r["out"] * p
        report.append(dict(name=name, kind=r["kind"], fixed=r["fixed"], out=r["out"],
                           push=p, face=face))
        print(f"[{half}] stair {name}: {'tread y' if r['kind'] == 'T' else 'riser x'} "
              f"drawing={r['fixed']:.3f} out={r['out']:+d} push={p:.2f} -> face={face:.3f}")
    print(f"[{half}] stair quantized: worst face wall (excl. joints) = {worst_d:.3f}")
    return new_outline, report

def bridge_stair(poly, chain, disks=(), label=""):
    """階段側の輪郭をランごとの直線フェイスに寄せる（v2.2、§17.11）。

    【v2.3 で引退】v2.2 では pcb_outline2 の階段帯が内側配線グルーブを
    誤認した深い三角形の湾を含んでいた（実測ソケット中心が最大 2.52mm
    外にはみ出す）ため、その対策として入れた。v2.3 で輪郭は outline3
    （矩形ステップ再構成）に替わり、fill 矩形が隣接蹴上の円弧や窓外の
    境界点を拾ってキャビティ面を引っ張る副作用（実測で最大約1.2mm）
    の方が大きいため、キャビティ／レッジとも適用をやめた（§17.12）。
    記録のため関数だけ残す。
    """
    bnd = poly.boundary
    pts = [bnd.interpolate(s) for s in np.arange(0, bnd.length, 0.25)]
    fills = []
    worst_shift = 0.0
    for r in chain:
        a, b, out = r["a"], r["b"], r["out"]
        fixed = r["fixed"]
        if r["kind"] == "T":
            w0, w1 = min(a[0], b[0]) - 1.0, max(a[0], b[0]) + 1.0
            cand = [p.y for p in pts
                    if w0 <= p.x <= w1 and -1.0 <= (fixed - p.y) * out <= 9.0]
            if not cand:
                continue
            ext = [cy + out * STAIR_DISK_R for (cx, cy) in disks
                   if w0 - STAIR_DISK_R <= cx <= w1 + STAIR_DISK_R
                   and -1.0 <= (fixed - cy) * out <= 9.0 + STAIR_DISK_R]
            face = (max if out > 0 else min)(cand + ext)
            inner = (min if out > 0 else max)(cand)
            lo = min(face, inner - out * 1.0)
            hi = max(face, inner - out * 1.0)
            fills.append(Polygon([(w0, lo), (w1, lo), (w1, hi), (w0, hi)]))
            ref = (max if out > 0 else min)(cand)
            worst_shift = max(worst_shift, abs(face - ref))
        else:
            w0, w1 = min(a[1], b[1]) - 1.0, max(a[1], b[1]) + 1.0
            cand = [p.x for p in pts
                    if w0 <= p.y <= w1 and -1.0 <= (fixed - p.x) * out <= 9.0]
            if not cand:
                continue
            ext = [cx + out * STAIR_DISK_R for (cx, cy) in disks
                   if w0 - STAIR_DISK_R <= cy <= w1 + STAIR_DISK_R
                   and -1.0 <= (fixed - cx) * out <= 9.0 + STAIR_DISK_R]
            face = (max if out > 0 else min)(cand + ext)
            inner = (min if out > 0 else max)(cand)
            lo = min(face, inner - out * 1.0)
            hi = max(face, inner - out * 1.0)
            fills.append(Polygon([(lo, w0), (hi, w0), (hi, w1), (lo, w1)]))
            ref = (max if out > 0 else min)(cand)
            worst_shift = max(worst_shift, abs(face - ref))
    if not fills:
        return poly
    print(f"  [bridge {label}] runs={len(fills)} max face shift by disks={worst_shift:.2f}")
    return largest(unary_union([poly] + fills))

def stair_disks(half):
    """階段帯の実測ソケット中心（ドーム重心法のみ、信頼できる実測）。
    ブリッジ面の保険に使う。階段帯: short y<48 / long y>125。"""
    out = []
    for row in csv.DictReader(open(f"{BASE}/template/pcb_sockets.csv")):
        if row["half"] != half or row["method"] != "dome_centroid":
            continue
        if row["kind"] not in ("square", "tall"):
            continue
        x, y = float(row["meas_x_mm"]), float(row["meas_y_mm"])
        if (half == "short" and y < 48.0) or (half == "long" and y > 125.0):
            out.append((x, y))
    return out

def stair_strip(chain, outline):
    """壁厚キャップを効かせる帯: 階段ラン列の全セグメントを
    (STAIR_WALL + CAP_STRIP_EXTRA) だけ膨らませ、外形と交差させた範囲。
    背面リム（ネジ帯域）には届かないようラン列基準で限定する。"""
    segs = [r["seg"] for r in chain]
    buf = unary_union([s.buffer(STAIR_WALL + CAP_STRIP_EXTRA) for s in segs])
    return largest(buf.intersection(outline))

halves = {}
for half in ("short", "long"):
    outline_dxf = shp(loc(dxf["OUTLINE"][IDX[half]]["pts"], half)).simplify(SIMPLIFY)
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
    pcb_pts = np.loadtxt(f"{BASE}/template/pcb_outline3_{half}.csv", delimiter=",", skiprows=1)
    pcb = shp([tuple(r) for r in pcb_pts])
    # v2.3: キャビティは outset(pcb3, 0.5) そのもの（§17.12）。
    # v2.2 の bridge_stair は outline2 の幻影対策だったが、矩形ステップの
    # outline3 に対しては fill 矩形が隣接蹴上の円弧や窓外の点を拾って
    # キャビティ面を最大約1.2mm引っ張る副作用の方が大きいため引退させた。
    # ソケット円盤の保険は check_v21 §8 で検証する（全ソケット中心が
    # 輪郭内側にドーム+1.33mm以上で収まることは OUTLINE3_NOTES で確認済み）。
    chain, _chain_coords = stair_chain(outline_dxf)
    cavity_q = largest(outset(pcb, CAV_CLR, round_join=True))
    # v2.1: 階段外形をランごとのブロックに量子化（§17.3）。図面外形は
    # outline_dxf として保持し、下流は量子化後の outline を使う。
    outline, stair_report = quantize_stair(outline_dxf, pcb, half, cav0=cavity_q)
    halves[half] = dict(outline=outline, outline_dxf=outline_dxf, pocket=pocket,
                        sw=sw_holes, slots=slots, pcb=pcb, stair=stair_report,
                        chain=chain, cavity_q=cavity_q)
    print(f"[{half}] outline area={outline.area:.0f} (dxf {outline_dxf.area:.0f}) "
          f"pocket area={pocket.area:.0f} "
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

def merge_close(spans, gap_max):
    """間隔が gap_max 未満の区間を連結する（窓間の細い歯・孤立フィン除去用）。"""
    out = []
    for a, b in sorted(spans):
        if out and a - out[-1][1] < gap_max:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out

for half in ("short", "long"):
    halves[half]["paddle_spans"] = merged_spans(half)
    # v2.1: ボトム窓専用に gap < WIN_MERGE_GAP の窓間を連結した区間も持つ
    halves[half]["paddle_spans_bot"] = merge_close(halves[half]["paddle_spans"], WIN_MERGE_GAP)
    print(f"[{half}] paddle spans: {[(round(a,1), round(b,1)) for a,b in halves[half]['paddle_spans']]} "
          f"bottom windows: {[(round(a,1), round(b,1)) for a,b in halves[half]['paddle_spans_bot']]}")

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

def ring_prism(poly_outer, poly_inner, z0, z1):
    """輪郭2つに挟まれたリング状プリズム（スカート・溝用）。
    内側プリズムは z を少しはみ出させて切り口をきれいにする。"""
    return prism(poly_outer, z0, z1) - prism(poly_inner, z0 - 0.05, z1 + 0.05)

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
    trrs_y = TRRS_Y[half]

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
    # v2.3: キャビティは cavity_q（= outset(pcb3, 0.5)、§17.12）を
    # 最小壁厚でクリップしたものを正とする。
    cavity = largest(H["cavity_q"].intersection(inset(outline, MIN_WALL)))
    # フレーム下帯専用のキャビティ（MIN_WALL クリップなし）。
    # クリップ付き cavity は背面タブ先端など基板が外形に迫る箇所で基板側へ
    # 食い込み、フレームと基板が干渉する（v2.1 初回チェックで 78.7mm3）。
    # フレーム側は壁が消える箇所が出ても干渉ゼロを優先する（ボトム側は
    # 従来どおりクリップ付き cavity で最小壁 0.8 を守る）。
    cavity_full = H["cavity_q"]
    H["cavity_full"] = cavity_full
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

    # ---------- v2.3: 階段壁厚キャップ（§17.12、本人決定） ----------
    # 階段帯では「外形から STAIR_WALL より深い領域」をキャビティへ和集合
    # し、壁厚を STAIR_WALL 以下に制限する（段差の形に沿って概ね均一な
    # 壁にし、三角形の厚い壁を消す）。キャビティを広げる方向のみの変更
    # なので基板クリアランス（基板+0.5）は割らない。ネジ周りは保持
    # 円盤で除外し、タップ穴の肉を残す。
    if STAIR_WALL_CAP:
        strip = stair_strip(H["chain"], outline)
        deep = inset(outline, STAIR_WALL).intersection(strip)
        keeps = [Point(e["x"], e["y"]).buffer(
                     BACK_SCREW_SPECS[e["size"]]["tap"] / 2 + CAP_SCREW_KEEP)
                 for e in back_screws]
        keeps += [Point(e["x"], e["y"]).buffer(
                      HANG_TAP_DIA / 2 + CAP_SCREW_KEEP) for e in hangs]
        if keeps:
            deep = deep.difference(unary_union(keeps))
        if not deep.is_empty and deep.area > 0:
            cavity_full = largest(unary_union([cavity_full, deep]))
            cavity = largest(unary_union([cavity, deep])
                             .intersection(inset(outline, MIN_WALL)))
            H["cavity_full"], H["cavity"] = cavity_full, cavity
            print(f"[{half}] stair wall cap: deep area={deep.area:.1f} mm2 "
                  f"merged into cavity (stair wall <= {STAIR_WALL} mm)")
    # 吊りボス用の耳をプレート外周へ追加し、最終外周を確定
    ears = [Point(e["x"], e["y"]).buffer(HANG_DIA / 2 + 1.5) for e in hangs if e.get("ear")]
    if ears:
        plate_bnd = largest(unary_union([plate_bnd] + ears))
    H["plate_bnd"] = plate_bnd
    xmax = outline.bounds[2]
    ymax = outline.bounds[3]
    trrs_y = TRRS_Y[half]

    # ---------- スイッチプレート（別体） ----------
    sq_polys = [square_poly(s["cx"], s["cy"], SW_HOLE_MODEL) for s in H["sw"]]
    hole_polys = sq_polys + list(H["slots"])
    # フィン取り込み: 角穴は閾値 FIN_EPS_OUT=0.5（v2.1 で外形側にも拡張）、
    # 横長スロットは従来どおり FIN_EPS=0.15。削り方は穴の全周バッファとする。
    # 帯限定（穴∧外周の重なりだけ削る）も試したが、階段側の縁ストリップは
    # 穴カットだけでも首部 0.5 未満で分離してしまう（無修正でも最終
    # フットプリントが複数成分になることを確認済み）ため、一体に保てない
    # ストリップは notch として開口側へ吸収するのが唯一の一貫した解になる。
    fin_parts = [hp.buffer(FIN_EPS_OUT) for hp in sq_polys
                 if hp.boundary.distance(plate_bnd.boundary) < FIN_EPS_OUT]
    fin_parts += [hp.buffer(FIN_EPS) for hp in H["slots"]
                  if hp.boundary.distance(plate_bnd.boundary) < FIN_EPS]
    plate_bnd_p = plate_bnd
    if fin_parts:
        moat = unary_union(fin_parts)
        plate_bnd_p = shp(ring_pts(largest(plate_bnd.difference(moat))))
        print(f"[{half}] plate fin-fix: {len(fin_parts)} hole(s) near outline, "
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
    # v2.1: 下帯（基板下面〜プレート下面）の内壁はキャビティ輪郭に合わせる。
    # v2 ではプレート帯域（plate_bnd+0.25）が内壁で、キャビティ（基板+0.5）
    # より内側に入る箇所があり基板と約1,559mm3 干渉した（背面帯で最大 6.2mm）。
    # 使う輪郭はクリップなしの基板+0.5（cavity_full）で、基板との干渉を
    # 完全になくす。プレート帯（PLATE_BOT〜PLATE_TOP）だけ従来の ch を使い、
    # 境界は 0.05 重ねる。
    frame = (prism(outline, PCB_BOT, FRAME_TOP)
             - prism(cavity_full, PCB_BOT - 0.1, PLATE_BOT + 0.05)
             - prism(ch, PLATE_BOT - 0.05, PLATE_TOP)
             - prism(well, PLATE_TOP, FRAME_TOP + 0.1))
    # 背面締結のタッピング穴（サイズ別）
    for e in back_screws:
        spec = BACK_SCREW_SPECS[e["size"]]
        frame = frame - cyl(e["x"], e["y"], PCB_BOT - 0.1, spec["tap"], spec["tap_depth"] + 0.1)
    # v2.1: パドル通路はタクト別の横スロットにする（完成形 7354 準拠）。
    # 幅は中心 ±3.0、高さは配置B のバー（z 6.8〜9.5）+ 上下 0.6 で z 6.2〜10.1、
    # x は内側端を 104 に留めて壁部中心に限定する。上壁（10.1〜16.1）・下壁・
    # タクト間の歯が残るため、ブロック（幅 8.7）はスロット（幅 6.0）から
    # 抜けず保持が効く。v2 の帯全高開放は廃止。
    for tc in TACT_CENTERS[half]:
        frame = frame - box(PADDLE_SLOT_X0, xmax + 1, tc - PADDLE_SLOT_HW, tc + PADDLE_SLOT_HW,
                            PADDLE_SLOT_Z0, PADDLE_SLOT_Z1)
    # USB開口（外側端の壁）
    if half == "short":
        frame = frame - box(USB_XC - USB_W / 2, USB_XC + USB_W / 2, ymax - 1, ymax + 2, USB_Z0, USB_Z1)
    else:
        frame = frame - box(USB_XC - USB_W / 2, USB_XC + USB_W / 2, -2, 1, USB_Z0, USB_Z1)
    # TRRS開口（背面壁）
    frame = frame - box(xmax - 6.5, xmax + 1, trrs_y - TRRS_W / 2, trrs_y + TRRS_W / 2, TRRS_Z0, TRRS_Z1)

    # ---------- ネジ一覧（トレイ・バンド共通） ----------
    all_screws = [(e["x"], e["y"], BACK_SCREW_SPECS[e["size"]]) for e in back_screws]
    all_screws += [(e["x"], e["y"], BACK_SCREW_SPECS["M3"]) for e in hangs]

    # ---------- ボトムトレイ（黒、浅いトレイ: 床＋内側の造形） ----------
    tray = prism(outline, 0, FLOOR_T)
    # 位置決め溝（バンド下面のスカートを受ける、全周）
    tray = tray - ring_prism(inset(outline, GROOVE_IN0), inset(outline, GROOVE_IN1),
                             FLOOR_T - GROOVE_DEPTH, FLOOR_T + 0.05)
    # パドル窓の床部分（バンド側と共通の帯を抜く）
    for (sy0, sy1) in H["paddle_spans_bot"]:
        tray = tray - box(PADDLE_WIN_X0, xmax + 1, sy0, sy1, -0.1, FLOOR_T + 0.1)
    # ネジ通し穴＋頭ザグリ（床の分。バンド帯域の逃げはバンド側で切る）
    for (sx, sy, spec) in all_screws:
        tray = tray - cyl(sx, sy, -0.1, spec["clr"], FLOOR_T + 0.2)
        tray = tray - cyl(sx, sy, -0.1, spec["cb"], CB_DEPTH + 0.1)
    # ゴム足逃げ
    for (fx, fy, _) in all_screws:
        tray = tray - cyl(fx, fy, -0.1, 11.0, 1.0)
    for (fx, fy) in FEET_EXTRA[half]:
        tray = tray - cyl(fx, fy, -0.1, 11.0, 1.0)

    # ---------- 側面バンド（白、z 2.5〜5.7 の全周リング） ----------
    band = prism(outline, FLOOR_T, PCB_BOT)
    # 薄壁部（光漏れ、全周）: 床上面〜レッジ下端は内側を inset(BAND_T) まで広げる
    band = band - prism(inset(outline, BAND_T), FLOOR_T - 0.1, BAND_THIN_Z1)
    # レッジ帯（4.4〜5.7）: 内側はキャビティ輪郭（レッジを支える壁を残す）
    band = band - prism(cavity, BAND_THIN_Z1, PCB_BOT + 0.1)
    # 基板支持レッジ（キャビティ壁から基板縁の下へ LEDGE_UNDER 潜る帯。
    # 外周はキャビティ壁の外へ食い込ませて融合させる。従来はボトム側だった）
    # v2.2 ではレッジ内側もブリッジ化したが、v2.3 では outline3 の
    # 矩形ステップにより inset そのままで直線フェイスになる（§17.12）。
    ledge_in_q = inset(pcb, LEDGE_UNDER)
    H["ledge_in_q"] = ledge_in_q
    ledge = (prism(outset(cavity, LEDGE_EMBED, round_join=True), LEDGE_Z0, PCB_BOT)
             - prism(ledge_in_q, LEDGE_Z0 - 0.1, PCB_BOT + 0.1))
    band = band + ledge
    # 位置決めスカート（下面のリング状リブ、トレイの溝にはまる）
    band = band + ring_prism(inset(outline, SKIRT_IN0), inset(outline, SKIRT_IN1),
                             FLOOR_T - SKIRT_DROP, FLOOR_T + 0.3)
    # パドル窓（トレイと共通の帯。スカートもろとも抜く）
    for (sy0, sy1) in H["paddle_spans_bot"]:
        band = band - box(PADDLE_WIN_X0, xmax + 1, sy0, sy1,
                          FLOOR_T - SKIRT_DROP - 0.1, PCB_BOT + 0.1)
    # 背面ネジの逃げ（バンド帯域分。吊りボス用ネジは内側の空間を通るので不要）
    for e in back_screws:
        spec = BACK_SCREW_SPECS[e["size"]]
        band = band - cyl(e["x"], e["y"], FLOOR_T - SKIRT_DROP - 0.1,
                          spec["clr"], PCB_BOT - FLOOR_T + SKIRT_DROP + 0.2)
    # v2.1: パドル窓端フィン対策。窓端と背面ネジの間では、壁（外形−キャビティ）
    # とレッジが「窓／基板タブ角／ネジ穴」に囲まれたポケットに残片として
    # 取り残され、最薄約0.1mm のフィンになる（short: 窓端 y=126.65 と
    # M3 (110.24,129) の間、実測 x 105.5〜108.7 / y 126.7〜129.1 / z 3.5〜5.3）。
    # 対策はポケットの広さで分ける:
    #   - 壁領域が広い場合（long の窓始端側など）は、壁領域の範囲内で
    #     床上面〜壁天端まで埋め直すウェブで一体化させる。
    #   - 壁領域が 5mm2 未満までピンチしている場合はウェブでは届かないため、
    #     フィンごと切り取る（窓の開口が壁側に最大で約 3mm 延びるだけで、
    #     パドル羽根の到達範囲の外なので機能影響はない）。
    # ネジ通し穴からはウェブ側で clr/2 + 0.9 を確保する。
    wall2d = outline.difference(cavity)
    for e in back_screws:
        spec = BACK_SCREW_SPECS[e["size"]]
        keep = Point(e["x"], e["y"]).buffer(spec["clr"] / 2 + 0.9)
        for (a, b) in H["paddle_spans_bot"]:
            for end in (a, b):
                if abs(e["y"] - end) > 6.0:
                    continue
                sgn = 1 if e["y"] > end else -1
                wy0, wy1 = (end, e["y"] + 2.8) if sgn > 0 else (e["y"] - 2.8, end)
                rect = Polygon([(104.5, wy0), (e["x"] + 3.0, wy0),
                                (e["x"] + 3.0, wy1), (104.5, wy1)])
                web = rect.intersection(wall2d).difference(keep)
                if web.area < 5.0:
                    # 到達範囲はネジ中心 ±1.35: ノッチ角ではスカート（バンド
                    # 下面のリブ）のアーク部がこの切り取りで孤立残片になる
                    # ため、残片（実測で +0.75 では y 130.03 まで残った）ごと除く
                    cy0, cy1 = (end - 0.1, e["y"] + 1.35) if sgn > 0 else (e["y"] - 1.35, end + 0.1)
                    crect = Polygon([(104.5, cy0), (e["x"] + 0.3, cy0),
                                     (e["x"] + 0.3, cy1), (104.5, cy1)])
                    band = band - prism(crect, FLOOR_T - SKIRT_DROP - 0.1, PCB_BOT + 0.05)
                    print(f"[{half}] fin cut: screw ({e['x']:.2f},{e['y']:.0f}) "
                          f"span end {end:.2f} (web area {web.area:.1f} < 5)")
                else:
                    geoms = [web] if web.geom_type == "Polygon" else list(getattr(web, "geoms", []))
                    for g in geoms:
                        if g.area > 1.0:
                            band = band + prism(g, FLOOR_T, PCB_BOT)
                            print(f"[{half}] fin web: screw ({e['x']:.2f},{e['y']:.0f}) "
                                  f"span end {end:.2f} area={g.area:.1f}")

    return dict(plate=plate, frame=frame, tray=tray, band=band)

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

results = {}
for half in ("short", "long"):
    print(f"===== build {half} =====")
    parts = build_half(half)
    results[half] = parts
    export(parts["plate"], f"switch_plate_{half}")
    export(parts["frame"], f"top_frame_{half}")
    export(parts["tray"], f"bottom_tray_{half}")
    export(parts["band"], f"side_band_{half}")

# ============================= 試作片（1回の印刷セッションに集約） =============================
# 方針（v2.1 後半の本人指示）: 試作回数を最小化する。必須の確認だけを
# A1 mini のベッドに同時配置できる小片セットにする（全9片）:
#   - プレート穴のパチ留め: trial_plate_holes（小片1枚）
#   - 階段の当たり: trial_stair_band_<half>（バンドのクリップ。バンドは
#     基板を受けるレッジと階段外形の両方を持つので、これで当たりが分かる。
#     トレイは基板に触れないため不要、フレーム側は仮想検証で干渉0を確認済み）
#   - パドルスロット: trial_corner_{tray,band,frame}_<half>（両半分。
#     手で重ねてパドルの挿入・保持・タクト逃げを見る。long はタクト1の
#     ブロック角が仮想で壁に近いため特に確認対象）
# ネジまわりの試作片（旧 trial_screw）は、ネジ経路を仮想検証で確認する
# ことにして廃止した。積層クリップ（旧 trial_compose）も廃止し、
# 全てパーツ別クリップとする。

# 1) 階段境界（両半分）: バンドだけを切り出す
for half, yr in (("short", (-3, 50)), ("long", (127.2, 180.2))):
    export(clip(results[half]["band"], (-3, 117.3), yr), f"trial_stair_band_{half}")

# 2) 背面-外側角（両半分）: トレイ／バンド／フレームを別々に切り出す
for half, yr in (("short", (80, 146.4)), ("long", (-3, 50))):
    P = results[half]
    for pname in ("tray", "band", "frame"):
        export(clip(P[pname], (80, 117.3), yr), f"trial_corner_{pname}_{half}")

# 3) プレート穴のパチ留め確認片: 実寸の穴 2x2（ピッチ 19.05）だけの小片。
#    厚みは実プレートと同じ 1.5。スイッチを差して保持されるかだけを見る。
tp = box(0, 47.6, 0, 38.1, 0, PLATE_T)
for hx in (14.275, 33.325):
    for hy in (9.525, 28.575):
        sq = square_poly(hx, hy, SW_HOLE_MODEL)
        tp = tp - prism(sq, -0.2, PLATE_T + 0.2)
export(tp, "trial_plate_holes")

print("DONE")
