#!/usr/bin/env python3
"""タクト位置バリエーション試作・逆向き版（v2.4.16 / §17.31）。

§17.28 の +側セット（s15/s19/s23）は、実物判定で是正方向が
逆だったと確定したため、階段側（−y）へずらした 6 種を新たに
作る:
  y（並び方向、階段側へ）: −1.5 / −1.9 / −2.3（§17.18 基準中心比）
  x（奥行き）: 0 / −1.9
単体 STL は trial_tact_frame_short_r{15,19,23}[_x19].stl
（build_case を環境変数 TACT_VARIANT_STEP=−<量> /
TACT_VARIANT_TAG=r<量> で生成）。"r" は reverse の意で、
long 版の m19 等とは混同しない命名にした。

彫り込み文字は make_tact_variants の text_cutter（§17.30 で
鏡像修正済みの方式）をそのまま使い、外から正しく読める。
統合ファイルは trial_tact_variants_rev.stl。
"""
import numpy as np
import trimesh

import make_trial_all as mt
import make_tact_variants as mv

BASE = mt.BASE

VARIANTS = [  # (step_y, dx, file tag)
    (-1.5, 0.0, "r15"), (-1.9, 0.0, "r19"), (-2.3, 0.0, "r23"),
    (-1.5, -1.9, "r15_x19"), (-1.9, -1.9, "r19_x19"),
    (-2.3, -1.9, "r23_x19"),
]


def main():
    plungers = mt.load_solids(f"{BASE}/plunger.stl")
    assert len(plungers) == 1
    pieces = []
    labels = {}
    for step, dx, tag in VARIANTS:
        name = f"trial_tact_frame_short_{tag}"
        solids = mt.load_solids(f"{BASE}/{name}.stl")
        assert len(solids) == 1, f"{name}: solids={len(solids)}"
        print(f"== {name} (Y{step:+} / X{dx}) ==")
        m = mv.engrave(solids[0], step, dx)
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
    path = f"{BASE}/trial_tact_variants_rev.stl"
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
    ax.set_title("タクト位置バリエーション試作・逆向き版（short・フレーム角のみ）",
                 fontsize=14)
    fig.text(0.5, 0.012,
             "§17.28 の +側セットは方向が逆だったため、これは階段側"
             "（−方向）へずらした版です。\n"
             "各ピースの外側の端面に、ずらし量が彫り込んであります"
             "（例: Y-1.9 / X0 = 並び方向に −1.9、奥行きは変更なし）。\n"
             "ピースは天面を下にして印刷します（並びはこの図のとおり）。"
             "小ボタンは各ピースに 3 個ずつ、横倒し（平らな背面を下）で"
             "付いています。\n"
             "当て方: バンドを先に基板へ正しく座らせ、ピースをタクトに"
             "合わせて、座りと穴の合いが一番いいものを選んでください。",
             ha="center", fontsize=10.5)
    fig.tight_layout(rect=(0, 0.07, 1, 0.97))
    fig.savefig(f"{BASE}/guide_tact_variants_rev.png", dpi=110)
    print("saved guide_tact_variants_rev.png")


if __name__ == "__main__":
    main()
