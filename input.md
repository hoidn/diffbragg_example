Summary: Capture Stage A vs Stage C panel-loss diagnostics so we can pinpoint the persistent +0.067 % chi² offset before touching physics/perf gates.
Mode: Parity
InitiativeType: perf
Focus: PERF-WARM-SIM-001 — Warm Simulator
Branch: integration
Mapped tests:
- pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
- pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
- pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full
- pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T223500Z/{panel_diag/,collect_stage_c_small.log,pytest_stage_c_small.log,telemetry_stage_c_small.json,collect_stage_c_full.log,pytest_stage_c_full.log,telemetry_stage_c_full.json,stage_c_warm_cache_report.json,panel_diag_compare_small.json,panel_diag_compare_full.json,summary.md}

Do Now:
- Implement: `dbex/refinement/stage_a_impl.py::_compute_panel_loss` (+ callers) to accept an optional diagnostics collector that records per-panel chi², mask, sigma, and target checksums whenever env var `DBEX_STAGE_C_PANEL_DIAG_DIR` is set; propagate the collector through `_build_stage_a_lbfgs_closure` and `_run_stage_a_lbfgs` so baseline/final panel validations emit `stage_a_panel_diag.json` under the env-provided directory.
- Implement: analogous diagnostics plumbing in `dbex/refinement/stage_c_impl.py::_build_stage_c_lbfgs_closure` and `_run_stage_c_lbfgs` so Stage C records its iteration-0/periodic/final panel metrics to `stage_c_panel_diag.json` whenever the env var is set (use the directory supplied per smoketest invocation).
- Implement: `plans/active/PERF-WARM-SIM-001/bin/compare_panel_diag.py` that ingests the Stage A/Stage C JSON files for a detector size, aligns entries by `panel_id`, reports chi² deltas (absolute + relative), and dumps both JSON and Markdown summary into the current report directory.
- Validate: rerun the Stage C detector microslip smoketests (small + full) with diagnostics enabled, run the existing warm-cache summarizer, and then run the new comparison script for each detector size so the artifacts clearly show where Stage C diverges.

How-To Map:
1. Stage A diagnostics plumbing  
   - In `dbex/refinement/stage_a_impl.py::_compute_panel_loss`, add an optional `panel_diag` parameter (list). When provided, fall back to per-panel `_compute_variance_weighted_loss` evaluations so you can append dicts `{panel_id, chi_squared, masked_pixels, mask_true_count, target_sum, sigma_sum}` before aggregating totals; keep the current stacked fast-path when diagnostics are `None`.  
   - Thread an env-gated collector (`DBEX_STAGE_C_PANEL_DIAG_DIR`) through `_build_stage_a_lbfgs_closure` so baseline/final (and forced) panel validations call the helper with `panel_diag`. Store the resulting metadata in `telemetry_state['panel_loss_diag']`, and inside `_run_stage_a_lbfgs` write one JSON per env directory (e.g., `<dir>/stage_a_panel_diag.json`) after Stage A finishes.
2. Stage C diagnostics plumbing  
   - Mirror the collector wiring in `dbex/refinement/stage_c_impl.py::_build_stage_c_lbfgs_closure` (capture iteration‑0 full validation plus periodic/final) and `_run_stage_c_lbfgs`. Each smoketest run will set `DBEX_STAGE_C_PANEL_DIAG_DIR` to a unique subdirectory (e.g., `.../panel_diag/small` and `.../panel_diag/full`), so Stage C can write `stage_c_panel_diag.json` beside Stage A’s file without needing dataset detection.
3. Comparison tool  
   - Author `plans/active/PERF-WARM-SIM-001/bin/compare_panel_diag.py` (T2 script) that accepts `--stage-a-json`, `--stage-c-json`, `--out-dir`, and optional `--label`. The script should load both JSON payloads, align entries by `panel_id`, compute absolute/relative chi² deltas plus mask/sigma checksum diffs, emit a machine-readable JSON summary (e.g., `panel_diag_compare_<label>.json`), and print/emit a Markdown snippet the summary.md can reference.
4. Test & analysis commands (run these from repo root; env var points at detector-specific subdirs):  
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_STAGE_C_PANEL_DIAG_DIR=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T223500Z/panel_diag/small pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T223500Z/collect_stage_c_small.log`  
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_STAGE_C_PANEL_DIAG_DIR=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T223500Z/panel_diag/small DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T223500Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T223500Z/pytest_stage_c_small.log`  
   - Repeat both commands with `--smoke-detector-size=full` and `DBEX_STAGE_C_PANEL_DIAG_DIR=.../panel_diag/full`, storing logs in the same report directory (rename files with `_full`).  
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md python plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_warm_cache.py --telemetry-small plans/active/PERF-WARM-SIM-001/reports/2025-12-01T223500Z/telemetry_stage_c_small.json --telemetry-full plans/active/PERF-WARM-SIM-001/reports/2025-12-01T223500Z/telemetry_stage_c_full.json --out-json plans/active/PERF-WARM-SIM-001/reports/2025-12-01T223500Z/stage_c_warm_cache_report.json`  
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md python plans/active/PERF-WARM-SIM-001/bin/compare_panel_diag.py --stage-a-json plans/active/PERF-WARM-SIM-001/reports/2025-12-01T223500Z/panel_diag/small/stage_a_panel_diag.json --stage-c-json plans/active/PERF-WARM-SIM-001/reports/2025-12-01T223500Z/panel_diag/small/stage_c_panel_diag.json --label small --out-dir plans/active/PERF-WARM-SIM-001/reports/2025-12-01T223500Z/`  
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md python plans/active/PERF-WARM-SIM-001/bin/compare_panel_diag.py --stage-a-json plans/active/PERF-WARM-SIM-001/reports/2025-12-01T223500Z/panel_diag/full/stage_a_panel_diag.json --stage-c-json plans/active/PERF-WARM-SIM-001/reports/2025-12-01T223500Z/panel_diag/full/stage_c_panel_diag.json --label full --out-dir plans/active/PERF-WARM-SIM-001/reports/2025-12-01T223500Z/`

Pitfalls To Avoid:
- Keep diagnostics opt-in: the helper must stay on the vectorized fast-path unless `DBEX_STAGE_C_PANEL_DIAG_DIR` is set, and the env var should never change default telemetry.
- Do not mutate shared tensors when collecting diagnostics—work on local slices so Stage A/Stage C caches remain reusable.
- Stage C still needs to respect REFINE-011/012 (panel validations when Stage B/C enabled); don’t gate diagnostics on ROI mode alone.
- Ensure JSON writers create directories (`mkdir(parents=True, exist_ok=True)`) and overwrite previous runs to avoid mixing detector sizes.
- Avoid large binary dumps—only store per-panel scalars/checksums, not raw images, to keep artifacts diffable.
- Keep Stage C best-snapshot logic untouched; diagnostics should not reset `distance_offset_raw` or interfere with LBFGS gradients.
- Do not relax any REFINE-007 acceptance gates; failures must remain visible in pytest output/telemetry.

If Blocked:
- Capture the failure signature (stack trace or telemetry mismatch) under `plans/active/PERF-WARM-SIM-001/reports/2025-12-01T223500Z/summary.md`, note whether Stage A/Stage C JSON files were produced, and log the block plus rationale in docs/fix_plan.md with this timestamp so we can decide on a spec-change vs. deeper instrumentation follow-up.

Findings Applied (Mandatory):
- REFINE-011 / REFINE-012 — Diagnostics must honor Stage A’s forced panel validations and ROI provenance.
- REFINE-013 — Best-snapshot telemetry depends on accurate panel-loss measurements; diagnostics can’t perturb those tensors.
- REFINE-016 — Trusted-mask gating must remain identical in the helper so panel-level metrics reflect Stage A parity.
- PERF-WARM-006 / PERF-WARM-013 — Warm-cache reuse and detector retargeting semantics can’t regress while instrumentation is added.
- DIAGNOSTICS-001 — New telemetry artifacts must live under the initiative report directory with clear provenance.

Pointers:
- docs/spec-db-workflow.md §62–75 — Canonical Stage A/B/C sequencing and validation scope rules.
- dbex/refinement/stage_a_impl.py:970-2100 — Stage A closure/telemetry helpers you’ll extend with diagnostics.
- dbex/refinement/stage_c_impl.py:300-980 — Stage C closure + runner where diagnostics need to be mirrored.
- plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_warm_cache.py — Existing warm-cache report the new JSONs should complement.

Next Up (optional):
1. Once per-panel diagnostics highlight the offending panels, prepare a follow-up loop to trace their mask/sigma provenance (likely via callchain analysis) before touching physics or gate tolerances.
