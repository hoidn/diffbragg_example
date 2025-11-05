Summary: Stabilize the Stage A LBFGS scale parameter so the refinement smoke runs without gradient guard failures.
Mode: Parity
Focus: TORCH-REFINE-001 — Implement LBFGS refinement nucleus (Stage A)
Branch: integration
Mapped tests:
- tests/dbex/test_torch_refine_smoke.py::test_loss_decreases
Artifacts: plans/active/TORCH-REFINE-001/reports/2025-11-05T015500Z/
Do Now:
- TORCH-REFINE-001: Implement: dbex/nanobrag_refinement.py::run_nanobrag_refinement — warm-start `log_scale` from `inputs.global_scale_hint` (fallback to 0 when hint missing) and clamp/bound the exponent before `torch.exp` so LBFGS cannot blow up the scale; preserve telemetry deltas/status and keep the closure differentiable; Validate: env KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_loss_decreases --maxfail=1; Artifacts: plans/active/TORCH-REFINE-001/reports/2025-11-05T015500Z/
How-To Map:
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. export TORCH_REFINE_ARTIFACTS=plans/active/TORCH-REFINE-001/reports/2025-11-05T015500Z
3. env KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_loss_decreases | tee "$TORCH_REFINE_ARTIFACTS/collect_refine_smoke.log"
4. env KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_loss_decreases --maxfail=1 --durations=1 | tee "$TORCH_REFINE_ARTIFACTS/pytest_refine_smoke.log"
5. env KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python -m dbex.refine_one --backend nanobrag -e refGeom.expt -r refGeom.refl -i 0 -o tmp/torch_refine_stage_a.h5 -m 747_mask.pkl -z scaled.mtz --mtzCol F,SIGF | tee "$TORCH_REFINE_ARTIFACTS/refine_cli.log"
6. python plans/active/TORCH-REFINE-001/bin/dump_refine_telemetry.py --h5 tmp/torch_refine_stage_a.h5 --output "$TORCH_REFINE_ARTIFACTS/telemetry_snapshot.json"
7. cp tmp/torch_refine_stage_a.h5 "$TORCH_REFINE_ARTIFACTS/torch_refine_stage_a.h5"
Pitfalls To Avoid:
- Do not leave `log_scale` starting at 0 when `inputs.global_scale_hint` is present; spec requires using the calibration seed.
- Clamp or otherwise bound the log-scale before exponentiation instead of clamping the raw scale (maintains smooth gradients).
- Keep the LBFGS closure fully differentiable—no `.detach()`/`.item()`/`.cpu()` on tensors that influence the loss.
- Preserve `/torch_diagnostics` structure (DIAGNOSTICS-001); append fields without removing existing telemetry.
- Maintain deterministic ROI sampling and np.random seeding; avoid introducing nondeterminism that would destabilize loss traces.
- Respect Environment Freeze; do not install packages or touch nanobrag_torch sources unless a separate patch workflow is invoked.
If Blocked: Capture the failing telemetry/status plus stack trace under "$TORCH_REFINE_ARTIFACTS/blocked.md", update docs/fix_plan.md Attempts History with the blocker, and log the same in galph_memory before pivoting focus.
Findings Applied (Mandatory):
- DIAGNOSTICS-001 — `/torch_diagnostics` stays authoritative; ensure telemetry remains complete after the scale fix.
- MASKING-001 — Sparse loss mask coverage is expected; avoid “fixes” that rely on dense coverage assumptions when adjusting ROI sampling.
- REFINE-001 — Warm-start the Stage A scale from the calibration hint and bound `log_scale` to keep LBFGS stable.
Pointers:
- dbex/nanobrag_refinement.py:129 — Stage A LBFGS implementation where the scale parameter is initialized and exponentiated.
- docs/spec-db-workflow.md:20 — Stage A calibration warm-start and optimization rules.
- plans/nanobrag_integration_plan.md:172 — Refinement nucleus contract (LBFGS closure + telemetry expectations).
- tests/dbex/test_torch_refine_smoke.py:121 — Smoke test enforcing ≥5% loss descent and telemetry checks.
- plans/active/TORCH-REFINE-001/reports/2025-11-05T013525Z/pytest_refine_smoke_fail.log — Evidence of the current NaN/Inf gradient failure to reproduce.
Next Up (optional): Consider adding a regression assert on telemetry.status once the scale fix lands.
Doc Sync Plan: After the smoke passes, refresh docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md with the new artifact timestamp, and stash the updated telemetry snapshot path in the fixture ledger before marking the initiative ready for Stage B.
