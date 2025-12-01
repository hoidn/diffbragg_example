Summary: Auto-disable Stage A ROI sampling for the 29-ROI refGeom_small smoke so Stage C sees the real chi² drop without weakening REFINE-007.
Mode: none
Focus: ARCH-REFINE-001 — Refinement Engine Modularization & Torch IO
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small; tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T105916Z/
Do Now:
- Implement: dbex/refinement/stage_a_impl.py::_build_stage_a_params — add a documented `stage_a_min_roi_for_roi_mode` threshold (default 32) that flips Stage A, Stage B, and Stage C into panel mode when `len(panel_slices)` is tiny so telemetry/perf counters and downstream stages agree on `roi_mode`; thread the knob through dbex/nanobrag_refinement.py::RefinementConfig and refresh tests/dbex/test_torch_refine_smoke.py expectations for the small-detector path.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T105916Z/telemetry_stage_bc_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T105916Z/pytest_stage_bc_small.log
How-To Map:
1. Extend `RefinementConfig` in dbex/nanobrag_refinement.py with `stage_a_min_roi_for_roi_mode` (default 32) and keep the existing `stage_a_force_panel_validation` knobs; expose it everywhere StageA is constructed so callers don’t need to hardcode heuristics.
2. Inside `_build_stage_a_params` (and the analogous helper in dbex/nanobrag_refinement.py), compute `canonical_roi_count = len(panel_slices)` and set `use_stage_a_roi_mode=False` when `canonical_roi_count <= stage_a_min_roi_for_roi_mode`; include a note in Stage A telemetry/perf counters so logs explain whether panel mode was forced.
3. Propagate the auto-panel flag through the Stage B/Stage C wrappers and the smoke tests: Stage B/S C perf counters should now look at telemetry (`telemetry_a.roi_mode`) instead of raw config flags, and tests must assert that small-detector runs switch to panel mode while canonical/full runs still respect ROI mode.
4. Export `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md` and run a `--collect-only` sanity check before the full smokes: `DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py -k "test_stage_b_shell_modifiers or test_stage_c_detector_microslip" --smoke-detector-size=small | tee plans/active/ARCH-REFINE-001/reports/2025-12-01T105916Z/collect_stage_bc_small.log`, then rerun the full selector command above so telemetry/logs land under this loop’s report directory.
Pitfalls To Avoid:
- Don’t “fix” tests by toggling `config.enable_stage_a_roi_mode`; the auto-switch must be driven by Stage A code so telemetry remains authoritative.
- Keep Stage A perf counters (`roi_mode`, `roi_count_*`, cache metadata) consistent between telemetry and the per-stage perf dicts; Stage B/C assertions read both.
- Preserve warm-cache behavior: disabling ROI mode should still reuse StageAContext detectors/masks instead of rebuilding per iteration.
- When stage count ≤ threshold, make sure sampled ROI counts report the canonical totals (so dashboards don’t show 0 sampled ROIs).
- Stage C and Stage B wrappers should branch on Stage A telemetry, not their own heuristics—otherwise ROI label drift will resurface.
- Zero tolerance for ENV churn: if missing sigma-map assets resurface, stop and log the blocker in docs/fix_plan.md instead of regenerating silently.
- Capture telemetry JSON + pytest logs for both selectors; we need the proof that Stage A now improves ≥0.1%.
If Blocked:
- If Stage A still reports 0% improvement after the auto-panel switch, rerun `plans/active/ARCH-REFINE-001/bin/capture_stage_c_stage_a_probe.py` with `--stage-a-roi-mode panel` and attach the JSON/logs to docs/fix_plan.md while marking ARCH-REFINE-001 blocked with the new failure signature.
Findings Applied (Mandatory):
- REFINE-007 — Stage C must compare against Stage A’s real chi²; auto-panel ROI switching restores that invariant without weakening gates.
- PERF-WARM-008 — Stage B/C perf counters must mirror Stage A’s ROI mode, so the telemetry wiring has to update alongside the config knob.
- REFINE-010 — Newly documented requirement that refGeom_small (≤32 ROIs) runs need panel-mode closures to converge; this Do Now implements that policy.
Pointers:
- docs/spec-db-workflow.md:116 — Stage smoke policy and ROI-minibatching clause that permits panel fallbacks when full-image descent is required.
- docs/data_dependency_manifest.md:52 — Notes refGeom_small has exactly 29 ROIs/sigma crops, justifying the ≤32 heuristic.
- plans/active/ARCH-REFINE-001/reports/2025-12-01T105500Z/stage_c_stage_a_probe_cli.json:1 — Shows Stage A ROI-mode improvement=0.0% despite healthy detector recovery when Stage C runs.
Next Up (optional): If time remains after the smokes, rerun the metadata-sigma variant of `test_stage_c_detector_microslip` to ensure the new policy still holds when `DBEX_SMOKE_SIGMA_SOURCE=metadata`.
