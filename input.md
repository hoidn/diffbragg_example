Summary: Rebuild the Stage A warm-cache simulators whenever `_retarget_stage_a_detectors` applies distance deltas so Stage C finally evaluates the updated geometry (≤0.05% χ² regression) while retaining the existing autograd + ROI telemetry wiring.
Mode: Perf
InitiativeType: perf
Focus: PERF-WARM-SIM-001 — Warm Simulator
Branch: integration
Mapped tests:
- pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
- pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
- pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full
- pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T235900Z/{collect_stage_c_small.log,pytest_stage_c_small.log,telemetry_stage_c_small.json,collect_stage_c_full.log,pytest_stage_c_full.log,telemetry_stage_c_full.json,panel_diag/small/stage_{a,c}_panel_diag.json,panel_diag/full/stage_{a,c}_panel_diag.json,stage_c_warm_cache_report.json,panel_diag_compare_small.{json,md},panel_diag_compare_full.{json,md},summary.md}

Do Now:
- Implement: `dbex/refinement/stage_c_impl.py::_retarget_stage_a_detectors` — when Stage C passes `distance_deltas_mm`, rebuild each affected panel’s Detector *and* cached `Simulator` using `stage_a_ctx.detector_configs[pid]`, `stage_a_ctx.simulators[pid].crystal`, and `stage_a_ctx.beam_config`, then replace `stage_a_ctx.simulators[pid]` so warm-cache closures and `_retarget_stage_a_simulators` operate on fresh instances. Preserve GRADIENT-004 by keeping tensor math (no `.item()` on deltas) and continue updating `stage_a_ctx.detector_models`.
- Implement: `dbex/refinement/stage_a_impl.py::StageAROIEntry` usage — if `stage_a_ctx.roi_entries` exists, refresh each ROI detector/simulator pair when its panel receives a delta (reuse the entry’s bbox/config, but update `detector_model.config.distance_mm` and instantiate a new ROI `Simulator`). This keeps Stage B/C ROI-mode closures in sync with the panel geometry.
- Validate: Re-run `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` for both detector sizes with diagnostics enabled to prove χ² regression ≤0.05% and detector-offset reduction ≥99.999%. Capture collect-only logs, pytest logs, telemetry JSON, panel diagnostics, the warm-cache summary JSON, and the Stage A vs Stage C panel comparison reports under the artifact path above.

How-To Map:
1. Stage C code updates — edit `dbex/refinement/stage_c_impl.py` per above (no CLI command; ensure `_retarget_stage_a_detectors` rebuilds simulators and ROI entries while keeping tensor-valued distances).
2. Collect-only (small) — `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T235900Z/collect_stage_c_small.log`
3. Stage C small run + diagnostics — `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T235900Z/telemetry_stage_c_small.json DBEX_STAGE_C_PANEL_DIAG_DIR=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T235900Z/panel_diag/small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T235900Z/pytest_stage_c_small.log`
4. Collect-only (full) — `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T235900Z/collect_stage_c_full.log`
5. Stage C full run + diagnostics — `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T235900Z/telemetry_stage_c_full.json DBEX_STAGE_C_PANEL_DIAG_DIR=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T235900Z/panel_diag/full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T235900Z/pytest_stage_c_full.log`
6. Warm-cache summary — `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md python plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_warm_cache.py --telemetry-small plans/active/PERF-WARM-SIM-001/reports/2025-12-01T235900Z/telemetry_stage_c_small.json --telemetry-full plans/active/PERF-WARM-SIM-001/reports/2025-12-01T235900Z/telemetry_stage_c_full.json --out-json plans/active/PERF-WARM-SIM-001/reports/2025-12-01T235900Z/stage_c_warm_cache_report.json`
7. Panel diagnostics comparison —
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md python plans/active/PERF-WARM-SIM-001/bin/compare_panel_diag.py --stage-a-json plans/active/PERF-WARM-SIM-001/reports/2025-12-01T235900Z/panel_diag/small/stage_a_panel_diag.json --stage-c-json plans/active/PERF-WARM-SIM-001/reports/2025-12-01T235900Z/panel_diag/small/stage_c_panel_diag.json --label small --out-dir plans/active/PERF-WARM-SIM-001/reports/2025-12-01T235900Z/`
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md python plans/active/PERF-WARM-SIM-001/bin/compare_panel_diag.py --stage-a-json plans/active/PERF-WARM-SIM-001/reports/2025-12-01T235900Z/panel_diag/full/stage_a_panel_diag.json --stage-c-json plans/active/PERF-WARM-SIM-001/reports/2025-12-01T235900Z/panel_diag/full/stage_c_panel_diag.json --label full --out-dir plans/active/PERF-WARM-SIM-001/reports/2025-12-01T235900Z/`

Pitfalls To Avoid:
- Do not call `.item()` on the distance tensors (GRADIENT-004) or mutate shared configs in ways that detach Stage C’s autograd graph.
- Keep ROI-mode provenance (`roi_mode_reason`) and Stage C perf counters intact; retargeting must not reset telemetry state or clobber `stage_a_ctx.trusted_masks_t`.
- When rebuilding simulators, reuse the existing crystal pointer so `_retarget_stage_a_simulators` can reattach Stage A’s final crystal without recreating HKL tensors.
- Ensure diagnostics directories contain both Stage A and Stage C JSON files per detector size before running `compare_panel_diag.py`; missing files should be treated as a block, not ignored.
- Respect Environment Freeze: no package installs or simulator dependency upgrades while editing Stage C helpers.
- Keep ROI caches optional—guard against `stage_a_ctx.roi_entries is None` so Stage B cold paths don’t crash.

If Blocked:
- If rebuilding simulators exposes a latent dependency (e.g., Simulator constructor requires additional metadata) capture the full traceback and current `distance_deltas_mm` payload in `plans/active/PERF-WARM-SIM-001/reports/2025-12-01T235900Z/blocked.md`, leave the code untouched, and update docs/fix_plan.md + galph_memory.md with the new blocker.
- If either smoketest still reports >0.05% χ² regression after simulator rebuild, archive the new telemetry + panel diagnostics and stop; note the failure signature in the same blocked.md so the supervisor can reclassify the initiative (do not relax REFINE-007 thresholds).

Findings Applied (Mandatory):
- GRADIENT-004 — warm-cache retargeting must keep tensor-valued distance offsets; rebuilding simulators must not introduce `.item()` conversions.
- REFINE-011/012 — Stage C panel validations must measure the same population as Stage A; updated detectors/simulators must preserve force-panel validation + ROI-mode provenance.
- REFINE-016 — Trusted-mask parity stays mandatory; simulator rebuild must not drop `stage_a_ctx.trusted_masks_t` or ROI slicing guards.
- PERF-WARM-013 — Stage A context owns the canonical simulator cache; retarget helpers are the only place we mutate detector geometry and must keep Stage A/B/C telemetry consistent.

Pointers:
- dbex/refinement/stage_c_impl.py:41 — `_retarget_stage_a_detectors` scaffolding to extend with simulator rebuild.
- docs/fix_plan.md:1462 — Phase D.4 warm-cache simulator rebuild plan + validation expectations.
- plans/active/PERF-WARM-SIM-001/bin/compare_panel_diag.py — required diagnostics alignment CLI for this loop.

Next Up (optional):
- If χ² parity lands, run `summarize_stage_c_warm_cache.py` with historical logs to document the perf delta and decide whether PERF-WARM-SIM-001 can advance to Stage B retargeting.
