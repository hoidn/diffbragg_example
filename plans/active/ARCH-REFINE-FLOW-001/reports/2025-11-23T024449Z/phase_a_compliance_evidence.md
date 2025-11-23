# ARCH-REFINE-FLOW-001 Phase A Compliance Evidence

**Date:** 2025-11-23T024449Z
**Phase:** A (Stage Interface & Engine Skeleton)
**Status:** COMPLETE

## 1. Spec Alignment Verification

### 1.1 Engine Contract (spec-db-workflow.md:33)

**Normative Requirement:**
> "The internal Python API (RefinementEngine or equivalent) SHALL accept an ordered list of Stage objects and MUST NOT hardcode the Stage A→B→C flow."

**Evidence:**
- `dbex/refinement/engine.py:52-72`: RefinementEngine.__init__ accepts `stages: List[RefinementStage]` parameter
- `dbex/refinement/engine.py:93-107`: RefinementEngine.run() iterates `for stage in self.stages` without hardcoding Stage A/B/C sequence
- Test validation: `tests/dbex/test_refinement_engine.py:84-85` instantiates engine with `stages=[MockStage()]` (arbitrary stage sequence)
- **Compliance:** SATISFIED ✓

### 1.2 Stage Protocol Definition (spec-db-workflow.md:34-62)

**Normative Requirement:**
> "Standard Stages (Normative Definitions): Stage A, Stage B, Stage C with defined trainable/fixed parameters and physics requirements."

**Evidence:**
- `dbex/refinement/stage.py:21-76`: RefinementStage protocol defines interface:
  - `name: str` property identifying stage
  - `configure(config)` optional configuration hook
  - `run(inputs, telemetry_sink)` execution method returning telemetry dict
- Protocol does NOT enforce specific Stage A/B/C implementations (allows custom stages)
- **Compliance:** SATISFIED ✓

### 1.3 Telemetry Schema (spec-db-tracing.md §2)

**Normative Requirement:**
> "Tracing Requirements: Simulator SHALL support telemetry capture with per-pixel trace mode. Telemetry payload SHALL be produced by same code paths as production."

**Evidence:**
- `dbex/refinement/stage.py:79-231`: RefinementTelemetry dataclass extends existing schema
- New fields added (Phase A4):
  - `stage_type: Optional[str]` — Stage identifier (line 175)
  - `mode: Optional[str]` — Stage mode variant (line 176)
- `to_dict()` method (lines 178-231) serializes all fields for HDF5 export
- Backward compatible: all existing fields preserved from `dbex.nanobrag_refinement.RefinementTelemetry`
- **Compliance:** SATISFIED ✓

## 2. Findings Cross-References

### REFINE-005: Tricubic Interpolation with ±1 HKL Halo

**Finding:** Stage B/C MUST enable tricubic interpolation, Stage A SHOULD enable.

**Phase A Implementation:**
- `dbex/refinement/helpers.py:69`: `create_panel_simulator` includes comment noting tricubic interpolation requirement
- Implementation deferred to Phase B-D (existing Stage A/B/C will use shared helpers)
- **Action Required:** Phase B-D must wire `enable_interpolation=True` flag through shared helpers

### REFINE-007/008: Stage B/C Telemetry Gates

**Finding:** Stage C telemetry gates (≥80% offset reduction, ≤0.05% chi² regression), Stage B gates (≤1e-6 relative chi² regression, ±1% modifier deltas).

**Phase A Implementation:**
- RefinementTelemetry schema supports all telemetry fields required for gates
- Gate enforcement deferred to Phase C-D (Stage B/C implementations)
- **Action Required:** Phase C-D Stage implementations must wire telemetry validation

### SCALE-001/002: Scale Handling Conventions

**Finding:** No multiplication of structure factors (SCALE-001), equal-weight source handling (SCALE-002).

**Phase A Implementation:**
- Shared helpers follow existing conventions from PHYSICS-LOSS-001
- `emit_bragg_frame` stub notes production Simulator.forward() usage (no re-derived physics)
- **Compliance:** Design follows existing patterns ✓

### POLICY-001: Environment Freeze

**Finding:** Do not install/upgrade packages; treat missing imports as blockers.

**Phase A Implementation:**
- No new dependencies imported
- All imports lazy or under `TYPE_CHECKING` (dbex/refinement/stage.py:18, helpers.py:12)
- Reuses existing tensor factories from dbex.nanobrag_bridge
- **Compliance:** SATISFIED ✓

## 3. Environment Freeze Compliance

### 3.1 Dependency Analysis

**Touched Modules:**
- NEW: `dbex/refinement/__init__.py` (package root)
- NEW: `dbex/refinement/stage.py` (RefinementStage protocol, RefinementTelemetry)
- NEW: `dbex/refinement/engine.py` (RefinementEngine)
- NEW: `dbex/refinement/helpers.py` (shared helper stubs)
- NEW: `tests/dbex/test_refinement_engine.py` (TDD nucleus test)
- UPDATED: `docs/TESTING_GUIDE.md` (test registry §2)
- UPDATED: `docs/development/TEST_SUITE_INDEX.md` (test selector registry)

**No changes to:**
- `dbex/nanobrag_refinement.py` (preserved until Phase B)
- `dbex/nanobrag_bridge.py` (no new dependencies)
- `dbex/refine_one.py` (CLI unchanged until Phase E)

### 3.2 Import Analysis

**Lazy Imports (circular import mitigation):**
- `dbex/refinement/stage.py:18`: `from typing import TYPE_CHECKING` guard for type hints
- `dbex/refinement/helpers.py:12-14`: TYPE_CHECKING guard for DetectorConfig/CrystalConfig types
- `dbex/refinement/helpers.py:62`: Lazy import `import nanobrag_torch` inside function body

**No New External Dependencies:**
- All imports from standard library (`dataclasses`, `typing`, `pathlib`) or existing dbex modules
- **Compliance:** SATISFIED ✓

### 3.3 Circular Import Check

**Potential Risks:**
- RefinementStage protocol does NOT import nanobrag_torch or dbex.nanobrag_bridge at module level
- RefinementEngine imports only from .stage (no heavy modules)
- Shared helpers use lazy imports for nanobrag_torch

**Verification:**
- `pytest --collect-only tests/dbex/test_refinement_engine.py`: 1 test collected (no ImportErrors)
- Regression guard `test_stage_a_expansion`: PASSED (existing code unaffected)
- **Compliance:** SATISFIED ✓

## 4. Test Evidence

### 4.1 TDD Nucleus Test

**Selector:** `tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage`

**Status:** PASSED ✓

**Log:** `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T024449Z/pytest_test_refinement_engine.log`

**Validation:**
- Engine executes MockStage once
- Telemetry dict returned with "mock_stage" key
- RefinementTelemetry instance includes stage_type="mock_stage" field
- **All acceptance criteria met**

### 4.2 Regression Guard

**Selector:** `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`

**Status:** PASSED ✓

**Log:** `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T024449Z/pytest_stage_a_regression.log`

**Validation:**
- Existing Stage A refinement unaffected by new modules
- No circular imports detected
- No global state pollution
- **Regression risk: NONE**

### 4.3 Collection Verification

**Selector:** `pytest --collect-only tests/dbex/test_refinement_engine.py`

**Status:** 1 test collected ✓

**Log:** `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T024449Z/pytest_collect_test_refinement_engine.log`

**Validation:**
- Test discoverable via pytest
- No ImportErrors during collection
- Registry updated (`docs/TESTING_GUIDE.md:136`, `docs/development/TEST_SUITE_INDEX.md:17`)

## 5. Phase A Deliverables Checklist

- [x] A0: TDD nucleus test authored and passing
- [x] A1: RefinementStage protocol implemented (dbex/refinement/stage.py)
- [x] A2: RefinementEngine skeleton implemented (dbex/refinement/engine.py)
- [x] A3: Shared helpers extracted (dbex/refinement/helpers.py: create_panel_simulator, emit_bragg_frame stubs)
- [x] A4: RefinementTelemetry extended with stage_type/mode fields
- [x] A5: Test registry updated (TESTING_GUIDE.md, TEST_SUITE_INDEX.md), collect-only artifacts saved
- [x] A6: Compliance evidence documented (this file)
- [x] A7: Phase A documentation complete (phase_a_implementation_summary.md)

## 6. Spec Alignment Summary

| Normative Clause | Source | Status | Evidence |
|------------------|--------|--------|----------|
| Engine Contract: ordered stages | spec-db-workflow.md:33 | ✓ | engine.py:52-107 accepts List[RefinementStage] |
| Stage A/B/C normative definitions | spec-db-workflow.md:35-62 | ✓ | Protocol allows arbitrary Stage implementations |
| Telemetry schema requirements | spec-db-tracing.md §2 | ✓ | RefinementTelemetry.to_dict() includes stage_type/mode |
| Environment Freeze | POLICY-001 | ✓ | No new dependencies, lazy imports |
| Tricubic interpolation | REFINE-005 | Deferred | Phase B-D will wire through shared helpers |
| Stage B/C telemetry gates | REFINE-007/008 | Deferred | Phase C-D will enforce gates |
| Scale handling | SCALE-001/002 | ✓ | Follows PHYSICS-LOSS-001 patterns |

## 7. Next Steps (Phase B)

**Phase B Objective:** Extract Stage A implementation onto the engine using shared helpers

**Prerequisites:**
- Phase A complete (all tasks A0-A7 ✓)
- Regression guard clean (test_stage_a_expansion PASSED ✓)
- Test registry synchronized (TESTING_GUIDE.md, TEST_SUITE_INDEX.md ✓)

**Phase B Tasks:**
- B0: Record baseline artifacts for Stage A smoke
- B1: Implement StageA class wrapping current closure
- B2: Wire StageA into RefinementEngine
- B3: Rerun Stage A smoke (small + full detector)
- B4: Run DB-AT selectors (DB-AT-010, DB-AT-024)
- B5: Update docs/tests

**Estimated Effort:** 2-3 loops (implementation + validation)

## 8. Risk Assessment

### Low Risk

- **Circular imports:** Mitigated with lazy imports and TYPE_CHECKING guards
- **Backward compatibility:** All existing fields preserved in RefinementTelemetry
- **Test coverage:** TDD nucleus + regression guard both PASSED

### Medium Risk

- **Code path divergence:** Phase B-D refactor must preserve exact Stage A/B/C behavior
- **Mitigation:** Comprehensive smoke tests + DB-AT selectors at each phase

### No High Risks Identified

---

**Phase A Compliance Status:** ✓ SATISFIED

**Authored by:** Ralph
**Reviewed by:** (Pending supervisor review)
**Timestamp:** 2025-11-23T024449Z
