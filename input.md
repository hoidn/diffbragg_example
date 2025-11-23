# Ralph Input — ARCH-REFINE-FLOW-001 Phase B1a-loop3 Bugfix

**Summary:** Fix params dict bug causing NoneType zero_grad error in regression guard test

**Mode:** none (straightforward bugfix)

**Focus:** ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase B1a-loop3 bugfix)

**Branch:** integration

**Mapped tests:**
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (regression guard, MUST PASS)

**Artifacts:** `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T060500Z/`

## Do Now (Phase B1a-loop3 Bugfix)

Ralph, this is a straightforward one-line fix to complete Phase B1a-loop3. The regression guard failure has been diagnosed: the `params` list is missing from the `param_values` dict, causing helper2 to get an empty list and the LBFGS optimizer to fail.

Execute the following steps:

1. **Review blocker analysis** (2 min):
   - Read `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T060000Z/BLOCKER.md`
   - Understand: params is in helper1_result['params'] but NOT in param_values dict
   - Helper2 line 1073 does `params = param_values.get('params', [])` → returns empty list

2. **Apply one-line fix** (1 min):
   - **File:** `dbex/nanobrag_refinement.py`
   - **Location:** Line 943 (inside `_build_stage_a_params` helper, in param_values dict construction)
   - **Change:** Add `'params': params,` to the param_values dict (after line 942, before closing the dict)
   - **Expected diff:**
     ```python
     # Build param_values dict for return
     param_values = {
         'initial_log_scale': initial_log_scale,  # Store initial value for telemetry
         'log_scale': log_scale,
         'log_cell_a_delta': log_cell_a_delta,
         # ... other params ...
         'orientation_vec': orientation_vec,
+        'params': params,  # List of Parameter objects for optimizer
         'q_params': q_params,
         'B_ideal_reciprocal_torch': B_ideal_reciprocal_torch,
         # ... rest of dict ...
     }
     ```

3. **Verify params list construction** (2 min):
   - Check lines 802-820: params list should be correctly filtered based on parameterization mode
   - Default mode (lines 802-807): 8 params (log_scale, 3 cell, 3 angles, orientation_vec)
   - U-matrix mode (line 811): append q_params
   - Incremental UB mode (lines 815-820): replace with 8 params (log_scale, q_delta, 3 delta_log, 3 delta_angles)
   - Confirm NO None values in any params list

4. **Compilation check** (1 min):
   - Run: `python -c "import dbex.nanobrag_refinement"`
   - Exit code MUST be 0

5. **Regression guard test** (30 sec):
   - **Environment:** `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`
   - **Command:** `pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion 2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T060500Z/pytest_stage_a_expansion.log`
   - **Expected:** PASSED with ≥0.2% improvement

6. **Telemetry comparison** (ONLY if step 5 PASSES):
   - Extract improvement from pytest log: `grep "improvement" plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T060500Z/pytest_stage_a_expansion.log`
   - Verify telemetry status != 'error'
   - Verify closure_evals > 0 (optimizer ran)
   - Compare with baseline 2025-11-23T030000Z: chi² improvement ~18.3%

7. **Update implementation.md checklist** (1 min):
   - Mark `[ ] B1a-loop3: Extract _run_stage_a_lbfgs + Refactor main function` as COMPLETE (✓)
   - Note: "One-line bugfix: added 'params' to param_values dict, regression guard PASSED"

8. **Write summary.md** (2 min):
   - File: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T060500Z/summary.md`
   - Include Turn Summary block (3-5 sentences):
     - Fixed params dict bug (one-line change)
     - Regression guard now PASSES
     - Phase B1a-loop3 extraction COMPLETE
     - File reduced by 692 lines, Stage A helpers fully extracted
     - Next: Phase B1b (StageA wrapper class)
   - Metrics: test result, improvement %, closure_evals count

9. **Commit and push** (30 sec):
   ```bash
   git add -A
   git commit -m "RALPH: ARCH-REFINE-FLOW-001 Phase B1a-loop3 bugfix — fix params dict bug

   One-line fix: added 'params' to param_values dict in _build_stage_a_params helper.
   Regression guard test_stage_a_expansion now PASSES.
   Phase B1a extraction COMPLETE (692 lines reduced, 3 helpers extracted, main function refactored).

   Tests: test_stage_a_expansion PASSED
   "
   git push
   ```

## How-To Map

**Fix application:**
- File: `dbex/nanobrag_refinement.py:943`
- Add: `'params': params,` to param_values dict

**Regression guard:**
```bash
cd /home/ollie/Documents/diffbragg_example
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T060500Z/pytest_stage_a_expansion.log
```

**Telemetry extraction (if test passes):**
```bash
grep -E "(improvement|status|closure_evals)" plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T060500Z/pytest_stage_a_expansion.log
```

**Baseline comparison:**
- Baseline: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/pytest_small.log`
- Expected improvement: ~18.3% (small detector)

## Pitfalls To Avoid

1. **Do NOT** modify params list construction logic (lines 802-820) — it's already correct
2. **Do NOT** add params to multiple dicts — only param_values dict needs it
3. **Do NOT** skip the regression guard — it MUST PASS before marking B1a-loop3 complete
4. **Do NOT** modify helper2 line 1073 — the fix is in helper1, not helper2
5. **Environment:** KMP_DUPLICATE_LIB_OK=TRUE required (Intel MKL workaround)
6. **Environment:** NANOBRAGG_DISABLE_COMPILE=1 required (skip torch.compile for smoke tests)
7. **Telemetry comparison:** Compare with 2025-11-23T030000Z baseline, NOT 2025-11-23T060000Z blocker artifacts
8. **Commit message:** Include "Phase B1a-loop3 bugfix" and "COMPLETE" to mark milestone

## If Blocked

**Scenario A: Test still fails with same error**
- Capture: `params` list contents at line 802-820 (print before returning from helper1)
- Verify: No None values in params list
- Check: param_values dict has 'params' key with non-empty list
- Document: params list contents + error in blocker file

**Scenario B: Test fails with different error**
- Capture: Full pytest log + error traceback
- Document: New error signature in blocker file
- Do NOT attempt further fixes — escalate to Galph

**Scenario C: Test passes but telemetry wrong (improvement <0.2% or status='error')**
- Capture: Full telemetry dict from test output
- Compare: With baseline 2025-11-23T030000Z telemetry
- Document: Telemetry diff in blocker file
- Do NOT modify code — escalate to Galph

## Findings Applied

- **REFINE-006:** Stage A improvement gate ≥0.2% (empirically calibrated ceiling)
- **CONVERGENCE-001:** Zero-delta bypass fix enables stable convergence
- **GEOMETRY-004:** Incremental UB parameterization (not active in default small detector test)

## Pointers

- Fix location: `dbex/nanobrag_refinement.py:943` (param_values dict)
- Blocker analysis: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T060000Z/BLOCKER.md`
- Implementation plan: `plans/active/ARCH-REFINE-FLOW-001/implementation.md:102` (B1a-loop3 checklist)
- Baseline artifacts: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/baseline/`
- Test registry: `docs/TESTING_GUIDE.md:80` (test_stage_a_expansion selector)

## Next Up (after B1a-loop3 bugfix complete)

Phase B1b: Wrap extracted helpers in StageA.run() class method (estimated 1 loop)
