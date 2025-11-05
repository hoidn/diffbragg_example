Summary: Restore Stage B shell-modifier telemetry (ROI counts + full-loss validations) so the smoke test can enforce the ≥3% gate with real data.
Mode: none
Focus: TORCH-REFINE-004 — Stage B Fhkl modifiers (optional)
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers
Artifacts: plans/active/TORCH-REFINE-004/reports/2025-11-05T190344Z/

Do Now:
- TORCH-REFINE-004 — Stage B Fhkl modifiers (optional)
  - Implement: dbex/nanobrag_refinement.py::run_nanobrag_refinement — repair the Stage B ROI sampler/full-validation loop so it reuses Stage A sampled panels (with full fallback), appends at least one full-loss validation + best-snapshot restore, updates roi_count_sampled from the actual panel list, and recomputes the ≥3% improvement gate from Stage A’s final loss (document if the measured ceiling forces recalibration).
  - Implement: tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers — tighten assertions around Stage B telemetry (roi_count_sampled >= 1, full-loss trace present) and, if the measured improvement remains <3%, rebase the gate + assertion to the observed ceiling with artifact references.
  - Validate: KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --maxfail=1 | tee $ARTIFACTS/pytest_stage_b_fix.log
  - Artifacts: plans/active/TORCH-REFINE-004/reports/2025-11-05T190344Z/

How-To Map:
- export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
- export ARTIFACTS=plans/active/TORCH-REFINE-004/reports/2025-11-05T190344Z
- mkdir -p "$ARTIFACTS"
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers | tee "$ARTIFACTS/collect_stage_b.log"
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --maxfail=1 --capture=tee-sys | tee "$ARTIFACTS/pytest_stage_b_fix.log"
- rg "Stage [AB] (final|improvement)" "$ARTIFACTS/pytest_stage_b_fix.log" | tee "$ARTIFACTS/stage_b_metrics.txt"
- printf "Stage B improvement gate evidence recorded in %s\\n" "$ARTIFACTS/stage_b_metrics.txt" >> "$ARTIFACTS/summary.md"

Pitfalls To Avoid:
- Respect Environment Freeze: no conda/pip installs; treat missing torch deps as blockers and record them.
- Keep Stage B tensor ops device/dtype neutral (float32 CPU path) and do not hard-code panel counts.
- Do not regress REFINE-005: Stage B must error if halo/interpolation prerequisites fail; keep guards intact.
- Clamp shell modifiers after softplus so gradients remain stable; avoid in-place ops that break autograd snapshots.
- Ensure LBFGS full-loss validations run under `torch.no_grad()` to avoid graph capture; keep NANOBRAGG_DISABLE_COMPILE=1 for determinism.
- When adjusting thresholds, cite measured improvement and archive artifacts before changing constants/tests.

If Blocked:
- Capture the failing command, stack trace, and the partial telemetry in $ARTIFACTS/blocker.log, set the fix-plan item to blocked with rationale, and log the next retry condition in galph_memory.md before exiting.

Findings Applied (Mandatory):
- REFINE-005 — Stage B requires halo grids + interpolation; maintain guards while adjusting telemetry.
- REFINE-006 — Stage A gate stays at ≥0.2%; reuse Stage A baseline loss when computing Stage B improvement.
- SCALE-001/002 — Shell modifiers must not rescale structure factors globally; keep multiplicative per-shell semantics.
- RUNTIME-001 — Disable torch.compile (NANOBRAGG_DISABLE_COMPILE=1) to avoid graph capture with LBFGS closures.

Pointers:
- dbex/nanobrag_refinement.py:900 — Stage B LBFGS closure + telemetry path to be fixed.
- tests/dbex/test_torch_refine_smoke.py:604 — Stage B smoke acceptance criteria and gate assertions.
- docs/spec-db-workflow.md:31 — Stage B contract across staging phases.
- plans/nanobrag_integration_plan.md:226 — Shell modifier requirements and telemetry expectations.
- docs/findings.md:6 — REFINE-005/006 guardrails informing ROI sampling and gate calibration.

Next Up (optional):
- Once Stage B gate stabilizes, draft a metrics script under plans/active/TORCH-REFINE-004/bin to chart Stage B improvement versus shell count.

Doc Sync Plan (Conditional):
- None — selectors unchanged; update docs only if gate recalibration introduces new findings.
