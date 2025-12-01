Summary: Align Stage C variance-weighted loss with Stage A by AND-ing the trusted mask into both ROI-mode closures and panel validations, then prove the chi² delta disappears on the Stage C detector microslip smokes.
Mode: Parity
Focus: PERF-WARM-SIM-001 — Warm Simulator
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip [--smoke-detector-size=small], tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip [--smoke-detector-size=full]
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T214200Z/

Do Now:
- Implement: dbex/refinement/stage_c_impl.py::_build_stage_c_lbfgs_closure — pull `trusted_masks_t` from `StageAContext` (warm path) or tensorize `inputs.trusted_mask` (cold path) and intersect it with `loss_mask_t`/ROI slices before `_compute_variance_weighted_loss`, covering both ROI-mode closures and panel-mode validations without mutating the shared mask tensors in-place.
- Validate: tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip [small/full] with the usual Stage C smoke env flags, capture collect-only logs + pytest logs + telemetry JSON, then rerun `plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_warm_cache.py` so REFINE-007 evidence proves ≤0.05% chi² regression alongside the detector-offset reductions.
- Archive: Drop the new telemetry, summarizer output, and log files into `plans/active/PERF-WARM-SIM-001/reports/2025-12-01T214200Z/` next to trusted_mask_analysis.md.

How-To Map:
1. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T214200Z/collect_stage_c_small.log`
2. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T214200Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T214200Z/pytest_stage_c_small.log`
3. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T214200Z/collect_stage_c_full.log`
4. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T214200Z/telemetry_stage_c_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full | tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T214200Z/pytest_stage_c_full.log`
5. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md python plans/active/PERF-WARM-SIM-001/bin/summarize_stage_c_warm_cache.py --telemetry-small plans/active/PERF-WARM-SIM-001/reports/2025-12-01T214200Z/telemetry_stage_c_small.json --telemetry-full plans/active/PERF-WARM-SIM-001/reports/2025-12-01T214200Z/telemetry_stage_c_full.json --out-json plans/active/PERF-WARM-SIM-001/reports/2025-12-01T214200Z/stage_c_warm_cache_report.json`

Pitfalls To Avoid:
- Keep mask tensors boolean; use `torch.logical_and` on clones/slices so stage_a_ctx.trusted_masks_t stays immutable.
- Do not reintroduce ROI disabling or gate adjustments—Stage C must continue to use ROI-mode closures when Stage A telemetry says so.
- Ensure cold-path tensorization (`inputs.trusted_mask`) runs on the same device/dtype as the loss mask to avoid accidental CPU↔GPU copies.
- Guard for `stage_a_ctx.trusted_masks_t is None`; fall back to the tensorized trusted mask from inputs instead of skipping the gate.
- Maintain PHYSICS-LOSS invariants (variance floor / sigma tracking) and leave REFINE-007 acceptance thresholds unchanged.
- Avoid touching Environment/requirements; this is pure source + test work.
- Capture all artifacts under the new timestamped directory so docs/fix_plan references stay valid.
- Keep ROI/perf counters intact—no in-place mask mutation that could ripple back into telemetry.
- Run tests with `NANOBRAGG_DISABLE_COMPILE=1` and `KMP_DUPLICATE_LIB_OK=TRUE` as documented.

If Blocked:
- If Stage C still reports +0.05% chi² after the trusted-mask gate lands, save the fresh telemetry/logs in the artifacts directory, note the failure signature in docs/fix_plan.md Attempts History, and ping Galph with the log snippets plus any new hypotheses.

Findings Applied (Mandatory):
- REFINE-007 — Non-regression gate for Stage C must pass once the trusted-mask parity fix lands.
- REFINE-011/REFINE-012 — Keep panel-mode validations aligned with Stage A telemetry; this change only adjusts masking, not validation scope.
- REFINE-013 — Ensure best-snapshot telemetry still reflects the updated chi²; don’t bypass the existing rehydration logic.
- REFINE-015 — Preserve Stage A log-scale clamp behavior when wrapping the new mask gate around the loss computation.
- REFINE-016 — Stage C must apply the DIALS trusted mask before variance-weighted loss just like Stage A.

Pointers:
- docs/fix_plan.md:1277-1346 (PERF-WARM-SIM-001 status + trusted-mask parity Do Now)
- plans/active/PERF-WARM-SIM-001/reports/2025-12-01T214200Z/trusted_mask_analysis.md (mask mismatch evidence)
- dbex/refinement/stage_a_impl.py:1336-1365 (Stage A trusted-mask gate reference)
- dbex/refinement/stage_c_impl.py:512-593 (Stage C loss computation that needs the mask fix)

Next Up (optional): Investigate whether Stage C ROI sampling can regain performance once the masking parity fix proves chi² alignment, e.g., retuning ROI_sampling or validation cadence after gates are green.
