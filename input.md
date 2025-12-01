Summary: Backfill Phase B.5 guardrail tests so RefinementContext/JobContext usage and Stage B CPU fallback device switching stay reproducible before we resume production code changes.
Mode: none
Focus: ARCH-REFINE-001 — Refinement Engine Modularization & Torch IO
Branch: integration
Mapped tests: pytest -vv tests/dbex/test_refinement_engine.py; pytest -vv tests/dbex/test_refinement_context.py; pytest -vv tests/dbex/test_stage_b_cpu_fallback.py
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T140500Z/
Do Now:
- Implement: tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage — update the nucleus to supply a minimal `RefinementContext` via `inputs['context']` and add a new `test_engine_requires_context` that asserts the ValueError emitted when the key is missing (ARCH-ENGINE-003, spec-db-workflow.md §33).
- Implement: tests/dbex/test_refinement_context.py::test_build_refinement_context_copies_job_context_metadata (new file) — author builder tests that prove JobContext extras (`asu_map`, `hkl_indices_grid`, `halo_mask`) copy into RefinementContext and that `build_job_context` rejects a non-positive `sigma_reference_value` per PHYSICS-LOSS-001.
- Implement: tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_params_cpu_fallback_clones_stage_a_ctx — patch `_build_stage_a_context`/`compute_hkl_shell_lookup` to lightweight stubs and assert `_build_stage_b_params` flips `use_stage_b_cpu_fallback=True`, clones the Stage A context to CPU, and keeps `stage_b_cache_mode="warm"` when `config.stage_b_full_eval_on_cpu` and `device='cuda:0'` (GRADIENT-003, PERF-WARM-011/012).
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_refinement_engine.py tests/dbex/test_refinement_context.py tests/dbex/test_stage_b_cpu_fallback.py | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T140500Z/pytest_context_cpu_fallback.log`
How-To Map:
1. `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md`.
2. For `tests/dbex/test_refinement_engine.py`, import `RefinementInputs` and build a tiny numpy/torch payload plus mock detector/beam/crystal to instantiate `RefinementContext`; update the existing test to pass `{'context': ctx}` and add the missing-context ValueError test.
3. Create `tests/dbex/test_refinement_context.py` with helpers that fabricate `JobContext`/`RefinementContext` inputs (use numpy arrays for HKL metadata and `RefinementConfig()` defaults); assert the builder copies metadata and enforces sigma provenance rules.
4. Add `tests/dbex/test_stage_b_cpu_fallback.py` that patches `_build_stage_a_context` and `compute_hkl_shell_lookup` via `unittest.mock`, calls `_build_stage_b_params` twice (CUDA/ROI-off vs CPU/ROI-on), and asserts the CPU fallback telemetry fields toggle as expected.
5. `pytest --collect-only tests/dbex/test_refinement_engine.py tests/dbex/test_refinement_context.py tests/dbex/test_stage_b_cpu_fallback.py > plans/active/ARCH-REFINE-001/reports/2025-12-01T140500Z/collect_context_cpu_fallback.log` to log selector health before running the suite.
6. Run the combined `pytest -vv ...` command above, keep the tee’d log, and stash any additional artifacts (e.g., failing traces) under the same timestamped directory if reruns are required.
Pitfalls To Avoid:
- This is a tests-only loop: do not modify production modules or Stage wrappers—limit edits to the test tree.
- Keep tests hermetic: no reliance on `sp.proc/refGeom_small` or other assets listed in docs/data_dependency_manifest.md.
- When faking CUDA devices in CPU fallback tests, patch helpers so no real CUDA allocation occurs (only inspect flags).
- Preserve deterministic assertions (e.g., ROI sampling) by seeding or sorting any random outputs; avoid brittle dependence on numpy RNG defaults.
- Import builders lazily inside tests to avoid import cycles while Stage modules still evolve.
- Keep new tests ASCII-only, small, and self-documenting; avoid instantiating `nanobrag_torch.Simulator`.
- Record every new artifact/log under the provided timestamp so docs/fix_plan.md references stay valid.
- Respect Environment Freeze—no package installs or GPU diagnostics; missing imports must be logged as blockers instead.
If Blocked:
- Capture the failing test log under `plans/active/ARCH-REFINE-001/reports/2025-12-01T140500Z/blocked.log`, summarize the failure signature plus findings link in docs/fix_plan.md Attempts History and galph_memory.md, then stop so we can replan or retarget the item.
Findings Applied (Mandatory):
- ARCH-ENGINE-003 — Engine telemetry contract now requires `inputs['context']`; tests must enforce this guard.
- REFINE-005 — HKL halos/asu_map metadata must propagate through contexts; tests need to cover that builder behavior.
- REFINE-010 — Stage A ROI auto-panel threshold is the precondition for Stage B CPU fallback; capture it in the CPU fallback test setup.
- GRADIENT-003 & PERF-WARM-011/012 — Document the device-switch logic so fallback regressions are caught.
Pointers:
- docs/fix_plan.md:400 — Phase B.5 scope + validation bullets for this loop.
- docs/architecture/dbex/refinement/context.idl.md:1 — Field contracts for RefinementContext/JobContext builders.
- docs/TESTING_GUIDE.md:150 — Selector registry + artifact expectations for new pytest modules.
- docs/findings.md:65-76 — REFINE-010 and GRADIENT-003 context behind the CPU fallback behavior we’re testing.
Next Up (optional): Once these guardrail tests land, resume ARCH-REFINE-001 Phase C telemetry/IO cleanup or advance to SPEC-REALIGN-001 prep.
Doc Sync Plan: After the new tests pass, keep the collect-only log above in the artifacts directory and update `docs/TESTING_GUIDE.md` §2 / `docs/development/TEST_SUITE_INDEX.md` only if new selectors are promoted beyond module-level invocations (none expected here).
Mapped Tests Guardrail: Ensure the Step 5 collect-only run above reports ≥1 collected test for each mapped selector before executing the full pytest command; abort and investigate if collection returns zero.
