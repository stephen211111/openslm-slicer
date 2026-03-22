"""
OpenSLM Slicer — Portfolio Demo
================================
Author: Stefan Dobrowolski
License: MIT (wrapper) | LGPL-2.1 (pyslm library)

Overview
--------
This script demonstrates the core workflow of preparing a 3D CAD model (STL)
for Selective Laser Melting (SLM) — a powder-bed metal Additive Manufacturing
(AM) process. The pipeline mirrors what commercial AM pre-processing software
(e.g. Magics, Amphyon) does under the hood:

  1. Load & orient the part in the build chamber
  2. Slice the mesh into 2-D cross-sections (one per layer)
  3. Generate laser scan vectors (hatching) for each layer
  4. Assign laser process parameters (BuildStyle)
  5. Analyse scan-path statistics (path length, jump length, build time)
  6. Visualise the result

Why each step matters
---------------------
- Layer slicing determines dimensional accuracy along Z.
- Hatch strategy affects residual stress, porosity, and surface finish.
- Scan-vector sorting minimises thermal gradients (fewer cracks / warping).
- Build-time estimation drives cost modelling for quoting.
"""

import numpy as np
import pyslm
import pyslm.visualise
import pyslm.analysis
import pyslm.geometry
from pyslm import hatching


# =============================================================================
# 1. Part setup
# =============================================================================

# Create a Part object — the root entity that wraps the Trimesh mesh and
# exposes slicing helpers.  The string label is user-defined metadata.
solid_part = pyslm.Part("frameGuide")

# Point to the included test model.  PySLM supports any watertight STL.
solid_part.setGeometry("pyslm/models/frameGuide.stl")

# Position the part origin inside the build chamber (X, Y, Z in mm).
# Keeping X/Y away from the plate edge avoids recoater collisions.
solid_part.origin = [5.0, 10.0, 0.0]

# Rotate 30° around Z so scan vectors don't always run parallel to part
# boundaries — a common practice to reduce stress concentration.
solid_part.rotation = np.array([0, 0, 30])

# Snap the lowest point of the bounding box to Z = 0 (the base plate).
solid_part.dropToPlatform()

print("Bounding box (mm) [xmin, xmax, ymin, ymax, zmin, zmax]:")
print(" ", solid_part.boundingBox)

# =============================================================================
# 2. Hatcher configuration — Island (Checkerboard) strategy
# =============================================================================
# The island strategy divides each layer into small square "islands" that are
# scanned in a randomised order.  Compared with simple back-and-forth hatching
# it distributes heat more evenly, reducing residual stress.

hatcher = hatching.BasicIslandHatcher()

# Island width (mm): each checkerboard cell is 3 × 3 mm.
# Smaller islands → better stress distribution but more jump overhead.
hatcher.islandWidth = 3.0

# Stripe width (mm): used as fallback when the layer area is narrow.
hatcher.stripeWidth = 5.0

# Hatch angle (°): the angle of the parallel scan lines within each island.
# Rotating this by ~66.7° per layer is standard practice to spread texture.
hatcher.hatchAngle = 10

# volumeOffsetHatch (mm): inward offset between the contour lines and the
# hatch fill — prevents the hatch from overlapping the part boundary.
hatcher.volumeOffsetHatch = 0.08

# spotCompensation (mm): half the laser spot diameter.  The contour is shrunk
# by this amount so the melt pool centre lands on the nominal part surface.
hatcher.spotCompensation = 0.06

# numInnerContours: concentric inward contour passes before the hatch fill.
# More contours → better surface finish at the cost of scan time.
hatcher.numInnerContours = 2

# numOuterContours: contour passes outside the part boundary (skin pass).
hatcher.numOuterContours = 1

# Sort method: AlternateSort reverses the scan direction on every other
# vector, which reduces the laser jump distance and therefore scan time.
hatcher.hatchSortMethod = hatching.AlternateSort()

# =============================================================================
# 3. Slicing — obtain the 2-D cross-section at height z
# =============================================================================
# getVectorSlice() intersects the mesh with the horizontal plane z = z_pos
# and returns a list of closed Shapely polygons (outer boundaries + holes).
# simplificationFactor collapses short collinear segments — useful for STLs
# with many small triangles that would produce redundant contour vertices.

z_pos = 1.0  # layer height (mm)

geom_slice = solid_part.getVectorSlice(z_pos, simplificationFactor=0.1)

# =============================================================================
# 4. Hatching — generate laser scan vectors for this layer
# =============================================================================
# hatch() takes the 2-D polygon slice and returns a Layer object containing:
#   - ContourGeometry  : the border scan passes
#   - HatchGeometry    : the infill scan vectors as (x0,y0)→(x1,y1) pairs

layer = hatcher.hatch(geom_slice)

# =============================================================================
# 5. Assign process parameters (BuildStyle + Model)
# =============================================================================
# Every LayerGeometry must reference a Model ID (mid) and BuildStyle ID (bid).
# These map to entries in the machine build file header that store the laser
# parameters for each scan type.

# Assign both contour and hatch geometries to model 1, build style 1.
for geom in layer.geometry:
    geom.mid = 1
    geom.bid = 1

# BuildStyle encodes the laser parameters for this scan strategy.
# Typical SLM contour parameters for stainless steel 316L:
#   Power ~100–150 W, Speed ~600–800 mm/s, Point Distance ~40–60 µm
build_style = pyslm.geometry.BuildStyle()
build_style.bid = 1
build_style.laserSpeed = 200   # mm/s  — continuous-wave scan velocity
build_style.laserPower = 200   # W     — laser output power
build_style.jumpSpeed  = 5000  # mm/s  — repositioning speed (no lasing)

# Group the BuildStyle under a Model.  Multiple models can coexist in one
# build (e.g. different alloys or parameter sets for support vs. part).
model = pyslm.geometry.Model()
model.mid = 1
model.buildStyles.append(build_style)

# =============================================================================
# 6. Analysis — path statistics and build-time estimate
# =============================================================================
# These metrics feed into cost modelling and machine scheduling.

total_scan_mm  = pyslm.analysis.getLayerPathLength(layer)
total_jump_mm  = pyslm.analysis.getLayerJumpLength(layer)
layer_time_s   = pyslm.analysis.getLayerTime(layer, [model])

print(f"\nLayer analysis (z = {z_pos:.1f} mm):")
print(f"  Scan path length : {total_scan_mm:.1f} mm")
print(f"  Jump distance    : {total_jump_mm:.1f} mm  (laser off, repositioning)")
print(f"  Estimated time   : {layer_time_s:.2f} s")

# Jump distance as a fraction of total motion is a useful efficiency metric.
# A high ratio means the hatcher wastes time repositioning — worth optimising.
efficiency = total_scan_mm / (total_scan_mm + total_jump_mm) * 100
print(f"  Scan efficiency  : {efficiency:.1f}%  (higher is better)")

# =============================================================================
# 7. Visualisation
# =============================================================================
# plot() renders the scan vectors in the order they will be executed.
# - plotOrderLine=True draws a thin line connecting consecutive vector starts
#   so you can visually inspect the scan sequence and spot inefficient routing.
# - plotArrows shows arrowheads on each vector (slower for dense layers).

pyslm.visualise.plot(layer, plot3D=False, plotOrderLine=True, plotArrows=False)
