# Environment Tag: nanobrag-partiality-2025-12-26

## Summary
Fixed SQUARE lattice factor sincg evaluation to use fractional Miller index offsets (h-h0, k-k0, l-l0) in float64 precision.

## Patch Applied
- File: `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/partiality_fix.patch`
- Target: `src/nanobrag-torch/src/nanobrag_torch/simulator.py`
- Lines modified: 283-304 (SQUARE branch in compute_physics_for_position)

## Changes Made
1. **SQUARE lattice factor fix** (simulator.py:294-304):
   - Changed from using integer Miller indices `h, k, l` directly
   - Now computes fractional offsets `delta_h = (h - h0)`, etc.
   - Promotes deltas to `torch.float64` before calling `sincg`
   - Casts result back to simulator dtype to preserve precision
   - Prevents sincg collapse at integer Miller indices

2. **Enforcement test** (tests/architecture/test_nanobrag_partiality.py):
   - Created `test_square_lattice_applies_ncells`
   - Verifies intensity scales by (Na·Nb·Nc)^2 for N_cells=(Na,Nb,Nc)
   - Compares baseline (1,1,1) vs (5,7,11) with 10% tolerance
   - ARCH-CONTRACT enforcement per docs/spec-db-core.md:70-110

## Rebuild Command
```bash
cd src/nanobrag-torch
python -m pip install -e .
```

## Git Status at Patch Time
```
# nanobrag-torch submodule
Modified: src/nanobrag_torch/simulator.py (lines 283-304)

# Main repository
Added: tests/architecture/test_nanobrag_partiality.py
```

## Validation
- Mapped test: Stage A baseline probe should show median f_latt ≈ Na·Nb·Nc (not ≈1e-4)
- Architecture test: pytest tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells
- Acceptance gates: DB-AT-028, DB-AT-029 should pass with partiality-corrected intensities

## Contract References
- ARCH-SIM-CONSTRUCTION-001: docs/spec-db-core.md:70-110
- Config preservation: docs/config_crosswalk.md:61-85
- Acceptance gates: docs/spec-db-conformance.md:139-172

---

# Environment Tag: simtbx-square-lattice-integral-norm-2026-01-06

## Summary
ARCH-SIM-CONSTRUCTION-001 C.35: Fixed nanobrag_torch SQUARE lattice normalization to use integral semantics (sum) rather than mean semantics (sum/oversample²).

## Patch Applied
- File: `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/square_lattice_steps_fix.patch`
- Targets:
  - `src/nanobrag-torch/src/nanobrag_torch/simulator.py` (lines 1086-1099)
  - `tests/architecture/test_nanobrag_partiality.py` (lines 43-129)

## Changes Made
1. **SQUARE lattice normalization fix** (simulator.py:1086-1099):
   - Modified `steps` calculation to exclude `oversample * oversample` when `CrystalShape.SQUARE`
   - For SQUARE: `steps = sources·phi_steps·mosaic_domains` (integral semantics)
   - For GAUSS/TOPHAT/ROUND: `steps = sources·phi_steps·mosaic_domains·oversample²` (mean semantics)
   - Added `steps_scalar` emission through `_partiality_stats` when debug hook enabled

2. **Architecture test enforcement** (test_nanobrag_partiality.py:43-129):
   - Enabled `collect_partiality_stats` debug config in both test runs
   - Added assertions to verify `steps_scalar` excludes `oversample²` for SQUARE shape
   - Tightened tolerance from 5% to 1% after normalization fix
   - Test now validates both the steps calculation and the (Na·Nb·Nc)² intensity ratio

## Rebuild Command
```bash
cd src/nanobrag-torch
python -m pip install -e .
```

## Git Status at Patch Time
```
# nanobrag-torch submodule
Modified: src/nanobrag_torch/simulator.py (lines 1086-1099)

# Main repository
Modified: tests/architecture/test_nanobrag_partiality.py (lines 43-129)
```

## Validation
After applying this fix:
1. Architecture test: `pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells`
   - Expected: `steps_scalar=1` (no oversample²), intensity ratio within 1% of `(Na·Nb·Nc)²`

2. Single-pixel probe: `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-06T010000Z --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1`
   - Expected: observed ratio ≈ 1.448e9 (within 1% of `(41·29·32)²`)

3. DB-AT-028/029 acceptance tests:
   - Expected: chi² drops sharply, ROI correlation improves toward spec

## Rationale
The previous implementation divided summed subpixel contributions by `oversample²`, treating the result as a mean. For GAUSS/TOPHAT/ROUND shapes with broad features, this is correct. However, SQUARE lattices produce narrow sincg peaks that are rarely sampled by the oversample grid at typical resolutions. The single subpixel carrying the `(Na·Nb·Nc)²` weight was being diluted by the oversample factor (e.g., 169× for oversample=13), causing 99.99% intensity loss. By using integral semantics (no oversample² division) for SQUARE, we preserve the correct lattice weighting.

Coverage analysis (`plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T150000Z/square_lattice_scaling.md`) showed 0/169 subpixels hit the central sincg lobe for the canonical test case, confirming the diagnosis.

## Contract References
- ARCH-SIM-CONSTRUCTION-001 Phase C.35: `plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md:450-457`
- Normative simulator contracts: `docs/spec-db-core.md:60-140`
- Finding: SIM-CONSTR-PARTIALITY-001

---

# Environment Tag: nanobrag-partiality-omega-2026-01-13

## Patch Applied
- **Date**: 2026-01-13T01:00:00Z
- **Initiative**: ARCH-SIM-CONSTRUCTION-001
- **Patch File**: `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/omega_compensation.patch`

## Description
Applied Phase C.39 omega-compensation patch to `src/nanobrag_torch/simulator.py`.

**Change**: When `crystal.shape == CrystalShape.SQUARE` and `oversample > 1`:
- Changed from last-value omega semantics to **shape-gated** omega application
- SQUARE: Apply omega (from center subpixel) **once after** the Riemann-sum aggregation
- Other shapes (GAUSS/TOPHAT/ROUND): Preserve existing last-value or per-subpixel omega semantics
- This restores the missing `(Na·Nb·Nc)²` lattice weight while maintaining integral semantics

## Files Modified
- `src/nanobrag_torch/simulator.py` (lines 1333-1418)
  - Added `is_square` branch to gate omega application strategy
  - SQUARE path: sum all subpixels, then apply center omega once (lines 1377-1391)
  - Added telemetry flags: `omega_applied_post_sum=True`, `square_used_riemann_sum=True`
  - Preserved trace fields: `trace_subpixel_F_total_sq_sum`, `trace_normalized_intensity`, `trace_subpixel_omega_last`
- `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py` (lines 303-309)
  - Added ingestion of `square_used_riemann_sum` telemetry flag

## Rebuild Command
The nanobrag-torch package is in PYTHONPATH from `src/`, so changes take effect immediately:
```bash
# Verify changes are live:
python -c "import nanobrag_torch.simulator; import inspect; print(inspect.getsourcefile(nanobrag_torch.simulator.Simulator))"
# Expected: /home/ollie/Documents/diffbragg_example_2/diffbragg_example/src/nanobrag_torch/simulator.py
```

## Validation Targets
- Architecture test: `tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells` (oversample=13, ≤1% tolerance)
- Probe script: `probe_square_lattice_scaling.py --n-cells 41 29 32 --oversample 13`
- Acceptance tests: DB-AT-028, DB-AT-029

## Expected Outcomes
- Probe normalized/raw intensity ratio → 1.0 (was 1e-6)
- Architecture test cpu/cuda ratios → (41·29·32)² = 1,447,650,304 within ≤1% (was 59% error)
- DB-AT-028 chi²/pixel initial → ≤100 (was 2.1e5)
- DB-AT-029 median ROI corr → ≥0.2 (was -0.053)

## SIM-CONSTR-PARTIALITY-001 Note
This patch implements the canonical omega placement for SQUARE lattices with oversample>1 per docs/spec-db-core.md:60-140 SCALE-009 contract and docs/architecture/calibration_scaling.md:80-145. The Lorentz solid-angle correction (`omega`) must be applied exactly once after the Riemann-sum accumulation to preserve the lattice weight `(Na·Nb·Nc)²`.
