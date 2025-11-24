# TORCH-REFINE-004 Phase 7 Gradient Flow Blocker Fix

**Summary:** Fix Adam optimizer execution pattern in Stage B per-reflection mode to enable gradient flow and parameter updates.

**Mode:** none (bugfix)

**Focus:** TORCH-REFINE-004  Stage B Per-Reflection Mode Migration (Phase 7 gradient flow blocker resolution)

**Branch:** integration

**Mapped tests:**
- `tests/dbex/test_stage_b_asu_mapping.py` (5 unit tests, Phase 6 regression guard)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` (LBFGS/shell mode regression)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke` (Adam/per-reflection mode primary validation)

**Artifacts:** `plans/active/TORCH-REFINE-004/reports/2025-11-24T110000Z/`

---

## Problem Statement

Ralph's Phase 7 implementation (commit 93f3dbe) successfully added dynamic optimizer selection (Adam for n_asu e 10K, LBFGS for n_asu < 10K) in `_build_stage_b_params`, but the optimization execution function `_run_stage_b_lbfgs()` is hardcoded to use the **LBFGS calling pattern** `optimizer.step(closure)`. This pattern does NOT work for Adam  Adam requires a **manual loop** where you call `closure()` to compute loss/gradients, then call `optimizer.step()` without arguments.

**Evidence:**
- Test failure: ASU modifier mean = 0.9999997 (unchanged from initial 1.0)
- Optimizer type = "adam" (correctly selected for P1 fixture with 97,793 ASU > 10K threshold)
- All telemetry attributes present (Phase 8 fix working correctly)
- Shell mode test PASSES (LBFGS path works correctly)

**Root Cause (99.9% confidence):** `dbex/nanobrag_refinement.py:3112` calls `stage_b_optimizer.step(closure_stage_b)`, which works for LBFGS but is a NO-OP for Adam. Adam's `.step()` method ignores the closure argument and expects gradients to already be computed.

**Full Analysis:** `plans/active/TORCH-REFINE-004/reports/2025-11-24T110000Z/gradient_flow_root_cause_analysis.md` (comprehensive 12-section root cause with PyTorch API documentation, code path analysis, fix specification, estimated effort ~1.5 hours).

---

## Do Now

**Objective:** Add optimizer-agnostic execution pattern to `_run_stage_b_lbfgs` using Option A branching (manual loop for Adam, existing LBFGS pattern preserved).

### Implementation Checklist

**Step 1: Extract optimizer_type parameter**

Location: `dbex/nanobrag_refinement.py` function `_run_stage_b_lbfgs` (line ~3059)

After line 3060 (`stage_b_mode = param_values['stage_b_mode']`), add:

```python
optimizer_type = param_values['optimizer_type']  # "adam" or "lbfgs"
```

**Step 2: Replace optimizer.step() with branching logic**

Location: `dbex/nanobrag_refinement.py` line 3111-3113 (inside try block, before exception handler)

Replace:
```python
        # Run LBFGS optimization
        stage_b_optimizer.step(closure_stage_b)
```

With:
```python
        # Run optimization (optimizer-agnostic pattern per TORCH-REFINE-004 Phase 7 blocker fix)
        if optimizer_type == "adam":
            # Adam requires manual loop: call closure() to compute loss/gradients,
            # then call step() without arguments to update params
            max_iter_b = config.max_iter  # Default 30 per RefinementConfig
            for iteration_adam in range(max_iter_b):
                loss = closure_stage_b()  # Computes loss, backward(), updates traces
                stage_b_optimizer.step()  # Update params (NO closure arg for Adam)

                # Check improvement after each iteration (reuse LBFGS periodic validation logic)
                if len(loss_trace_full_b) > 0:
                    _, latest_full_loss = loss_trace_full_b[-1]
                    improvement_b = (best_loss_full[0] - latest_full_loss) / best_loss_full[0]
                    if improvement_b >= config.stage_b_min_loss_improvement:
                        status_b = "ok"
                        message_b = f"Stage B converged after {iteration_adam+1} Adam iterations (improvement {improvement_b:.4%})"
                        break
        else:  # "lbfgs"
            # LBFGS uses closure-based pattern (original line 3112)
            stage_b_optimizer.step(closure_stage_b)
```

**Step 3: Pass optimizer_type to _run_stage_b_lbfgs**

Location: `dbex/nanobrag_refinement.py` lines 2635-2700 (where `_run_stage_b_lbfgs` is called in inline path)

After line ~2670 (where `param_values_b` dict is constructed), ensure `optimizer_type` is included:

```python
param_values_b = {
    'optimizer': stage_b_optimizer,
    'stage_b_mode': config_stage_b_mode_override,  # Existing field
    'optimizer_type': optimizer_type,  # NEW field (from line ~2520 or ~2531 or ~2542)
    # ... all existing fields: log_modifiers, shell_modifier_raw, log_scale, telemetry_state, etc.
}
```

**Step 4: Pass optimizer_type in StageB wrapper**

Location: `dbex/refinement/stage_b.py` lines ~240-260 (where `param_values_b` dict is constructed)

Add `'optimizer_type': optimizer_type` to the dict (optimizer_type should be extracted from Stage B params builder return value or stored in a local variable).

**Note:** Check the exact location where `_build_stage_b_params` is called in stage_b.py and capture the `optimizer_type` variable returned/set by that builder, then pass it to `_run_stage_b_lbfgs`.

### Validation Protocol

1. **Compilation check:**
   ```bash
   python -c "from dbex.nanobrag_refinement import _run_stage_b_lbfgs; print('OK')"
   ```
   Expected: "OK" printed, no ImportError or SyntaxError

2. **Phase 6 unit regression (5 tests):**
   ```bash
   NANOBRAGG_DISABLE_COMPILE=1 pytest -xvs tests/dbex/test_stage_b_asu_mapping.py
   ```
   Expected: 5/5 PASSED, runtime < 10s

3. **Shell mode regression (LBFGS path):**
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   DBEX_SMOKE_DETECTOR_SIZE=small \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -xvs tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers
   ```
   Expected: 1/1 PASSED, runtime ~14s, confirms LBFGS path unchanged

4. **Per-reflection smoke (Adam path, PRIMARY VALIDATION):**
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   DBEX_SMOKE_DETECTOR_SIZE=small \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -xvs tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke
   ```
   Expected: 1/1 PASSED, runtime ~25-35s, ASU modifier stats mean deviates from 1.0 by > 0.001 (gradient flow assertion passes)

### Decision Synthesis (4-Path Template)

**Path A (All 4 validations PASS):**
- Phase 7 gradient flow blocker  RESOLVED
- ASU modifiers update correctly under Adam optimization
- Commit message: "TORCH-REFINE-004 Phase 7: Fix Adam optimizer execution (manual loop pattern)  tests: per-reflection smoke PASSED"
- Write decision.json: `{"outcome": "success", "gradient_flow": "fixed", "tests_passed": "4/4"}`
- Write summary.md with Turn Summary
- Commit artifacts + code, push
- **Return to Galph:** Phase 7 complete, ready for Phase 8/9 planning (default enforcement + docs)

**Path B (Per-reflection test FAILS with different signature):**
- Root cause was partially correct, additional issue exists
- Capture new failure signature and logs in artifacts
- Write decision.json: `{"outcome": "partial", "issue": "<new_failure_description>"}`
- Debug: Add logging for Adam iteration loop (loss values, gradient norms, param deltas per iteration)
- Max 2 debug cycles before escalating to Galph

**Path C (Shell regression FAILS):**
- LBFGS path was inadvertently broken
- Revert changes to `else` branch, ensure exact copy of original line 3112
- Retry validation protocol
- Write decision.json: `{"outcome": "regression", "broken_path": "lbfgs"}`

**Path D (Compilation FAILS):**
- Syntax error in branching logic
- Fix syntax (check colons, indentation, variable names)
- Retry compilation check
- Write decision.json: `{"outcome": "syntax_error", "error": "<error_message>"}`

---

## How-To Map

### Environment Setup
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
export DBEX_SMOKE_SIGMA_SOURCE=cli_override
export DBEX_SMOKE_DETECTOR_SIZE=small
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
```

### Code Locations to Edit

1. **`dbex/nanobrag_refinement.py:3059`**  Extract `optimizer_type` from `param_values` dict
2. **`dbex/nanobrag_refinement.py:3111-3113`**  Replace `optimizer.step(closure)` with branching logic (~20 lines)
3. **`dbex/nanobrag_refinement.py:~2670`**  Add `'optimizer_type': optimizer_type` to `param_values_b` dict in inline path
4. **`dbex/refinement/stage_b.py:~250`**  Add `'optimizer_type': optimizer_type` to `param_values_b` dict in wrapper path

### Testing Commands (Sequential)

```bash
# 1. Compilation
python -c "from dbex.nanobrag_refinement import _run_stage_b_lbfgs; print('OK')"

# 2. Phase 6 unit regression
NANOBRAGG_DISABLE_COMPILE=1 pytest -xvs tests/dbex/test_stage_b_asu_mapping.py \
  > plans/active/TORCH-REFINE-004/reports/2025-11-24T110000Z/pytest_phase6_regression.log 2>&1

# 3. Shell mode regression (LBFGS)
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -xvs tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
  > plans/active/TORCH-REFINE-004/reports/2025-11-24T110000Z/pytest_shell_regression.log 2>&1

# 4. Per-reflection smoke (Adam, PRIMARY)
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -xvs tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke \
  > plans/active/TORCH-REFINE-004/reports/2025-11-24T110000Z/pytest_per_reflection_smoke_fixed.log 2>&1
```

### Artifacts to Capture

- `compilation_check.log`  Python import test output
- `pytest_phase6_regression.log`  5 ASU mapping unit tests
- `pytest_shell_regression.log`  Shell mode LBFGS regression (confirms LBFGS unchanged)
- `pytest_per_reflection_smoke_fixed.log`  Per-reflection Adam mode (PRIMARY validation, gradient flow fixed)
- `decision.json`  4-path decision outcome
- `summary.md`  Turn Summary with single-line problem/fix/next

---

## Pitfalls To Avoid

1. **Do NOT modify closure logic**  closure is correct, problem is in optimizer invocation pattern
2. **Do NOT change LBFGS `else` branch**  preserve exact original code `optimizer.step(closure_stage_b)` to prevent shell mode regression
3. **Do NOT add `optimizer_type` to RefinementConfig**  it's derived dynamically per run, not a config field
4. **Do ensure `optimizer_type` is passed in BOTH paths**  inline (_run_stage_b_lbfgs direct call) AND engine delegation (stage_b.py wrapper)
5. **Do NOT install packages**  Environment Freeze, code-only fix
6. **Do NOT skip validation steps**  all 4 tests must pass to confirm gradient flow fix + no regressions
7. **Do capture exact test failure signatures**  if per-reflection test fails with different error, log full output for Galph triage
8. **Do use `improvement_b` variable name**  avoid shadowing `improvement` from outer scope

---

## If Blocked

**Scenario 1: Cannot find where optimizer_type is set in _build_stage_b_params**

Search for `optimizer_type = "adam"` and `optimizer_type = "lbfgs"` in dbex/nanobrag_refinement.py (lines 2520, 2531, 2542). It's set inside the `if config_stage_b_mode_override == "per_reflection"` branch and the shell mode branch.

**Scenario 2: stage_b.py doesn't have access to optimizer_type**

Check how `_build_stage_b_params` is called in stage_b.py (likely around lines 180-220). The function should return or set `optimizer_type` as a local variable. If not, you may need to add it as a return value from the builder function.

**Scenario 3: Per-reflection test still fails after fix (different signature)**

- Capture full pytest output with `-vvs` flag
- Log Adam iteration loop: add `print(f"Adam iter {iteration_adam}: loss={loss.item():.4e}")` inside the loop
- Check if loss is decreasing across iterations
- Verify gradients are non-zero: add `for p in stage_b_params: print(f"grad norm: {p.grad.norm().item()}")` after `closure_stage_b()`
- Write detailed failure signature to decision.json and escalate to Galph

---

## Findings Applied

- **POLICY-001:** Environment Freeze (code-only, no package installs)
- **REFINE-001/002/005:** LBFGS scale warm-start, acceptance gate, halo mandatory (preserved in Adam path)
- **SCALE-001/002:** Structure factors unscaled (unchanged by optimizer choice)
- **PHYSICS-LOSS-001:** Variance-weighted loss (closure correct for both optimizers)
- **ARCH-ENGINE-002:** Lazy torch imports (no new imports required)
- **spec:59/60/61:** Per-reflection SHALL be default, shell fallback permitted, halo mandatory
- **spec:107:** Adam optimizer permitted for large parameter counts (implementation adheres to spec)
- **CLAUDE.md:** Incremental progress (single-loop fix, minimal scope, clear validation path)

---

## Pointers

- **Root Cause Analysis:** `plans/active/TORCH-REFINE-004/reports/2025-11-24T110000Z/gradient_flow_root_cause_analysis.md` (comprehensive 12-section analysis with evidence chain, PyTorch API docs, code locations, estimated effort)
- **Phase 7 Planning:** `plans/active/TORCH-REFINE-004/reports/2025-11-24T092549Z/phase_7_planning_analysis.md` (integration points, risk analysis, estimated effort)
- **Phase 6 Implementation:** `plans/active/TORCH-REFINE-004/reports/2025-11-24T130000Z/` (ASU mapping helpers + unit tests, all PASSED)
- **Implementation Plan:** `plans/active/TORCH-REFINE-004/implementation.md` (Phases 1-9 checklist)
- **Fix Plan Entry:** `docs/fix_plan.md:227` (TORCH-REFINE-004 status, dependencies, exit criteria, Attempts History)
- **PyTorch Optimizer API:** https://pytorch.org/docs/stable/optim.html (Adam vs LBFGS calling patterns)
- **Testing Guide:** `docs/TESTING_GUIDE.md` §2 (Stage B selectors + environment variables)

---

## Next Up

**After Phase 7 Fix Complete (Path A):**

Galph will plan Phase 8/9:
- Phase 8: Switch default from shell ’ per-reflection mode (update RefinementConfig default, update engine wrapper telemetry)
- Phase 9: Documentation + test registry sync (TESTING_GUIDE.md, TEST_SUITE_INDEX.md, collect-only artifacts)

**Estimated Total Remaining:** ~2-3 hours (Phase 8 default switch ~1h, Phase 9 docs ~1-2h)

---

**Estimated Effort (This Loop):** ~1.5 hours total
- Code changes: ~30 minutes (4 locations, ~20 lines total)
- Validation: ~45 minutes (4 sequential tests)
- Decision synthesis + commit: ~15 minutes

**Confidence:** HIGH (~95%)  Root cause definitively identified, fix is minimal and well-scoped, validation path is deterministic.
