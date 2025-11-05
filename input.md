Summary: Calibrate Stage C detector microslip gate to the measured 0.002% ceiling and align smoke test + telemetry messaging.
Mode: none
Focus: TORCH-REFINE-003 — Stage C detector microslip
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip
Artifacts: plans/active/TORCH-REFINE-003/reports/2025-11-05T090201Z/

Do Now:
- Implement: dbex/nanobrag_refinement.py::RefinementConfig; tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip — lower `stage_c_min_loss_improvement` to 2e-5 (0.002%) per REFINE-007, update early-stop messaging, and relax the smoke assertion while preserving telemetry coverage references.
- Validate: KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --maxfail=1
- Artifacts: Save `pytest_stage_c.log` under plans/active/TORCH-REFINE-003/reports/2025-11-05T090201Z/

How-To Map:
- export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip | tee plans/active/TORCH-REFINE-003/reports/2025-11-05T090201Z/collect_stage_c.log
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --maxfail=1 | tee plans/active/TORCH-REFINE-003/reports/2025-11-05T090201Z/pytest_stage_c.log
- python plans/active/TORCH-REFINE-003/bin/probe_stage_c_improvement.py --output plans/active/TORCH-REFINE-003/reports/2025-11-05T090201Z/stage_c_improvement_probe.json (rerun only if telemetry drifts)

Pitfalls To Avoid:
- Do not modify environment packages (Environment Freeze policy).
- Keep nanobrag tensor operations device/dtype neutral; no `.cpu()` in the optimization path.
- Preserve Stage A defaults and regression gates while touching Stage C config.
- Retain telemetry JSON structure and Stage labels when adjusting messages.
- Keep Stage C test deterministic (same perturbation helper, no randomness).
- Ensure new thresholds reference REFINE-007 and existing artifacts; avoid magic numbers without rationale.
- Do not relax improvement gate below measured ceiling without logging rationale in docs/fix_plan.md.
- Capture all pytest logs in artifacts path using tee (guardrail from docs/TESTING_GUIDE.md).
- Avoid editing shipped nanobrag_torch sources (external dependency).
- Keep doc updates in sync with fix_plan and findings ledger.

If Blocked:
- Log failure signature and rationale in docs/fix_plan.md Attempts History, update galph_memory.md state to `blocked`, and pivot to TORCH-REFINE-002D per dependency ordering.

Findings Applied (Mandatory):
- REFINE-001 — Warm-start scale guard already in place; ensure untouched.
- REFINE-006 — Respect calibrated Stage A 0.2% gate while updating Stage C defaults.
- REFINE-007 — Stage C gate capped at ≈0.003% per improvement probe; use 2e-5 threshold and cite metrics artifact.

Pointers:
- docs/spec-db-workflow.md:35 — Stage staging requirements and Stage C scope.
- plans/active/TORCH-REFINE-003/implementation.md — Updated working plan with 0.002% gate.
- plans/active/TORCH-REFINE-003/reports/2025-11-05T090201Z/stage_c_improvement_probe.json — Empirical ceiling data for Stage C.
- docs/findings.md:40 — REFINE-007 entry documenting calibrated gate.

Next Up (optional):
- Assess detector rotation perturbations once translation gate stabilizes.

Doc Sync Plan (Conditional):
- None (no new tests added or renamed).

Mapped Tests Guardrail:
- Confirm selector collects via `pytest --collect-only`; if collection count drops to zero, restore Stage C test before finishing.
