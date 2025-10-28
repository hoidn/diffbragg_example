Summary: Plan Phase C smoke harness to run DataLoad through the bridge, stitch a Bragg tensor, and capture ROI diagnostics.
Mode: TDD
Focus: TORCH-BRIDGE-001 — Bridge DataLoad to nanobrag_torch
Branch: integration
Mapped tests: python -m pytest -v tests/dbex/test_nanobrag_smoke.py::TestSmokeHarness
Artifacts: plans/active/TORCH-BRIDGE-001/reports/2025-10-28T230500Z/{do-now-notes.md,pytest.log,smoke_metrics.json,roi_triptych.png}
Do Now:
1. TORCH-BRIDGE-001.C1 — Use plans/active/TORCH-BRIDGE-001/implementation.md Phase C to author smoke-harness pytest scaffolding that exercises DataLoad→bridge→stub simulator on the refGeom dataset; tests: python -m pytest -v tests/dbex/test_nanobrag_smoke.py::TestSmokeHarness::test_single_experiment_flow
2. TORCH-BRIDGE-001.C1 — Implement the single-experiment smoke harness to stitch per-panel tensors, compute masked MSE, and return metrics for one run; tests: python -m pytest -v tests/dbex/test_nanobrag_smoke.py::TestSmokeHarness::test_masked_mse_and_shapes
3. TORCH-BRIDGE-001.C2 — Persist ROI triptych artifacts plus metrics under plans/active/TORCH-BRIDGE-001/reports/2025-10-28T230500Z/ and update docs/fix_plan.md + plans/active/TORCH-BRIDGE-001/implementation.md; tests: none — process+docs
Priorities & Rationale:
- docs/spec-db-workflow.md:24-29 mandates stitched per-panel Bragg tensors and masked MSE, driving the smoke harness scope.
- docs/spec-db-core.md:32-56 requires the bridge outputs to align with `[panel, slow, fast]` arrays and apply `(background >= 0) ∧ trusted` loss masks.
- docs/config_crosswalk.md:86-95 documents ROI/background handling and artifact expectations, guiding triptych capture.
- docs/dials_api.md:10-28 covers bbox ordering we must honor when slicing ROIs for diagnostics.
- docs/nanobrag_api.md:21-83 details simulator config expectations and stitch semantics the harness must respect even with stubs.
How-To Map:
- export KMP_DUPLICATE_LIB_OK=TRUE and (if torch compile issues appear) NANOBRAGG_DISABLE_COMPILE=1 before running pytest.
- python -m pytest -v tests/dbex/test_nanobrag_smoke.py::TestSmokeHarness::test_single_experiment_flow | tee plans/active/TORCH-BRIDGE-001/reports/2025-10-28T230500Z/pytest.log
- python -m pytest -v tests/dbex/test_nanobrag_smoke.py::TestSmokeHarness::test_masked_mse_and_shapes | tee -a plans/active/TORCH-BRIDGE-001/reports/2025-10-28T230500Z/pytest.log
- python -m scripts/orchestration/stamp_handoff.py --focus TORCH-BRIDGE-001 --report plans/active/TORCH-BRIDGE-001/reports/2025-10-28T230500Z/ (optional for artifact stamping)
- Save smoke metrics to plans/active/TORCH-BRIDGE-001/reports/2025-10-28T230500Z/smoke_metrics.json and ROI triptych figure to roi_triptych.png via matplotlib.
Pitfalls To Avoid:
- Importing nanobrag_torch without guarding for its absence; keep stubs or skips for now.
- Forgetting `[panel, slow, fast]` ordering when stitching panel tensors back into the Bragg image.
- Omitting the `(background >= 0) & trusted` loss mask so masked MSE deviates from spec.
- Writing artifacts outside the documented reports directory or without timestamps.
- Letting pytest reuse cached DataLoad state that mutates global fixtures; reload per test.
- Skipping KMP_DUPLICATE_LIB_OK, which can crash torch imports in CI environments.
- Generating plots without labeling axes/units, making triptych artifacts ambiguous.
- Hardcoding absolute paths instead of repo-relative ones for dataset inputs.
- Allowing tests to depend on random global state (set seeds or deterministic outcomes).
- Leaving docs/fix_plan.md without updated Metrics/Artifacts lines after the run.
If Blocked: Capture the blocker (e.g., DataLoad loading error or missing torch install) in docs/fix_plan.md Attempts History with Metrics: pending and Artifacts pointing at plans/active/TORCH-BRIDGE-001/reports/2025-10-28T230500Z/blocker.log, mark status blocked, and note the condition plus dataset diagnostics.
Findings Applied (Mandatory):
- GEOMETRY-001 — Ensure the smoke harness keeps detector geometry and square-pixel guards intact when stitching outputs.
- CONFORMANCE-001 — Export KMP_DUPLICATE_LIB_OK=TRUE around pytest runs per acceptance guidance.
- RUNTIME-001 — Keep torch.compile disabled for grad-sensitive paths if we extend the harness with gradient checks.
