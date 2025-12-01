Summary: Unify Stage A and Stage C panel-mode loss logic so Stage C reuses the canonical helper and stops adding a +0.067 % chi² bias before detector offsets adjust.
Mode: Parity
Focus: PERF-WARM-SIM-001 — Warm Simulator
Branch: integration
Mapped tests:
- pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
- pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
- pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full
- pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T221500Z/{collect_stage_c_small.log,pytest_stage_c_small.log,telemetry_stage_c_small.json,collect_stage_c_full.log,pytest_stage_c_full.log,telemetry_stage_c_full.json,stage_c_warm_cache_report.json,summary.md}

Do Now:
- Implement: dbex/refinement/stage_a_impl.py::_compute_panel_loss helper (refactor the current panel branch out of `compute_loss`) and dbex/refinement/stage_c_impl.py::_build_stage_c_lbfgs_closure (panel path) so Stage C calls the same helper and measures the identical panel population as Stage A before any detector offsets apply.
- Validate: tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip for both detector sizes with telemetry capture plus `plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_warm_cache.py` on the resulting telemetry JSON to confirm chi² parity and warm-cache metrics.

How-To Map:
1. Stage A helper refactor
   - Move the panel-mode block of `compute_loss` (starting near dbex/refinement/stage_a_impl.py:1450) into a new private helper (e.g., `_compute_panel_loss_from_context`) that accepts StageAContext, detector/beam/crystal inputs, log_scale clamp, target/loss/sigma tensors, sigma-floor tensor, and panel IDs. Return `(chi_squared_loss, masked_mse_loss, masked_pixels, clamped_pixels)` so existing telemetry counters stay intact. Update `compute_loss` to call the helper instead of duplicating the logic.
2. Stage C reuse
   - In dbex/refinement/stage_c_impl.py::_build_stage_c_lbfgs_closure, keep the ROI branch as-is but replace the panel-mode branch (currently stacking tensors manually) with a call to the new helper right after retargeting detectors and building `crystal_model`. Pass the same StageAContext, detector, beam, log_scale clamp, sigma tensors, etc., so Stage C’s initial/full validations use the canonical Stage A code path. Ensure cold-path execution still instantiates detectors when `stage_a_ctx` is None.
3. Regression suite
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T221500Z/collect_stage_c_small.log`
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T221500Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T221500Z/pytest_stage_c_small.log`
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T221500Z/collect_stage_c_full.log`
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T221500Z/telemetry_stage_c_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T221500Z/pytest_stage_c_full.log`
4. Warm-cache summarizer
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md python plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_warm_cache.py --telemetry-small plans/active/PERF-WARM-SIM-001/reports/2025-12-01T221500Z/telemetry_stage_c_small.json --telemetry-full plans/active/PERF-WARM-SIM-001/reports/2025-12-01T221500Z/telemetry_stage_c_full.json --out-json plans/active/PERF-WARM-SIM-001/reports/2025-12-01T221500Z/stage_c_warm_cache_report.json`

Pitfalls To Avoid:
- Don’t duplicate trusted-mask logic; the helper must apply the same `torch.logical_and` Stage A already uses and Stage C must not add another pass.
- Preserve warm-cache reuse (no re-instantiation of detectors/simulators when `stage_a_ctx` exists) to avoid perf regressions and stale ROI metadata.
- Keep Stage C ROI-mode closure untouched; only the panel-mode branch should change.
- Ensure the helper handles both warm and cold paths; cold path should continue tensorizing `inputs.trusted_mask` on the correct device/dtype once.
- Maintain variance-floor telemetry updates (clamped/masked pixel counts) so Stage C reports don’t regress.
- Don’t relax REFINE-007 tolerances; the goal is to eliminate the 0.067 % bias, not hide it.
- Avoid in-place modification of shared tensors (`loss_mask_t`, `trusted_masks_t`, `sigma_readout_t`); always work on local views.
- Keep Stage C best-snapshot logic intact—only the loss computation should change.

If Blocked:
- Capture the precise failure/signature in `plans/active/PERF-WARM-SIM-001/reports/2025-12-01T221500Z/summary.md`, including the pytest log snippet and telemetry deltas, then note the block with timestamp + rationale in docs/fix_plan.md Attempts History (PERF-WARM-SIM-001) so we can decide whether deeper instrumentation or spec tweaks are required.

Findings Applied:
- REFINE-007 — Stage C must not regress Stage A chi² by >0.05% on canonical runs; matching the panel-loss helper enforces that acceptance gate.
- REFINE-011/REFINE-012 — Stage C validations must mirror Stage A validation scope/ROI semantics; reusing the helper ensures validation scope stays in sync.
- REFINE-013 — Best-snapshot telemetry relies on accurate loss measurements; aligning the panel helper avoids skewing chi²_best.
- REFINE-016 — Trusted-mask parity was already implemented; the shared helper must keep the same boolean gating.
- PERF-WARM-006/013 — Warm cache reuse and detector retargeting semantics must stay unchanged when the helper is extracted.

Pointers:
- docs/spec-db-workflow.md:62 — Stage C shall evaluate the same canonical loss population as Stage A before detector offsets apply.
- dbex/refinement/stage_a_impl.py:1450 — Current panel-mode loss block to extract into a helper.
- dbex/refinement/stage_c_impl.py:512 — Panel-mode branch that should call the shared helper after detector retargeting.
- docs/TESTING_GUIDE.md:12 — Canonical env knobs for Stage C smoketests (DBEX_SMOKE_* and AUTHORITATIVE_CMDS_DOC).

Next Up (optional):
1. If parity refactor succeeds quickly, add a per-panel chi² telemetry dump in Stage C to capture future baseline drift regressions.
