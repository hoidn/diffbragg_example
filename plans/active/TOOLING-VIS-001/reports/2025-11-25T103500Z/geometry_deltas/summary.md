# Geometry Zero-Point Comparison

**Base case:** `refgeom`

**Cases compared:** refgeom, idx_refined, golden_refined

## Per-Case Geometry

### refgeom

- **Unit cell:** a=27.3758 Å, b=32.0658 Å, c=34.4664 Å, α=88.77°, β=71.63°, γ=68.19°
- **Detector distance:** 382.22 mm
- **Beam center:** fast=-217.57 mm, slow=-212.77 mm
- **Wavelength:** 0.976800 Å

### idx_refined

- **Unit cell:** a=27.4055 Å, b=32.0993 Å, c=34.4976 Å, α=88.64°, β=71.54°, γ=68.04°
- **Detector distance:** 382.22 mm
- **Beam center:** fast=-217.57 mm, slow=-212.77 mm
- **Wavelength:** 0.976800 Å

### golden_refined

- **Unit cell:** a=27.3642 Å, b=32.0577 Å, c=34.4693 Å, α=88.67°, β=71.55°, γ=68.12°
- **Detector distance:** 382.21 mm
- **Beam center:** fast=-217.51 mm, slow=-212.79 mm
- **Wavelength:** 0.976800 Å

## Deltas vs Base Case

### idx_refined − refgeom

- **Unit cell deltas:** Δa=0.0297 Å, Δb=0.0335 Å, Δc=0.0313 Å, Δα=0.132°, Δβ=0.094°, Δγ=0.145°
- **U rotation angle:** 0.9469°
- **A* Frobenius norm:** 7.775055e-04
- **Detector distance delta:** 0.000 mm
- **Beam center shift:** 0.000 mm
- **Panel normal dot product:** 1.000000
- **Beam direction dot product:** 1.000000

### golden_refined − refgeom

- **Unit cell deltas:** Δa=0.0116 Å, Δb=0.0081 Å, Δc=0.0030 Å, Δα=0.096°, Δβ=0.081°, Δγ=0.066°
- **U rotation angle:** 0.9724°
- **A* Frobenius norm:** 8.188339e-04
- **Detector distance delta:** 0.012 mm
- **Beam center shift:** 0.055 mm
- **Panel normal dot product:** 1.000000
- **Beam direction dot product:** 1.000000

## Interpretation

- **U rotation angle** shows orientation drift between experiments.
- **A* Frobenius norm** quantifies total reciprocal lattice drift.
- **Beam center shift** and **detector distance delta** show physical detector movements.
- Dot products near 1.0 indicate parallel directions (good alignment).
