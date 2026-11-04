#!/usr/bin/env python3
"""pcb_outline3 v2.4.2 (part 2): straighten the BACK edge chains.

Runs AFTER straighten_outline3.py (end/front).  See DESIGN_NOTES
§17.15 and OUTLINE3_NOTES.md addendum.

short: the back chain between the end corner and the long run carried
a zigzag (113.07,130.62)->(113.06,129.31)->(112.48,129.60)->
(113.05,122.78)->(113.20,126.85)->(113.78,125.10) inherited from the
panel-scan trace (it wandered around the tact area).  The genuine run
is the segment (113.78,125.10)-(113.64,45.00); fit x = a + b*y through
those two points and replace the whole stretch, recomputing the
end x back corner as the intersection of the end line and the back
line.  All zigzag points lie INSIDE the fitted line (max genuine
poke = 0 at the fit points), so the cavity keeps >= 0.5mm clearance
to every genuine traced point of the run.

long: the back side is a rectangular cutout (wall at x~=103.2) with
three tabs reaching the back plane x~=113.4 (tab A y 107.9-113.1,
TRRS tab y 77.9-85.9, and the full-height run below the step at
y~=58).  The trace wobbles +-0.4mm on the wall, follows the TRRS
jack footprint on the tab top edge (dips up to 1.0mm inward), and
draws a fake thin spike at the step (111.58,58.01)->(112.45,58.59)->
(113.37,76.75)->(113.21,13.23); the mat photo shows one clean step.
Fit both planes (wall line, back line) by LSQ over the genuine run
points, clamp so no genuine point pokes > 0.1mm beyond its line
(cavity clearance >= 0.4mm), and rebuild the chain as clean
rectangles through the tab root levels of the trace.  The corner
radius fan at the stair x back corner (y 164.45-164.88) and the
block edge x=103.40 are kept as-is (smooth / already straight).
"""
import numpy as np
from shapely.geometry import Polygon, Point
import csv

BASE = "/home/hatch/workspace/7spromax-case"
EPS = 0.1


def load_csv(path):
    return np.loadtxt(path, delimiter=",", skiprows=1)


def lsq(t, v):
    A = np.vstack([np.ones_like(t), t]).T
    (a, b), *_ = np.linalg.lstsq(A, v, rcond=None)
    return a, b


def fit_x_of_y(pts, outward, label):
    """x = a + b*y through pts [(x,y)...]; outward=+1 for +x.
    Clamp: shift so max poke beyond line <= EPS."""
    P = np.array(pts, dtype=float)
    a, b = lsq(P[:, 1], P[:, 0])
    poke = outward * (P[:, 0] - (a + b * P[:, 1]))
    shift = max(0.0, poke.max() - EPS)
    a += outward * shift
    print(f"  [{label}] line x={a:.3f}{b:+.6f}*y  fitpts="
          + ", ".join(f"({x:.2f},{y:.2f})" for x, y in pts)
          + f"  maxpoke={poke.max():.3f} shift={shift:.3f}")
    return a, b


def find_idx(ring, xy, tol=0.03):
    d = np.hypot(ring[:, 0] - xy[0], ring[:, 1] - xy[1])
    i = int(np.argmin(d))
    assert d[i] < tol, f"anchor {xy} not found (nearest {d[i]:.3f})"
    return i


def check(old, new, half):
    assert new.is_valid and new.geom_type == "Polygon", half
    rows = list(csv.DictReader(open(f"{BASE}/template/pcb_sockets.csv")))
    worst = None
    for r in rows:
        if r["half"] != half:
            continue
        sx = float(r["meas_x_mm"] or r["dxf_x_mm"])
        sy = float(r["meas_y_mm"] or r["dxf_y_mm"])
        d = new.exterior.distance(Point(sx, sy))
        key = d if new.covers(Point(sx, sy)) else -d
        if worst is None or key < worst[0]:
            worst = (key, r["hole_id"])
    print(f"  {half}: area {old.area:.1f} -> {new.area:.1f}; "
          f"worst socket margin {worst[0]:.2f}mm ({worst[1]})")


def save(ring, half):
    out = f"{BASE}/template/pcb_outline3_{half}.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["x_mm", "y_mm"])
        for x, y in ring:
            w.writerow([f"{x:.3f}", f"{y:.3f}"])
    print(f"  wrote {out} ({len(ring)} pts)")


def do_short():
    print("===== short back")
    ring = load_csv(f"{BASE}/template/pcb_outline3_short.csv")
    old = Polygon([tuple(p) for p in ring])
    ba, bb = fit_x_of_y([(113.78, 125.10), (113.64, 45.00)], +1,
                        "short back")
    # end line from straighten_outline3: y = 138.008 + 0.00387 x
    ea, eb = 138.008, 0.00387
    # corner C3: x = ba + bb*(ea + eb*x) -> x*(1-bb*eb) = ba + bb*ea
    xc = (ba + bb * ea) / (1 - bb * eb)
    yc = ea + eb * xc
    print(f"  C3 (end x back corner) = ({xc:.2f},{yc:.2f})")
    iA = find_idx(ring, (3.60, 138.02))        # C1 (front x end)
    iB = find_idx(ring, (113.64, 45.00))       # run bottom anchor
    # ring order (circular): anchor(iB) -> stair -> front -> C1(iA)
    # -> C2 -> zigzag -> back to anchor.  Keep iB..iA, append C3.
    assert iB < iA
    new = np.vstack([ring[iB:iA + 1], [(xc, yc)]])
    newp = Polygon([tuple(p) for p in new])
    check(old, newp, "short")
    save(new, "short")


def do_long():
    print("===== long back")
    ring = load_csv(f"{BASE}/template/pcb_outline3_long.csv")
    old = Polygon([tuple(p) for p in ring])
    wa, wb = fit_x_of_y([(103.22, 86.38), (102.99, 107.60),
                         (103.00, 113.42), (103.00, 128.00),
                         (103.40, 128.00)], +1, "long cutout wall")
    ba, bb = fit_x_of_y([(113.47, 113.10), (113.46, 107.86),
                         (113.40, 85.91), (113.38, 77.92),
                         (113.21, 13.23)], +1, "long back plane")
    wall = lambda y: wa + wb * y
    back = lambda y: ba + bb * y
    # end line from straighten_outline3 (after clamp): y = 5.110+0.00012x
    ea, eb = 5.110, 0.00012
    xc = (ba + bb * ea) / (1 - bb * eb)
    yc = ea + eb * xc
    print(f"  C2' (end x back corner) = ({xc:.2f},{yc:.2f})")
    chain = [
        (wall(128.00), 128.00),
        (wall(112.83), 112.83), (back(113.10), 113.10),
        (back(107.86), 107.86), (wall(108.04), 108.04),
        (wall(86.38), 86.38), (back(85.91), 85.91),
        (back(77.92), 77.92), (wall(78.23), 78.23),
        (wall(58.32), 58.32), (back(58.01), 58.01),
        (xc, yc),
    ]
    iA = find_idx(ring, (103.40, 170.80))   # block edge top (kept side)
    # anchors in ring order: block edge (103.40,128.00) is ring[46];
    # old C2 (113.21,5.12) is ring[68]; chain replaces ring[46..68]
    iTop = find_idx(ring, (103.40, 128.00))
    iC2 = find_idx(ring, (113.21, 5.12))
    assert iTop < iC2
    new = np.vstack([ring[:iTop], chain, ring[iC2 + 1:]])
    newp = Polygon([tuple(p) for p in new])
    check(old, newp, "long")
    save(new, "long")


if __name__ == "__main__":
    do_short()
    do_long()
