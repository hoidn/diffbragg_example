# TORCH-REFINE-002D Turn Summary (2025-11-05T083500Z)

## Implementation Complete

Implemented halo support and tricubic HKL interpolation per input.md Do Now:

### Code Changes

1. **dbex/nanobrag_bridge.py:559-692** — Extended `build_structure_factor_grid` with optional `halo=True` parameter
   - Adds ±1 padding to h/k/l axes when enabled
   - Updates metadata with `has_halo` flag
   - Preserves data envelope bounds in logging for diagnostics

2. **dbex/nanobrag_refinement.py:147-154** — Extended `RefinementConfig` with `enable_hkl_interpolation: bool = False`
   - Defaults to nearest-neighbor (False) to protect datasets without halo
   - Documented TORCH-REFINE-002D/REFINE-005 rationale

3. **dbex/nanobrag_refinement.py:412-416, 613-617** — Wired interpolation toggle to `Crystal.interpolate`
   - Honors `config.enable_hkl_interpolation` in both LBFGS closure and final render paths
   - Replaces hardcoded `interpolate = False` with config-driven control

4. **tests/dbex/test_torch_refine_smoke.py:174-192** — Updated `hkl_data` fixture to request haloed grid
   - `build_structure_factor_grid(..., halo=True)`
   - Documented TORCH-REFINE-002D purpose

5. **tests/dbex/test_torch_refine_smoke.py:220-230** — Enabled interpolation in Stage A config
   - `enable_hkl_interpolation=True` in `RefinementConfig`
   - Updated docstring to reflect tricubic + halo usage

6. **tests/dbex/test_torch_refine_smoke.py:317-338** — Removed xfail guard, enabled hard ≥5% assertion
   - Replaced `pytest.xfail(...)` with `assert improvement >= 0.05`
   - Added logging of achieved improvement for telemetry tracking

### Test Results

**Selector**: `pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`

**Collection**: 1 test collected ✓

**Execution**: **FAILED** — improvement 0.21% < 5% threshold

**Metrics**:
- Initial loss: 9.76e+05
- Final loss: 9.74e+05
- Improvement: 0.21% (0.0021)
- Iterations: 13 (LBFGS)
- HKL hit rate: 98.07% (6103634/6224001) — haloed grid working correctly
- Interpolation: tricubic enabled via `crystal_model.interpolate = True`

**Status**: Tricubic interpolation + haloed grid **implementation is correct** and functioning (98% hit rate confirms halo prevents out-of-bounds fallback), but the refGeom dataset with REFINE-004 perturbation (+2/+1/+1% cell, +1.5° Z-misset) achieves only 0.21% improvement — insufficient to clear the ≥5% gate.

## Analysis

The prior TORCH-REFINE-002 attempts documented that the refGeom dataset with REFINE-004 perturbation plateaus around 0.22-0.23% improvement even after fixing gradient flow issues. The hypothesis that tricubic interpolation would unlock additional gradient strength appears **incorrect** for this dataset/perturbation combination.

**Possible root causes**:
1. Perturbation magnitude too small — cell stretch +2%/+1%/+1% and +1.5° Z-misset may not create enough misalignment to yield 5% masked-MSE recovery headroom
2. Dataset too well-calibrated — refGeom geometry is close to optimal, so LBFGS has limited improvement space
3. Interpolation gradients present but weak — tricubic provides smooth gradients, but magnitude may still be insufficient for large recovery steps
4. Loss mask coverage too sparse — only ~1% of pixels contribute to loss, so small parameter changes have diluted impact

## Options

**A. Accept implementation complete; lower threshold**
- Mark TORCH-REFINE-002D done with telemetry/plumbing exit criteria satisfied
- Document that ≥5% gate requires either larger perturbation or less-calibrated dataset
- Update REFINE-004/REFINE-005 findings to note that halo+interpolation are necessary but not sufficient for 5% gate on refGeom

**B. Increase perturbation magnitude**
- Modify `create_perturbed_geometry` to apply larger cell stretch (e.g., +5%/+3%/+3%) and orientation misset (e.g., +5° Z)
- Risk: Larger perturbations may push fractional HKL further from grid even with halo, or violate physical plausibility
- Requires validation that HKL hit rate remains ≥95% with increased perturbation

**C. Source alternative dataset**
- Find or generate a dataset with poorer initial calibration (larger geometry errors) so Stage A recovery has more headroom
- Time-intensive; may not be available in workspace

**D. Supervisor escalation**
- Pause implementation and request supervisor guidance on whether to proceed with Option A/B/C
- Document blocked state in fix_plan.md Attempts History with test log + metrics

## Recommendation

**Option D (escalate)** — Implementation is functionally correct (halo+interpolation work as designed), but the ≥5% gate cannot be met with current dataset/perturbation. Supervisor should decide whether to:
1. Accept lower threshold (e.g., ≥0.2%) and mark done
2. Authorize larger perturbation attempt
3. Defer ≥5% gate to future dataset initiative

Do not proceed with Option B (larger perturbation) without supervisor approval per input.md "If Blocked" guidance.

## Artifacts

- `collect_stage_a.log` — 1 test collected
- `pytest_stage_a.log` — FAILED (improvement 0.21% < 5%)
- `summary.md` (this file)

---

### Turn Summary
Implemented HKL grid halo padding and tricubic interpolation toggle to restore gradient flow for Stage A perturbed geometry refinement.
Haloed grid + interpolation implementation is correct and functioning (98% HKL hit rate validates halo prevents default_F fallback), but achieved only 0.21% improvement vs ≥5% exit criterion — blocked by dataset/perturbation limitation rather than implementation bug.
Next: Supervisor decision required per blocked.md — accept lower threshold (≥0.2%) and close, authorize larger perturbation trial, or defer ≥5% gate to future dataset work.
Artifacts: plans/active/TORCH-REFINE-002D/reports/2025-11-05T083500Z/ (collect_stage_a.log, pytest_stage_a.log, blocked.md)
