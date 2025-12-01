Summary: Rebuild Stage C’s warm-cache simulator path so detector retargeting actually changes the Bragg tensors and the +0.067 % χ² regression disappears under REFINE-007.
Mode: Parity
InitiativeType: perf
Focus: PERF-WARM-SIM-001 — Warm Simulator
Branch: integration
Mapped tests:
- pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
- pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
- pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full
- pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T230800Z/{panel_diag/,collect_stage_c_small.log,pytest_stage_c_small.log,telemetry_stage_c_small.json,collect_stage_c_full.log,pytest_stage_c_full.log,telemetry_stage_c_full.json,stage_c_warm_cache_report.json,panel_diag_compare_small.{json,md},panel_diag_compare_full.{json,md},summary.md}

Do Now:
- Implement: update `dbex/refinement/stage_c_impl.py::_retarget_stage_a_detectors` so each detector delta rebuilds the nanobrag `Simulator` (per panel and any ROI-entry simulators) after the new distance is applied. Reuse Stage A’s cached beam config/HKL tensors, keep distance deltas as tensors (GRADIENT-004), and ensure `_retarget_stage_a_simulators` still reattaches the warmed crystal so closures stay warm-cache friendly.
- Validate: rerun `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` for both detector sizes with diagnostics enabled (same env knobs as last loop) and capture collect-only logs, pytest logs, and telemetry JSONs under the new artifact directory.
- Analyze: re-run `plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_warm_cache.py` plus `compare_panel_diag.py` for small and full detectors so the panel-delta summaries prove χ² parity (≤0.05 % regression) while detector-offset telemetry still shows ≥99.999 % reductions.

How-To Map:
1. Warm-cache simulator rebuild  
   - In `_retarget_stage_a_detectors`, after computing `new_distance_mm` instantiate a fresh nanobrag `Detector` and pass it to a newly created `Simulator` (mirror the constructor in `_build_stage_a_context` using `stage_a_ctx.beam_config`, the warmed crystal/HKL tensors, `device`, and `dtype`). Replace `stage_a_ctx.simulators[pid]` with the new simulator and update any `roi_entries` simulators whose `panel_id` matches; continue storing the detector model in `stage_a_ctx.detector_models`.  
   - Keep tensor arithmetic (no `.item()`), respect existing guards (device/dtype, panel bounds), and finish by calling `_retarget_stage_a_simulators` as before so the shared crystal stays in sync.
2. Smoketest execution (repo root)  
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_STAGE_C_PANEL_DIAG_DIR=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T230800Z/panel_diag/small pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T230800Z/collect_stage_c_small.log`  
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_STAGE_C_PANEL_DIAG_DIR=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T230800Z/panel_diag/small DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T230800Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T230800Z/pytest_stage_c_small.log`  
   - Repeat both commands with `--smoke-detector-size=full` and `DBEX_STAGE_C_PANEL_DIAG_DIR=.../panel_diag/full`, writing `collect_stage_c_full.log` and `pytest_stage_c_full.log`.
3. Telemetry + diagnostics post-processing  
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md python plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_warm_cache.py --telemetry-small plans/active/PERF-WARM-SIM-001/reports/2025-12-01T230800Z/telemetry_stage_c_small.json --telemetry-full plans/active/PERF-WARM-SIM-001/reports/2025-12-01T230800Z/telemetry_stage_c_full.json --out-json plans/active/PERF-WARM-SIM-001/reports/2025-12-01T230800Z/stage_c_warm_cache_report.json`  
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md python plans/active/PERF-WARM-SIM-001/bin/compare_panel_diag.py --stage-a-json plans/active/PERF-WARM-SIM-001/reports/2025-12-01T230800Z/panel_diag/small/stage_a_panel_diag.json --stage-c-json plans/active/PERF-WARM-SIM-001/reports/2025-12-01T230800Z/panel_diag/small/stage_c_panel_diag.json --label small --out-dir plans/active/PERF-WARM-SIM-001/reports/2025-12-01T230800Z/`  
   - Repeat compare command with `panel_diag/full/...` to generate the full-detector summary.

Pitfalls To Avoid:
- Rebuilding simulators must keep tensors on the same device/dtype to avoid reallocations and gradient detaches (GRADIENT-004); never call `.item()` on the delta tensors.
- Update ROI-entry simulators together with per-panel simulators so ROI closures and panel validations read identical geometry.
- Do not disable warm cache globally—only adjust the retarget helper; Stage A/Stage C perf counters must still report `cache_mode="warm"`.
- Preserve REFINE-011/012 behavior: full validations still force panel mode, and ROI mode remains controlled by Stage A telemetry.
- Leave Stage C best-snapshot and telemetry plumbing untouched; the only functional change is how detectors are patched.
- Keep REFINE-007 gate thresholds intact; if Stage C still regresses, capture exact telemetry before marking blocked.

If Blocked:
- Write the failure signature and current detector-distance telemetry to `plans/active/PERF-WARM-SIM-001/reports/2025-12-01T230800Z/summary.md`, update docs/fix_plan.md with the timestamped block reason, and note whether warm-cache still ignored the rebuilt simulators so we can escalate to a spec-change or deeper callchain loop.

Findings Applied (Mandatory):
- REFINE-007 — Stage C must not increase χ² by >0.05 % once detector offsets collapse; validation reruns enforce this gate.
- REFINE-011 / REFINE-012 — Panel validations stay in sync with Stage A telemetry while ROI mode remains provenance-tracked.
- REFINE-013 — Best snapshot persistence relies on accurate full validations; simulator rebuilds cannot disrupt the tuple flow.
- REFINE-016 — Trusted-mask parity in `_compute_panel_loss` must keep working after simulator replacement.
- GRADIENT-004 — Distance deltas must remain differentiable tensors through the retarget+optimizer path.

Pointers:
- dbex/refinement/stage_c_impl.py:1-110, 440-520, 612-704 — Detector retarget helper, warm-cache closure, and simulator wiring you’ll modify.
- dbex/refinement/stage_a_impl.py:300-420 — Stage A context construction (reference for simulator instantiation and stored metadata).
- docs/spec-db-workflow.md §§62‑75 — Stage B/C sequencing and REFINE-007/011/012 guardrails.
- plans/active/PERF-WARM-SIM-001/reports/2025-12-01T223500Z/ — Previous diagnostics showing uniform χ² deltas and offset telemetry.
