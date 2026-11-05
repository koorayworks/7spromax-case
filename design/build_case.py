# -*- coding: utf-8 -*-
"""
7sProMax 3Dプリントケース 立体設計 v2.4

v2.4 の要点（詳細は DESIGN_NOTES §17.13、根拠は DOCKING_STUDY 案2）:
  - 左右ドッキング（一体型風連結）を実装した。磁石は入れない（本人
    指示）。両半分の階段フェイスを、基板テッセレーション由来の1本の
    共有シームカーブ上に再設計した: 踏面は基板レベル ±2.7（= キャビティ
    0.5 + 壁 2.2）で統一し、蹴上は基板の共有境界 x（26.6/46.2/65.2/
    84.4）に一致させた。ドッキング位置（隙間 0.30）では主階段の継ぎ目
    隙間が均一 0.30mm、全体幅は約 301.1mm になる。
  - 背面ラン（x>=84.4、段5+6 統合）は例外: long はフレームのウェル
    制約のため現行（v2.3 量子化）フェイス 177.222 を残し、short は
    段5の統一フェイス 21.76 を 2.0mm 延長した 19.76 に合わせてある。
  - 変更は外形の階段帯のみ。キャビティ（outline3+0.5）・パドル・
    開口・ネジ計画など v2.3 の成立条件は変えていない。

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

# --- v2.4.1: プレート階段縁のブリッジ（§17.14、本人目視指摘） ---
PLATE_BRIDGE       = True
PLATE_BRIDGE_CLR   = 0.2   # 階段側の上限: フレーム下帯内壁（cavity_full）
                           # から最低この隙間を残す範囲まで広げてよい
PLATE_BRIDGE_GUARD = 0.5   # ケース外形の内側に収めるための最小ガード
                           # （階段側の実質的な上限は cavity_full 側で決まる）
PLATE_BRIDGE_STRIP = 15.0  # 基板階段プロファイルからこの距離の帯の中だけで
                           # ブリッジを効かせる（階段側以外は変えない）

# --- スイッチプレート穴（v2 で変更） ---
SW_HOLE        = 14.0   # MX プレートパチ留め標準（mm角）
SW_HOLE_FDM    = 0.15   # FDM 印刷補正（穴は小さく出るためモデル側で拡大）
SW_HOLE_MODEL  = SW_HOLE + SW_HOLE_FDM   # 14.15mm角でモデリングする

# --- パドル（エクストラスイッチ）まわり: 実測エンベロープで作り直し ---
# 実測（PADDLE_MEASUREMENTS、2026-11-05 ノギス実測が正）: 全長 25.2 /
# ブロック高さ 8.6 / バー厚 2.8 / バー幅 4.8。羽根込み幅は 7455 の
# 注記では 8.2 だが旧推定 8.7 との食い違いが残るため、窓寸法は
# 大きい方（8.7）を安全側として使う（§17.18）。
PADDLE_WING_W  = 8.7    # 羽根込み幅（設計用: 実測 8.2 と旧推定 8.7 の大きい方）
PADDLE_CLR     = 1.05   # 羽根に対する片側クリアランス → 窓幅 10.8
                        # （v2.4.4/§17.18: タクト中心の実測精度 ±1〜2mm に
                        # 対し従来の 0.6 では不足するため拡大）
PADDLE_WIN_X0  = 97.0   # 窓の x 開始（背面側）。ブロック占有 x≈101..111 に余裕を持たせた値
TACT_CENTERS   = {      # タクト中心 y（ケース座標）
    # v2.4.4 (§17.18): 本人の実物写真注記で是正。long は写真 7464 の
    # 注記チェーン（ピン線 83.5 −6.2→ 77.3 −36.6→ 40.7 −29.5→ 11.2、
    # 端面 5.11 から 9.8 → 最寄り中心 14.91）と画素計測で
    # [15.0, 24.5, 34.0]（間隔 9.5）。short は本人明示「位置関係は
    # ロング側と一緒」を鏡像適用し、写真 7466 の 10mm 注記
    # （SW1 中心 128.45 → 外側端面 138.45）と SW64 の列一致から
    # [109.5, 119.0, 128.5]。旧 §8 値は short で約 7mm の系統ずれ。
    "short": [109.5, 119.0, 128.5],
    "long":  [15.0, 24.5, 34.0],
}
# --- v2.1: フレームのパドルスロット（完成形 7354 準拠の横スロット） ---
# 配置Bのバー（z 6.8〜9.5、幅 4.8）に上下 0.6 のクリアランスを加えた開口。
# ブロック（羽根込み幅 8.7）はスロット幅 6.0 を通れないため保持が効く。
# v2.4.4 (§17.18): 実物で「全然はまらない」となり、当初はスロット
# 余裕不足とみて y ±3.6（幅 7.2）、z 5.7〜10.6 に拡大した。その後の
# 本人確認で、根本原因は高さ方向の前提違い（タクトは基板上面・
# ボタン上向きで上面 z≈12.5、パドル側の要求位置と約 3.4〜4.2mm
# 不一致）と判明し、本人決定で金属パドル自体を使わないことになった。
# スロット／窓は今ラウンドでは残置する（次ラウンドのプランジャ
# 実装時に壁へ戻し、タクト中心位置にプランジャ穴を開ける。§17.18）。
PADDLE_SLOT_HW   = 3.6    # スロット半幅（タクト中心 ±3.6 → 幅 7.2）
PADDLE_SLOT_Z0   = 5.7    # スロット下端（= PCB_BOT、フレーム下端まで開放）
# v2.4.4 (§17.18): タクト実体ボックス（上面 z 7.3〜12.5）との干渉
# 実測で、フレーム側はスロット上端より上の材料（z 10.6〜12.5）が
# 約 33〜38mm3 当たることが判明した。タクトの逃げとして上端を
# 13.2（先端 12.5 + 0.7）まで上げ、内側端も 102.0 に広げる。
# この逃げは次ラウンドのプランジャ穴の土台になる。
PADDLE_SLOT_Z1   = 13.2   # スロット上端（タクト先端 12.5 + 逃げ 0.7）
PADDLE_SLOT_X0   = 102.0  # スロット内側端 x

# --- v2.4.5: プランジャ（小ボタン）§17.19 ---
# §17.18 の推奨案 (A) を実装する。タクト中心の x は未実測のため、
# §17.18 のタクト実体ボックス（x 103.5〜109.5、check_paddle_real と
# 共通）の中心を最善推定として使う（実体は約 5mm 幅でボックス内に
# 収まるとされ、中心のずれは ±1mm 級の見込み。受け側の余裕は下記）。
TACT_X           = 106.5  # タクト中心 x（推定。実物確認は試作で本人）
# フレーム側の受け（タクト中心に同軸）:
PLUNGER_HOLE_D   = 5.4    # ガイド穴径（軸 Ø4.6 に片側 0.4 逃げ、§17.18）
PLUNGER_CB_D     = 8.6    # キャップ座ぐり径（キャップ Ø8 に片側 0.3）。
                          # §17.18 の Ø9 級（座ぐり 9.6）はタクト間隔
                          # 9.5 と同等で座ぐり間にウェブが残らないため、
                          # 間隔内に収まる径へ縮小した（座ぐり間に
                          # 0.9 のウェブが残る）。なお屋根の分離問題は
                          # 座ぐりでなくガイド穴が原因（連結帯の項）
PLUNGER_CB_FLOOR = 14.1   # 座ぐり床 z（天面 16.1 から深さ 2.0）
PLUNGER_GUIDE_Z0 = 12.9   # ガイド穴カットの下端（スロット上面 13.2 の
                          # 少し下から切り、貫通を確実にする）
# プランジャ本体（組立座標の z。静止時）:
#   キャップ  z[15.2, 17.2]（天面から +1.1 出る。§17.18 の +1 目標）
#   軸        z[12.9, 15.2]（Ø4.6、長さ 2.3）
#   フランジ  z[11.9, 12.9]（Ø7、厚 1.0。ガイド穴 Ø5.4 より大きく
#             抜け止め。天井（スロット上面 13.2）まで 0.3 の遊び）
#   受け凹み  フランジ下面から深さ 0.9（天井 z=12.8、Ø4.0）。
#             タクト先端（z 12.5、Ø2 級・推定）を呑み、接触面と
#             先端の静止間隔 0.3 を確保する。先端が凹み中心から
#             ±1.0 ずれても凹みに入る。
# 押下ストローク: 静止間隔 0.3 + 作動 0.5 + オーバートラベル 0.3
#   = 1.1 でキャップ下面が座ぐり床に当たりストッパが効く
#   （スイッチ側のオーバートラベル予算 0.5 を使い切る前に止まる）。
#   フランジ下面とスイッチ本体上面（z≈10.6）の間隔は静止 1.3 で、
#   ストッパ（1.1）が先に効く。
PLUNGER_CAP_D    = 8.0    # §17.18 の Ø9 から縮小（座ぐり Ø8.6 と対。
                          # 間隔 9.5 内に収めるため、上の座ぐりの項参照）
PLUNGER_CAP_T    = 2.0    # §17.18 は厚 3 だったが、ストッパ位置
                          # （床 14.1）と上面 +1.1 を両立させるため 2.0
PLUNGER_SHAFT_D  = 4.6
PLUNGER_SHAFT_L  = 2.3
PLUNGER_FLANGE_D = 7.0
PLUNGER_FLANGE_T = 1.0
PLUNGER_RECESS_D = 4.0
PLUNGER_RECESS_DEPTH = 0.9
PLUNGER_TOTAL_H  = (PLUNGER_CAP_T + PLUNGER_SHAFT_L
                    + PLUNGER_FLANGE_T)   # 5.3（印刷時の全高）
# フレーム屋根の連結帯（§17.19）: 屋根ブロック（タクト上の屋根）は
# 外形の段差コーナー（タブ付け根、x≈106.25）で細く括れており、
# ガイド穴 Ø5.4 がその括れを断ち切って屋根が島になる（切り分け:
# ガイド穴のみで 3 ソリッド化、座ぐりのみでは 1 ソリッド）。
# 対策として、屋根の内側縁（キャビティ縁 x≈104.5）に沿って
# x[102.0, 104.6] × z[13.2, 16.1] の帯をタクト列の前後に渡し、
# 穴（内側端 103.8）と座ぐり（同 102.2）の下層 z[13.2, 14.1] に
# 幅 1.8 の連結糸を残す。帯は天面開口の背面側に 1.7mm 張り出す
# 唇状になる（タクト先端との間隔はスロット上面と同じ 0.7）。
PLUNGER_STRIP_X0 = 102.0  # 連結帯の内側面 x
PLUNGER_STRIP_X1 = 104.6  # 連結帯の背面側面 x（キャビティ縁 104.5 へ重ねる）
PLUNGER_STRIP_YM = 6.0    # 帯の y 余長（タクト列の両端から）
WIN_MERGE_GAP    = 3.0    # ボトム窓どうしの間隔がこれ未満なら連結する
                          # （窓間に残る細い歯・孤立フィンの除去、v2.1）

# --- v2.1: 階段壁の塊化 ---
STAIR_WALL     = 2.2    # 階段ランごとの公称壁厚（キャビティ＝基板+0.5 から）
# --- v2.2: 階段内側のブリッジ化（§17.11） ---
STAIR_DISK_R   = 3.25   # 階段帯の実測ソケット中心からキャビティ面までの最小距離
                        # （ドーム半径 2.75 + クリアランス 0.5。v2.3 で輪郭は
                        # outline3（矩形ステップ再構成）になったため通常は
                        # 余裕があるが、保険として残す）
# --- v2.4: 左右ドッキングのシーム整形（§17.13、DOCKING_STUDY 案2） ---
SEAM_PROJ       = CAV_CLR + STAIR_WALL  # 2.7: 踏面の張り出し（基板→ケースフェイス）
SEAM_BACK_EXT   = 2.0   # 背面ランで short 側フェイスを延長する量（long は現行維持）
SEAM_STRIP_X    = (3.2, 113.7)  # シーム整形を効かせる x 範囲（outline3 の置換帯と同じ）
SEAM_FILL_DEPTH = 12.0  # 整形フィル矩形が外形内側へ潜る深さ

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
# v2.4.4 (§17.18): 本人確定でマイコンは裏面実装（ソケットのある
# 裏面側にヘッダで接続）。使うのは RP2040 の ProMicro 互換ボード
# （33×18mm 級、基板厚 1.6 級、USB-C）で実物は未入手のため標準
# 寸法ベース。ヘッダ／ソケット高さは 2.5 か 3mm か未確定（本人
# 保留中）→ 3mm の方でも収まる余裕で仮設計する（推定扱い）。
# スタック（基板裏 5.7 から下向き）: ヘッダ 3.0 ならモジュール
# 基板 z[1.1, 2.7]、2.5 なら z[1.6, 3.2]。コネクタ（ミッドマウント
# 前提）の中心は基板中心付近で z 1.5〜2.8、レセプタクル半高
# 約 1.6 → 上端最大 約 4.4。よって開口は z 0〜4.5 とし、フレーム
# （旧 z 9.8〜15.3、スイッチ側実装前提で誤り）からトレイ＋バンド
# の端壁へ移す。フレーム側の旧開口とプラグポケットは廃止（壁に
# 戻す）。プラグの金属シェル（Type-C 8.4×2.6 等）はコネクタ面
# まで約 4.4mm の壁厚をシェル長（約 6.5）で届くため、外面
# ポケットは設けない。
USB_Z0, USB_Z1 = 0.0, 4.5   # 新開口の z 帯（トレイ全高＋バンド下部）
USB_CUT_IN   = 6.5      # 開口カットの内側への食い込み（外面基準、壁厚約4.4＋余裕）
# マイコン裏面実装の逃げ（トレイ床のポケット）: モジュール占有は
# x 85〜103 / 端から約 33mm。モジュール基板下面はヘッダ 3.0 で
# z=1.1、2.5 で z=1.6 となり床上面 (2.5) と干渉するため、床を
# 0.3 まで彫る（基板下面との間隔 0.8〜1.3）。コネクタ帯（端寄り
# 13mm）はコネクタ下面（最悪で z 0 付近〜僅かに下）まで逃げる
# よう床を貫通させる。
MCU_POCKET_X0, MCU_POCKET_X1 = 83.0, 105.0   # ポケット x 範囲
MCU_POCKET_LEN = 38.0   # ポケットの端からの長さ（y方向）
MCU_POCKET_FLOOR = 0.3  # ポケット床の残し厚
MCU_DEEP_LEN   = 13.0   # 端寄りの貫通帯の長さ（コネクタ逃げ）
# TRRS: v2.4.4 (§17.18) で本人の実物写真注記により再是正。旧値は
# ジャックのピン列（はんだピン位置）であって軸ではなかった。
# long: 写真 7465 の 91.2（階段端 171.6 から中心まで）＋画素計測
# （中心 y≈80.1）で軸 80.3。short: 写真 7466 の 33.6 は SW25 穴
# 左端 (30.38) → ピン線 (63.98、スキャン穴 64.07 と一致) で、
# 軸はピン線から外側端方向へ long と同じ +3.1 → 67.2。
TRRS_Y   = {"short": 67.2, "long": 80.3}   # TRRS開口中心 y（ケース座標、実測）
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
# 背面ネジ同士の最小中心間隔（v2.4.2 §17.15）。背面の直線化で slack が
# 帯域境界の両側で同点タイになると、隣接帯域が境界付近に寄って
# ボス同士が重なる配置を選んでしまうため、既配置から離れた候補を優先する。
BACK_SCREW_MIN_SEP = 12.0
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
FIN_RESTORE_TOL = 0.05  # v2.4.3: fin-fix 復元の判定許容差（§17.16）。fin-fix 前の
                        # フットプリントで中心走査の開口が設計値 ±この値に収まる
                        # 角穴は「全周に壁があった穴」とみなし、堀で断たれた壁を
                        # 戻して開口を設計値に復元する。もともと縁に開いた notch
                        # （開口が設計値より大きい穴）は対象外。

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

# ============================= v2.4: 階段フェイスのシーム整形 =============================
import sys as _sys
_sys.path.insert(0, f"{BASE}/template")
from make_outline3 import STEPS as PCB_STEPS, XB as PCB_XB

def seam_stair(outline_q, pcb, half):
    """階段フェイスを左右共有のシームカーブ上に再設計する（§17.13、案2）。

    入力は v2.3 の量子化済み外形（outline_q）。階段帯（x 3.2〜113.7）の
    輪郭だけを、基板ステップ（pcb_outline3 の STEPS が正本）から作る
    階段状プロファイルで置き換える:
      - 踏面フェイス = 基板レベル ∓ SEAM_PROJ（2.7 = キャビティ 0.5 + 壁 2.2）
      - 蹴上フェイス = 基板の共有境界 x（26.6/46.2/65.2/84.4、両半分で同一）
    これにより、両半分を寄せたとき主階段（x 26.6〜84.4）の継ぎ目隙間が
    均一になる（基板同士のテッセレーションがそのままケースに写る）。
    背面ラン（x>=84.4、段5+6 は現行どおり1ラン）だけは例外扱い:
      - long: フレームのウェル（ポケット+0.25）が現行フェイス 177.222 を
        既に超えている（リムが開いている）ため、フェイスを現行維持する
        （プロファイル整形は x<84.4 で打ち切り、背面ランには触れない）。
      - short: 段5の統一フェイス（24.46-2.7=21.76、現行 T1 と一致）を
        SEAM_BACK_EXT=2.0 だけ延長した 19.76 にし、long の現行フェイス
        との隙間もドッキング位置で約 0.3 になるよう合わせる。
    戻り値: (new_outline, report, chain)
      chain は壁厚キャップ（stair_strip）用のラン列（T/R の seg を持つ）。
    """
    steps = PCB_STEPS[half]                    # [(x0, level)] x 6段
    bounds = [s[0] for s in steps] + [PCB_XB]  # [3.2, 26.6, 46.2, 65.2, 84.4, 103.4, 113.7]
    sgn = -1 if half == "short" else 1         # 階段側の向き（short は -y）
    # 踏面フェイス（段1〜4 は統一ルール、段5+6 は背面ランとして統合）
    faces = [lev + sgn * SEAM_PROJ for _, lev in steps[:4]]
    if half == "short":
        back_face = steps[4][1] + sgn * SEAM_PROJ - SEAM_BACK_EXT   # 19.76
        ranges = [(bounds[i], bounds[i + 1], faces[i]) for i in range(4)]
        ranges.append((bounds[4], bounds[6], back_face))
    else:
        ranges = [(bounds[i], bounds[i + 1], faces[i]) for i in range(4)]
        back_face = None   # long の背面ランは現行維持（整形範囲外）
    x0s, x1s = ranges[0][0], ranges[-1][1]
    # 階段状プロファイル（西→東）: 踏面と蹴上を交互に辿る点列
    prof = [(ranges[0][0], ranges[0][2])]
    for i in range(1, len(ranges)):
        prof.append((ranges[i][0], ranges[i - 1][2]))   # 蹴上（x 一定で段差）
        prof.append((ranges[i][0], ranges[i][2]))       # 次の踏面
    prof.append((ranges[-1][1], ranges[-1][2]))
    # 外側（階段側）への切り取りポリゴンと、内側へのフィルポリゴン
    far = -40.0 if sgn < 0 else 230.0
    cut = Polygon(prof + [(x1s, far), (x0s, far)])
    off = -sgn * SEAM_FILL_DEPTH
    fill = Polygon(prof + [(x, y + off) for (x, y) in reversed(prof)])
    base = outline_q.difference(cut)
    if base.is_empty:
        base = outline_q
    new_outline = largest(unary_union([largest(base), fill]))
    # レポートとキャップ用ラン列
    report, chain = [], []
    names = ["T1", "T2", "T3", "T4", "T-back"]
    for i, (xa, xb, f) in enumerate(ranges):
        lev = steps[i][1] if i < 4 else None
        report.append(dict(name=names[i], kind="T", fixed=lev, out=sgn, face=f))
        chain.append(dict(kind="T", a=(xa, f), b=(xb, f), fixed=lev, out=sgn,
                          back=(i == len(ranges) - 1 and half == "short"),
                          seg=LineString([(xa, f), (xb, f)])))
        print(f"[{half}] seam {names[i]}: tread x[{xa:.1f},{xb:.1f}] "
              f"{'pcb level ' + format(lev, '.2f') if lev is not None else 'back run (merged 5+6)'} "
              f"-> face={f:.3f}")
    for i in range(1, len(ranges)):
        B = ranges[i][0]
        flo, fhi = ranges[i - 1][2], ranges[i][2]
        chain.append(dict(kind="R", a=(B, flo), b=(B, fhi), fixed=B, out=sgn,
                          seg=LineString([(B, flo), (B, fhi)])))
        print(f"[{half}] seam R{i}: riser x={B:.2f} (shared boundary, "
              f"face span {flo:.2f}..{fhi:.2f})")
    print(f"[{half}] seam outline: area {outline_q.area:.0f} -> {new_outline.area:.0f}")
    return new_outline, report, chain

def stair_profile_line(half):
    """基板階段プロファイル（踏面＋蹴上を交互に辿る折れ線、make_outline3
    の STEPS が正本）。プレートのブリッジ帯（§17.14）の基準線。"""
    steps = PCB_STEPS[half]                    # [(x0, level)] x 6段
    pts = [(steps[0][0], steps[0][1])]
    for i in range(1, len(steps)):
        pts.append((steps[i][0], steps[i - 1][1]))   # 蹴上（x 一定で段差）
        pts.append((steps[i][0], steps[i][1]))       # 次の踏面
    pts.append((PCB_XB, steps[-1][1]))
    return LineString(pts)

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
    背面リム（ネジ帯域）には届かないようラン列基準で限定する。
    v2.4.4 (§17.18): short の背面ラン（T-back）はキャップ対象から
    外す。背面ランは SEAM_BACK_EXT でフェイスを 2.0 延長してあり、
    キャップが効くとキャビティまで 2.0 広がって T5（SW25 の段）の
    クリアランスが 0.5 → 2.5 になっていた（試作で「最上段だけ
    隙間が広い／段が浅い」の実物判定の原因）。背面ランは long と
    同様に厚壁（4.2）のまま残す。"""
    segs = [r["seg"] for r in chain if not r.get("back")]
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
    cavity_q = largest(outset(pcb, CAV_CLR, round_join=True))
    # v2.1: 階段外形をランごとのブロックに量子化（§17.3）。図面外形は
    # outline_dxf として保持し、下流は量子化後の outline を使う。
    outline_q, _q_report = quantize_stair(outline_dxf, pcb, half, cav0=cavity_q)
    # v2.4: 階段フェイスを左右共有のシームカーブへ整形（§17.13、案2）。
    # 量子化外形を土台に階段帯だけを置き換える（long の背面ランなど
    # 対象外の部分と外形の他の辺は v2.3 のまま）。壁厚キャップ用の
    # ラン列（halves["chain"]）もシーム側のラン列に替える。
    outline, stair_report, seam_chain = seam_stair(outline_q, pcb, half)
    halves[half] = dict(outline=outline, outline_dxf=outline_dxf, pocket=pocket,
                        sw=sw_holes, slots=slots, pcb=pcb, stair=stair_report,
                        chain=seam_chain, cavity_q=cavity_q)
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

def opening_at(foot, cx, cy):
    """フットプリント（材料ポリゴン）上で点 (cx, cy) を通る void ランの
    幅 (x 方向, y 方向) を返す。材料区間の隙間のうち中心を含むものを測る。
    fin-fix 復元の判定（§17.16）に使う。"""
    def _spans(axis, v):
        if axis == "x":
            line = LineString([(cx - 40.0, v), (cx + 40.0, v)])
        else:
            line = LineString([(v, cy - 40.0), (v, cy + 40.0)])
        inter = foot.intersection(line)
        if inter.is_empty:
            return []
        geoms = [inter] if inter.geom_type == "LineString" else list(inter.geoms)
        out = []
        for g in geoms:
            if g.length > 0:
                vals = [c[0] if axis == "x" else c[1] for c in g.coords]
                out.append((min(vals), max(vals)))
        return sorted(out)

    def _run(spans, c):
        prev = None
        for a, b in spans:
            if a > c:
                return a - (prev if prev is not None else c - 40.0)
            prev = b
        return (c + 40.0) - (prev if prev is not None else c - 40.0)

    return _run(_spans("x", cy), cx), _run(_spans("y", cx), cy)

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
                far = [f for f in cand
                       if all(abs(f[0] - e["y"]) >= BACK_SCREW_MIN_SEP
                              for e in back)]
                if far and len(far) < len(cand):
                    print(f"[{half}] back screw band y[{b0:.0f},{b1:.0f}): "
                          f"min-sep filter {len(cand)} -> {len(far)} cand")
                y, bx, slack = max(far if far else cand, key=lambda f: f[2])
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

    # ---------- v2.4.1: プレート階段縁のブリッジ（§17.14、本人目視指摘） ----------
    # プレート外周はポケット（スイッチ配置）の歯形に沿うため、階段列の穴
    # では縁が内側へ入り込んで穴の縁サポートが不足する。さらに穴が外周
    # 0.5mm 以内に近づくと fin-fix が穴全周に 0.5mm の堀（moat）を切り、
    # 角付近の材料まで失われる（リングテストで short (36.6,9.3) が 8/24、
    # §17.14）。対策として階段側の湾を橋渡しする。階段側で追加して
    # よい上限は、外形キャップ（PLATE_CAP_INSET）ではなくフレーム
    # 下帯内壁（cavity_full）から PLATE_BRIDGE_CLR の隙間を残す範囲
    # とする（欠陥方向では外形キャップ側が先に効いており、基板+0.5
    # 基準の方が実際の壁の余裕を正しく表すため。ケース内に収める
    # ための最小ガードとして inset(outline, PLATE_BRIDGE_GUARD) は
    # 残す）。効かせる帯は基板階段プロファイルから PLATE_BRIDGE_STRIP
    # 以内に限定する（階段側以外・既存の外周は変えない）。ネジ計画
    # （背面ネジ／吊りボス）は変更前の外周で確定済みで、v2.4 と同一に保つ。
    if PLATE_BRIDGE:
        pre_bridge = plate_bnd
        strip = stair_profile_line(half).buffer(PLATE_BRIDGE_STRIP) \
                                          .intersection(outline)
        allow = inset(cavity_full, PLATE_BRIDGE_CLR) \
            .intersection(inset(outline, PLATE_BRIDGE_GUARD))
        fill = allow.intersection(strip).difference(plate_bnd)
        if not fill.is_empty and fill.area > 0:
            merged = unary_union([plate_bnd, fill])
            plate_bnd = largest(merged)
            H["plate_bnd"] = plate_bnd
            print(f"[{half}] plate bridge: fill area={fill.area:.1f} mm2 "
                  f"(dropped by largest: {merged.area - plate_bnd.area:.2f}) "
                  f"plate outline area -> {plate_bnd.area:.0f}")
        # v2.4.2 (§17.15): 階段×背面の角で fill が作る孤立した歯を落とす。
        # long では fill がポケット切り欠きの下（最後の蹴上 x=103.4 より
        # 背面側、テール踏面レベル +0.3 以下の角ブロック帯）に歯
        # （107.2〜113.8 × 164.2〜171.1、44.8mm2）を作り、切り欠きとの
        # 間に 2.1mm のスリットが残って櫛状になる（本人目視指摘）。
        # 最寄りの穴 (93.7, 167.4) まで 13mm 以上あり縁サポートには
        # 寄与しないため、fill 追加分に限ってこの帯を取り除き、角を
        # 単純な塊に戻す。short では帯内の fill 追加分は 0 で無変化
        # （検証済み）。§17.14 の上限（cavity-0.2 等）は変更しない。
        tail_x0, tail_lv = PCB_STEPS[half][-1]
        if half == "long":
            zone = Polygon([(tail_x0, -1e4), (1e4, -1e4),
                            (1e4, tail_lv + 0.35),
                            (tail_x0, tail_lv + 0.35)])
        else:
            zone = Polygon([(tail_x0, tail_lv - 0.35),
                            (1e4, tail_lv - 0.35),
                            (1e4, 1e4), (tail_x0, 1e4)])
        tooth = plate_bnd.difference(pre_bridge).intersection(zone)
        if not tooth.is_empty and tooth.area > 0:
            plate_bnd = largest(plate_bnd.difference(tooth))
            H["plate_bnd"] = plate_bnd
            print(f"[{half}] plate corner cleanup: removed fill tooth "
                  f"{tooth.area:.1f} mm2 in stair/back corner zone, "
                  f"plate outline area -> {plate_bnd.area:.0f}")
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
    fin_sq = [hp for hp in sq_polys
              if hp.boundary.distance(plate_bnd.boundary) < FIN_EPS_OUT]
    fin_parts = [hp.buffer(FIN_EPS_OUT) for hp in fin_sq]
    fin_parts += [hp.buffer(FIN_EPS) for hp in H["slots"]
                  if hp.boundary.distance(plate_bnd.boundary) < FIN_EPS]
    plate_bnd_p = plate_bnd
    if fin_parts:
        moat = unary_union(fin_parts)
        plate_bnd_p = shp(ring_pts(largest(plate_bnd.difference(moat))))
        print(f"[{half}] plate fin-fix: {len(fin_parts)} hole(s) near outline, "
              f"outline area {plate_bnd.area:.0f} -> {plate_bnd_p.area:.0f}")
    # ---------- v2.4.3: fin-fix で断たれた「閉じた穴」の壁を復元（§17.16） ----------
    # 本人目視指摘＋親側実測で確定した欠陥: long の階段×背面角の穴
    # (93.72, 167.44) は、fin-fix 前は全周に壁があり開口は設計どおり
    # 14.15 角だったが、穴の上辺〜外周の壁が 0.45mm しかなく、0.5mm の
    # 堀が壁を断ち切って開口が外側の切り欠きとつながった（実測 x 15.0 /
    # y 22.5 以上、MX のパチ留めタブが掛からない）。ブリッジ（§17.14）の
    # 上限は cavity-0.2 で、この穴は基板踏面（y=171.6、§17.12 の推定）
    # より外にはみ出すため、壁を「追加」で直すことはできない。代わりに、
    # fin-fix 前のフットプリントで開口が設計値ちょうどだった角穴に限り、
    # 堀が削った材料（fin-fix 前の外周 plate_bnd の内側のみ）を戻し、
    # 開口を設計値に復元する。もともと縁へ開いた notch 穴（開口が設計値
    # より大きい）は判定で外れ、従来どおり堀が残る。戻す材料は
    # plate_bnd の内側だけなので §17.14/§17.15 のエンベロープは超えない。
    if fin_sq:
        foot_pre = plate_bnd.difference(unary_union(hole_polys))
        for hp in fin_sq:
            cc = hp.centroid
            ow, oh = opening_at(foot_pre, cc.x, cc.y)
            if (abs(ow - SW_HOLE_MODEL) <= FIN_RESTORE_TOL
                    and abs(oh - SW_HOLE_MODEL) <= FIN_RESTORE_TOL):
                collar = plate_bnd.intersection(hp.buffer(FIN_EPS_OUT))
                if not collar.is_empty and collar.area > 0:
                    plate_bnd_p = shp(ring_pts(largest(
                        unary_union([plate_bnd_p, collar]))))
                    print(f"[{half}] plate fin-fix restore: hole "
                          f"({cc.x:.2f},{cc.y:.2f}) collar {collar.area:.1f} mm2 "
                          f"restored, outline area -> {plate_bnd_p.area:.0f}")
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
    # v2.4.5 (§17.19): 屋根の連結帯。ガイド穴で断たれる屋根ブロック
    # 同士を、内側縁に沿う帯（PLUNGER_STRIP 参照）で連結する。
    strip_y0 = min(TACT_CENTERS[half]) - PLUNGER_STRIP_YM
    strip_y1 = max(TACT_CENTERS[half]) + PLUNGER_STRIP_YM
    frame = frame + box(PLUNGER_STRIP_X0, PLUNGER_STRIP_X1,
                        strip_y0, strip_y1, PADDLE_SLOT_Z1, FRAME_TOP)
    # v2.4.5 (§17.19): プランジャの受け。タクト中心（TACT_X は推定）に
    # ガイド穴 Ø5.4（スロット上面〜天面）とキャップ座ぐり Ø8.6
    # （床 z=14.1）を開ける。パドルスロットは今回も残置する: スロットは
    # タクト実体とプランジャのフランジ（Ø7）の逃げとして現役であり、
    # 埋めると干渉確認ができなくなるため（§17.19 の判断記録）。
    # なおガイド穴の内側端（x<約104.5）は天面開口（well）側へ
    # 約 0.7mm 破れる（屋根の実材は x≈104.5〜背面フェイス）。軸の
    # 案内は残る 3 方向と座ぐりで足りる見込みで、試作で確認する。
    for tc in TACT_CENTERS[half]:
        frame = frame - cyl(TACT_X, tc, PLUNGER_GUIDE_Z0, PLUNGER_HOLE_D,
                            FRAME_TOP + 0.3 - PLUNGER_GUIDE_Z0)
        frame = frame - cyl(TACT_X, tc, PLUNGER_CB_FLOOR, PLUNGER_CB_D,
                            FRAME_TOP + 0.3 - PLUNGER_CB_FLOOR)
    # USB開口は v2.4.4 (§17.18) でトレイ＋バンドの端壁へ移設した
    # （裏面実装でコネクタが z 0〜3 に来るため）。フレーム側にあった
    # 旧開口（z 9.8〜15.3）とプラグポケットは廃止し、壁に戻す。
    # カットはトレイ／バンド構築側で行う。
    # TRRS開口（背面壁）
    frame = frame - box(xmax - 6.5, xmax + 1, trrs_y - TRRS_W / 2, trrs_y + TRRS_W / 2, TRRS_Z0, TRRS_Z1)

    # ---------- ネジ一覧（トレイ・バンド共通） ----------
    all_screws = [(e["x"], e["y"], BACK_SCREW_SPECS[e["size"]]) for e in back_screws]
    all_screws += [(e["x"], e["y"], BACK_SCREW_SPECS["M3"]) for e in hangs]

    # ---------- USB開口（端壁）と MCU ポケットの y 範囲（v2.4.4, §17.18） ----------
    if half == "short":
        usb_ch_y = (ymax - USB_CUT_IN, ymax + 2)
        mcu_pk_y = (ymax - MCU_POCKET_LEN, ymax + 0.5)
        mcu_dp_y = (ymax - MCU_DEEP_LEN, ymax + 0.5)
    else:
        ymin = H["outline"].bounds[1]
        usb_ch_y = (ymin - 2, ymin + USB_CUT_IN)
        mcu_pk_y = (ymin - 0.5, ymin + MCU_POCKET_LEN)
        mcu_dp_y = (ymin - 0.5, ymin + MCU_DEEP_LEN)

    # ---------- ボトムトレイ（黒、浅いトレイ: 床＋内側の造形） ----------
    tray = prism(outline, 0, FLOOR_T)
    # 位置決め溝（バンド下面のスカートを受ける、全周）
    tray = tray - ring_prism(inset(outline, GROOVE_IN0), inset(outline, GROOVE_IN1),
                             FLOOR_T - GROOVE_DEPTH, FLOOR_T + 0.05)
    # パドル窓の床部分（バンド側と共通の帯を抜く）
    for (sy0, sy1) in H["paddle_spans_bot"]:
        # v2.4.4 (§17.18): 窓端と端壁の間に残る床の帯（約 9.5mm）が
        # MCU ポケットの貫通帯と挟まれて孤立片（別ソリッド）になる
        # ため、端まで 12mm 未満の帯は窓を端壁まで延長して切り取る
        # （トレイのみ。バンドはリング連続性があり不要）。
        ob = H["outline"].bounds
        if half == "short" and ob[3] - sy1 < 12.0:
            sy1 = ob[3] + 0.5
        if half == "long" and sy0 - ob[1] < 12.0:
            sy0 = ob[1] - 0.5
        tray = tray - box(PADDLE_WIN_X0, xmax + 1, sy0, sy1, -0.1, FLOOR_T + 0.1)
    # MCUポケット（裏面実装の逃げ）: 床を MCU_POCKET_FLOOR まで彫り、
    # コネクタ帯（端寄り MCU_DEEP_LEN）は床を貫通させる
    tray = tray - box(MCU_POCKET_X0, MCU_POCKET_X1, mcu_pk_y[0], mcu_pk_y[1],
                      MCU_POCKET_FLOOR, FLOOR_T + 0.1)
    tray = tray - box(MCU_POCKET_X0, MCU_POCKET_X1, mcu_dp_y[0], mcu_dp_y[1],
                      -0.1, FLOOR_T + 0.1)
    # USB開口（端壁、トレイ分）: z USB_Z0〜USB_Z1 を端壁に通す
    tray = tray - box(USB_XC - USB_W / 2, USB_XC + USB_W / 2,
                      usb_ch_y[0], usb_ch_y[1], USB_Z0 - 0.1, USB_Z1)
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
    # USB開口（端壁、バンド分）: z USB_Z0〜USB_Z1 を端壁に通す（v2.4.4, §17.18）
    band = band - box(USB_XC - USB_W / 2, USB_XC + USB_W / 2,
                      usb_ch_y[0], usb_ch_y[1], USB_Z0 - 0.1, USB_Z1)
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

def build_plunger():
    """プランジャ（小ボタン）単体。左右・6タクト共通の同一部品。

    印刷方向でモデリングする: キャップ上面をベッドに置く
    （print z=0 が組立 z=17.2、print z が上がるほど組立では下がる）。
      print z[0.0, 2.0] キャップ Ø9（組立 z[15.2, 17.2]）
      print z[2.0, 4.3] 軸 Ø4.6（組立 z[12.9, 15.2]）
      print z[4.3, 5.3] フランジ Ø7（組立 z[11.9, 12.9]）
      受け凹みはフランジの組立下面 = print 上面から深さ 0.9 の
      Ø4.0 の窪み（組立の天井 z=12.8）。
    サポート不要（段差は軸→フランジの 1.2mm/片側のみで、下面は
    抜け止めの接触面だが多少の垂れは機能に影響しない）。
    """
    p = cyl(0, 0, 0, PLUNGER_CAP_D, PLUNGER_CAP_T)
    p = p + cyl(0, 0, PLUNGER_CAP_T, PLUNGER_SHAFT_D, PLUNGER_SHAFT_L)
    p = p + cyl(0, 0, PLUNGER_CAP_T + PLUNGER_SHAFT_L,
                PLUNGER_FLANGE_D, PLUNGER_FLANGE_T)
    p = p - cyl(0, 0, PLUNGER_TOTAL_H - PLUNGER_RECESS_DEPTH,
                PLUNGER_RECESS_D, PLUNGER_RECESS_DEPTH + 0.2)
    return p

results = {}
for half in ("short", "long"):
    print(f"===== build {half} =====")
    parts = build_half(half)
    results[half] = parts
    export(parts["plate"], f"switch_plate_{half}")
    export(parts["frame"], f"top_frame_{half}")
    export(parts["tray"], f"bottom_tray_{half}")
    export(parts["band"], f"side_band_{half}")

# プランジャ（小ボタン）: 左右共通部品を 1 点書き出す（必要数 6）
export(build_plunger(), "plunger")

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
#   - v2.4.5: 角フレームにはプランジャのガイド穴＋座ぐりが入り、
#     plunger.stl（6 個、make_trial_all で複製）が試作一式に加わる。
#     実基板のタクトに当てて押し心地・ストローク・戻りを見る。
# ネジまわりの試作片（旧 trial_screw）は、ネジ経路を仮想検証で確認する
# ことにして廃止した。積層クリップ（旧 trial_compose）も廃止し、
# 全てパーツ別クリップとする。

# 1) 階段境界（両半分）: バンドだけを切り出す
#    v2.4: クリップ範囲は継ぎ目に関わる階段ラン全部（両半分の全踏面・
#    全蹴上）を含む。左右の試作片同士を机の上で向き合わせれば、
#    ドッキングの噛み合い（継ぎ目 0.3mm）を実物で確認できる。
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
