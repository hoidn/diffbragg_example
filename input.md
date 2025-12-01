Summary: Define and thread a JobContext object from the CLI into run_nanobrag_refinement so stages receive consistent job metadata before resuming Stage B/C smokes.
Mode: none
Focus: ARCH-REFINE-001 — Refinement Engine Modularization & Torch IO
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small; tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small; tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small; tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T121221Z/
Do Now:
- Implement: dbex/refinement/context.py::build_job_context — add the JobContext dataclass/builder, then propagate it through dbex/refine_one.py::run_nanobrag_backend and dbex/nanobrag_refinement.py::run_nanobrag_refinement so RefinementEngine inputs always include both RefinementContext and JobContext; update the CLI tests/mocks accordingly.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T121221Z/telemetry_stage_a_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small (repeat for the Stage B/C selectors with per-stage telemetry paths, then rerun pytest -vv tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T121221Z/pytest_cli_job_context.log).
How-To Map:
1. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py -k "test_stage_a_expansion or test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small > plans/active/ARCH-REFINE-001/reports/2025-12-01T121221Z/collect_stage_smokes_small.log
2. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T121221Z/telemetry_stage_a_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T121221Z/pytest_stage_a_small.log
3. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T121221Z/telemetry_stage_b_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T121221Z/pytest_stage_b_small.log
4. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T121221Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T121221Z/pytest_stage_c_small.log
5. pytest -vv tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T121221Z/pytest_cli_job_context.log
Pitfalls To Avoid:
- Do not instantiate JobContext inside the stage modules; construct it once in the CLI path to avoid circular imports and to keep Environment Freeze intact.
- Keep simulator factory usage confined to forward-only helpers (ARCH-FACTORY-001); Stage A/B/C closures still need direct nanobrag_torch.Simulator construction.
- Preserve Stage A ROI auto-panel fallback (REFINE-010) when threading JobContext through stage inputs—do not collapse ROI sampling flags or telemetry tags.
- Avoid `.item()` / `.cpu()` conversions on detector/crystal tensors when wiring new context fields so Stage C gradients stay attached (GRADIENT-004).
- Respect docs/data_dependency_manifest.md for the `sp.proc/refGeom_small` assets; do not introduce alternate paths or hard-coded absolute directories.
- Do not touch torch/dials installations or add new dependencies; Environment Freeze remains in effect.
- When updating CLI tests, keep the existing mock patch order intact so fixtures continue to intercept simulator constructors.
- Ensure DBEX_SMOKE environment variables are set for every Stage smoke run; tests/conftest.py will hard-fail otherwise.
If Blocked:
- Capture the failing pytest output (and stack traces) under plans/active/ARCH-REFINE-001/reports/2025-12-01T121221Z/blocked.log, note the signature in docs/fix_plan.md Attempts History, and mark ARCH-REFINE-001 blocked in galph_memory with the exact selector/error before attempting retries.
Findings Applied (Mandatory):
- ARCH-FACTORY-001 — JobContext must not leak simulator factory usage into Stage closures; keep `create_unified_simulator` limited to run_nanobrag_backend forward-only code.
- REFINE-010 — Stage A ROI auto-panel telemetry has to remain in sync with Stage C gates, so JobContext plumbing cannot disable the ROI→panel fallback when Stage C is enabled.
- GRADIENT-004 — Warm-cache retargeting relies on tensor-connected detector offsets; do not coerce JobContext payloads to Python scalars that would break autograd.
- PHYSICS-LOSS-001 — Sigma provenance and reference values must travel with the job; JobContext should capture and preserve those fields so Stage smokes keep variance-weighted telemetry consistent.
Pointers:
- docs/fix_plan.md:301 — current ARCH-REFINE-001 Phase B.1/B.2 scope, blockers, and validation expectations.
- plans/active/ARCH-REFINE-001/implementation.md:75 — Phase B checklist outlining JobContext goals and downstream dependencies.
- docs/TESTING_GUIDE.md:161 — Stage smoke selector/env var requirements for small-detector runs.
- docs/data_dependency_manifest.md:52 — refGeom_small dataset + sigma-map provenance needed for the mapped tests.
Next Up (optional):
- B3: Share HKL grid/ASU builders between CLI and contexts so Stage B/C stop recomputing halo metadata once JobContext exists.
