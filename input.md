Summary: Verify the nanobrag CLI path honors the torch mask contract and keep Stage B telemetry green while tightening test coverage.
Mode: none
Focus: TORCH-REFINE-004 — Stage B Fhkl modifiers (optional)
Branch: integration
Mapped tests: tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator, tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers
Artifacts: plans/active/TORCH-REFINE-004/reports/2025-11-05T210730Z/

Do Now:
- TORCH-REFINE-004 — Stage B Fhkl modifiers (optional)
  - Implement: tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator — capture the mocked Detector config, assert `mask_array` is a torch float tensor with {0.0, 1.0} values (CLI-001), and document the guard so the CLI path can’t regress back to numpy.
  - Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator | tee $ARTIFACTS/collect_cli_bridge.log && AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator --maxfail=1 --capture=tee-sys | tee $ARTIFACTS/pytest_cli_bridge.log
  - Validate: export KMP_DUPLICATE_LIB_OK=TRUE; export NANOBRAGG_DISABLE_COMPILE=1; AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers | tee $ARTIFACTS/collect_stage_b.log && AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --maxfail=1 --capture=tee-sys | tee $ARTIFACTS/pytest_stage_b.log
  - Validate: KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md python -m dbex.refine_one --backend nanobrag -e refGeom.expt -r refGeom.refl -i 0 -o $ARTIFACTS/nanobrag_stage_progress.h5 -m 747_mask.pkl -z scaled.mtz | tee $ARTIFACTS/refine_cli.log
  - Artifacts: plans/active/TORCH-REFINE-004/reports/2025-11-05T210730Z/

How-To Map:
- export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
- export ARTIFACTS=plans/active/TORCH-REFINE-004/reports/2025-11-05T210730Z
- mkdir -p "$ARTIFACTS"
- AUTHORITATIVE_CMDS_DOC=$AUTHORITATIVE_CMDS_DOC pytest --collect-only tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator | tee "$ARTIFACTS/collect_cli_bridge.log"
- AUTHORITATIVE_CMDS_DOC=$AUTHORITATIVE_CMDS_DOC pytest -vv tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_runs_simulator --maxfail=1 --capture=tee-sys | tee "$ARTIFACTS/pytest_cli_bridge.log"
- export KMP_DUPLICATE_LIB_OK=TRUE
- export NANOBRAGG_DISABLE_COMPILE=1
- AUTHORITATIVE_CMDS_DOC=$AUTHORITATIVE_CMDS_DOC pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers | tee "$ARTIFACTS/collect_stage_b.log"
- AUTHORITATIVE_CMDS_DOC=$AUTHORITATIVE_CMDS_DOC pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --maxfail=1 --capture=tee-sys | tee "$ARTIFACTS/pytest_stage_b.log"
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=$AUTHORITATIVE_CMDS_DOC python -m dbex.refine_one --backend nanobrag -e refGeom.expt -r refGeom.refl -i 0 -o "$ARTIFACTS/nanobrag_stage_progress.h5" -m 747_mask.pkl -z scaled.mtz | tee "$ARTIFACTS/refine_cli.log"
- rg "mask_array" dbex/nanobrag_bridge.py | tee "$ARTIFACTS/mask_guard_probe.txt"
- printf "CLI mask guard + Stage B smoke verified; see %s, %s, %s\\n" "$ARTIFACTS/pytest_cli_bridge.log" "$ARTIFACTS/pytest_stage_b.log" "$ARTIFACTS/refine_cli.log" >> "$ARTIFACTS/summary.md"

Pitfalls To Avoid:
- Keep Environment Freeze intact; no installs or conda tweaks if imports fail.
- Do not revert torch mask emission—CLI-001 requires `torch.Tensor` with float32 dtype.
- Ensure Stage B smoke runs with `NANOBRAGG_DISABLE_COMPILE=1` (RUNTIME-001) to avoid Dynamo interference.
- Preserve deterministic ROI sampling; Stage B sampler must reuse Stage A IDs (REFINE-008).
- Capture collect-only logs before running selectors (TESTING-003) so documentation stays synchronized.
- When running the CLI, confirm output paths live under `$ARTIFACTS` to avoid polluting prior reports.
- Keep CLI run on CPU; do not set CUDA-specific flags that might change telemetry.
- Do not modify `RefinementConfig.stage_b_min_loss_improvement`; calibration already landed at 1e-8.
- Preserve mask polarity (1=include) when asserting in tests; no tolerance for float drift.
- If CLI throws, record minimal traceback and exit rather than continuing with stale artifacts.

If Blocked:
- Save the failing command output to $ARTIFACTS/blocker.log, note the traceback and offending dtype/device, update docs/fix_plan.md status to `blocked` with the error signature, and log the retry condition in galph_memory.md before exiting.

Findings Applied (Mandatory):
- CLI-001 — Guard torch mask emission in CLI paths; new test must enforce tensor dtype/polarity.
- REFINE-008 — Stage B gate calibrated to 1e-8; smoke rerun ensures telemetry stays consistent.
- TESTING-003 — Collect-only logs precede pytest runs so selector status remains authoritative.
- RUNTIME-001 — Disable torch.compile via `NANOBRAGG_DISABLE_COMPILE=1` for refinement selectors.

Pointers:
- dbex/nanobrag_bridge.py:379 — Torch mask coercion logic referenced by CLI-001.
- tests/dbex/test_refine_one_cli.py:90 — Nanobrag backend simulator test to enhance with mask assertions.
- tests/dbex/test_torch_refine_smoke.py:647 — Stage B telemetry assertions that must remain green post-CLI run.
- docs/config_crosswalk.md:31 — Detector mask mapping reference confirming torch float32 requirement.
- plans/active/TORCH-REFINE-004/reports/2025-11-05T200729Z/pytest_stage_b_regression.log — Previous Stage B telemetry pass baseline.

Next Up (optional):
- Re-run full pytest suite once CLI smoke and Stage B pass to confirm no latent regressions.
