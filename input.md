# Input for Ralph — Loop i=139

**Summary**: Fix detector and beam test harness gradient breaks by implementing tensor-valued override mechanisms in config factories.

**Mode**: none (production fix)

**ActionType**: implementation_ready

**DecisionStatus**: patch_ready

**InitiativeType**: architecture

**Focus**: ARCH-GRADIENT-FLOW-001 — Gradient Flow Restoration (DB-AT-010 Unblock)

**Branch**: integration

**Mapped tests**:
- `tests/dbex/test_gradients.py::test_db_at_010_gradcheck_detector_distance` (expect PASS post-fix)
- `tests/dbex/test_gradients.py::test_db_at_010_gradcheck_beam_wavelength` (expect PASS post-fix)
- `pytest -v tests -k DB_AT_010 --smoke-detector-size=full` (full suite regression check)

**Artifacts**: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T220000Z/`

**Findings Applied (Mandatory)**:

- **GRADIENT-001** (Gradient test patterns): Tests must inject differentiable parameters via override dicts to preserve autograd graph.
  - Code: `tests/dbex/test_gradients.py` (existing crystal_overrides pattern)
  - Adherence: Implement `distance_mm_override` and `wavelength_override` following same pattern.

- **RUNTIME-001** (Runtime execution guardrails): DB-AT-010 requires `NANOBRAGG_DISABLE_COMPILE=1` to avoid Dynamo interference.
  - Code: `docs/TESTING_GUIDE.md:161`
  - Adherence: Use canonical flags for all pytest runs.

- **ARCH-ENGINE-002** (Config factory ownership): Geometry construction logic lives in config factories; overrides must flow through public API.
  - Code: `dbex/refinement/config_factories.py`
  - Adherence: Add override parameters to `create_detector_config` / `create_beam_config`, no test-specific backdoors.

**Pointers**:

- **Evidence artifacts**: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T212000Z/` (Phase A.1-A.2 complete)
  - `suspect_audit.md` — Root cause analysis (test_gradients.py:383, :496)
  - `call_graph_trace.md` — Execution path from gradcheck → forward → loss
- **Implementation plan**: `plans/active/ARCH-GRADIENT-FLOW-001/implementation.md` (Phase B.1 tasks)
- **Planning notes**: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T220000Z/planning_notes.md`
- **SPEC**: `docs/spec-db-conformance.md` §DB-AT-010 (gradcheck acceptance criteria)
- **ARCH**: `docs/architecture.md` §13 Common Pitfalls (gradient hygiene)
- **Testing docs**: `docs/TESTING_GUIDE.md` §1.4 (DB-AT-010 selector pattern)

**ARCH Contracts (mandatory)**:

1. **GRADIENT-001** (Test gradient preservation):
   - **Owner module/API**: Test harness must use tensor-valued override mechanisms (e.g., `crystal_overrides` dict pattern)
   - **Failure classification**: Implementation bug within architecture (test harness violates gradient hygiene by calling `.item()`)
   - **Spec/Doc pointer**: `docs/spec-db-runtime.md` §Gradient Hygiene, `tests/dbex/test_gradients.py` existing crystal tests

2. **ARCH-ENGINE-002** (Config factory ownership):
   - **Owner module/API**: `dbex/refinement/config_factories.py` owns geometry config construction
   - **Failure classification**: Implementation bug within architecture (config factories lack tensor override parameters)
   - **Spec/Doc pointer**: `docs/architecture/module_map.md` (config_factories.py responsibility)

3. **RUNTIME-001** (Gradient execution environment):
   - **Owner module/API**: PyTorch runtime checklist (`NANOBRAGG_DISABLE_COMPILE=1` for gradcheck)
   - **Failure classification**: Implementation bug within architecture (test harness uses correct flags per TESTING_GUIDE.md)
   - **Spec/Doc pointer**: `docs/pytorch_runtime_checklist.md:26`, `docs/TESTING_GUIDE.md:161`

**Do Now (hard validity contract)**:

1. **Implement: `dbex/refinement/config_factories.py::create_detector_config`**
   - Add `distance_mm_override: Optional[torch.Tensor] = None` parameter
   - Conditional logic: if override provided and is tensor, use it; else extract scalar from dxtbx Detector
   - Estimated: 20-30 LOC
   - Pattern reference: `dbex/physics/forward.py:158-163` (existing `crystal_overrides` mechanism)

2. **Implement: `dbex/refinement/config_factories.py::create_beam_config`**
   - Add `wavelength_override: Optional[torch.Tensor] = None` parameter
   - Conditional logic: if override provided and is tensor, use it; else extract scalar from dxtbx Beam
   - Estimated: 15-25 LOC
   - Alternative: Modify test to use BeamConfig constructor directly (if simpler)

3. **Update: `tests/dbex/test_gradients.py::test_db_at_010_gradcheck_detector_distance`**
   - Lines 379-427: Replace `float(distance_tensor.item())` pattern
   - Call `create_detector_config(..., distance_mm_override=distance_tensor)`
   - Remove manual Detector construction workaround
   - Estimated: 5-10 LOC

4. **Update: `tests/dbex/test_gradients.py::test_db_at_010_gradcheck_beam_wavelength`**
   - Lines 493-518: Replace `float(wavelength_tensor.item())` pattern
   - Call `create_beam_config(..., wavelength_override=wavelength_tensor)` or equivalent
   - Estimated: 5-10 LOC

5. **Validate: Run primary tests** (with canonical flags):
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_gradients.py::test_db_at_010_gradcheck_detector_distance
   ```
   - Capture log: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T220000Z/pytest_detector_distance_post_fix.log`
   - Expected: PASSED

   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_gradients.py::test_db_at_010_gradcheck_beam_wavelength
   ```
   - Capture log: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T220000Z/pytest_beam_wavelength_post_fix.log`
   - Expected: PASSED

6. **Validate: Run full DB-AT-010 suite** (regression check):
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests -k DB_AT_010 --smoke-detector-size=full
   ```
   - Capture log: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T220000Z/pytest_db_at_010_full_suite_post_fix.log`
   - Expected: 2/5 PASSED (detector + beam), 3/5 status TBD (crystal tests)

7. **Deliverables: Create analysis report**
   - File: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T220000Z/phase_b1_analysis.md`
   - Contents:
     - Implementation summary (LOC changed, modules touched)
     - Test results (detector PASS/FAIL, beam PASS/FAIL, crystal status)
     - Crystal test failure signature (if still failing)
     - Next action recommendation (Phase A.3 probe OR Phase B.2-B.3 enforcement test)
   - File: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T220000Z/summary.md`
   - Contents: Loop summary for galph_memory.md (focus, deliverables, test metrics, next action)

**Forbidden This Loop**:
- No new plan-local diagnostic scripts (Phase B.1 is production fix only)
- Do not attempt to fix crystal tests (defer to Phase A.3 probe if needed)
- Do not write enforcement test yet (defer to Phase B.2 after status clear)
- Do not update docs/findings.md or TEST_SUITE_INDEX.md (defer to Phase B.4 after all tests passing)

**How-To Map**:

1. Read existing code for patterns:
   - `dbex/physics/forward.py:158-163` — `crystal_overrides` pattern
   - `dbex/refinement/config_factories.py` — detector/beam config factory signatures

2. Implement config factory overrides:
   - Add optional tensor parameters to function signatures
   - Add conditional branches: `if override is not None and isinstance(override, torch.Tensor): ...`
   - Preserve backward compatibility: if override not provided, use existing scalar extraction path

3. Update test harness:
   - Remove `float(tensor.item())` calls
   - Pass tensor directly via new override parameters
   - Ensure rest of test logic unchanged (same loss_fn closure pattern)

4. Run tests sequentially (not parallel):
   - First: detector test alone
   - Second: beam test alone
   - Third: full suite (assess crystal test status)

5. Write analysis report:
   - Document exact LOC changed
   - Copy-paste pytest output (PASSED/FAILED lines, gradcheck tolerances if applicable)
   - For crystal tests: copy full error traceback if still failing

**Pitfalls To Avoid**:

1. **Type discipline**: This is `architecture` (gradient hygiene enforcement), not `bugfix` (semantic change)
2. **No stacking**: Production code is clean; only fix test harness + config factory API
3. **Parity-first**: Not applicable (gradient flow, not numerical parity)
4. **No shadow-pipeline**: Do not create probe scripts; Phase B.1 is production code only
5. **Thin wrapper budget**: Not applicable this loop (production fix, not probe)
6. **No test weakening**: Do not relax gradcheck tolerances or skip tests
7. **Backward compat**: Config factory changes must not break existing call sites (optional parameters)
8. **Symmetric patterns**: Detector and beam overrides should follow same pattern for maintainability
9. **Minimal scope**: Fix only detector + beam this loop; crystal tests investigated separately if needed
10. **Evidence-based next action**: If crystal tests still fail, recommend Phase A.3 probe with concrete hypothesis

**If Blocked**:

- **If config factory override implementation complex** (>30 LOC per function):
  - Document complexity, propose alternative (e.g., test-side BeamConfig construction)
  - Continue with detector override only, defer beam to next loop

- **If detector/beam tests still fail post-fix**:
  - Capture full pytest traceback in analysis report
  - Mark Phase B.1 as blocked, recommend deeper call graph audit or pivot to spec_change

- **If crystal tests mysteriously pass**:
  - Great! Proceed to Phase B.2-B.3 next loop (enforcement test + docs)
  - Update planning_notes.md with surprise success scenario

- **If environment issues** (e.g., nanobrag_torch import errors):
  - Treat as blocker per Environment Freeze policy
  - Do not attempt local patches; mark ARCH-GRADIENT-FLOW-001 blocked_pending_environment

**Doc Sync Plan**: Not applicable this loop (no test renames, no registry changes)

---

**Galph's confidence in this plan**: 0.9 (high confidence detector/beam fixes work; low confidence crystal tests self-resolve)

**Estimated effort**: 1 loop (40-60 LOC implementation + 3 pytest runs)

**Next loop decision tree**:
- If 2/5 PASS (detector+beam), 3/5 FAIL (crystal) → Phase A.3 probe
- If 5/5 PASS → Phase B.2-B.3 enforcement test + docs
- If 0/5 or 1/5 PASS → Deeper audit or blocked
