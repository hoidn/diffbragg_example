Summary: Repair the Stage C warm-cache retargeter so detector distance tensors stay connected to autograd and the small-detector smoke can finish.
Mode: none
Focus: ARCH-REFINE-001 — Refinement Engine Modularization & Torch IO
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small; tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T112335Z/
Do Now:
- Implement: dbex/refinement/stage_c_impl.py::{_retarget_stage_a_detectors,_run_stage_c_lbfgs} — keep the warm-cache detector retargeting differentiable by propagating `distance_offset_raw` tensors (no `.item()` conversions) through both the closure path and the final reconstruction so Stage C warm-mode gradients mirror the cold path.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T112335Z/telemetry_stage_bc_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T112335Z/pytest_stage_bc_small.log
How-To Map:
1. Confirm the failure signature: `rg -n "distance_deltas_mm" dbex/refinement/stage_c_impl.py` shows `_retarget_stage_a_detectors` converting tensors to floats, and `plans/active/ARCH-REFINE-001/reports/2025-12-01T105916Z/pytest_stage_bc_small_v3.log` captures the `element 0 of tensors does not require grad` error for reference.
2. Update `_retarget_stage_a_detectors` so each offset stays on the Stage C device/dtype (wrap `stage_a_ctx.baseline_distance_mm[pid]` with `torch.tensor(..., device=device, dtype=dtype)` and add the tensor delta). Ensure both the cache mutation loop and the warm-cache panel loop inside `_run_stage_c_lbfgs` reuse that tensor helper so the final Bragg rebuild mirrors the closure path.
3. After editing, run `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T112335Z/telemetry_stage_bc_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T112335Z/pytest_stage_bc_small.log` and verify Stage C now reports `status != "error"` with a ≥0.002% chi² drop; Stage B should continue to pass.
4. If gradients still fail, archive the new telemetry JSON + pytest log under this loop’s artifacts and log the signature in docs/fix_plan.md before marking the item blocked.
Pitfalls To Avoid:
- Do not fall back to the cold path; PERF-WARM-006 requires Stage C to reuse Stage A caches.
- Avoid `.item()`, `.detach()`, or `torch.no_grad()` in the Stage C closure per GRADIENT-001; the tensor fix must keep the graph intact.
- Keep tensors on the configured device/dtype (CUDA vs CPU) to avoid device mismatch crashes.
- Remember to retarget both the closure path and `_run_stage_c_lbfgs` final reconstruction so telemetry/Bragg arrays stay in sync.
- Preserve telemetry/perf counters (cache_mode, roi_mode, roi_counts) so REFINE-010 and PERF-WARM-006 assertions stay valid.
If Blocked:
- If Stage C still reports `status="error"`, archive the latest Stage B/C logs + telemetry under this loop’s artifacts and document the new failure signature in docs/fix_plan.md before switching focus.
Findings Applied (Mandatory):
- REFINE-010 — Small-detector runs SHALL use panel closures, so Stage C must honor that while keeping gradients.
- PERF-WARM-006 — Stage C must reuse Stage A warm caches and continue emitting `cache_mode="warm"` telemetry.
- GRADIENT-001 — Optimization code must avoid `.item()`/`.detach()` on differentiable tensors.
- GRADIENT-004 — Newly logged requirement: Stage C detector retargeting must preserve tensor offsets so LBFGS can run in warm mode.
Pointers:
- docs/spec-db-workflow.md:81 — Stage C normative scope (per-panel detector offsets with tricubic interpolation and L-BFGS).
- docs/TESTING_GUIDE.md:48 — Canonical Stage B/C smoke selectors and required env vars.
- docs/data_dependency_manifest.md:52 — refGeom_small ROI count (29) that forces the auto-panel path exercised here.
- dbex/refinement/stage_c_impl.py:39 — Warm-cache retargeter currently calling `.item()` on detector offsets.
Next Up (optional): After Stage C passes on the CLI sigma path, rerun the metadata-sigma variant (`DBEX_SMOKE_SIGMA_SOURCE=metadata`) to ensure the fix is source-agnostic.
