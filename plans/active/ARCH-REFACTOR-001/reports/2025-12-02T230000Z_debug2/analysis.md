# ARCH-REFACTOR-001 Phase D.3 Batch 2 — Second Debug Analysis

## Problem Summary
Ralph's commit fd64e9f3 attempted to fix the bragg_before computation but DID NOT follow the instruction correctly. Both DB-AT tests still FAIL with identical signatures:
- test_db_at_028: chi²/pixel initial 209817 >> 100 bound
- test_db_at_029: median ROI correlation before -0.037 << 0.2 floor

## Root Cause
**Geometry Mismatch Between "Before" and "After" States**

The fixture has THREE distinct geometry states:
1. **Baseline geometry** (lines 122-124): Original geometry from dataload
   - `baseline_crystal`, `baseline_detector`, `baseline_beam`

2. **Perturbed geometry** (lines 126-128): Baseline + small perturbations for refinement
   - `perturbed_crystal`, `perturbed_detector`, `perturbed_beam`
   - Created via `create_perturbed_geometry(baseline_*)`

3. **Refined geometry**: Result of RefinementEngine.run() with perturbed geometry as starting point
   - Stored in `bragg_final` (line 163) extracted from `engine._artifacts["stage_a"].bragg_full`

**The Bug:**
Line 175 uses:
```python
bragg_before = mapping_context.bragg_zero_iter  # Wrong geometry!
```

But `mapping_context.bragg_zero_iter` was computed with **BASELINE** geometry (lines 195-198 of dbex/vis/mapping.py):
```python
bragg_zero_iter, diagnostics = simulate_forward_once(
    inputs=inputs,
    detector=dataload.detector,      # ← BASELINE detector
    beam=dataload.beam,              # ← BASELINE beam
    crystal=dataload.crystal,        # ← BASELINE crystal
    ...
)
```

This creates a **3-state mismatch**:
- `bragg_before` = forward model from **baseline** geometry (wrong!)
- Refinement starts from **perturbed** geometry
- `bragg_after` (`bragg_final`) = forward model from **refined** geometry

The test expects:
- `bragg_before` = forward model from **perturbed** geometry (before refinement)
- `bragg_after` = forward model from **refined** geometry (after refinement)

**Why Tests Fail:**
1. Chi² calculation (line 331 of test): Uses `bragg_before` (baseline geometry) vs target
   - Baseline geometry is FAR from correct geometry → chi²/pixel = 2.1e5 instead of ~10
2. ROI correlation (line 465): Computes correlation between `bragg_before` (baseline) and target
   - Baseline forward model anticorrelates with data → median correlation = -0.037 instead of ~0.3

## Evidence
1. **mapping_context construction** (test fixture lines 94-99):
   - Uses `refgeom_dataload` which contains **baseline** geometry
   - No perturbations applied to geometry passed to `build_mapping_stage_a_context`

2. **Refinement context construction** (lines 148-157):
   - Uses **perturbed** geometry: `perturbed_detector`, `perturbed_beam`, `perturbed_crystal`
   - Engine refines from this perturbed starting point

3. **Test metrics** (pytest log):
   - chi²/pixel initial = 209817 (expected ~10-50 for perturbed geometry)
   - median ROI correlation before = -0.037 (expected ~0.2-0.4 for perturbed geometry)
   - These values are consistent with baseline geometry being ~180° rotation or large translation away

## Correct Solution
Replace line 175 with a `simulate_forward_once` call using **PERTURBED** geometry:

```python
bragg_before = simulate_forward_once(
    inputs=refinement_inputs,  # Same inputs as refinement
    detector=perturbed_detector,  # ← PERTURBED geometry (before refinement)
    beam=perturbed_beam,          # ← PERTURBED geometry
    crystal=perturbed_crystal,    # ← PERTURBED geometry
    experiment=mapping_context.experiment,  # Experiment object
    device=device_obj,  # Torch device
)
```

This will:
1. Compute forward model from perturbed geometry (refinement starting point)
2. Match the geometry state that RefinementEngine begins refining from
3. Give reasonable chi² (~10-50) and correlation (~0.2-0.4) for "before" metrics
4. Allow tests to validate chi² reduction and correlation improvement correctly

## Why Ralph's Fix Was Incorrect
Ralph changed the **comment** on line 173 but kept the **code** on line 175 unchanged:
```python
# ARCH-REFACTOR-001 Phase D.3 Batch 2 bugfix: Use pre-computed bragg_zero_iter from mapping_context
# instead of non-existent mapping_context attribute access. The mapping context already computed
# the zero-iteration forward model via build_mapping_stage_a_context, so reuse it directly.
bragg_before = mapping_context.bragg_zero_iter  # Zero-iteration forward (baseline geometry)
```

The comment incorrectly states "reuse it directly" — this is wrong because:
1. `mapping_context.bragg_zero_iter` exists and can be accessed (no AttributeError)
2. BUT it contains the forward model for the **wrong geometry** (baseline instead of perturbed)
3. The test needs "before refinement" = perturbed geometry, not "baseline zero-iteration" = baseline geometry

Ralph may have been confused by:
- Earlier galph_memory note saying "bragg_zero_iter doesn't exist" (that was based on JSON export, not the actual object)
- Comment in input.md suggesting the attribute was missing (actually it exists but has wrong semantics)

## Next Action
Correct Do Now must:
1. Import `simulate_forward_once` from `dbex.nanobrag_bridge` (may already be imported for other uses)
2. Replace line 175 with `simulate_forward_once(...)` call using perturbed geometry
3. Keep the emit_mapping_context_diagnostics fixes Ralph already made (those are correct)
4. Run 2/2 tests expecting PASSED with reasonable chi²/correlation values

## Expected Metrics After Fix
- chi²/pixel initial: ~10-50 (perturbed geometry is close to correct geometry)
- median ROI correlation before: ~0.2-0.4 (perturbed forward model correlates with data)
- chi²/pixel final: ~5-20 (refinement improves from perturbed starting point)
- median ROI correlation after: ~0.4-0.7 (refinement improves correlation)
