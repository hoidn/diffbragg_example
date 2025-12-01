Summary: Move Stage B LBFGS helpers (params/closures/run + ASU utilities) into `dbex/refinement/stage_b_impl.py` so the engine and inline paths stop importing the monolith for Stage B.
Mode: none
Focus: ARCH-REFINE-001 - Refinement Engine Modularization & Torch IO
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small, tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke --smoke-detector-size=small
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T084505Z/
Do Now:
- Implement: dbex/refinement/stage_b_impl.py::_build_stage_b_params - migrate `_build_stage_b_params/_build_stage_b_lbfgs_closure/_run_stage_b_lbfgs` plus the Stage B ASU/shell helpers (`compute_hkl_shell_lookup`, `compute_hkl_asu_map`, `initialize_asu_modifiers`, `apply_asu_modifiers`) into a refinement-owned module, update `dbex/refinement/stage_b.py` and the inline Stage B branch in `dbex/nanobrag_refinement.py` to import from it, and preserve StageAContext warm-cache + telemetry semantics so Stage B CPU fallback (PERF-WARM-011) and PHYSICS-LOSS-001 dual metrics stay intact.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T084505Z/telemetry_stage_b_shell.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T084505Z/pytest_stage_b_shell.log
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T084505Z/telemetry_stage_b_per_reflection.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T084505Z/pytest_stage_b_per_reflection.log
How-To Map:
1. mkdir -p plans/active/ARCH-REFINE-001/reports/2025-12-01T084505Z
2. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T084505Z/collect_stage_b.log
3. Implement the helper migration: create `dbex/refinement/stage_b_impl.py`, move the Stage B helper definitions there, update `dbex/refinement/stage_b.py`/`dbex/nanobrag_refinement.py` imports, and confirm via `rg -n "_build_stage_b" dbex` that only the new module owns these definitions.
4. Run the Stage B shell smoke command above (ensure `DBEX_SMOKE_TELEMETRY_PATH` points to `telemetry_stage_b_shell.json`) and archive the pytest log + telemetry file under the artifacts directory.
5. Rerun the Stage B per-reflection selector with its telemetry path, tee output to `pytest_stage_b_per_reflection.log`, and stash both JSON payloads alongside the logs for parity review.
Pitfalls To Avoid:
- Do not introduce circular imports; `stage_b_impl` must not import `dbex.refinement.stage_b` or CLI modules.
- Keep CPU fallback + warm-cache semantics identical (PERF-WARM-011) - Stage B must still clone StageAContext on CPU when fallback triggers.
- Preserve telemetry fields (`stage_b_mode`, `optimizer_type`, ASU stats, variance-floor counters) so REFINE-008 gates remain meaningful.
- Leave environment untouched (POLICY-001) and avoid editing third-party packages.
- Respect PHYSICS-LOSS-001 dual-metric tracking inside the migrated helpers; both chi-squared and masked-MSE traces must continue to record full/sample entries.
- Shell vs per-reflection mode must still auto-fallback when ASU mapping fails; log warnings exactly once (REFINE-008 + REFINE-FLOW-001).
- Ensure Stage B inline branch and StageB wrapper both import from the new module to keep engine vs inline parity.
- Keep dtype/device neutrality (no `.cuda()` shortcuts); rely on the incoming config device when allocating tensors.
- Update docstrings/import comments referencing helper locations to avoid stale breadcrumbs in future loops.
If Blocked:
- If cyclic imports or missing dependencies prevent Stage B helper extraction, capture the traceback plus `rg` evidence in the artifacts directory, note the blocker (file+line) in `docs/fix_plan.md` Attempts History, and log the same context in `galph_memory.md` before pausing.
Findings Applied (Mandatory):
- REFINE-008 - Maintain Stage B loss-improvement/±1% modifier gates by keeping telemetry + validation hooks untouched.
- PERF-WARM-011 - CPU fallback/warm-cache behavior cannot regress while relocating helpers.
- PHYSICS-LOSS-001 - Stage telemetry must continue to emit chi-squared and masked-MSE traces with sigma provenance.
- POLICY-001 - No environment/toolchain changes; treat missing imports as blockers.
Pointers:
- plans/active/ARCH-REFINE-001/implementation.md:47 - Phase A checklist detailing Stage B helper extraction requirements before context refactors.
- dbex/nanobrag_refinement.py:61 - Stage B ASU/shell helper definitions currently living in the monolith and targeted for relocation.
- dbex/refinement/stage_b.py:1 - Stage B wrapper still importing `_build_stage_b_*` from `dbex.nanobrag_refinement`.
- docs/spec-db-workflow.md:59 - Stage B shell/per-reflection spec clauses that govern optimizer selection and halo requirements.
- docs/TESTING_GUIDE.md:140 - Commands/env expectations for `test_stage_b_shell_modifiers` and per-reflection selectors.
Next Up (optional):
- Stage C helper migration (`stage_c_impl.py`) so the inline path and wrapper share one source before introducing RefinementContext/JobContext.
