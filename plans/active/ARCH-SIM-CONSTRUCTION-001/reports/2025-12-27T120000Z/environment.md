# Environment Freeze Trail — ARCH-SIM-CONSTRUCTION-001 Partiality Fix

## Patch Application

**Date:** 2025-12-27T120000Z
**Initiative:** ARCH-SIM-CONSTRUCTION-001 (Simulator Construction Convention Alignment)
**Finding:** SIM-CONSTR-PARTIALITY-001 (Square lattice sincg precision requirement)

### Submodule: nanobrag-torch

**Commit:** 9c0d6ed3
**Message:** ARCH-SIM-CONSTRUCTION-001: Fix SQUARE lattice sincg precision (SIM-CONSTR-PARTIALITY-001)

**Files Modified:**
- `src/nanobrag_torch/simulator.py` (lines 295-316: SQUARE lattice sincg path)

**Patch Location:**
- `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/partiality_fix.patch`

### Change Summary

Modified `compute_physics_for_position` SQUARE branch to:
1. Compute fractional HKL deltas (`delta_h`, `delta_k`, `delta_l`) in `torch.float64`
2. Convert `Na`, `Nb`, `Nc` to float64 tensors on correct device using `torch.as_tensor`
3. Evaluate `sincg(torch.pi * delta, N)` entirely in float64
4. Downcast final `F_latt` product to simulator dtype before combining with `F_cell`

**Rationale:** Near integer Miller indices, float32 sincg collapsed to ~1e-4 instead of ~Na·Nb·Nc (≈38,048 for typical mosaic domains), causing Stage A/|F|²·F_latt²·LP ratios to approach zero.

### Rebuild Commands

```bash
cd /home/ollie/Documents/diffbragg_example_2/diffbragg_example/src/nanobrag-torch
python -m pip install -e .
```

**Rebuild Output:** `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T120000Z/nanobrag_rebuild.log`

### Environment Tag

**Tag:** `nanobrag-partiality-2025-12-27`
**Python:** 3.9 (simtbx conda environment)
**PyTorch:** 2.4.1+cu121
**nanobrag-torch:** 0.1.0 (editable install)

### Verification Plan

1. **Enforcement Test:** `tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells`
   - Compares simulator intensity with `N_cells=(1,1,1)` vs `(41,29,32)`
   - Asserts ratio matches `(Na·Nb·Nc)^2 ±5%`

2. **Stage A Baseline Probe:**
   - Command: `python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode baseline --stage-a-mosaic-domains 16 --collect-hkl-stats --collect-spot-profiles --collect-orientation-metrics --collect-physics-ledger --collect-partiality-ledger --collect-simulator-partiality-stats`
   - Expected: `f_latt` medians approach Na·Nb·Nc, Stage A/|F|²·F_latt²·LP ratios approach 1

3. **DB-AT-028/029 Acceptance:**
   - Selectors: `tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"`
   - Expected: chi²/pixel initial ≤1e2, ROI correlation ≥0.2

### References

- **SPEC:** docs/spec-db-core.md:60-140 (lattice weighting contracts)
- **ARCH:** docs/config_crosswalk.md:61-118 (N_cells threading rules)
- **Finding:** docs/findings.md (SIM-CONSTR-PARTIALITY-001)
- **Patch:** plans/active/ARCH-SIM-CONSTRUCTION-001/patches/partiality_fix.patch
