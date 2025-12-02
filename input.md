Summary: Enforce the new telemetry dataclasses end-to-end by deleting the legacy `dict` compatibility shims in Stage A/B/C so LBFGS closures, parity guards, and telemetry packaging mutate `StageATelemetryState`/`StageBTelemetryState`/`StageCTelemetryState` directly instead of half-converted mappings.
Mode: none
InitiativeType: architecture
Focus: ARCH-STAGE-CONTEXT-001 — Stage Context + Engine Artifact Boundary
Branch: integration
Mapped tests:
- tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
- tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers
- tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip
Artifacts: plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T160500Z/

Do Now:
- FocusItem: ARCH-STAGE-CONTEXT-001 Phase E — Telemetry Dataclass Enforcement
- Implement: `dbex/refinement/stage_a.py::_build_lbfgs_closure` + `_run_stage_a_lbfgs` (stage_a_impl.py) — remove the `isinstance(telemetry_state, dict)` branches and convert all reads/writes to the `StageATelemetryState` attributes (`loss_trace_full`, `chi_squared_best`, `panel_loss_diag`, etc.). Update type hints/commentary so Stage A expects the dataclass everywhere, and make sure list-based counters (`iteration_count`, `perf_validation_runs`, …) are still mutated in place so closures share the same container.
- Implement: `dbex/refinement/stage_b_impl.py::_check_stage_b_baseline_parity` and `dbex/refinement/stage_b.py::StageB.run` — drop the dict fallback, assign/read parity diagnostics from `StageBTelemetryState` fields, and simplify telemetry extraction/packaging accordingly. Verify the CPU-fallback test path still sees the dataclass (`StageB._build_stage_b_params` already constructs it) instead of a fabricated dict.
- Implement: `dbex/refinement/stage_c_impl.py::{_build_stage_c_lbfgs_closure,_run_stage_c_lbfgs}` and `dbex/refinement/stage_c.py::StageC.run` — migrate the remaining `telemetry_state['foo']` sites to the `StageCTelemetryState` attributes, remove the compatibility shims, and keep PERF-WARM-SIM-001 panel diagnostics writing through `panel_loss_diag`. After the change, Stages A/B/C should no longer import `Dict` for telemetry plumbing.
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T160500Z/pytest_stage_a_small.log`
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T160500Z/pytest_stage_b_shell.log`
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T160500Z/pytest_stage_c_small.log` (full-detector run still fails due to PERF-WARM-SIM-001; no need to rerun it here).

How-To Map:
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T160500Z/pytest_stage_a_small.log`
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T160500Z/pytest_stage_b_shell.log`
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T160500Z/pytest_stage_c_small.log`

Pitfalls To Avoid:
- Do not leave stray `telemetry_state[...]` indexing anywhere; it will raise immediately once the dataclasses stop emulating dicts.
- Preserve mutable list semantics (e.g., `iteration_count[0] += 1`)—replacing them with ints breaks the closure capture used across LBFGS callbacks.
- Keep PERF-WARM-SIM-001 panel diagnostics optional: only allocate `panel_loss_diag` lists when the env var is set, and avoid writing JSON files when it isn’t.
- Stage B per-reflection test still xfails on the known gradient-flow bug; run it only if you need to confirm the failure signature, but do not attempt to “fix” it inside this initiative.
- CPU fallback remains unsupported; do not resurrect dict plumbing just to placate that deferred path (GRADIENT-003).

If Blocked: Capture the failing pytest output and a short note in `plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T160500Z/blocked.md`, cite the offending stage/finding in docs/fix_plan.md, and stop before reintroducing dict shims or weakening the telemetry contract.

Findings Applied (Mandatory):
- ARCH-STAGE-CTX-001 — Stage wrappers must rely on typed contexts/telemetry instead of mutable dicts.
- ARCH-STAGE-CTX-002 — Stage B baseline parity diagnostics need the dataclass-safe path; removing dict writes keeps the guard compliant with REFINE-FLOW-001.
- PHYSICS-LOSS-001 — Telemetry still needs both chi² and masked-MSE traces per stage after the refactor.

Pointers:
- plans/active/ARCH-STAGE-CONTEXT-001/implementation.md#phase-e — scope/details for the telemetry cleanup.
- docs/fix_plan.md §ARCH-STAGE-CONTEXT-001 — current status + artifact links.
- dbex/refinement/stage_a.py & stage_a_impl.py, dbex/refinement/stage_b.py & stage_b_impl.py, dbex/refinement/stage_c.py & stage_c_impl.py — code locations for the telemetry shims to remove.

Next Up (optional): If this lands cleanly, run the Stage B per-reflection smoketest just to archive the expected TORCH-REFINE-004 failure signature under the new telemetry plumbing before closing ARCH-STAGE-CONTEXT-001.
