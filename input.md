# ARCH-REFINE-FLOW-001 Phase B1a — Extract Stage A Helper Functions (IMPLEMENTATION REQUIRED)

## Summary
Extract ~1000 lines of inline LBFGS closure logic from `run_nanobrag_refinement` into three helper functions and refactor the main function to call them. **CRITICAL: This is a PRODUCTION CODE loop — you MUST modify dbex/nanobrag_refinement.py and run the regression guard test.**

## Mode
none (production refactoring with regression guard)

## Focus
ARCH-REFINE-FLOW-001 — Refactor to Protocol-based Refinement Engine (Phase B1a: Helper extraction)

## Branch
integration

## Mapped Tests
- **test_stage_a_expansion** (regression guard): `pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
  - **Acceptance:** MUST PASS with identical telemetry to baseline (small detector, 18.3% improvement)
  - **Environment:** `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`

## Artifacts
`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T034500Z/`
- `pytest_stage_a_regression.log` (MANDATORY — regression guard output)
- `telemetry_comparison.json` (MANDATORY — baseline vs extracted comparison)
- `summary.md` (MANDATORY — Turn Summary block)

## HARD REQUIREMENTS (Dwell Enforcement)
**This is the THIRD loop for Phase B1a focus. The last TWO loops were docs-only (planning + extraction documentation).**

Per Implementation Floor (hard) rule: "For a given focus, you may run at most one docs-only loop in a row. The next turn must hand off a Do Now with at least one production code task."

**You MUST complete ALL of Steps 1-10 in this loop, including:**
1. ✓ DONE (i=190): Phase B1a extraction documentation created
2. **NOW REQUIRED:** Extract `_build_stage_a_params` helper (Step 3)
3. **NOW REQUIRED:** Extract `_build_stage_a_lbfgs_closure` helper (Step 4)
4. **NOW REQUIRED:** Extract `_run_stage_a_lbfgs` helper (Step 5)
5. **NOW REQUIRED:** Refactor `run_nanobrag_refinement` to call helpers (Step 6)
6. **NOW REQUIRED:** Update final Bragg generation to use dicts (Step 7)
7. **NOW REQUIRED:** Run regression guard `test_stage_a_expansion` (Step 8)
8. **NOW REQUIRED:** Compare telemetry with baseline (Step 9)
9. **NOW REQUIRED:** Update implementation.md B1a checklist (Step 10)
10. **NOW REQUIRED:** Commit with production code changes and push

**BLOCKER ESCALATION:** If you encounter a blocker during Steps 3-7, document it in `phase_b1a_blocker.md` with:
- Exact error message
- Which step failed
- What you attempted
- Recommended escalation path
Then STOP and commit the blocker report. Do NOT deliver another docs-only artifact.

## Do Now (Steps 3-10 — PRODUCTION CODE REQUIRED)

### PRE-CHECK: Review Previous Work
You already completed Step 2 (inventory) in loop i=190:
- ✓ Documentation: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T032647Z/phase_b1a_extraction.md` (350 lines)
- ✓ Boundaries identified: Section 1 (lines 761-935), Section 2 (lines 998-1573), Section 3 (lines 1575-1685)
- ✓ Nonlocal variables documented: ~30 variables (params, telemetry, stage_a_context)
- ✓ Helper signatures defined: _build_stage_a_params, _build_stage_a_lbfgs_closure, _run_stage_a_lbfgs

**DO NOT re-document or re-inventory. Proceed directly to Step 3 (extraction).**

### Step 3: Extract `_build_stage_a_params` helper
**Location:** Add before `run_nanobrag_refinement` in `dbex/nanobrag_refinement.py` (around line 650)

**Action:** Copy lines 761-935 from `run_nanobrag_refinement` into this helper with the exact signature from your extraction.md.

**Returns:** Dict with keys `params`, `param_values`, `telemetry_state`, `stage_a_context`, `optimizer`

**Critical:**
- Preserve ALL 3 parameterization modes (cell+misset, U-matrix, incremental UB)
- Keep optimizer initialization (LBFGS with history_size, line_search_fn="strong_wolfe")
- Keep all telemetry accumulator initialization (list comprehensions, mutable [0] counters)
- Keep ROI/panel sampling logic
- Keep warm-cache context building

### Step 4: Extract `_build_stage_a_lbfgs_closure` helper
**Location:** Add after `_build_stage_a_params` (around line 900)

**Action:** Copy lines 998-1573 from `run_nanobrag_refinement` into this helper.

**Structure:**
```python
def _build_stage_a_lbfgs_closure(...):
    # Define nested compute_loss function (lines 998-1406)
    def compute_loss(work_item_ids, is_full):
        # ... exact copy of original compute_loss ...
        return chi_squared_loss, masked_mse_loss

    # Define nested closure function (lines 1408-1573)
    def closure():
        # ... exact copy of original closure ...
        return chi_squared_loss

    # Return both functions as tuple
    return (closure, compute_loss)
```

**Critical:**
- Nested functions MUST capture variables from helper parameters via lexical scope (not function parameters)
- Keep lazy imports (nanobrag_bridge imports INSIDE compute_loss, not at module level)
- Preserve lifecycle telemetry (U-matrix mode)
- Keep gradient validation (NaN/Inf check)
- Keep periodic full validation logic

### Step 5: Extract `_run_stage_a_lbfgs` helper
**Location:** Add after `_build_stage_a_lbfgs_closure` (around line 1400)

**Action:** Copy lines 1575-1685 from `run_nanobrag_refinement` into this helper.

**Returns:** Tuple `(status, message, final_chi_squared_value, final_masked_mse_value)`

**Critical:**
- Exception handling wrapper (try/except around optimizer.step)
- Final validation with compute_loss_fn
- Convergence check (≥0.2% improvement gate per REFINE-006)
- Best params rollback on error
- Fallback telemetry population

### Step 6: Refactor `run_nanobrag_refinement` to call helpers
**Action:** Replace lines ~761-1685 with ~20 lines calling the three helpers:

```python
# ARCH-REFINE-FLOW-001 Phase B1a: Extract Stage A helper functions
param_data = _build_stage_a_params(
    crystal=crystal,
    detector=detector,
    inputs=inputs,
    config=config,
    device=device,
    dtype=dtype,
    hkl_grid=hkl_grid,
    hkl_metadata=hkl_metadata,
    sigma_floor_sq_cache=sigma_floor_sq_cache,
    baseline_crystal=baseline_crystal,
    baseline_detector=baseline_detector
)

params = param_data['params']
param_values = param_data['param_values']
telemetry_state = param_data['telemetry_state']
stage_a_context = param_data['stage_a_context']
optimizer = param_data['optimizer']

closure, compute_loss_fn = _build_stage_a_lbfgs_closure(
    param_values=param_values,
    telemetry_state=telemetry_state,
    stage_a_context=stage_a_context,
    inputs=inputs,
    detector=detector,
    beam=beam,
    crystal=crystal,
    hkl_grid=hkl_grid,
    hkl_metadata=hkl_metadata,
    config=config,
    device=device,
    dtype=dtype,
    optimizer=optimizer,
    sigma_floor_sq_cache=sigma_floor_sq_cache,
    baseline_crystal=baseline_crystal,
    baseline_detector=baseline_detector
)

status, message, final_chi_squared_value, final_masked_mse_value = _run_stage_a_lbfgs(
    optimizer=optimizer,
    closure=closure,
    compute_loss_fn=compute_loss_fn,
    param_values=param_values,
    telemetry_state=telemetry_state,
    stage_a_context=stage_a_context,
    config=config,
    device=device,
    dtype=dtype
)
```

### Step 7: Update final Bragg generation + telemetry packaging
**Action:** Update lines ~1686-1900 to access variables via dicts instead of direct references.

**Examples:**
- `log_scale.item()` → `param_values['log_scale'].item()`
- `chi_squared_trace_full` → `telemetry_state['chi_squared_trace_full']`
- `canonical_roi_count` → `stage_a_context['canonical_roi_count']`
- `iteration_count[0]` → `telemetry_state['iteration_count'][0]`

### Step 8: Run regression guard (MANDATORY)
```bash
mkdir -p plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T034500Z

AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T034500Z/pytest_stage_a_regression.log 2>&1
```

**Acceptance:** Test MUST PASS. If it fails:
1. Check the log for errors
2. Compare parameter initialization between helpers and original
3. Verify nonlocal variable captures in closure
4. Document blocker in `phase_b1a_blocker.md` if you can't resolve in this loop

### Step 9: Compare telemetry with baseline (MANDATORY)
```python
import json

baseline = json.load(open("plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/baseline/telemetry_small.json"))
# Extract telemetry from the test run (look for test_stage_a_expansion output files)

comparison = {
    "chi_squared_initial": {
        "baseline": baseline.get("chi_squared_trace_full", [[None, None]])[0][1] if baseline.get("chi_squared_trace_full") else None,
        "extracted": "...",  # From current run
        "match": "..."
    },
    "chi_squared_final": {...},
    "iteration_count": {...},
    "improvement_percent": {...}
}

with open("plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T034500Z/telemetry_comparison.json", "w") as f:
    json.dump(comparison, f, indent=2)
```

### Step 10: Update implementation checklist and commit (MANDATORY)
**Action:**
1. Open `plans/active/ARCH-REFINE-FLOW-001/implementation.md`
2. Mark B1a as complete:
   ```markdown
   - [x] B1a: **Extract helper functions from inline LBFGS closure** (Loop 1): ✓ COMPLETE (2025-11-23T034500Z)
   ```
3. Write `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T034500Z/summary.md` with Turn Summary block
4. Commit with message:
   ```
   ARCH-REFINE-FLOW-001 Phase B1a: Extract Stage A helper functions

   Refactored ~1000 lines of inline LBFGS closure logic into three helpers:
   - _build_stage_a_params: Parameter initialization + telemetry state
   - _build_stage_a_lbfgs_closure: Nested compute_loss + closure functions
   - _run_stage_a_lbfgs: Optimizer execution + final validation

   Regression guard PASSED: test_stage_a_expansion (small detector).
   Telemetry parity verified: chi² traces identical to baseline.

   Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T034500Z/

   tests: not run
   ```
5. Push

---

## How-To Map

### Environment
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
export DBEX_SMOKE_SIGMA_SOURCE=cli_override
export DBEX_SMOKE_DETECTOR_SIZE=small
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
```

### Extract helpers (Steps 3-5)
1. Add `_build_stage_a_params` at line ~650 in dbex/nanobrag_refinement.py
2. Add `_build_stage_a_lbfgs_closure` at line ~900 (after _build_stage_a_params)
3. Add `_run_stage_a_lbfgs` at line ~1400 (after _build_stage_a_lbfgs_closure)
4. Refactor `run_nanobrag_refinement` lines ~761-1685 → ~50 lines of helper calls (Step 6)
5. Update final Bragg generation lines ~1686-1900 to use dicts (Step 7)

### Regression guard (Step 8)
```bash
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T034500Z/pytest_stage_a_regression.log 2>&1
```

### Telemetry comparison (Step 9)
Create `telemetry_comparison.json` comparing baseline (from B0) with extracted helpers run.

---

## Pitfalls To Avoid

1. **DO NOT deliver another docs-only artifact** — You MUST modify dbex/nanobrag_refinement.py and run tests
2. **DO NOT change parameter initialization logic** — Extract as-is, preserve all 3 modes
3. **DO NOT break lexical scope captures** — Nested functions must capture via closure, not parameters
4. **DO NOT forget to return `compute_loss`** — `_run_stage_a_lbfgs` needs it for final validation
5. **DO NOT introduce new imports** — All imports stay as they were (lazy imports for nanobrag_bridge)
6. **DO NOT modify telemetry field names** — Preserve backward compatibility
7. **DO NOT remove comments** — Preserve TORCH-REFINE-* / PHYSICS-LOSS-* annotations
8. **DO NOT change optimizer behavior** — LBFGS config must stay identical
9. **DO NOT commit if regression guard fails** — Debug first; extraction must be behavior-preserving
10. **DO NOT skip telemetry comparison** — Even if test passes, verify chi² traces match baseline

---

## If Blocked

### Scenario A: Regression guard fails with different chi² values
**Action:**
1. Compare `telemetry_comparison.json` to identify which parameter diverged
2. Check that all helper parameters are passed correctly
3. Verify `param_values` dict construction
4. Document blocker in `phase_b1a_blocker.md` with exact divergence point
5. Commit blocker report (do NOT deliver docs-only artifact)

### Scenario B: Regression guard fails with import/syntax errors
**Action:**
1. Verify helpers are defined BEFORE `run_nanobrag_refinement`
2. Check lazy imports (nanobrag_bridge INSIDE nested functions)
3. Ensure nanobrag_torch imports stay lazy
4. Document blocker in `phase_b1a_blocker.md`
5. Commit blocker report

### Scenario C: Cannot complete extraction in reasonable time
**Action:**
1. Document progress (which helpers extracted, which tests pass)
2. Create `phase_b1a_partial_progress.md` with status
3. Commit partial work if at least ONE helper is extracted and wired
4. DO NOT commit if zero production code changes

---

## Findings Applied
- **CONVERGENCE-001**: Preserve U-matrix lifecycle telemetry in closure
- **GEOMETRY-003**: Preserve MOSFLM baseline misset derivation
- **GEOMETRY-004**: Preserve incremental UB initialization
- **REFINE-006**: Preserve ≥0.2% improvement gate
- **PHYSICS-LOSS-001**: Preserve dual metric tracking (chi_squared + masked_mse)
- **PERF-WARM-SIM-001**: Preserve stage_a_ctx, perf counters, sampled indices
- **GRADIENT-001**: Preserve MOSFLM a/b/c_star path (no cell overrides)

---

## Pointers

### Extraction Documentation (From i=190)
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T032647Z/phase_b1a_extraction.md` — Your 350-line boundary analysis

### Baseline Artifacts (From B0)
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/baseline/telemetry_small.json` — Baseline for comparison
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/baseline/pytest_small.log` — Expected test output

### Implementation Plan
- `plans/active/ARCH-REFINE-FLOW-001/implementation.md:86-90` — Phase B1a checklist

### Code Target
- `dbex/nanobrag_refinement.py:680-3048` — Target file for extraction
- `dbex/nanobrag_refinement.py:761-876` → `_build_stage_a_params`
- `dbex/nanobrag_refinement.py:998-1573` → `_build_stage_a_lbfgs_closure`
- `dbex/nanobrag_refinement.py:1575-1685` → `_run_stage_a_lbfgs`

---

## Next Up
If B1a completes successfully (all tests PASS):
- **B1b (next loop):** Wrap helpers in StageA.run() class method
- **B2 (loop after):** Update run_nanobrag_refinement for engine delegation

If blocked:
- Document blocker in `phase_b1a_blocker.md`
- Supervisor reviews and decides path forward
