Summary: Replace the nanobrag CLI stub with the real simulator, carrying SCALE/geometry guardrails into code and tests.
Mode: none
Focus: NANOBRAG-BACKEND-002 — Replace CLI torch backend stub with nanobrag_torch simulator
Branch: integration
Mapped tests: tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator
Artifacts: plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T024719Z/

Do Now:
- Focus: NANOBRAG-BACKEND-002
- Implement: dbex/nanobrag_bridge.py::build_structure_factor_grid
- Implement: dbex/refine_one.py::create_parser (add --spot-scale-override threading into nanobrag backend)
- Implement: dbex/refine_one.py::run_nanobrag_backend (invoke nanobrag_torch Simulator, apply √scale, retire stub)
- Implement: tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator
- Pytest: KMP_DUPLICATE_LIB_OK=TRUE AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -v tests/dbex/test_refine_one_cli.py -k nanobrag_backend_runs_simulator
- Artifacts: plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T024719Z/

How-To Map:
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only tests/dbex/test_refine_one_cli.py -k nanobrag_backend_runs_simulator | tee plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T024719Z/pytest_collect.log
3. KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_refine_one_cli.py -k nanobrag_backend_runs_simulator --maxfail=1 --log-cli-level=INFO | tee plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T024719Z/pytest_nanobrag_backend.log
4. Capture any patched-simulator call trace (if added) into plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T024719Z/simulator_call.txt for parity evidence.

Pitfalls To Avoid:
- Do not install or upgrade packages; missing `nanobrag_torch` imports must block and be logged.
- Keep structure factors unscaled inside the bridge helper (SCALE-001) and log metadata for diagnostics.
- Apply √(spot_scale_override) only after simulator output (SCALE-002) and assert against double scaling.
- Force simulator execution on CPU and move tensors to NumPy before HDF5 writes to avoid dtype/device leaks.
- Preserve GEOMETRY-002 analytic Euler inversion when instantiating DetectorConfig/Detector.
- Respect HKL-ORIENT-001: use source→sample incident direction; do not negate twice.
- Patch Simulator in tests rather than running the real kernel to keep unit tests deterministic and fast.
- Maintain CLI backwards compatibility (default behavior matches previous args when override omitted).
- Ensure `_write_torch_outputs` stays untouched structurally so existing diagnostics remain valid.

If Blocked:
- Record the precise ImportError/RuntimeError, append it to docs/fix_plan.md Attempts History with blocker status, stash the supporting log under plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T024719Z/, and halt further implementation steps.

Findings Applied (Mandatory):
- GEOMETRY-002 — Detector configs must continue using analytic XYZ inversion when wiring nanobrag_torch.
- SCALE-001 — Structure factors pass through unscaled while hydrating HKL grids.
- SCALE-002 — Apply √(spot_scale_override) as a post-simulation multiplier only.
- HKL-ORIENT-001 — Maintain source→sample incident direction when configuring Simulator.
- CONFIG-002 — Use DetectorConvention enum members when instantiating DetectorConfig.
- CONFIG-003 — Supply BeamConfig.polarization_axis as a tuple with polarization_factor only.
- MODEL-001 — Keep Detector/Crystal instantiation tests covering bridge outputs.

Pointers:
- dbex/refine_one.py:15 — CLI parser where `--spot-scale-override` must be added.
- dbex/refine_one.py:135 — Current nanobrag backend stub slated for Simulator integration.
- dbex/nanobrag_bridge.py:96 — Target location to port `build_structure_factor_grid` helper.
- scripts/generate_simple_cubic_golden.py:96 — Reference implementation of structure-factor hydration and √scale handling.
- docs/nanobrag_api.md:1 — Simulator/Detector/Crystal contract details.
- docs/pytorch_runtime_checklist.md:26 — Device and dtype neutrality guardrails for torch code.

Next Up (optional):
1. Refresh DB_AT_001 parity harness to exercise the real torch backend once simulator wiring lands.
2. Sync docs/TESTING_GUIDE.md + TEST_SUITE_INDEX entries to new artifact timestamps during Phase C.

Doc Sync Plan (Conditional): After tests pass, archive the collect-only log under this report, then update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md with the new pytest selector artifacts per TESTING-003.
