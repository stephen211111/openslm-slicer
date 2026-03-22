"""
generate_docs_images.py
-----------------------
Generates example slice images for the project documentation.
Run once; outputs go to docs/images/.

Demonstrates three scan strategies at three different layer heights:
  - StripeHatcher  (limits max scan-vector length)
  - BasicIslandHatcher  (checkerboard, reduces residual stress)
  - Alternating plain hatch  (simplest strategy for reference)
"""

import sys
import os

# Prevent the local pyslm/ submodule from shadowing the installed package.
_root = os.path.dirname(os.path.abspath(__file__))
sys.path = [p for p in sys.path if p != "" and os.path.normcase(p) != os.path.normcase(_root)]

import numpy as np
import matplotlib
matplotlib.use("Agg")  # non-interactive backend — write to files
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors

import pyslm
import pyslm.visualise
import pyslm.analysis
import pyslm.geometry
from pyslm import hatching

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
MODEL_PATH = os.path.join(_root, "pyslm", "models", "frameGuide.stl")
OUT_DIR = os.path.join(_root, "docs", "images")
os.makedirs(OUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Part setup (shared across all examples)
# ---------------------------------------------------------------------------
part = pyslm.Part("frameGuide")
part.setGeometry(MODEL_PATH)
part.origin = [5.0, 10.0, 0.0]
part.rotation = np.array([0, 0, 30])
part.dropToPlatform()

bbox = part.boundingBox  # [xmin, xmax, ymin, ymax, zmin, zmax]
part_height_mm = bbox[5]
print(f"Part bounding box: {bbox}")
print(f"Part height: {part_height_mm:.2f} mm")

# Slice heights: early / mid / near-top layers
z_levels = {
    "bottom (z=1 mm)":     1.0,
    "middle (z={:.0f} mm)".format(part_height_mm * 0.5): round(part_height_mm * 0.5, 1),
    "top (z={:.0f} mm)".format(part_height_mm * 0.85):   round(part_height_mm * 0.85, 1),
}

# ---------------------------------------------------------------------------
# Helper: build a hatcher for each strategy
# ---------------------------------------------------------------------------
def make_stripe_hatcher():
    h = hatching.StripeHatcher()
    h.stripeWidth = 5.0
    h.hatchAngle = 10
    h.volumeOffsetHatch = 0.08
    h.spotCompensation = 0.06
    h.numInnerContours = 2
    h.numOuterContours = 1
    h.hatchSortMethod = hatching.AlternateSort()
    return h

def make_island_hatcher():
    h = hatching.BasicIslandHatcher()
    h.islandWidth = 3.0
    h.stripeWidth = 5.0
    h.hatchAngle = 10
    h.volumeOffsetHatch = 0.08
    h.spotCompensation = 0.06
    h.numInnerContours = 2
    h.numOuterContours = 1
    h.hatchSortMethod = hatching.AlternateSort()
    return h

STRATEGIES = {
    "Stripe": make_stripe_hatcher,
    "Island (Checkerboard)": make_island_hatcher,
}

# ---------------------------------------------------------------------------
# Helper: render a single layer to axes
# ---------------------------------------------------------------------------
def render_layer(ax, layer, title):
    """Draw contours (blue) and hatch vectors (orange) on ax."""
    for geom in layer.geometry:
        coords = geom.coords  # numpy array (N, 2) or (N*2, 2) depending on type
        if isinstance(geom, pyslm.geometry.HatchGeometry):
            # Hatch vectors: pairs of points — draw as line segments
            pts = geom.coords.reshape(-1, 2, 2)  # (M, 2, 2)
            for seg in pts:
                ax.plot(seg[:, 0], seg[:, 1], color="#E8731A", lw=0.4, alpha=0.7)
        elif isinstance(geom, pyslm.geometry.ContourGeometry):
            pts = geom.coords  # closed polygon path
            ax.plot(pts[:, 0], pts[:, 1], color="#2A6EBB", lw=1.0)

    ax.set_aspect("equal")
    ax.set_title(title, fontsize=9, pad=4)
    ax.set_xlabel("X (mm)", fontsize=7)
    ax.set_ylabel("Y (mm)", fontsize=7)
    ax.tick_params(labelsize=6)
    ax.grid(True, lw=0.3, alpha=0.4)

# ---------------------------------------------------------------------------
# 1. Strategy comparison grid  (3 heights × 2 strategies)
# ---------------------------------------------------------------------------
z_list = list(z_levels.items())
strat_names = list(STRATEGIES.keys())

fig, axes = plt.subplots(
    len(z_list), len(strat_names),
    figsize=(len(strat_names) * 4.5, len(z_list) * 4.0),
)
fig.suptitle("SLM Layer Slice — Scan Strategy Comparison\n(frameGuide.stl)", fontsize=12, y=1.01)

row_stats = []

for row, (z_label, z) in enumerate(z_list):
    for col, strat_name in enumerate(strat_names):
        ax = axes[row][col]
        geom_slice = part.getVectorSlice(z, simplificationFactor=0.1)
        if not geom_slice:
            ax.text(0.5, 0.5, "No geometry", ha="center", va="center")
            continue

        hatcher_instance = STRATEGIES[strat_name]()
        layer = hatcher_instance.hatch(geom_slice)

        render_layer(ax, layer, f"{strat_name}\n{z_label}")

        # Collect stats for bottom-left cell annotation
        for geom in layer.geometry:
            geom.mid = 1
            geom.bid = 1
        bs = pyslm.geometry.BuildStyle()
        bs.bid = 1
        bs.laserSpeed = 200
        bs.laserPower = 200
        bs.jumpSpeed = 5000
        m = pyslm.geometry.Model()
        m.mid = 1
        m.buildStyles.append(bs)

        path_mm  = pyslm.analysis.getLayerPathLength(layer)
        jump_mm  = pyslm.analysis.getLayerJumpLength(layer)
        time_s   = pyslm.analysis.getLayerTime(layer, [m])
        eff      = path_mm / (path_mm + jump_mm) * 100 if (path_mm + jump_mm) > 0 else 0

        ax.annotate(
            f"scan: {path_mm:.0f} mm | jump: {jump_mm:.0f} mm\n"
            f"time: {time_s:.2f} s | eff: {eff:.0f}%",
            xy=(0.02, 0.02), xycoords="axes fraction",
            fontsize=6, color="#333333",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.7),
        )

        if row == 0 and col == 0:
            pass  # legend added globally below

# Global legend
hatch_patch   = mpatches.Patch(color="#E8731A", label="Hatch fill vectors")
contour_patch = mpatches.Patch(color="#2A6EBB", label="Contour boundary pass")
fig.legend(handles=[hatch_patch, contour_patch], loc="lower center",
           ncol=2, fontsize=9, bbox_to_anchor=(0.5, -0.02))

plt.tight_layout()
out_path = os.path.join(OUT_DIR, "slice_strategy_comparison.png")
fig.savefig(out_path, dpi=150, bbox_inches="tight")
plt.close(fig)
print(f"Saved: {out_path}")

# ---------------------------------------------------------------------------
# 2. Scan-order plot  (island hatcher, mid layer, showing order line)
# ---------------------------------------------------------------------------
z_mid = round(part_height_mm * 0.5, 1)
geom_slice = part.getVectorSlice(z_mid, simplificationFactor=0.1)
island_h = make_island_hatcher()
layer_mid = island_h.hatch(geom_slice)

# Use pyslm's built-in plot to a file
fig2, ax2 = plt.subplots(figsize=(7, 6))

# Replicate pyslm.visualise.plot logic: draw order line manually
prev_x, prev_y = None, None
for i, geom in enumerate(layer_mid.geometry):
    if isinstance(geom, pyslm.geometry.HatchGeometry):
        pts = geom.coords.reshape(-1, 2, 2)
        for j, seg in enumerate(pts):
            color = plt.cm.plasma(j / max(len(pts) - 1, 1))
            ax2.plot(seg[:, 0], seg[:, 1], color=color, lw=0.5)
            if prev_x is not None:
                ax2.plot([prev_x, seg[0, 0]], [prev_y, seg[0, 1]],
                         color="grey", lw=0.25, alpha=0.4, linestyle="--")
            prev_x, prev_y = seg[1, 0], seg[1, 1]
    elif isinstance(geom, pyslm.geometry.ContourGeometry):
        ax2.plot(geom.coords[:, 0], geom.coords[:, 1], color="#2A6EBB", lw=1.2)

sm = plt.cm.ScalarMappable(cmap="plasma", norm=mcolors.Normalize(vmin=0, vmax=1))
sm.set_array([])
cbar = fig2.colorbar(sm, ax=ax2, fraction=0.03, pad=0.02)
cbar.set_label("Scan order (first → last)", fontsize=8)
cbar.ax.tick_params(labelsize=7)

ax2.set_aspect("equal")
ax2.set_title(
    f"Island Hatcher — scan-vector order\n(frameGuide.stl, z = {z_mid} mm)",
    fontsize=10,
)
ax2.set_xlabel("X (mm)", fontsize=8)
ax2.set_ylabel("Y (mm)", fontsize=8)
ax2.grid(True, lw=0.3, alpha=0.4)

plt.tight_layout()
out_path2 = os.path.join(OUT_DIR, "slice_scan_order.png")
fig2.savefig(out_path2, dpi=150, bbox_inches="tight")
plt.close(fig2)
print(f"Saved: {out_path2}")

# ---------------------------------------------------------------------------
# 3. Multi-layer stack overview  (10 evenly spaced layers, island hatcher)
# ---------------------------------------------------------------------------
n_layers = 10
z_values = np.linspace(1.0, part_height_mm * 0.95, n_layers)
hatch_angles = np.linspace(0, 180, n_layers, endpoint=False)  # rotate per layer

fig3, axes3 = plt.subplots(2, 5, figsize=(18, 7))
fig3.suptitle(
    "Multi-layer scan paths — Island Hatcher with 18° rotation per layer\n(frameGuide.stl)",
    fontsize=11,
)

for idx, (z_val, angle) in enumerate(zip(z_values, hatch_angles)):
    ax = axes3[idx // 5][idx % 5]
    geom_slice = part.getVectorSlice(z_val, simplificationFactor=0.1)
    if not geom_slice:
        ax.axis("off")
        continue

    h = make_island_hatcher()
    h.hatchAngle = float(angle)
    layer = h.hatch(geom_slice)
    render_layer(ax, layer, f"z = {z_val:.1f} mm\n(θ = {angle:.0f}°)")

plt.tight_layout()
out_path3 = os.path.join(OUT_DIR, "slice_multilayer.png")
fig3.savefig(out_path3, dpi=150, bbox_inches="tight")
plt.close(fig3)
print(f"Saved: {out_path3}")

print("\nAll documentation images generated successfully.")
print(f"Output directory: {OUT_DIR}")
