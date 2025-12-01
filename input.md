Summary: Switch Stage A’s baseline/final validations to panel mode whenever Stage C runs (or ROI count is tiny) so the Stage C gate sees the real chi² improvement.
Mode: Parity
Focus: ARCH-REFINE-001 — Refinement Engine Modularization & Torch IO
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T103325Z/
Do Now:
- Implement: dbex/refinement/stage_a.py::StageA.run — plumb a `stage_a_force_panel_validation` flag (auto-enable when `config.enable_stage_c` or ROI count ≤32) through `_build_stage_a_lbfgs_closure`/`_run_stage_a_lbfgs` so baseline, periodic, and final validations call the panel path even while closures keep ROI sampling. Update `RefinementConfig` with the new knobs and ensure Stage A telemetry still records ROI counters plus the panel-level chi².
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T103325Z/pytest_stage_c_small_fix.log
How-To Map:
1. Edit `dbex/nanobrag_refinement.py` to add `stage_a_force_panel_validation` / `stage_a_panel_validation_roi_threshold` to `RefinementConfig`, defaulting to False/32. When `config.enable_stage_c` is True, set the flag before wiring the engine; otherwise rely on the ROI-count heuristic inside StageA.
2. In `dbex/refinement/stage_a.py`, compute `canonical_roi_count = len(refinement_inputs.panel_slices)`, derive `force_panel_validation = config.stage_a_force_panel_validation or config.enable_stage_c or canonical_roi_count <= config.stage_a_panel_validation_roi_threshold`, stash it on `stage_a_context`, and pass the boolean into `_run_stage_a_lbfgs`.
3. Update `dbex/refinement/stage_a_impl.py` so `_build_stage_a_lbfgs_closure`’s `compute_loss` accepts `force_panel_eval=False`, skipping the ROI branch when True, and so periodic validations set the flag. `_run_stage_a_lbfgs` should pass `force_panel_eval=True` for baseline/final/exception evaluations when the new boolean is set.
4. AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T103325Z/collect_stage_c_small_fix.log, then run the full selector command above capturing stdout/telemetry.
Pitfalls To Avoid:
- Do not relax Stage C’s REFINE-007 assertions; the goal is to fix Stage A telemetry, not weaken gates.
- Keep ROI-mode closures intact for perf—only baseline/full validations should flip to panel mode.
- Ensure telemetry still reports ROI counters/labels so Stage B tooling and perf dashboards stay consistent.
- Preserve variance-floor accounting when forcing panel mode; the clamped-pixel stats feed PHYSICS-LOSS-001.
- Update both StageA (engine path) and any inline Stage A callers so they share the new behavior; avoid duplicating heuristics in multiple places.
- Re-run pytest with `DBEX_SMOKE_SIGMA_SOURCE=cli_override`; mismatched sigma sources invalidate the repro data.
If Blocked:
- If panel-mode validations explode GPU memory, fall back to CPU for the validation pass (mirroring Stage B) and log the OOM signature in docs/fix_plan.md plus galph_memory.md before deferring the fix.
Findings Applied (Mandatory):
- REFINE-007 — Stage C telemetry gates require Stage A to provide the same chi² surface; enforcing panel-mode validations honors the detector-offset spec.
- PHYSICS-LOSS-001 — Dual chi²/masked-MSE traces must remain intact when we switch validation scope.
- docs/spec-db-workflow.md §Stage Smoke Dataset Policy — Small-detector smokes (29 ROIs) must still demonstrate Stage A improvement; forcing panel validation keeps the smoke harness meaningful.
Pointers:
- dbex/refinement/stage_a_impl.py:1100 — ROI vs panel compute paths and variance-floor tracking.
- dbex/refinement/stage_a.py:190 — StageA.run() orchestration where we can inject the validation flag.
- docs/data_dependency_manifest.md §Cropped Sigma-Map Asset — Confirms the small-detector ROI count (29) and why the ≤32 heuristic is justified.
Next Up (optional): After the panel-validation hook lands, rerun the combined Stage B/C selector to ensure Stage B still reads the Stage A telemetry correctly.
