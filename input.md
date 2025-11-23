# Phase D1a: Extract _build_stage_c_params Helper (Loop i=227)

## Summary
Extract the Stage C parameter initialization helper function from the inline Stage C code (lines 3828-3897 in `dbex/nanobrag_refinement.py`). This is the first of three helper extraction loops following the proven Phase B/C multi-loop pattern.

## Mode
none

## Focus
ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase D1a: Stage C helper extraction)

## Branch
integration

## Mapped Tests
- **Primary Validation**: Compilation check via `python -c "import dbex.nanobrag_refinement"`
- **Regression Guard**: `pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small` (should PASS unchanged, helper not yet wired)

## Artifacts
`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T150000Z/phase_d1a/`

## Do Now

### Context Review
1. **Phase D0 Completion**: Both Stage C smoke tests PASSED (small 16.0s, full 40.83s) with baseline artifacts captured. Two blocking bugs fixed (UnboundLocalError, NameError for `baseline_detector_distances`). Decision: Path A → Phase D1 ready.

2. **Inline Stage C Location**: Lines 3824-4328 in `dbex/nanobrag_refinement.py` (~504 lines total)
   - Lines 3828-3897: Parameter initialization + optimizer setup (target for D1a extraction)
   - Lines 3899-4295: LBFGS closure (nested compute_loss_stage_c + closure_stage_c)
   - Lines 4296-4328: LBFGS execution + telemetry aggregation

3. **Multi-Loop Extraction Pattern** (proven in Phase B/C):
   - **D1a** (this loop): Extract `_build_stage_c_params` helper (~200 lines)
   - **D1b** (next loop): Extract `_build_stage_c_lbfgs_closure` helper (~400 lines)
   - **D1c** (final loop): Extract `_run_stage_c_lbfgs` + wire all helpers + regression guard

### Implement: dbex/nanobrag_refinement.py::_build_stage_c_params

Extract lines 3828-3919 as a new helper function `_build_stage_c_params` to be inserted **before** `run_nanobrag_refinement` (around line 2700, after Stage B helpers).

**Helper Signature**:
```python
def _build_stage_c_params(
    config: RefinementConfig,
    device: torch.device,
    dtype: torch.dtype,
    n_panels: int,
    baseline_detector: Optional[Any],  # dxtbx.model.Detector
    detector: Any,  # dxtbx.model.Detector
    sampled_panel_ids: List[int],
    panel_slices: List[Tuple[int, int, int, int, int]],
    stage_a_ctx: Optional[StageAContext],
    sigma_floor_sq_cache: Dict[str, torch.Tensor],
    params: List[torch.Tensor]  # Stage A params to freeze
) -> Dict[str, Any]:
    """
    Initialize Stage C detector distance offset parameters and optimizer.

    Stage C refines per-panel translations along detector normal (distance offset)
    with crystal orientation/cell frozen from Stage A.

    Returns dict with keys:
        - 'distance_offset_raw': torch.Tensor (n_panels,) trainable parameter
        - 'stage_c_params': List[torch.Tensor] (optimizer params)
        - 'stage_c_optimizer': torch.optim.LBFGS
        - 'baseline_detector_distances': Optional[List[float]] (mm per panel)
        - 'stage_c_use_warm_cache': bool
        - 'stage_c_cache_mode': str ('warm' or 'cold')
        - 'stage_c_roi_mode_active': bool
        - 'stage_c_roi_mode_label': str ('roi' or 'panel')
        - 'stage_c_roi_count_total': int
        - 'stage_c_roi_count_sampled': int
        - 'roi_slices_by_pid': Dict[int, List[Tuple[int, int, int, int]]]
        - 'perf_closure_evals_c': List[int] (mutable counter)
        - 'perf_validation_runs_c': List[int] (mutable counter)
        - 'perf_forward_times_ms_c': List[float] (mutable accumulator)
        - 'loss_trace_sample_c': List[float]
        - 'loss_trace_full_c': List[float]
        - 'best_loss_full_c': Tuple[float, int] (value, iteration)
        - 'best_params_snapshot_c': Optional[List[torch.Tensor]]
        - 'iteration_count_c': List[int] (mutable counter)
        - 'chi_squared_trace_sample_c': List[float]
        - 'chi_squared_trace_full_c': List[float]
        - 'chi_squared_best_c': Tuple[float, int]
        - 'masked_mse_trace_sample_c': List[float]
        - 'masked_mse_trace_full_c': List[float]
        - 'masked_mse_best_c': Tuple[float, int]
        - 'variance_floor_clamped_pixels_c': List[int]
        - 'variance_floor_masked_pixels_c': List[int]
        - 'sigma_floor_sq_tensor_stage_c': torch.Tensor
    """
```

**Extraction Steps**:

1. **Create helper function** at line ~2700 (after `_run_stage_b_lbfgs`, before `run_nanobrag_refinement`)

2. **Extract baseline_detector_distances computation** (lines 3828-3834):
   - Move into helper body (this was the NameError fix from D0)
   - Return as dict key `'baseline_detector_distances'`

3. **Extract Stage A parameter freezing** (lines 3836-3838):
   - Move loop that sets `p.requires_grad = False` for all Stage A params
   - Keep in helper body (Stage C freezes Stage A gradients)

4. **Extract distance_offset_raw initialization** (lines 3840-3844):
   - Move `torch.zeros(n_panels, device, dtype, requires_grad=True)`
   - Wrap in `stage_c_params = [distance_offset_raw]`
   - Return as dict keys `'distance_offset_raw'` and `'stage_c_params'`

5. **Extract warm cache logic** (lines 3845-3851):
   - Move `stage_c_use_warm_cache` conditional
   - Move `stage_c_cache_mode` assignment
   - Return as dict keys

6. **Extract performance counters initialization** (lines 3852-3854):
   - Move `perf_closure_evals_c`, `perf_validation_runs_c`, `perf_forward_times_ms_c`
   - Initialize as mutable lists (same pattern as Stage A/B)
   - Return as dict keys

7. **Extract ROI mode logic** (lines 3855-3870):
   - Move `roi_slices_by_pid` dict construction from `panel_slices`
   - Move `stage_c_roi_mode_active` conditional (warm cache + ROI enabled + slices present)
   - Move `stage_c_roi_mode_label` assignment
   - Move `sampled_pid_set` construction
   - Move `stage_c_roi_count_total` and `stage_c_roi_count_sampled` computation
   - Return all as dict keys

8. **SKIP baseline detector prior helper** (lines 3872-3887):
   - **DO NOT extract `_apply_baseline_detector_prior`** — this nested function stays inline for now
   - It will be handled in D1c wiring when the call site logic is addressed

9. **Extract LBFGS optimizer initialization** (lines 3889-3897):
   - Move `stage_c_optimizer` construction with config params
   - Return as dict key `'stage_c_optimizer'`

10. **Extract telemetry accumulators** (lines 3899-3919):
    - Move all telemetry list/tuple initializations:
      - `loss_trace_sample_c`, `loss_trace_full_c`, `best_loss_full_c`, `best_params_snapshot_c`, `iteration_count_c`
      - `chi_squared_trace_sample_c`, `chi_squared_trace_full_c`, `chi_squared_best_c`
      - `masked_mse_trace_sample_c`, `masked_mse_trace_full_c`, `masked_mse_best_c`
      - `variance_floor_clamped_pixels_c`, `variance_floor_masked_pixels_c`
      - `sigma_floor_sq_tensor_stage_c` (call to `_get_sigma_floor_sq_tensor`)
    - Return all as dict keys

11. **Return dict** with all keys listed in signature docstring

**DO NOT**:
- Wire the helper into `run_nanobrag_refinement` (no call site changes)
- Extract the `compute_loss_stage_c` closure (that's D1b)
- Extract the LBFGS execution loop (that's D1c)
- Extract the `_apply_baseline_detector_prior` nested function (stays inline)
- Modify any Stage C inline logic beyond the extracted lines
- Change test behavior (helper not called, tests should pass unchanged)

**Compilation Check**:
```bash
python -c "import dbex.nanobrag_refinement; print('Compilation PASSED')"
```

**Regression Guard**:
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
export DBEX_SMOKE_DETECTOR_SIZE=small
export DBEX_SMOKE_SIGMA_SOURCE=cli_override
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1

pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --tb=short
```

Expected: PASS (helper not wired, no behavior change)

### Validation Protocol

1. **Compilation**: Import `dbex.nanobrag_refinement` successfully
2. **Regression Guard**: Stage C smoke test PASSES on small detector
3. **Helper Signature**: Verify function signature matches specification exactly
4. **Return Keys**: Verify all 30 dict keys present in return value
5. **Lines Extracted**: Verify approximately 90-120 lines extracted from inline code

### Decision Synthesis (4-Path Template)

**Path A (Compilation PASS + Regression PASS)**:
- Helper extraction SUCCESSFUL
- Proceed to Phase D1b next loop (extract `_build_stage_c_lbfgs_closure`)
- Update implementation.md checklist D1a complete
- Commit helper extraction with message: "ARCH-REFINE-FLOW-001 Phase D1a: Extract _build_stage_c_params helper — tests: 1 passed"

**Path B (Compilation FAIL)**:
- Syntax error or import error in helper
- Debug syntax, fix imports, retest compilation
- Do NOT proceed to D1b until compilation clean

**Path C (Regression FAIL)**:
- Stage C smoke test fails (should not happen, helper not wired)
- Investigate test infrastructure issue
- Revert helper extraction if test regression confirmed
- Escalate to Galph with blocker report

**Path D (Helper signature mismatch)**:
- Missing return keys or incorrect types
- Fix return dict to match specification
- Retest compilation + regression
- Do NOT proceed to D1b until signature correct

### Artifacts Capture

Save to `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T150000Z/phase_d1a/`:

1. **compilation_check.log**: Output of `python -c "import dbex.nanobrag_refinement"`
2. **pytest_stage_c_regression.log**: Regression guard test output
3. **helper_diff.patch**: Git diff showing extracted helper (for reproducibility)
4. **decision.md**: 4-path synthesis with chosen path and rationale
5. **metrics.json**: Extract via T0 probe:
   ```python
   import json
   metrics = {
       "compilation_status": "PASS" or "FAIL",
       "regression_status": "PASS" or "FAIL",
       "helper_lines_extracted": 120,  # approximate count
       "helper_signature_keys_count": 30,
       "decision_path": "A"  # or "B", "C", "D"
   }
   with open("plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T150000Z/phase_d1a/metrics.json", "w") as f:
       json.dump(metrics, f, indent=2)
   ```
6. **summary.md**: Turn Summary block (prepend to existing summary.md)

### Update Checklist

Mark complete in `plans/active/ARCH-REFINE-FLOW-001/implementation.md`:
- Add under Phase D section (around line 228):
  ```markdown
  - [ ] D1: Implement `StageC` class managing detector offset parameters, baseline detector seeding, and telemetry.
    - [x] D1a: Extract `_build_stage_c_params` helper (~120 lines) ✓ COMPLETE (2025-11-23T150000Z)
    - [ ] D1b: Extract `_build_stage_c_lbfgs_closure` helper (~400 lines)
    - [ ] D1c: Extract `_run_stage_c_lbfgs` + wire all helpers + regression guard
  ```

### Commit and Push

```bash
git add -A
git commit -m "ARCH-REFINE-FLOW-001 Phase D1a: Extract _build_stage_c_params helper — tests: 1 passed"
git push
```

## How-To Map

### Compilation Check Command
```bash
python -c "import dbex.nanobrag_refinement; print('Compilation PASSED')" 2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T150000Z/phase_d1a/compilation_check.log
```

### Regression Guard Command
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
export DBEX_SMOKE_DETECTOR_SIZE=small
export DBEX_SMOKE_SIGMA_SOURCE=cli_override
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1

pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --tb=short 2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T150000Z/phase_d1a/pytest_stage_c_regression.log
```

### Metrics Extraction (T0 Probe)
Inline Python after tests complete — save to `metrics.json` in artifacts directory.

## Pitfalls To Avoid

1. **DO NOT wire helper**: No call site changes in `run_nanobrag_refinement`. Helper extraction only.
2. **DO NOT extract closure**: `compute_loss_stage_c` stays inline (that's Phase D1b).
3. **DO NOT modify tests**: Regression guard should PASS unchanged.
4. **SKIP nested function**: `_apply_baseline_detector_prior` stays inline (handled in D1c).
5. **Mutable accumulators**: Use `List[int]` for counters (not `int`) to allow mutation in closures.
6. **Dict keys**: Return ALL 30 keys listed in signature docstring (missing keys will break D1c wiring).
7. **Device/dtype consistency**: Use `device` and `dtype` params passed to helper (no hardcoded `'cuda:0'`).
8. **Lazy imports**: No new imports at module level (helper may use existing imports only).
9. **Baseline detector None-safety**: Check `baseline_detector is not None` before accessing.
10. **Environment Freeze**: No package installs, no environment changes. Code-only extraction.

## If Blocked

If compilation fails or regression fails unexpectedly:

1. **Capture error output** to `blocker.md` in artifacts directory
2. **Revert extraction** if test regression confirmed: `git checkout dbex/nanobrag_refinement.py`
3. **Update Attempts History** in `docs/fix_plan.md` with blocker signature
4. **Mark Phase D1a blocked** in `galph_memory.md`
5. **Escalate to Galph** with blocker report including:
   - Exact error message
   - Line numbers where helper was inserted
   - Compilation traceback or pytest failure output
   - Hypothesis about root cause (import cycle, missing dependency, etc.)

## Findings Applied (Mandatory)

- **REFINE-007** (docs/findings.md:43): Stage C gate is "stable detector offset" (not chi² improvement) — helper preserves telemetry accumulators for offset tracking
- **PHYSICS-LOSS-001/002** (docs/findings.md:20,21): Variance-weighted loss + sigma_floor preserved — helper extracts `sigma_floor_sq_tensor_stage_c` initialization
- **POLICY-001** (docs/findings.md:66): Environment Freeze — helper extraction only, no env changes
- **TESTING-003** (docs/findings.md:56): Test registry updates deferred until D1c wiring complete (no selector changes this loop)
- **CONFORMANCE-001** (docs/findings.md:28): Test environment flags applied to regression guard
- **RUNTIME-001** (docs/findings.md:29): `NANOBRAGG_DISABLE_COMPILE=1` set for Stage C smoke (torch.compile conflicts with gradcheck)

No relevant findings in knowledge base for helper extraction methodology (standard refactoring).

## Pointers

- **Spec**: docs/spec-db-workflow.md §7 (Refinement Protocol Architecture)
- **Architecture**: docs/architecture/pytorch_design.md (RefinementEngine contract)
- **Testing**: docs/TESTING_GUIDE.md §1.1 (environment flags for Stage C smoke)
- **Fix Plan**: docs/fix_plan.md `[ARCH-REFINE-FLOW-001]` line 28
- **Implementation Plan**: plans/active/ARCH-REFINE-FLOW-001/implementation.md Phase D (line 220)
- **Baseline Evidence**: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T143000Z/baseline/summary.md (Stage C PASSED both detectors)
- **Phase B Extraction Pattern**: plans/active/ARCH-REFINE-FLOW-001/implementation.md Phase B (lines 80-178) — proven multi-loop extraction methodology
- **Stage C Inline Code**: dbex/nanobrag_refinement.py lines 3824-4328

## Next Up (Optional)

If Phase D1a completes successfully (Path A):
- **Phase D1b**: Extract `_build_stage_c_lbfgs_closure` helper (nested `compute_loss_stage_c` + `closure_stage_c`, ~400 lines)
- **Phase D1c**: Extract `_run_stage_c_lbfgs` + wire all three helpers + validate Stage C smoke (small + full detectors)

If Phase D1a blocked (Path B/C/D):
- Debug compilation or regression issue
- Escalate to Galph with blocker report
- Do NOT proceed to D1b until D1a compilation clean and regression guard PASSES

## Doc Sync Plan (Conditional)

Not applicable this loop (no new tests authored, no selector changes). Test registry updates deferred to Phase D1c after full helper wiring and validation complete.

## Mapped Tests Guardrail

**Compilation check** (python import) always collects (N/A for pytest collection).

**Regression guard** `test_stage_c_detector_microslip` collects 1 test (confirmed in Phase D0 baseline: `pytest_collect_stage_c.log`).

If collection fails (0 tests), mark Phase D1a BLOCKED and escalate to Galph with collection log.

## Normative Math/Physics

Not applicable this loop (no physics equations extracted, parameter initialization only). Variance-weighted loss computation stays inline until Phase D1b.

Reference docs/spec-db-core.md §Variance Definition for normative variance-floor clamping specification (applied in `compute_loss_stage_c`, extracted in D1b).
