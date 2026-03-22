# OpenSLM Slicer

A Python portfolio project exploring pre-processing algorithms for **Selective Laser Melting (SLM)** — a powder-bed metal Additive Manufacturing (AM) process used for printing stainless steel, titanium, aluminium alloys, and other metals layer by layer with a focused laser.

Built on top of the open-source [PySLM](https://github.com/drlukeparry/pyslm) library by Luke Parry.

---

## What this project demonstrates

| Domain | Skill |
|--------|-------|
| Computational geometry | Mesh slicing, polygon offsetting, Clipper-based Boolean operations |
| AM process knowledge | Hatch strategies, BuildStyle parameters, support structures |
| Scientific Python | NumPy, Shapely, Trimesh, Matplotlib |
| Software architecture | Class hierarchies, document-graph pattern, iterator protocol |
| Performance | Multiprocessing for layer-parallel slicing, Cython/C++ extension usage |

---

## The SLM pre-processing pipeline

```
STL mesh
   │
   ▼
Part  ──── orient, scale, dropToPlatform()
   │
   ▼
getVectorSlice(z)  ──── Trimesh Boolean intersection → Shapely polygons
   │
   ▼
Hatcher.hatch()  ──── contour offsets + infill vectors via PyClipper
   │                  strategies: Stripe | Island | Custom sinusoidal
   ▼
Layer  ──── ContourGeometry + HatchGeometry (x0,y0→x1,y1 pairs)
   │
   ├── BuildStyle  ── laser power (W), scan speed (mm/s), spot size (µm)
   │
   ├── analysis  ── path length, jump distance, build-time estimate
   │
   ├── export  ── Renishaw MTT | EOS SLI | DMG Mori REA | SLM Solutions
   │
   └── visualise  ── Matplotlib scan-vector plots, exposure heatmaps
```

---

## Repository layout

```
.
├── main.py              # Annotated end-to-end demo (stripe → island strategy)
├── pyslm/               # PySLM library (git submodule, LGPL-2.1)
│   ├── pyslm/
│   │   ├── core.py          # Part, DocumentObject, dependency graph
│   │   ├── geometry/        # Layer, BuildStyle, Model data classes
│   │   ├── hatching/        # Hatch strategies + sorting algorithms
│   │   ├── support/         # Block/truss support structure generation
│   │   ├── analysis/        # Build-time estimation, scan iterators
│   │   ├── visualise.py     # Matplotlib rendering helpers
│   │   └── export.py        # Machine build-file exporters
│   ├── examples/            # 17 runnable example scripts
│   └── models/              # Sample STL files (frameGuide.stl, etc.)
└── LICENSE              # MIT (this wrapper) | LGPL-2.1 (pyslm submodule)
```

---

## Quick start

```bash
# 1. Clone with the pyslm submodule
git clone --recurse-submodules https://github.com/stephen211111/openslm-slicer.git
cd openslm-slicer

# 2. Install dependencies
pip install PythonSLM trimesh shapely numpy matplotlib

# 3. Run the annotated demo
python main.py
```

---

## Key concepts explained

### Hatch strategies

| Strategy | Description | Use case |
|----------|-------------|----------|
| `StripeHatcher` | Divides the layer into parallel stripes; limits max scan-vector length | General-purpose, minimises long vectors that cause warping |
| `BasicIslandHatcher` | Checkerboard grid; islands scanned in randomised order | Reduces residual stress; preferred for complex geometries |
| Custom (sinusoidal) | User-defined curved scan paths | Research into novel strategies |

### Scan-vector sorting

After hatching, vectors are reordered to minimise the **jump distance** (laser-off repositioning moves). The included sort algorithms are:

- **AlternateSort** — reverses direction on every other vector (bidirectional)
- **LinearSort** — sweeps monotonically in one direction
- **FlipSort** — groups vectors by proximity

### BuildStyle parameters

| Parameter | Typical range | Effect |
|-----------|--------------|--------|
| `laserPower` | 100–400 W | Melt pool size and depth |
| `laserSpeed` | 200–2000 mm/s | Energy density (J/mm³) |
| `spotCompensation` | 0.04–0.1 mm | Dimensional accuracy |
| `pointDistance` | 20–80 µm | Overlap between exposure points (pulsed mode) |

---

## License

- `main.py` and all files in this wrapper repository: **MIT License** — see [LICENSE](LICENSE)
- `pyslm/` submodule: **GNU Lesser General Public License v2.1** — see [pyslm/LICENSE](pyslm/LICENSE)

Original PySLM library © Luke Parry — https://github.com/drlukeparry/pyslm
