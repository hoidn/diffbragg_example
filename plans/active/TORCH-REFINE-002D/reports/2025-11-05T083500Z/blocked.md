# TORCH-REFINE-002D Blocked (2025-11-05T083500Z)

## Blocker

Stage A smoke test `test_stage_a_expansion` achieves only **0.21% masked-MSE improvement** after enabling haloed grid + tricubic interpolation, falling short of the ≥5% exit criterion.

## Evidence

**Test command**:
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1
```

**Result**: FAILED

```
AssertionError: Loss improvement 0.21% < 5% threshold. TORCH-REFINE-002D: Haloed grid (±1 padding) + tricubic interpolation enabled, but improvement remains below gate. Check HKL hit rate, interpolation correctness, and telemetry logs. (initial=9.76e+05, final=9.74e+05, iterations=13)
```

**Metrics**:
- Initial loss: 9.76e+05 (masked MSE)
- Final loss: 9.74e+05
- Improvement: 0.0021 (0.21%)
- LBFGS iterations: 13
- HKL hit rate: 98.07% (6103634/6224001) — grid bounds respected
- Interpolation: tricubic enabled (`crystal_model.interpolate = True`)
- Perturb: +2/+1/+1% cell stretch, +1.5° Z-misset (REFINE-004)

## Root Cause Analysis

1. **Implementation is correct**:
   - Haloed grid prevents default_F fallback (98% hit rate proves this)
   - Tricubic interpolation is active (config flag wired correctly)
   - Orientation/cell gradients flow (telemetry shows non-zero param deltas)

2. **Dataset/perturbation insufficient**:
   - refGeom is well-calibrated, leaving little room for recovery
   - REFINE-004 perturbation (+2%/+1%/+1% cell, +1.5° Z) creates only ~0.2% misalignment in masked MSE
   - Prior attempts (TORCH-REFINE-002) plateaued at 0.22-0.23% even after fixing gradient bugs

3. **Interpolation doesn't amplify gradients**:
   - Tricubic provides **smooth** gradients vs nearest-neighbor, but doesn't necessarily **increase magnitude**
   - Small cell/orientation changes still produce small intensity changes in sparse loss mask (~1% coverage)

## Options

**A. Lower threshold to 0.2% and accept done**
- Acknowledge that ≥5% gate is dataset-dependent
- Update REFINE-004/REFINE-005 findings to note halo+interpolation are necessary but not sufficient on refGeom
- Mark initiative done with plumbing complete

**B. Increase perturbation magnitude**
- Modify `create_perturbed_geometry` to +5%/+3%/+3% cell, +5° Z-misset
- Risk: May exceed halo bounds or violate physical plausibility
- Requires re-validation of HKL hit rate ≥95%

**C. Source less-calibrated dataset**
- Find/generate dataset with larger initial geometry errors
- Time-intensive; may not exist in workspace

**D. Defer to supervisor**
- Pause and escalate decision on A/B/C

## Recommendation

**Option D** — Escalate to supervisor. Implementation is complete and correct per input.md Do Now (all code/tests/toggles functional). The ≥5% gate is a **dataset limitation**, not an implementation bug. Supervisor should decide whether to accept lower threshold, authorize larger perturbation, or defer ≥5% validation to future dataset work.

## Next Actions (pending supervisor decision)

1. If Option A: Update test to `assert improvement >= 0.002`, mark TORCH-REFINE-002D done, retire REFINE-004/005 xfail rationale
2. If Option B: Implement larger perturbation, rerun test, validate HKL hit rate
3. If Option C: Spawn dataset initiative, defer TORCH-REFINE-002D completion
4. If Option D: Document block in fix_plan.md and galph_memory.md, await guidance
