# Ralph Input — Loop i=249

## Summary
Migrate test harness files from facade pattern to direct RefinementEngine usage, completing ARCH-REFACTOR-001 Phase D.3.

## Focus
ARCH-REFACTOR-001 — Phase D.3 Test Harness Migration

## Branch
`integration`

## Mapped Tests
```
tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers
tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip
tests/dbex/test_stage_a_smoke_parity.py::test_stage_a_mapping_to_refine_roundtrip
```

## Artifacts
`plans/active/ARCH-REFACTOR-001/reports/2025-12-09T060000Z/`

---

## Do Now

**Focus Item:** ARCH-REFACTOR-001 Phase D.3
**Action Type:** Implementation (Test Harness Migration)

### Context

ARCH-SIM-CONSTRUCTION-001 is now **DONE** — upstream confirmed no simulator bug existed (test geometry was flawed). ARCH-REFACTOR-001 Phase D.3 is unblocked.

Phase D.2 (CLI Refactor) provides the reference pattern. The CLI now:
1. Builds `JobContext` then `RefinementContext` via `build_refinement_context()`
2. Instantiates `RefinementEngine` with conditional stage list
3. Calls `engine.run({"context": refinement_context})`
4. Extracts artifacts from `engine._artifacts`

### Implement (Phase D.3 Scope)

Migrate these files from `run_nanobrag_refinement` facade to direct `RefinementEngine` usage:

#### File 1: `tests/dbex/test_torch_refine_smoke.py`

Target functions (6 total):
- `test_stage_a_expansion`
- `test_stage_a_engine_delegation_telemetry`
- `test_stage_b_shell_modifiers`
- `test_stage_c_detector_microslip`
- `test_stage_b_asu_mapping_smoke`
- `test_stage_c_stage_a_baseline_detector_dist`

**Pattern to apply:**
1. Change imports: remove `run_nanobrag_refinement`, add `RefinementEngine`, `build_refinement_context`, `StageA`, `StageB`, `StageC`
2. Replace facade call with Engine pattern (see `dbex/refine_one.py::run_nanobrag_backend()` for reference)
3. Ensure test assertions still validate the same telemetry/artifacts

#### File 2: `tests/dbex/test_stage_a_smoke_parity.py`

Target function (1 total):
- `test_stage_a_mapping_to_refine_roundtrip`

**Pattern:** Same as File 1.

#### File 3: `dbex/tools/stage_a_adam.py`

Target function (1 total):
- `run_debug_refinement` (lines ~350-400)

**Pattern:** Same as File 1 (production tooling).

### How-To Map

1. **Read the reference implementation:**
   - `dbex/refine_one.py::run_nanobrag_backend()` (lines ~270-350)

2. **Key imports to add:**
   ```python
   from dbex.refinement.engine import RefinementEngine
   from dbex.refinement.context import build_refinement_context
   from dbex.refinement.stage_a import StageA
   from dbex.refinement.stage_b import StageB
   from dbex.refinement.stage_c import StageC
   ```

3. **Key imports to remove:**
   ```python
   from dbex.nanobrag_refinement import run_nanobrag_refinement
   ```

4. **Engine instantiation pattern:**
   ```python
   # Build context
   refinement_context = build_refinement_context(
       job_context=job_context,
       baseline_detector=baseline_detector  # if enable_stage_c
   )

   # Build stage list
   stages = [StageA()]
   if enable_stage_b:
       stages.append(StageB())
   if enable_stage_c:
       stages.append(StageC())

   # Run engine
   engine = RefinementEngine(stages=stages)
   result = engine.run({"context": refinement_context})

   # Extract artifacts
   telemetry = engine._artifacts.get("telemetry")
   ```

5. **Validation command:**
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   DBEX_SMOKE_DETECTOR_SIZE=small \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv \
     tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
     tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
     tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip \
     tests/dbex/test_stage_a_smoke_parity.py \
     --smoke-detector-size=small \
     2>&1 | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-09T060000Z/pytest_phase_d3.log
   ```

---

## Pitfalls To Avoid

1. **DO NOT** change test assertions — only migrate the refinement call pattern
2. **DO NOT** change telemetry structure or field names
3. **DO** preserve all fixture setup/teardown logic unchanged
4. **DO** follow the exact Engine pattern from Phase D.2 CLI refactor
5. **DO NOT** remove facade imports from files outside Phase D.3 scope
6. **DO** check for `baseline_detector` usage — it's required for Stage C context building
7. **DO** maintain backward compatibility — tests should produce identical telemetry values

---

## If Blocked

If any test fails after migration:
1. Capture the full pytest output with `-vv --tb=long`
2. Compare the Engine call path with the CLI reference implementation
3. Check if `refinement_context` has all required fields
4. Document the specific failure mode in artifacts
5. Mark D.3 blocked and return to supervisor with findings

---

## Findings Applied (Mandatory)

- **ARCH-ENGINE-002**: RefinementEngine protocol — engine accepts `{"context": RefinementContext}` dict
- **ARCH-FACTORY-001**: Factory scope — simulators come from context, not constructed inline
- **RUNTIME-001**: Test env vars — use canonical `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`
- **TESTING-003**: Mapped test selectors from `docs/TESTING_GUIDE.md`

---

## Pointers

- `plans/active/ARCH-REFACTOR-001/implementation.md:363-385` — Phase D checklist and scope
- `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T201539Z/cli_refactor_blueprint.md` — CLI migration pattern
- `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T220000Z/` — Phase D.2 CLI refactor artifacts
- `dbex/refine_one.py:270-350` — Reference implementation (Engine pattern)
- `docs/fix_plan.md:129-146` — ARCH-REFACTOR-001 exit criteria

---

## Next Up (Optional)

If Phase D.3 completes successfully:
- Phase D.5: Facade Deletion (delete `dbex/nanobrag_refinement.py`)
