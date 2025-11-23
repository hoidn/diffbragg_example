# Phase D2: StageC Class Wrapper Implementation

## Summary
Implement StageC class wrapper (dbex/refinement/stage_c.py) calling all 3 extracted Stage C helpers directly, mirroring proven StageB pattern. Validate via compilation check, regression guards (small+full detector), and engine contract test.

## Mode
none

## Focus
ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase D2: StageC wrapper class)

## Branch
integration

## Mapped Tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` (small detector, regression guard primary)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` (full detector, regression guard secondary)
- `tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage` (engine contract validation)

## Artifacts
plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d2/

## Do Now

**Objective**: Create StageC class wrapper calling the 3 extracted Stage C helpers (_build_stage_c_params, _build_stage_c_lbfgs_closure, _run_stage_c_lbfgs) and validate via regression guards + engine contract test.

**Context**: Phase D1c (loop i=229, commit 7a92a87) successfully extracted and wired all 3 Stage C helpers with **net reduction 124 lines**. Both regression tests PASSED (small + full detector). Phase D2 wraps these helpers in a StageC class following the proven StageB pattern (Phase C1b, dbex/refinement/stage_b.py).

### Implementation Steps (10 total)

#### Step 1: Review Phase D1c Completion
- Read `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d1c/decision.md` (Path A: both tests PASS)
- Review commit 7a92a87 diff to understand helper signatures:
  - `_build_stage_c_params(config, device, dtype, n_panels, baseline_detector, detector, sampled_panel_ids, panel_slices, stage_a_ctx, sigma_floor_sq_cache, params)` → Dict[str, Any] (30 keys)
  - `_build_stage_c_lbfgs_closure(param_values, telemetry_state, stage_c_context, ...)` → Tuple[Callable, Callable]
  - `_run_stage_c_lbfgs(config, device, dtype, param_values, closure_stage_c, compute_loss_stage_c, ...)` → Dict[str, Any]

#### Step 2: Create StageC Wrapper File
- Create `dbex/refinement/stage_c.py` following StageB template (dbex/refinement/stage_b.py:1-438)
- File header docstring: "Stage C implementation for Protocol-based Refinement Engine. Wraps existing LBFGS closure logic from run_nanobrag_refinement into a RefinementStage class per docs/spec-db-workflow.md §7 (Refinement Protocol Architecture) and ARCH-REFINE-FLOW-001 Phase D2. Stage C optimizes: detector offset parameters (distance_offset_raw). Freezes Stage A parameters (log_scale, cell, misset) from stage_a_telemetry input."
- Imports:
  ```python
  from dataclasses import asdict
  from pathlib import Path
  from typing import Any, Dict, Optional
  import numpy as np
  import torch
  ```

#### Step 3: Implement StageC Class Skeleton
- Class definition: `class StageC:`
- Docstring: "Stage C: Detector offset refinement (LBFGS). Implements RefinementStage protocol per spec-db-workflow.md:33. Wraps existing inline LBFGS closure logic from run_nanobrag_refinement. Attributes: _name: Stage identifier ('stage_c'), _config: Optional RefinementConfig (set via configure())"
- `__init__(self)`: Initialize `self._name = "stage_c"`, `self._config = None`
- `@property name(self) -> str`: Return `self._name`
- `def configure(self, config: Any) -> None`: Set `self._config = config` with docstring

#### Step 4: Implement StageC.run() Method Signature
- Method signature:
  ```python
  def run(
      self,
      inputs: Any,
      telemetry_sink: Optional[Path] = None
  ) -> Dict[str, Any]:
  ```
- Docstring (mirror StageB pattern):
  - Execute Stage C LBFGS refinement calling extracted helpers directly
  - Args: inputs dict with keys (refinement_inputs, detector, beam, crystal, hkl_grid, baseline_detector, stage_a_telemetry, stage_a_ctx, stage_b_telemetry [optional])
  - Returns: Telemetry dict with all RefinementTelemetry fields + stage_type="C" + mode="detector_offsets"
  - Raises: RuntimeError (simulator fails, gradients NaN/Inf), ValueError (config not set)
- Config guard: `if self._config is None: raise ValueError("StageC not configured...")`

#### Step 5: Import Helpers + Unpack Inputs
- Lazy imports inside run() method (prevent circular imports):
  ```python
  from dbex.nanobrag_refinement import (
      _build_stage_c_params,
      _build_stage_c_lbfgs_closure,
      _run_stage_c_lbfgs,
      RefinementTelemetry,
  )
  from dbex.nanobrag_bridge import (
      create_detector_config,
      create_crystal_config,
      compute_baseline_misset_deg,
  )
  from nanobrag_torch.models import Detector, Crystal
  from nanobrag_torch.simulator import Simulator
  ```
- Extract inputs (mirror StageB lines 105-114):
  ```python
  refinement_inputs = inputs['refinement_inputs']
  detector = inputs['detector']
  beam = inputs['beam']
  crystal = inputs['crystal']
  hkl_grid = inputs['hkl_grid']
  baseline_detector = inputs['baseline_detector']  # REQUIRED for Stage C
  stage_a_telemetry = inputs['stage_a_telemetry']
  stage_a_ctx = inputs.get('stage_a_ctx', None)
  stage_b_telemetry = inputs.get('stage_b_telemetry', None)  # Optional (Stage A→C skip Stage B)
  ```
- Extract device/dtype: `device = torch.device(self._config.device); dtype = self._config.dtype`

#### Step 6: Rebuild Stage A Final Parameters from Telemetry
- Mirror StageB pattern (lines 144-192):
  - Extract log_scale, log_cell_a/b/c_delta, angle_alpha/beta/gamma_raw, misset_xyz_deg from `stage_a_telemetry['param_deltas']['<key>']['final']`
  - Rebuild tensors on device: `log_scale = torch.tensor(log_scale_final, device=device, dtype=dtype)`
  - Apply cell deltas to baseline_crystal params: `cell_a_tensor = cell_params[0] * torch.exp(log_cell_a_delta)`
  - Apply angle tanh transform: `cell_alpha_tensor = cell_params[3] + torch.tanh(angle_alpha_raw) * max_angle_delta`
  - Compute baseline_misset_deg_tensor via `compute_baseline_misset_deg(crystal, baseline_crystal, device, dtype)` if baseline_crystal provided
- Build sigma_floor_sq_cache empty dict, canonical_baseline dict from stage_a_telemetry (mirror StageB lines 194-204)
- Determine use_stage_a_roi_mode from telemetry: `use_stage_a_roi_mode = (stage_a_telemetry['roi_mode'] == "roi")`
- Extract n_panels, panel_shape, sampled_panel_ids (mirror StageB lines 137-142)

#### Step 7: Call All 3 Stage C Helpers
- **STEP 1**: Call `_build_stage_c_params` (mirror StageB lines 214-231):
  ```python
  param_values = _build_stage_c_params(
      config=self._config,
      device=device,
      dtype=dtype,
      n_panels=n_panels,
      baseline_detector=baseline_detector,
      detector=detector,
      sampled_panel_ids=sampled_panel_ids,
      panel_slices=refinement_inputs.panel_slices,
      stage_a_ctx=stage_a_ctx,
      sigma_floor_sq_cache=sigma_floor_sq_cache,
      params=stage_a_params,  # Extract from step 6: frozen Stage A params list
  )
  ```
- **Add frozen Stage A tensors** to param_values dict (mirror StageB lines 234-242):
  ```python
  param_values['log_scale'] = log_scale
  param_values['cell_a_tensor'] = cell_a_tensor
  # ... (all 7 cell/angle tensors + misset_xyz_deg)
  param_values['best_loss_full'] = stage_a_telemetry['best_loss_full']
  ```
- **STEP 2**: Build telemetry_state dict and stage_c_context dict (check helper2 signature in dbex/nanobrag_refinement.py ~line 2894 for exact params)
- **STEP 3**: Call `_build_stage_c_lbfgs_closure` to get closure tuple:
  ```python
  (compute_loss_stage_c, closure_stage_c) = _build_stage_c_lbfgs_closure(
      param_values=param_values,
      telemetry_state=telemetry_state,
      stage_c_context=stage_c_context,
      # ... (add remaining params per helper signature)
  )
  ```
- **STEP 4**: Call `_run_stage_c_lbfgs` for optimization + telemetry:
  ```python
  result_c = _run_stage_c_lbfgs(
      config=self._config,
      device=device,
      dtype=dtype,
      param_values=param_values,
      closure_stage_c=closure_stage_c,
      compute_loss_stage_c=compute_loss_stage_c,
      # ... (add remaining params per helper signature)
  )
  ```
- **Extract helper results** (mirror StageB lines 250-355):
  - status_c, message_c, loss_trace_sample_c, ..., variance_floor_clamped_pixels_c, etc.
  - Build param_deltas_c dict with initial/final/delta structure for distance_offset_raw (per-panel)

#### Step 8: Package Telemetry
- Build RefinementTelemetry object (mirror StageB lines 373-411):
  - All standard fields: optimizer="LBFGS", stage="C", history_size, max_iter, tolerances, roi_sample_fraction, loss/chi²/mse traces, param_deltas_c, perf_counters, canonical_* fields
  - PHYSICS-LOSS-001: Dual loss metrics (chi_squared_trace_*, masked_mse_trace_*)
  - PHYSICS-LOSS-002: Variance floor (variance_floor_value, variance_floor_clamp_fraction)
  - REFINE-007: Detector offset deltas in param_deltas_c (distance_offset_raw: {initial, final, delta} per panel)
- Convert to dict: `telemetry_output = asdict(telemetry_c)`
- Add Phase A4 stage identification: `telemetry_output["stage_type"] = "C"; telemetry_output["mode"] = "detector_offsets"`
- Return telemetry_output dict

#### Step 9: Validation Protocol (3 tests)
- **Compilation Check**:
  ```bash
  python -c "import dbex.refinement.stage_c; from dbex.refinement.stage_c import StageC; print('Compilation: PASS')"
  ```
  - Expected: Exit code 0, no import errors
  - Save output to `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d2/compilation_check.log`

- **Regression Guard (Small Detector)**:
  ```bash
  AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
  DBEX_SMOKE_DETECTOR_SIZE=small \
  DBEX_SMOKE_SIGMA_SOURCE=cli_override \
  KMP_DUPLICATE_LIB_OK=TRUE \
  NANOBRAGG_DISABLE_COMPILE=1 \
  pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip
  ```
  - Expected: EXIT CODE 0 (1 passed)
  - Save output to `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d2/pytest_stage_c_small.log`

- **Regression Guard (Full Detector)**:
  ```bash
  AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
  DBEX_SMOKE_DETECTOR_SIZE=full \
  DBEX_SMOKE_SIGMA_SOURCE=cli_override \
  KMP_DUPLICATE_LIB_OK=TRUE \
  NANOBRAGG_DISABLE_COMPILE=1 \
  pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip
  ```
  - Expected: EXIT CODE 0 (1 passed)
  - Save output to `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d2/pytest_stage_c_full.log`

- **Engine Contract Test**:
  ```bash
  pytest -vv tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage
  ```
  - Expected: EXIT CODE 0 (validates RefinementStage protocol compliance)
  - Save output to `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d2/pytest_engine_contract.log`

#### Step 10: Decision Synthesis + Commit
- Extract metrics via T0 micro probe:
  ```bash
  python -c "
  import json
  metrics = {
      'compilation_status': 'PASS',  # or 'FAIL'
      'stage_c_small_status': 'PASS',  # or 'FAIL'
      'stage_c_full_status': 'PASS',  # or 'FAIL'
      'engine_contract_status': 'PASS',  # or 'FAIL'
      'decision_path': 'A'  # A/B/C/D per decision tree below
  }
  print(json.dumps(metrics, indent=2))
  " > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d2/metrics.json
  ```
- Write decision.md with 4-path synthesis (see Decision Tree section below)
- Update `plans/active/ARCH-REFINE-FLOW-001/implementation.md` to mark D2 checklist item complete
- Write summary.md with Turn Summary block (3-5 sentences: what shipped, main challenge, next step)
- Commit:
  ```bash
  git add -A && git commit -m "ARCH-REFINE-FLOW-001 Phase D2: Implement StageC wrapper class — tests: 3 passed" && git push
  ```

## How-To Map

### StageC Wrapper Template Reference
- **Pattern source**: `dbex/refinement/stage_b.py` (Phase C1b, 438 lines)
- **Key differences from StageB**:
  1. Stage C optimizes `distance_offset_raw` (n_panels trainable offsets) instead of `shell_modifier_raw` (n_shells)
  2. Stage C requires baseline_detector (NOT optional like StageB)
  3. Stage C param_deltas structure: `distance_offset_raw` dict with keys per panel_id (e.g., `0: {initial, final, delta}`)
  4. Stage C telemetry includes detector offset reduction stats per REFINE-007 (≥80% reduction OR ≤±0.05mm final)

### Helper Signature Reference
- Check exact signatures in `dbex/nanobrag_refinement.py`:
  - `_build_stage_c_params`: Line ~2737
  - `_build_stage_c_lbfgs_closure`: Line ~2894
  - `_run_stage_c_lbfgs`: Line ~3194

### Telemetry Packaging Checklist
- [ ] optimizer, stage, history_size, max_iter, tolerances (from config)
- [ ] roi_sample_fraction, roi_count_sampled, roi_count_total (from param_values)
- [ ] loss_trace_sample, loss_trace_full, best_loss_full (from result_c)
- [ ] param_deltas_c: distance_offset_raw with initial/final/delta per panel
- [ ] status, message (from result_c)
- [ ] perf_counters: cache_mode, roi_mode, closure_evals, validation_runs, forward_time_ms
- [ ] chi_squared_trace_sample/full/best (PHYSICS-LOSS-001)
- [ ] masked_mse_trace_sample/full/best (PHYSICS-LOSS-001)
- [ ] sigma_readout_provenance, sigma_readout_reference_value (from config)
- [ ] variance_floor_value, variance_floor_clamp_fraction (PHYSICS-LOSS-002)
- [ ] canonical_stage_label, canonical_chi_squared, canonical_chi_squared_iteration, canonical_roi_count, canonical_detector_distances_mm (from canonical_baseline)
- [ ] roi_mode (from perf_counters)
- [ ] stage_type="C", mode="detector_offsets" (Phase A4 engine contract)

### Environment Flags (All Tests)
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md  # Test registry reference
DBEX_SMOKE_DETECTOR_SIZE=small|full              # Detector size selector
DBEX_SMOKE_SIGMA_SOURCE=cli_override             # Sigma override mode
KMP_DUPLICATE_LIB_OK=TRUE                        # Intel MKL threading workaround
NANOBRAGG_DISABLE_COMPILE=1                      # Disable torch.compile for smoke tests
```

## Pitfalls To Avoid

1. **Circular Imports**: Use lazy imports (import inside run() method) for nanobrag_refinement, nanobrag_bridge, nanobrag_torch modules to prevent circular dependency at module load time
2. **Dict Key Mismatches**: Verify helper calls use exact param names from helper signatures (e.g., `param_values` not `params`, `telemetry_state` not `telemetry_dict`)
3. **Frozen Stage A Parameters**: Extract from `stage_a_telemetry['param_deltas']['<key>']['final']` (NOT raw tensors), rebuild as tensors on device before passing to helpers
4. **baseline_detector Requirement**: Stage C REQUIRES baseline_detector (NOT optional), raise ValueError if missing
5. **Telemetry Schema Alignment**: Use asdict(RefinementTelemetry(...)) to ensure all fields present, add stage_type/mode AFTER asdict conversion
6. **Device/Dtype Consistency**: Rebuild all Stage A tensors with correct device/dtype from config (e.g., `torch.tensor(log_scale_final, device=device, dtype=dtype)`)
7. **Lazy Import Scoping**: DO NOT import helpers at module level, only inside run() method
8. **param_deltas_c Structure**: distance_offset_raw is DICT with panel IDs as keys (e.g., `{0: {initial, final, delta}, 1: {...}, ...}`), NOT single dict
9. **Regression Test Environment**: All 3 environment flags MUST be set (AUTHORITATIVE_CMDS_DOC, DBEX_SMOKE_DETECTOR_SIZE, DBEX_SMOKE_SIGMA_SOURCE, KMP_DUPLICATE_LIB_OK, NANOBRAGG_DISABLE_COMPILE)
10. **Engine Contract**: StageC MUST implement RefinementStage protocol (name property, configure method, run method returning dict), test via test_engine_executes_mock_stage

## If Blocked

**Compilation Fails**:
1. Check import errors (circular imports? missing nanobrag_torch?)
2. Verify lazy import placement (inside run() method only)
3. Check helper function names match dbex/nanobrag_refinement.py exactly
4. Capture full traceback in blocker.md

**Regression Guard Fails (Small or Full Detector)**:
1. Compare helper calls in StageC.run() vs inline wiring in dbex/nanobrag_refinement.py (~lines 3824-4328 post-D1c)
2. Check for dict key mismatches (target_t vs target, loss_mask_t vs loss_mask, etc. — same bugs as D1c wiring)
3. Verify all frozen Stage A parameters are passed to helpers correctly
4. Run test with `-s` flag to capture print statements: `pytest -vv -s <test>`
5. Capture full pytest log + telemetry JSON in blocker.md

**Engine Contract Fails**:
1. Verify class implements all 3 protocol methods (name property, configure(), run())
2. Check run() returns dict (not None, not RefinementTelemetry object)
3. Verify stage_type and mode fields present in return dict
4. Capture contract test traceback in blocker.md

**Decision Escalation**:
- If >1 blocker after 2 fix attempts, write comprehensive blocker.md with:
  1. All 3 test logs (compilation, small detector, full detector, engine contract)
  2. Full error signatures + tracebacks
  3. Root cause hypothesis (imports? dict keys? telemetry schema?)
  4. Attempted fixes and outcomes
- Mark Phase D2 BLOCKED in galph_memory.md
- Await Galph review next loop

## Findings Applied

**Mandatory Knowledge Base Integration:**

- **REFINE-007** (docs/findings.md:58): Stage C gate = "stable detector offset" (≥80% offset reduction OR ≤±0.05mm final, ≤0.05% χ² regression). StageC.run() MUST preserve improvement gate logic + param_deltas_c telemetry for offset tracking. Include distance_offset_raw delta per panel in param_deltas_c output dict.

- **PHYSICS-LOSS-001** (docs/findings.md:20): Variance-weighted loss dual metrics. Telemetry MUST include chi_squared_trace_sample/full/best AND masked_mse_trace_sample/full/best.

- **PHYSICS-LOSS-002** (docs/findings.md:21): Sigma floor guard. Telemetry MUST include variance_floor_value and variance_floor_clamp_fraction computed from variance_floor_clamped_pixels_c / variance_floor_masked_pixels_c.

- **PERF-WARM-006** (docs/findings.md:37): Stage C warm cache reuses Stage A detector configs. Pass stage_a_ctx to _build_stage_c_params helper to enable warm cache path.

- **POLICY-001** (docs/findings.md:66): Environment Freeze. Do NOT modify any dependencies, only create new wrapper file dbex/refinement/stage_c.py.

- **RUNTIME-001** (docs/findings.md:29): Disable torch.compile for smoke tests. Set NANOBRAGG_DISABLE_COMPILE=1 in all pytest commands.

- **CONFORMANCE-001** (docs/findings.md:28): Environment flags for canonical tests. Use AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md, DBEX_SMOKE_DETECTOR_SIZE, DBEX_SMOKE_SIGMA_SOURCE=cli_override, KMP_DUPLICATE_LIB_OK=TRUE.

**No other relevant findings in the knowledge base for Stage C wrapper implementation.**

## Pointers

**Spec/Arch Documents:**
- docs/spec-db-workflow.md:33 — RefinementStage protocol definition (name, configure, run)
- docs/spec-db-workflow.md:73-89 — Stage C detector offset refinement specification
- docs/spec-db-runtime.md:34-39 — Device/dtype neutrality requirements
- docs/architecture/pytorch_design.md — RefinementEngine protocol architecture
- docs/pytorch_runtime_checklist.md — Telemetry schema + perf counters contract

**Code References:**
- dbex/refinement/stage_b.py:1-438 — StageB wrapper template (Phase C1b)
- dbex/refinement/stage.py:21-76 — RefinementStage protocol interface
- dbex/refinement/engine.py — RefinementEngine aggregation logic
- dbex/nanobrag_refinement.py:2737 — _build_stage_c_params signature
- dbex/nanobrag_refinement.py:2894 — _build_stage_c_lbfgs_closure signature
- dbex/nanobrag_refinement.py:3194 — _run_stage_c_lbfgs signature
- dbex/nanobrag_refinement.py:3824-4328 — Inline Stage C wiring post-D1c (helper calls reference)

**Test References:**
- tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip — Regression guard
- tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage — Engine contract validation
- docs/TESTING_GUIDE.md:2 — Test selector registry + environment flags

**Fix Plan:**
- docs/fix_plan.md:184-213 — ARCH-REFINE-FLOW-001 Attempts History (Phase A-D1c complete)
- plans/active/ARCH-REFINE-FLOW-001/implementation.md:220-240 — Phase D checklist (D1c ✓, D2 current)

**Artifacts:**
- plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d1c/ — D1c completion evidence (decision.md, metrics.json, pytest logs)
- plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d2/ — D2 artifacts destination (THIS LOOP)

## Decision Tree (4 Paths)

**Path A: All Tests PASS** (compilation + small + full + engine contract)
- **Verdict**: StageC wrapper SUCCESSFUL, protocol compliance validated
- **Confidence**: HIGH (~95%)
- **Next Loop**: Phase D3-D5 validation (DB-AT selectors, registry sync, findings update, mark Phase D COMPLETE)
- **Galph Action**: Plan D3-D5 comprehensive validation + documentation sync

**Path B: Compilation FAIL** (import error, syntax error, helper not found)
- **Verdict**: Circular import or helper signature mismatch
- **Confidence**: MEDIUM (~60%)
- **Root Cause Hypotheses**: (1) Missing lazy import for helpers, (2) Incorrect helper function names, (3) Circular import from nanobrag_refinement at module level
- **Fix Strategy**: Debug import traceback, verify lazy import placement, check helper names against dbex/nanobrag_refinement.py
- **Next Loop**: If fixed → rerun Step 9 validation. If blocked after 2 attempts → escalate to Galph with blocker.md

**Path C: Regression Guard FAIL** (small or full detector test fails, compilation PASS)
- **Verdict**: StageC.run() helper calls mismatch inline wiring
- **Confidence**: MEDIUM-HIGH (~70%)
- **Root Cause Hypotheses**: (1) Dict key mismatch (target_t vs target, etc. — same as D1c), (2) Frozen Stage A parameters incorrectly reconstructed, (3) Missing param_values dict fields
- **Fix Strategy**: Compare StageC.run() helper calls vs dbex/nanobrag_refinement.py inline wiring (lines 3824-4328), add missing dict keys, verify frozen params match telemetry extraction
- **Next Loop**: If fixed → rerun Step 9 validation. If blocked after 2 attempts → escalate to Galph with blocker.md + test logs

**Path D: Engine Contract FAIL** (test_engine_executes_mock_stage fails, regression guards PASS)
- **Verdict**: RefinementStage protocol violation (missing method, wrong return type)
- **Confidence**: LOW (~20% — rare, protocol is well-defined)
- **Root Cause Hypotheses**: (1) run() returns RefinementTelemetry object instead of dict, (2) Missing name property or configure method, (3) stage_type/mode fields missing from return dict
- **Fix Strategy**: Verify all 3 protocol methods implemented, check run() returns dict (use asdict conversion), ensure stage_type="C" and mode="detector_offsets" present
- **Next Loop**: If fixed → rerun Step 9 validation. If blocked → escalate to Galph (protocol issue unlikely, may indicate spec drift)

## Next Up (Optional, If Step 9 Finishes Early)

If all validation tests PASS and time permits:
1. Review dbex/refinement/__init__.py to add StageC export (mirroring StageA/StageB)
2. Scan tests/dbex/test_torch_refine_smoke.py for any hardcoded Stage C inline references that should use StageC class (defer to Phase D3 if time constrained)
3. Verify implementation.md Phase D2 checklist matches actual deliverables

**Do NOT proceed to Phase D3-D5 tasks** — those require Galph planning for DB-AT selector mapping + registry sync strategy.
