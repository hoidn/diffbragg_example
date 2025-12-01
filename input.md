Summary: Route Stage A/B final Bragg reconstruction back through `create_unified_simulator` so forward-only paths inherit the centralized mask/calibration plumbing before Ralph runs the next smoke tests.
Mode: none
Focus: ARCH-REFINE-001 — Refinement Engine Modularization & Torch IO
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small; tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T130955Z/
Do Now:
- Implement: dbex/nanobrag_refinement.py::_build_final_bragg_from_stage_a_telemetry + dbex/nanobrag_refinement.py::_build_final_bragg_from_stage_b_telemetry — convert the cold reconstruction paths to call `dbex.refinement.helpers.create_unified_simulator`, reusing the existing warm-cache route when `StageAContext` is present, and keep stage closures on direct `Simulator` instantiation per ARCH-FACTORY-001.
- Validate: Run the small-detector Stage B and Stage C smokes with telemetry capture:
  1. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T130955Z/telemetry_stage_b_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T130955Z/pytest_stage_b_small.log`
  2. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T130955Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T130955Z/pytest_stage_c_small.log`
How-To Map:
1. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small > plans/active/ARCH-REFINE-001/reports/2025-12-01T130955Z/collect_stage_bc_small.log`
2. Apply the factory changes in `dbex/nanobrag_refinement.py` (Stage A/B final Bragg helpers) plus any supporting comments/tests, keeping Stage closures untouched.
3. Run the Stage B command above, capturing both telemetry JSON and pytest output under the artifacts directory.
4. Run the Stage C command above with its telemetry/log targets so REFINE-007/010 telemetry stays archived.
Pitfalls To Avoid:
- Do not retrofit `create_unified_simulator` into Stage closures or warm-cache contexts; those paths must keep direct `Simulator` construction for autograd (ARCH-FACTORY-001).
- Preserve the warm-cache retargeting flow (GRADIENT-004) when Stage A context is available; the factory should only cover cold starts.
- Keep Stage B CPU fallback behavior identical: convert the shell-modified HKL grid to `final_device` before factory invocation so CPU reconstructions remain deterministic.
- Reuse the existing spot-scale/log_scale math; do not double-apply sqrt scaling after calling the factory.
- Maintain lazy imports and Environment Freeze boundaries; no module-scope imports or new dependencies.
- Capture telemetry/log artifacts for both selectors and keep DBEX_SMOKE_ env vars identical to previous runs.
If Blocked:
- Save the failing selector output into the artifacts directory (e.g., `blocked_stage_b.log`), summarize the failure signature in docs/fix_plan.md Attempts History and galph_memory, and halt work so we can replan around the blocker.
Findings Applied (Mandatory):
- ARCH-FACTORY-001 — Factory is forward-only; document why stage closures remain on direct `Simulator`.
- REFINE-005 — Haloed HKL grids and interpolation metadata must flow through the same factory wiring.
- REFINE-010 — Panel-mode Stage A telemetry feeds the Stage C gate; ensure the reconstruction path preserves those traces.
- GRADIENT-004 — Stage C warm-cache retargeting must keep detector offsets as tensors when reusing context simulators.
Pointers:
- docs/fix_plan.md:387 — Phase B.4 task list and validation requirements for the factory wiring.
- docs/TESTING_GUIDE.md:161 — Stage A/B/C smoke selector contract and required env vars.
- docs/architecture/dbex/refinement/context.idl.md:1 — Context/JobContext contract the factory path must respect.
Next Up (optional): Phase B.5 — consolidate simulator factory usage for forward-only helpers beyond `run_nanobrag_refinement` once the reconstruction path lands.
