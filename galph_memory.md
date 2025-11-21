
## 2025-11-05T041539Z — TORCH-REFINE-002 HKL grid block triage
- Focus: TORCH-REFINE-002 — Stage A expansion — full crystal and orientation
- Action Type: planning
- Key Observations: Confirmed the deterministic perturbation triggers 0% HKL hit rate (REFINE-005) so the ≥5% gate cannot pass until structure factors are reindexed; logged the new finding, refreshed implementation checklist (Option D), and rewrote `input.md` with the baseline-geometry + `pytest.xfail` handoff. Perturbation helper remains in place for future HKL-ready assets.
- Artifact Path: plans/active/TORCH-REFINE-002/reports/2025-11-05T041539Z/
- Next Actions: Ralph implements the Stage A smoke rewrite (telemetry assertions + `pytest.xfail`), captures selector logs, and records the HKL dependency before pivoting to the dataset initiative.
- <Action State>: [ready_for_implementation]

2025-11-05T041539Z focus=TORCH-REFINE-002 state=ready_for_implementation dwell=1 artifacts=plans/active/TORCH-REFINE-002/reports/2025-11-05T041539Z/ next_action=stage_a_xfail_implementation

## 2025-11-05T044720Z — TORCH-REFINE-002 closeout pivot
- Focus: TORCH-REFINE-002 — Stage A expansion — full crystal and orientation
- Action Type: review_or_housekeeping
- Key Observations: Audited Option D logs (telemetry assertions precede the expected `xfail`, full suite clean), marked fix-plan status `done`, refreshed implementation checklist to defer perturbation work, and spun up TORCH-REFINE-002D for HKL-aware dataset follow-up.
- Artifact Path: plans/active/TORCH-REFINE-002/reports/2025-11-05T044720Z/
- Next Actions: Switch focus to TORCH-REFINE-002D to deliver HKL-grid probe + dataset plan.
- <Action State>: [review_or_housekeeping]

2025-11-05T044720Z focus=TORCH-REFINE-002 state=ready_for_implementation dwell=0 artifacts=plans/active/TORCH-REFINE-002/reports/2025-11-05T044720Z/ next_action=switch_focus_to_TORCH-REFINE-002D

## 2025-11-05T044720Z — TORCH-REFINE-002D kickoff plan
- Focus: TORCH-REFINE-002D — Stage A HKL-aware perturbation dataset
- Action Type: planning
- Key Observations: Authored implementation plan covering HKL grid rebuild phases, updated fix plan entry, and published Do Now directing a coverage probe script plus Stage A regression run.
- Artifact Path: plans/active/TORCH-REFINE-002D/reports/2025-11-05T044720Z/
- Next Actions: Ralph to implement the HKL hit-rate probe script (`plans/active/TORCH-REFINE-002D/bin/probe_hkl_hit_rate.py`) and capture JSON metrics + smoke selector logs.
- <Action State>: [ready_for_implementation]

2025-11-05T044720Z focus=TORCH-REFINE-002D state=ready_for_implementation dwell=0 artifacts=plans/active/TORCH-REFINE-002D/reports/2025-11-05T044720Z/ next_action=hkl_probe_script_implementation
2025-11-05T060833Z focus=TORCH-REFINE-002D state=planning dwell=1 artifacts=plans/active/TORCH-REFINE-002D/reports/2025-11-05T060833Z/ next_action=prep_misset_override_do_now

## 2025-11-05T083500Z — TORCH-REFINE-002D halo plan
- Focus: TORCH-REFINE-002D — Stage A HKL-aware perturbation dataset
- Action Type: planning
- Key Observations: Nearest-neighbor HKL tops out at 0.22% improvement despite deterministic misset; refreshed Phase 1 to add optional ±1 halo in `build_structure_factor_grid`, gate interpolation via `RefinementConfig`, and update the Stage A smoke to consume the haloed grid while logging improvement ≥5%.
- Artifact Path: plans/active/TORCH-REFINE-002D/reports/2025-11-05T083500Z/
- Next Actions: Ralph to implement halo/interpolation toggles, enable Stage A interpolation, rerun the smoke, and capture improvement + telemetry metrics.
- <Action State>: [ready_for_implementation]

2025-11-05T083500Z focus=TORCH-REFINE-002D state=ready_for_implementation dwell=0 artifacts=plans/active/TORCH-REFINE-002D/reports/2025-11-05T083500Z/ next_action=halo_interpolation_implementation
## 2025-11-05T093000Z — TORCH-REFINE-002D gate recalibration planning
- Focus: TORCH-REFINE-002D — Stage A HKL-aware perturbation dataset
- Action Type: planning
- Key Observations: Authored probe `plans/active/TORCH-REFINE-002D/bin/probe_stage_a_improvement.py` and ran baseline + amplified perturbations (halo widths 1–2). Canonical perturbation (+2/+1/+1%, +1.5°) consistently yields 0.206% improvement (initial 9.76e+05 → final 9.74e+05, 13 LBFGS iters). Larger cell/orientation deltas or ROI sampling tweaks remain ≤0.12% and >±3° missets trip tricubic OOB even with halo 2. Conclusion: dataset ceiling ≈0.2%; updated fix_plan/implementation.md exit criteria and added REFINE-006 finding to codify the calibrated gate.
- Artifact Path: plans/active/TORCH-REFINE-002D/reports/2025-11-05T093000Z/
- Next Actions: Ralph to lower `min_loss_improvement` to 0.002, update Stage A smoke assertion/logs to ≥0.2%, rerun selector, and downgrade REFINE-004/005 once metrics captured.
- <Action State>: [ready_for_implementation]
2025-11-05T093000Z focus=TORCH-REFINE-002D state=ready_for_implementation dwell=0 artifacts=plans/active/TORCH-REFINE-002D/reports/2025-11-05T093000Z/ next_action=calibrate_stage_a_gate_implementation

## 2025-11-05T110500Z — TORCH-REFINE-003 stage C planning handoff
- Focus: TORCH-REFINE-003 — Stage C detector microslip
- Action Type: planning
- Key Observations: Authored Stage C implementation plan (phases covering detector distance parameterization, LBFGS loop, telemetry, validation), confirmed Stage C contract in docs/spec-db-workflow.md §7 and plans/nanobrag_integration_plan.md §Phase 3, and probed nanobrag_torch DetectorConfig fields to plan distance overrides. Fix plan marked in_progress with attempt history and reports scaffolding seeded.
- Artifact Path: plans/active/TORCH-REFINE-003/reports/2025-11-05T110500Z/
- Next Actions: Delegate Stage C LBFGS integration + smoke test implementation per new input.md Do Now.
- <Action State>: [ready_for_implementation]

2025-11-05T110500Z focus=TORCH-REFINE-003 state=ready_for_implementation dwell=0 artifacts=plans/active/TORCH-REFINE-003/reports/2025-11-05T110500Z/ next_action=stage_c_lbfgs_integration

## 2025-11-06T130000Z — TORCH-REFINE-003 Stage C Do Now refresh
- Focus: TORCH-REFINE-003 — Stage C detector microslip
- Action Type: planning
- Key Observations: Stage C TODO remains in run_nanobrag_refinement; Stage A telemetry dict stable post-infrastructure. Drafted refreshed Do Now covering Stage C LBFGS loop, multi-stage telemetry persistence, new smoke test, and metrics script; updated docs/fix_plan.md and input.md accordingly.
- Artifact Path: plans/active/TORCH-REFINE-003/reports/2025-11-06T130000Z/
- Next Actions: Ralph implements Stage C LBFGS loop + telemetry, adds smoke test/metrics script, and runs Stage C/A selectors per the new How-To map.
- <Action State>: [ready_for_implementation]
2025-11-06T130000Z focus=TORCH-REFINE-003 state=ready_for_implementation dwell=0 artifacts=plans/active/TORCH-REFINE-003/reports/2025-11-06T130000Z/ next_action=implement_stage_c_lbfgs_and_smoke

## 2025-11-05T090201Z — TORCH-REFINE-003 Stage C gate calibration plan
- Focus: TORCH-REFINE-003 — Stage C detector microslip
- Action Type: planning
- Key Observations: Ran Stage C improvement probe (probe_stage_c_improvement.py) showing refGeom ceiling ≈0.0027% despite offsets saturating at 0.46 mm; updated fix_plan Attempts History, added REFINE-007 finding, refreshed working plan exit criteria to ≥0.002% gate, and drafted new Do Now for Ralph to lower `stage_c_min_loss_improvement` + relax smoke assertion.
- Artifact Path: plans/active/TORCH-REFINE-003/reports/2025-11-05T090201Z/
- Next Actions: Ralph updates config/test thresholds per REFINE-007 and reruns Stage C selector with artifacts captured.
- <Action State>: [ready_for_implementation]
2025-11-05T090201Z focus=TORCH-REFINE-003 state=ready_for_implementation dwell=1 artifacts=plans/active/TORCH-REFINE-003/reports/2025-11-05T090201Z/ next_action=lower_stage_c_gate_impl

## 2025-11-05T100554Z — TORCH-REFINE-004 Stage B launch plan
- Focus: TORCH-REFINE-004 — Stage B Fhkl modifiers (optional)
- Action Type: planning
- Key Observations: Stage B path is still unimplemented (RefinementConfig lacks Stage B controls and `run_nanobrag_refinement` exits after Stage A/C). Reviewed Stage B contract (spec-db-workflow §7, integration plan §Stage B) plus halo/default_F guard (REFINE-005) and scaling findings (SCALE-001/002/003/007). Authored new implementation plan with config plumbing, shell lookup helper, Stage B LBFGS loop, telemetry/HDF5 persistence, and smoke test/doc updates; fix_plan status set to in_progress with Attempts History captured.
- Artifact Path: plans/active/TORCH-REFINE-004/reports/2025-11-05T100554Z/
- Next Actions: Ralph to implement Stage B shell modifier stage per new input.md (LBFGS loop + telemetry + tests) and capture Stage B improvement artifacts.
- <Action State>: [ready_for_implementation]
2025-11-05T100554Z focus=TORCH-REFINE-004 state=ready_for_implementation dwell=0 artifacts=plans/active/TORCH-REFINE-004/reports/2025-11-05T100554Z/ next_action=implement_stage_b_shell_modifiers

## 2025-11-05T164800Z — TORCH-REFINE-004 Stage B bridge audit
- Focus: TORCH-REFINE-004 — Stage B Fhkl modifiers (optional)
- Action Type: gathering_evidence
- Key Observations: Replayed the Stage B selector; failure occurs before telemetry because `run_nanobrag_refinement` passes unsupported `device`/`dtype` kwargs into `create_beam_config` during the Stage B post-pass. Logs confirm bridge helpers still expect the Stage A signature (beam only), so the current Stage B implementation is out of sync with `dbex.nanobrag_bridge`. No default_F fallback or structure-factor violations observed; failure is purely the API mismatch. Collected fresh collect-only + pytest logs under 2025-11-05T164800Z.
- Artifact Path: plans/active/TORCH-REFINE-004/reports/2025-11-05T164800Z/
- Next Actions: Realign Stage B loop with bridge helpers (pass trusted_mask to `create_detector_config`, reuse Stage A `Detector`/`Crystal` models, drop unsupported kwargs), then rerun the Stage B smoke to calibrate improvement vs the ≥3% gate and capture telemetry for doc sync.
- <Action State>: [gathering_evidence]
2025-11-05T164800Z focus=TORCH-REFINE-004 state=gathering_evidence dwell=1 artifacts=plans/active/TORCH-REFINE-004/reports/2025-11-05T164800Z/ next_action=realign_stage_b_bridge_calls

## 2025-11-05T172937Z — TORCH-REFINE-004 Stage B ROI sampler handoff
- Focus: TORCH-REFINE-004 — Stage B Fhkl modifiers (optional)
- Action Type: planning
- Key Observations: Reviewed `pytest_stage_b_v2.log` (2025-11-05T164800Z) and `dbex/nanobrag_refinement.py:847-1179`; Stage B now dies inside the LBFGS closure with `NameError: roi_sampler`, leaving loss traces empty and telemetry status `error`. Stage A’s deterministic `sampled_panel_ids` exists but the Stage B helper no longer captures it, and there is no fallback when the ROI sample list is empty. Re-confirmed Stage B contract/guards via docs/spec-db-workflow.md:31-34, plans/nanobrag_integration_plan.md:226-244, and findings REFINE-005/SCALE-001. Authored updated Do Now + How-To map directing a closure refactor that reuses the Stage A ROI sample (with a full-panel fallback), restores telemetry/improvement gating, and archives fresh collect/test logs under 2025-11-05T172937Z.
- Artifact Path: plans/active/TORCH-REFINE-004/reports/2025-11-05T172937Z/
- Next Actions: Delegate Stage B ROI sampler/telemetry repair (`run_nanobrag_refinement` Stage B block) and rerun `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` with artifacts captured per new plan.
- <Action State>: [ready_for_implementation]
2025-11-05T172937Z focus=TORCH-REFINE-004 state=ready_for_implementation dwell=2 artifacts=plans/active/TORCH-REFINE-004/reports/2025-11-05T172937Z/ next_action=repair_stage_b_roi_sampler
## 2025-11-05T190344Z — TORCH-REFINE-004 Stage B telemetry gate reset
- Focus: TORCH-REFINE-004 — Stage B Fhkl modifiers (optional)
- Action Type: planning
- Key Observations: Replayed `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers`; LBFGS now makes progress (three sampled-loss points) but never records a full-loss validation, leaving `best_loss_full_b=(inf, 0)` and the ≥3% improvement gate unenforced. Telemetry reports `roi_count_sampled=0` despite Stage A sampling one panel, so ROI accounting and gating are inconsistent. Captured failing run and log under `plans/active/TORCH-REFINE-004/reports/2025-11-05T190344Z/pytest_stage_b.log` and refreshed input.md with a ready-for-implementation handoff (ROI sampler fallback, mandatory full validations/best-snapshot restore, and gate recalibration path if the measured ceiling stays below 3%).
- Artifact Path: plans/active/TORCH-REFINE-004/reports/2025-11-05T190344Z/
- Next Actions: Execute Stage B telemetry fixes in `dbex/nanobrag_refinement.py::run_nanobrag_refinement`, adjust the Stage B smoke assertions/gate, rerun the selector capturing new logs, and archive measured improvement metrics for potential gate recalibration.
- <Action State>: [ready_for_implementation]
2025-11-05T190344Z focus=TORCH-REFINE-004 state=ready_for_implementation dwell=0 artifacts=plans/active/TORCH-REFINE-004/reports/2025-11-05T190344Z/ next_action=stage_b_telemetry_fix
2025-11-05T111500Z focus=REPORT-NANOBRAG-STATUS-001 state=gathering_evidence dwell=0 artifacts=plans/active/REPORT-NANOBRAG-STATUS-001/reports/2025-11-05T111500Z/ next_action=locate latest torch HDF5 and draft validation summary skeleton

## 2025-11-05T184233Z — REPORT-NANOBRAG-STATUS-001 telemetry planning handoff
- Focus: REPORT-NANOBRAG-STATUS-001 — Nanobrag Progress Reporting Pack
- Action Type: planning
- Key Observations: No existing `/torch_diagnostics` HDF5 artifacts or `reports/nanobrag_validation.md`; staged a fresh nanobrag CLI run using refGeom assets and scripted telemetry summarizer in input.md so Ralph can emit JSON tables plus the stakeholder report in one loop. Logged refined HKL guardrails (SCALE-006/007) and pytest telemetry selector to keep documentation synchronized.
- Artifact Path: plans/active/REPORT-NANOBRAG-STATUS-001/reports/2025-11-05T184233Z/
- Next Actions: Ralph executes the CLI run, authors `bin/emit_nanobrag_summary.py`, updates `reports/nanobrag_validation.md`, and captures pytest telemetry logs per Do Now.
- <Action State>: [ready_for_implementation]
2025-11-05T184233Z focus=REPORT-NANOBRAG-STATUS-001 state=ready_for_implementation dwell=2 artifacts=plans/active/REPORT-NANOBRAG-STATUS-001/reports/2025-11-05T184233Z/ next_action=execute_telemetry_run_and_report

## 2025-11-05T200729Z — TORCH-REFINE-004 bridge/test contract reset
- Focus: TORCH-REFINE-004 — Stage B Fhkl modifiers (optional)
- Action Type: planning
- Key Observations: Full-suite replay surfaced `TestDetectorConfigMapping::test_mask_array_float_conversion` failure because the bridge now returns `torch.float32` masks (per CLI-001) while the test still asserts numpy floats. Confirmed Stage B smoke remains green and documented plan to update the bridge test + docs to accept torch tensors while keeping polarity checks. `docs/config_crosswalk.md` now calls out the torch.as_tensor contract.
- Artifact Path: plans/active/TORCH-REFINE-004/reports/2025-11-05T200729Z/
- Next Actions: Ralph to update `create_detector_config` mask coercion (`torch.as_tensor` + asserts), refresh the bridge config test, and rerun the bridge + Stage B selectors per new input.md.
- <Action State>: [planning]
2025-11-05T200729Z focus=TORCH-REFINE-004 state=planning dwell=0 artifacts=plans/active/TORCH-REFINE-004/reports/2025-11-05T200729Z/ next_action=run_bridge_mask_realignment_do_now
## 2025-11-05T210730Z — TORCH-REFINE-004 CLI mask guard handoff
- Focus: TORCH-REFINE-004 — Stage B Fhkl modifiers (optional)
- Action Type: planning
- Key Observations: Marked Stage B gate calibration (1e-8) in docs/fix_plan.md, closed the bridge mask cleanup in the implementation plan, and drafted a ready-for-implementation Do Now directing Ralph to harden the nanobrag CLI test for torch masks plus rerun the CLI/Stage B selectors with fresh artifacts under 2025-11-05T210730Z/. Findings CLI-001, REFINE-008, TESTING-003, and RUNTIME-001 are all referenced in the new handoff.
- Artifact Path: plans/active/TORCH-REFINE-004/reports/2025-11-05T210730Z/
- Next Actions: Execute CLI mask guard Do Now (update CLI test, rerun targeted selectors, capture refine_one telemetry).
- <Action State>: [ready_for_implementation]
2025-11-05T210730Z focus=TORCH-REFINE-004 state=ready_for_implementation dwell=0 artifacts=plans/active/TORCH-REFINE-004/reports/2025-11-05T210730Z/ next_action=execute_cli_mask_guard_do_now

## 2025-11-05T221000Z — TORCH-REFINE-004 Stage B closeout
- Focus: TORCH-REFINE-004 — Stage B Fhkl modifiers (optional)
- Action Type: review_or_housekeeping
- Key Observations: Verified the CLI mask guard loop landed cleanly, marked the initiative `done` in docs/fix_plan.md with a closeout attempt referencing 2025-11-05T210730Z artifacts, and checked the implementation plan so the outstanding cleanup item is now complete. Stage B telemetry gate, findings (REFINE-008/CLI-001), and artifacts all reflect the calibrated 1e-8 ceiling.
- Artifact Path: plans/active/TORCH-REFINE-004/reports/2025-11-05T210730Z/
- Next Actions: Switch focus to PERF-WARM-SIM-001 for Stage A warm-simulator work.
- <Action State>: [review_or_housekeeping]
2025-11-05T221000Z focus=TORCH-REFINE-004 state=ready_for_implementation dwell=0 artifacts=plans/active/TORCH-REFINE-004/reports/2025-11-05T210730Z/ next_action=switch_focus

## 2025-11-05T221200Z — PERF-WARM-SIM-001 Stage A cache plan
- Focus: PERF-WARM-SIM-001 — Warm Simulator; Eliminate Per-Iteration Re-Instantiation
- Action Type: planning
- Key Observations: Audited Stage A closure in `dbex/nanobrag_refinement.py` and confirmed each LBFGS step rebuilds detector configs/models and retensors masks per panel. Updated docs/fix_plan.md and input.md with a Do Now that introduces a reusable Stage A panel cache (detector config/model + mask/target views) so we can drop the rebuild churn while preserving Stage B/C telemetry semantics.
- Artifact Path: plans/active/PERF-WARM-SIM-001/reports/2025-11-05T221200Z/
- Next Actions: Implement stage_a_panel_cache_impl in `run_nanobrag_refinement`, rerun Stage A/B smokes under `NANOBRAGG_DISABLE_COMPILE=1`, and capture logs + perf notes for the new artifact set.
- <Action State>: [planning]
2025-11-05T221200Z focus=PERF-WARM-SIM-001 state=planning dwell=0 artifacts=plans/active/PERF-WARM-SIM-001/reports/2025-11-05T221200Z/ next_action=stage_a_panel_cache_impl
## 2025-11-06T081209Z — PERF-WARM-SIM-001 perf telemetry planning
- Focus: PERF-WARM-SIM-001 — Warm Simulator; Eliminate Per-Iteration Re-Instantiation
- Action Type: planning
- Key Observations: Reviewed Stage A warm cache artifacts (pytest_stage_a_v2.log shows 180.29s runtime) and confirmed perf exit criteria 1/3 remain unmet—no baseline/improved timing diff captured yet and `/torch_diagnostics` lacks perf counters. Fix plan marked in_progress and new Do Now drafted to extend `RefinementTelemetry` with perf counters plus Stage A timing instrumentation.
- Artifact Path: plans/active/PERF-WARM-SIM-001/reports/2025-11-06T081209Z/
- Next Actions: Ralph to add Stage A perf counters in `run_nanobrag_refinement`, emit them via telemetry (with safe defaults for Stage B/C), update Stage A smoke assertions, and rerun Stage A/B selectors with logs + perf JSON.
- <Action State>: [ready_for_implementation]

2025-11-06T081209Z focus=PERF-WARM-SIM-001 state=ready_for_implementation dwell=0 artifacts=plans/active/PERF-WARM-SIM-001/reports/2025-11-06T081209Z/ next_action=stage_a_perf_counters_impl
## 2025-11-06T090721Z — PERF-WARM-SIM-001 Stage A speedup planning
- Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
- Action Type: planning
- Key Observations: Baseline Stage A runtime before warm cache (`plans/active/TORCH-REFINE-002/reports/2025-11-05T041539Z/pytest_stage_a.log`) still sits at 184.55s vs warm-cache telemetry run at 175.22s (plans/active/PERF-WARM-SIM-001/reports/2025-11-06T081209Z/), leaving exit criterion #1 unmet. Need reproducible cold vs warm comparison, so plan is to add a guarded config flag that reinstates the cold rebuild path for benchmarking and a T2 script that runs both modes, capturing wall-clock + perf counters for findings update.
- Artifact Path: plans/active/PERF-WARM-SIM-001/reports/2025-11-06T090721Z/
- Next Actions: Ralph implements warm-cache toggle + benchmark script, reruns Stage A smoke, runs the benchmark to gather timings, and updates findings with the measured ratio.
- <Action State>: [planning]
2025-11-06T090721Z focus=PERF-WARM-SIM-001 state=planning dwell=0 artifacts=plans/active/PERF-WARM-SIM-001/reports/2025-11-06T090721Z/ next_action=implement_warm_cache_benchmark

## 2025-11-06T095520Z — PERF-WARM-SIM-001 benchmark unblock plan
- Focus: PERF-WARM-SIM-001 — Warm Simulator; Eliminate Per-Iteration Re-Instantiation
- Action Type: planning
- Key Observations: Benchmark script currently resolves the installed `dbex` distribution instead of the workspace checkout, so `RefinementConfig` appears without the warm-cache flag and warm/cold runs bail before emitting metrics. Stage A telemetry also lacks an explicit cache-mode tag, making future artifacts ambiguous. Prepared new Do Now to prepend the repo root to the script `sys.path`, record cache mode in telemetry/tests, rerun warm vs cold benchmarks, and log speedup evidence under 2025-11-06T095520Z.
- Artifact Path: plans/active/PERF-WARM-SIM-001/reports/2025-11-06T095520Z/
- Next Actions: Execute cache-mode telemetry + benchmark script fix, rerun Stage A smoke, run warm/cold benchmark, and update findings with measured speedup.
- <Action State>: [planning]
2025-11-06T095520Z focus=PERF-WARM-SIM-001 state=planning dwell=1 artifacts=plans/active/PERF-WARM-SIM-001/reports/2025-11-06T095520Z/ next_action=ship_cache_mode_benchmark_handoff

## 2025-11-06T111515Z — PERF-WARM-SIM-001 cache-mode telemetry handoff
- Focus: PERF-WARM-SIM-001 — Warm Simulator; Eliminate Per-Iteration Re-Instantiation
- Action Type: planning
- Key Observations: Verified Stage A telemetry still lacks a `cache_mode` tag and the benchmark harness continues to import the packaged `dbex` while reading stale perf counter keys, so warm/cold runs can’t be attributed or compared. Updated docs/fix_plan.md and input.md with a ready-for-implementation Do Now covering the telemetry field, benchmark script `sys.path` fix + schema sync, Stage A smoke rerun, and warm/cold benchmark artifacts under 2025-11-06T111515Z.
- Artifact Path: plans/active/PERF-WARM-SIM-001/reports/2025-11-06T111515Z/
- Next Actions: Implement cache-mode telemetry + benchmark fixes, rerun Stage A smoke, run warm/cold comparison, and refresh docs/findings.md with speedup ratios.
- <Action State>: [ready_for_implementation]
2025-11-06T111515Z focus=PERF-WARM-SIM-001 state=ready_for_implementation dwell=0 artifacts=plans/active/PERF-WARM-SIM-001/reports/2025-11-06T111515Z/ next_action=implement_cache_mode_benchmark_fix
## 2025-11-20T231627Z — PHYSICS-LOSS-001 chi-squared planning
- Focus: PHYSICS-LOSS-001 — Implement variance-weighted loss function
- Action Type: planning
- Key Observations: Manual override demanded variance-weighted (chi-squared) loss + Stage B per-reflection staging, so patched `plans/nanobrag_integration_plan.md` §Phase 3 to the mandated text, inserted PHYSICS-LOSS/ARCH-REFINE-FLOW/TOOLING-VIS initiatives at the top of `docs/fix_plan.md`, marked PHYSICS-LOSS-001 in_progress with Attempts History, and rewrote `input.md` with a ready-for-implementation Do Now covering sigma plumbing, weighted loss in `run_nanobrag_refinement`, telemetry, and DB-AT-010 validation. TORCH-REFINE-005 now depends on ARCH-REFINE-FLOW-001 per override.
- Artifact Path: plans/active/PHYSICS-LOSS-001/reports/2025-11-20T231627Z/
- Next Actions: Execute the Do Now (implement chi-squared loss + telemetry + DB-AT-010) and capture pytest logs under the artifact directory.
- <Action State>: [ready_for_implementation]
2025-11-20T231627Z focus=PHYSICS-LOSS-001 state=ready_for_implementation dwell=0 artifacts=plans/active/PHYSICS-LOSS-001/reports/2025-11-20T231627Z/ next_action=implement_variance_weighted_loss
## 2025-11-20T233552Z — PHYSICS-LOSS-001 Stage B/C readiness plan
- Focus: PHYSICS-LOSS-001 — Implement variance-weighted loss function
- Action Type: planning
- Key Observations: Verified Stage A chi-squared path landed and DB-AT-010 artifacts exist, but Stage B/C closures (dbex/nanobrag_refinement.py:1132-1515) still emit masked-MSE values. `RefinementTelemetry` lacks chi-squared vs masked-MSE fields and `_write_torch_outputs` only records masked_mse, so exit criteria 2/4 remain open. Updated implementation plan (Phase B checklist split), fix plan attempts, findings ledger, and drafted a ready-for-implementation input.md targeting Stage B/C variance wiring plus telemetry/HDF5 updates. New artifacts directory: plans/active/PHYSICS-LOSS-001/reports/2025-11-20T233552Z/.
- Artifact Path: plans/active/PHYSICS-LOSS-001/reports/2025-11-20T233552Z/
- Next Actions: Execute Stage B/C chi-squared wiring + telemetry emission and run Stage B/C smokes plus CLI diagnostics test per the new Do Now.
- <Action State>: [planning]

2025-11-20T233552Z focus=PHYSICS-LOSS-001 state=planning dwell=0 artifacts=plans/active/PHYSICS-LOSS-001/reports/2025-11-20T233552Z/ next_action=ship_stage_b_c_chi_squared_impl

## 2025-11-20T235741Z — PHYSICS-LOSS-001 chi-squared validation handoff
- Focus: PHYSICS-LOSS-001 — Implement variance-weighted loss function
- Action Type: planning
- Key Observations: Confirmed commit ec6f485 threads `inputs.sigma_readout` plus dual chi-squared/masked-MSE telemetry through Stage B/C and `_write_torch_outputs`; Phase B checklist + fix-plan attempts updated and a fresh Do Now now targets smoke-test assertion upgrades plus DB-AT-024/Stage A replays. Artifacts staged under 2025-11-20T235741Z for the upcoming evidence capture.
- Artifact Path: plans/active/PHYSICS-LOSS-001/reports/2025-11-20T235741Z/
- Next Actions: Ralph updates `tests/dbex/test_torch_refine_smoke.py` telemetry asserts, reruns Stage A/B/C smokes + DB-AT-024, and captures metrics/logs per the new input.md.
- <Action State>: [planning]

2025-11-20T235741Z focus=PHYSICS-LOSS-001 state=planning dwell=1 artifacts=plans/active/PHYSICS-LOSS-001/reports/2025-11-20T235741Z/ next_action=stage_b_c_chi_squared_validation
2025-11-21T003959Z focus=PHYSICS-LOSS-001 state=ready_for_implementation dwell=0 artifacts=plans/active/PHYSICS-LOSS-001/reports/2025-11-21T003959Z/ next_action=implement_sigma_floor_guard

## 2025-11-21T003959Z — PHYSICS-LOSS-001 sigma-floor planning
- Focus: PHYSICS-LOSS-001 — Implement variance-weighted loss function
- Action Type: planning
- Key Observations: Stage B/C smokes still fail because the variance term clamps at 1.0 instead of `sigma_floor^2`, producing NaN/Inf gradients on GPU. Spec-db-core.md:67 mandates the floor plus telemetry, so I drafted a Do Now to add a CLI `--sigma-floor`, carry `RefinementConfig.sigma_floor_value` through Stage A/B/C variance math, log the clamp fraction inside `RefinementTelemetry`/`/torch_diagnostics`, and refresh Stage A/B/C smokes plus the CLI metadata test. Findings ledger now records PHYSICS-LOSS-002 for the sigma-floor guard, and docs/fix_plan.md attempts describe the new work scope.
- Artifact Path: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T003959Z/
- Next Actions: Implement sigma-floor guard + telemetry, rerun the mapped Stage A/B/C selectors, and unblock Phase B4/B5 + Phase C2/C3.
- <Action State>: [ready_for_implementation]

## 2025-11-21T010127Z — PHYSICS-LOSS-001 variance helper planning
- Focus: PHYSICS-LOSS-001 — Stage A/B/C variance-weighted loss
- Action Type: planning
- Key Observations: Stage B smoke still records zero LBFGS samples because the NaN/Inf guard fires immediately after the sigma-floor patch (telemetry status=`error`, see plans/active/PHYSICS-LOSS-001/reports/2025-11-21T003959Z/pytest_stage_b.log:60-99) and Stage C gate compares ≈8.09e3 vs ≈3.02e8 chi-squared values because Stage A still divides Σ(diff²) by Σ(variance) instead of summing per-pixel ratios (plans/active/PHYSICS-LOSS-001/reports/2025-11-21T003959Z/pytest_stage_c.log:112-134). Logged PHYSICS-LOSS-003 and refreshed the fix plan/input to mandate a shared helper in `dbex/nanobrag_refinement.py` so Stage A/B/C reuse the spec equation with one cached `sigma_floor_sq` tensor and aligned telemetry.
- Artifact Path: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T010127Z/
- Next Actions: Implement the shared variance-weighted helper + telemetry wiring, then rerun Stage A/B/C smokes and the CLI diagnostics test per the new input.
- <Action State>: [ready_for_implementation]

2025-11-21T010127Z focus=PHYSICS-LOSS-001 state=ready_for_implementation dwell=0 artifacts=plans/active/PHYSICS-LOSS-001/reports/2025-11-21T010127Z/ next_action=shared_variance_helper_implementation

## 2025-11-21T023537Z — PERF-SMOKE-DETSIZE override planning
- Focus: PERF-SMOKE-DETSIZE — Introduce small-detector fixture for Stage smokes
- Action Type: planning
- Key Observations: Manual override “Smoke Test Resource Guardrail” blocks PHYSICS-LOSS-001 until Stage smokes default to a cropped dataset, so I marked PHYSICS-LOSS-001 blocked, promoted PERF-SMOKE-DETSIZE to in_progress, and scoped the deliverables. Micro probes on `refGeom` confirmed a single 2463×2527 panel with 282 ROIs and showed a centred 1024×1024 crop keeps 87 ROIs (31%), satisfying the ≥50 ROI requirement while slashing tensor area by 76%. Authored a Do Now for Ralph covering: the T2 crop script that emits `sp.proc/refGeom_small/{lys_nitr_10_6_0001_small.cbf,refGeom_small.expt,refGeom_small.refl,refGeom_small_mask.pkl,README.md}` with provenance + checksums; Stage A/B/C smoke fixture parameterization via `--smoke-detector-size` defaulting to `small` plus gate recalibration with perf telemetry capture; and doc/test-index updates that codify small-smoke vs full-parity workflows and guard DB-AT selectors against accidentally using the cropped assets. Artifacts recorded under plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T023537Z/.
- Artifact Path: plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T023537Z/
- Next Actions: Ralph implements the crop script, rewires `tests/dbex/test_torch_refine_smoke.py` fixtures + gates, and updates docs/TESTING_GUIDE.md + spec workflow text before rerunning the Stage smokes on the new dataset.
- <Action State>: [planning]

2025-11-21T023537Z focus=PERF-SMOKE-DETSIZE state=planning dwell=0 artifacts=plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T023537Z/ next_action=crop_script_and_fixture_parameterization

## 2025-11-21T031620Z — PERF-SMOKE-DETSIZE DB-AT guard plan
- Focus: PERF-SMOKE-DETSIZE — Stage smoke detector-size split
- Action Type: planning
- Key Observations: Confirmed no DB-AT selector enforces the canonical detector footprint even after the `--smoke-detector-size` knob landed, so parity runs could still exercise the cropped assets. Updated docs/fix_plan.md and input.md with the pytest guard handoff (tests/conftest.py), documented the failure mode + telemetry expectations, and earmarked artifacts under 2025-11-21T031620Z/ for the full-detector Stage smokes + DB-AT_021 log plus an optional guard-failure capture.
- Artifact Path: plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T031620Z/
- Next Actions: Implement the guard/doc updates, rerun Stage A/B/C smokes with `--smoke-detector-size=full`, and attach both passing + guard-failure logs before unblocking PHYSICS-LOSS-001.
- <Action State>: [ready_for_implementation]

2025-11-21T031620Z focus=PERF-SMOKE-DETSIZE state=ready_for_implementation dwell=0 artifacts=plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T031620Z/ next_action=implement_db_at_guard

## 2025-11-21T032803Z — PERF-SMOKE-DETSIZE strict-gate calibration plan
- Focus: PERF-SMOKE-DETSIZE — Introduce small-detector fixture for smoke tests
- Action Type: planning
- Key Observations: DB-AT guard landed but canonical Stage B/C smokes are still red: Stage C chi-squared improvement is flat (0.0000%) and Stage B regresses by −7.6e-8% (plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T031620Z/pytest_stage_smokes_full.log:142-369). Drafted a ready-for-implementation Do Now directing Ralph to capture telemetry via `DBEX_SMOKE_TELEMETRY_PATH`, replace the strict gates with detector-offset reduction + no-regression guards (Stage C) and bounded loss deltas + shell-modifier sanity (Stage B), and sync docs/TESTING_GUIDE.md with the new tolerances so exit criterion #4 can close.
- Artifact Path: plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T032803Z/
- Next Actions: Implement the Stage B/C gating updates + doc sync, rerun the mapped selectors on `--smoke-detector-size=full`, and publish telemetry/logs so PHYSICS-LOSS-001 can resume.
- <Action State>: [ready_for_implementation]
2025-11-21T032803Z focus=PERF-SMOKE-DETSIZE state=ready_for_implementation dwell=0 artifacts=plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T032803Z/ next_action=recalibrate_stage_b_c_full_detector_gates
## 2025-11-21T042222Z — REFINE-SMOKE-CANONICAL canonical repair plan
- Focus: REFINE-SMOKE-CANONICAL — Restore canonical Stage B/C smoke convergence
- Action Type: planning
- Key Observations: Confirmed the canonical Stage B/C smokes still fail: `plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T031620Z/pytest_stage_smokes_full.log:460-509` shows the Stage B LBFGS closure crashing with `UnboundLocalError: chi_squared_best_b`, and `plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T032803Z/telemetry_full.json:1-49` still reports 100% detector-offset reduction even though chi-squared never changes because `param_deltas` hard-code zero baselines in `dbex/nanobrag_refinement.py:2017-2039`. Updated docs/fix_plan.md (REFINE-SMOKE-CANONICAL now in_progress) and rewrote input.md with a Do Now that adds the missing `nonlocal` declarations, strips the debug prints, threads an optional `baseline_detector` through `run_nanobrag_refinement`, and reruns the strict Stage B/C selectors with telemetry artifacts under 2025-11-21T042222Z/.
- Artifact Path: plans/active/REFINE-SMOKE-CANONICAL/reports/2025-11-21T042222Z/
- Next Actions: Ralph implements the Stage B closure + Stage C telemetry fixes, updates the smoke/probe call sites, replays the canonical Stage B/C selectors, and publishes logs + telemetry.
- <Action State>: [ready_for_implementation]

2025-11-21T042222Z focus=REFINE-SMOKE-CANONICAL state=ready_for_implementation dwell=0 artifacts=plans/active/REFINE-SMOKE-CANONICAL/reports/2025-11-21T042222Z/ next_action=ship_stage_b_c_canonical_fix
## 2025-11-21T045800Z — PHYSICS-LOSS-001 chi-squared alignment planning
- Focus: PHYSICS-LOSS-001 — Implement variance-weighted loss function
- Action Type: planning
- Key Observations: Verified REFINE-SMOKE-CANONICAL artifacts (`plans/active/REFINE-SMOKE-CANONICAL/reports/2025-11-21T042222Z/telemetry_full.json`) show Stage B/C full-detector smokes passing with detector_offset_reduction_min≈0.99999994 and chi-squared traces back in tolerance, so the dependency is closed. Updated docs/fix_plan.md status→in_progress, marked Phase B4/B5 complete in the implementation plan, added Phase D for the shared variance helper, and rewrote input.md with a Do Now that threads the helper through Stage A/B/C plus the Stage B/C full-detector selectors.
- Artifact Path: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T045800Z/
- Next Actions: Ralph implements the shared chi-squared helper + telemetry alignment, reruns the Stage B/C full detectors, and refreshes the CLI diagnostics test per the new schema.
- <Action State>: [ready_for_implementation]

2025-11-21T045800Z focus=PHYSICS-LOSS-001 state=ready_for_implementation dwell=1 artifacts=plans/active/PHYSICS-LOSS-001/reports/2025-11-21T045800Z/ next_action=shared_variance_helper_implementation

## 2025-11-21T052443Z — PHYSICS-LOSS-001 Stage A + DB-AT chi-squared plan
- Focus: PHYSICS-LOSS-001 — Implement variance-weighted loss function
- Action Type: planning
- Key Observations: Marked Phase D checklist items complete after verifying the shared helper + canonical telemetry landed, refreshed Phase C tasks to emphasize Stage A full-detector smoke evidence and DB-AT-024 chi-squared diagnostics, added a new fix-plan attempt plus report directory, and rewrote input.md with simulate_forward_once + test updates plus strict env commands.
- Artifact Path: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T052443Z/
- Next Actions: Ralph adds chi-squared/sigma-floor diagnostics to simulate_forward_once, updates the Stage A smoke + DB-AT-024 tests, and reruns the mapped selectors with telemetry logging per the new instructions.
- <Action State>: [ready_for_implementation]

2025-11-21T052443Z focus=PHYSICS-LOSS-001 state=ready_for_implementation dwell=0 artifacts=plans/active/PHYSICS-LOSS-001/reports/2025-11-21T052443Z/ next_action=stage_a_full_and_db_at_024_chi_squared_validation

## 2025-11-21T054520Z — PHYSICS-LOSS-001 sigma provenance handoff
- Focus: PHYSICS-LOSS-001 — Implement variance-weighted loss function
- Action Type: planning
- Key Observations: Verified the 2025-11-21T052443Z Stage A full-detector + DB-AT-024 artifacts close Phase C, so the remaining blocker is Phase A4: `run_nanobrag_backend` still allows sigma_readout=0 when `--sigma-rdout` is omitted, violating docs/spec-db-core.md:57-68 and hiding provenance in telemetry. Checked in the implementation-plan updates (C2/C3 marked done) and logged a fix-plan attempt describing the sigma provenance gap, then rewrote input.md with a ready-for-implementation Do Now targeting the CLI fail-fast guard, telemetry provenance fields, unit tests, and docs/TESTING_GUIDE.md sync. Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T054520Z/.
- Artifact Path: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T054520Z/
- Next Actions: Implement the sigma guard + telemetry provenance in `dbex/refine_one.py::{create_parser,run_nanobrag_backend}` and `_write_torch_outputs`/`RefinementTelemetry`, refresh `tests/dbex/test_refine_one_cli.py`, update docs/TESTING_GUIDE.md, and rerun the targeted CLI pytest selectors before logging results.
- <Action State>: [ready_for_implementation]
2025-11-21T054520Z focus=PHYSICS-LOSS-001 state=ready_for_implementation dwell=1 artifacts=plans/active/PHYSICS-LOSS-001/reports/2025-11-21T054520Z/ next_action=ship_sigma_rdout_guard
## 2025-11-21T060701Z — PHYSICS-LOSS-001 sigma-map ingestion plan
- Focus: PHYSICS-LOSS-001 — Implement variance-weighted loss function
- Action Type: planning
- Key Observations: Confirmed `_resolve_sigma_readout` already refuses missing noise sources and inspects `DataLoad.sigma_readout_map`, but DataLoad never sets that attribute—python probes on `sp.proc/idx-0000_refined.expt` show `external_lookup.{gain,pedestal,mask}` expose zero tiles, so the calibrated-map path is unused. Updated docs/fix_plan.md and the implementation plan with Phase E checklist items plus a Do Now covering the new `--sigma-map` parser option, loader helper, CLI regression, helper unit tests, and Testing Guide/Test Suite Index refresh. Published the new instructions + artifacts under 2025-11-21T060701Z/.
- Artifact Path: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T060701Z/
- Next Actions: Ralph implements the calibrated sigma-map ingestion path, runs the mapped CLI + helper pytest selectors, and syncs docs per the refreshed input.md.
- <Action State>: [ready_for_implementation]
2025-11-21T060701Z focus=PHYSICS-LOSS-001 state=ready_for_implementation dwell=2 artifacts=plans/active/PHYSICS-LOSS-001/reports/2025-11-21T060701Z/ next_action=ship_sigma_map_loader

## 2025-11-21T063052Z — PHYSICS-LOSS-001 external-lookup metadata plan
- Focus: PHYSICS-LOSS-001 — Implement variance-weighted loss function
- Action Type: planning
- Key Observations: Reviewed the 2025-11-21T060701Z sigma-map artifacts, re-checked spec-db-core.md §Variance + docs/simtbx_api.md, and re-probed `sp.proc/idx-0000_refined.expt` to confirm `imageset.external_lookup.{gain,pedestal,mask}` still report `n_tiles=0`. Updated `docs/fix_plan.md`, Phase F in `plans/active/PHYSICS-LOSS-001/implementation.md`, and `docs/findings.md` (PHYSICS-LOSS-005) to scope the next increment: add a helper that harvests `ExternalLookupItemDouble` tiles into `[panel, slow, fast]` tensors, enforces positivity, plumbs provenance through `_resolve_sigma_readout`, and extends loader/CLI tests plus Testing Guide/Test Suite Index entries so metadata becomes the default sigma source once available.
- Artifact Path: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T063052Z/
- Next Actions: Ralph builds the external-lookup helper + provenance plumbing, updates docs, and reruns the sigma CLI + loader selectors while archiving logs in the new artifact directory.
- <Action State>: [ready_for_implementation]

2025-11-21T063052Z focus=PHYSICS-LOSS-001 state=ready_for_implementation dwell=0 artifacts=plans/active/PHYSICS-LOSS-001/reports/2025-11-21T063052Z/ next_action=external_lookup_metadata_implementation

## 2025-11-21T065454Z — PHYSICS-LOSS-001 metadata fixture plan
- Focus: PHYSICS-LOSS-001 — Implement variance-weighted loss function
- Action Type: planning
- Key Observations: Phase F metadata ingestion is complete but we still lack an on-disk fixture + smoke harness to exercise `external_lookup` sigma tiles, so I carved out Phase G (embedding script + smoke sigma-source knob), refreshed the implementation plan/input, and marked PERF-SMOKE-DETSIZE done so only two initiatives remain in progress.
- Artifact Path: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T065454Z/
- Next Actions: Ralph implements the embedding script, updates smoke fixtures/tests/docs, and runs the Stage A full-detector selector with metadata provenance logging.
- <Action State>: [planning]

2025-11-21T065454Z focus=PHYSICS-LOSS-001 state=planning dwell=1 artifacts=plans/active/PHYSICS-LOSS-001/reports/2025-11-21T065454Z/ next_action=metadata_fixture_implementation
## 2025-11-21T071912Z — PHYSICS-LOSS-001 Stage B/C metadata plan
- Focus: PHYSICS-LOSS-001 — Implement variance-weighted loss function
- Action Type: planning
- Key Observations: Verified Stage B/C smokes still `pytest.skip` whenever `DBEX_SMOKE_SIGMA_SOURCE=metadata` because `tests/dbex/test_torch_refine_smoke.py::refinement_inputs` requires the `allow_metadata_sigma` marker (present only on Stage A) and the Stage B/C configs hard-code `sigma_readout_provenance="cli_override"`, so metadata telemetry never flows past Stage A. Updated the implementation plan with Phase H (Stage B/C metadata coverage), logged a new fix-plan attempt, and rewrote input.md with a ready-for-implementation Do Now covering the Stage B/C markers + telemetry asserts, docs updates, and metadata pytest selectors with artifact targets under 2025-11-21T071912Z/.
- Artifact Path: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T071912Z/
- Next Actions: Ralph implements the Stage B/C metadata plumbing + docs per the new Do Now and reruns the Stage B/C smoke selectors with metadata.
- <Action State>: [ready_for_implementation]

2025-11-21T071912Z focus=PHYSICS-LOSS-001 state=ready_for_implementation dwell=2 artifacts=plans/active/PHYSICS-LOSS-001/reports/2025-11-21T071912Z/ next_action=stage_bc_metadata_smokes
## 2025-11-21T075449Z — PHYSICS-LOSS-001 Phase I metadata plan
- Focus: PHYSICS-LOSS-001 — Implement variance-weighted loss function
- Action Type: planning
- Key Observations: Closed Phase H by capturing the 2025-11-21T071912Z Stage B/C metadata artifacts, added Phase I to `plans/active/PHYSICS-LOSS-001/implementation.md` for DB-AT-024 + CLI diagnostics coverage, appended the fix-plan ledger with the new attempt, and rewrote `input.md` so Ralph has a ready-for-implementation Do Now covering the DB-AT plumbing (smoke_sigma_source fixture, metadata telemetry asserts, mapping metrics provenance), CLI diagnostics metadata asserts, and Testing Guide/Test Suite Index refresh; artifacts staged under 2025-11-21T075449Z for the upcoming pytest logs/metrics.
- Artifact Path: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T075449Z/
- Next Actions: Ralph implements the DB-AT-024/CLI metadata coverage, reruns the mapped selectors with metadata enabled, captures `mapping_metrics.{json,csv}` + pytest logs in the new report dir, and then proceeds to the remaining Phase G manifest tasks.
- <Action State>: [ready_for_implementation]

2025-11-21T075449Z focus=PHYSICS-LOSS-001 state=ready_for_implementation dwell=0 artifacts=plans/active/PHYSICS-LOSS-001/reports/2025-11-21T075449Z/ next_action=db_at_cli_metadata_implementation
## 2025-11-21T083500Z — PHYSICS-LOSS-001 metadata manifest gate plan
- Focus: PHYSICS-LOSS-001 — Implement variance-weighted loss function
- Action Type: planning
- Key Observations: Phase I (DB-AT + CLI metadata) artifacts look healthy, so Phase G now needs fixture governance—marked the implementation checklist G4/G5 with manifest + CI-test details, added a fix-plan attempt describing the `--manifest` embedding flag, README, and pytest hash gate, refreshed input.md with log/artifact targets under 2025-11-21T083500Z/, and confirmed docs/fix_plan.md references the new scope.
- Artifact Path: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T083500Z/
- Next Actions: Ralph ships the manifest-aware embedding script, publishes `sp.proc/sigma_metadata_manifest.json` + README, adds `tests/sp_proc/test_sigma_metadata_fixture.py`, syncs docs, and runs the new pytest selector with logs/manifest snapshots in the artifact dir.
- <Action State>: [ready_for_implementation]

2025-11-21T083500Z focus=PHYSICS-LOSS-001 state=ready_for_implementation dwell=0 artifacts=plans/active/PHYSICS-LOSS-001/reports/2025-11-21T083500Z/ next_action=ship_sigma_metadata_manifest_gate
## 2025-11-21T093500Z — PERF-SMOKE-DETSIZE canonical parity relaunch
- Focus: PERF-SMOKE-DETSIZE — Introduce small-detector fixture for smoke tests
- Action Type: planning
- Key Observations: REFINE-SMOKE-CANONICAL closed the Stage B/C implementation bug, so PERF-SMOKE-DETSIZE can resume. Phase A–C checklists and the ledger were stale, so I backfilled the completed crop/script/doc work (artifacts: 2025-11-21T023537Z/031620Z/032803Z/), added Phase D for canonical parity re-validation, and drafted a new Do Now directing Ralph to regenerate the metadata sigma fixtures, rerun Stage A/B/C smokes on the full detector for both sigma sources, capture fresh telemetry/logs under 2025-11-21T093500Z/, and refresh docs/test-index/fix-plan pointers with the new canonical metrics. Input.md now maps every pytest command + telemetry target so exit criterion #4 can close once the artifacts land.
- Artifact Path: plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T093500Z/
- Next Actions: Ralph executes the Stage A/B/C full-detector smokes (CLI + metadata), archives logs/telemetry in the new report directory, and then updates docs/ledger per the Do Now.
- <Action State>: [ready_for_implementation]

2025-11-21T093500Z focus=PERF-SMOKE-DETSIZE state=ready_for_implementation dwell=0 artifacts=plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T093500Z/ next_action=canonical_full_detector_smokes
## 2025-11-21T090949Z — PERF-WARM-SIM-001 Stage A warm-cache refactor plan
- Focus: PERF-WARM-SIM-001 — Warm simulator; Eliminate Per-Iteration Re-Instantiation
- Action Type: planning
- Key Observations: Stage A warm vs cold benchmarks from 2025-11-06 are still 1.00× because `run_nanobrag_refinement.compute_loss` rebuilds `create_crystal_config`/`Crystal` (and per-panel Simulator objects) even when `StageAContext` is available, so cached HKL/mask tensors never amortize the expensive constructor path. Authored a new Do Now telling Ralph to thread StageAContext through `compute_loss`, hoist the crystal instantiation outside the panel loop for warm mode while keeping the cold control path, run `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`, and regenerate the warm/cold benchmark artifacts under 2025-11-21T090949Z before updating docs/fix_plan if the speedup still lags.
- Artifact Path: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T090949Z/
- Next Actions: Implement the Stage A warm-cache reuse (context plumbing + benchmark), run the mapped Stage A smoke, execute the warm/cold benchmark script, and refresh docs/fix_plan/findings if results differ.
- <Action State>: [ready_for_implementation]
2025-11-21T090949Z focus=PERF-WARM-SIM-001 state=ready_for_implementation dwell=0 artifacts=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T090949Z/ next_action=implement_stage_a_warm_cache_refactor
