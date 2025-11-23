# ARCH-REFINE-FLOW-001 Phase A — Stage Interface & Engine Skeleton (TDD Nucleus + Implementation)

## Summary
Implement Phase A of the Protocol-based Refinement Engine: define RefinementStage protocol, RefinementEngine skeleton, shared helpers for simulator/Bragg generation, extended telemetry schema, and TDD nucleus test validating the engine contract.

## Mode
TDD (supervisor-scoped test specification + engineer implementation)

## Focus
ARCH-REFINE-FLOW-001 — Refactor to Protocol-based Refinement Engine (Phase A: Stage Interface & Engine Skeleton)

## Branch
integration

## Mapped Tests
- **New Tests (Phase A):**
  - `pytest -v tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage` (TDD nucleus: validates RefinementEngine executes dummy Stage and emits telemetry)

- **Regression Guard:**
  - `pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (existing Stage A smoke test must PASS unchanged, proving new modules don't break existing refinement path)

## Artifacts
All outputs under: `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T024449Z/`
- `phase_a_implementation_summary.md` — Phase A completion report with compliance evidence and spec alignment verification
- `pytest_test_refinement_engine.log` — TDD nucleus test execution log (expect PASS after A0-A2 complete)
- `pytest_collect_test_refinement_engine.log` — Collection log for new test (must collect 1 test)
- `pytest_stage_a_regression.log` — Regression guard log (existing test_stage_a_expansion must PASS)
- `phase_a_compliance_evidence.md` — Spec alignment documentation per A6 (links to spec-db-workflow.md §7, findings cross-refs)
- `summary.md` — Turn Summary block (required end-of-loop artifact)

## Do Now

Execute Phase A tasks (A0–A7) implementing the Stage protocol and Engine skeleton per `plans/active/ARCH-REFINE-FLOW-001/implementation.md`.

### Step 1: Review Context (30min, read-only)
Read the following documents in order to understand the normative requirements and existing patterns:
1. **Normative Spec:** `docs/spec-db-workflow.md` §7 (Refinement Protocol Architecture, Engine Contract, Stage definitions) — lines 32-63
2. **Telemetry Requirements:** `docs/spec-db-tracing.md` §2 (telemetry contract for stages)
3. **Canonical Stage A Pattern:** `plans/active/PHYSICS-LOSS-001/reports/2025-11-21T045800Z/` (variance-weighted loss telemetry structure to replicate)
4. **ROI/Cache Contract:** `plans/active/PERF-WARM-SIM-001/implementation.md` (Stage A warm-cache, ROI sampling, perf-telemetry fields like `roi_count_*`, `cache_mode`, `roi_mode`, `forward_time_ms`)
5. **Findings:**
   - REFINE-005: Tricubic interpolation with ±1 HKL halo (Stage B/C MUST enable, Stage A SHOULD enable)
   - REFINE-007: Stage C telemetry gates (≥80% offset reduction, ≤0.05% chi² regression)
   - REFINE-008: Stage B telemetry gates (≤1e-6 relative chi² regression, ±1% modifier deltas)
   - SCALE-001/SCALE-002: Scale handling conventions

**Normative Constraints:**
- **spec-db-workflow.md:33**: "RefinementEngine SHALL accept an ordered list of Stage objects and MUST NOT hardcode the Stage A→B→C flow"
- **spec-db-workflow.md:35-62**: Stage A/B/C normative definitions (trainable params, fixed params, physics requirements)
- **Environment Freeze (POLICY-001)**: Reuse existing tensors/config; new modules MUST NOT import optional dependencies

### Step 2: Implement A0 — TDD Nucleus Test (CRITICAL)
Create `tests/dbex/test_refinement_engine.py` with a minimal unit test validating the engine contract:

**Test Specification (TDD):**
- Test Name: `test_engine_executes_mock_stage`
- Purpose: Verify RefinementEngine can execute a dummy Stage object and aggregate telemetry
- Inputs:
  - MockStage implementing RefinementStage protocol (name="mock_stage", returns dummy telemetry dict)
  - RefinementEngine instantiated with `[MockStage()]`
- Expected Behavior:
  - Engine.run() executes the stage once
  - Engine.telemetry returns `{"mock_stage": <RefinementTelemetry object>}`
  - RefinementTelemetry includes `stage_type="mock_stage"` field
- Acceptance: Test PASSES after A1-A2 implementation complete

**Implementation Notes:**
- Use dataclasses or Protocol (typing.Protocol) for RefinementStage interface
- MockStage.run() returns a dict like `{"chi_squared": 1.0, "masked_mse": 0.1}` (minimal telemetry)
- RefinementEngine.telemetry should return `Dict[str, RefinementTelemetry]`

### Step 3: Implement A1-A2 — Stage Protocol & Engine Skeleton
Create new package `dbex/refinement/` with:

**File: `dbex/refinement/__init__.py`**
```python
# Empty or expose RefinementEngine, RefinementStage for imports
from .engine import RefinementEngine
from .stage import RefinementStage, RefinementTelemetry

__all__ = ["RefinementEngine", "RefinementStage", "RefinementTelemetry"]
```

**File: `dbex/refinement/stage.py`**
- Define `RefinementStage` protocol/abstract base class with methods:
  - `name: str` (property or field)
  - `configure(config: RefinementConfig) -> None` (optional, for future use)
  - `run(inputs: RefinementInputs, telemetry_sink: Optional[Path]) -> Dict[str, Any]`
    - Returns telemetry dict with keys like `chi_squared`, `masked_mse`, `stage_type`, etc.
- Define `RefinementTelemetry` dataclass extending current telemetry structure with:
  - `stage_type: str` (new field: identifies which stage produced this telemetry)
  - `mode: Optional[str]` (new field: e.g., "shell_modifiers" for Stage B, "parity" for future variants)
  - All existing fields from current telemetry (chi_squared, masked_mse, improvement, n_rois, etc.)
  - Method: `to_dict() -> Dict[str, Any]` for serialization

**File: `dbex/refinement/engine.py`**
- Define `RefinementEngine` class with:
  - `__init__(self, stages: List[RefinementStage], config: RefinementConfig)` — store stages, config
  - `run(self, inputs: RefinementInputs) -> Dict[str, RefinementTelemetry]`:
    - Iterate through stages in order
    - Call `stage.run(inputs, telemetry_sink)` for each
    - Aggregate telemetry into dict keyed by stage.name
    - Return aggregated telemetry
  - `telemetry` property returning the aggregated telemetry dict

**Circular Import Mitigation:**
- `RefinementStage` module MUST NOT import heavy simulator modules (`nanobrag_torch`, `dbex.nanobrag_bridge`) at module load time
- Use TYPE_CHECKING imports or lazy imports inside methods if needed

### Step 4: Implement A3 — Shared Helpers Extraction
Create `dbex/refinement/helpers.py` with two shared utilities:

**Function: `create_panel_simulator(...)`**
- Signature: `create_panel_simulator(detector_config: DetectorConfig, crystal_config: CrystalConfig, hkl_grid: ..., config: RefinementConfig, device: torch.device, dtype: torch.dtype) -> Simulator`
- Purpose: Centralize simulator instantiation logic currently duplicated in Stage A/B/C
- Implementation: Extract from `dbex/nanobrag_refinement.py` Stage A panel loop (lines ~800-900)
- Returns: nanobrag_torch.Simulator instance configured for the panel

**Function: `emit_bragg_frame(...)`**
- Signature: `emit_bragg_frame(stage_params: Dict[str, torch.Tensor], inputs: RefinementInputs, config: RefinementConfig, simulators: List[Simulator]) -> torch.Tensor`
- Purpose: Centralize full-frame Bragg generation from stage parameters
- Implementation: Extract Bragg stitching logic from Stage A/B/C closures
- Returns: `[panel, slow, fast]` Bragg tensor

**Notes:**
- These helpers are PLAN-LOCAL for Phase A (not yet used by existing Stage A/B/C code until Phase B-D)
- Ensure helpers respect device/dtype neutrality per `docs/spec-db-runtime.md:12-13`
- No Environment Freeze violations (reuse existing tensor factories, no new deps)

### Step 5: Implement A4 — Extend RefinementTelemetry Schema
Update `RefinementTelemetry` dataclass in `dbex/refinement/stage.py`:

**New Fields:**
- `stage_type: str` — Stage identifier (e.g., "stage_a", "stage_b", "stage_c")
- `mode: Optional[str] = None` — Stage mode variant (e.g., "shell_modifiers" for Stage B, "parity" for future per-reflection)

**Backward Compatibility:**
- Existing telemetry consumers (HDF5 writers, test assertions) read from dict form via `to_dict()`
- Ensure `to_dict()` includes all existing fields plus new `stage_type`/`mode` fields
- New fields should have sensible defaults (mode=None is acceptable)

### Step 6: Implement A5 — Test Registry Update
Update test documentation to reflect new test:

**File: `docs/TESTING_GUIDE.md` §2**
Add new row to the acceptance tests table:
```
| ARCH-ENGINE-001 | RefinementEngine TDD Nucleus | pytest -v tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage | Active | KMP_DUPLICATE_LIB_OK=TRUE | test PASSES, validates engine executes mock stage and aggregates telemetry | plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T024449Z/ | ARCH-REFINE-FLOW-001, spec-db-workflow.md:32-33 |
```

**File: `docs/development/TEST_SUITE_INDEX.md`**
Add row documenting the new test selector.

**Collect-Only Artifact:**
Run `pytest --collect-only tests/dbex/test_refinement_engine.py` and save output to:
`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T024449Z/pytest_collect_test_refinement_engine.log`

### Step 7: Write A6 Compliance Evidence
Create `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T024449Z/phase_a_compliance_evidence.md`:

**Required Content:**
1. **Spec Alignment Verification:**
   - Confirm `RefinementEngine` accepts ordered list of Stages (spec-db-workflow.md:33)
   - Confirm engine does NOT hardcode A→B→C flow (spec-db-workflow.md:33)
   - Confirm `RefinementTelemetry` includes `stage_type`/`mode` fields per spec-db-tracing.md

2. **Findings Cross-References:**
   - REFINE-005: Note that shared helpers will support tricubic interpolation when haloed grids available
   - REFINE-007/008: Note that Stage B/C implementations (Phase C-D) will wire telemetry gates through shared helpers
   - SCALE-001/002: Note that scale handling follows existing conventions from PHYSICS-LOSS-001

3. **Environment Freeze Compliance:**
   - Confirm no new dependencies imported
   - Confirm all imports lazy or under TYPE_CHECKING where needed

4. **Dependency Analysis:**
   - List touched modules: `dbex/refinement/` (new), no changes to `dbex/nanobrag_refinement.py` (preserved until Phase B)
   - Confirm no circular imports detected

### Step 8: Write A7 Documentation
Create `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T024449Z/phase_a_implementation_summary.md`:

**Required Sections:**
1. **Overview** — Phase A deliverables summary
2. **RefinementStage Protocol** — Interface definition, methods, contract
3. **RefinementEngine Skeleton** — Execution flow, telemetry aggregation
4. **Shared Helpers** — `create_panel_simulator`, `emit_bragg_frame` signatures and purposes
5. **Telemetry Schema Extensions** — `stage_type`/`mode` fields, backward compatibility notes
6. **Test Registry** — New test selector, collect-only results
7. **Compliance Evidence** — Link to phase_a_compliance_evidence.md
8. **Next Steps** — Phase B preview (Stage A extraction)

### Step 9: Execute Tests & Regression Guard
Run tests in sequence:

**TDD Nucleus Test:**
```bash
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage 2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T024449Z/pytest_test_refinement_engine.log
```
**Expected Result:** PASS (after A0-A2 implementation complete)

**Regression Guard:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion 2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T024449Z/pytest_stage_a_regression.log
```
**Expected Result:** PASS (existing Stage A unaffected by new modules since they're not imported yet)

### Step 10: Update Implementation Plan Checklist
Edit `plans/active/ARCH-REFINE-FLOW-001/implementation.md`:

Mark Phase A tasks complete:
- [x] A0: TDD nucleus test authored and passing
- [x] A1: RefinementStage protocol implemented
- [x] A2: RefinementEngine skeleton implemented
- [x] A3: Shared helpers extracted (create_panel_simulator, emit_bragg_frame)
- [x] A4: RefinementTelemetry extended with stage_type/mode fields
- [x] A5: Test registry updated, collect-only artifacts saved
- [x] A6: Compliance evidence documented
- [x] A7: Phase A documentation complete

### Step 11: Write Turn Summary
Create `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T024449Z/summary.md` with Turn Summary block:

**Format:**
```markdown
### Turn Summary
Implemented Phase A of Protocol-based Refinement Engine: RefinementStage protocol, RefinementEngine skeleton, shared simulator/Bragg helpers.
TDD nucleus test validates engine executes mock stage and aggregates telemetry; regression guard confirms existing Stage A unaffected.
Next: Phase B extracts Stage A implementation onto the engine using shared helpers.
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T024449Z/ (phase_a_implementation_summary.md, pytest logs, compliance evidence)
```

### Step 12: Commit and Push
Commit all changes with descriptive message:
```bash
git add -A
git commit -m "$(cat <<'EOF'
ARCH-REFINE-FLOW-001 Phase A: Stage Interface & Engine Skeleton

Implemented RefinementStage protocol and RefinementEngine skeleton per
spec-db-workflow.md §7 (Refinement Protocol Architecture). Engine
accepts ordered list of Stages and aggregates telemetry without
hardcoding A→B→C flow.

Changes:
- New package dbex/refinement/ with stage.py (protocol) and engine.py
- RefinementTelemetry extended with stage_type/mode fields for future
  Stage variants (shell_modifiers, parity modes)
- Shared helpers (create_panel_simulator, emit_bragg_frame) extracted
  for code reuse in Phase B-D Stage implementations
- TDD nucleus test (test_refinement_engine.py) validates engine contract

Tests:
- test_engine_executes_mock_stage: PASS (TDD nucleus validates engine)
- test_stage_a_expansion: PASS (regression guard, existing Stage A unaffected)

Spec Alignment:
- spec-db-workflow.md:32-63 (Engine Contract, Stage definitions)
- spec-db-tracing.md §2 (telemetry requirements)
- REFINE-005/007/008 (findings referenced for Phase B-D)

Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T024449Z/

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
git push
```

## How-To Map

### Test Execution Commands
```bash
# TDD Nucleus Test (new test, must collect 1 test and PASS)
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage 2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T024449Z/pytest_test_refinement_engine.log

# Collect-Only (verify new test discovered)
pytest --collect-only tests/dbex/test_refinement_engine.py 2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T024449Z/pytest_collect_test_refinement_engine.log

# Regression Guard (existing Stage A smoke must PASS)
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion 2>&1 | tee plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T024449Z/pytest_stage_a_regression.log
```

### Artifacts Structure
```
plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T024449Z/
├── phase_a_implementation_summary.md   # Overview and deliverables
├── phase_a_compliance_evidence.md      # Spec alignment + findings cross-refs
├── pytest_test_refinement_engine.log   # TDD nucleus test execution
├── pytest_collect_test_refinement_engine.log  # Collect-only output
├── pytest_stage_a_regression.log       # Regression guard
└── summary.md                          # Turn Summary block
```

## Pitfalls To Avoid

1. **Circular Imports:** RefinementStage module MUST NOT import nanobrag_torch or heavy bridge modules at module level. Use TYPE_CHECKING or lazy imports inside methods.

2. **Hardcoded Stage Flow:** RefinementEngine MUST accept arbitrary ordered list of Stages. Do NOT hardcode A→B→C sequence in engine.run() method.

3. **Telemetry Backward Compatibility:** Ensure `RefinementTelemetry.to_dict()` includes all existing fields. New `stage_type`/`mode` fields must not break existing HDF5 writers or test assertions.

4. **Environment Freeze:** Do NOT import new dependencies. Reuse existing config/tensor factories from `dbex.nanobrag_bridge` and `dbex.nanobrag_refinement`.

5. **Shared Helper Usage:** Shared helpers `create_panel_simulator` and `emit_bragg_frame` are PLAN-LOCAL for Phase A testing. Do NOT refactor existing Stage A/B/C code to use them yet (that happens in Phase B-D).

6. **Test Registry:** Do NOT skip updating `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md`. Missing registry entries violate Exit Criterion #4.

7. **TDD Discipline:** Implement A0 test FIRST (test should FAIL until A1-A2 implemented). Do NOT skip the failing test step.

8. **Device/Dtype Neutrality:** Shared helpers must accept `device` and `dtype` parameters explicitly. Do NOT hardcode `cuda:0` or `float32`.

9. **Spec Alignment:** Phase A compliance evidence MUST cite spec-db-workflow.md:32-63 (Engine Contract). Do NOT skip A6 compliance documentation.

10. **Regression Guard:** test_stage_a_expansion MUST PASS unchanged. If it fails, your new modules are leaking side effects. Revert and fix circular imports or global state pollution.

## If Blocked

**Test Failures:**
- If `test_engine_executes_mock_stage` fails: Check RefinementStage protocol implementation, ensure MockStage.run() returns dict, verify Engine.telemetry aggregation logic.
- If `test_stage_a_expansion` fails: Your new modules are interfering with existing code. Check for accidental imports in `dbex/nanobrag_refinement.py`, revert circular import fixes.

**Circular Import Errors:**
- Move heavy imports inside method bodies instead of module level.
- Use `if TYPE_CHECKING:` blocks for type hints only.
- Verify `dbex/refinement/__init__.py` does not trigger cascade imports.

**Spec Drift:**
- If engine hardcodes A→B→C flow: Refactor `Engine.run()` to iterate `self.stages` generically.
- If telemetry schema breaks existing tests: Check `to_dict()` includes all original fields.

**Capture & Escalate:**
Document blocker in `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T024449Z/blocker_report.md`:
- What failed (test name, error message)
- What you tried (max 3 attempts per issue)
- Hypothesis for root cause
- Request for supervisor guidance (include spec clause or finding ID)

Update `docs/fix_plan.md` Attempts History with blocker entry and mark status `blocked`.

## Findings Applied

**Mandatory Adherence:**
- **REFINE-005:** Shared helpers will support tricubic interpolation when haloed HKL grids available (helpers accept `enable_interpolation` flag).
- **REFINE-007:** Stage C telemetry gates (≥80% offset reduction, ≤0.05% chi² regression) will be wired through shared helpers in Phase D.
- **REFINE-008:** Stage B telemetry gates (≤1e-6 relative chi² regression, ±1% modifier deltas) will be wired through shared helpers in Phase C.
- **SCALE-001/SCALE-002:** Scale handling follows existing PHYSICS-LOSS-001 conventions (no multiplication of structure factors).
- **POLICY-001 (Environment Freeze):** No new dependencies, reuse existing tensor/config factories.

**No relevant findings in the knowledge base conflict with Phase A scope.**

## Pointers

**Normative Specs:**
- `docs/spec-db-workflow.md:32-63` — Refinement Protocol Architecture (Engine Contract, Stage definitions)
- `docs/spec-db-tracing.md` §2 — Telemetry requirements

**Context Priming:**
- `plans/active/PHYSICS-LOSS-001/reports/2025-11-21T045800Z/` — Canonical Stage A telemetry structure
- `plans/active/PERF-WARM-SIM-001/implementation.md` — ROI/cache contract (`roi_count_*`, `cache_mode`, `roi_mode`, `forward_time_ms`)

**Existing Code References:**
- `dbex/nanobrag_refinement.py:800-900` — Stage A panel loop (source for `create_panel_simulator` helper)
- `dbex/nanobrag_refinement.py:1132-1227` — Stage B closure (reference for shared loss computation)
- `tests/dbex/test_torch_refine_smoke.py:583-781` — Stage A smoke test (regression guard)

**Findings:**
- `docs/findings.md` REFINE-005, REFINE-007, REFINE-008 (Stage B/C telemetry gates)
- `docs/findings.md` SCALE-001, SCALE-002 (scale handling)

**Fix Plan:**
- `docs/fix_plan.md` ARCH-REFINE-FLOW-001 entry (initiative tracking)
- `plans/active/ARCH-REFINE-FLOW-001/implementation.md` (full Phase A-E plan)

## Next Up
If Phase A completes successfully (all tests PASS, compliance evidence complete):
- **Phase B:** Extract Stage A implementation onto the engine using shared helpers
- **Phase B0:** Record baseline artifacts for Stage A smoke test
- **Phase B1-B5:** Implement StageA class, wire into RefinementEngine, verify no regression

If Phase A blocked or partial:
- Continue Phase A tasks (complete checklist items, fix test failures)
- Document blocker per "If Blocked" section above

## Doc Sync Plan
**Triggered:** Phase A adds new test `test_refinement_engine.py::test_engine_executes_mock_stage`

After code passes:
1. Run `pytest --collect-only tests/dbex/test_refinement_engine.py` and save to `pytest_collect_test_refinement_engine.log`
2. Update `docs/TESTING_GUIDE.md` §2 table with ARCH-ENGINE-001 row (selector, acceptance criteria, artifacts path, findings cross-refs)
3. Update `docs/development/TEST_SUITE_INDEX.md` with ARCH-ENGINE-001 row

## Mapped Tests Guardrail
**New Test:** `test_refinement_engine.py::test_engine_executes_mock_stage`
- Expected: Collects 1 test (verified via `--collect-only`)
- Status after implementation: Active (must PASS)

**Regression Guard:** `test_stage_a_expansion`
- Expected: Continues to PASS unchanged
- If FAILS: New modules leaking side effects, revert and fix

**Hard Gate:** Do NOT mark Phase A done if `--collect-only` returns 0 tests or if either test FAILS.
