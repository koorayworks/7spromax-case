# -*- coding: utf-8 -*-
"""STL 実ファイルの独立検証: 頂点溶接ベースで
コンポーネント数 / 最小z / non-manifold エッジ数を数える。
使い方: python verify_stl.py file1.stl [file2.stl ...]
"""
import sys, struct
from collections import Counter, defaultdict

def load_tris(path):
    with open(path, "rb") as f:
        data = f.read()
    if data[:5] == b"solid" and b"facet" in data[:4096]:
        tris = []
        cur = []
        for line in data.decode("utf-8", "ignore").splitlines():
            t = line.strip()
            if t.startswith("vertex"):
                p = t.split()
                cur.append((float(p[1]), float(p[2]), float(p[3])))
                if len(cur) == 3:
                    tris.append(tuple(cur)); cur = []
        return tris
    n = struct.unpack("<I", data[80:84])[0]
    tris = []
    off = 84
    for _ in range(n):
        v = struct.unpack("<12fH", data[off:off + 50]); off += 50
        tris.append((v[3:6], v[6:9], v[9:12]))
    return tris

def weld_id(p, cache):
    key = (round(p[0], 4), round(p[1], 4), round(p[2], 4))
    if key not in cache:
        cache[key] = len(cache)
    return cache[key]

def analyze(path):
    tris = load_tris(path)
    cache = {}
    wtris = [tuple(weld_id(p, cache) for p in tri) for tri in tris]
    # エッジ集計（non-manifold 判定 + コンポーネント連結）
    edge_count = Counter()
    for a, b, c in wtris:
        for e in ((a, b), (b, c), (c, a)):
            edge_count[tuple(sorted(e))] += 1
    nonmanifold = sum(1 for v in edge_count.values() if v != 2)
    # コンポーネント: エッジを共有する三角形を union-find
    parent = list(range(len(wtris)))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    edge2tri = defaultdict(list)
    for i, (a, b, c) in enumerate(wtris):
        for e in ((a, b), (b, c), (c, a)):
            edge2tri[tuple(sorted(e))].append(i)
    for ts in edge2tri.values():
        for t in ts[1:]:
            ra, rb = find(ts[0]), find(t)
            if ra != rb:
                parent[ra] = rb
    comps = len({find(i) for i in range(len(wtris))})
    zmin = min(p[2] for tri in tris for p in tri)
    return dict(tris=len(tris), comps=comps, nonmanifold=nonmanifold, zmin=zmin)

if __name__ == "__main__":
    print(f"{'file':34s} {'tris':>8s} {'comp':>5s} {'minz':>7s} {'nonmanif':>9s}  verdict")
    for path in sys.argv[1:]:
        r = analyze(path)
        ok = (r["comps"] == 1 and abs(r["zmin"]) < 1e-6 and r["nonmanifold"] == 0)
        name = path.split("/")[-1]
        print(f"{name:34s} {r['tris']:8d} {r['comps']:5d} {r['zmin']:7.3f} "
              f"{r['nonmanifold']:9d}  {'OK' if ok else 'NG'}")
