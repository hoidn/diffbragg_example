Summary: Use the new shared refinement context to shrink Stage B helper signatures so `_build_stage_b_lbfgs_closure` and `StageB.run` stop passing 11 loosely-typed arguments and still satisfy the Stage B smoketests.
Mode: none
InitiativeType: architecture
Focus: ARCH-STAGE-CONTEXT-001 — Stage Context + Engine Artifact Boundary
Branch: integration
Mapped tests:
- pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small
- pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke --smoke-detector-size=small
Artifacts: plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T020900Z/{collect_stage_b_shell.log,pytest_stage_b_shell.log,collect_stage_b_per_reflection.log,pytest_stage_b_per_reflection.log,summary.md}

Do Now:
- Implement: `dbex/refinement/stage_b_impl.py::_build_stage_b_lbfgs_closure` — add the `RefinementSharedContext` compatibility shim (reuse Stage A pattern) so config/device/dtype plus crystal/detector/beam/inputs/HKL/sigma-floor cache come from the dataclass when provided, compute target/loss/sigma tensors and panel geometry lazily, and keep a ValueError guard when the legacy parameters are missing.
- Implement: `dbex/refinement/stage_b.py::StageB.run` — build a `RefinementSharedContext` right after `sigma_floor_sq_cache` is created, stop materializing the target/loss/sigma tensors locally, and call `_build_stage_b_lbfgs_closure` with `shared_context=...` so only Stage-B-specific knobs (ROI samples, Stage A ctx, CPU fallback) are passed explicitly. Preserve the existing `context` hook for ASU metadata reuse.
- Validate: Re-run the small-detector Stage B smoketests for both shell and per-reflection modes, capturing `--collect-only` and full pytest logs into the artifact directory, and update `plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T020900Z/summary.md` with a short status + next steps.

How-To Map:
1. Edit Stage B helper: import `RefinementSharedContext` at the top of `dbex/refinement/stage_b_impl.py`, extend `_build_stage_b_lbfgs_closure(...)` with `shared_context: Optional[RefinementSharedContext] = None`, and inside the function branch exactly once: when `shared_context` exists, pull `config`, `device`, `dtype`, `crystal`, `detector`, `beam`, `inputs`, `hkl_grid`, `hkl_metadata`, and `sigma_floor_sq_cache` from it, convert `inputs.target/loss_mask/sigma_readout` to torch tensors on demand, and derive `n_panels`/`panel_shape` from the detector. When it is absent, keep the existing parameter requirements and raise `ValueError` if any legacy argument is missing.
2. Update StageB wrapper: in `dbex/refinement/stage_b.py`, import `RefinementSharedContext`, instantiate it via `.from_inputs(...)` after `sigma_floor_sq_cache = {}`, and pass only `shared_context=shared_context` (plus the Stage-B-specific args) to `_build_stage_b_lbfgs_closure`. Remove the manual `torch.from_numpy` conversions and the legacy `panel_shape` argument since the helper now computes them.
3. Collect-only (shell mode): `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T020900Z/collect_stage_b_shell.log`
4. Run shell smoketest: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T020900Z/telemetry_stage_b_shell.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T020900Z/pytest_stage_b_shell.log`
5. Collect-only (per-reflection): `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T020900Z/collect_stage_b_per_reflection.log`
6. Run per-reflection smoketest: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T020900Z/telemetry_stage_b_per_reflection.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T020900Z/pytest_stage_b_per_reflection.log`
7. Wrap up: append a short note (what changed, test status, remaining work) to `plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T020900Z/summary.md` so artifacts stay synchronized with the fix-plan entry.

Pitfalls To Avoid:
- Keep the legacy dict-based arguments working until Stage C and the CLI adopt the dataclass; raise a clear error only when neither path is supplied.
- Do not mutate `context.asu_map`/`context.halo_mask`; Stage B relies on `RefinementContext` for ASU reuse.
- CPU fallback (`use_stage_b_cpu_fallback`) must remain functional; the shared context should not force tensors back onto CUDA when we intentionally evaluate on CPU.
- Preserve REFINE-FLOW-001 telemetry fields (`stage_b_baseline_rel_diff`, `stage_b_baseline_diff_path`) by keeping the current telemetry dict intact.
- No environment changes—just Python edits and pytest.
- Leave `sigma_floor_sq_cache` as a shared dict so repeated tensor builds keep working; don’t replace it with a new object when constructing the dataclass.

If Blocked:
- If Stage B closure still sees missing attributes after the refactor, stop editing, capture the stack trace plus the parameters you attempted to pass, and log it in `plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T020900Z/blocked.md` before notifying Galph.
- If either smoketest fails with unrelated physics regressions, archive the failing logs in the artifact directory, annotate the failure in the summary file, and flag the focus as blocked in docs/fix_plan.md + galph_memory so we can reassess scope.

Findings Applied (Mandatory):
- ARCH-STAGE-CTX-001 (docs/findings.md:83) — This work directly addresses the Stage helper data-clump finding.
- ARCH-ENGINE-002 (docs/findings.md:80) — Stage wrappers must keep their RefinementStage protocol guarantees while adopting the new context.
- REFINE-FLOW-001 (docs/findings.md:71) — Baseline parity telemetry must remain untouched after the signature change.

Pointers:
- docs/fix_plan.md:86 — Initiative metadata and the updated Next Actions checklist.
- plans/active/ARCH-STAGE-CONTEXT-001/implementation.md:55 — Phase A checklist detailing the Stage B context task.
- docs/data_dependency_manifest.md:34 — Stage smoketest data sourcing and required env overrides for `refgeom_dataload`.
- tests/dbex/test_torch_refine_smoke.py:1276 — Stage B shell smoketest that must stay green.

Next Up (optional): Stage C needs the same shared-context refactor once Stage B is verified; keep notes on any shim gaps you spot while updating Stage B.
Doc Sync Plan: none — no new selectors or renamed tests this loop.
