# input.md — Loop i=236 (Ralph) — PERF-WARM-SIM-001 Phase D: Stage C Detector Reuse

## Summary
Implement Stage C warm-cache detector reuse to eliminate per-panel/ROI Detector/Simulator instantiation overhead per PERF-WARM-013 finding.

## Mode
none

## Focus
PERF-WARM-SIM-001 — Warm Simulator: Eliminate Per-Iteration Re-Instantiation (Phase D: Stage C Detector Reuse)

## Branch
`integration` (current working branch)

## Mapped Tests
- `pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_c_microslip_small` (Stage C smoke small detector)
- `pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_c_microslip_full` (Stage C smoke full detector)

Environment flags:
```bash
export DBEX_SMOKE_DETECTOR_SIZE=small  # or full
export DBEX_SMOKE_SIGMA_SOURCE=cli_override
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
```

## Artifacts
All outputs under: `plans/active/PERF-WARM-SIM-001/reports/2025-11-23T180000Z/`

Expected artifacts:
- `pytest_stage_c_small.log` (Stage C smoke small detector test log)
- `pytest_stage_c_full.log` (Stage C smoke full detector test log)
- `telemetry_stage_c_small.json` (Stage C telemetry small detector)
- `telemetry_stage_c_full.json` (Stage C telemetry full detector)
- `phase_d_decision.md` (Decision synthesis with path selection)
- `summary.md` (Turn Summary block)

## Do Now

**Objective:** Eliminate Stage C per-panel/ROI Detector/Simulator instantiation by retargeting cached StageAContext detectors with bounded distance offsets.

**Background:** Per PERF-WARM-013 finding (docs/findings.md row 25), Stage C currently instantiates fresh Detector/Simulator objects for every panel (and every ROI slice) inside `compute_loss_stage_c` (dbex/nanobrag_refinement.py:2238-2545) plus the final reconstruction block, even when `stage_a_ctx` is available. This pays full construction cost on warm runs. Implementation.md Phase D (lines 70-76) defines the fix: extend StageAContext with baseline distances, implement a retarget helper that mutates cached simulators instead of recreating them, and update Stage C warm branches to call the helper.

### Tasks (D1–D4):

**D1 — Extend StageAContext metadata (extend StageAContext + _build_stage_a_context):**

1. Read current StageAContext definition (dbex/nanobrag_refinement.py: search for `StageAContext` class or dict construction, likely near lines 600-700).
2. Add two new fields to StageAContext:
   - `baseline_distances: Dict[int, float]` — per-panel distance baselines in mm (keys: panel_id 0..N-1, values: baseline detector.distance_mm for each panel)
   - `roi_panel_map: Dict[int, int]` — ROI index → panel_id mapping (keys: ROI index from roi_entries, values: panel_id)
3. Update `_build_stage_a_context` helper (likely near lines 700-900) to populate these two fields:
   - Extract baseline distances from detector_configs list: `{panel_id: cfg.distance_mm for panel_id, cfg in enumerate(detector_configs)}`
   - Build roi_panel_map from roi_entries: `{roi_idx: entry['panel_id'] for roi_idx, entry in enumerate(roi_entries)}`
4. Verify compilation: `python -c "from dbex.nanobrag_refinement import run_nanobrag_refinement"`

**D2 — Implement retarget helper (_retarget_stage_a_detectors):**

1. Add new helper function after `_build_stage_a_context` (before Stage A closure helpers, likely near line 900):
   ```python
   def _retarget_stage_a_detectors(
       stage_a_ctx: Dict,
       distance_deltas_mm: Dict[int, float],
       device: torch.device,
       dtype: torch.dtype
   ) -> None:
       """
       Mutate cached Stage A detector configs/simulators with bounded distance offsets.

       Args:
           stage_a_ctx: StageAContext dict with detector_configs, simulators, baseline_distances
           distance_deltas_mm: Per-panel distance deltas in mm (keys: panel_id, values: delta_distance_mm)
           device: torch.device for distance tensor updates
           dtype: torch.dtype for distance tensor updates

       Updates stage_a_ctx['detector_configs'] and stage_a_ctx['simulators'] IN PLACE.

       Spec refs:
           - docs/spec-db-runtime.md §2.1 (cache reuse pattern)
           - docs/spec-db-workflow.md §Stage C (detector distance refinement)
           - PERF-WARM-013 finding (eliminate cold instantiation)
       """
       # Implementation steps:
       # 1. Extract baseline_distances from stage_a_ctx
       # 2. For each panel_id in distance_deltas_mm:
       #    a. Compute new_distance_mm = baseline_distances[panel_id] + distance_deltas_mm[panel_id]
       #    b. Guard: if new_distance_mm outside safe bounds (e.g., <10mm or >10000mm), raise ValueError
       #    c. Update detector_configs[panel_id].distance_mm = new_distance_mm
       #    d. If simulators exist for this panel, check if nanobrag_torch Simulator has update_detector_distance() method
       #       - If YES: call simulator.update_detector_distance(new_distance_mm)
       #       - If NO: reconstruct only the Detector model (NOT Simulator) using updated config,
       #         then replace simulators[panel_id] with new Simulator(detector=new_detector, ...)
       # 3. Log warning if any panel_id in distance_deltas_mm is not in baseline_distances (skip silently)
   ```

   **Implementation Notes:**
   - **Lazy imports:** Import `nanobrag_torch.Simulator` INSIDE the function to avoid circular deps (pattern from ARCH-ENGINE-002).
   - **Device/dtype neutrality:** Ensure any torch.tensor() calls use `device=device, dtype=dtype`.
   - **Bounds check:** Stage C distance deltas are typically ±0.25mm (per REFINE-007 microslip tests), so safe bounds: `10mm < new_distance_mm < 10000mm`.
   - **API check:** Try `hasattr(simulator, 'update_detector_distance')` first; if False, fall back to Detector reconstruction + Simulator re-instantiation (still faster than full cold path because masks/HKL tensors stay cached).

2. Verify compilation after adding helper: `python -c "from dbex.nanobrag_refinement import _retarget_stage_a_detectors"`

**D3 — Refactor Stage C warm branches (compute_loss_stage_c + final reconstruction):**

1. Locate Stage C code sections (dbex/nanobrag_refinement.py:2238-2545):
   - `compute_loss_stage_c` function (likely lines 2238-2400)
   - Final Stage C reconstruction loop (likely lines 2450-2545)

2. For each section, identify detector instantiation pattern (search for `create_detector_config`, `Detector(`, `Simulator(`).

3. Add warm-cache branching BEFORE instantiation:
   ```python
   if stage_c_use_warm_cache and stage_a_ctx is not None:
       # Warm path: retarget cached detectors with current distance deltas
       _retarget_stage_a_detectors(
           stage_a_ctx=stage_a_ctx,
           distance_deltas_mm=current_distance_deltas_mm_dict,  # Dict[int, float]
           device=device,
           dtype=dtype
       )
       # Reuse cached detector_configs and simulators from stage_a_ctx
       detector = stage_a_ctx['detector_configs'][panel_id]  # or appropriate accessor
       simulator = stage_a_ctx['simulators'][panel_id]
   else:
       # Cold path: instantiate fresh (existing code, keep AS-IS)
       detector_config = create_detector_config(...)
       detector = Detector(detector_config)
       simulator = Simulator(detector=detector, ...)
   ```

4. **Guard:** Build `current_distance_deltas_mm_dict` from Stage C trainable parameters (likely `distance_offset` tensor passed to tanh bounds). Extract per-panel deltas BEFORE calling retarget helper.

5. **Lazy imports:** Move `from nanobrag_torch import Detector, Simulator` INSIDE the cold branch to avoid imports when warm path is active (pattern from ARCH-ENGINE-002).

6. Verify compilation: `python -c "from dbex.nanobrag_refinement import run_nanobrag_refinement"`

**D4 — Validation + telemetry + commit:**

1. Set environment flags:
   ```bash
   export DBEX_SMOKE_DETECTOR_SIZE=small
   export DBEX_SMOKE_SIGMA_SOURCE=cli_override
   export KMP_DUPLICATE_LIB_OK=TRUE
   export NANOBRAGG_DISABLE_COMPILE=1
   export DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-23T180000Z
   ```

2. Run Stage C smoke tests (small detector first, then full):
   ```bash
   pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_c_microslip_small \
     > plans/active/PERF-WARM-SIM-001/reports/2025-11-23T180000Z/pytest_stage_c_small.log 2>&1

   export DBEX_SMOKE_DETECTOR_SIZE=full
   pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_c_microslip_full \
     > plans/active/PERF-WARM-SIM-001/reports/2025-11-23T180000Z/pytest_stage_c_full.log 2>&1
   ```

3. Extract telemetry JSON (if DBEX_SMOKE_TELEMETRY_PATH emission is active):
   ```bash
   # Look for telemetry_stage_c_{small,full}.json in artifacts directory
   ls -la plans/active/PERF-WARM-SIM-001/reports/2025-11-23T180000Z/
   ```

4. Synthesize decision per 4-path template (write `phase_d_decision.md`):
   - **Path A (both smokes PASS):** Phase D COMPLETE. Stage C detector reuse operational. Mark implementation.md Phase D tasks D1-D4 COMPLETE. Next: Galph reviews exit criteria (PERF-WARM-SIM-001 ready for closure assessment).
   - **Path B (Stage C smoke FAIL with device/dtype error):** Debug retarget helper device/dtype mismatch. Check simulator tensor device placement, verify distance_mm tensors use correct device. Document blocker in phase_d_blocker.md, return control to Galph.
   - **Path C (retarget helper blocked by immutable Detector API):** Fallback to config cloning. Update _retarget_stage_a_detectors to ALWAYS clone detector configs with updated distances instead of mutating existing configs. Rerun validation. If PASS → Path A, if FAIL → Path B.
   - **Path D (compilation/import FAIL):** Lazy import issue or circular dependency. Check import order, ensure nanobrag_torch imports INSIDE cold branches. Document blocker in phase_d_blocker.md, return control to Galph.

5. Update `plans/active/PERF-WARM-SIM-001/implementation.md` checklist (mark D1-D4 COMPLETE if Path A).

6. Write `summary.md` with Turn Summary block (3-5 sentences: what shipped, main problem handled, next step, artifacts path).

7. Commit with message:
   ```
   PERF-WARM-SIM-001 Phase D: Stage C detector reuse via retargeting (tests: <PASS/FAIL>)

   - Extended StageAContext with baseline_distances + roi_panel_map (D1)
   - Implemented _retarget_stage_a_detectors helper for bounded distance deltas (D2)
   - Refactored compute_loss_stage_c + final reconstruction to call retarget helper on warm path (D3)
   - Validated Stage C smokes small+full, telemetry captured (D4)
   - Decision: <Path A/B/C/D>
   ```

8. Git push.

## How-To Map

**Environment setup:**
```bash
export DBEX_SMOKE_DETECTOR_SIZE=small  # or full for canonical
export DBEX_SMOKE_SIGMA_SOURCE=cli_override
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
export DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-23T180000Z
```

**Compilation checks (after each task):**
```bash
python -c "from dbex.nanobrag_refinement import run_nanobrag_refinement"
python -c "from dbex.nanobrag_refinement import _retarget_stage_a_detectors"
```

**Validation commands:**
```bash
# Small detector
pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_c_microslip_small \
  > plans/active/PERF-WARM-SIM-001/reports/2025-11-23T180000Z/pytest_stage_c_small.log 2>&1

# Full detector (after small PASS)
export DBEX_SMOKE_DETECTOR_SIZE=full
pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_c_microslip_full \
  > plans/active/PERF-WARM-SIM-001/reports/2025-11-23T180000Z/pytest_stage_c_full.log 2>&1
```

**Decision synthesis (T0 micro probe for test statuses):**
```bash
# Extract test exit codes from pytest logs
grep -E "PASSED|FAILED" plans/active/PERF-WARM-SIM-001/reports/2025-11-23T180000Z/pytest_stage_c_*.log
```

## Pitfalls To Avoid

1. **Device/dtype neutrality (CRITICAL):** All tensor operations in `_retarget_stage_a_detectors` MUST use `device=device, dtype=dtype` parameters. Do NOT assume cuda or cpu.

2. **Protected Assets:** Do NOT modify `dbex/refinement/{engine.py, stage.py, stage_a.py, stage_b.py, stage_c.py}` (engine protocol complete per ARCH-REFINE-FLOW-001). Only touch `dbex/nanobrag_refinement.py`.

3. **Lazy imports (ARCH-ENGINE-002 pattern):** Import `nanobrag_torch.{Detector, Simulator}` INSIDE cold branches or INSIDE helper functions to avoid circular dependencies and top-level import overhead.

4. **Bounds checking:** Stage C distance deltas are typically ±0.25mm per REFINE-007. Guard against pathological values: `10mm < new_distance_mm < 10000mm`. Raise ValueError if violated.

5. **Immutable Detector API fallback:** If nanobrag_torch Detector does not support `update_detector_distance()` (check with `hasattr`), fall back to cloning configs with updated distances. Do NOT fail the entire task.

6. **Vectorization (NOT required here):** Stage C operates per-panel sequentially (no batched distance updates). Do NOT attempt to vectorize retarget helper; keep it simple Dict[int, float] iteration.

7. **Environment Freeze:** Do NOT install/upgrade packages. Do NOT modify CUDA/torch versions. Code-only changes per POLICY-001.

8. **Telemetry structure:** Do NOT change existing telemetry fields (chi_squared, masked_mse, param_deltas). Only ADD new perf_counters if needed (e.g., retarget_calls_count).

9. **No ad-hoc scripts:** All analysis must use existing scripts (`scripts/tools/*`) or initiative `bin/` scripts per right-sized scriptization policy. Do NOT create new bin/ scripts for this task (reuse existing Stage C smoke tests).

10. **Test registry sync (NOT required here):** No new tests are being authored. Do NOT update TESTING_GUIDE.md or TEST_SUITE_INDEX.md unless test names change (they won't).

## If Blocked

**Scenario 1: Stage C smoke tests FAIL with device/dtype error**
- Capture full error message + stack trace in `phase_d_blocker.md`.
- Check retarget helper device placement: `print(f"device={device}, dtype={dtype}")` at helper entry.
- Verify all tensor operations use explicit device/dtype (search for `torch.tensor(` without device arg).
- Document exact line number where error occurs.
- Commit partial progress (D1-D2 complete, D3 blocked), return control to Galph.

**Scenario 2: nanobrag_torch Detector API does not support distance mutation**
- Check Simulator.__init__ signature: does it accept `distance_mm` as separate arg?
- Fall back to config cloning: `updated_config = detector_config.clone(); updated_config.distance_mm = new_distance_mm`.
- If clone() not available, reconstruct config dict manually.
- Document fallback decision in `phase_d_decision.md` under Path C.
- Rerun validation with fallback implementation.

**Scenario 3: Circular import error when importing nanobrag_torch**
- Move `from nanobrag_torch import Detector, Simulator` INSIDE cold branch (after `if not stage_c_use_warm_cache:` check).
- Ensure imports are NOT at module top level in dbex/nanobrag_refinement.py.
- Verify compilation with `python -c "from dbex.nanobrag_refinement import run_nanobrag_refinement"`.
- Document lazy import fix in summary.md.

**Scenario 4: StageAContext missing baseline_distances or roi_panel_map after D1**
- Check `_build_stage_a_context` call sites: is it being invoked with correct parameters?
- Verify StageAContext dict keys with `print(stage_a_ctx.keys())` in compute_loss_stage_c.
- Document missing fields error in `phase_d_blocker.md`, return control to Galph.

## Findings Applied

- **PERF-WARM-013 (Active):** Stage C instantiation overhead — target of this Do Now.
- **PERF-WARM-006 (Active):** StageAContext reuse pattern validated in Stage B/C smokes.
- **ARCH-ENGINE-002 (Active):** Lazy imports pattern to avoid circular dependencies.
- **REFINE-007 (Active):** Stage C microslip tests inject ±0.25mm panel offsets, recovery gate ≥80%.
- **POLICY-001 (Active):** Environment Freeze — code-only changes, no package installs.
- **TESTING-003 (Active):** No test registry sync needed (no new tests authored).

## Pointers

**Specs:**
- `docs/spec-db-runtime.md:§2.1` (Cache reuse pattern)
- `docs/spec-db-workflow.md:§Stage C` (Detector distance refinement)

**Implementation Plan:**
- `plans/active/PERF-WARM-SIM-001/implementation.md:70-76` (Phase D definition)

**Findings:**
- `docs/findings.md:25` (PERF-WARM-013: Stage C instantiation overhead)
- `docs/findings.md:23` (PERF-WARM-006: StageAContext reuse from Stage B/C)
- `docs/findings.md:row 8 ARCH-ENGINE-002` (Lazy imports + telemetry packaging)

**Fix Plan:**
- `docs/fix_plan.md:§PERF-WARM-SIM-001` (Status: in_progress, Exit Criteria #1 blocked by PERF-WARM-013)

**Test Registry:**
- `docs/TESTING_GUIDE.md:§2` (Stage C smoke selectors)
- `docs/development/TEST_SUITE_INDEX.md` (Test suite index)

**Code:**
- `dbex/nanobrag_refinement.py:600-900` (StageAContext definition + _build_stage_a_context helper, estimated)
- `dbex/nanobrag_refinement.py:2238-2545` (Stage C code: compute_loss_stage_c + final reconstruction)
- `tests/dbex/test_torch_refine_smoke.py:500-640` (Stage C smoke tests)

## Next Up (Optional)

If Ralph finishes early AND all tests PASS:
- Review implementation.md Phase D exit criteria and document any deviations in summary.md.
- Check if Exit Criteria #1 (Stage A/B/C reuse StageAContext with cache_mode telemetry) is NOW MET for Stage C.
- Do NOT attempt Exit Criteria #3 (benchmarking) — deferred per implementation.md scope.

## Doc Sync Plan (Conditional)

NOT REQUIRED for this loop (no new tests authored, no test name changes, no spec updates).
