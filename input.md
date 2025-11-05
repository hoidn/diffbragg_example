Summary: Fix mask tensor coercion on the Stage A LBFGS path so the refinement smoke can run and emit telemetry.
Mode: TDD
Focus: TORCH-REFINE-001 — Implement LBFGS refinement nucleus (Stage A)
Branch: integration
Mapped tests:
- tests/dbex/test_torch_refine_smoke.py::test_loss_decreases
- tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata
Artifacts: plans/active/TORCH-REFINE-001/reports/2025-11-05T010747Z/
Do Now:
- TORCH-REFINE-001: Implement: dbex/nanobrag_refinement.py::run_nanobrag_refinement — coerce each panel’s trusted mask to a torch tensor on the LBFGS refinement path (matching the zero-iteration helper) before instantiating `nanobrag_torch.Detector`, preserving device/dtype so the simulator no longer raises `AttributeError: 'numpy.ndarray' object has no attribute 'to'`; Validate: env KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_loss_decreases; env KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_loss_decreases --maxfail=1; env KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata --maxfail=1; env KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python -m dbex.refine_one --backend nanobrag -e refGeom.expt -r refGeom.refl -i 0 -o tmp/torch_refine_stage_a.h5 -m 747_mask.pkl -z scaled.mtz --mtzCol F,SIGF. Artifacts: $TORCH_REFINE_ARTIFACTS/{collect_refine_smoke.log,pytest_refine_smoke.log,pytest_cli_diag.log,refine_cli.log,telemetry_snapshot.json,torch_refine_stage_a.h5}.
How-To Map:
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. export TORCH_REFINE_ARTIFACTS=plans/active/TORCH-REFINE-001/reports/2025-11-05T010747Z
3. env KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_loss_decreases | tee "$TORCH_REFINE_ARTIFACTS/collect_refine_smoke.log"
4. env KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_loss_decreases --maxfail=1 --durations=1 | tee "$TORCH_REFINE_ARTIFACTS/pytest_refine_smoke.log"
5. env KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata --maxfail=1 --durations=1 | tee "$TORCH_REFINE_ARTIFACTS/pytest_cli_diag.log"
6. env KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python -m dbex.refine_one --backend nanobrag -e refGeom.expt -r refGeom.refl -i 0 -o tmp/torch_refine_stage_a.h5 -m 747_mask.pkl -z scaled.mtz --mtzCol F,SIGF | tee "$TORCH_REFINE_ARTIFACTS/refine_cli.log"
7. python plans/active/TORCH-REFINE-001/bin/dump_refine_telemetry.py --h5 tmp/torch_refine_stage_a.h5 --output "$TORCH_REFINE_ARTIFACTS/telemetry_snapshot.json"
8. cp tmp/torch_refine_stage_a.h5 "$TORCH_REFINE_ARTIFACTS/torch_refine_stage_a.h5"
Pitfalls To Avoid:
- Mirror the zero-iteration mask handling (dbex/nanobrag_bridge.py:991-1004) so tensor dtype/device stay consistent; no ad-hoc `.cpu()` conversions.
- Keep ROI sampling deterministic (seeded np.random) so smoke assertions remain stable; do not introduce nondeterministic panel shuffles.
- Preserve `/torch_diagnostics` metadata (DIAGNOSTICS-001); append keys without overwriting SCALE-003/006 telemetry.
- Avoid touching `nanobrag_torch` internals—fix lives in the DBEX bridge/refinement layer only.
- Respect Environment Freeze: no package installs or torch upgrades while debugging.
- Ensure CLI test fixtures remain fast by reusing existing mocks; no new large file dependencies.
If Blocked: Capture the failing stack trace plus `telemetry_snapshot.json` (if emitted) into $TORCH_REFINE_ARTIFACTS/blocked.md, update docs/fix_plan.md Attempts History with the blocker summary, and log the same context in galph_memory (state=blocked) before switching focus.
Findings Applied (Mandatory):
- DIAGNOSTICS-001 — `/torch_diagnostics` must remain authoritative; extend telemetry without dropping existing attrs.
- RUNTIME-001 — Keep NANOBRAGG_DISABLE_COMPILE=1 for LBFGS tests to avoid Dynamo interference.
- CONFORMANCE-001 — Maintain CLI env flags (`KMP_DUPLICATE_LIB_OK=TRUE`) for parity selectors and smoke tests.
- CONFIG-001 — Honor mask polarity/dtype conversions when bridging dxtbx masks to nanobrag_torch configs.
Pointers:
- plans/nanobrag_integration_plan.md:172 — Refinement nucleus spec (LBFGS closure + telemetry contract).
- docs/spec-db-workflow.md:34 — Stage A optimizer mandate and ROI validation policy.
- dbex/nanobrag_bridge.py:991 — Zero-iteration mask tensor coercion to emulate.
- dbex/nanobrag_refinement.py:318 — LBFGS detector instantiation currently lacking mask tensor conversion.
- tests/dbex/test_torch_refine_smoke.py:129 — Failing smoke asserting ≥5% loss decrease and telemetry completeness.
Next Up (optional): Stage Stage-B planning (extend DoFs beyond {scale, cell_a}) once Stage A smoke is green.
Doc Sync Plan: After tests pass, append the refinement smoke selector and artifact paths to docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md, referencing $TORCH_REFINE_ARTIFACTS/collect_refine_smoke.log; archive updated telemetry expectations in plans/active/TORCH-REFINE-001/reports/.
