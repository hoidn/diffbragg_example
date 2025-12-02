# Input for Ralph — ARCH-REFACTOR-001 Phase D.3 Engine Bugfixes

## Summary
Fix 2 Engine bugs blocking Phase D.3 test migration: (1) Stage A artifacts not stored in cold mode, (2) engine_protocol/stage_modes fields not populated.

## Mode
Parity

## InitiativeType
bugfix

## Focus
ARCH-REFACTOR-001 — Refinement Engine Modularization & Physics Separation (Phase D.3: Engine bugfixes before resuming test migration)

## Branch
integration

## Mapped tests
```
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv \
  tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry \
  tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke \
  --smoke-detector-size=small
```
Expected: 2/2 tests PASSED (both currently failing)

## Artifacts
`plans/active/ARCH-REFACTOR-001/reports/2025-12-04T220000Z/`
- `pytest_engine_bugfixes.log` — Full pytest output for both tests
- `summary.md` — Turn summary (prepend to existing file if present)

---

## Do Now

**Context**: Ralph's telemetry key fix (commit a6f39bac) got 3/5 tests passing. The 2 remaining failures expose separate Engine bugs:

1. **Bug #1 (artifacts storage)**: `test_stage_b_per_reflection_smoke` fails because Stage A artifacts are missing from `engine._artifacts` when cold mode is enabled. Root cause: `stage_a.py:2046-2050` only creates StageAArtifacts when `stage_a_ctx is not None`, but cold mode (`enable_stage_a_warm_cache=False`) means `stage_a_ctx=None`, so `artifacts=None`, so Engine doesn't store it.

2. **Bug #2 (Phase E telemetry)**: `test_stage_a_engine_delegation_telemetry` fails because `engine_protocol` and `stage_modes` fields are None. Root cause: Engine.run() doesn't populate these Phase E fields after aggregating telemetry.

Both fixes are small and local to Engine/Stage A code.

---

### Fix 1: Always Create StageAArtifacts (Even in Cold Mode)

**File:** `dbex/refinement/stage_a.py`

**Current code (lines ~2046-2050):**
```python
        # Create StageAArtifacts with warm context payload + optional final Bragg
        artifacts = StageAArtifacts(
            stage_a_ctx=stage_a_ctx,
            context_schema_version="v1",
            bragg_full=bragg_full_artifact
        ) if stage_a_ctx is not None else None
```

**Replace with:**
```python
        # Create StageAArtifacts with warm context payload + optional final Bragg
        # ARCH-REFACTOR-001 Phase D.3: Always create artifacts (even if stage_a_ctx is None in cold mode)
        # This ensures Engine can store Stage A artifacts for all runs, not just warm cache mode
        artifacts = StageAArtifacts(
            stage_a_ctx=stage_a_ctx,  # May be None in cold mode (enable_stage_a_warm_cache=False)
            context_schema_version="v1",
            bragg_full=bragg_full_artifact  # May be None when Stage B/C follow
        )
```

**Rationale**: StageAArtifacts should always exist to provide a typed channel for outputs. The `stage_a_ctx` field can be None (it's typed as `Any` which includes None). This matches the design intent of artifacts.

---

### Fix 2: Populate engine_protocol and stage_modes Fields

**File:** `dbex/refinement/engine.py`

**Location:** After the loop that processes stages (after line ~190), before the legacy telemetry dict mapping (before line ~192).

**Add this code block:**

```python
        # Aggregate into telemetry dict keyed by stage name
        self._telemetry[stage.name] = telemetry

    # ARCH-REFINE-FLOW-001 Phase E: Populate engine_protocol and stage_modes for all stages
    # These fields describe the stage execution plan (which stages ran, what modes they used)
    engine_protocol_str = self._compute_engine_protocol()
    stage_modes_dict = self._compute_stage_modes()

    for stage_name, telem in self._telemetry.items():
        telem.engine_protocol = engine_protocol_str
        telem.stage_modes = stage_modes_dict

    # ARCH-REFACTOR-001 Phase D.3: Map stage names to legacy labels for backward compatibility
```

**Then add these two helper methods to the RefinementEngine class (after the `run` method, before the `telemetry` property):**

```python
def _compute_engine_protocol(self) -> str:
    """
    Compute engine protocol string describing stage execution sequence.

    Returns:
        str: Protocol string like "stage_a", "stage_a+stage_b", "stage_a+stage_b+stage_c"

    Examples:
        - Stage A only → "stage_a"
        - Stage A + B → "stage_a+stage_b"
        - Stage A + B + C → "stage_a+stage_b+stage_c"
    """
    executed_stages = sorted(self._telemetry.keys())  # Sort for deterministic order
    return "+".join(executed_stages)

def _compute_stage_modes(self) -> Dict[str, str]:
    """
    Compute stage modes dict mapping stage labels to their mode strings.

    Returns:
        Dict[str, str]: Map of stage label → mode. Empty dict if no modes set.

    Examples:
        - Stage A only with no mode → {}
        - Stage B shell mode → {"B": "shell"}
        - Stage B + C → {"B": "per_reflection", "C": "detector_offsets"}
    """
    stage_modes = {}

    # Map internal stage names to legacy labels for consistency with telemetry keys
    label_map = {"stage_a": "A", "stage_b": "B", "stage_c": "C"}

    for stage_name, telem in self._telemetry.items():
        if telem.mode is not None:
            label = label_map.get(stage_name, stage_name)
            stage_modes[label] = telem.mode

    return stage_modes
```

**Rationale**: The Phase E fields describe the execution plan. `engine_protocol` describes the sequence of stages (like "stage_a+stage_b"), and `stage_modes` maps stage labels to their modes (like `{"B": "shell"}`). These need to be computed after all stages run but before returning telemetry.

---

### Step 3: Validation

**Command:**
```bash
mkdir -p plans/active/ARCH-REFACTOR-001/reports/2025-12-04T220000Z

AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv \
  tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry \
  tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke \
  --smoke-detector-size=small \
  | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-04T220000Z/pytest_engine_bugfixes.log
```

**Gate:** 2/2 tests PASSED

**Expected outcomes:**
- `test_stage_a_engine_delegation_telemetry`: Should pass with `engine_protocol="stage_a"` and `stage_modes={}`
- `test_stage_b_per_reflection_smoke`: Should pass with Stage A artifacts present in `engine._artifacts` dict

**If tests still fail:**
1. Check that StageAArtifacts is created even when `stage_a_ctx=None`
2. Verify `engine_protocol` and `stage_modes` are populated before legacy key mapping
3. Check that helper methods return correct values for different stage combinations
4. Capture failure signature in artifacts and mark blocked

---

### Step 4: Commit

**Message template:**
```
ARCH-REFACTOR-001 Phase D.3 Engine bugfixes: artifacts storage + Phase E telemetry (tests: 2/2 pass)

Fixed 2 Engine bugs blocking Phase D.3 test migration:

Bug #1 - Stage A artifacts storage in cold mode:
- Root cause: stage_a.py:2046-2050 only created StageAArtifacts when stage_a_ctx != None
- In cold mode (enable_stage_a_warm_cache=False), stage_a_ctx=None, so artifacts=None
- Engine.run() line 156-157 only stores artifacts if not None, so Stage A missing from dict
- Fix: Always create StageAArtifacts (allow stage_a_ctx field to be None in cold mode)
- Impact: test_stage_b_per_reflection_smoke now passes (Stage A artifacts present)

Bug #2 - Phase E telemetry fields not populated:
- Root cause: Engine.run() aggregated telemetry but never populated engine_protocol/stage_modes
- These Phase E fields (RefinementTelemetry lines 172-173) describe execution plan
- Fix: Added _compute_engine_protocol() and _compute_stage_modes() helpers
- Populate these fields for all stages after loop completes, before legacy key mapping
- Impact: test_stage_a_engine_delegation_telemetry now passes (protocol="stage_a", modes={})

Tests: 2/2 PASSED
- test_stage_a_engine_delegation_telemetry ✓ (engine_protocol populated)
- test_stage_b_per_reflection_smoke ✓ (Stage A artifacts stored)

Metrics: 2 files touched (stage_a.py: -1 line conditional, engine.py: +29 lines helpers), net +28 lines
Phase D.3 Engine blockers resolved; can resume test migration in next loop.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Pitfalls To Avoid

1. **StageAArtifacts fields can be None**: The dataclass allows `stage_a_ctx: Any` and `bragg_full: Optional[Any]`, so None values are valid.

2. **engine_protocol format**: Use internal names ("stage_a+stage_b"), not legacy labels ("A+B"), for consistency with stage.name.

3. **stage_modes keys**: Use legacy labels ("A", "B", "C") for consistency with returned telemetry dict keys.

4. **Populate before legacy mapping**: The Phase E fields must be set before the legacy telemetry dict mapping (line 192).

5. **Deterministic ordering**: Sort stage names when building engine_protocol to ensure consistent strings.

6. **Empty stage_modes**: Return `{}` (empty dict), not None, when no stages have modes set.

7. **All stages get same values**: Every stage telemetry gets the same `engine_protocol` and `stage_modes` (describes overall run).

8. **Import location**: Add Dict import if not already present in engine.py (for `_compute_stage_modes` return type).

9. **Environment Freeze**: Do not install/upgrade packages. If an import fails, mark blocked.

10. **Initiative type**: This is a bugfix (fixing broken Engine behavior), not architecture (not changing structure).

---

## If Blocked

**Scenario 1: Tests still fail with artifacts missing**
- Debug: Add print statement showing `artifacts` value before `if artifacts is not None` check in Engine
- Verify StageAArtifacts is created (check type) even when stage_a_ctx=None
- Check that Stage A actually returns a StageResult with artifacts field populated
- Capture debug output in artifacts, mark blocked

**Scenario 2: Tests still fail with engine_protocol=None**
- Debug: Add print statement showing when _compute_engine_protocol() is called and what it returns
- Verify the field assignment happens before legacy key mapping
- Check that telem.engine_protocol exists and is mutable
- Capture debug output, mark blocked

**Scenario 3: Wrong engine_protocol value**
- Check stage execution order (should be stage_a, stage_b, stage_c)
- Verify sorting produces consistent order
- Compare expected vs actual protocol string format
- Capture mismatch in artifacts, mark blocked

**Fallback:** Capture all evidence in artifacts directory, update Attempts History in `docs/fix_plan.md`, and mark ARCH-REFACTOR-001 blocked pending deeper Engine investigation.

---

## Findings Applied

**Relevant findings from `docs/findings.md`:**

- **ARCH-STAGE-CONTEXT-001**: StageAArtifacts provides typed artifact channel; should always exist regardless of warm cache mode.
- **ARCH-REFINE-FLOW-001 Phase E**: engine_protocol and stage_modes fields added to RefinementTelemetry for execution plan description.
- **Environment Freeze**: Runtime is pre-provisioned; do not install/upgrade packages during loops.
- **Initiative type: bugfix**: Fixing broken Engine behavior (not changing architecture or specs).

---

## Pointers

**Reference documents:**
- Engine code: `dbex/refinement/engine.py` lines 135-206 (stage loop and telemetry aggregation)
- Stage A artifacts creation: `dbex/refinement/stage_a.py` lines 2046-2050
- Phase E telemetry fields: `dbex/refinement/stage.py` lines 172-173 (RefinementTelemetry dataclass)
- Test expectations: `tests/dbex/test_torch_refine_smoke.py` lines 1017-1020, 1923-1927
- Implementation plan: `plans/active/ARCH-REFACTOR-001/implementation.md` Phase D.3

**Code pointers:**
- Fix 1 target: `dbex/refinement/stage_a.py::StageA.run()` line ~2050
- Fix 2 target: `dbex/refinement/engine.py::RefinementEngine.run()` after line ~190
- Helper methods location: After `run()` method, before `telemetry` property (line ~208)

---

## Next Up

**After this loop (Engine bugfixes complete):**
1. Resume ARCH-REFACTOR-001 Phase D.3 Batch 1 test migration
2. Re-run all 5 smoke tests (should be 5/5 PASSED)
3. Continue Phase D.3 Batch 2 (remaining test files)
4. Proceed to Phase D.4 and D.5 (facade deletion)

**Sign-off:** These are small, targeted bugfixes within the Engine that unblock Phase D.3 test migration. Both fixes preserve existing semantics (no breaking changes to artifacts or telemetry structure).

---

## Doc Sync Plan

**Not applicable this loop** (no new tests added/renamed; fixing Engine implementation bugs).

---

## Mapped Tests Guardrail

Both mapped selectors already exist and should pass after bugfixes:
- `test_stage_a_engine_delegation_telemetry` (currently fails on engine_protocol=None)
- `test_stage_b_per_reflection_smoke` (currently fails on missing Stage A artifacts)
