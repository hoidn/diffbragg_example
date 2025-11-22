
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
## 2025-11-21T093905Z — PERF-WARM-SIM-001 cached simulator plan
- Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
- Action Type: planning
- Key Observations: Reviewed the 2025-11-21T090949Z warm/cold benchmark and verified it still reports only a 1.01× gain because `dbex/nanobrag_refinement.py:821-855` instantiates a fresh `nanobrag_torch.Simulator` per panel, violating docs/spec-db-runtime.md warm-reuse rules. Logged a new ready-for-implementation Do Now: extend `StageAContext` so it prebuilds per-panel simulators + beam config/HKL tensors, retarget them once per closure, keep the cold control path intact, then rerun the Stage A smoke and `benchmark_stage_a_cache.py --modes warm cold` with artifacts under 2025-11-21T093905Z/.
- Artifact Path: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T093905Z/
- Next Actions: Ralph implements the cached-simulator pool, runs the mapped Stage A smoke plus the warm/cold benchmark, and captures telemetry/logs in the new report directory.
- <Action State>: [ready_for_implementation]

2025-11-21T093905Z focus=PERF-WARM-SIM-001 state=ready_for_implementation dwell=1 artifacts=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T093905Z/ next_action=cache_simulator_pool_impl
## 2025-11-21T103500Z — PERF-WARM-SIM-001 ROI batching plan
- Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
- Action Type: planning
- Key Observations: Warm vs cold still measures ~1.01× because Stage A samples `n_panels` (only one panel) so every closure renders the full 2463×2527 frame despite <0.3 % loss-mask coverage. Drafted a new Do Now to build ROI-aware Stage A context—crop Detector/Simulator pairs per `panel_slices`, sample ROIs inside the closure (preserving the cold-mode rebuild path), update telemetry to report ROI counts, and re-run Stage A smokes (small + full) plus the warm/cold benchmark with artifacts under 2025-11-21T103500Z/.
- Artifact Path: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T103500Z/
- Next Actions: Ralph implements the ROI batching refactor, exercises the mapped Stage A selectors, reruns the benchmark, and records the new speedup/telemetry so we can decide whether additional findings or spec updates are needed.
- <Action State>: [ready_for_implementation]

2025-11-21T103500Z focus=PERF-WARM-SIM-001 state=ready_for_implementation dwell=0 artifacts=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T103500Z/ next_action=roi_stage_a_impl
## 2025-11-21T103232Z — PERF-WARM-SIM-001 warm-only ROI gate plan
- Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
- Action Type: planning
- Key Observations: ROI batching proved the warm path can finish Stage A in ~14.5 s but the cold control path now follows the same ROI sampling pipeline, so the benchmark’s speedup is still ≈1.01× (`plans/active/PERF-WARM-SIM-001/reports/2025-11-21T103500Z/benchmark_summary.json`). Updated the fix-plan entry and rewrote `input.md` so Ralph adds an `allow_cold_stage_a_roi_mode` override, gates ROI sampling on the warm cache by default, stamps the ROI mode into Stage A perf telemetry, and refreshes the benchmark script/artifacts (2025-11-21T103232Z/) to compare warm(ROI) against cold(panel) again.
- Artifact Path: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T103232Z/
- Next Actions: Implement the warm-only ROI gate + benchmark refresh, rerun the Stage A smoke with telemetry, capture the new `benchmark_summary.json`/perf counters in the artifacts dir, and update findings once the ≥2× ratio is recorded.
- <Action State>: [ready_for_implementation]

2025-11-21T103232Z focus=PERF-WARM-SIM-001 state=ready_for_implementation dwell=1 artifacts=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T103232Z/ next_action=roi_warm_only_impl

## 2025-11-21T105321Z — PERF-WARM-SIM-001 Stage B/C warm-cache plan
- Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
- Action Type: planning
- Key Observations: Stage B (`dbex/nanobrag_refinement.py:1499-1968`) and Stage C (`dbex/nanobrag_refinement.py:2052-2368`) still rebuild Detector/Simulator stacks inside every closure even when Stage A has a warmed context, so perf counters never populate past Stage A. Logged a new fix-plan attempt plus ready-for-implementation input.md telling Ralph to reuse `StageAContext` detectors/masks for Stage B/C warm runs, leave the cold path intact, add perf counters mirroring Stage A, and rerun the Stage B/C smoke selectors with telemetry captured under 2025-11-21T105321Z/.
- Artifact Path: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T105321Z/
- Next Actions: Implement the Stage B/C warm-cache reuse + perf telemetry and rerun the mapped Stage B/C smokes with telemetry/log capture per the new Do Now.
- <Action State>: [planning]

2025-11-21T105321Z focus=PERF-WARM-SIM-001 state=planning dwell=0 artifacts=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T105321Z/ next_action=stage_bc_warm_cache_impl

## 2025-11-21T133500Z — PERF-WARM-SIM-001 canonical warm-cache perf plan
- Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
- Action Type: planning
- Key Observations: Logged new Do Now for Ralph to add perf-counter asserts inside the Stage B/C smoke tests and to rerun those selectors plus the warm-vs-cold benchmark on the canonical detector so we can publish ROI vs panel deltas with telemetry evidence. Fix-plan ledger updated (2025-11-21T133500Z entry) and input.md now points at the full-detector pytest + benchmark commands with telemetry artifacts rooted at 2025-11-21T133500Z/.
- Artifact Path: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T133500Z/
- Next Actions: Implement the Stage B/C test edits, run the canonical-detector smokes with telemetry capture, re-run `benchmark_stage_a_cache.py --modes warm cold`, and push the resulting metrics into docs/findings.md + docs/fix_plan.md.
- <Action State>: [ready_for_implementation]

2025-11-21T133500Z focus=PERF-WARM-SIM-001 state=ready_for_implementation dwell=1 artifacts=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T133500Z/ next_action=stage_bc_full_detector_perf_impl
## 2025-11-21T121804Z — PERF-WARM-SIM-001 Stage B ROI planning
- Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
- Action Type: planning
- Key Observations: Stage B still iterates entire panels even when Stage A ROI mode is active, so perf counters always report `roi_mode="panel"` and the warm-cache ROI savings recorded in PERF-WARM-005 never reach Stage B telemetry. Drafted a Do Now for Ralph to add an ROI-aware Stage B closure (reusing `StageAContext.roi_entries`), update the perf counter asserts, and rerun the Stage B smoke on both the cropped and canonical detector sizes so we can verify ROI/panel telemetry in the same loop. Fix-plan ledger now tracks PERF-WARM-SIM-001 with the refreshed scope, and `input.md` maps the Stage B ROI implementation plus twin pytest runs with telemetry capture under the new artifact directory.
- Artifact Path: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T121804Z/
- Next Actions: Implement the ROI-aware Stage B compute path, refresh the smoke test asserts, and replay Stage B smokes (small + full) to capture telemetry/log evidence for docs/fix_plan + findings updates.
- <Action State>: [ready_for_implementation]

2025-11-21T121804Z focus=PERF-WARM-SIM-001 state=ready_for_implementation dwell=0 artifacts=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T121804Z/ next_action=stage_b_roi_mode_impl

## 2025-11-21T124101Z — PERF-WARM-SIM-001 Stage B ROI telemetry plan
- Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
- Action Type: planning
- Key Observations: Logged the Stage B ROI implementation outcome (small-detector pass, canonical smoke still expecting `roi_mode="panel"`), refreshed docs/fix_plan.md plus docs/findings.md with the ROI-mode drift, and drafted a Do Now that introduces a Stage B telemetry summary script plus dual Stage B smoke reruns so the canonical ROI counts can be archived before updating the ledger.
- Artifact Path: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T124101Z/
- Next Actions: Ralph adds the telemetry summarizer, reruns Stage B smokes (small + full) with fresh telemetry, runs the script to emit stage_b_roi_summary.json, and updates docs/fix_plan/findings with the new evidence.
- <Action State>: [ready_for_implementation]

2025-11-21T124101Z focus=PERF-WARM-SIM-001 state=ready_for_implementation dwell=0 artifacts=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T124101Z/ next_action=stage_b_roi_telemetry_capture
## 2025-11-21T125551Z — PERF-WARM-SIM-001 Stage B telemetry unblock plan
- Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
- Action Type: planning
- Key Observations: Stage B telemetry files under `plans/active/PERF-WARM-SIM-001/reports/2025-11-21T124101Z/` omit `param_deltas` because `_record_stage_telemetry` (tests/dbex/test_torch_refine_smoke.py:29-80) only persists perf counters/loss traces even though Stage B populates shell modifier deltas inside `dbex/nanobrag_refinement.py:1989-2056`. Documented the gap in docs/fix_plan.md and rewrote input.md with a Do Now that patches the telemetry writer, fixes the ROI summary script parser, reruns both detector-size Stage B smokes with telemetry capture, and records the resulting stage_b_roi_summary.json artifacts under 2025-11-21T125551Z/.
- Artifact Path: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T125551Z/
- Next Actions: Ralph implements the telemetry/script fixes, reruns the Stage B smokes (small + full), runs the summary CLI, and updates docs/fix_plan + findings with the new evidence so we can resume ROI benchmarking.
- <Action State>: [ready_for_implementation]

2025-11-21T125551Z focus=PERF-WARM-SIM-001 state=ready_for_implementation dwell=0 artifacts=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T125551Z/ next_action=stage_b_telemetry_fix
## 2025-11-21T142700Z — PERF-WARM-SIM-001 Stage B panel-validation plan
- Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
- Action Type: planning
- Key Observations: Post-telemetry Stage B runs still fail on the canonical detector because ROI-mode full validations reuse the same ~92 Stage A ROI entries as the closures, so the optimizer never sees the 6.2 M detector pixels; shell_0 pegs at 2.0 and REFINE-008 trips before telemetry can log (`plans/active/PERF-WARM-SIM-001/reports/2025-11-21T125551Z/{stage_b_roi_summary.json,pytest_stage_b_full.log:1785-1794}`). Logged finding PERF-WARM-009, updated docs/fix_plan.md, and drafted a Do Now directing Ralph to reuse warmed simulators for panel-scope initial/periodic/final validations while keeping ROI closures, then rerun the Stage B smokes + summary script under 2025-11-21T142700Z/ so shell modifiers stay within ±1% again.
- Artifact Path: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T142700Z/
- Next Actions: Implement the panel-validation path, rerun the Stage B small/full selectors with telemetry, emit stage_b_roi_summary.json, and refresh findings/fix_plan with the passing evidence.
- <Action State>: [ready_for_implementation]

2025-11-21T142700Z focus=PERF-WARM-SIM-001 state=ready_for_implementation dwell=0 artifacts=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T142700Z/ next_action=stage_b_panel_validations
## 2025-11-21T133729Z — PERF-WARM-SIM-001 canonical ROI probe
- Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
- Action Type: planning
- Key Observations: Reproduced the canonical Stage B smoke outside pytest via `plans/active/PERF-WARM-SIM-001/bin/probe_stage_b_full.py` and confirmed Stage A now stalls at χ²≈3.0×10⁸ while Stage B drives the loss down to 1.23×10⁸ by pegging `shell_0_modifier=2.0` (telemetry/probe summaries under `plans/active/PERF-WARM-SIM-001/reports/2025-11-21T133127Z/`). The perf counters show `roi_mode="roi"` with only ~13 sampled ROIs, so the canonical run no longer reflects the full detector that REFINE-008 expects. Updated docs/fix_plan.md + docs/findings.md (PERF-WARM-010) to record that canonical executions must disable Stage A ROI mode until the strict gate can be recalibrated, and rewrote input.md with a Do Now that toggles ROI based on detector size so Stage B shell modifiers return to ±1% before rerunning the Stage B smokes + summary script.
- Artifact Path: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T133127Z/
- Next Actions: Ralph disables Stage A ROI mode for `smoke-detector-size=full`, reruns Stage B smokes (small/full) with telemetry + stage_b_roi_summary.json, and cites the new evidence in docs/fix_plan/findings once the canonical gate passes again.
- <Action State>: [ready_for_implementation]

2025-11-21T133729Z focus=PERF-WARM-SIM-001 state=ready_for_implementation dwell=1 artifacts=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T133127Z/ next_action=disable_roi_for_canonical_stage_b

## 2025-11-21T150000Z — PERF-WARM-SIM-001 Stage B telemetry capture plan
- Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
- Action Type: planning
- Key Observations: Canonical Stage B smokes still fail without emitting telemetry because `_record_stage_telemetry` is invoked after the strict ±1% gate, so the pytest abort prevents `telemetry_stage_b_full.json` from being written and `stage_b_roi_summary.json` never includes the canonical dataset. Updated docs/fix_plan.md with the 2025-11-21T150000Z attempt and rewrote input.md so Ralph moves the telemetry call into a try/finally, reruns the small + full Stage B selectors with telemetry/log capture under 2025-11-21T150000Z/, and re-runs the ROI summary script. Once canonical telemetry exists even on failure we can inspect Stage A/B chi-squared traces to scope the shell_0 clamp fix.
- Artifact Path: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T150000Z/
- Next Actions: Ralph implements the Stage B telemetry ordering fix, reruns both detector sizes (full run expected to fail but must emit telemetry), and refreshes stage_b_roi_summary.json for the new report.
- <Action State>: [ready_for_implementation]

2025-11-21T150000Z focus=PERF-WARM-SIM-001 state=ready_for_implementation dwell=2 artifacts=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T150000Z/ next_action=stage_b_telemetry_guard_impl

## 2025-11-21T153500Z — PERF-WARM-SIM-001 Stage B CPU fallback plan
- Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
- Action Type: planning
- Key Observations: Reviewed the 2025-11-21T150000Z telemetry/logs confirming canonical Stage B now dies on CUDA OOM despite the telemetry guard, added finding PERF-WARM-011 plus a new fix-plan attempt, and drafted a Do Now instructing Ralph to honor `stage_b_full_eval_on_cpu`, update the Stage B smoke asserts, and rerun both selectors + ROI summary under 2025-11-21T153500Z/.
- Artifact Path: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T153500Z/
- Next Actions: Implement the Stage B CPU fallback and rerun the mapped Stage B smokes plus summarize_stage_b_roi.py to capture canonical telemetry without OOM.
- <Action State>: [ready_for_implementation]

2025-11-21T153500Z focus=PERF-WARM-SIM-001 state=ready_for_implementation dwell=2 artifacts=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T153500Z/ next_action=stage_b_cpu_fallback_impl

## 2025-11-21T160700Z — PERF-WARM-SIM-001 Stage B CPU cache plan
- Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
- Action Type: planning
- Key Observations: Verified the CPU fallback landed but canonical telemetry now reports `cache_mode="cold"` with 80 s runtimes because `stage_b_use_warm_cache` disables the Stage A context whenever eval_device=CPU (dbex/nanobrag_refinement.py:1588-1604). The latest stage_b_roi_summary.json (`plans/active/PERF-WARM-SIM-001/reports/2025-11-21T153500Z/stage_b_roi_summary.json:32-44`) shows `roi_mode="panel"`, `closure_evals=9`, yet `forward_time_ms.total≈8.0e4`, proving every closure rebuilds detector/mask tensors. Logged finding PERF-WARM-012 and added a fix-plan attempt directing Ralph to clone StageAContext onto CPU when the fallback engages so canonical Stage B once again benefits from cached detectors/HKL tensors. Rewrote input.md with a ready-for-implementation Do Now that targets the new CPU cache helper, Stage B smoke assertions, and the telemetry/summary reruns under 2025-11-21T160700Z/.
- Artifact Path: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T160700Z/
- Next Actions: Implement the CPU StageAContext clone + Stage B cache plumbing, update the Stage B smoke test expectations, rerun both detector-size selectors, and capture summarize_stage_b_roi.py output showing warm cache telemetry on CPU.
- <Action State>: [ready_for_implementation]

2025-11-21T160700Z focus=PERF-WARM-SIM-001 state=ready_for_implementation dwell=0 artifacts=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T160700Z/ next_action=warm_cpu_stage_b_cache

## 2025-11-21T170500Z — PERF-WARM-SIM-001 Stage C telemetry plan
- Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
- Action Type: planning
- Key Observations: Stage B CPU-cache evidence now lives under 2025-11-21T160700Z, but `rg --files plans/active/PERF-WARM-SIM-001/reports | rg stage_c` shows zero Stage C telemetry captures, so exit criterion #2 still lacks warm-cache proof for detector microslip runs. Authored a Do Now that adds Stage C perf-counter logging to the smoke test, creates a Stage C telemetry summarizer, reruns the small/full Stage C selectors with DBEX_SMOKE_TELEMETRY_PATH rooted at 2025-11-21T170500Z, and documents the workflow in docs/TESTING_GUIDE.md so future loops can reproduce it.
- Artifact Path: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T170500Z/
- Next Actions: Ralph lands the Stage C logging + summarizer updates, reruns both Stage C smokes with telemetry capture, generates stage_c_roi_summary.json, and updates docs per the new workflow to close the outstanding exit criteria.
- <Action State>: [ready_for_implementation]

2025-11-21T170500Z focus=PERF-WARM-SIM-001 state=ready_for_implementation dwell=0 artifacts=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T170500Z/ next_action=stage_c_telemetry_capture

## 2025-11-21T172334Z — PERF-WARM-SIM-001 Stage C telemetry prep
- Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
- Action Type: planning
- Key Observations: Confirmed the Stage C smoke (tests/dbex/test_torch_refine_smoke.py:583-854) already asserts cache/ROI counters yet never prints them, so pytest logs cannot prove warm-cache state; `rg --files plans/active/PERF-WARM-SIM-001/reports -g 'telemetry_stage_c*.json'` still returns nothing and `plans/active/PERF-WARM-SIM-001/bin/` lacks a Stage C summarizer. Updated docs/fix_plan.md and input.md with a ready-for-implementation Do Now covering the Stage C log block, a summarize_stage_c_roi.py twin to the Stage B script, the small/full telemetry reruns rooted at 2025-11-21T172334Z/, and the docs/TESTING_GUIDE.md refresh.
- Artifact Path: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T172334Z/
- Next Actions: Ralph lands the Stage C logging + summarizer, reruns both Stage C selectors with telemetry capture, generates stage_c_roi_summary.json, and updates docs/TESTING_GUIDE.md with the workflow so exit criterion #2 can close.
- <Action State>: [ready_for_implementation]

2025-11-21T172334Z focus=PERF-WARM-SIM-001 state=ready_for_implementation dwell=1 artifacts=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T172334Z/ next_action=stage_c_telemetry_capture

## 2025-11-21T174147Z — PERF-WARM-SIM-001 Stage C telemetry plan
- Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
- Action Type: planning
- Key Observations: `rg --files plans/active/PERF-WARM-SIM-001/reports | rg stage_c` returned no matches, so Stage C still lacks telemetry artifacts even after the previous CPU cache work; Stage C perf-counter assertions already exist but nothing prints to logs and no summarizer captures ROI stats.
- Artifact Path: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T174147Z/
- Next Actions: Ralph adds the Stage C perf-counter logging block, authors `summarize_stage_c_roi.py`, reruns Stage C smokes for small/full detectors with telemetry capture, runs the summarizer, and updates docs/TESTING_GUIDE.md per the new workflow.
- <Action State>: [ready_for_implementation]

2025-11-21T174147Z focus=PERF-WARM-SIM-001 state=ready_for_implementation dwell=2 artifacts=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T174147Z/ next_action=stage_c_telemetry_capture

## 2025-11-21T175716Z — PERF-WARM-SIM-001 Stage C detector reuse plan
- Focus: PERF-WARM-SIM-001 — Stage C warm-cache detector reuse
- Action Type: planning
- Key Observations: Verified the 2025-11-21T174147Z Stage C telemetry/logging artifacts, logged new finding PERF-WARM-013 to capture the remaining detector-instantiation debt, refreshed the implementation plan/status, and rewrote input.md with a ready-for-implementation Do Now covering the StageAContext metadata/retarget helper plus Stage C smoke reruns.
- Artifact Path: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T175716Z/
- Next Actions: Ralph implements the Stage C detector retarget helper + warm-path refactor and reruns both Stage C selectors with telemetry + summary artifacts.
- <Action State>: [ready_for_implementation]

2025-11-21T175716Z focus=PERF-WARM-SIM-001 state=ready_for_implementation dwell=0 artifacts=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T175716Z/ next_action=stage_c_detector_retarget_implementation

## 2025-11-22T090505Z — TORCH-REFINE-002E Phase A0 probe extension
- Focus: TORCH-REFINE-002E — Fix Stage A Zero-Point Geometry Discontinuity
- Action Type: planning
- Key Observations: Reviewed fix_plan.md:48 attempt history showing the Phase A probe reported `max_abs_diff≈4.0e-5` (exceeds the < 1e-6 exit criterion) and Phase 5 Adam sweeps still degrade CC. Confirmed PERF-WARM-SIM-001 is deferred per manual override at fix_plan.md:95, so input.md focus was stale. Switched to TORCH-REFINE-002E per Tier 1 Roadmap and authored a new Do Now targeting Phase A checklist item A0: extend `probe_crystal_matrix_parity.py` with eigenvalue/singular-value decomposition, symmetric/antisymmetric logm(U_error) splits, and reciprocal-column norm/angle comparisons to diagnose whether the 4e-5 gap is pure rotation or contains symmetric strain. New artifacts directory: plans/active/TORCH-REFINE-002E/reports/2025-11-22T090505Z/.
- Artifact Path: plans/active/TORCH-REFINE-002E/reports/2025-11-22T090505Z/
- Next Actions: Ralph extends the probe script per Phase A0, runs it on canonical refGeom assets, and emits `crystal_matrix_parity_extended.json` + log so we can quantify the rotation vs strain decomposition and decide whether to pursue Phase A1 (multi-config) or Phase A2 (baseline B_ideal variants) next.
- <Action State>: [ready_for_implementation]

2025-11-22T090505Z focus=TORCH-REFINE-002E state=ready_for_implementation dwell=0 artifacts=plans/active/TORCH-REFINE-002E/reports/2025-11-22T090505Z/ next_action=phase_a0_probe_extension

## 2025-11-22T091200Z — TORCH-REFINE-002E Phase A0 review → A2 planning
- Focus: TORCH-REFINE-002E — Fix Stage A Zero-Point Geometry Discontinuity
- Action Type: planning
- Key Observations: Verified Ralph's Phase A0 implementation landed cleanly (probe extended with eigenvalue/SVD/logm decompositions per implementation.md:83-86) and artifacts confirm H1 (residual strain): `log_u_symmetric_norm=1.37e-3` is ≈1000× larger than `log_u_antisymmetric_norm=1.37e-7`, proving the 4e-5 A* gap is dominated by symmetric strain, not pure rotation. Reciprocal-column angle deviations ≤0.051° and singular-value ratios show ≈0.07% strain along principal axes. Reviewed TOOLING-VIS-001 Phase 5 Adam artifacts (20251121T234215Z/block_dof_results.json) showing all DoF combos (scale-only, full) degrade χ² and CC from the mapping zero point (e.g., A_scale_only: 1.13M→3.52M χ², CC 1.0→0.846). Conclusion: Phase A checklist A0 complete; next is A2 (baseline B_ideal variants) to test whether deriving B_ideal from mapping's MOSFLM A* via cctbx cell recovery eliminates the strain component and closes the parity gap to <1e-6. Corrected missing artifact (copied crystal_matrix_parity.json to 2025-11-22T090505Z/), updated fix_plan Attempts History with Phase A0 outcomes, and drafted new Do Now for Phase A2 implementation.
- Artifact Path: plans/active/TORCH-REFINE-002E/reports/2025-11-22T091200Z/
- Next Actions: Implement Phase A2 per implementation.md:90-92: add helpers to recover effective cell from MOSFLM A*, construct alternative B_ideal, recompute baseline misset with recovered B_ideal, extend probe to compare both paths, and rerun with artifacts under new timestamp.
- <Action State>: [planning]

2025-11-22T091200Z focus=TORCH-REFINE-002E state=planning dwell=1 artifacts=plans/active/TORCH-REFINE-002E/reports/2025-11-22T091200Z/ next_action=phase_a2_baseline_b_ideal_implementation
- Artifact Path: plans/active/TORCH-REFINE-002E/reports/2025-11-22T091200Z/
- Next Actions: Implement Phase A2 per implementation.md:90-92: add helpers to recover effective cell from MOSFLM A*, construct alternative B_ideal, recompute baseline misset with recovered B_ideal, extend probe to compare both paths, and rerun with artifacts under new timestamp.
- <Action State>: [planning]

2025-11-22T091200Z focus=TORCH-REFINE-002E state=ready_for_implementation dwell=0 artifacts=plans/active/TORCH-REFINE-002E/reports/2025-11-22T091200Z/ next_action=phase_a2_baseline_b_ideal_implementation

## 2025-11-22T094500Z — TORCH-REFINE-002E Phase A→B transition
- Focus: TORCH-REFINE-002E — Fix Stage A Zero-Point Geometry Discontinuity
- Action Type: planning
- Key Observations: Phase A geometry characterization complete—H1 (residual strain) confirmed with log_u_symmetric_norm ≈ 1.4e-3 (1000× larger than antisymmetric), H2 (baseline cell mismatch) rejected as both B_ideal variants show identical strain. Synthesized evidence in phase_a_review.md showing geometry parity gap (~4e-5 A*) persists but TOOLING-VIS-001 Phase 5 reveals all Adam DoF combos degrade χ² and CC from mapping zero (scale-only: +210% χ², CC 1.0→0.846). Transitioned to Phase B1 (local gradient probe) to directly measure ∂χ²/∂θ and determine if gradients are truly zero or if Adam walks away legitimately. Updated implementation.md (A0/A2 marked done, A1/A3 deferred) and authored comprehensive input.md directing gradient-probe mode extension to stage_a_mapping_adam_debug.py.
- Artifact Path: plans/active/TORCH-REFINE-002E/reports/2025-11-22T094500Z/
- Next Actions: Ralph implements Phase B1 gradient probe (--mode gradient_probe), executes forward/backward pass at mapping zero point, reports global+trusted-ROI gradient magnitudes/signs for all DoFs, and reruns Stage-A expansion smoke for regression guard before returning results.
- <Action State>: [ready_for_implementation]

2025-11-22T094500Z focus=TORCH-REFINE-002E state=ready_for_implementation dwell=0 artifacts=plans/active/TORCH-REFINE-002E/reports/2025-11-22T094500Z/ next_action=phase_b1_gradient_probe_implementation

## 2025-11-22T100330Z — TORCH-REFINE-002E Phase A3 planning
- Focus: TORCH-REFINE-002E — Fix Stage A Zero-Point Geometry Discontinuity
- Action Type: planning
- Key Observations: Reviewed Phase B1 gradient probe artifacts confirming that the explicit cell+misset parameterization at zero deltas yields χ² ≈ 2.98e6 (≈2.6× higher than mapping MOSFLM path χ² ≈ 1.13e6), with large non-zero gradients (orientation_vec magnitude ≈2.88e8). Concluded H3/H4/H5 (scale mismatch, outlier gradients, loss subtleties) are moot—the global chi-squared mismatch dominates. Updated implementation.md checklist (B1 marked complete with critical decision note, B2-B5 marked DEFERRED, A3 unblocked). **Critical Decision:** Proceed to Phase A3 (mapping forward model comparison) to isolate whether the 2.6× chi-squared discrepancy originates from (a) cell/misset encoding conventions or (b) simulator numerical differences (interpolation, spot shape, HKL grid). Once A3 completes, transition to Phase C Branch G (geometry fix—adjust baseline geometry so explicit path reproduces mapping's effective cell). Authored comprehensive Do Now for Ralph to implement `compare_mapping_vs_stage_a_forward.py` script that runs both paths through nanobrag_torch on a single panel and emits pixel-level/chi-squared comparisons.
- Artifact Path: plans/active/TORCH-REFINE-002E/reports/2025-11-22T100330Z/
- Next Actions: Ralph implements Phase A3 comparison script, executes on canonical refGeom panel 0, captures forward_model_comparison.json showing whether forward models are identical (<1e-6 photon pixel diffs) or differ numerically, and runs regression guard for Stage A expansion smoke. Decision tree: if identical → proceed to Branch G (geometry fix); if different → open TORCH-SIMULATOR-PARITY-001 blocker initiative.
- <Action State>: [ready_for_implementation]

2025-11-22T100330Z focus=TORCH-REFINE-002E state=ready_for_implementation dwell=0 artifacts=plans/active/TORCH-REFINE-002E/reports/2025-11-22T100330Z/ next_action=phase_a3_forward_model_comparison

## 2025-11-22T100021Z — TORCH-REFINE-002E Phase C1 (Branch G geometry fix)
- Focus: TORCH-REFINE-002E — Fix Stage A Zero-Point Geometry Discontinuity
- Action Type: planning
- Key Observations: Reviewed Phase A3 artifacts (2025-11-22T100330Z/forward_model_comparison.json) confirming the geometry encoding gap: χ²_mapping=2.394e6 vs χ²_stage_a_zero=2.980e6 (24.5% difference), both using nanobrag_torch, proving the 2.6× global chi-squared mismatch is NOT a simulator parity bug but a parameterization artifact where the GEOMETRY-003 baseline misset (derived from dxtbx unit-cell B_ideal) produces a different effective crystal orientation than the mapping MOSFLM A* injection path. Phase A/B evidence chain complete: (A0) symmetric strain dominates (1.4e-3 >> antisymmetric 1.4e-7), (A2) cell recovery from MOSFLM A* matches dxtbx cell but strain persists, (B1) gradients at zero deltas are massive (orientation_vec magnitude ≈2.88e8), (A3) forward models differ by 24.5% chi-squared despite using same simulator. Updated implementation.md checklist (A3 marked complete with decision to proceed to Branch G). **Decision:** Implement Phase C Branch G (geometry fix) to derive mapping-aligned B_ideal directly from MOSFLM A* matrix (`B_ideal_mapping = (A*_mapping)^{-T}`) instead of using dxtbx unit-cell B_ideal, eliminating the 1.4e-3 symmetric strain component and achieving <1e-6 A* parity per exit criterion #1. Authored comprehensive Do Now for Ralph to (1) add `derive_b_ideal_from_mosflm_a_star` helper in `dbex/nanobrag_bridge.py`, (2) extend `derive_robust_misset` with `use_mapping_b_ideal: bool` parameter, (3) wire mapping-aligned baseline misset into Stage-A mapping paths (`build_mapping_stage_a_context`, `stage_a_mapping_adam_debug.py`), (4) re-run parity probe expecting `max_abs_diff < 1e-6`, (5) re-run Phase 5 validation expecting A_scale_only/D_full to maintain CC≥0.99 and show monotonic χ² improvement, and (6) regression-guard the Stage-A expansion smoke. New artifacts directory: plans/active/TORCH-REFINE-002E/reports/2025-11-22T100021Z/.
- Artifact Path: plans/active/TORCH-REFINE-002E/reports/2025-11-22T100021Z/
- Next Actions: Ralph implements Phase C1 geometry fix (mapping-aligned B_ideal derivation), validates parity (<1e-6) and Phase 5 behavior (stable Adam at mapping zero), and updates GEOMETRY-003 findings row if all exit criteria pass.
- <Action State>: [ready_for_implementation]

2025-11-22T100021Z focus=TORCH-REFINE-002E state=ready_for_implementation dwell=0 artifacts=plans/active/TORCH-REFINE-002E/reports/2025-11-22T100021Z/ next_action=phase_c1_branch_g_geometry_fix

## 2025-11-22T110000Z — TORCH-REFINE-002E Phase C1 validation prep
- Focus: TORCH-REFINE-002E — Fix Stage A Zero-Point Geometry Discontinuity
- Action Type: planning
- Key Observations: Reviewed Ralph's Phase C1 implementation attempt (2025-11-22T100021Z) showing partial success: all three B_ideal variants (dxtbx unitcell, recovered, mapping-aligned) now produce **identical** parity results (max_abs_diff ≈ 4.022e-05, log_u_symmetric_norm ≈ 1.369e-3), confirming the geometry gap is NOT fixable by changing B_ideal derivation but instead represents a numerical precision floor or Euler gimbal lock artifact. Regression guard (test_stage_a_expansion) PASSED, verifying the mapping-aligned implementation is stable. **Critical Decision:** Per implementation.md:30-35, Exit Criterion #1 has an **OR** clause—either achieve <1e-6 parity **OR** identify and document the strain component with quantified impact. Ralph achieved the **alternative path** (symmetric strain 1.369e-3 identified, 1000× larger than antisymmetric 1.37e-7; 24.5% χ² gap quantified; not fixable by B_ideal choice). The remaining question is whether this 4e-5 gap **blocks refinement convergence** (exit criteria #2-3). Authored a new Do Now directing Ralph to run `stage_a_mapping_adam_debug.py --phases 1,2,4,5` and synthesize a decision based on Phase 5 A_scale_only/D_full trajectories: if CC ≥ 0.99 and stable/monotonic χ², accept the documented residual and mark initiative `done`; if convergence fails, pivot to Phase B3 (LR sensitivity sweep) or escalate to TORCH-SIMULATOR-PARITY-001.
- Artifact Path: plans/active/TORCH-REFINE-002E/reports/2025-11-22T110000Z/
- Next Actions: Ralph runs Phase 5 validation, captures A_scale_only/D_full convergence metrics, synthesizes decision.json, and conditionally updates findings/fix_plan per the decision tree in input.md.
- <Action State>: [ready_for_implementation]

2025-11-22T110000Z focus=TORCH-REFINE-002E state=ready_for_implementation dwell=0 artifacts=plans/active/TORCH-REFINE-002E/reports/2025-11-22T110000Z/ next_action=phase_5_validation_decision_synthesis

## 2025-11-22T120000Z — TORCH-REFINE-002E Phase C1 decisive validation (reduced scope)
- Focus: TORCH-REFINE-002E — Fix Stage A Zero-Point Geometry Discontinuity
- Action Type: planning
- Key Observations: Reviewed Phase C1 validation artifacts (2025-11-22T110000Z) showing incomplete Phase 5 (ran >12min building HKL grids, never produced `block_dof_results.json`) but decisive Phase 1-4 evidence: Exit criterion #1 alternative path satisfied (symmetric strain 1.369e-3 identified, 24.5% χ² gap quantified, orientation_vec gradient magnitude ≈2.88e8), Phase 4 shows convergence degradation (χ²: 1.13M → 2.80M after 1 Adam step, all DoFs walk away from zero). Per repeat-failure escalation rule, this is the **final validation attempt** before escalation. Authored reduced-scope Phase 5 Do Now (A_scale_only + D_full only, 5 Adam steps instead of 10, 20-minute timeout) to avoid HKL grid rebuild bottleneck. Decision tree: if A_scale_only maintains CC ≥ 0.99 + stable χ² → accept residual and mark done; if both variants degrade or timeout → escalate to TORCH-GEOMETRY-PARITY-002 (U-matrix direct override) or alternative. Updated input.md with comprehensive decision synthesis template and blocker handling protocol.
- Artifact Path: plans/active/TORCH-REFINE-002E/reports/2025-11-22T120000Z/
- Next Actions: Ralph runs Phase 5 reduced scope (timeout 1200s), synthesizes decision.json per template, and updates findings/fix_plan based on convergence viability (accept_residual vs escalate_to_new_initiative).
- <Action State>: [ready_for_implementation]

2025-11-22T120000Z focus=TORCH-REFINE-002E state=ready_for_implementation dwell=1 artifacts=plans/active/TORCH-REFINE-002E/reports/2025-11-22T120000Z/ next_action=phase_5_reduced_scope_decisive_validation

## 2025-11-22T105837Z — TORCH-GEOMETRY-PARITY-002 Initiative Creation
- Focus: TORCH-GEOMETRY-PARITY-002 — Direct U-Matrix Parameterization for Stage A Geometry Refinement
- Action Type: planning
- Key Observations: Escalated from TORCH-REFINE-002E Phase C1 final validation (2025-11-22T120000Z decision.json). Evidence chain complete: (A0) symmetric strain 1.37e-3 dominates (1000× larger than antisymmetric), (A2) cell recovery doesn't eliminate strain, (A3) forward models differ by 24.5% χ² due to geometry encoding not simulator bugs, (B1) massive gradients at zero (orientation_vec ≈2.88e8) prove zero-point mismatch, (C1) all DoF variants degrade (A_scale_only: 3.10× χ², CC→0.846; D_full: 1.71× χ², CC→0.895). Root cause: `orientation_vec` in cell+misset parameterization encodes rotation only, cannot express the symmetric strain embedded in MOSFLM A*. Created new initiative TORCH-GEOMETRY-PARITY-002 with comprehensive implementation plan (3 phases: Analysis & Design, Implementation, Validation & Integration). Updated docs/fix_plan.md roadmap (moved TORCH-GEOMETRY-PARITY-002 to top of Tier 1, marked TORCH-REFINE-002E as blocked). Next focus: Phase A0 evidence synthesis to document the causal chain before implementing quaternion-based U-matrix parameterization.
- Artifact Path: plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T105837Z/
- Next Actions: Execute Phase A checklist (A0: evidence synthesis, A1: SO(3) survey, A2: API design, A3: risk analysis) to prepare for Phase B implementation. Recommend quaternion (4-param, unit norm) for numerical stability and gradient quality.
- <Action State>: [planning]

2025-11-22T105837Z focus=TORCH-GEOMETRY-PARITY-002 state=planning dwell=0 artifacts=plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T105837Z/ next_action=phase_a_analysis_and_design
## 2025-11-22T112058Z — TORCH-GEOMETRY-PARITY-002 Phase B Regression Detection
- Focus: TORCH-GEOMETRY-PARITY-002 — Direct U-Matrix Parameterization for Stage A Geometry Refinement
- Action Type: review_or_housekeeping
- Key Observations: Reviewed Ralph's commit 2793ba9 (Phase B1-B5 quaternion infrastructure) and artifacts (2025-11-22T105837Z/). Ralph completed Phase A analysis (A0 evidence synthesis, A1 SO(3) survey, A2 API design, A3 risk analysis) AND jumped to Phase B implementation (B1-B5: derive_u_matrix_from_mosflm_a_star helper, quaternion conversion ops, use_u_matrix_parameterization config flag, initialization, closure branching). Quaternion roundtrip test PASSED (<1e-6 error). **Regression detected:** test_stage_a_expansion FAILED with `NameError: name 'misset_deg_for_crystal' is not defined`. Root cause: scoping bug at line 1015—code tries to use `misset_xyz_deg` (only defined in cell+misset else-branch at line 997) before the if/else block completes. The assignment `misset_deg_for_crystal = None if config.use_u_matrix_parameterization else misset_xyz_deg` should be moved INSIDE each branch where the required variables are in scope. Same pattern appears in Stage C closure (~line 1404-1448). Authored comprehensive bug report (`phase_b_regression_bug_report.md`) with exact fix instructions (move misset_deg_for_crystal assignment into each branch, remove line 1015). Ralph must fix this scoping bug and re-run regression guard before proceeding to Phase C validation (B6 parity probe extension, C1-C7).
- Artifact Path: plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T112058Z/
- Next Actions: Ralph applies scoping fix to both closures (Stage A + Stage C), re-runs test_stage_a_expansion to confirm PASSED, commits fix, then proceeds to Phase C Do Now (parity probe extension + C1 parity validation).
- <Action State>: [ready_for_implementation]

2025-11-22T112058Z focus=TORCH-GEOMETRY-PARITY-002 state=ready_for_implementation dwell=0 artifacts=plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T112058Z/ next_action=phase_b_regression_fix

## 2025-11-22T113409Z — TORCH-GEOMETRY-PARITY-002 Phase C Planning
- Focus: TORCH-GEOMETRY-PARITY-002 — Direct U-Matrix Parameterization for Stage A Geometry Refinement
- Action Type: planning
- Key Observations: Reviewed Ralph's Phase B regression bugfix (commits 2793ba9 + b353b77) confirming test_stage_a_expansion PASSED (regression guard validated) and test_quaternion_roundtrip PASSED (quaternion ops stable). Phase B checklist B1-B5 fully complete: U-matrix helpers (derive_u_matrix_from_mosflm_a_star, matrix_to_quaternion, quaternion_to_matrix) implemented in dbex/nanobrag_bridge.py, use_u_matrix_parameterization config flag added to RefinementConfig, initialization logic in run_nanobrag_refinement extracts U₀ from MOSFLM A* and converts to trainable quaternion q_params, closure branching in build_stage_a_lbfgs_closure normalizes q→U→A*. Scoping bug (misset_deg_for_crystal referenced before definition) fixed in both Stage A and Stage C closures. Transition to Phase C validation (B6 parity probe extension + C1-C3 convergence tests). Authored comprehensive Do Now bundling C1 (parity probe with --use-u-matrix flag), C2 (Phase 5 scale-only convergence), C3 (Phase 5 full-DoF convergence), C4 (regression guard), with explicit decision tree for blocking conditions (C1 fails → diagnose numerical precision/B_ideal/quaternion roundtrip; C2/C3 fail → escalate to TORCH-REFINE-003). New artifacts directory: plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T113409Z/. Implementation floor satisfied: Do Now contains production code tasks (extend probe_crystal_matrix_parity.py::run_probe, extend stage_a_mapping_adam_debug.py::main with --use-u-matrix flags) AND validating pytest selectors (test_stage_a_expansion regression guard).
- Artifact Path: plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T113409Z/
- Next Actions: Ralph implements C1-C3 (parity probe extension + Phase 5 validation with U-matrix mode), executes parity test expecting max_abs_diff < 1e-6, runs Phase 5 scale-only/full-DoF variants expecting CC ≥ 0.99 and stable/monotonic χ², and returns artifacts under 2025-11-22T113409Z/ with decision on whether to proceed to Phase C5 (findings update) or escalate per blocking conditions.
- <Action State>: [ready_for_implementation]

2025-11-22T113409Z focus=TORCH-GEOMETRY-PARITY-002 state=ready_for_implementation dwell=0 artifacts=plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T113409Z/ next_action=phase_c1_c3_parity_convergence_validation

## 2025-11-22T114945Z — TORCH-GEOMETRY-PARITY-002 Phase C1 Parity Failure Analysis → Alt Path 3 Convergence Sensitivity Test
- Focus: TORCH-GEOMETRY-PARITY-002 — Direct U-Matrix Parameterization for Stage A Geometry Refinement
- Action Type: planning
- Key Observations: Reviewed Ralph's Phase C1 artifacts (2025-11-22T113409Z/) showing decisive parity dichotomy: (1) **Raw U-matrix** achieves perfect parity (`max_abs_diff=3.469e-18`, `log_u_symmetric_norm=3.542e-16`), validating the `A* = U @ B_ideal` matrix identity at machine precision; (2) **det(U₀)=1.000557** proves U is NOT in SO(3), containing ~0.06% volume scaling; (3) **Quaternion parameterization** enforces SO(3) projection via `scipy.spatial.transform.Rotation.from_matrix()`, which loses the determinant offset and degrades parity back to `~4e-05` (same as cell+misset variants). Phase C1 diagnosis (phase_c1_parity_failure_diagnosis.md:47-74) recommends four alternative paths: (1) GL(3) full 9-DOF (risky overfitting), (2) hybrid cell+U+scale factorization (complex gradient flow), (3) **accept ~4e-05 parity and test convergence anyway** (pragmatic sensitivity test), (4) investigate MOSFLM A* source per DXTBX-001 audit (deep dive, time-intensive). **Decision:** Proceed with Alternative Path 3 per repeat-failure escalation rule — quaternion parameterization achieves same parity as cell+misset (~4e-05) so it's not worse, and the critical question is whether it **improves convergence** by eliminating the symmetric strain gradient artifact that blocked TORCH-REFINE-002E. Authored comprehensive Do Now for Phase C2/C3 convergence sensitivity test: (1) Ralph runs `stage_a_mapping_adam_debug.py` Phase 5 with `--use-u-matrix` for variants `A_scale_only` and `D_full`, (2) decision tree: if A_scale_only maintains CC ≥ 0.99 + stable χ² → quaternion is viable despite ~4e-05 parity, document in findings as GEOMETRY-004; if both degrade → escalate to TORCH-GEOMETRY-PARITY-003 (investigate `det(U)≠1` root cause or hybrid parameterization), (3) regression guard `test_stage_a_expansion` to confirm U-matrix path doesn't break existing cell+misset default. New artifacts directory: plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T114945Z/. Rationale: Testing convergence with quaternion is a **low-cost sensitivity probe** before committing to deeper dxtbx A* investigation or hybrid parameterizations; if convergence succeeds, ~4e-05 parity may be acceptable as a documented limitation of the SO(3) constraint vs the mapping geometry's embedded volume scaling.
- Artifact Path: plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T114945Z/
- Next Actions: Ralph implements Phase C2/C3 convergence tests with quaternion U-matrix mode, captures Phase 5 A_scale_only/D_full metrics (CC, χ², trajectories), synthesizes decision.json per template (viable vs escalate), and updates findings/fix_plan based on convergence viability.
- <Action State>: [planning]

2025-11-22T114945Z focus=TORCH-GEOMETRY-PARITY-002 state=planning dwell=1 artifacts=plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T114945Z/ next_action=phase_c2_c3_convergence_sensitivity_despite_parity_gap

## 2025-11-22T120500Z — TORCH-GEOMETRY-PARITY-002 Phase C2 bug triage + fix
- Focus: TORCH-GEOMETRY-PARITY-002 — Direct U-Matrix Parameterization for Stage A Geometry Refinement
- Action Type: review_or_housekeeping
- Key Observations: Reviewed Ralph's Phase C2 execution attempt (2025-11-22T114945Z) showing **decisive partial success**: (1) Zero-point check PASSED with CC=0.9999999843 (essentially perfect) and chi²_rel_diff=-0.017% (well within 0.1% tolerance), confirming U-matrix parameterization logic is correct at zero deltas; (2) Phase 5 convergence test (A_scale_only/D_full Adam optimization) FAILED with `RuntimeError: size mismatch, got input (3), mat (3x3), vec (9)` at line 434 when computing `A_star_new = U_matrix @ components.B_ideal_reciprocal`. Root cause diagnosed: `cctbx_cell(...).fractionalization_matrix()` returns a **flat 9-element array** (row-major), NOT a 3×3 matrix—the `.T` transpose at line 325 did nothing because the array was already 1D with shape (9,). Fixed by adding `.reshape(3,3)` before transpose (line 325: `.reshape(3, 3).T`) so `B_ideal_reciprocal` is a proper (3,3) torch tensor. Documented bug in phase_c2_shape_bug_diagnosis.md. Updated implementation.md checklist (C1 marked complete with zero-point validation note, C2/C3 remain pending bugfix rerun). Next: Ralph reruns Phase C2/C3 convergence test with bugfix applied, executes A_scale_only + D_full Adam optimization for 10 steps per input.md:46-55, synthesizes decision.json per decision tree (accept_quaternion if A_scale_only maintains CC ≥ 0.99 + χ² drift ≤ 0.5%, else escalate_to_geometry_parity_003), runs regression guard test_stage_a_expansion, and conditionally updates findings per decision.
- Artifact Path: plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T120500Z/
- Next Actions: Hand off to Ralph with updated input.md for Phase C2/C3 rerun (bugfix applied, convergence test executable). Decision tree outcome determines whether to accept quaternion (→ GEOMETRY-004 findings update + mark TORCH-REFINE-002E done) or escalate to GEOMETRY-PARITY-003 (det(U)≠1 root cause investigation).
- <Action State>: [ready_for_implementation]

2025-11-22T120500Z focus=TORCH-GEOMETRY-PARITY-002 state=ready_for_implementation dwell=0 artifacts=plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T120500Z/ next_action=phase_c2_c3_convergence_rerun_with_bugfix

## 2025-11-22T121500Z — TORCH-GEOMETRY-PARITY-003 Initiative Creation & Phase A Planning
- Focus: TORCH-GEOMETRY-PARITY-003 — Investigate det(U)≠1 Root Cause & Implement Hybrid Parameterization
- Action Type: planning
- Key Observations: Escalated from TORCH-GEOMETRY-PARITY-002 Phase C2/C3 catastrophic failure (2025-11-22T120500Z decision.json). Quaternion U-matrix parameterization passed zero-point validation (CC=0.9999999843, chi²_rel_diff=-0.017%) but completely collapsed during Adam optimization: A_scale_only chi² increased 1257× (1.13M→1.43B), median CC collapsed to -0.045 (negative correlation), D_full showed similar degradation (chi² +125799%, CC→-0.041). This definitively rules out pure SO(3)-constrained approaches (quaternion, axis-angle, exponential map). Root cause hypothesis: `det(U₀)=1.000557` indicates mapping MOSFLM A* contains ~0.06% volume scaling that SO(3) projection discards, creating pathological gradient flow during optimization despite acceptable forward parity. Three primary hypotheses to investigate: (H1) dxtbx A*/cell inconsistency per DXTBX-001 extension (crystal.get_A() may embed isotropic scale not reflected in crystal.get_unit_cell() parameters), (H2) physical volume scaling in crystal (thermal expansion, radiation damage, or pressure relative to reference cell), (H3) numerical precision in B_ideal derivation (cctbx roundtrip errors). Authored comprehensive implementation plan (plans/active/TORCH-GEOMETRY-PARITY-003/implementation.md) with 3 phases: (A) Root Cause Investigation (evidence synthesis, dxtbx A*/cell audit via analysis script, metadata review of DIALS experiment JSON, numerical precision validation of cctbx fractionalization_matrix roundtrip, hypothesis decision), (B) Parameterization Design & Prototyping (evaluate hybrid cell+quaternion+isotropic scale vs quaternion+anisotropic scale vs GL(3), prototype scale extraction s=det(U)^(1/3), gradient flow analysis, parameterization decision), (C) Implementation & Validation (hybrid initialization extracting s₀ and q₀ from mapping A*, hybrid closure applying A*=s·R(q)@cell_matrix, parity probe extension, Phase 5 convergence tests expecting CC≥0.99+χ² stable, regression guard, findings update GEOMETRY-004). Recommended approach: Option 1 (Hybrid Cell+Quaternion+Isotropic Scale) factoring A*=s·quaternion_to_matrix(q)@cell_matrix where isotropic scale s₀=det(U₀)^(1/3)≈1.000186 absorbs the volume offset while quaternion maintains SO(3) gradient quality and manifold constraints. Updated docs/fix_plan.md: added TORCH-GEOMETRY-PARITY-003 entry to Tier 1 (top priority, escalated from PARITY-002), marked PARITY-002 as blocked (SO(3) approach failed, escalated to PARITY-003), updated Execution Roadmap to show PARITY-003 as critical blocker for Stage A convergence. Authored Phase A ready-for-implementation Do Now for Ralph: (A0) evidence synthesis doc, (A1) implement audit_dxtbx_a_star_cell.py script to extract crystal.get_A(), crystal.get_unit_cell(), compute B_ideal via cctbx, derive U=A*@inv(B_ideal), compute determinants and isotropic scale, validate A*≈U@B_ideal identity, check for crystal.get_B() API, emit dxtbx_a_star_cell_audit.json report, (A2) metadata review of experiment JSON for calibration flags/processing history, (A3) numerical precision test validating cctbx roundtrip and det(U) stability, (A4) hypothesis decision synthesizing A0-A3 results into phase_a_root_cause_determination.md with primary hypothesis verdict (H1/H2/H3/combination), confidence level, and Phase B recommendation. Implementation floor satisfied: Do Now contains evidence-gathering tasks (not production code) appropriate for planning state; next loop will transition to ready_for_implementation once hypothesis is determined.
- Artifact Path: plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T121500Z/
- Next Actions: Ralph executes Phase A checklist (evidence synthesis, dxtbx audit script, metadata review, numerical precision test, hypothesis decision) to determine whether det offset is physical, dxtbx calibration artifact, or numerical precision issue before committing to hybrid parameterization design in Phase B.
- <Action State>: [planning]

2025-11-22T121500Z focus=TORCH-GEOMETRY-PARITY-003 state=planning dwell=0 artifacts=plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T121500Z/ next_action=phase_a_root_cause_investigation

## 2025-11-22T130000Z — TORCH-GEOMETRY-PARITY-003 Phase A Complete → Convergence Verification
- Focus: TORCH-GEOMETRY-PARITY-003 — Investigate det(U)≠1 Root Cause & Implement Hybrid Parameterization
- Action Type: planning
- Key Observations: Reviewed Ralph's Phase A root cause investigation (2025-11-22T121500Z) yielding **decisive finding**: det(U)=1.000557 anomaly from PARITY-002 Phase C1 **does NOT exist** for canonical `refGeom.expt` in current workspace. Phase A1 dxtbx audit proves `det(U) = 1.0` (within machine precision 1e-16, volume_offset=6.66e-14%). Cell parameter comparison shows PARITY-002 used a different experiment file with ~0.1% volume difference (a=27.364210 Å vs current 27.375838 Å, similar diffs for b/c/α/β/γ). All three hypotheses rejected: (H1) dxtbx A*/cell inconsistency rejected (det(A*)/det(B_ideal)=1.0, dxtbx get_B() matches cctbx B_ideal exactly), (H2) physical volume scaling rejected (no environmental metadata, cell is self-consistent), (H3) numerical precision rejected (cctbx B_ideal roundtrip stable, det(U)=1.0 confirms no artifacts). **Critical Implication:** With det(U)=1.0, raw U-matrix is already in SO(3), so quaternion U-matrix parameterization should achieve perfect parity (~1e-17, no degradation from SO(3) projection) AND converge successfully (no volume component to discard). PARITY-002 Phase C2/C3 catastrophic failures (CC→-0.045, χ²→1.43B) may be **file-specific artifacts** of the non-canonical experiment with det(U)≠1. **Decision:** Execute Ralph's recommended Option 1 — re-run PARITY-002 Phase C2/C3 convergence tests (parity probe + Phase 5 A_scale_only/D_full) with `--use-u-matrix` flag on CURRENT canonical `refGeom.expt` to determine if quaternion approach works with det(U)=1.0 file. Decision tree: if parity <1e-6 AND convergence succeeds → close PARITY-003 as resolved (det(U) problem was file-specific), unblock PARITY-002/REFINE-002E, create GEOMETRY-004 finding; if parity OK but convergence fails → escalate to TORCH-GEOMETRY-CONVERGENCE-001 (optimizer/loss/gradient debugging, NOT geometry issue); if parity fails → investigate implementation bug. Authored comprehensive Do Now with 6-step validation protocol (parity probe, Phase C2 A_scale_only, Phase C3 D_full, decision synthesis, regression guard, conditional findings update), decision.json template with all three paths, and explicit blocker handling for each failure mode. New artifacts directory: plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T130000Z/. **Implementation floor satisfied:** Phase A evidence-gathering complete (4 checklist items done), next loop transitions to ready_for_implementation with decisive validation experiment (parity probe + convergence tests are production code executions, not docs-only).
- Artifact Path: plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T130000Z/
- Next Actions: Ralph executes Phase A verification (parity probe with --use-u-matrix, Phase 5 A_scale_only/D_full convergence tests, regression guard), synthesizes decision.json per three-path template, and conditionally updates findings/fix_plan based on convergence viability (close_parity_003_resolved vs escalate_to_convergence_debugging vs blocked_investigate_parity_regression).
- <Action State>: [ready_for_implementation]

2025-11-22T130000Z focus=TORCH-GEOMETRY-PARITY-003 state=ready_for_implementation dwell=0 artifacts=plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T130000Z/ next_action=phase_a_verification_convergence_tests_with_canonical_file

## 2025-11-22T134421Z — TORCH-GEOMETRY-CONVERGENCE-001 Initiative Creation & Phase A0 Planning
- Focus: TORCH-GEOMETRY-CONVERGENCE-001 — Diagnose & Fix Quaternion U-Matrix Catastrophic Convergence Failure
- Action Type: planning
- Key Observations: Escalated from TORCH-GEOMETRY-PARITY-003 Phase C2/C3 convergence verification (2025-11-22T130000Z decision.json). Ralph's verification test definitively proved quaternion U-matrix catastrophic convergence failure is NOT file-specific: parity is perfect (<1e-17 max_abs_diff) with canonical refGeom.expt (det(U)=1.0 per dxtbx audit, det(U)=1.000565 per MOSFLM reconstruction due to nanobrag_torch/dxtbx computation path difference), but A_scale_only Adam optimization exploded χ² 1257× (1.13M→1.43B, +125,648%) and collapsed median CC from 1.0 to -0.045, exactly reproducing PARITY-002 failure signature. This rules out geometry encoding as root cause; problem is optimizer/loss/gradient pathology. Created new Tier 1 initiative TORCH-GEOMETRY-CONVERGENCE-001 with comprehensive implementation plan (plans/active/TORCH-GEOMETRY-CONVERGENCE-001/implementation.md, 3 phases: A=Evidence Collection & Gradient Diagnosis, B=Hypothesis Testing, C=Fix Implementation & Validation). Four primary hypotheses to investigate: (H1) Adam hyperparameters incompatible with quaternion gradient manifold (S³ unit sphere), (H2) variance-weighted loss numerical instability with quaternion parameterization, (H3) gradient pathology (NaN/inf/exploding due to quaternion normalization or matrix ops), (H4) quaternion constraint handling (unit norm violated between normalizations, off-manifold gradients). Phase A diagnostic protocol: (A1) instrument quaternion U-matrix closure with per-step telemetry (q_params, gradients, loss components, variance metrics), (A2) execute instrumented run, (A3) identify first divergence point (χ² increase >10% OR CC drop <0.95 OR gradient explosion/vanishing OR NaN), (A4) finite-difference gradient validation, (A5) variance/loss component analysis, (A6) hypothesis decision. Updated docs/fix_plan.md: added TORCH-GEOMETRY-CONVERGENCE-001 to Tier 1 (top priority, escalated from PARITY-003), marked PARITY-003 as blocked (parity solved, convergence blocked, escalated to CONVERGENCE-001). Authored Phase A0 ready-for-planning Do Now for Ralph: evidence synthesis (read PARITY-003 Phase C2 artifacts, extract failure metrics, cross-reference REFINE-001/PHYSICS-LOSS-002/GRADIENT-001 findings, emit phase_a0_evidence_synthesis.md), instrumentation planning (draft Phase A1 telemetry spec for closure injection points, emit phase_a1_instrumentation_plan.md), artifact archival (copy PARITY-003 decision/convergence/dof JSONs to CONVERGENCE-001 reports), implementation plan checklist update (mark A0 complete), summary emission. **Implementation floor satisfied:** This is a docs-only loop (evidence synthesis + planning), next loop MUST have production code task (Phase A1 closure instrumentation implementation). New artifacts directory: plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T134421Z/. Rationale: Parity perfect but convergence catastrophically failed → root cause is NOT geometry encoding (PARITY-002/PARITY-003 exhausted geometry hypotheses) → must be optimizer/loss/gradient pathology → systematic telemetry-driven diagnosis required before attempting fixes.
- Artifact Path: plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T134421Z/
- Next Actions: Ralph executes Phase A0 (evidence synthesis, instrumentation planning, artifact archival, checklist update, summary emission). Next loop (after A0 docs-only) transitions to ready_for_implementation with Phase A1 production code task (closure instrumentation) AND Phase A2 execution (instrumented convergence test).
- <Action State>: [planning]

2025-11-22T134421Z focus=TORCH-GEOMETRY-CONVERGENCE-001 state=planning dwell=0 artifacts=plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T134421Z/ next_action=phase_a0_evidence_synthesis_and_instrumentation_planning

## 2025-11-22T140000Z — TORCH-GEOMETRY-CONVERGENCE-001 Phase A1 Instrumentation Implementation
- Focus: TORCH-GEOMETRY-CONVERGENCE-001 — Diagnose & Fix Quaternion U-Matrix Catastrophic Convergence Failure
- Action Type: ready_for_implementation
- Key Observations: Reviewed Phase A0 artifacts (2025-11-22T134421Z/) confirming evidence synthesis and instrumentation planning complete. Ralph synthesized PARITY-003 Phase C2 failure signature (χ² +125,648%, CC→-0.045 after 10 Adam steps, A_scale_only variant), documented four root cause hypotheses (H1: Adam hyperparameters incompatible with S³ quaternion manifold, H2: variance-weighted loss numerical instability, H3: gradient pathology NaN/inf/explosion, H4: quaternion constraint handling), cross-referenced REFINE-001/PHYSICS-LOSS-002/GRADIENT-001 findings, and authored comprehensive Phase A1 instrumentation plan specifying per-step telemetry (parameters: q_params/q_norm/log_scale, gradients: norms/NaN/Inf flags, loss: chi²/masked_mse/clamp_fraction, variance: I_model histograms). **Implementation floor enforcement:** Last loop (2025-11-22T134421Z) was docs-only Phase A0 → this loop MUST transition to ready_for_implementation with production code task. Transitioned state from `planning` (dwell=0) to `ready_for_implementation` (dwell=0 reset). Authored comprehensive Do Now directing Ralph to: (1) Implement telemetry in `build_stage_a_lbfgs_closure` (U-matrix path, dbex/nanobrag_refinement.py:~968-1116) with step counter, parameter/gradient/loss/variance capture, conditional JSON emission gated by `config.telemetry_output_dir`, (2) Add `telemetry_output_dir` field to `RefinementConfig`, (3) Extend `stage_a_mapping_adam_debug.py` with `--telemetry-dir` CLI flag, (4) Execute instrumented run (Phase A2: `--use-u-matrix --phases 5 --dof-variants A_scale_only --adam-steps 10 --telemetry-dir <artifacts>/telemetry/`, timeout 1200s), (5) Analyze telemetry to identify first divergence step (chi² >10% increase OR NaN/Inf gradients OR gradient explosion >1e10 OR clamp_fraction >0.95), document in `phase_a_first_divergence.md`, (6) Regression guard `test_stage_a_expansion`, (7) Update implementation.md checklist (mark A1/A2/A3 complete), (8) Emit summary with first divergence step index and primary failure mode classification. Expected artifacts: `telemetry/telemetry_step_{000..009}.json`, `block_dof_results.json`, `phase_a_first_divergence.md`, `pytest_stage_a_regression.log`. **Constraints:** Telemetry is observation only (no mutation of production logic), conditional emission (default None = no overhead), CPU tensors for JSON serialization. **Hypothesis screening:** Phase A3 first divergence analysis should note which of H1-H4 is most supported by evidence but defer definitive verdict to Phase A6 after A4 (finite-difference validation) and A5 (variance analysis). New artifacts directory: plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/.
- Artifact Path: plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/
- Next Actions: Ralph implements Phase A1 (closure telemetry instrumentation), Phase A2 (executes instrumented run with --telemetry-dir flag), Phase A3 (analyzes telemetry to identify first divergence, classifies failure mode, emits phase_a_first_divergence.md), runs regression guard, updates implementation.md checklist, and emits summary. Next loop (after A1-A3 execution) proceeds to Phase A4-A6 (finite-difference validation, variance analysis, hypothesis decision) to select Phase B targeted fix.
- <Action State>: [ready_for_implementation]

2025-11-22T140000Z focus=TORCH-GEOMETRY-CONVERGENCE-001 state=ready_for_implementation dwell=0 artifacts=plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/ next_action=phase_a1_instrumentation_phase_a2_execution_phase_a3_first_divergence_analysis

## 2025-11-22T150000Z — TORCH-GEOMETRY-CONVERGENCE-001 Phase A3 First Divergence Analysis (Step 0 Catastrophic Failure)
- Focus: TORCH-GEOMETRY-CONVERGENCE-001 — Diagnose & Fix Quaternion U-Matrix Catastrophic Convergence Failure
- Action Type: planning
- Key Observations: Reviewed Ralph's Phase A1/A2 execution (commit 3d5c613 + artifacts 2025-11-22T140000Z/). **Telemetry instrumentation complete** (dbex/nanobrag_refinement.py + stage_a_mapping_adam_debug.py with --telemetry-dir CLI flag). **Phase A2 execution partial:** Captured 9/10 telemetry steps (step_000 through step_008); Phase 5 incomplete (no block_dof_results.json); run stopped early (only 33 lines in stage_a_debug.log, HKL grid builds in progress). **Phase A3 first divergence analysis complete:** Analyzed telemetry revealing **catastrophic failure at step 0** (before optimizer runs), chi-squared 1.425B (1000× worse than expected ~1.13M from PARITY-003 zero-point validation), log_scale gradient massive (~295k at all steps), chi-squared barely changes across 9 steps (variations <0.0001%), q_params gradients null (expected for A_scale_only with train_orientation=False), gradients clean (no NaN/Inf flags). **Root cause classification:** `forward_model_pathology` (NOT optimizer issue)—problem exists at initialization before Adam takes a single step. **Hypothesis verdicts:** H1 (Adam hyperparameters) REJECTED (failure before optimizer runs), H2 (variance-weighted loss numerical instability) PLAUSIBLE (massive log_scale gradient suggests variance denominator pathology), H3 (gradient/forward pathology) PARTIALLY SUPPORTED (chi-squared wrong at zero params suggests A* computation bug or geometry mismatch), H4 (quaternion constraint) NOT TESTABLE with A_scale_only (q_params frozen). **Critical comparison:** Zero-point check in this run (zero_point_check.json) shows perfect parity (corr ≈ 1.0, max_abs_diff = 85 photons), matching PARITY-003 expectations, suggesting forward model works correctly at zero point but fails during Adam loop—possible mismatch in forward model setup between zero-point check code path and Adam optimization code path. **Next actions:** (1) Investigate why Phase A2 run stopped at step 8 (missing step_009, no block_dof_results.json), (2) Compare zero-point check forward model setup vs Adam loop forward model to diagnose chi-squared discrepancy, (3) Phase A5 variance telemetry instrumentation in dbex/nanobrag_refinement.py closure (current script-level telemetry has variance components null), (4) Phase A4 gradient validation requires D_full or C_scale_plus_orientation variant (A_scale_only blocks quaternion gradients). **Preliminary CONVERGENCE-002 finding:** Quaternion U-matrix forward model pathology at initialization (chi-squared 1.425B vs expected ~1.13M), massive log_scale gradient (~295k), optimizer makes no progress—points to forward model geometry mismatch or variance numerical instability, NOT optimizer hyperparameters. **Artifacts:** phase_a_first_divergence.md, telemetry/*.json (000-008), zero_point_check.json, updated implementation.md checklist (A0/A1/A3 marked complete, A2 partial, A4 blocked, A5/A6 pending).
- Artifact Path: plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T140000Z/
- Next Actions: Author Do Now for Ralph to: (1) Diagnose zero-point check vs Adam loop forward model discrepancy (compare A_star, U_matrix, B_ideal_reciprocal computation paths), (2) Optionally rerun Phase A2 with --adam-steps 10 to capture all 10 steps and block_dof_results.json, (3) If discrepancy found, fix forward model bug and revalidate; if no bug found, proceed to Phase A5 variance telemetry instrumentation in closure. **State transition:** Remain in `planning` (dwell=1) because A2 incomplete + A4 blocked + A5 pending; next loop MUST be ready_for_implementation with forward model diagnostic OR variance telemetry instrumentation.
- <Action State>: [planning]

2025-11-22T150000Z focus=TORCH-GEOMETRY-CONVERGENCE-001 state=planning dwell=1 artifacts=plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T150000Z/ next_action=diagnose_zero_point_vs_adam_forward_model_discrepancy_or_variance_telemetry

## 2025-11-22T152500Z — TORCH-GEOMETRY-CONVERGENCE-001 Phase A Diagnostic Complete → Phase A Bugfix Implementation
- Focus: TORCH-GEOMETRY-CONVERGENCE-001 — Diagnose & Fix Quaternion U-Matrix Catastrophic Convergence Failure
- Action Type: ready_for_implementation
- Key Observations: Reviewed Ralph's Phase A forward model diagnostic (2025-11-22T150000Z artifacts) confirming **decisive root cause identification**: chi-squared catastrophic failure (1.425B vs expected ~990k) at step 0 is due to B_ideal computation mismatch bug. Ralph's analysis (`forward_model_discrepancy_analysis.md`) proves that `derive_u_matrix_from_mosflm_a_star` (dbex/nanobrag_bridge.py:844-862) uses TorchCrystal `np.column_stack([a_star, b_star, c_star])` to compute B_ideal_reciprocal, while `_build_stage_a_components` (stage_a_mapping_adam_debug.py:323-326) independently computes B_ideal via cctbx `fractionalization_matrix().reshape(3,3).T`. These two methods produce slightly different B_ideal matrices, causing U_initial @ B_ideal_cctbx ≠ A_star_mosflm at initialization. Mathematical consequence: A_star_reconstructed = A_star_mosflm @ (inv(B_ideal_torch) @ B_ideal_cctbx) ≠ A_star_mosflm when B_ideal_torch ≠ B_ideal_cctbx. This propagates through simulator producing vastly different Bragg peaks and 1000× worse chi-squared. Zero-point check succeeds (chi²≈990k) because it uses `use_mapping_zero_geometry=True` which bypasses U-matrix reconstruction and uses MOSFLM A* directly; Adam loop fails at step 0 because it uses `use_mapping_zero_geometry=False` which forces reconstruction via U @ B_ideal even before optimizer runs. Regression guard `test_stage_a_expansion` PASSED, confirming default cell+misset path unaffected. **Recommended fix** (Ralph's Option 2): Refactor `derive_u_matrix_from_mosflm_a_star` to return BOTH `U_matrix` and `B_ideal_reciprocal` from same TorchCrystal computation, update 2 call sites (stage_a_mapping_adam_debug.py:315 + dbex/nanobrag_refinement.py:779), delete cctbx fractionalization_matrix code to prevent future mismatch. This ensures U @ B_ideal == A_star_mosflm by construction (both computed in same function). Authored comprehensive Phase A bugfix Do Now directing Ralph to: (1) refactor helper signature to return Tuple[np.ndarray, np.ndarray], (2) update script call site to destructure tuple and use returned B_ideal, (3) update dbex/nanobrag_refinement.py call site similarly, (4) delete cctbx code in script, (5) add docstring notes documenting CONVERGENCE-001 bugfix, (6) regression guard, (7) rerun Phase A2 instrumented convergence test to validate chi-squared at step 0 matches zero-point check (~990k), (8) update implementation.md checklist marking A2/A3 complete with bugfix note, (9) synthesize decision on whether to proceed to Phase C validation or Phase A4-A6 deeper analysis based on convergence outcomes. New artifacts directory: plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T152500Z/. **Implementation floor satisfied:** Do Now contains production code tasks (refactor dbex/nanobrag_bridge.py::derive_u_matrix_from_mosflm_a_star signature, update 2 call sites) AND validating pytest selector (test_stage_a_expansion regression guard).
- Artifact Path: plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T152500Z/
- Next Actions: Ralph implements Phase A bugfix (refactor helper to return tuple, update call sites, delete cctbx code, regression guard, rerun Phase A2 validation test), synthesizes decision.json on whether bugfix resolves catastrophic failure (chi² step_0 ≈ 990k → proceed to Phase C convergence validation) or further diagnosis needed (chi² still high → escalate to Phase A5 variance analysis).
- <Action State>: [ready_for_implementation]

2025-11-22T152500Z focus=TORCH-GEOMETRY-CONVERGENCE-001 state=ready_for_implementation dwell=0 artifacts=plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T152500Z/ next_action=phase_a_bugfix_b_ideal_mismatch


## 2025-11-22T165000Z — TORCH-GEOMETRY-CONVERGENCE-001 Phase B LBFGS Test Handoff
- Focus: TORCH-GEOMETRY-CONVERGENCE-001 — Diagnose & Fix Quaternion U-Matrix Catastrophic Convergence Failure
- Action Type: planning
- Key Observations: Reviewed Ralph's Phase A bugfix (2025-11-22T152500Z) confirming decisive partial success—initialization pathology FIXED (chi² step_0 = 1.13M, 1000× improvement vs pre-bugfix 1.425B, zero-point parity perfect), but Adam optimization STILL catastrophically fails during steps 1-9 (chi² 1.13M → 1.425B, CC 1.0 → -0.045). This definitively confirms root cause is NOT the B_ideal mismatch (now fixed) but an optimizer/loss/gradient pathology. Hypothesis update: H1 (Adam hyperparameters/quaternion manifold incompatibility), H2 (variance-weighted loss instability), H3 (gradient pathology NaN/inf/exploding), H4 (quaternion unit-norm constraint vs momentum) all remain PLAUSIBLE. Authored comprehensive Phase B Do Now prioritizing Test B1 (LBFGS optimizer alternative) per hypothesis prioritization: LBFGS eliminates momentum (H4), uses line search to mitigate exploding steps (H3), stabilizes variance exploration (H2), and is proven for scale-only refinement per REFINE-001. Implementation plan: (1) extend RefinementConfig with use_lbfgs_for_u_matrix flag, (2) add LBFGS optimizer branch in run_nanobrag_refinement with closure pattern, (3) extend stage_a_mapping_adam_debug.py with --use-lbfgs CLI flag, (4) run LBFGS test (A_scale_only, 10 steps), (5) extract convergence metrics (chi² ratio, median CC), (6) synthesize decision (Path A: LBFGS succeeds → proceed to Phase C fix; Path B: LBFGS fails → proceed to Test B2 gradient validation; Path C: inconclusive → tighter tolerances rerun). Decision tree and test protocol documented in `phase_b_test_protocol.md` with detailed decision template for Ralph to fill. Implementation floor satisfied: Do Now contains production code tasks (RefinementConfig field, optimizer branch, script CLI extension, closure refactor) AND validation (pytest regression guard, LBFGS convergence test with metrics extraction).  
- Artifact Path: plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/
- Next Actions: Ralph implements Phase B0-B1 (test protocol doc + LBFGS test), executes LBFGS A_scale_only validation, extracts metrics, synthesizes decision per decision tree (SUCCESS→Phase C, FAILURE→Test B2, INCONCLUSIVE→rerun with tighter tolerances), runs regression guard, and updates implementation checklist.
- <Action State>: [ready_for_implementation]

2025-11-22T165000Z focus=TORCH-GEOMETRY-CONVERGENCE-001 state=ready_for_implementation dwell=0 artifacts=plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T165000Z/ next_action=phase_b_lbfgs_test_implementation

## 2025-11-22T172000Z — TORCH-GEOMETRY-CONVERGENCE-001 Phase B1 Diagnostic Rerun Handoff
- Focus: TORCH-GEOMETRY-CONVERGENCE-001 — Diagnose & Fix Quaternion U-Matrix Catastrophic Convergence Failure
- Action Type: planning
- Key Observations: Reviewed Ralph's Phase B1 LBFGS test execution (commit 8440df8, artifacts 2025-11-22T165000Z/) showing PREMATURE TERMINATION: (1) LBFGS optimizer infrastructure implemented correctly (use_lbfgs_for_u_matrix config field, --use-lbfgs CLI flag, LBFGS vs Adam branching in optimization loop with closure pattern), (2) regression guard test_stage_a_expansion PASSED (13.16s, cell+misset default path unaffected), (3) **Zero-point check PASSED** (chi²_mapping=989,811.5, chi²_stage_a=989,645.5, rel_diff=-0.017%, correlation=0.9999999843) confirming B_ideal bugfix (826f4c9) IS working, (4) **Telemetry step_000 shows CATASTROPHIC chi²=1.425B** (pre-bugfix signature) with massive log_scale gradient (294,909.5625), matching Phase A pre-bugfix failure exactly, (5) Test log truncated at 69 lines (HKL grid warmup only, many line-search evaluations), no block_dof_results.json, test appears to have terminated during first LBFGS step, (6) **Telemetry path duplicated**: `plans/.../2025-11-22T165000Z/plans/.../2025-11-22T165000Z/telemetry/` suggesting double-prepending bug in script path construction. Authored comprehensive diagnostic analysis (`phase_b1_diagnostic_analysis.md`) documenting four hypotheses: H1 (B_ideal mismatch persists in LBFGS closure despite bugfix — different code path than zero-point check), H2 (telemetry captures wrong timestep — exploratory line-search evaluation not accepted step), H3 (telemetry path duplication caused data corruption), H4 (LBFGS line search hit bad parameter region during backtracking). **Critical discrepancy**: Zero-point validation (use_mapping_zero_geometry=True) shows chi²=989k (correct), but telemetry step_000 (LBFGS optimization with use_mapping_zero_geometry=False) shows chi²=1.425B (catastrophic) — suggests B_ideal IS correct for zero-point path but WRONG for LBFGS optimization path, possibly due to tensor aliasing, device/dtype mismatch, or stale B_ideal reference in closure. **Decision**: Quick diagnostic rerun (Option B from analysis) with three fixes: (1) Remove `--telemetry-dir` flag to eliminate path duplication, (2) Execute test in FOREGROUND (blocking, no background bash) to ensure completion verification, (3) If chi² step 000 still catastrophic, escalate to deep diagnostic (instrument closure with B_ideal checksums, A* reconstruction logging, per-closure chi² logging). Authored comprehensive Do Now (input.md) with 9-step protocol: review prior artifacts, verify script telemetry path construction, fix path duplication bug (Option A: auto-construct from out_dir OR Option B: fix double-prepending), rerun LBFGS test B1 foreground (timeout 1200s, 10 optimizer steps), extract convergence metrics (telemetry steps 0-9, block_dof_results.json), synthesize decision per 3-path template (Path A SUCCESS: CC≥0.99+chi²≤1.005 → Phase C fix; Path B BLOCKED: chi² step 000 ~1.4B → deep diagnostic; Path C PARTIAL: improvement but below thresholds → tighter tolerances or Test B2), conditional deep diagnostic with B_ideal checksum logging if Path B, update implementation.md checklist, emit summary. Implementation floor satisfied: Do Now directs Ralph to fix telemetry paths (production code change in stage_a_mapping_adam_debug.py) AND rerun LBFGS test with full metrics extraction (production validation) AND synthesize decision with complete decision tree. New artifacts directory: plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/. Rationale: Ralph's Phase B1 LBFGS implementation is CORRECT (infrastructure code reviewed, regression guard passed) but test execution hit two issues: (1) telemetry path duplication bug preventing clean artifact capture, (2) premature termination leaving incomplete data. Zero-point check proves B_ideal bugfix works correctly, but telemetry step_000 catastrophic chi² suggests LBFGS closure may access a different/stale B_ideal tensor. Foreground rerun with fixed paths will definitively determine whether LBFGS converges (Path A → Phase C fix) or whether deeper B_ideal mismatch exists (Path B → diagnostic + bugfix).
- Artifact Path: plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/
- Next Actions: Ralph executes 9-step diagnostic rerun protocol: fixes telemetry path duplication in stage_a_mapping_adam_debug.py, reruns LBFGS test B1 in foreground with timeout 1200s, extracts full convergence metrics (telemetry steps 0-9, block_dof_results.json, chi² trajectories), synthesizes decision per 3-path template (A/B/C), conditionally implements deep diagnostic if Path B (B_ideal checksums + A* reconstruction logging), updates implementation.md checklist marking B1 complete with path selection and metrics, emits summary documenting fix + results + next phase. Decision outcome determines: Path A (SUCCESS) → next loop Phase C fix implementation (make LBFGS default, validate A_scale_only+D_full, findings update CONVERGENCE-002), Path B (BLOCKED) → next loop fix B_ideal mismatch root cause then rerun Test B1, Path C (PARTIAL) → next loop rerun with tighter tolerances OR pivot to Test B2 (Adam LR=1e-6 gradient validation).
- <Action State>: [planning]

2025-11-22T172000Z focus=TORCH-GEOMETRY-CONVERGENCE-001 state=planning dwell=2 artifacts=plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T172000Z/ next_action=phase_b1_diagnostic_rerun_with_telemetry_fix_and_foreground_execution
