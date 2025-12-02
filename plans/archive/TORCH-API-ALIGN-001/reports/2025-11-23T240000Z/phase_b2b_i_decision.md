# Phase B2b(i) refine_one CLI Wiring Decision

## Results
- DB-AT-024 Regression Guard: **PASS** (31.85s, mapping parity unchanged)
- Stage A Expansion Smoke Test: **PASS** (12.37s, refine_one CLI unaffected)

## Decision Path: A (All Tests PASS)

### Verdict
Phase B2b(i) **COMPLETE**. Factory wiring validated for refine_one CLI forward simulation panel loop.

### Code Changes
- **File:** `dbex/refine_one.py` lines 438-461 (panel loop in run_nanobrag_backend)
- **Reduction:** Panel loop reduced from 73 lines to ~50 lines (net -23 lines)
  - Removed: 41 lines (manual Detector/Crystal instantiation, HKL attachment, beam_config branching for Simulator construction)
  - Added: 18 lines (unified factory call with consolidated parameters)
- **Config Creation:** Preserved lines 407-436 (detector_config, beam_config, crystal_config creation) for downstream Stage A refinement at line 510 (`run_nanobrag_refinement` requires `crystal_config`)

### Factory Integration Benefits
1. **Centralizes Model Instantiation:** Detector and Crystal models now created by factory, eliminating duplication
2. **Eliminates beam_config Branching:** Factory accepts optional beam_config parameter, removing 14-line if/else block
3. **Standardizes sqrt_scale Computation:** Factory returns `sqrt_scale_value`, caller applies post-run scaling consistently
4. **Mask Normalization:** Factory handles mask validation and device/dtype conversion
5. **HKL Attachment:** Factory owns HKL tensor attachment to crystal model

### Validation Evidence
- **DB-AT-024 Mapping Parity:** Zero-iteration forward model unchanged (median correlation ≥0.2, localization ≥90%)
- **Stage A Smoke Test:** refine_one CLI + Stage A LBFGS refinement completes successfully, telemetry structure correct
- **Compilation:** Import check PASSED, no circular dependency detected

### Next Actions
Phase B2b(ii) wiring: Wire `nanobrag_refinement` Stage B/C panel loops to factory (~60 lines changes, validate Stage B/C smoke tests)

### Confidence
**HIGH** (~95%) factory wiring correct:
- DB-AT-024 PASSED: mapping parity unchanged, zero regression
- Stage A smoke PASSED: refine_one CLI unaffected, refinement convergence stable
- No behavior change observed: config creation preserved, sqrt_scale application consistent

## Artifacts
- `phase_b2b_i_decision.md` (this file)
- `pytest_db_at_024.log` (DB-AT-024 regression guard: 1 passed, 31.85s)
- `pytest_stage_a_expansion.log` (Stage A smoke test: 1 passed, 12.37s)
