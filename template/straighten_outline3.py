#!/usr/bin/env python3
"""pcb_outline3 v2.4.2: replace the OUTER-END and FRONT edge chains of
pcb_outline3 with straight-line fits (see OUTLINE3_NOTES.md addendum and
DESIGN_NOTES §17.15).

Why: outline3 kept outline2 (= v1 panel-scan trace) point-for-point
outside the stair strip.  Those chains carry trace artefacts that the
split-board mat photos (7378/7379) disprove:
  * short end: a fake "plateau" at y 140.5-140.8 (x 84-98), a wide dip
    at x 68-74, and a tangled blob in the MCU corner zone (x 92-113,
    boundary diving to y 132.1).  Photo: the end edge is ONE straight
    line with a single small semicircular notch (the notch cuts INTO
    the board, so straightening over it only adds clearance).
  * long end: same pattern (valley x 70-77 = the notch, corner tangle
    in the MCU zone x 86-113, front-corner spike to y 12.35).
  * front edges: 0.3-1.0mm wander + corner spikes on both halves.
The wiggly chains fed cavity = outset(pcb, 0.5), so every part whose
inner wall follows the cavity (side_band rims, top_frame lower band
under the plate lip, plate bridge fill) inherited the noise.

Fit rule (per §17.15): least squares over the clean straight-run points
of each edge, then shift outward only as far as needed so that no fit
point pokes more than 0.1mm beyond the line -> the cavity (line + 0.5)
keeps >= 0.4mm clearance to every genuine traced edge point.
Excluded spans (photo-disproven artefacts) are listed per edge in the
printed report; clearances against ALL outline2 points are reported so
the exclusions are auditable.

The stair strip (§17.12) and the back edge are NOT touched.
"""
import csv
import numpy as np
from shapely.geometry import Polygon, Point

BASE = "/home/hatch/workspace/7spromax-case"
EPS = 0.1  # max allowed poke-out of a genuine point beyond the fit line


def load_csv(path):
    return np.loadtxt(path, delimiter=",", skiprows=1)


def lsq_line(t, v):
    """v = a + b*t least squares."""
    A = np.vstack([np.ones_like(t), t]).T
    (a, b), *_ = np.linalg.lstsq(A, v, rcond=None)
    return a, b


def fit_edge(pts, tsel, v_of, outward_sign, label):
    """pts: (N,2) trace points; tsel: boolean mask of fit points;
    v_of: returns (t, v) arrays; outward_sign: +1 if outward = +v.
    Returns (a, b, report) with the clamp applied."""
    t, v = v_of(pts[tsel])
    print(f"  [{label}] fit points: "
          + ", ".join(f"({x:.2f},{y:.2f})" for x, y in pts[tsel]))
    a, b = lsq_line(t, v)
    dev = outward_sign * (v - (a + b * t))  # >0: point pokes beyond line
    shift = max(0.0, dev.max() - EPS)
    a += outward_sign * shift
    print(f"  [{label}] fit n={len(t)} line v={a:.3f}{b:+.5f}*t "
          f"max_poke_before_clamp={dev.max():.3f} shift={shift:.3f}")
    return a, b


def clearance_report(pts, a, b, v_of, outward_sign, label):
    """min cavity clearance (0.5 - poke) over ALL given trace points."""
    t, v = v_of(pts)
    poke = outward_sign * (v - (a + b * t))
    clr = 0.5 - poke
    i = int(np.argmin(clr))
    print(f"  [{label}] worst cavity clearance vs ALL trace pts in span: "
          f"{clr[i]:.2f}mm at (x={pts[i][0]:.2f}, y={pts[:,1][i]:.2f})")
    return clr


def find_idx(ring, xy, tol=0.02):
    d = np.hypot(ring[:, 0] - xy[0], ring[:, 1] - xy[1])
    i = int(np.argmin(d))
    assert d[i] < tol, f"anchor {xy} not found (nearest {d[i]:.3f})"
    return i


def surgery_short(ring, front, end):
    """ring order: ...[B=34 (113.07,130.62)] -> back -> steps ->
    [F=77 (3.20,13.18)] -> front chain -> end chain -> blob -> B...
    Replace F..B with straight chains."""
    fa, fb = front
    ea, eb = end
    iB = find_idx(ring, (113.07, 130.62))
    iF = find_idx(ring, (3.20, 13.18))
    assert iB < iF
    # corner C1 = intersection of front line x=fa+fb*y and end line y=ea+eb*x
    # x = fa + fb*(ea + eb*x) -> x*(1 - fb*eb) = fa + fb*ea
    xc = (fa + fb * ea) / (1 - fb * eb)
    yc = ea + eb * xc
    c2 = (113.07, ea + eb * 113.07)
    fstart = (fa + fb * 13.18, 13.18)
    new = np.vstack([ring[iB:iF + 1],
                     [fstart, (xc, yc), c2]])
    print(f"  short: kept ring[{iB}..{iF}] ({iF - iB + 1} pts); "
          f"Fstart={fstart} C1=({xc:.2f},{yc:.2f}) C2={c2}")
    return new


def surgery_long(ring, front, end):
    """ring order: ...[F=17 (3.17,128.00)] -> steps/back -> [B=84
    (113.21,13.23)] -> corner tangle -> end chain -> front tangle -> F...
    Replace B..F with straight chains (B -> C2 -> C1 -> front -> F)."""
    fa, fb = front
    ea, eb = end
    iF = find_idx(ring, (3.17, 128.00))
    iB = find_idx(ring, (113.21, 13.23))
    assert iF < iB
    xc = (fa + fb * ea) / (1 - fb * eb)
    yc = ea + eb * xc
    c2 = (113.21, ea + eb * 113.21)
    fend = (fa + fb * 128.00, 128.00)
    tail = [c2, (xc, yc)]
    if np.hypot(fend[0] - ring[iF][0], fend[1] - ring[iF][1]) > 0.01:
        tail.append(fend)  # else Fend coincides with the anchor vertex
    new = np.vstack([ring[iF:iB + 1], tail])
    print(f"  long: kept ring[{iF}..{iB}] ({iB - iF + 1} pts); "
          f"C2={c2} C1=({xc:.2f},{yc:.2f}) Fend={fend}")
    return new


def main():
    for half in ("short", "long"):
        print(f"===== {half}")
        ring3 = load_csv(f"{BASE}/template/pcb_outline3_{half}.csv")
        ring2 = load_csv(f"{BASE}/template/pcb_outline2_{half}.csv")
        old = Polygon([tuple(p) for p in ring3])
        if half == "short":
            # --- end edge: y = a + b*x ; outward = +y
            # fit span: the clean straight run only (y>=137.9 drops the
            # corner climb (8.01,136.89),(9.03,137.76); x 64..80 = notch
            # span (inward, harmless), x>=80 = plateau complex
            # (photo-disproven), so the run is x 8..64)
            m = (ring3[:, 0] >= 8) & (ring3[:, 0] <= 64) & \
                (ring3[:, 1] >= 137.9)
            end = fit_edge(ring3, m, lambda p: (p[:, 0], p[:, 1]), +1,
                           "short end")
            span = ring2[(ring2[:, 0] >= 8) & (ring2[:, 0] <= 80) &
                         (ring2[:, 1] > 130)]
            clearance_report(span, *end, lambda p: (p[:, 0], p[:, 1]), +1,
                             "short end (genuine span x8..80)")
            # --- front edge: x = a + b*y ; outward = -x
            # run points y 13..132, x<=3.8 (drops the (4.08,129.50)
            # spikelet and the corner spike y>132)
            m = (ring3[:, 1] >= 13) & (ring3[:, 1] <= 132) & \
                (ring3[:, 0] <= 3.8)
            front = fit_edge(ring3, m, lambda p: (p[:, 1], p[:, 0]), -1,
                             "short front")
            span = ring2[(ring2[:, 0] < 6) & (ring2[:, 1] >= 10) &
                         (ring2[:, 1] <= 132)]
            clearance_report(span, *front, lambda p: (p[:, 1], p[:, 0]), -1,
                             "short front")
            new_ring = surgery_short(ring3, front, end)
        else:
            # --- end edge: y = a + b*x ; outward = -y (board is y>=edge)
            # fit span: run x 10.5..84, y 4.5..6 (drops the (9.68,5.94)
            # corner climb, the notch points y>6, and the tangle x>84)
            m = (ring3[:, 0] >= 10.5) & (ring3[:, 0] <= 84) & \
                (ring3[:, 1] >= 4.5) & (ring3[:, 1] <= 6.0)
            end = fit_edge(ring3, m, lambda p: (p[:, 0], p[:, 1]), -1,
                           "long end")
            span = ring2[(ring2[:, 0] >= 8) & (ring2[:, 0] <= 86) &
                         (ring2[:, 1] < 13)]
            clearance_report(span, *end, lambda p: (p[:, 0], p[:, 1]), -1,
                             "long end (genuine span x8..86)")
            # --- front edge: the traced front "edge" is already ONE
            # straight segment (2.84,2.62)->(3.17,128.00); there are no
            # intermediate trace points to fit.  Adopt that segment's
            # line as-is (poke of its endpoints = 0 by construction).
            front = (2.84 - (3.17 - 2.84) / (128.00 - 2.62) * 2.62,
                     (3.17 - 2.84) / (128.00 - 2.62))
            print(f"  [long front] segment line x={front[0]:.3f}"
                  f"{front[1]:+.5f}*y (through (2.84,2.62),(3.17,128.00))")
            span = ring2[(ring2[:, 0] < 6) & (ring2[:, 1] >= 10) &
                         (ring2[:, 1] <= 125)]
            clearance_report(span, *front, lambda p: (p[:, 1], p[:, 0]), -1,
                             "long front")
            new_ring = surgery_long(ring3, front, end)
        new = Polygon([tuple(p) for p in new_ring])
        assert new.is_valid, f"{half}: new polygon invalid"
        assert new.geom_type == "Polygon"
        # stair strip invariance: symmetric difference inside the strip == old
        from shapely.geometry import box
        if half == "short":
            strip = box(3.2, -5, 113.7, 45.0)
        else:
            strip = box(3.2, 128.0, 113.7, 220.0)
        sd = old.intersection(strip).symmetric_difference(
            new.intersection(strip)).area
        # sockets containment (same test as make_outline3)
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
        print(f"  {half}: pts {len(ring3)} -> {len(new_ring)}; "
              f"area {old.area:.1f} -> {new.area:.1f}; "
              f"stair-strip symdiff={sd:.4f} mm^2; "
              f"worst socket margin {worst[0]:.2f}mm ({worst[1]})")
        out = f"{BASE}/template/pcb_outline3_{half}.csv"
        with open(out, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["x_mm", "y_mm"])
            for x, y in new_ring:
                w.writerow([f"{x:.3f}", f"{y:.3f}"])
        print(f"  wrote {out}")


if __name__ == "__main__":
    main()
