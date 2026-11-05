#!/usr/bin/env python3
"""pcb_outline3: rebuild the STAIR band of the PCB outline as clean
rectangular steps, anchored on measured data (see OUTLINE3_NOTES.md).

Why: pcb_outline2's stair band came from a local edge search over mat
photos (PCB_SCAN2_NOTES §6) and follows the step-shaped GROOVES on the
board surface instead of the edge in many places — the boundary zigzags
up to ~32mm into the board.  The real edge is a clean rectangular
staircase: 5 treads aligned to the 5 socket columns (x boundaries =
DXF case-outline run boundaries, which coincide with the column
midlines), plus the end landing next to the back edge.

Anchors per tread (all in case coords, X=depth 0..114.29, Y=length):
  A = outline2 envelope extreme / flat runs inside the tread extent
  B = edge-socket centre (dome centroid) -/+ per-half constant margin
      (short 8.63 from cols 3/4/5 margins 8.56/8.65/8.68;
       long  9.05 from cols 1..4 margins 9.19/9.27/8.94/8.78)
  D = DXF case-outline tread level + constant PCB inset
      (short inset ~= +0.7: treads 3/4/5 give 0.73/0.65/0.66 and the
       tab gives 0.65; long inset ~= -0.7..-1.1 on treads 2/3/4)
Where A and B agree (most treads) the value is solid.  Exceptions:
  * short tab (col 2): the traced "tip" at y=3.96 is a groove artefact.
    The socket dome (S27 centre y=9.28, dome r=2.75) bounds the tip to
    <= 6.53, the margin model gives 0.65 and the DXF inset check gives
    0.65 — adopt 0.65.  (Adopting 3.96 instead would risk hard
    interference if wrong; adopting 0.65 only costs wall clearance.)
  * short/long tread 1 (front corner tooth): A wins (corner geometry,
    margin model does not apply cleanly at the corner).
  * long tread 5: the tooth is truncated by the back corner; A wins.
  * tails (x>103.4): outline2 has a clean final landing segment on
    short (y~=30.0) and a mildly noisy one on long (~170.4-171.3);
    modelled as one more tread at the conservative level.

Outside the replaced strip (x in [3.2, 113.7] on the stair side) the
outline is outline2, point for point.
"""
import csv
import numpy as np
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

BASE = "/home/hatch/workspace/7spromax-case"
XA, XB = 3.2, 113.7          # replaced strip in x
BAND = 45.0                  # fill band depth (covers deepest spike ~32)

# (x_start, level) per tread; level = min-y for short, max-y for long.
# 2026-11-05 correction (§17.18): the tread x boundaries were re-anchored
# on the owner's caliper measurements of the real boards (photos
# 7461/7462).  The measured segments are the 5 keyed treads from the
# back, starting at the landing|T5 riser (x=103.4, kept from the DXF
# anchor; the landing itself was not re-measured):
#   long  (back->front): 17.2 / 19.1 / 19.1 / 22.0 / 17.2 (tooth tip)
#         -> risers at 86.2 / 67.1 / 48.0 / 26.0; old DXF-midline
#         risers were 84.4 / 65.2 / 46.2 / 26.6 (up to 1.9 mm off,
#         which is why the trial band would not seat at SW31-33).
#   short (back->front): 20 / 19 / 19 / 16 / 20 (tooth tip)
#         -> risers at 83.4 / 64.4 / 45.4 / 29.4; old risers were
#         84.4 / 65.2 / 46.2 / 26.6 (tab tread 19.6 -> 16.0).
# Levels (depth direction) are NOT covered by those measurements and
# are unchanged.
STEPS = {
    "short": [(3.2, 11.00), (29.4, 0.65), (45.4, 10.25), (64.4, 14.93),
              (83.4, 24.46), (103.4, 29.98)],
    "long":  [(3.2, 160.05), (26.0, 152.73), (48.0, 162.25),
              (67.1, 166.90), (86.2, 171.60), (103.4, 170.80)],
}


def load_outline(path):
    pts = np.loadtxt(path, delimiter=",", skiprows=1)
    return Polygon([tuple(p) for p in pts])


def step_rects(half):
    """cut rects (outside the board beyond the step edge) and fill band
    rects (from the step edge BAND mm into the board), per tread."""
    steps = STEPS[half]
    cuts, fills = [], []
    for i, (x0, lev) in enumerate(steps):
        x1 = steps[i + 1][0] if i + 1 < len(steps) else XB
        if half == "short":
            cuts.append(box(x0, -10.0, x1, lev))
            fills.append(box(x0, lev, x1, lev + BAND))
        else:
            cuts.append(box(x0, lev, x1, 220.0))
            fills.append(box(x0, lev - BAND, x1, lev))
    return unary_union(cuts), unary_union(fills)


def step_polyline(half):
    """the step edge as a LineString (for component touch tests)."""
    from shapely.geometry import LineString
    steps = STEPS[half]
    pts = []
    for i, (x0, lev) in enumerate(steps):
        x1 = steps[i + 1][0] if i + 1 < len(steps) else XB
        if i == 0:
            pts.append((x0, lev))
        pts.append((x1, lev))
        if i + 1 < len(steps):
            pts.append((x1, steps[i + 1][1]))
    return LineString(pts)


def build_outline3(half):
    old = load_outline(f"{BASE}/template/pcb_outline2_{half}.csv")
    if not old.is_valid:
        old = old.buffer(0)
    cut, fill = step_rects(half)
    added = fill.difference(old)
    # Keep only added components that TOUCH the step edge: those are the
    # groove valleys.  A genuine notch that opens to another edge (e.g.
    # long's back-corner cutout x 103.4..114 / y 128..164.5, walled off
    # from the stair edge by board material) must NOT be filled.
    edge = step_polyline(half)
    kept = []
    comps = list(added.geoms) if added.geom_type == "MultiPolygon" \
        else ([added] if added.geom_type == "Polygon" else [])
    for c in comps:
        if c.distance(edge) < 0.01:
            kept.append(c)
    new = old.difference(cut)
    if kept:
        new = new.union(unary_union(kept))
    if new.geom_type == "MultiPolygon":
        new = max(new.geoms, key=lambda g: g.area)
    if not new.is_valid:
        new = new.buffer(0)
        if new.geom_type == "MultiPolygon":
            new = max(new.geoms, key=lambda g: g.area)
    return old, new


def profile_deviation(old, new, half):
    """max |profile difference| inside the strip + worst outline2
    boundary point distance to the new polygon (removed spikes)."""
    xs = np.arange(XA, XB, 0.1)

    def prof(poly, x):
        from shapely.geometry import LineString
        inter = poly.intersection(LineString([(x, -5), (x, 220)]))
        ys = []
        geoms = [inter] if inter.geom_type in ("LineString", "Point",
                                               "MultiLineString") else \
            list(getattr(inter, "geoms", []))
        flat = []
        for g in geoms:
            if g.geom_type == "MultiLineString":
                flat += list(g.geoms)
            else:
                flat.append(g)
        for g in flat:
            if g.geom_type == "LineString":
                ys += [c[1] for c in g.coords]
            elif g.geom_type == "Point":
                ys.append(g.y)
        if not ys:
            return np.nan
        return min(ys) if half == "short" else max(ys)

    devs = []
    steps = STEPS[half]
    for x in xs:
        lev = max([lv for (sx, lv) in steps if sx <= x + 1e-9])
        pn = prof(new, x)
        if not np.isnan(pn):
            devs.append(abs(pn - lev))
    return (max(devs) if devs else None)


def main():
    report = {}
    for half in ("short", "long"):
        old, new = build_outline3(half)
        # save CSV (same format as outline2: header x_mm,y_mm)
        ring = np.array(new.exterior.coords)[:-1]
        out = f"{BASE}/template/pcb_outline{3}_{half}.csv"
        with open(out, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["x_mm", "y_mm"])
            for x, y in ring:
                w.writerow([f"{x:.3f}", f"{y:.3f}"])
        # --- verification ---
        strip = box(XA, -5, XB, 220)
        out_old = old.difference(strip)
        out_new = new.difference(strip)
        sym_out = out_old.symmetric_difference(out_new).area
        # removed/added area inside strip
        added = new.difference(old).intersection(strip).area
        removed = old.difference(new).intersection(strip).area
        # worst outline2 vertex distance into the new polygon (spikes)
        from shapely.geometry import Point
        worst = 0.0
        worst_xy = None
        for (x, y) in np.array(old.exterior.coords):
            if XA <= x <= XB:
                d = new.exterior.distance(Point(x, y)) \
                    if not new.contains(Point(x, y)) else 0.0
                # distance from vertex to new polygon boundary when the
                # vertex was cut away = distance to new polygon
                if not new.covers(Point(x, y)):
                    d = new.distance(Point(x, y))
                else:
                    d = 0.0
                if d > worst:
                    worst, worst_xy = d, (x, y)
        # sockets containment
        rows = list(csv.DictReader(open(f"{BASE}/template/pcb_sockets.csv")))
        worst_sock = None
        for r in rows:
            if r["half"] != half:
                continue
            sx = float(r["meas_x_mm"] or r["dxf_x_mm"])
            sy = float(r["meas_y_mm"] or r["dxf_y_mm"])
            d = new.exterior.distance(Point(sx, sy))
            inside = new.covers(Point(sx, sy))
            key = d if inside else -d
            if worst_sock is None or key < worst_sock[0]:
                worst_sock = (key, r["hole_id"], sx, sy)
        dev = profile_deviation(old, new, half)
        report[half] = dict(
            area_old=old.area, area_new=new.area,
            sym_outside_strip=sym_out, added=added, removed=removed,
            worst_vertex=worst, worst_xy=worst_xy,
            worst_socket=worst_sock, profile_dev=dev,
            npts=len(ring))
        print(f"[{half}] pts={len(ring)} area {old.area:.1f} -> "
              f"{new.area:.1f}  outside-strip symdiff={sym_out:.4f} mm^2")
        print(f"        in-strip: added {added:.1f} / removed "
              f"{removed:.1f} mm^2; worst cut vertex {worst:.2f} mm "
              f"at {worst_xy}")
        print(f"        profile vs step table: max dev {dev:.3f} mm")
        print(f"        socket nearest boundary: {worst_sock[1]} "
              f"dist {worst_sock[0]:.2f} mm (dome r 2.75 -> spare "
              f"{worst_sock[0] - 2.75:.2f})")
    return report


if __name__ == "__main__":
    main()
