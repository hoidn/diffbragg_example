# Ralph Input — Phase B2: Engine Delegation for Stage-A-Only Mode

**Loop:** i=196
**Date:** 2025-11-23T050432Z
**Initiative:** ARCH-REFINE-FLOW-001 Phase B2
**Branch:** integration
**Mode:** TDD (validate engine delegation produces identical outputs to inline path)

## Summary

Implement conditional engine delegation for Stage-A-only mode in `run_nanobrag_refinement`. When both `enable_stage_c=False` and `enable_stage_b=False`, delegate to `RefinementEngine([StageA()])` instead of calling inline helpers. Keep Stage B/C inline temporarily (Phases C/D will extract them).

## Focus

**ARCH-REFINE-FLOW-001** — Protocol-based Refinement Engine (Phase B2)

## Mapped Tests

- `pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (regression guard, engine path)
- `pytest -vv tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage` (engine contract)

## Artifacts

`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050432Z/`
- `pytest_stage_a_expansion.log` (regression guard test output)
- `pytest_engine.log` (engine contract validation)
- `phase_b2_implementation_summary.md` (implementation notes)
- `summary.md` (Turn Summary block)

## Do Now (10 tasks)

**CRITICAL:** This is a production code change. You MUST implement the engine delegation logic and extract the final Bragg reconstruction helper. The regression guard test_stage_a_expansion will validate the engine path produces identical results to the inline path.

### Task 1: Review Phase B1b completion evidence

**Action:** Read artifacts from Phase B1b (plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T045012Z/)
- Read `phase_b1b_implementation_summary.md` to understand StageA.run() implementation
- Read `pytest_stage_a_expansion.log` to confirm baseline test behavior
- Note: StageA.run() calls three extracted helpers and returns telemetry dict

**Validation:** Confirm StageA.run() exists at dbex/refinement/stage_a.py:62-367

### Task 2: Extract _build_final_bragg_from_stage_a_telemetry helper

**File:** `dbex/nanobrag_refinement.py`

**Action:** Extract the final Bragg reconstruction logic (current lines ~2046-2285) into a new helper function. Place this helper immediately after `_run_stage_a_lbfgs` (around line 1888).

**IMPORTANT:** Copy lines 2046-2285 EXACTLY as they are. The only changes should be:
1. Wrap in a function definition with signature below
2. Extract param_deltas from telemetry parameter (added at top)
3. Add proper imports if needed

**Helper signature:**
```python
def _build_final_bragg_from_stage_a_telemetry(
    telemetry_a: RefinementTelemetry,
    detector,
    beam,
    crystal,
    inputs,
    hkl_grid: torch.Tensor,
    hkl_metadata: Dict,
    config: RefinementConfig,
    device: torch.device,
    dtype: torch.dtype,
) -> np.ndarray:
    """
    Build final Bragg array from Stage A telemetry (optimized parameters).
    
    Extracts optimized parameters from telemetry.param_deltas and regenerates
    full Bragg image by looping over panels with final crystal geometry.
    
    Args:
        telemetry_a: RefinementTelemetry instance with optimized param_deltas
        detector: dxtbx Detector object
        beam: dxtbx Beam object  
        crystal: dxtbx Crystal object
        inputs: RefinementInputs with panel_slices, trusted_mask
        hkl_grid: torch.Tensor structure factor grid
        hkl_metadata: dict with grid dimensions
        config: RefinementConfig with device, dtype, parameterization mode
        device: torch.device for tensor operations
        dtype: torch.dtype for tensor operations
    
    Returns:
        bragg_full: np.ndarray, shape [n_panels, slow, fast], final Bragg image
    """
    # Extract param_deltas from telemetry (already a dict)
    param_deltas = telemetry_a.param_deltas if hasattr(telemetry_a, 'param_deltas') else telemetry_a['param_deltas']
    
    # Convert param deltas to torch tensors (no requires_grad, final forward pass)
    log_scale = torch.tensor(param_deltas['log_scale'], device=device, dtype=dtype, requires_grad=False)
    log_cell_a_delta = torch.tensor(param_deltas['log_cell_a_delta'], device=device, dtype=dtype, requires_grad=False)
    log_cell_b_delta = torch.tensor(param_deltas['log_cell_b_delta'], device=device, dtype=dtype, requires_grad=False)
    log_cell_c_delta = torch.tensor(param_deltas['log_cell_c_delta'], device=device, dtype=dtype, requires_grad=False)
    angle_alpha_raw = torch.tensor(param_deltas['angle_alpha_raw'], device=device, dtype=dtype, requires_grad=False)
    angle_beta_raw = torch.tensor(param_deltas['angle_beta_raw'], device=device, dtype=dtype, requires_grad=False)
    angle_gamma_raw = torch.tensor(param_deltas['angle_gamma_raw'], device=device, dtype=dtype, requires_grad=False)
    orientation_vec = torch.tensor(param_deltas['orientation_vec'], device=device, dtype=dtype, requires_grad=False)
    
    # Extract optional params for U-matrix/incremental UB modes
    q_params = param_deltas.get('q_params')
    if q_params is not None:
        q_params = torch.tensor(q_params, device=device, dtype=dtype, requires_grad=False)
    
    q_delta = param_deltas.get('q_delta')
    if q_delta is not None:
        q_delta = torch.tensor(q_delta, device=device, dtype=dtype, requires_grad=False)
    
    B_ideal_reciprocal_torch = param_deltas.get('B_ideal_reciprocal_torch')
    if B_ideal_reciprocal_torch is not None:
        B_ideal_reciprocal_torch = torch.tensor(B_ideal_reciprocal_torch, device=device, dtype=dtype, requires_grad=False)
    
    # Get n_panels and panel_shape
    n_panels = len(detector)
    panel_shape = inputs.target.shape[1:]  # (slow, fast)
    
    # === NOW COPY LINES 2046-2285 EXACTLY ===
    # (The panel loop that regenerates Bragg array with optimized parameters)
    
    # Generate final Bragg array with optimized parameters
    with torch.no_grad():
        bragg_full = np.zeros((n_panels, *panel_shape), dtype=np.float32)
        
        # ... COPY THE REST OF THE PANEL LOOP FROM LINES 2049-2285 ...
    
    return bragg_full
```

**Validation:** Helper function compiles without errors

### Task 3: Add stage detection logic

**File:** `dbex/nanobrag_refinement.py`
**Location:** After line 1951 (`if config is None: config = RefinementConfig()`)

**Action:** Add stage detection logic:
```python
# Detect Stage-A-only mode for conditional engine delegation (Phase B2)
stage_a_only_mode = (not config.enable_stage_c and not config.enable_stage_b)
```

**Validation:** Variable `stage_a_only_mode` is boolean

### Task 4: Implement engine delegation branch

**File:** `dbex/nanobrag_refinement.py`
**Location:** Immediately after Task 3 stage detection logic

**Action:** Add full engine delegation branch:
```python
if stage_a_only_mode:
    # === ENGINE DELEGATION PATH (Phase B2) ===
    # Lazy imports to avoid circular dependencies at module load time
    from dbex.refinement.engine import RefinementEngine
    from dbex.refinement.stage_a import StageA
    
    # Build inputs dict per StageA.run() contract (dbex/refinement/stage_a.py:71-78)
    engine_inputs = {
        'refinement_inputs': inputs,
        'detector': detector,
        'beam': beam,
        'crystal': crystal,
        'hkl_grid': hkl_grid,
        'hkl_metadata': hkl_metadata,
        'baseline_crystal': baseline_crystal,
        'baseline_detector': baseline_detector,
    }
    
    # Instantiate RefinementEngine with StageA
    engine = RefinementEngine(stages=[StageA()], config=config)
    
    # Execute engine and get telemetry dict (keyed by stage.name = "stage_a")
    telemetry_dict = engine.run(engine_inputs)
    
    # Extract StageA telemetry (keyed by "stage_a" per StageA.name property)
    telemetry_a = telemetry_dict["stage_a"]
    
    # Build final Bragg array using optimized parameters from telemetry
    device = torch.device(config.device)
    dtype = config.dtype
    bragg_full = _build_final_bragg_from_stage_a_telemetry(
        telemetry_a, detector, beam, crystal, inputs, hkl_grid,
        hkl_metadata, config, device, dtype
    )
    
    # Return with telemetry dict using "A" key for backward compatibility
    # (Legacy code expects {"A": RefinementTelemetry, ...})
    return bragg_full, {"A": telemetry_a}

else:
    # === INLINE PATH (existing implementation) ===
    # All existing Stage A/B/C logic stays here (lines 1953-3407)
```

**Validation:** Syntax is valid (no unmatched braces/indents)

### Task 5: Wrap existing inline code in else branch

**File:** `dbex/nanobrag_refinement.py`

**Action:** Indent ALL lines from 1953 to 3407 by 4 spaces (one indentation level) to place them inside the `else:` block from Task 4.

**CRITICAL:** Do NOT modify any logic inside the else block. This is a PURE indentation change only.

**Before:**
```python
if stage_a_only_mode:
    ...
else:
sigma_floor_sq_cache: Dict[...] = {}  # line ~1953
...
return bragg_full, telemetry_dict  # line ~3407
```

**After:**
```python
if stage_a_only_mode:
    ...
else:
    sigma_floor_sq_cache: Dict[...] = {}  # line ~1953 (indented by 4 spaces)
    ...
    return bragg_full, telemetry_dict  # line ~3407 (indented by 4 spaces)
```

**Tool:** Use editor's indent-block feature or careful manual indent. Verify NO logic changes.

**Validation:** Compilation check passes (Task 6)

### Task 6: Compilation check

**Action:** Run compilation check:
```bash
python -c "from dbex import nanobrag_refinement; print('OK')"
```

**Expected output:** `OK` (exit code 0)

**If compilation fails:**
- Check for missing imports (torch already imported at top)
- Check for indentation errors in else block
- Check helper function signature matches call site
- Check for unmatched braces in if/else
- Document error → write to blockers.md

### Task 7: Regression guard test

**Action:** Run Stage A smoke test:
```bash
\
  DBEX_SMOKE_DETECTOR_SIZE=small \
  KMP_DUPLICATE_LIB_OK=TRUE \
  NANOBRAGG_DISABLE_COMPILE=1 \
  pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
    > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050432Z/pytest_stage_a_expansion.log 2>&1
```

**Expected outcome:** 1 passed

**Notes:**
- Test default config has enable_stage_c=False, enable_stage_b=False → engine path
- Telemetry structure should match inline path (key "A")
- bragg_full array should be numerically identical

**If test fails:**
- Capture full pytest log (already redirected above)
- Check telemetry key ("A" vs "stage_a")
- Check param_deltas unpacking in helper
- Document failure → write to blockers.md

### Task 8: Engine contract validation

**Action:** Run engine contract test:
```bash
cd /home/ollie/Documents/diffbragg_example && \
  pytest -vv tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage \
    > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050432Z/pytest_engine.log 2>&1
```

**Expected outcome:** 1 passed

**Validation:** Engine protocol test still passes (validates engine.run() interface)

### Task 9: Update implementation.md checklist

**File:** `plans/active/ARCH-REFINE-FLOW-001/implementation.md`
**Location:** Line ~115 (Phase B checklist, B2 item)

**Action:** Mark B2 as complete:
```markdown
- [✓] B2: **Update run_nanobrag_refinement for engine delegation** (Loop i=196) — COMPLETE (2025-11-23T050432Z):
  - Added stage detection logic (enable_stage_c=False AND enable_stage_b=False)
  - Extracted _build_final_bragg_from_stage_a_telemetry helper (~240 lines, dbex/nanobrag_refinement.py:~1888)
  - Implemented engine delegation path with RefinementEngine([StageA()])
  - Wrapped existing inline logic in else branch (Stage B/C combinations preserved)
  - Regression guard test_stage_a_expansion PASSED (engine delegation path active)
  - Engine contract test test_engine_executes_mock_stage PASSED
  - Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050432Z/
```

**Validation:** Checklist B2 marked [✓] with timestamp

### Task 10: Write implementation summary + commit

**Action:**

1. **Create implementation summary:**
   - File: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050432Z/phase_b2_implementation_summary.md`
   - Document:
     - Helper extraction (final Bragg reconstruction)
     - Engine delegation logic (if/else branching)
     - Test results (pytest logs)
     - Any issues encountered

2. **Write Turn Summary:**
   - File: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050432Z/summary.md`
   - Content:
     ```markdown
     ### Turn Summary
     Implemented engine delegation for Stage-A-only mode (enable_stage_c=False AND enable_stage_b=False).
     Extracted final Bragg reconstruction helper (~240 lines) and wrapped existing inline logic in else branch.
     Regression guard test_stage_a_expansion PASSED using engine delegation path; telemetry structure matches inline path.
     Next: Phase B3 full smoke validation (full detector + DB-AT selectors).
     Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050432Z/ (pytest logs, implementation summary)
     ```

3. **Commit and push:**
   ```bash
   git add -A
   git commit -m "ARCH-REFINE-FLOW-001 Phase B2: Engine delegation for Stage-A-only mode — tests: passed

   - Added stage detection logic (enable_stage_c=False AND enable_stage_b=False)
   - Extracted _build_final_bragg_from_stage_a_telemetry helper (~240 lines)
   - Implemented engine delegation path with RefinementEngine([StageA()])
   - Wrapped existing inline logic in else branch (Stage B/C combinations)
   - Regression guard test_stage_a_expansion PASSED (engine delegation path)
   - Phase B2 COMPLETE, ready for Phase B3 full smoke validation"
   git push
   ```

**Validation:** Commit created and pushed successfully

## How-To Map

### Compilation Check
```bash
python -c "from dbex import nanobrag_refinement; print('OK')"
```

### Regression Guard Test
```bash
cd /home/ollie/Documents/diffbragg_example
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
```

### Engine Contract Test
```bash
cd /home/ollie/Documents/diffbragg_example
pytest -vv tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage
```

## Pitfalls To Avoid

1. **DO NOT modify logic inside else block** — pure indentation change only
2. **DO extract exact copy of lines 2046-2285** — no logic changes in helper
3. **DO use lazy imports** — import engine/StageA inside `if stage_a_only_mode:`
4. **DO preserve telemetry key** — return {"A": telemetry_a} for backward compat
5. **DO NOT change param_deltas structure** — keep existing dict keys
6. **DO handle RefinementTelemetry vs dict** — telemetry_a is RefinementTelemetry instance
7. **DO preserve device/dtype** — all tensors use config.device/dtype
8. **DO check both test selectors** — regression guard AND engine contract
9. **DO document helper location** — place at ~line 1888 (after _run_stage_a_lbfgs)
10. **DO archive all logs** — save pytest outputs to artifacts directory

## If Blocked

**Compilation errors:**
- Write error to `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050432Z/blockers.md`
- Check imports, indentation, function signatures
- Capture full traceback

**Test failures:**
- Write failure to `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050432Z/blockers.md`
- Capture full pytest output
- Compare telemetry structures
- Check Bragg array equality

**Always:** Update docs/fix_plan.md Attempts History with blocker signature

## Findings Applied (Mandatory)

- **PHYSICS-LOSS-001**: StageA telemetry includes chi_squared fields (engine preserves)
- **PHYSICS-LOSS-002**: StageA telemetry includes variance_floor fields (engine preserves)
- **PHYSICS-LOSS-003**: StageA telemetry includes canonical metadata (engine preserves)
- **PERF-WARM-001**: StageA preserves warm-cache telemetry (engine consumes StageAContext)
- **GEOMETRY-003**: Baseline misset handled in StageA.run() (transparent to delegation)
- **GEOMETRY-004**: Incremental UB mode handled in StageA.run() (transparent to delegation)
- **GRADIENT-001**: Autograd preservation in helper2 (transparent to delegation)
- **CONVERGENCE-001**: Zero-delta bypass in helper2 (transparent to delegation)
- **POLICY-001**: Environment Freeze — no package installs during loop

## Pointers

- **Spec:** docs/spec-db-workflow.md:33-36 (Engine Contract)
- **Implementation Plan:** plans/active/ARCH-REFINE-FLOW-001/implementation.md:115-120 (Phase B2)
- **Fix Plan:** docs/fix_plan.md:181-206 (ARCH-REFINE-FLOW-001)
- **StageA:** dbex/refinement/stage_a.py:62-367 (run() method)
- **Engine:** dbex/refinement/engine.py:21-125 (engine.run())
- **Inline Code:** dbex/nanobrag_refinement.py:1950-3407 (lines to wrap in else)
- **Bragg Reconstruction:** dbex/nanobrag_refinement.py:2046-2285 (to extract into helper)
- **Testing Guide:** docs/TESTING_GUIDE.md §2 (pytest selectors)

## Next Up (optional)

**Do NOT proceed unless all Phase B2 tests pass.**

If you finish early:
- Run full detector smoke (preview Phase B3)
- Run DB-AT-010 collect-only (preview Phase B3)

Archive logs to artifacts directory but DO NOT mark Phase B3 tasks as done.
