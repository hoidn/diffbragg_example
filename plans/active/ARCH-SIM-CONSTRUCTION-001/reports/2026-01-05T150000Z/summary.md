# Ralph Loop Summary — 2026-01-05T150000Z

## Phase C.34 — Subpixel Coverage Analysis

### Turn Summary
Verified existing trace slicing implementation already in place. Ran single-pixel probe with trace instrumentation enabled. Coverage metrics definitively show 0 of 169 subpixels hit the central sincg lobe. The (Na·Nb·Nc)² deficit stems from subpixel sampling coverage, not sincg kernel bugs or normalization. Next step: fix subpixel offset grid or redesign accumulation to weight by coverage.

Artifacts: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T150000Z/` (square_lattice_probe.log, square_lattice_scaling.{json,md}, pytest_partiality.log)

## Problem & SPEC/ARCH Alignment

**Problem**: DB-AT-028/029 remain red after C.33 subpixel-centering patch. Single-pixel probe ratio only 0.25% of expected `(Na·Nb·Nc)²` even though TRACE_PY shows correct `F_latt_a/b/c = 41/29/32`.

**SPEC/ARCH Contracts**:
- docs/spec-db-core.md:60-140 — SQUARE lattice must deliver `(Na·Nb·Nc)²` scaling
- SIM-CONSTR-PARTIALITY-001 — Square-lattice sincg must deliver `(Na·Nb·Nc)²` scaling

**Alignment**: Input.md Do Now requested per-subpixel coverage metrics to determine whether deficit originates from normalization or sampling. Existing code already implemented trace slicing (simulator.py:1533-1569), so no production changes needed — just ran the probe.

## Search & Existing Implementation Summary

Searched for:
- `partiality_stats\[` in simulator.py → found keys collected at lines 317-462
- `trace_pixel` debug flow → found slicing logic at lines 1533-1569
- `probe_square_lattice_scaling.py` consumption → lines 176-194 already consume trace tensors

**Finding**: Phase C.34 trace slicing code was already implemented by prior loop. Code paths:
- src/nanobrag-torch/src/nanobrag_torch/simulator.py:317-326 (delta_h/k/l, F_latt_a/b/c collection)
- simulator.py:391 (F_total_squared_pre_lorentz collection)
- simulator.py:1533-1569 (trace slicing when both trace_pixel and collect_partiality_stats enabled)
- plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py:176-194 (trace tensor consumption)

## Code Analysis Performed

Verified existing implementation by reading:
1. simulator.py:1471-1570 — `_apply_debug_output` slicing logic
2. simulator.py:1452-1465 — call site passes `oversample` parameter correctly
3. probe_square_lattice_scaling.py:450-544 — Phase C.34 coverage analysis block

**DMI Ledger Evidence** (from probe run):
- **Producer**: `_compute_physics_for_position` SQUARE branch → generates per-subpixel delta_{h,k,l}, F_latt_{a,b,c}, F_total_squared_pre_lorentz
- **Hydration**: `_apply_debug_output` slices to trace_pixel → creates `trace_delta_*` and `trace_F_latt_*` keys
- **Consumer**: probe script lines 456-498 → computes central lobe counts and intensity share

**Observed Evidence at Consumer**:
- Total subpixels: 169 (oversample=13 → 13²)
- Central lobe thresholds: |Δh|<0.024, |Δk|<0.034, |Δl|<0.031
- **Subpixels hitting all three thresholds: 0 (0.00%)**
- min_abs_delta_h = 0.000 (h-axis samples Δ=0)
- min_abs_delta_k = 5.38e-02 (k-axis never reaches threshold)
- min_abs_delta_l = 5.38e-02 (l-axis never reaches threshold)
- Intensity share from central lobe: **0.00%**

**First Divergence**: The oversample grid spans `(-(N-1)/(2N), ..., +(N-1)/(2N))` for slow/fast detector axes but does not align with reciprocal-space HKL axes. For N_cells=(41,29,32), the C.33 centering guaranteed h-axis samples Δ=0, but k/l axes stay offset by ≈0.054 (≈5 × their respective thresholds). The deficit occurs because **reciprocal-space fractional HKL offsets depend on the crystal orientation relative to the detector**, not just detector subpixel positions.

**Next Boundary**: The `steps` normalization (dividing by sources × mosaic × φ × oversample²) assumes all subpixels contribute equally. If the sincg peak is sparse, the normalization dilutes the central-lobe contribution by ~1/169. Next decision gate: either (a) fix subpixel offset computation to track reciprocal-space HKL deltas instead of detector coordinates, or (b) weight subpixel contributions by their sincg amplitude before averaging.

## Changes Made

**None**. The trace slicing code was already complete. This loop only executed the probe and enforcement test to gather coverage evidence.

Files verified (no edits):
- src/nanobrag-torch/src/nanobrag_torch/simulator.py:1533-1569 (trace slicing)
- plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py:450-544 (coverage analysis)

## Tests and Static Checks

**Probe command**:
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py \
  --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T150000Z \
  --n-cells 41 29 32 --oversample 13 --phi-count 1 --mosaic-count 1 --spixels 1 --fpixels 1 \
  | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T150000Z/square_lattice_probe.log
```

**Result**: Probe completed successfully. Coverage table shows 0% central-lobe hits. JSON and Markdown outputs written.

**Enforcement test**:
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' \
pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells \
  | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T150000Z/pytest_partiality.log
```

**Result**: FAILED (both cpu and cuda). Observed ratio 3.56e6 vs expected 1.45e9 (0.25% of spec). Expected failure given 0% coverage.

**Static checks**: Not applicable (no code changes).

## Docs & Ledgers Updates

- **docs/fix_plan.md**: Added 2026-01-05T150000Z attempt entry documenting coverage findings
- **Implementation plan**: No update needed (Phase C.34 was already planning-only)
- **docs/findings.md**: SIM-CONSTR-PARTIALITY-001 should be updated to note coverage issue (deferred to next loop)

## Next Step

The coverage evidence is decision-carrying: **0% of subpixels hit the central sincg lobe because the oversample grid is computed in detector coordinates but HKL fractional deltas depend on the crystal orientation in reciprocal space**.

The supervisor must choose:
1. **Option A (Reciprocal-space oversample)**: Modify `_compute_physics_for_position` to compute subpixel offsets in reciprocal space (HKL deltas) instead of detector coordinates, guaranteeing central-lobe samples for every pixel.
2. **Option B (Weighted accumulation)**: Keep detector-coordinate oversample but weight each subpixel's contribution by its `|F_latt|²` before dividing by `steps`, so the central-lobe samples dominate even if sparse.

**Recommended**: Option B is safer (does not change the oversample semantic) and directly addresses the normalization assumption that all subpixels contribute equally. Next Do Now should modify the `steps` normalization to weight by sincg amplitude.
