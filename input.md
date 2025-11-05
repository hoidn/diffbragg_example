Summary: Hand off Stage B shell-modifier LBFGS work with clear config, telemetry, and testing instructions.
Mode: none
Focus: TORCH-REFINE-004 — Stage B Fhkl modifiers (optional)
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers; tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion; tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip
Artifacts: plans/active/TORCH-REFINE-004/reports/2025-11-05T100554Z/

Do Now:
- TORCH-REFINE-004 — Stage B Fhkl modifiers (optional)
  - Implement: dbex/nanobrag_refinement.py::run_nanobrag_refinement — insert the Stage B shell-modifier LBFGS loop (config plumbing, shell lookup helper, telemetry/HDF5 persistence) while keeping Stage A/C behavior unchanged; update RefinementConfig/CLI wiring and add the Stage B smoke selector plus supporting docs/tests.
  - Validate: KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --maxfail=1
  - Artifacts: plans/active/TORCH-REFINE-004/reports/2025-11-05T100554Z/

How-To Map:
- export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers | tee plans/active/TORCH-REFINE-004/reports/2025-11-05T100554Z/collect_stage_b.log
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --maxfail=1 | tee plans/active/TORCH-REFINE-004/reports/2025-11-05T100554Z/pytest_stage_b_shell.log
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1 | tee plans/active/TORCH-REFINE-004/reports/2025-11-05T100554Z/pytest_stage_a_regression.log
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --maxfail=1 | tee plans/active/TORCH-REFINE-004/reports/2025-11-05T100554Z/pytest_stage_c_regression.log
- Capture Stage B telemetry/improvement snapshot (JSON or markdown) from `_write_torch_outputs` and drop under the same artifacts directory for traceability.

Pitfalls To Avoid:
- Do not modify or install packages (Environment Freeze); treat missing nanobrag_torch hooks as blockers.
- Keep Stage B interpolation gated on halo metadata; fail fast if `hkl_metadata["has_halo"]` is false.
- Maintain Stage A/C parameter states and telemetry; Stage B must not mutate `hkl_grid` globally or regress existing tests.
- Ensure shell modifiers stay positive (softplus/log-exp); no direct scaling of structure factors that violates SCALE-001/002.
- Track and surface any default_F fallback in Stage B telemetry; abort if fallback occurs.
- Persist new Stage B telemetry to HDF5 without breaking existing readers; keep stage labels stable.
- Collect pytest logs via `tee` into the artifacts directory to satisfy TESTING-003.
- Keep new helpers device/dtype neutral and avoid `.detach()`/`.cpu()` on values that influence the optimization path.
- Update docs (`docs/TESTING_GUIDE.md`, `docs/development/TEST_SUITE_INDEX.md`) once tests pass.
- Avoid editing external nanobrag_torch sources; wrap functionality inside dbex unless a documented patch is required.

If Blocked:
- If nanobrag_torch lacks hooks for modifier application or default_F telemetry, capture the failure signature, update docs/fix_plan.md Attempts History, mark the initiative blocked in galph_memory.md, and outline the missing API contract so we can escalate.

Findings Applied (Mandatory):
- REFINE-005 — Stage B must run only with halo-padded HKL grids and emit default_F telemetry/guards.
- SCALE-001 — Structure factors stay unscaled; shell modifiers must operate multiplicatively without duplicating spot_scale_override.
- SCALE-002 — Preserve global scale handling separate from Stage B modifiers to avoid double-scaling.
- SCALE-003 — Retain refined MTZ telemetry when Stage B runs so we can audit refined-vs-raw usage.
- SCALE-007 — Extend CLI/HDF5 telemetry to capture Stage B status alongside existing structure-factor metadata.

Pointers:
- docs/spec-db-workflow.md:31 — Stage B contract and interpolation guardrails.
- plans/nanobrag_integration_plan.md:226 — Stage B mode expectations (shell vs per-reflection).
- docs/architecture/pytorch_design.md:37 — Halo requirement and default_F fallback guard.
- docs/TESTING_GUIDE.md:113 — Stage B testing guardrail (halo + default_F checks).
- plans/active/TORCH-REFINE-004/implementation.md:1 — Detailed implementation phases for this initiative.

Next Up (optional):
- Outline per-reflection parity mode (TORCH-REFINE-005) once shell modifiers land.

Doc Sync Plan (Conditional):
- After Stage B selector passes, rerun `pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` for archival, then update `docs/TESTING_GUIDE.md` §4 and `docs/development/TEST_SUITE_INDEX.md` with selector status + artifact paths before marking the initiative done.

Mapped Tests Guardrail:
- Verify the new Stage B selector collects (>0 tests) before finishing; if collection drops to zero, restore the test or downgrade its status in docs/fix_plan.md before closing the loop.
