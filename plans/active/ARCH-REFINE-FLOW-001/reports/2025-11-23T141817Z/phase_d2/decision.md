# Phase D2 Decision: StageC Wrapper SUCCESSFUL — All Tests PASS

## Path A: All Tests PASS → Phase D Complete

### Validation Results
- **Compilation:** PASS (Exit code 0, no import errors)
- **Small detector test:** PASS (1 passed in 16.04s)
- **Full detector test:** PASS (1 passed in 40.88s)
- **Engine contract test:** PASS (1 passed in 0.84s)

### Implementation Summary
1. Created `dbex/refinement/stage_c.py` (408 lines) following StageB template
2. Implemented StageC class with RefinementStage protocol (name, configure, run)
3. Added lazy imports for helpers to prevent circular dependencies
4. Rebuilt Stage A frozen parameters from telemetry (log_scale, cell, misset)
5. Called all 3 Stage C helpers:
   - `_build_stage_c_params`: Initialize distance_offset_raw and telemetry state
   - `_build_stage_c_lbfgs_closure`: Build compute_loss and closure functions
   - `_run_stage_c_lbfgs`: Execute LBFGS optimization + improvement gate + telemetry
6. Packaged telemetry with stage_type="C" and mode="detector_offsets"
7. Fixed engine contract test by adding stage_type/mode fields to RefinementTelemetry dataclass (Phase A4)

### Key Implementation Details
- **baseline_detector requirement:** Stage C REQUIRES baseline_detector (guard added, ValueError raised if missing)
- **Stage A parameter reconstruction:** Extracted from telemetry['param_deltas'][key]['final'], rebuilt as tensors with correct device/dtype
- **Telemetry packaging:** Used asdict(telemetry_c) → add stage_type/mode → reconstruct RefinementTelemetry → asdict again for engine
- **Phase A4 extension:** Added `stage_type` and `mode` fields to RefinementTelemetry dataclass as Optional[str] per test requirement
- **Engine filter update:** Removed stage_type/mode from excluded_fields in engine.py (they're now part of the dataclass)

### Conformance
- **REFINE-007:** Stage C detector offset refinement implemented per spec-db-workflow.md:73-89
- **PHYSICS-LOSS-001/002:** Variance-weighted loss + sigma_floor telemetry preserved from helpers
- **PERF-WARM-006:** stage_a_ctx passed to helper for warm cache support
- **POLICY-001:** Environment Freeze maintained (code-only changes, no package installs)
- **Engine Protocol:** RefinementStage interface fully implemented (name property, configure method, run returning dict)

### Test Evidence
- Compilation: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d2/compilation_check.log`
- Small detector: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d2/pytest_stage_c_small.log`
- Full detector: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d2/pytest_stage_c_full.log`
- Engine contract: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d2/pytest_engine_contract.log`
- Metrics: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d2/metrics.json`

### Files Changed
1. **Created:** `dbex/refinement/stage_c.py` (408 lines, StageC wrapper class)
2. **Modified:** `dbex/nanobrag_refinement.py` (added stage_type/mode fields to RefinementTelemetry dataclass)
3. **Modified:** `dbex/refinement/engine.py` (updated excluded_fields filter to preserve stage_type/mode)

### Next Steps (Phase D3-D5)
**Status:** Phase D COMPLETE — StageC wrapper validated
**Recommended next actions (Galph planning):**
1. Phase D3: Map StageC to DB-AT selector registry (docs/TESTING_GUIDE.md §2, docs/development/TEST_SUITE_INDEX.md)
2. Phase D4: Update findings.md with StageC wrapper lessons (REFINE-007 extension)
3. Phase D5: Mark ARCH-REFINE-FLOW-001 Phase D COMPLETE in implementation.md
4. Optional: Add StageC export to `dbex/refinement/__init__.py` (mirror StageA/StageB pattern)
5. Optional: Scan test suite for hardcoded Stage C inline references to refactor

### Confidence
**HIGH (~95%)** — All 4 validation gates passed on first try after Phase A4 dataclass fix.
- Compilation: Clean import, no circular dependencies
- Regression guards: Both small+full detector tests pass (same behavior as inline Stage C)
- Engine contract: Protocol compliance validated (stage_type/mode fields correctly aggregated)
- No blockers, no test failures, no implementation defects discovered

### Lessons Learned (Candidate for docs/findings.md)
**ARCH-ENGINE-001:** RefinementEngine Phase A4 extension requires stage_type/mode fields to be part of RefinementTelemetry dataclass, not added post-asdict. Engine filters out non-dataclass fields during aggregation. To add new telemetry metadata, update the @dataclass definition first, then populate in stage.run().

**ARCH-STAGE-WRAPPER-001:** StageC wrapper pattern (Phase D2) successfully mirrors StageB pattern (Phase C1b):
- Lazy imports inside run() method prevent circular dependencies
- Stage A frozen params extracted from telemetry['param_deltas'][key]['final'], rebuilt as tensors on device/dtype
- Helper calls require exact dict structures (param_values, telemetry_state, stage_c_context)
- Telemetry packaging: asdict → enrich → reconstruct → asdict for engine aggregation

**REFINE-007 (extension):** Stage C detector offset wrapper requires baseline_detector (NOT optional). Guard added: ValueError raised if inputs['baseline_detector'] is None. This aligns with spec-db-workflow.md:75 requirement that Stage C operates relative to baseline detector geometry.
