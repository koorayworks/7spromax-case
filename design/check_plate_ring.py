# -*- coding: utf-8 -*-
"""
7sProMax ケース: スイッチプレートの穴サポート リングテスト（§17.14）

各スイッチ穴中心から半径 RING_R の円周上 24 点（15°刻み）をサンプリングし、
プレート実材内にある点数を数える。穴（14.15 角）のコーナー方向の 4 点は
穴内部に落ちるため、満点は 20/24。これが満点でない穴は、その方向で
穴の縁から (RING_R - 7.075) mm 未満しか材料が無い＝サポート不足。

対象は書き出し済み STL（単体）。板厚方向の代表 z は、断面積走査で
スラブ区間の中央を自動で取る（吊りボス区間を避ける）。

実行: ~/workspace/.venv-cad/bin/python check_plate_ring.py
"""
import json
import numpy as np
import trimesh
from shapely.geometry import Polygon

BASE = "/home/hatch/workspace/7spromax-case"
RING_R = 8.2
N_PTS = 24

# --- スイッチ中心（render_assembled_v22.py と同じ方法: DXF 正本から） ---
_dx = json.load(open(f"{BASE}/work_design/dxf_polys.json"))
_ORIGIN = {"short": (0.0, 183.414), "long": (0.0, 0.0)}
SW = {}
for half in ("short", "long"):
    ox, oy = _ORIGIN[half]
    sw = []
    for hp in _dx["SWITCH_HOLES"]:
        pts = hp["pts"]
        cy = float(np.mean([q[1] for q in pts]))
        if (cy > 183.41) == (half == "short"):
            poly = Polygon([(x - ox, y - oy) for x, y in pts])
            b = poly.bounds
            if (b[2] - b[0]) > 15.5 and (b[3] - b[1]) < 8.0:
                continue            # 横長スロットは対象外
            c = poly.centroid
            sw.append((c.x, c.y))
    SW[half] = sw


def _section_area(mesh, z):
    sec = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if sec is None:
        return 0.0
    total = 0.0
    verts = np.asarray(sec.vertices)
    for ent in sec.entities:
        pts = verts[ent.points]
        if len(pts) >= 4:
            p = Polygon(pts[:, :2])
            if not p.is_valid:
                p = p.buffer(0)
            if p.geom_type == "MultiPolygon":
                p = max(p.geoms, key=lambda g: g.area)
            if not p.is_empty:
                total += p.area
    return total


def slab_mid_z(mesh):
    """断面積が最大級で安定する区間（スラブ）の中央 z を返す。"""
    z0, z1 = mesh.bounds[0][2], mesh.bounds[1][2]
    zs = np.arange(z0 + 0.05, z1, 0.1)
    areas = np.array([_section_area(mesh, z) for z in zs])
    amax = areas.max()
    good = areas > 0.9 * amax
    # 最も長い連続区間を取る
    best, cur = (0, 0), None
    for i, g in enumerate(good):
        if g and cur is None:
            cur = i
        if (not g or i == len(good) - 1) and cur is not None:
            end = i - 1 if not g else i
            if end - cur > best[1] - best[0]:
                best = (cur, end)
            cur = None
    return float((zs[best[0]] + zs[best[1]]) / 2), amax


def ring_scores(half, mesh=None, verbose=True):
    if mesh is None:
        mesh = trimesh.load(f"{BASE}/design/switch_plate_{half}.stl")
        if isinstance(mesh, trimesh.Scene):
            mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    zmid, amax = slab_mid_z(mesh)
    scores = {}
    for (cx, cy) in SW[half]:
        ang = np.deg2rad(np.arange(N_PTS) * (360.0 / N_PTS))
        pts = np.column_stack([cx + RING_R * np.cos(ang),
                               cy + RING_R * np.sin(ang),
                               np.full(N_PTS, zmid)])
        inside = mesh.contains(pts)
        scores[(round(cx, 1), round(cy, 1))] = int(inside.sum())
    if verbose:
        bad = {k: v for k, v in scores.items() if v < 20}
        print(f"[{half}] z_mid={zmid:.2f} section area={amax:.0f} "
              f"holes={len(scores)} full(20)={sum(1 for v in scores.values() if v >= 20)} "
              f"deficient={len(bad)}")
        for k in sorted(bad, key=lambda k: bad[k]):
            print(f"    hole {k}: {bad[k]}/24")
    return scores


if __name__ == "__main__":
    for half in ("short", "long"):
        ring_scores(half)
    print("RING CHECK DONE")
