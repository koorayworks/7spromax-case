# -*- coding: utf-8 -*-
"""
USB / TRRS 開口の貫通チェック（v2.4.3、§17.17 の回帰防止）

v2.4.2 まで USB 開口は外面から 1mm のカットしかなく、端壁の内側に
2.8mm のウェブが残って貫通していなかった（実測で確定した欠陥）。
ここでは開口チャネルの中心線に沿って断面ポリゴンをサンプルし、
内側ポケット面からケース外面まで材料が無いことを確認する。
TRRS チャネルも同じ方法で確認する。

実行: ~/workspace/.venv-cad/bin/python check_usb_channel.py
"""
import numpy as np
import trimesh
from shapely.geometry import Polygon, Point
import build_case as bc

def section_polys(mesh, z_local):
    sec = mesh.section(plane_origin=[0, 0, z_local], plane_normal=[0, 0, 1])
    out = []
    if sec is None:
        return out
    for ent in sec.entities:
        pts = np.asarray(sec.vertices)[ent.points]
        if len(pts) >= 4:
            p = Polygon(pts[:, :2])
            if not p.is_valid:
                p = p.buffer(0)
            if p.geom_type == "MultiPolygon":
                p = max(p.geoms, key=lambda g: g.area)
            if not p.is_empty and p.area > 0.01:
                out.append(p)
    return out

def blocked(polys, x, y):
    return any(p.covers(Point(x, y)) for p in polys)

def main():
    ok = True
    for half in ("short", "long"):
        m = trimesh.load(f"{bc.OUTDIR}/top_frame_{half}.stl")
        if isinstance(m, trimesh.Scene):
            m = trimesh.util.concatenate(tuple(m.geometry.values()))
        ob = bc.halves[half]["outline"].bounds
        # --- USB: 中心 (USB_XC, z 中心) の y 走査 ---
        zc = (bc.USB_Z0 + bc.USB_Z1) / 2
        polys = section_polys(m, zc - 5.7)
        if half == "short":
            ys = np.arange(136.0, ob[3] + 0.01, 0.25)
        else:
            ys = np.arange(ob[1], 8.01, 0.25)
        hits = [y for y in ys if blocked(polys, bc.USB_XC, y)]
        # ポケット内 (基板側) は開いていて当然なので、壁帯域だけを見る:
        # 壁帯域 = cavity 面の外側。short: y >= 138.9 / long: y <= 4.7
        if half == "short":
            wall_hits = [y for y in hits if y >= 138.9]
        else:
            wall_hits = [y for y in hits if y <= 4.7]
        stat = "OK (through)" if not wall_hits else f"NG blocked at y={wall_hits}"
        if wall_hits:
            ok = False
        print(f"{half} USB channel (x={bc.USB_XC}, z={zc:.1f}): {stat}")
        # --- USB プラグポケット: 外面から POCKET_D の範囲は広く開くこと ---
        zpk = (bc.USB_POCKET_Z0 + bc.USB_Z1) / 2
        polys_pk = section_polys(m, zpk - 5.7)
        xpk = bc.USB_XC + bc.USB_POCKET_W / 2 - 1.0   # ポケット端寄り
        if half == "short":
            ypk = ob[3] - bc.USB_POCKET_D / 2
        else:
            ypk = ob[1] + bc.USB_POCKET_D / 2
        pk_blocked = blocked(polys_pk, xpk, ypk)
        print(f"{half} USB plug pocket (x={xpk:.0f}, y={ypk:.1f}, z={zpk:.1f}): "
              f"{'NG blocked' if pk_blocked else 'OK (open)'}")
        if pk_blocked:
            ok = False
        # --- TRRS: 中心 (y=TRRS_Y, z 中心) の x 走査 ---
        zt = (bc.TRRS_Z0 + bc.TRRS_Z1) / 2
        polys_t = section_polys(m, zt - 5.7)
        ty = bc.TRRS_Y[half]
        xs = np.arange(104.0, ob[2] + 0.01, 0.25)
        hits_t = [x for x in xs if blocked(polys_t, x, ty)]
        # ジャック面はタブ先端付近 (x≈113)。壁帯域 x>=108 で見る
        wall_t = [x for x in hits_t if x >= 108.0]
        stat_t = "OK (through)" if not wall_t else f"NG blocked at x={wall_t}"
        if wall_t:
            ok = False
        print(f"{half} TRRS channel (y={ty}, z={zt:.2f}): {stat_t}")
    print("CHANNEL CHECK " + ("OK" if ok else "NG"))

if __name__ == "__main__":
    main()
