Summary: Wire the nanobrag CLI backend to the real simulator with scale guardrails and targeted tests.
Mode: none
Focus: NANOBRAG-BACKEND-002 — Replace CLI torch backend stub with nanobrag_torch simulator
Branch: integration
Mapped tests: tests/dbex/test_refine_one_cli.py::TestNanobragBackendSimulator::test_invokes_simulator
Artifacts: plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T024056Z/

Do Now:
- Focus: NANOBRAG-BACKEND-002
- Implement: dbex/refine_one.py::run_nanobrag_backend (also extend create_parser with --spot-scale-override and add nanobrag_bridge.build_structure_factor_grid)
- Pytest: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_refine_one_cli.py -k nanobrag_backend_simulator
- Artifacts: plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T024056Z/

How-To Map:
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_refine_one_cli.py -k nanobrag_backend_simulator --maxfail=1 --log-cli-level=INFO | tee plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T024056Z/pytest_nanobrag_backend.log
3. KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only tests/dbex/test_refine_one_cli.py -k nanobrag_backend_simulator | tee plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T024056Z/collect_nanobrag_backend.log

Pitfalls To Avoid:
- Do not reinstall or modify packages; Environment Freeze is in effect.
- Keep structure factors unscaled pre-simulator per SCALE-001; apply only the √(spot_scale_override) post-factor (SCALE-002).
- Ensure nanobrag_torch Simulator runs on CPU and tensors move back to numpy before serialization.
- Preserve GEOMETRY-002 Euler inversion outputs when creating DetectorConfig/Detector.
- Respect HKL-ORIENT-001: incident direction should be source→sample for single-source simulator runs.
- Guard missing nanobrag_torch imports with pytest.importorskip and log blockers instead of stubbing.
- Avoid touching DiffBragg code paths or parity fixtures in this loop.
- Keep new tests deterministic—patch Simulator instead of calling the real kernel during unit tests.
- Ensure `_write_torch_outputs` receives numpy arrays (not torch tensors) to avoid HDF5 dtype issues.

If Blocked:
- Capture the exact ImportError/RuntimeError signature, add it to docs/fix_plan.md Attempts History, and mark the initiative blocked; stash logs under the artifacts directory for Ralph to inspect next loop.

Findings Applied (Mandatory):
- GEOMETRY-002 — Preserve analytic Euler inversion when constructing DetectorConfig for Simulator inputs.
- SCALE-001 — Leave structure factors unscaled when hydrating HKL grids.
- SCALE-002 — Apply √(spot_scale_override) as a post-simulation factor only.
- HKL-ORIENT-001 — Maintain source→sample incident direction when configuring Simulator beams.
- CONFIG-002 — Use DetectorConvention enum values when instantiating DetectorConfig.
- CONFIG-003 — Pass polarization_axis as a tuple and omit polarization_fraction for BeamConfig.
- MODEL-001 — Retain roundtrip tests that instantiate Detector/Crystal models with bridge outputs.

Pointers:
- dbex/refine_one.py:135 — Current stubbed nanobrag backend to be replaced with real Simulator loop.
- scripts/generate_simple_cubic_golden.py:96 — Canonical build_structure_factor_grid implementation for hydration reference.
- dbex/nanobrag_bridge.py:250 — Detector/Beam/Crystal config helpers that supply Simulator inputs.
- tests/dbex/test_refine_one_cli.py:80 — Existing nanobrag backend tests to extend for simulator coverage.
- docs/pytorch_runtime_checklist.md:26 — Device/dtype neutrality guards for torch code.

Next Up (optional):
- After simulator loop lands, extend parity harness to exercise the real backend (Exit Criterion 3).
