Summary: Move the Stage C baseline-detector prior ahead of LBFGS so the rehydrated best snapshot keeps the detector-offset corrections, then rerun the Stage C detector microslip smokes with telemetry + warm-cache summarizer.
Mode: Perf
Focus: PERF-WARM-SIM-001 — Warm Simulator
Branch: integration
Mapped tests:
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T190945Z/collect_stage_c_small.log
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T190945Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small \| tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T190945Z/pytest_stage_c_small.log
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full > plans/active/PERF-WARM-SIM-001/reports/2025-12-01T190945Z/collect_stage_c_full.log
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T190945Z/telemetry_stage_c_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=full \| tee plans/active/PERF-WARM-SIM-001/reports/2025-12-01T190945Z/pytest_stage_c_full.log
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T190945Z/
Do Now:
- Implement: dbex/refinement/stage_c_impl.py::_run_stage_c_lbfgs — call `_apply_baseline_detector_prior()` before `stage_c_optimizer.step(closure_stage_c)` (only once per run), drop the post-step invocation, and keep the REFINE-013 tuple refresh so the rehydrated best snapshot uses the warm-started detector offsets instead of the stale pre-prior tensors.
- Validate: Re-run `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` for `--smoke-detector-size=small` and `--smoke-detector-size=full` with telemetry capture + warm-cache summarizer to prove ≥80% detector-offset reduction and ≤0.05% chi² regression before filing the artifacts under the new report directory.
How-To Map:
1. In `dbex/refinement/stage_c_impl.py::_run_stage_c_lbfgs` (around lines 738-780), move the `_apply_baseline_detector_prior()` call so it executes immediately before `stage_c_optimizer.step(closure_stage_c)` and remove the existing post-step call; keep the helper’s early returns so we only warm-start when a baseline detector and non-zero `stage_c_max_distance_delta_mm` exist.
2. Leave the REFINE-013 tuple refresh code intact, but double-check that the rehydration path still reloads `telemetry_state['best_params_snapshot_c']` onto the correct device/dtype after LBFGS; no extra prior application should occur after rehydration.
3. Rebuild `distance_offset_raw` tensors only via `torch.tensor(..., device=device, dtype=dtype)` so gradients remain detached but on the right backend; do not convert to numpy lists outside the existing persistence hook.
4. Run the mapped collect-only + small smoketest commands (steps listed under Mapped tests) to ensure selector health and capture telemetry/logs under `plans/active/PERF-WARM-SIM-001/reports/2025-12-01T190945Z/`.
5. Repeat the collect-only + full-detector smoketest, again piping stdout to the artifact logs and pointing `DBEX_SMOKE_TELEMETRY_PATH` at the new telemetry filenames.
6. Execute the warm-cache summarizer script on the two telemetry files so the JSON/markdown report documents `cache_mode`, `roi_mode`, detector offset reductions, and chi² deltas for this run.
Pitfalls To Avoid:
- Do not relax the REFINE-007 chi²/offset thresholds; the code change must satisfy the existing gates.
- Keep `roi_mode`, `validation_scope`, and `roi_mode_reason` telemetry untouched to preserve REFINE-010/011/012 evidence.
- Ensure `_apply_baseline_detector_prior()` still runs at most once per Stage C invocation; no repeated warm starts mid-optimizer.
- Preserve device/dtype neutrality (torch.float32 on the configured device) when reloading tensors from telemetry_state.
- Leave `_record_stage_telemetry` in the smoketest before assertions so failing runs still emit JSON.
- Capture collect-only logs before each smoketest to comply with selector health tracking.
- Don’t edit Stage A ROI heuristics or Stage C closure sampling—only the prior ordering is in scope.
- Keep `NANOBRAGG_DISABLE_COMPILE=1` and `KMP_DUPLICATE_LIB_OK=TRUE` in all smoketest commands for determinism.
- Avoid touching unrelated findings or gate thresholds; this is a targeted implementation fix.
If Blocked:
- Stop after the first failing smoketest, save the pytest log + telemetry under the artifact directory, note the failure signature in docs/fix_plan.md Attempts History, and tell Galph the focus remains blocked pending a new diagnosis.
Findings Applied (Mandatory):
- REFINE-007 — chi² regression must stay ≤0.05% with ≥80% detector-offset reduction; rerun smokes to prove it after the prior reorder.
- REFINE-010 — Stage A’s ROI auto-panel toggle continues to dictate closure vs validation mode; the change must not override its telemetry.
- REFINE-011 — When Stage B/C run, Stage C validations stay panel-scope; confirm `validation_scope="panel"` is unchanged after the fix.
- REFINE-012 — Maintain `roi_mode_reason` provenance so tooling can audit why ROI closures were (not) active.
- REFINE-013 — Persisted best tuples must be reloaded after LBFGS; this change ensures the baseline prior ordering doesn’t wipe them out.
Pointers:
- docs/fix_plan.md:190945 — Latest PERF-WARM-SIM-001 plan describing the baseline-prior ordering fix and validation commands.
- dbex/refinement/stage_c_impl.py:738 — `_run_stage_c_lbfgs` block where the prior call currently lives after LBFGS.
- tests/dbex/test_torch_refine_smoke.py:954 — Stage C detector microslip smoketest enforcing REFINE-007/011/012.
Next Up (optional):
- If the reordered prior still fails REFINE-007, capture per-iteration chi² traces via the warm-cache summarizer to decide whether LBFGS tolerances need adjustment in a follow-on loop.
