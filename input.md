# ARCH-REFINE-FLOW-001 Phase B1a — Extract Stage A Helper Functions

## Summary
Extract ~1000 lines of inline LBFGS closure logic from `run_nanobrag_refinement` into three helper functions: `_build_stage_a_params`, `_build_stage_a_lbfgs_closure`, and `_run_stage_a_lbfgs`. This is the first loop in a multi-loop extraction strategy approved by supervisor (2025-11-23T030000Z).

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
`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T<HHMMSSZ>/`
- `phase_b1a_extraction.md` (helper function signatures + docstrings + nonlocal variable inventory)
- `pytest_stage_a_regression.log`
- `telemetry_comparison.json` (side-by-side comparison: baseline vs extracted helpers)
- `summary.md` (Turn Summary block)

## Do Now (10 steps)

### 1. Review Phase B blocker report and implementation plan
Read `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/phase_b_blocker.md` to understand the extraction strategy.
Read `plans/active/ARCH-REFINE-FLOW-001/implementation.md` Phase B (lines 80-104) for updated checklist.

### 2. Inventory nonlocal variables and boundaries
Before extraction, document the exact boundaries and dependencies:
- **Lines ~761-876**: Parameter initialization (returns: list of trainable tensors)
- **Lines ~878-935**: Optimizer setup + telemetry accumulators (closure dependencies)
- **Lines 998-1407**: `compute_loss` nested function
- **Lines 1408-1573**: `closure` nested function
- **Lines 1575-1685**: LBFGS execution + final validation

Nonlocal variables accessed by `compute_loss` and `closure` (~30 variables):
- `config`, `device`, `dtype`, `inputs`, `detector`, `beam`, `crystal`, `hkl_grid`, `hkl_metadata`
- `baseline_crystal`, `baseline_detector`
- All trainable params: `log_scale`, `log_cell_*_delta`, `angle_*_raw`, `orientation_vec`, `q_params` (U-matrix mode), `q_delta`, `delta_log_*`, `delta_*` (incremental UB mode)
- `U_baseline`, `cell_baseline`, `B_ideal_reciprocal_torch`
- Telemetry accumulators: `loss_trace_*`, `chi_squared_*`, `masked_mse_*`, `best_*`, `iteration_count`, `perf_*`, `variance_floor_*`
- `sigma_floor_sq_tensor`, `sigma_floor_sq_cache`
- `canonical_roi_count`, `canonical_detector_distances`, `canonical_baseline`
- `sampled_stage_a_indices`, `full_stage_a_indices`, `stage_a_ctx`
- Lifecycle logs: `u_matrix_lifecycle_log`, `a_star_lifecycle_log`, `telemetry_step_counter`

Create `phase_b1a_extraction.md` documenting these dependencies.

### 3. Extract `_build_stage_a_params` helper
**Signature:**
```python
def _build_stage_a_params(
    crystal,
    detector,
    inputs: RefinementInputs,
    config: RefinementConfig,
    device: torch.device,
    dtype: torch.dtype,
    baseline_crystal=None,
    baseline_detector=None
) -> Dict[str, Any]:
    """
    Initialize Stage A trainable parameters and telemetry state.

    Returns dict with keys:
    - 'params': List of trainable tensors for optimizer
    - 'param_values': Dict mapping parameter names to tensors (for closure access)
    - 'telemetry_state': Dict with accumulators (loss_trace_*, iteration_count, etc.)
    - 'stage_a_context': Dict with ROI sampling, warm-cache ctx, canonical baselines
    """
```

**Task:** Extract lines ~761-935 into this helper. Preserve all initialization logic for:
- Default cell+misset path (orientation_vec, log_cell_*_delta, angle_*_raw)
- U-matrix quaternion path (q_params, B_ideal_reciprocal_torch)
- Incremental UB path (q_delta, delta_log_*, delta_*, U_baseline, cell_baseline)
- Optimizer setup (torch.optim.LBFGS)
- All telemetry accumulators
- ROI/panel sampling (sampled_stage_a_indices, full_stage_a_indices, stage_a_ctx)
- Canonical baselines

**Location:** Add before `run_nanobrag_refinement` in `dbex/nanobrag_refinement.py` (around line 650)

### 4. Extract `_build_stage_a_lbfgs_closure` helper
**Signature:**
```python
def _build_stage_a_lbfgs_closure(
    param_values: Dict[str, torch.Tensor],
    telemetry_state: Dict[str, Any],
    stage_a_context: Dict[str, Any],
    inputs: RefinementInputs,
    detector,
    beam,
    crystal,
    hkl_grid: torch.Tensor,
    hkl_metadata: Dict,
    config: RefinementConfig,
    device: torch.device,
    dtype: torch.dtype,
    optimizer: torch.optim.Optimizer,
    sigma_floor_sq_cache: Dict,
    baseline_crystal=None,
    baseline_detector=None
) -> Tuple[Callable[[], torch.Tensor], Callable[[List[int], bool], Tuple[torch.Tensor, torch.Tensor]]]:
    """
    Build LBFGS closure function for Stage A optimization.

    Returns tuple: (closure_fn, compute_loss_fn)
    - closure_fn: LBFGS closure that calls compute_loss + backward, returns chi_squared_loss
    - compute_loss_fn: The nested compute_loss function, needed by _run_stage_a_lbfgs for final validation

    The returned closure captures all parameters and state via lexical scope
    (following original inline pattern).

    Closure structure:
    1. Defines nested `compute_loss(work_item_ids, is_full)` function
    2. Defines nested `closure()` function that calls compute_loss + backward
    3. Returns tuple (closure, compute_loss)
    """
```

**Task:** Extract lines 998-1573 (both `compute_loss` and `closure` nested functions) into this helper. The helper should:
1. Define `compute_loss` (lines 998-1407) as a nested function
2. Define `closure` (lines 1408-1573) as a nested function
3. Return tuple `(closure, compute_loss)`

**Critical:** Preserve all lexical scope captures. The nested functions access `param_values`, `telemetry_state`, etc. via closure capture (not function parameters).

**Location:** Add after `_build_stage_a_params` (around line 900)

### 5. Extract `_run_stage_a_lbfgs` helper
**Signature:**
```python
def _run_stage_a_lbfgs(
    optimizer: torch.optim.Optimizer,
    closure: Callable[[], torch.Tensor],
    compute_loss_fn: Callable[[List[int], bool], Tuple[torch.Tensor, torch.Tensor]],
    param_values: Dict[str, torch.Tensor],
    telemetry_state: Dict[str, Any],
    stage_a_context: Dict[str, Any],
    config: RefinementConfig,
    device: torch.device,
    dtype: torch.dtype
) -> Tuple[str, str, Optional[float], Optional[float]]:
    """
    Execute LBFGS optimization and final validation.

    Returns tuple: (status, message, final_chi_squared_value, final_masked_mse_value)
    where status is "ok" | "early_stop" | "error"
    """
```

**Task:** Extract lines 1575-1685 (optimizer.step + final validation + convergence check). This includes:
- Exception handling wrapper
- `optimizer.step(closure)`
- Final full validation with `compute_loss_fn`
- Convergence check (`improvement < min_loss_improvement`)
- Best params snapshot rollback on error
- Fallback telemetry population

**Location:** Add after `_build_stage_a_lbfgs_closure` (around line 1400)

### 6. Refactor `run_nanobrag_refinement` to call helpers
Replace the inline logic (lines ~761-1685) with:

```python
# Extract Stage A helper functions (ARCH-REFINE-FLOW-001 Phase B1a)
param_data = _build_stage_a_params(
    crystal=crystal,
    detector=detector,
    inputs=inputs,
    config=config,
    device=device,
    dtype=dtype,
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

### 7. Preserve telemetry field access after helpers
After calling the helpers, the remaining code (lines ~1686-1900, final Bragg generation + telemetry packaging) needs access to:
- `param_values` dict (for final parameter values)
- `telemetry_state` dict (for loss traces, iteration count, etc.)
- `stage_a_context` dict (for ROI counts, cache mode, etc.)
- `status`, `message`, `final_chi_squared_value`, `final_masked_mse_value` from `_run_stage_a_lbfgs`

Update the final Bragg generation loop and telemetry packaging to use these dicts instead of direct variable references.

**Example:**
```python
# Old (inline):
log_scale_final = float(log_scale.item())

# New (after helpers):
log_scale_final = float(param_values['log_scale'].item())
```

### 8. Run regression guard
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T<HHMMSSZ>/pytest_stage_a_regression.log 2>&1
```

**Acceptance:** Test MUST PASS. If it fails, debug the helper extraction (most likely cause: missing nonlocal variable or broken lexical scope).

### 9. Compare telemetry with baseline
Extract telemetry from both runs and verify they are identical:

```python
# Micro probe (T0): Compare telemetry
import json
baseline_telem = json.load(open("plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/baseline/telemetry_small.json"))
extracted_telem = json.load(open("plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T<HHMMSSZ>/telemetry_extracted.json"))

# Compare critical fields
comparison = {
    "chi_squared_initial": {
        "baseline": baseline_telem.get("chi_squared_trace_full", [[None, None]])[0][1],
        "extracted": extracted_telem.get("chi_squared_trace_full", [[None, None]])[0][1],
        "match": ...,
    },
    "chi_squared_final": {...},
    "iteration_count": {...},
    "improvement": {...},
}

with open("plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T<HHMMSSZ>/telemetry_comparison.json", "w") as f:
    json.dump(comparison, f, indent=2)
```

Embed this comparison in `summary.md`.

### 10. Update implementation checklist and commit
Mark B1a complete in `plans/active/ARCH-REFINE-FLOW-001/implementation.md`:
```markdown
- [x] B1a: **Extract helper functions from inline LBFGS closure** (Loop 1): ✓ COMPLETE (2025-11-23T<HHMMSSZ>)
```

Write `summary.md` with Turn Summary block (see End-of-Loop Hygiene).

Commit with message:
```
ARCH-REFINE-FLOW-001 Phase B1a: Extract Stage A helper functions

Refactored ~1000 lines of inline LBFGS closure logic into three helpers:
- _build_stage_a_params: Parameter initialization + telemetry state (lines 650-750)
- _build_stage_a_lbfgs_closure: Nested compute_loss + closure functions (lines 750-1400)
- _run_stage_a_lbfgs: Optimizer execution + final validation (lines 1400-1500)

Regression guard PASSED: test_stage_a_expansion (small detector, 18.3% improvement).
Telemetry parity verified: chi² traces, iteration count, improvement identical to baseline.

Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T<HHMMSSZ>/

tests: not run
```

Push.

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
1. Create `phase_b1a_extraction.md` documenting boundaries and nonlocal variables
2. Add `_build_stage_a_params` at line ~650
3. Add `_build_stage_a_lbfgs_closure` at line ~900 (returns tuple `(closure, compute_loss)`)
4. Add `_run_stage_a_lbfgs` at line ~1400
5. Refactor `run_nanobrag_refinement` to call helpers (lines ~761-1685 → ~20 lines of helper calls)
6. Update final Bragg generation + telemetry packaging to use dicts

### Regression guard (Step 8)
```bash
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T<HHMMSSZ>/pytest_stage_a_regression.log 2>&1
```

### Telemetry comparison (Step 9)
```bash
python -c "
import json
baseline = json.load(open('plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/baseline/telemetry_small.json'))
extracted = json.load(open('plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T<HHMMSSZ>/telemetry_extracted.json'))
# Compare and write comparison.json
"
```

---

## Pitfalls To Avoid

1. **DO NOT change parameter initialization logic** — Extract as-is, preserve all 3 modes (cell+misset, U-matrix, incremental UB)
2. **DO NOT break lexical scope captures** — Nested functions in `_build_stage_a_lbfgs_closure` must capture variables via closure, not parameters
3. **DO NOT forget to return `compute_loss`** — `_run_stage_a_lbfgs` needs it for final validation
4. **DO NOT introduce new imports** — All imports must stay exactly as they were (lazy imports for nanobrag_bridge)
5. **DO NOT modify telemetry field names** — Preserve backward compatibility (chi_squared_trace_full, masked_mse_trace_full, etc.)
6. **DO NOT skip telemetry comparison** — Even if test passes, verify chi² traces are identical to baseline
7. **DO NOT remove comments** — Preserve all TORCH-REFINE-* / PHYSICS-LOSS-* / PERF-WARM-SIM-* annotations
8. **DO NOT change optimizer behavior** — LBFGS(params, history_size, ..., line_search_fn="strong_wolfe") must stay identical
9. **DO NOT add docstrings to nested functions** — `compute_loss` and `closure` nested inside `_build_stage_a_lbfgs_closure` should keep their current docstrings
10. **DO NOT commit if regression guard fails** — Debug first; extraction must be behavior-preserving

---

## If Blocked

### Scenario A: Regression guard fails with different chi² values
**Cause:** Missing nonlocal variable or broken parameter flow
**Action:**
1. Compare `telemetry_comparison.json` to identify which parameter diverged
2. Check that helper functions receive ALL required inputs
3. Verify `param_values` dict is properly constructed and accessed
4. Add debug prints to compare parameter values at closure entry
5. Document blocker in `phase_b1a_blocker.md` with exact divergence point

### Scenario B: Regression guard fails with import/syntax errors
**Cause:** Circular import or missing lazy import
**Action:**
1. Verify helpers are defined BEFORE `run_nanobrag_refinement` (not after)
2. Check that `from dbex.nanobrag_bridge import ...` remains INSIDE nested functions (not at module level)
3. Ensure `nanobrag_torch` imports stay lazy (inside compute_loss, not at top)
4. Document blocker in `phase_b1a_blocker.md`

### Scenario C: Telemetry comparison shows identical test results but different trace lengths
**Cause:** Iteration count logic changed or full_validation_interval mismatch
**Action:**
1. Verify `iteration_count[0]` is properly captured in `telemetry_state` dict
2. Check `config.full_validation_interval` is passed correctly
3. Ensure periodic validation logic (lines 1519-1554) is preserved exactly
4. Document in `phase_b1a_blocker.md` if tracing logic is fundamentally incompatible with helper extraction

---

## Findings Applied

- **CONVERGENCE-001** (zero-delta bypass, lifecycle tracking): Preserve U-matrix lifecycle telemetry in closure
- **GEOMETRY-003** (MOSFLM baseline misset): Preserve baseline_crystal derivation in param init
- **GEOMETRY-004** (incremental UB): Preserve q_delta/delta_log_*/U_baseline initialization
- **REFINE-006** (≥0.2% improvement gate): Preserve convergence check in `_run_stage_a_lbfgs`
- **PHYSICS-LOSS-001** (variance-weighted loss): Preserve dual metric tracking (chi_squared + masked_mse)
- **PERF-WARM-SIM-001** (warm-cache/ROI contract): Preserve stage_a_ctx, perf counters, sampled_stage_a_indices
- **GRADIENT-001** (no cell overrides with MOSFLM injection): Preserve MOSFLM a/b/c_star path in compute_loss
- **REFINE-005** (HKL halo/interpolation): Not directly relevant to extraction, but preserve hkl_grid handling

---

## Pointers

### Specs
- `docs/spec-db-workflow.md:33` — Refinement Protocol Architecture (Engine Contract)
- `docs/spec-db-core.md:57-68` — Variance model (variance-weighted loss)

### Architecture
- `docs/architecture/pytorch_design.md` — Vectorization, absorption, tricubic (not directly relevant but context)
- `plans/active/ARCH-REFINE-FLOW-001/implementation.md:80-104` — Phase B checklist

### Testing
- `docs/TESTING_GUIDE.md:136` — ARCH-ENGINE-001 test registry entry (Phase A)
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/baseline/` — Baseline artifacts (small detector: 18.3% improvement, chi²: 807M → 659M)

### Fix Plan
- `docs/fix_plan.md:184-197` — ARCH-REFINE-FLOW-001 initiative row + Attempts History
- `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/phase_b_blocker.md` — Ralph's blocker report explaining why multi-loop extraction is needed

### Code
- `dbex/nanobrag_refinement.py:680-3048` — Target file for extraction
- `dbex/nanobrag_refinement.py:761-876` — Parameter initialization (→ `_build_stage_a_params`)
- `dbex/nanobrag_refinement.py:998-1573` — Nested functions (→ `_build_stage_a_lbfgs_closure`)
- `dbex/nanobrag_refinement.py:1575-1685` — LBFGS execution (→ `_run_stage_a_lbfgs`)

---

## Next Up
If B1a completes successfully:
- **B1b (next loop):** Wrap helpers in StageA.run() class method
- **B2 (loop after):** Update run_nanobrag_refinement for engine delegation

If blocked:
- Document blocker in `phase_b1a_blocker.md` with exact error, attempted fixes, and recommended escalation path
- Supervisor reviews and decides: (A) Revise extraction strategy, (B) Defer Phase B, or (C) Different initiative
