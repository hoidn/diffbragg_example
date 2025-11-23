# ARCH-REFINE-FLOW-001 Phase A Implementation Summary

**Date:** 2025-11-23T024449Z
**Phase:** A (Stage Interface & Engine Skeleton)
**Status:** COMPLETE
**Loop ID:** 2025-11-23T024449Z

## 1. Overview

Phase A implements the foundational Protocol-based Refinement Engine architecture per docs/spec-db-workflow.md §7 (Refinement Protocol Architecture). This phase establishes the Stage interface, Engine skeleton, shared helpers, extended telemetry schema, and TDD nucleus test validating the engine contract.

**Key Deliverables:**
- RefinementStage protocol defining stage interface
- RefinementEngine executing ordered stage sequences
- Shared helper stubs for simulator/Bragg generation
- Extended RefinementTelemetry with stage_type/mode fields
- TDD nucleus test validating engine contract
- Test registry updates (TESTING_GUIDE.md, TEST_SUITE_INDEX.md)
- Compliance evidence documentation

## 2. RefinementStage Protocol

**File:** `dbex/refinement/stage.py:21-76`

**Interface Definition:**
```python
class RefinementStage(Protocol):
    @property
    def name(self) -> str:
        """Stage identifier (e.g., 'stage_a', 'stage_b', 'mock_stage')."""
        ...

    def configure(self, config: Any) -> None:
        """Optional configuration hook."""
        ...

    def run(
        self,
        inputs: Any,
        telemetry_sink: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Execute stage and return telemetry dict."""
        ...
```

**Contract:**
- Stages identify themselves via `name` property
- Stages accept optional configuration via `configure(config)`
- Stages execute via `run(inputs, telemetry_sink)` returning telemetry dict
- Telemetry dict MUST include all required RefinementTelemetry fields plus stage_type/mode

**Normative Alignment:**
- spec-db-workflow.md:33: Engine accepts ordered list of Stage objects
- spec-db-workflow.md:35-62: Stage A/B/C normative definitions (protocol is agnostic, allows custom stages)

**Circular Import Mitigation:**
- Module does NOT import heavy simulator modules (nanobrag_torch, dbex.nanobrag_bridge)
- Uses TYPE_CHECKING imports for type hints only
- Prevents cascade imports when stages instantiate detectors/crystals

## 3. RefinementEngine Skeleton

**File:** `dbex/refinement/engine.py`

**Execution Flow:**
1. `__init__(stages, config)`: Store ordered stage list and config
2. `run(inputs, telemetry_sink)`: Iterate stages in order
   - Call `stage.configure(config)` for each stage
   - Call `stage.run(inputs, telemetry_sink)` for each stage
   - Convert returned dict to RefinementTelemetry instance
   - Aggregate into `_telemetry` dict keyed by `stage.name`
3. `telemetry` property: Return aggregated telemetry dict

**Key Design Decisions:**
- Engine does NOT hardcode Stage A→B→C flow (accepts arbitrary sequences)
- Stages execute in order provided to `__init__` (deterministic)
- Telemetry aggregation by stage.name allows multi-stage refinement tracking
- Engine validates stages list is non-empty (ValueError if empty)

**Normative Alignment:**
- spec-db-workflow.md:33: "RefinementEngine SHALL accept an ordered list of Stage objects and MUST NOT hardcode the Stage A→B→C flow."

**Example Usage:**
```python
from dbex.refinement import RefinementEngine, RefinementStage
from dbex.nanobrag_refinement import RefinementConfig

# Define custom stages (or use StageA, StageB, StageC in Phase B-D)
stages = [StageA(...), StageB(...), StageC(...)]
config = RefinementConfig(...)
engine = RefinementEngine(stages=stages, config=config)

# Execute refinement
telemetry = engine.run(inputs)  # Returns Dict[str, RefinementTelemetry]
```

## 4. Shared Helpers

**File:** `dbex/refinement/helpers.py`

### 4.1 create_panel_simulator(...)

**Purpose:** Centralize simulator instantiation logic for a single panel (extracted from Stage A panel loop ~800-900).

**Signature:**
```python
def create_panel_simulator(
    detector_config: DetectorConfig,
    crystal_config: CrystalConfig,
    hkl_grid: Any,
    config: RefinementConfig,
    device: torch.device,
    dtype: torch.dtype
) -> nanobrag_torch.Simulator
```

**Implementation Status:** Minimal stub (Phase A)

**Full Implementation:** Phase B-D refactor will extract logic from dbex/nanobrag_refinement.py Stage A panel loop

**Normative Requirements:**
- MUST respect device/dtype parameters (no hardcoded .cuda() or float32)
- SHOULD enable tricubic interpolation when HKL grid has ±1 halo (REFINE-005)
- MUST use existing tensor factories from dbex.nanobrag_bridge (POLICY-001)

### 4.2 emit_bragg_frame(...)

**Purpose:** Centralize full-frame Bragg generation from stage parameters (extracted from Stage A/B/C closures).

**Signature:**
```python
def emit_bragg_frame(
    stage_params: Dict[str, torch.Tensor],
    inputs: RefinementInputs,
    config: RefinementConfig,
    simulators: List[nanobrag_torch.Simulator]
) -> torch.Tensor  # [panel, slow, fast]
```

**Implementation Status:** Stub with NotImplementedError (Phase A)

**Full Implementation:** Phase B-D refactor will extract Bragg stitching logic

**Normative Requirements:**
- Output MUST have shape [panel, slow, fast] per spec-db-core.md
- MUST respect device/dtype from simulators
- SHOULD NOT re-derive physics (use production Simulator.forward())

**Future Extensions (Phase B-D):**
- Stage B: apply per-reflection Fhkl modifiers before forward pass
- Stage C: update detector distances before forward pass

**Phase A Note:**
These helpers are PLAN-LOCAL for testing. Existing Stage A/B/C code will not use them until Phase B-D refactor.

## 5. Telemetry Schema Extensions (A4)

**File:** `dbex/refinement/stage.py:79-231`

**New Fields (Phase A4):**
- `stage_type: Optional[str]` — Stage identifier (e.g., "stage_a", "stage_b", "mock_stage")
- `mode: Optional[str]` — Stage mode variant (e.g., "shell_modifiers", "parity", "incremental_ub")

**Backward Compatibility:**
- All existing fields from `dbex.nanobrag_refinement.RefinementTelemetry` preserved
- `to_dict()` method includes all existing + new fields
- HDF5 writers and test assertions use `to_dict()` for serialization (no breaking changes)

**Normative Alignment:**
- spec-db-tracing.md §2: Telemetry contract for stages
- PHYSICS-LOSS-001: Chi-squared and masked-MSE dual metrics
- PHYSICS-LOSS-002: Variance floor telemetry
- PHYSICS-LOSS-003: Canonical Stage A metadata propagation

**Usage in TDD Nucleus Test:**
```python
# MockStage returns telemetry dict with stage_type/mode fields
telemetry_dict = {
    "stage_type": "mock_stage",
    "mode": None,
    "optimizer": "mock",
    "stage": "mock_stage",
    # ... all required fields
}

# Engine converts to RefinementTelemetry instance
telemetry = RefinementTelemetry(**telemetry_dict)
assert telemetry.stage_type == "mock_stage"
```

## 6. Test Registry (A5)

### 6.1 TESTING_GUIDE.md Update

**Location:** `docs/TESTING_GUIDE.md:136`

**Entry Added:**
```
| RefinementEngine TDD Nucleus | `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage` | Validates RefinementEngine executes mock stage and aggregates telemetry per `docs/spec-db-workflow.md:32-33` (Engine Contract: ordered stages, no hardcoded A→B→C). Tests engine executes dummy Stage once, returns Dict[str, RefinementTelemetry] with stage_type="mock_stage" field (ARCH-REFINE-FLOW-001 Phase A4 extension). | Active | Tests: `tests/dbex/test_refinement_engine.py` (1 test collected, 1 passed). Test PASSES validating engine contract: mock stage executed, telemetry dict aggregated, stage_type field present. Runtime: <1s. Skip guard: none (no external dependencies). Artifacts: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T024449Z/` (pytest_test_refinement_engine.log, pytest_collect_test_refinement_engine.log). Findings: ARCH-REFINE-FLOW-001 (Protocol-based Engine), spec-db-workflow.md:32-33. Environment: `KMP_DUPLICATE_LIB_OK=TRUE`, `NANOBRAGG_DISABLE_COMPILE=1` (optional for this test). |
```

### 6.2 TEST_SUITE_INDEX.md Update

**Location:** `docs/development/TEST_SUITE_INDEX.md:17`

**Entry Added:**
```
| ARCH-ENGINE-001: RefinementEngine TDD Nucleus | `tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage` | active | `docs/spec-db-workflow.md:32-33`, `plans/active/ARCH-REFINE-FLOW-001/implementation.md` | TDD nucleus test for Protocol-based Refinement Engine. Validates engine executes mock stage, aggregates telemetry Dict[str, RefinementTelemetry], and includes stage_type/mode fields (Phase A4 extension). 1 test collected, 1 passed. First added 2025-11-23. |
```

### 6.3 Collection Verification

**Command:**
```bash
pytest --collect-only tests/dbex/test_refinement_engine.py
```

**Result:** 1 test collected ✓

**Log:** `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T024449Z/pytest_collect_test_refinement_engine.log`

## 7. Compliance Evidence (A6)

**File:** `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T024449Z/phase_a_compliance_evidence.md`

**Verification Matrix:**
- ✓ Spec Alignment (spec-db-workflow.md:33, spec-db-tracing.md §2)
- ✓ Findings Cross-References (REFINE-005/007/008, SCALE-001/002, POLICY-001)
- ✓ Environment Freeze Compliance (no new dependencies, lazy imports)
- ✓ Test Evidence (TDD nucleus PASSED, regression guard PASSED)
- ✓ Dependency Analysis (circular imports mitigated)

**Risk Assessment:**
- Low Risk: Circular imports, backward compatibility, test coverage
- Medium Risk: Phase B-D refactor code path divergence (mitigated with smoke tests)
- No High Risks Identified

## 8. Next Steps (Phase B)

**Phase B Objective:** Extract Stage A implementation onto the engine using shared helpers

**Prerequisites (ALL MET):**
- [x] Phase A complete (all tasks A0-A7)
- [x] Regression guard clean (test_stage_a_expansion PASSED)
- [x] Test registry synchronized (TESTING_GUIDE.md, TEST_SUITE_INDEX.md)
- [x] Compliance evidence documented

**Phase B Tasks:**
- B0: Record baseline artifacts for Stage A smoke
- B1: Implement StageA class wrapping current LBFGS closure
- B2: Wire StageA into RefinementEngine (delegate run_nanobrag_refinement)
- B3: Rerun Stage A smoke (small + full detector) with telemetry validation
- B4: Run DB-AT selectors (DB-AT-010 Gradcheck, DB-AT-024 Mapping)
- B5: Update docs/tests to reference StageA class

**Estimated Effort:** 2-3 loops (implementation + validation)

**Critical Success Factors:**
- Preserve exact Stage A behavior (no numerical drift)
- Maintain warm-cache/perf-telemetry contract (PERF-WARM-SIM-001)
- Validate incremental UB parameterization compatibility (GEOMETRY-004)

## 9. Artifacts Index

**Reports Root:** `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T024449Z/`

**Files:**
- `pytest_test_refinement_engine.log` — TDD nucleus test execution log (1 test PASSED)
- `pytest_collect_test_refinement_engine.log` — Collection log (1 test collected)
- `pytest_stage_a_regression.log` — Regression guard (test_stage_a_expansion PASSED)
- `phase_a_compliance_evidence.md` — Spec alignment verification
- `phase_a_implementation_summary.md` — This file
- `summary.md` — Turn Summary block (required end-of-loop artifact)

**Code Files:**
- `dbex/refinement/__init__.py` — Package root exposing public API
- `dbex/refinement/stage.py` — RefinementStage protocol, RefinementTelemetry schema
- `dbex/refinement/engine.py` — RefinementEngine skeleton
- `dbex/refinement/helpers.py` — Shared helper stubs
- `tests/dbex/test_refinement_engine.py` — TDD nucleus test

**Documentation Files:**
- `docs/TESTING_GUIDE.md` — Test registry (ARCH-ENGINE-001 entry added)
- `docs/development/TEST_SUITE_INDEX.md` — Selector registry (ARCH-ENGINE-001 entry added)

## 10. Lessons Learned

### What Went Well
- TDD approach (test first) validated engine contract before implementation
- Lazy imports prevented circular dependency issues
- Backward-compatible telemetry schema allows smooth migration

### Challenges
- Initial test failure due to unexpected keyword args in RefinementTelemetry.__init__ (fixed by removing optional fields from MockStage return dict)
- Careful import ordering required to avoid heavy module loading

### Recommendations for Phase B
- Preserve StageA closure logic exactly (minimize diff for code review)
- Use shared helpers incrementally (don't refactor all Stage A code at once)
- Run full DB-AT suite + smoke tests at each commit to catch regressions early

---

**Phase A Status:** ✓ COMPLETE

**All Exit Criteria Met:**
1. ✓ RefinementEngine accepts ordered list of Stages (no hardcoded A→B→C)
2. ✓ RefinementStage protocol defines stage interface
3. ✓ Shared helpers extracted (stubs for create_panel_simulator, emit_bragg_frame)
4. ✓ RefinementTelemetry extended with stage_type/mode fields
5. ✓ TDD nucleus test PASSED (test_engine_executes_mock_stage)
6. ✓ Regression guard PASSED (test_stage_a_expansion)
7. ✓ Test registry synchronized (TESTING_GUIDE.md, TEST_SUITE_INDEX.md)
8. ✓ Compliance evidence documented

**Authored by:** Ralph
**Timestamp:** 2025-11-23T024449Z
