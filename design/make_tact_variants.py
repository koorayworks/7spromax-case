#!/usr/bin/env python3
"""タクト位置バリエーション試作（v2.4.14 / §17.28）。

short のフレームタクト角ピースを、ずらし量のグリッドで
1 ファイルにまとめる:
  y（並び方向、外側端へ）: +1.5 / +1.9 / +2.3（v2.4.13 中心比）
  x（奥行き）: 0 / -1.9（TACT_X 111.57 → 109.67）
の 6 種。各ピースは角フレームそのままの切り出し（差し込み口
込み）で、タクト位置だけが段階で変わる。プランジャは各種に
3 個ずつ同梱（横倒し、§17.28 の印刷ルール）。

区別は外側端面への彫り込み文字（凹み、深さ 0.5）:
  1 行目 "Y<量>"、2 行目 "X<量>"。端面は当て面でもベッド面
  でもない（§17.27 で浮き彫り残置が OK だったのと同じ面）。
  彫り込みはフレームを天地逆に印刷する前の向き（組立向き）
  で入れるため、印刷後にピースを基板へ当てる向きに戻せば
  そのまま読める。

ピース単体 STL（trial_tact_frame_short_s*.stl）は build_case
を環境変数 TACT_VARIANT_STEP / TACT_VARIANT_DX で回して作る。
"""
import numpy as np
import trimesh

import make_trial_all as mt

BASE = mt.BASE

VARIANTS = [  # (step_y, dx, file tag)
    (1.5, 0.0, "s15"), (1.9, 0.0, "s19"), (2.3, 0.0, "s23"),
    (1.5, -1.9, "s15_x19"), (1.9, -1.9, "s19_x19"),
    (2.3, -1.9, "s23_x19"),
]
TEXT_H = 3.2     # 彫り込み文字の高さ
DEPTH = 0.5      # 彫り込み深さ


def text_cutter(text, cx, cz, ymax):
    """端面（y=ymax の垂直面）に文字を彫るためのカッター。
    ローカル (a=面に沿う x, b=上向き z) の文字ポリゴンを、
    面の外側 (+y) から DEPTH+0.15 だけ差し込むソリッドにする。"""
    polys = mt.digit_polygons(text, TEXT_H)
    w = polys.bounds[2] - polys.bounds[0]
    assert w < 13.5, f"text '{text}' too wide: {w:.1f}mm"
    parts = []
    for p in polys.geoms:
        parts.append(trimesh.creation.extrude_polygon(p, DEPTH + 0.15))
    m = trimesh.util.concatenate(parts)
    M = np.eye(4)
    M[:3, 0] = [1, 0, 0]      # a -> +x
    M[:3, 1] = [0, 0, 1]      # b -> +z
    M[:3, 2] = [0, -1, 0]     # extrude dir -> -y (面の内側へ)
    M[:3, 3] = [cx, ymax + 0.15, cz]
    m.apply_transform(M)
    return m


def engrave(mesh, step, dx):
    b = mesh.bounds
    ymax = b[1, 1]
    cx = 107.5
    lines = [(f"Y{step:.1f}", 7.7), (f"X{dx:.1f}", 4.0)]
    out = mesh
    for text, cz in lines:
        cut = text_cutter(text, cx, cz, ymax)
        new = trimesh.boolean.difference([out, cut], engine="manifold")
        if isinstance(new, trimesh.Scene):
            new = trimesh.util.concatenate(tuple(new.geometry.values()))
        removed = out.volume - new.volume
        solids = new.split(only_watertight=False)
        print(f"    engrave '{text}': removed {removed:.2f} mm3, "
              f"solids={len(solids)}, watertight={new.is_watertight}")
        assert 0.05 < removed < 10.0 and len(solids) == 1 \
            and new.is_watertight
        out = new
    return out


def main():
    plungers = mt.load_solids(f"{BASE}/plunger.stl")
    assert len(plungers) == 1
    pieces = []
    labels = {}
    for step, dx, tag in VARIANTS:
        name = f"trial_tact_frame_short_{tag}"
        solids = mt.load_solids(f"{BASE}/{name}.stl")
        assert len(solids) == 1, f"{name}: solids={len(solids)}"
        print(f"== {name} (Y+{step} / X{dx}) ==")
        m = engrave(solids[0], step, dx)
        m = mt.flip_frame(m)
        label = f"{name}#0"
        labels[label] = (f"Y{step:.1f} X{dx:.1f}",
                         "天面を下に（逆さ）。端面の彫り込みで判別")
        pieces.append((label, m))
        for i in range(3):
            pl = f"plunger_{tag}#{i}"
            labels[pl] = ("小ボタン", "横倒し（平らな背面を下に）")
            pieces.append((pl, mt.lay_plunger_side(plungers[0])))
    placed = mt.pack(pieces)
    allm = trimesh.util.concatenate([m for _, m, _ in placed])
    bb = allm.bounds
    print(f"combined bbox x[{bb[0,0]:.1f},{bb[1,0]:.1f}] "
          f"y[{bb[0,1]:.1f},{bb[1,1]:.1f}] z[{bb[0,2]:.2f},{bb[1,2]:.1f}]")
    assert bb[1, 0] <= mt.BED and bb[1, 1] <= mt.BED
    assert abs(bb[0, 2]) < 1e-6
    path = f"{BASE}/trial_tact_variants.stl"
    allm.export(path)
    import os
    print(f"saved {path} ({os.path.getsize(path)} bytes)")

    # ガイド図
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
    fig, ax = plt.subplots(figsize=(10.5, 10.5))
    for label, m, fp in placed:
        xs, ys = np.array(fp.exterior.coords).T
        ax.plot(xs, ys, lw=1.1)
        rp = fp.representative_point()
        if label.startswith("trial_tact"):
            txt, _ = labels[label]
            ax.text(rp.x, rp.y, txt, ha="center", va="center",
                    fontsize=15, fontweight="bold", color="#C0272D")
    ax.set_xlim(0, mt.BED)
    ax.set_ylim(0, mt.BED)
    ax.set_aspect("equal")
    ax.grid(alpha=0.25)
    ax.set_title("タクト位置バリエーション試作（short・フレーム角のみ）",
                 fontsize=14)
    fig.text(0.5, 0.012,
             "各ピースの外側の端面に、ずらし量が彫り込んであります"
             "（例: Y1.9 / X0 = 並び方向に +1.9、奥行きは変更なし）。\n"
             "ピースは天面を下にして印刷します（並びはこの図のとおり）。"
             "小ボタンは各ピースに 3 個ずつ、横倒し（平らな背面を下）で"
             "付いています。\n"
             "当て方: バンドを先に基板へ正しく座らせ、ピースをタクトに"
             "合わせて、座りと穴の合いが一番いいものを選んでください。",
             ha="center", fontsize=10.5)
    fig.tight_layout(rect=(0, 0.07, 1, 0.97))
    fig.savefig(f"{BASE}/guide_tact_variants.png", dpi=110)
    print("saved guide_tact_variants.png")


if __name__ == "__main__":
    main()
