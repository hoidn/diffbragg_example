Summary: Finish Stage C detector microslip by adding the LBFGS loop, smoke test, and telemetry persistence while keeping Stage A stable.
Mode: none
Focus: TORCH-REFINE-003 — Stage C detector microslip
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip, tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
Artifacts: plans/active/TORCH-REFINE-003/reports/2025-11-06T130000Z/

Do Now:
- TORCH-REFINE-003
  - Implement: dbex/nanobrag_refinement.py::run_nanobrag_refinement — add the Stage C detector-distance LBFGS phase with bounded per-panel tensors, freeze Stage A params, emit stage "C" telemetry, and return the Stage C-adjusted Bragg tensor.
  - Implement: dbex/refine_one.py::_write_torch_outputs — persist multi-stage telemetry (Stage A + Stage C) in `/torch_diagnostics` without regressing existing attributes, storing per-stage loss traces and param deltas.
  - Implement: tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip — author deterministic detector perturbation smoke that enables Stage C, asserts ≥5% masked-MSE improvement, validates telemetry completeness, and guards Stage A regression via existing selector.
  - Implement: plans/active/TORCH-REFINE-003/bin/dump_stage_c_metrics.py — T2 script that reads the Stage A/C telemetry dict, accepts `--stage` (default \"C\"), and writes loss traces, per-panel offsets, and improvement % to JSON in the artifacts directory for reproducibility.
  - Validate: KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --maxfail=1 | tee plans/active/TORCH-REFINE-003/reports/2025-11-06T130000Z/pytest_stage_c.log
  - Validate: KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1 | tee plans/active/TORCH-REFINE-003/reports/2025-11-06T130000Z/pytest_stage_a.log
  - Artifacts: plans/active/TORCH-REFINE-003/reports/2025-11-06T130000Z/

How-To Map:
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
2. mkdir -p plans/active/TORCH-REFINE-003/reports/2025-11-06T130000Z
3. KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip | tee plans/active/TORCH-REFINE-003/reports/2025-11-06T130000Z/collect_stage_c.log
4. KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion | tee plans/active/TORCH-REFINE-003/reports/2025-11-06T130000Z/collect_stage_a.log
5. KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --maxfail=1 | tee plans/active/TORCH-REFINE-003/reports/2025-11-06T130000Z/pytest_stage_c.log
6. KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1 | tee plans/active/TORCH-REFINE-003/reports/2025-11-06T130000Z/pytest_stage_a.log
7. python plans/active/TORCH-REFINE-003/bin/dump_stage_c_metrics.py --telemetry-json plans/active/TORCH-REFINE-003/reports/2025-11-06T130000Z/telemetry_stage_c.json
8. python plans/active/TORCH-REFINE-003/bin/dump_stage_c_metrics.py --telemetry-json plans/active/TORCH-REFINE-003/reports/2025-11-06T130000Z/telemetry_stage_a.json --stage A

Pitfalls To Avoid:
- Do not mutate Stage A parameter tensors during Stage C; explicitly detach or clone before Stage C optimizer to maintain REFINE-001 guarantees.
- Keep detector distance offsets differentiable tensors and enforce tanh/clamp bounds so distances remain positive and within ±0.5 mm (GRADIENT-001).
- Preserve existing Stage A telemetry layout; Stage C additions must be additive (new group or JSON) without breaking current consumers.
- Ensure Stage C smoke uses deterministic detector perturbation (alternating ±offset) and records the exact offset magnitude in telemetry for audit.
- When writing telemetry to HDF5, respect Environment Freeze—no new dependencies; use JSON dumps for complex structures as done for Stage A.
- Avoid tightening the Stage A 0.2% gate when enabling Stage C; run the regression selector after Stage C changes to confirm stability.
- Capture collect-only logs before running tests so the mapped-test guardrail can be audited in artifacts.
- Keep ROI sampling and validation cadence consistent with Stage A (15%, every 5 iters) unless spec demands otherwise; document any deviations.

If Blocked:
- Preserve failing telemetry + loss traces via dump_stage_c_metrics.py into `plans/active/TORCH-REFINE-003/reports/2025-11-06T130000Z/blocked_stage_c.json`, note the failure signature in docs/fix_plan.md, and log the block with hypothesized fix in galph_memory.md before pivoting.

Findings Applied (Mandatory):
- REFINE-001 — Warm-start from Stage A and keep scale bounded; freeze Stage A tensors before Stage C to avoid scale explosions.
- REFINE-002 — Maintain Stage A nucleus gate (≥0.1–0.2%); Stage C builds on this baseline without loosening earlier acceptance thresholds.
- REFINE-005 — Respect haloed HKL interpolation toggles; do not disable the halo/NN safeguards when adding Stage C logic.
- REFINE-006 — Preserve the calibrated 0.2% Stage A gate; Stage C improvement must reference that baseline and achieve ≥5% additional recovery.
- GRADIENT-001 — No `.item()` or numpy casts on Stage C tensors; gradients must remain intact through detector overrides.

Pointers:
- docs/spec-db-workflow.md:35 — Stage C detector translation contract and ≥5% gate.
- plans/nanobrag_integration_plan.md:157 — Stage C LBFGS expectations and optimizer reuse.
- plans/active/TORCH-REFINE-003/implementation.md:45 — Phase checklist for microslip initiative.
- dbex/nanobrag_refinement.py:734 — Stage C TODO placeholder to replace with LBFGS loop.
- dbex/refine_one.py:364 — Telemetry handling that must persist Stage C output.
- tests/dbex/test_torch_refine_smoke.py:63 — Geometry perturbation helper enabling detector offsets.

Next Up (optional):
1. TORCH-REFINE-004 — Stage B |F| modifier scaffolding once Stage C smoke is green.

Doc Sync Plan:
- After Stage C selector passes, refresh `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` with the new smoke test, referencing collect-only and pytest logs under 2025-11-06T130000Z.

Mapped Tests Guardrail:
- Confirm `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` collects ≥1 test before implementation; if collection fails post-change, update docs/fix_plan.md instead of marking the initiative done.
