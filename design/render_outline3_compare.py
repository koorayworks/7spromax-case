#!/usr/bin/env python3
"""guide_outline3_compare.png — outline2 (noisy) vs outline3 (clean
steps) overlay for both halves."""
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, "/home/hatch/workspace/7spromax-case/template")
from make_outline3 import load_outline, STEPS

BASE = "/home/hatch/workspace/7spromax-case"
fig, axes = plt.subplots(2, 2, figsize=(15, 10))
for row, half in enumerate(("short", "long")):
    old = load_outline(f"{BASE}/template/pcb_outline2_{half}.csv")
    new = load_outline(f"{BASE}/template/pcb_outline3_{half}.csv")
    for col, (xlim, ylim, title) in enumerate([
            ((0, 118), None, f"{half}: full outline"),
            ((0, 118), None, f"{half}: stair band zoom")]):
        ax = axes[row][col]
        ox, oy = np.array(old.exterior.coords).T
        nx, ny = np.array(new.exterior.coords).T
        ax.plot(ox, oy, color="#d33", lw=0.9, label="outline2 (scan, noisy)")
        ax.plot(nx, ny, color="#1a7", lw=1.6, label="outline3 (clean steps)")
        # step levels
        for (sx, lv) in STEPS[half]:
            ax.axhline(lv, color="#1a7", lw=0.4, ls=":")
        ax.set_xlim(*xlim)
        if half == "short":
            ax.set_ylim(-6, 148 if col == 0 else 55)
        else:
            ax.set_ylim(100 if col == 1 else -4, 182)
            if col == 1:
                ax.set_ylim(125, 182)
        ax.set_aspect("equal")
        ax.set_title(title)
        ax.legend(loc="best", fontsize=8)
        ax.grid(alpha=0.25)
        ax.set_xlabel("x (case mm)")
        ax.set_ylabel("y (case mm)")
fig.suptitle("PCB outline: outline2 (red, groove-noise) vs outline3 "
             "(green, rectangular steps)", fontsize=13)
fig.tight_layout()
fig.savefig(f"{BASE}/design/guide_outline3_compare.png", dpi=110)
print("saved design/guide_outline3_compare.png")
