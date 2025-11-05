Summary: Hand off a ready-to-implement plan to repair Stage B’s ROI sampler so the shell-modifier LBFGS loop runs and emits telemetry.
Mode: none
Focus: TORCH-REFINE-004 — Stage B Fhkl modifiers (optional)
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers
Artifacts: plans/active/TORCH-REFINE-004/reports/2025-11-05T172937Z/

Do Now:
- TORCH-REFINE-004 — Stage B Fhkl modifiers (optional)
  - Implement: dbex/nanobrag_refinement.py::run_nanobrag_refinement — refactor the Stage B ROI sampler/closure so it reuses the Stage A `sampled_panel_ids`, falls back to a full panel sweep when the sample list is empty, and restores Stage B telemetry/improvement gating without mutating Stage A/C tensors.
  - Validate: KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --maxfail=1
  - Artifacts: plans/active/TORCH-REFINE-004/reports/2025-11-05T172937Z/

How-To Map:
- export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers | tee plans/active/TORCH-REFINE-004/reports/2025-11-05T172937Z/collect_stage_b.log
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --maxfail=1 | tee plans/active/TORCH-REFINE-004/reports/2025-11-05T172937Z/pytest_stage_b.log

Pitfalls To Avoid:
- Reuse Stage A’s deterministic ROI sample (`sampled_panel_ids`) and add a clear fallback to all panels so telemetry never shows zero sampled ROIs.
- Do not mutate Stage A or Stage C tensors/telemetry in place; Stage B must work on copies and leave earlier stages intact.
- Keep the halo + interpolation guard active (hkl_metadata["has_halo"]=True, config.enable_hkl_interpolation=True) and fail fast if violated (REFINE-005).
- Preserve shell modifier parameterization (softplus + clamp) and guard against NaN/Inf gradients before persisting telemetry.
- Write Stage B’s Bragg result into a fresh buffer to avoid leaking modifiers back into Stage A snapshots.
- Emit informative telemetry messages for both success and early-stop cases so the ≥3% gate is auditable.
- Maintain SCALE-001/002 separation: shell modifiers adjust |F| only; global scale stays in Stage A.
- Capture collect/test logs via `tee` under the artifacts directory to satisfy TESTING-003.

If Blocked:
- Record the exact exception (e.g., NameError/RuntimeError from Stage B closure) and sampled ROI state in docs/fix_plan.md Attempts History, mark the initiative `blocked`, and note follow-up requirements in galph_memory.md before exiting.

Findings Applied (Mandatory):
- REFINE-005 — Stage B remains halo-only with interpolation enabled; enforce guards before running LBFGS.
- RUNTIME-001 — Set NANOBRAGG_DISABLE_COMPILE=1 around torch LBFGS runs to avoid compile-time interference.
- CONFORMANCE-001 — Export KMP_DUPLICATE_LIB_OK=TRUE and archive pytest logs per selector policy.
- SCALE-001 — Keep shell modifiers multiplicative without duplicating DiffBragg spot scales.

Pointers:
- docs/spec-db-workflow.md:31 — Stage B shell-modifier contract and halo requirement.
- plans/nanobrag_integration_plan.md:226 — Stage B implementation expectations (shell mode).
- docs/architecture/pytorch_design.md:39 — Halo/default_F guardrail for Stage B interpolation.
- plans/active/TORCH-REFINE-004/implementation.md:1 — Current Stage B working plan checklist.
- plans/active/TORCH-REFINE-004/reports/2025-11-05T164800Z/pytest_stage_b_v2.log — Failure log showing the `roi_sampler` NameError.

Next Up (optional):
- Calibrate the observed Stage B improvement vs the ≥3% gate once the sampler bug is fixed and capture telemetry JSON for docs sync.
