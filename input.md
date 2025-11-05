Summary: Align Stage B refinement with the bridge helpers so the shell-modifier smoke test can run to completion and emit telemetry.
Mode: none
Focus: TORCH-REFINE-004 — Stage B Fhkl modifiers (optional)
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers; tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion; tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip
Artifacts: plans/active/TORCH-REFINE-004/reports/2025-11-05T164800Z/

Do Now:
- TORCH-REFINE-004 — Stage B Fhkl modifiers (optional)
  - Implement: dbex/nanobrag_refinement.py::run_nanobrag_refinement — refactor the Stage B shell-modifier block to reuse `create_detector_config`/`create_beam_config` exactly as Stage A does (pass trusted_mask, drop unsupported device/dtype kwargs, instantiate Simulator via Detector/Crystal models) so the loop can finish, update `bragg_full` with the shell-adjusted result, and surface Stage B telemetry without breaking Stage A/C behavior.
  - Validate: KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --maxfail=1
  - Artifacts: plans/active/TORCH-REFINE-004/reports/2025-11-05T164800Z/

How-To Map:
- export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers | tee plans/active/TORCH-REFINE-004/reports/2025-11-05T164800Z/collect_stage_b.log
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --maxfail=1 | tee plans/active/TORCH-REFINE-004/reports/2025-11-05T164800Z/pytest_stage_b.log
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1 | tee plans/active/TORCH-REFINE-004/reports/2025-11-05T164800Z/pytest_stage_a_regression.log
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --maxfail=1 | tee plans/active/TORCH-REFINE-004/reports/2025-11-05T164800Z/pytest_stage_c_regression.log

Pitfalls To Avoid:
- Do not pass unsupported kwargs (device/dtype) to bridge helpers; mirror Stage A calls exactly.
- Keep Stage B interpolation gated on `hkl_metadata["has_halo"]`; fail fast rather than falling back to default_F.
- Leave Stage A/C parameter tensors and telemetry untouched; Stage B must not mutate shared state inline.
- Preserve SCALE-001/002 separation: shell modifiers adjust |F|, global scale stays in Stage A.
- Ensure Stage B updates clone the HKL grid per evaluation and avoid in-place edits that leak across iterations.
- Reuse trusted_mask when creating DetectorConfig so masks stay deterministic.
- Guard for NaN/Inf gradients before persisting telemetry; surface errors via `telemetry_b.message` rather than silent failures.
- Capture pytest output with `tee` to satisfy TESTING-003 logging expectations.
- Do not tweak environment/packages; treat missing nanobrag_torch features as blockers to record in the ledger.

If Blocked:
- Capture the exact stack trace (e.g., TypeError from bridge helpers or nanobrag_torch gaps), append it to docs/fix_plan.md Attempts History, mark the initiative `blocked`, and note follow-up requirements in galph_memory.md before exiting.

Findings Applied (Mandatory):
- REFINE-005 — Maintain halo-only Stage B execution and keep the interpolation guard active.
- SCALE-001 — Structure factors remain unscaled; shell modifiers operate multiplicatively without duplicating spot scales.
- SCALE-002 — Preserve Stage A global scale handling so Stage B does not double-apply intensity factors.
- SCALE-003 — Retain refined hkl telemetry propagation when Stage B runs.
- SCALE-007 — Ensure Stage B does not regress refined MTZ enforcement or telemetry attributes in `_write_torch_outputs`.

Pointers:
- docs/spec-db-workflow.md:31 — Stage B contract and interpolation requirement.
- plans/nanobrag_integration_plan.md:226 — Stage B mode expectations (shell vs parity).
- docs/architecture/pytorch_design.md:37 — Halo requirement and default_F guard for Stage B.
- docs/TESTING_GUIDE.md:113 — Stage B test guardrails (halo + default_F checks).
- docs/fix_plan.md:106 — Latest Stage B attempt log capturing the bridge mismatch and artifacts for this loop.

Next Up (optional):
- Evaluate whether the ≥3% improvement gate is realistic once the loop runs; capture measured improvement and update the ledger if recalibration is needed.
