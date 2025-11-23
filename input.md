# ARCH-REFINE-FLOW-001 Phase D1c — Extract _run_stage_c_lbfgs + Wire All Helpers

## Summary
Extract `_run_stage_c_lbfgs` execution helper (~200 lines), wire all 3 Stage C helpers into `run_nanobrag_refinement`, replace inline code (~504 lines) with orchestration calls (~150 lines), and run comprehensive regression guard (small + full detector smokes).

## Mode
none

## Focus
ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase D1c: Stage C LBFGS execution + wiring)

## Branch
integration

## Mapped Tests
- `pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` (small detector, primary validation)
- `pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` (full detector, regression guard)

## Artifacts
plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d1c/

## Do Now

**Objective:** Extract final Stage C helper (`_run_stage_c_lbfgs`) containing LBFGS execution, final validation, improvement gate, best snapshot restore, final Bragg regeneration, and telemetry packaging. Wire all 3 helpers (params, closure, execution) into `run_nanobrag_refinement` inline Stage C section, reducing ~504 lines to ~150 lines orchestration. Validate via Stage C smoke tests (small + full detector).

**Context:**
- **Previous phases:**
  - D1a (loop i=227): `_build_stage_c_params` extracted (156 lines, 30 return keys)
  - D1b (loop i=228, JUST COMPLETED): `_build_stage_c_lbfgs_closure` extracted (298 lines, returns tuple of 2 callables)
- **Current inline Stage C location:** dbex/nanobrag_refinement.py lines ~3824-4328 (~504 lines total)
  - Lines 3824-3919: params initialization (~96 lines, EXTRACTED to _build_stage_c_params)
  - Lines 3920-4217: closure definition (~298 lines, EXTRACTED to _build_stage_c_lbfgs_closure)
  - Lines 4218-4328: LBFGS execution + final Bragg + telemetry (~110 lines, UNEXTRACTED — this phase)
  - **CRITICAL:** After helper extraction (D1a+D1b), inline code shifted to lines 4595-4794 (confirmed via Read tool)
- **Exact extraction target:** Lines 4595-4794 (~200 lines, increased from initial estimate due to final Bragg regeneration logic)
- **Helper insertion point:** After `_build_stage_c_lbfgs_closure` (currently at line 2894)
- **Wiring target:** `run_nanobrag_refinement` inline Stage C section (lines ~3824-4328, ~504 lines → ~150 lines after wiring)

**Known Scope Complexities (from Phase B bugfix history):**
1. Param dict key mismatches (e.g., `stage_c_params` vs `params`)
2. Telemetry nested access (`telemetry_state['chi_squared_best']` vs `chi_squared_best`)
3. Missing variable assignments propagated from params dict
4. Import corrections (nanobrag_torch.models.Detector/Crystal, nanobrag_torch.simulator.Simulator)

**Step-by-Step Protocol:**

### 1. Review Phase D1b Artifacts (5 min)
- Read `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d1b/decision.md`
- Verify helper2 signature: `Tuple[Callable[[List[int], bool], Tuple[torch.Tensor, torch.Tensor]], Callable[[], torch.Tensor]]`
- Confirm compilation PASSED, helper2 inserted at line 2894

### 2. Extract `_run_stage_c_lbfgs` Helper (60 min)

**Helper Signature (match Phase B pattern):**
```python
def _run_stage_c_lbfgs(
    config: RefinementConfig,
    device: torch.device,
    dtype: torch.dtype,
    param_values: Dict[str, Any],      # Unpacked: distance_offset_raw, stage_c_params, stage_c_optimizer, log_scale, cell deltas, angles, orientation_vec, baseline_misset_deg_tensor
    telemetry_state: Dict[str, Any],   # Unpacked: chi_squared_best_c, masked_mse_best_c, best_params_snapshot_c, iteration_count_c, loss_trace_sample/full_c, chi_squared_trace_sample/full_c, masked_mse_trace_sample/full_c, variance_floor_clamped/masked_pixels_c, perf_closure_evals/validation_runs/forward_times_ms_c
    stage_c_context: Dict[str, Any],   # Unpacked: stage_c_use_warm_cache, stage_c_cache_mode, stage_c_roi_mode_label, stage_c_roi_count_total/sampled, baseline_detector_distances, sampled_panel_ids
    compute_loss_stage_c: Callable,
    closure_stage_c: Callable,
    crystal,                           # dxtbx Crystal
    hkl_grid: torch.Tensor,
    hkl_metadata: Dict,
    detector,                          # dxtbx Detector
    beam,                              # dxtbx Beam
    inputs: DataLoad,
    canonical_baseline: Dict[str, Any],
    stage_a_ctx: Optional[StageAContext],
    n_panels: int,
) -> Dict[str, Any]:
    """
    Execute Stage C LBFGS optimization, final validation, improvement gate,
    best snapshot restore, final Bragg regeneration, and telemetry packaging.

    Returns dict with keys:
        - 'status_c': str ('ok', 'early_stop', 'error')
        - 'message_c': str
        - 'telemetry_c': RefinementTelemetry
        - 'bragg_full': np.ndarray (n_panels, slow, fast)
        - 'final_step_c': int
        - 'final_loss_value_c': float
        - 'final_mse_value_c': float
    """
```

**Extraction Steps:**

a) **Insert helper function at line ~3192** (after `_build_stage_c_lbfgs_closure`, before `run_nanobrag_refinement`)
   - Copy lines 4595-4794 (inline LBFGS execution + final Bragg + telemetry)
   - Wrap in `def _run_stage_c_lbfgs(...)` with signature above
   - **Critical:** Unpack ALL variables from input dicts at function start (30+ variables from 4 dicts)

b) **Variable unpacking (TOP of helper body):**
```python
    # Extract from param_values dict
    distance_offset_raw = param_values['distance_offset_raw']
    stage_c_params = param_values['stage_c_params']
    stage_c_optimizer = param_values['stage_c_optimizer']
    log_scale = param_values['log_scale']
    log_cell_a_delta = param_values.get('log_cell_a_delta')
    log_cell_b_delta = param_values.get('log_cell_b_delta')
    log_cell_c_delta = param_values.get('log_cell_c_delta')
    angle_alpha_raw = param_values.get('angle_alpha_raw')
    angle_beta_raw = param_values.get('angle_beta_raw')
    angle_gamma_raw = param_values.get('angle_gamma_raw')
    orientation_vec = param_values.get('orientation_vec')
    baseline_misset_deg_tensor = param_values.get('baseline_misset_deg_tensor')

    # Extract from telemetry_state dict (ALL as mutable references via list wrappers)
    chi_squared_best_c = telemetry_state['chi_squared_best_c']
    masked_mse_best_c = telemetry_state['masked_mse_best_c']
    best_params_snapshot_c = telemetry_state.get('best_params_snapshot_c')
    iteration_count_c = telemetry_state['iteration_count_c']
    loss_trace_sample_c = telemetry_state['loss_trace_sample_c']
    loss_trace_full_c = telemetry_state['loss_trace_full_c']
    chi_squared_trace_sample_c = telemetry_state['chi_squared_trace_sample_c']
    chi_squared_trace_full_c = telemetry_state['chi_squared_trace_full_c']
    masked_mse_trace_sample_c = telemetry_state['masked_mse_trace_sample_c']
    masked_mse_trace_full_c = telemetry_state['masked_mse_trace_full_c']
    variance_floor_clamped_pixels_c = telemetry_state['variance_floor_clamped_pixels_c']
    variance_floor_masked_pixels_c = telemetry_state['variance_floor_masked_pixels_c']
    perf_closure_evals_c = telemetry_state['perf_closure_evals_c']
    perf_validation_runs_c = telemetry_state['perf_validation_runs_c']
    perf_forward_times_ms_c = telemetry_state['perf_forward_times_ms_c']
    best_loss_full_c = telemetry_state['best_loss_full_c']

    # Extract from stage_c_context dict
    stage_c_use_warm_cache = stage_c_context['stage_c_use_warm_cache']
    stage_c_cache_mode = stage_c_context['stage_c_cache_mode']
    stage_c_roi_mode_label = stage_c_context['stage_c_roi_mode_label']
    stage_c_roi_count_total = stage_c_context['stage_c_roi_count_total']
    stage_c_roi_count_sampled = stage_c_context['stage_c_roi_count_sampled']
    baseline_detector_distances = stage_c_context.get('baseline_detector_distances')
    sampled_panel_ids = stage_c_context['sampled_panel_ids']

    # Extract from canonical_baseline dict (needed for improvement gate)
    best_loss_full = (canonical_baseline['chi_squared'], canonical_baseline['iteration'])

    # Derived variables
    panel_shape = inputs.data.shape[1:]
```

c) **Preserve ALL lazy imports INSIDE helper body** (after unpacking, before LBFGS execution):
```python
    # Lazy imports (inside helper to avoid circular deps)
    from nanobrag_torch.models import Detector, Crystal
    from nanobrag_torch.simulator import Simulator
    from dbex.nanobrag_bridge import create_detector_config, create_crystal_config
```

d) **Preserve LBFGS execution logic:**
   - Try/except wrapper around `stage_c_optimizer.step(closure_stage_c)`
   - Error handling (status_c = "error", best snapshot restore)
   - Final validation (`compute_loss_stage_c(list(range(n_panels)), is_full=True)`)
   - Best snapshot updates (chi_squared_best_c, masked_mse_best_c, best_params_snapshot_c)
   - Best snapshot restore before final Bragg

e) **Preserve improvement gate logic:**
   - Compare `final_loss_value_c` with `stage_a_final_loss = best_loss_full[0]`
   - Check `improvement_c < config.stage_c_min_loss_improvement`
   - Set `status_c = "early_stop"` with message per REFINE-007

f) **Preserve final Bragg regeneration logic (lines 4643-4724):**
   - Cell parameter reconstruction (log deltas → perturbed cell_a/b/c, angle deltas → perturbed alpha/beta/gamma)
   - Orientation quaternion reconstruction (orientation_vec → quat → misset_xyz_deg)
   - Baseline misset addition (`misset_xyz_deg + baseline_misset_deg_tensor`)
   - `crystal_overrides` dict construction
   - Per-panel loop (n_panels iterations):
     * Distance offset calculation (`bounded_offset = torch.tanh(distance_offset_raw[pid]) * config.stage_c_max_distance_delta_mm`)
     * Detector config branching (warm cache vs cold)
     * Simulator instantiation
     * Panel Bragg generation
     * Scale application (`torch.exp(log_scale_clamped)`)
   - `bragg_full_stage_c` array update

g) **Preserve telemetry packaging (lines 4726-4794):**
   - `param_deltas_c` dict (per-panel distance offsets with initial/final/delta)
   - `forward_stats_c` dict (mean/min/max/total from perf_forward_times_ms_c)
   - `perf_counters_c` dict (cache_mode, roi_mode, roi counts, closure/validation counts, forward stats)
   - `RefinementTelemetry` construction (30 fields including PHYSICS-LOSS-001/002, REFINE-007, canonical baseline fields)

h) **Return dict:**
```python
    return {
        'status_c': status_c,
        'message_c': message_c,
        'telemetry_c': telemetry_c,
        'bragg_full': bragg_full_stage_c,
        'final_step_c': final_step_c,
        'final_loss_value_c': final_loss_value_c,
        'final_mse_value_c': final_mse_value_c,
    }
```

### 3. Wire All 3 Helpers into `run_nanobrag_refinement` (45 min)

**Wiring Location:** Inline Stage C section (lines ~3824-4328, ~504 lines)

**Orchestration Pattern (match Phase B proven approach):**

a) **Replace lines 3824-4328** with orchestration code (~150 lines)

b) **Debugging aid:** Add compilation check after wiring:
```bash
python -c "import dbex.nanobrag_refinement; print('Compilation PASSED')"
```

### 4. Regression Guard (60 min)

**Run both Stage C smoke tests with FULL validation:**

a) **Small detector (primary validation):**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip \
  > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d1c/pytest_stage_c_small.log 2>&1 \
  ; echo "EXIT CODE: $?"
```

b) **Full detector (regression guard):**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=full \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip \
  > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d1c/pytest_stage_c_full.log 2>&1 \
  ; echo "EXIT CODE: $?"
```

c) **Extract metrics:**
```bash
# Micro probe (T0 tier): extract test results (2 tests × PASS/FAIL)
cat > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d1c/metrics.json <<'EOF'
{
  "compilation_status": "PASS",
  "helper_lines_extracted": 200,
  "inline_lines_removed": 504,
  "net_reduction": 354,
  "small_detector_status": "PASS",
  "full_detector_status": "PASS",
  "decision_path": "A"
}
EOF
```

### 5. Decision Synthesis (15 min)

Write `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d1c/decision.md` with 4-path template (Path A: both PASS → Phase D2, Path B: compilation FAIL, Path C: small detector FAIL, Path D: full detector FAIL).

### 6. Update Implementation Plan (5 min)

Edit `plans/active/ARCH-REFINE-FLOW-001/implementation.md`:
- Mark Phase D1c checklist item as COMPLETE
- Update Phase D status line with timestamp
- Add artifact path reference

### 7. Write Summary (10 min)

Write `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d1c/summary.md` with Turn Summary block.

### 8. Commit and Push (5 min)

```bash
git add -A
git commit -m "ARCH-REFINE-FLOW-001 Phase D1c: Extract _run_stage_c_lbfgs + wire all Stage C helpers — tests: small+full"
git push
```

## How-To Map

### Compilation Check
```bash
python -c "import dbex.nanobrag_refinement; print('Compilation PASSED')"
```

### Small Detector Smoke Test
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip
```

### Full Detector Smoke Test
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=full \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip
```

## Pitfalls to Avoid

1. **DO NOT modify production code outside Stage C section** — only extract helper + wire orchestration
2. **Preserve ALL lazy imports INSIDE helper** — avoid circular deps
3. **Unpack ALL variables from dicts at function start** — missing unpacking caused Phase B bugfix loop
4. **Match dict key names EXACTLY** — `param_values['stage_c_optimizer']` not `param_values['optimizer']`
5. **Preserve mutable list wrappers for telemetry state** — needed for closure mutation
6. **Use correct import paths** — `from nanobrag_torch.models import Detector, Crystal`
7. **Preserve ALL final Bragg regeneration logic** — lines 4643-4724 (~82 lines)
8. **Preserve ALL telemetry fields** — RefinementTelemetry has 30 fields
9. **Device/dtype neutrality** — respect `device` and `dtype` parameters
10. **No environment changes** — POLICY-001 Environment Freeze

## If Blocked

1. **Compilation FAIL:** Capture error, fix syntax/imports, recompile
2. **Small detector FAIL:** Read pytest log, fix dict key mismatch, rerun small test
3. **Full detector FAIL (small PASS):** Likely device/dtype issue, add diagnostics, fix
4. **Both tests FAIL with identical signature:** Likely helper signature mismatch, review param_values unpacking

**Escalation Trigger:** If >2 bugfix iterations with same failure signature, log blocker and mark Phase D1c BLOCKED.

## Findings Applied (Mandatory)

- **REFINE-007**: Stage C gate (≥80% offset reduction, ≤0.05% χ² regression)
- **PHYSICS-LOSS-001**: Variance-weighted chi-squared dual metrics
- **PHYSICS-LOSS-002**: Variance floor guard sigma_floor^2
- **PERF-WARM-013**: Stage C warm-cache deferred (preserve branching)
- **POLICY-001**: Environment Freeze (code-only extraction)

## Pointers

- **Spec:** docs/spec-db-workflow.md §7.5
- **Implementation Plan:** plans/active/ARCH-REFINE-FLOW-001/implementation.md Phase D
- **Testing:** docs/TESTING_GUIDE.md §2
- **Fix Plan:** docs/fix_plan.md ARCH-REFINE-FLOW-001
- **Previous Phase:** plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d1b/decision.md
- **Helper 1 (params):** dbex/nanobrag_refinement.py:2737-2893
- **Helper 2 (closure):** dbex/nanobrag_refinement.py:2894-3191
- **Inline target:** dbex/nanobrag_refinement.py:4595-4794
- **Wiring target:** dbex/nanobrag_refinement.py:3824-4328

## Next Up (optional)

If you finish early AND both regression guards PASS:
- Run compilation check
- Verify git diff shows net reduction ~354 lines
- Check for leftover dead code
- Ensure no debug logging left

**DO NOT proceed to Phase D2** — Phase D1c is a full-loop deliverable.

## Doc Sync Plan

NOT required this loop (no tests added/renamed). Test registry update deferred to Phase D5.

## Mapped Tests Guardrail

- test_stage_c_detector_microslip: Active selector, collects 2 tests (small + full detector), both must PASS for Phase D1c completion
