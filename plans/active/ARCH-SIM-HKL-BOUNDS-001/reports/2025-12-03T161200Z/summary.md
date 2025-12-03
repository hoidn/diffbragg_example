# ARCH-SIM-HKL-BOUNDS-001 Phase A.1 — Probe Execution Summary

**Date**: 2025-12-03T161200Z
**Initiative**: ARCH-SIM-HKL-BOUNDS-001 (Stage-A / Mapping HKL Alignment)
**Phase**: A.1 — Baseline HKL / A* Gap Measurement
**Actor**: Ralph (implementation loop)

## Executive Summary

The reciprocal lattice alignment probe **PASSED** the spec tolerance (max|ΔA*| = 4.4e-09 Å⁻¹ << 1e-6 Å⁻¹). This eliminates the hypothesis that the 0% HKL in-bounds coverage observed in DIAG-NANOBRAGG-OVERSAMPLE-001 Phase F stems from a bug in the basic dxtbx→nanobrag_torch crystal A* mapping.

The zero-parameter nanobrag_torch Crystal model correctly reproduces the dxtbx-derived reciprocal lattice matrix to within floating-point precision when using the canonical refGeom small-detector smoke fixture with no calibration overrides.

**Key Finding**: The HKL offset root cause lies **downstream** of the A* alignment—either in HKL grid indexing conventions, structure-factor grid bounds, or the coordinate transforms used during HKL lookups inside the simulator.

## Probe Results

### Dataset Configuration
- **Fixture**: refGeom small-detector smoke fixture
- **Detector Size**: 1024×1024 (cropped from full 2527×2463)
- **Experiment**: `sp.proc/refGeom_small/refGeom_small.expt`
- **MTZ**: `scaled.mtz` (raw intensities, no calibration refinement)
- **Device**: CPU (NANOBRAGG_DISABLE_COMPILE=1 for determinism)
- **N_cells applied**: False (baseline probe, no calibration metadata)

### A* Comparison Metrics

| Metric | Value | Tolerance | Status |
|--------|-------|-----------|--------|
| max\|ΔA*\| | 4.44e-09 Å⁻¹ | ≤ 1e-6 Å⁻¹ | **PASS** |
| mean\|ΔA*\| | 2.18e-09 Å⁻¹ | — | — |

**Per-column max\|Δ\|** (a*, b*, c*):
- a*: 4.44e-09 Å⁻¹
- b*: 1.56e-09 Å⁻¹
- c*: 4.16e-09 Å⁻¹

### Interpretation

The dxtbx and nanobrag_torch reciprocal lattices agree to within ~4 parts in 10⁹, which is well within double-precision numerical noise. Per docs/spec-db-core.md:72, the zero-point Stage-A invariant `A*(0) ≈ A*_mapping` is satisfied.

This result **contradicts** the initial hypothesis that the HKL offset (queries in `h∈[28,47], k∈[28,51], l∈[37,59]` vs grid bounds `h∈[-24,24], k∈[-28,28], l∈[-31,31]`) stems from a MOSFLM injection bug, incorrect basis order, or missing 2π factor in the crystal configuration factories.

## CLI Invocation

```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
python plans/active/ARCH-SIM-HKL-BOUNDS-001/bin/probe_crystal_hkl_alignment.py \
  --detector-size small \
  --out-dir plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/2025-12-03T161200Z/ \
  --device cpu
```

**Exit Status**: 0 (PASS)

## Artifacts Generated

1. **hkl_alignment_metrics.json** — Quantitative comparison (A* matrices, deltas, per-column statistics)
2. **hkl_alignment_summary.txt** — Human-readable prose summary with acceptance criterion evaluation
3. **probe_run.log** — Full stdout/stderr capture (includes DataLoad warnings and probe status)
4. **summary.md** (this file) — Initiative-level summary documenting findings and next actions

All artifacts stored under: `plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/2025-12-03T161200Z/`

## Implications for ARCH-SIM-HKL-BOUNDS-001

### Hypothesis Refinement

The probe eliminates the "A* misalignment" hypothesis. The actual bug must be in one of these downstream components:

1. **HKL grid indexing** — The structure-factor grid may be using a different index origin or stride convention than the simulator's HKL query logic.
2. **Grid bounds enforcement** — The grid envelope `h∈[-24,24], k∈[-28,28], l∈[-31,31]` may not account for the coordinate system used by the nanobrag_torch HKL calculator.
3. **Coordinate transforms** — The mapping from scattering vectors (q) to Miller indices (h, k, l) may apply an incorrect offset, rotation, or scaling factor.
4. **MOSFLM column injection interaction** — While A* itself is correct, the MOSFLM columns may be used inconsistently between grid construction and HKL lookup paths.

### Recommended Phase B Actions

1. **Instrument HKL lookups** — Add telemetry inside `nanobrag_torch.models.crystal` or the structure-factor grid accessor to capture the first few HKL queries and their reciprocal-space coordinates (q_x, q_y, q_z).
2. **Inspect grid construction** — Review `build_structure_factor_grid` and the grid's coordinate system definition to confirm the index→reciprocal-space mapping.
3. **Compare grid bounds vs queries** — Overlay the HKL query distribution from DIAG-NANOBRAGG-OVERSAMPLE-001 Phase F against the grid's declared envelope to visualize the offset.
4. **Check MOSFLM column usage** — Verify that both the grid construction and the HKL calculator use the same A* columns (either from `crystal.get_A()` or from MOSFLM injection, but not a mix).

## Exit Criteria Update

**Phase A.1 Status**: ✅ **Complete** (probe executed, artifacts captured, findings documented)

**Exit Criterion 1** (ARCH-SIM-HKL-BOUNDS-001):
- **Target**: `max_abs_diff(A*_nanobrag, A*_dxtbx) ≤ 1e-6 Å⁻¹`
- **Achieved**: `max_abs_diff = 4.44e-09 Å⁻¹` ✅
- **Interpretation**: A* alignment is correct; the HKL offset must be addressed in Phase B via grid/indexing fixes, not crystal config changes.

**Next Action**: Phase B — Root cause isolation (focus on HKL grid indexing, not A* mapping).

## References

- **SPEC**: docs/spec-db-core.md:64-80 (baseline crystal state and A* invariant)
- **SPEC**: docs/spec-db-conformance.md:261-285 (DB-AT-027/028/029 zero-point requirements)
- **Diagnostic Evidence**: docs/findings.md:51 (DIAG-OVERSAMPLE-001 HKL coverage stats)
- **Implementation Plan**: plans/active/ARCH-SIM-HKL-BOUNDS-001/implementation.md
- **Probe Source**: plans/active/ARCH-SIM-HKL-BOUNDS-001/bin/probe_crystal_hkl_alignment.py
