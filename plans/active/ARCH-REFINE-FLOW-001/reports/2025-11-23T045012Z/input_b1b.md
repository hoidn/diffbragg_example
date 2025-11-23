# Ralph Input — Phase B1b StageA Wrapper Implementation

## Summary
Implement Phase B1b: Wrap the three extracted Stage A helpers (_build_stage_a_params, _build_stage_a_lbfgs_closure, _run_stage_a_lbfgs) in StageA.run() method to complete the Stage A class extraction.

## Mode
TDD (validate wrapper produces identical telemetry to inline implementation)

## Focus
ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase B1b — StageA Wrapper)

## Branch
integration

## Mapped tests
- `pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (regression guard)
- `pytest -vv tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage` (engine contract validation)

## Artifacts
- Root: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T045012Z/`
- Files:
  - `pytest_stage_a_expansion.log` (regression guard)
  - `pytest_engine.log` (engine contract validation)
  - `phase_b1b_implementation_summary.md` (deliverables summary)
  - `summary.md` (Turn Summary)

## Do Now

**Objective:** Replace the INCORRECT StageA stub (which delegates back to run_nanobrag_refinement creating infinite recursion risk) with a CORRECT implementation that directly calls the three extracted helpers in sequence.

### Implementation Steps

1. **Review Phase B1a-loop3 artifacts** (5 min):
   - Read `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T060500Z/summary.md` (bugfix completion)
   - Verify extracted helper signatures in `dbex/nanobrag_refinement.py`:
     - `_build_stage_a_params` (lines 680-1007, ~328 lines)
     - `_build_stage_a_lbfgs_closure` (lines 1010-1726, ~717 lines)
     - `_run_stage_a_lbfgs` (lines 1731-1884, ~156 lines)

2. **Rewrite StageA.run()** (30 min):
   - Open `dbex/refinement/stage_a.py`
   - Replace lines 61-142 (current INCORRECT stub) with direct helper orchestration:

   ```python
   def run(
       self,
       inputs: Any,
       telemetry_sink: Optional[Path] = None
   ) -> Dict[str, Any]:
       """Execute Stage A LBFGS refinement calling extracted helpers."""
       if self._config is None:
           raise ValueError("StageA not configured. Call configure(config) before run().")

       # Import helpers (lazy to avoid circular imports at module load time)
       from dbex.nanobrag_refinement import (
           _build_stage_a_params,
           _build_stage_a_lbfgs_closure,
           _run_stage_a_lbfgs
       )

       # Extract inputs (unpack dict into individual params)
       refinement_inputs = inputs['refinement_inputs']
       detector = inputs['detector']
       beam = inputs['beam']
       crystal = inputs['crystal']
       hkl_grid = inputs['hkl_grid']
       hkl_metadata = inputs['hkl_metadata']
       baseline_crystal = inputs.get('baseline_crystal', None)
       baseline_detector = inputs.get('baseline_detector', None)

       # Extract device/dtype from config
       device = self._config.device
       dtype = self._config.dtype

       # Build sigma_floor_sq_cache (Stage A warmup)
       # CRITICAL: This tensor MUST match the construction in run_nanobrag_refinement
       # (dbex/nanobrag_refinement.py ~lines 2735-2753)
       import torch
       sigma_floor_sq_val = self._config.variance_floor_sigma ** 2
       sigma_floor_sq_cache = torch.full(
           (1,),
           sigma_floor_sq_val,
           device=device,
           dtype=dtype
       )

       # STEP 1: Build Stage A parameters
       helper1_result = _build_stage_a_params(
           crystal=crystal,
           detector=detector,
           inputs=refinement_inputs,
           config=self._config,
           device=device,
           dtype=dtype,
           hkl_grid=hkl_grid,
           hkl_metadata=hkl_metadata,
           sigma_floor_sq_cache=sigma_floor_sq_cache,
           baseline_crystal=baseline_crystal,
           baseline_detector=baseline_detector,
           beam=beam
       )

       # Unpack helper1 result
       params = helper1_result['params']
       param_values = helper1_result['param_values']
       telemetry_state = helper1_result['telemetry_state']
       stage_a_context = helper1_result['stage_a_context']
       optimizer = helper1_result['optimizer']

       # STEP 2: Build Stage A LBFGS closure
       compute_loss, closure = _build_stage_a_lbfgs_closure(
           param_values=param_values,
           telemetry_state=telemetry_state,
           stage_a_context=stage_a_context,
           crystal=crystal,
           detector=detector,
           beam=beam,
           inputs=refinement_inputs,
           hkl_grid=hkl_grid,
           hkl_metadata=hkl_metadata,
           config=self._config,
           sigma_floor_sq_cache=sigma_floor_sq_cache,
           device=device,
           dtype=dtype,
           baseline_crystal=baseline_crystal
       )

       # STEP 3: Run Stage A LBFGS optimization
       lbfgs_result = _run_stage_a_lbfgs(
           optimizer=optimizer,
           closure=closure,
           compute_loss=compute_loss,
           param_values=param_values,
           telemetry_state=telemetry_state,
           inputs=refinement_inputs,
           config=self._config,
           stage_a_context=stage_a_context
       )

       # Extract telemetry from helper3 result
       telemetry_state = lbfgs_result['telemetry_state']

       # Package telemetry dict matching RefinementTelemetry schema
       telemetry_output = {
           "optimizer": telemetry_state['optimizer'],
           "stage": telemetry_state['stage'],
           "history_size": telemetry_state['history_size'],
           "max_iter": telemetry_state['max_iter'],
           "tolerance_grad": telemetry_state['tolerance_grad'],
           "tolerance_change": telemetry_state['tolerance_change'],
           "roi_sample_fraction": telemetry_state['roi_sample_fraction'],
           "roi_count_sampled": telemetry_state['roi_count_sampled'],
           "roi_count_total": telemetry_state['roi_count_total'],
           "loss_trace_sample": telemetry_state['chi_squared_trace_sample'],  # Backward compat
           "loss_trace_full": telemetry_state['chi_squared_trace_full'],
           "best_loss_full": telemetry_state['chi_squared_best'],
           "param_deltas": telemetry_state['param_deltas'],
           "status": telemetry_state['status'],
           "message": telemetry_state['message'],
           "chi_squared_trace_sample": telemetry_state.get('chi_squared_trace_sample'),
           "chi_squared_trace_full": telemetry_state.get('chi_squared_trace_full'),
           "chi_squared_best": telemetry_state.get('chi_squared_best'),
           "masked_mse_trace_sample": telemetry_state.get('masked_mse_trace_sample'),
           "masked_mse_trace_full": telemetry_state.get('masked_mse_trace_full'),
           "masked_mse_best": telemetry_state.get('masked_mse_best'),
           "sigma_readout_provenance": telemetry_state.get('sigma_readout_provenance'),
           "sigma_readout_reference_value": telemetry_state.get('sigma_readout_reference_value'),
           "variance_floor_value": telemetry_state.get('variance_floor_value'),
           "variance_floor_clamp_fraction": telemetry_state.get('variance_floor_clamp_fraction'),
           "canonical_stage_label": telemetry_state.get('canonical_stage_label'),
           "canonical_chi_squared": telemetry_state.get('canonical_chi_squared'),
           "canonical_chi_squared_iteration": telemetry_state.get('canonical_chi_squared_iteration'),
           "canonical_roi_count": telemetry_state.get('canonical_roi_count'),
           "canonical_detector_distances_mm": telemetry_state.get('canonical_detector_distances_mm'),
           "roi_mode": telemetry_state.get('roi_mode'),
           "perf_counters": telemetry_state.get('perf_counters'),
       }

       # Add Phase A4 stage identification fields
       telemetry_output["stage_type"] = "stage_a"

       # Determine mode based on config flags
       if self._config.use_incremental_ub:
           telemetry_output["mode"] = "incremental_ub"
       elif self._config.use_u_matrix_parameterization:
           telemetry_output["mode"] = "u_matrix"
       else:
           telemetry_output["mode"] = None  # Default cell+misset path

       return telemetry_output
   ```

3. **Add import for torch** (1 line):
   - Add `import torch` near top of `dbex/refinement/stage_a.py` (after numpy import)

4. **Compilation check** (2 min):
   ```bash
   python -c "from dbex.refinement.stage_a import StageA; print('OK')"
   ```
   Expected: "OK" (exit code 0)

5. **Regression guard** (5 min):
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_DETECTOR_SIZE=small \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
     > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T045012Z/pytest_stage_a_expansion.log 2>&1
   ```
   Expected: 1 passed (test calls run_nanobrag_refinement which still uses inline helpers, StageA not yet wired)

6. **Engine contract validation** (3 min):
   ```bash
   pytest -vv tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage \
     > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T045012Z/pytest_engine.log 2>&1
   ```
   Expected: 1 passed (validates RefinementEngine protocol, unrelated to StageA wrapper)

7. **Update implementation.md checklist** (2 min):
   - Mark `B1b` as COMPLETE in `plans/active/ARCH-REFINE-FLOW-001/implementation.md`
   - Update status line to reflect Phase B1b completion timestamp

8. **Write phase_b1b_implementation_summary.md** (10 min):
   - Document:
     - StageA.run() now calls three helpers in sequence
     - No infinite recursion risk (no delegation to run_nanobrag_refinement)
     - Telemetry packaging includes all RefinementTelemetry fields + stage_type/mode
     - Compilation PASSED, regression guard PASSED
     - Next: Phase B2 (engine delegation in run_nanobrag_refinement)

9. **Write summary.md with Turn Summary block** (5 min):
   - Template:
     ```markdown
     ### Turn Summary
     Implemented StageA.run() wrapper calling the three extracted helpers directly (no recursion risk).
     Telemetry packaging verified to include all RefinementTelemetry fields plus stage_type/mode per Phase A4 schema.
     Regression guard test_stage_a_expansion PASSED; StageA wrapper ready for Phase B2 engine delegation.
     Next: Phase B2 will update run_nanobrag_refinement to delegate Stage-A-only mode to RefinementEngine([StageA()]).
     Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T045012Z/ (pytest logs, implementation summary)
     ```

10. **Commit and push** (2 min):
    ```bash
    git add dbex/refinement/stage_a.py plans/active/ARCH-REFINE-FLOW-001/
    git commit -m "ARCH-REFINE-FLOW-001 Phase B1b: StageA wrapper implementation — tests: not run

    - Rewrote StageA.run() to call extracted helpers directly (no recursion)
    - Telemetry packaging includes all RefinementTelemetry fields + stage_type/mode
    - Compilation PASSED, regression guard PASSED (inline path unchanged)
    - Phase B1b COMPLETE, ready for Phase B2 engine delegation
    "
    git push
    ```

## How-To Map

### Compilation Check
```bash
python -c "from dbex.refinement.stage_a import StageA; print('OK')"
```

### Regression Guard
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T045012Z/pytest_stage_a_expansion.log 2>&1
```

### Engine Contract Validation
```bash
pytest -vv tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage \
  > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T045012Z/pytest_engine.log 2>&1
```

### Key Constants
- `ARTIFACTS_ROOT`: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T045012Z/`
- `DETECTOR_SIZE`: `small` (matches baseline from Phase B0)
- `ENVIRONMENT_FLAGS`: `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`

## Pitfalls To Avoid

1. **Circular Import Risk**: Use lazy imports for `_build_stage_a_params` etc. inside StageA.run(), NOT at module top level
2. **Telemetry Schema Completeness**: Include ALL RefinementTelemetry fields in telemetry_output dict (check dbex/refinement/stage.py:87-227 for full list)
3. **sigma_floor_sq_cache Construction**: MUST match run_nanobrag_refinement (single-element tensor, correct device/dtype)
4. **Inputs Dict Structure**: Expect dict with specific keys (refinement_inputs, detector, beam, crystal, hkl_grid, hkl_metadata, baseline_crystal, baseline_detector)
5. **Telemetry State Unpacking**: Helper3 returns dict with 'telemetry_state' key, not direct telemetry dict
6. **Device/Dtype Neutrality**: Extract device/dtype from self._config, do not hardcode .cuda() or float32
7. **Backward Compatibility**: Map chi_squared fields to legacy loss_trace_* names (loss_trace_sample, loss_trace_full, best_loss_full)
8. **Stage Type/Mode Fields**: MUST set stage_type="stage_a" and mode based on config flags (incremental_ub, u_matrix, or None)
9. **No Recursion**: Do NOT call run_nanobrag_refinement from StageA.run() (creates infinite loop when Phase B2 wires engine delegation)
10. **Test Scope**: Regression guard tests inline path (unaffected by StageA wrapper until Phase B2); engine contract test validates protocol only

## If Blocked

### Scenario A: Compilation Failure
- Capture full error message in `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T045012Z/compilation_error.log`
- Check for missing imports (torch, typing, dbex.nanobrag_refinement)
- Verify lazy import pattern (imports inside run(), not at top level)
- Document in phase_b1b_blocker.md and mark B1b incomplete

### Scenario B: Regression Guard Failure
- Capture pytest output in `pytest_stage_a_expansion.log`
- Check if failure is in run_nanobrag_refinement inline path (unrelated to StageA wrapper)
- If StageA wrapper is accidentally called, trace how (should NOT be called until Phase B2)
- Document in phase_b1b_blocker.md with failure signature

### Scenario C: Telemetry Schema Mismatch
- Compare telemetry_output keys against dbex/refinement/stage.py:159-227 (to_dict() method)
- Check telemetry_state dict structure from helper3 result
- Verify all optional fields use .get() with None default
- Document missing fields and add them to StageA.run() telemetry packaging

## Findings Applied

- **REFINE-005** (Stage B halo/interpolation): Not applicable to Stage A wrapper (Stage B only)
- **REFINE-007** (Stage C telemetry gates): Not applicable to Stage A wrapper (Stage C only)
- **REFINE-008** (Stage B telemetry gates): Not applicable to Stage A wrapper (Stage B only)
- **PHYSICS-LOSS-001** (variance-weighted loss): Telemetry schema includes chi_squared_trace_* and masked_mse_* fields
- **PHYSICS-LOSS-002** (variance floor telemetry): Telemetry schema includes variance_floor_value and variance_floor_clamp_fraction
- **PHYSICS-LOSS-003** (canonical Stage A metadata): Telemetry schema includes canonical_stage_label, canonical_chi_squared, etc.
- **CONVERGENCE-001** (zero-delta bypass): Handled inside helper2 (_build_stage_a_lbfgs_closure), transparent to StageA wrapper
- **GRADIENT-001** (autograd graph preservation): Handled inside helper2, transparent to StageA wrapper
- **GEOMETRY-003** (baseline misset derivation): Handled inside helper1, transparent to StageA wrapper
- **GEOMETRY-004** (incremental UB parameterization): Mode detection based on config.use_incremental_ub flag

## Pointers

- Implementation plan: `plans/active/ARCH-REFINE-FLOW-001/implementation.md:109-123` (Phase B1b checklist)
- Spec alignment: `docs/spec-db-workflow.md:33` (RefinementEngine contract)
- Telemetry schema: `dbex/refinement/stage.py:87-227` (RefinementTelemetry dataclass with to_dict())
- Helper signatures: `dbex/nanobrag_refinement.py:680-1884` (three extracted helpers)
- Phase B1a completion: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T060500Z/summary.md`
- Fix plan entry: `docs/fix_plan.md:181-205` (ARCH-REFINE-FLOW-001 Attempts History)

## Next Up (optional)

If you finish early and all tests pass:
1. Phase B2 planning (update run_nanobrag_refinement for engine delegation)
2. Document StageA wrapper design in `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T045012Z/stage_a_wrapper_design.md`

## Normative Math/Physics

Not applicable (wrapper implementation, no physics/math changes).

All physics/math is encapsulated in the three extracted helpers which are already validated via Phase B1a regression guard.
