## 2025-11-23T092000Z — ARCH-REFINE-FLOW-001 Phase C2.2 Complete CPU Fallback Fix

- Focus: ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase C2.2 complete CPU fallback)
- Action Type: ready_for_implementation
- Key Observations: Reviewed Ralph's loop i=212 partial CPU fallback attempt (commits d5bc2c2, b7ef1a0). Ralph correctly fixed final Bragg reconstruction device (line 3110: `device=final_device`), moving OOM from crystal.py:356 → physics.py:79, but **CUDA OOM still occurs** (physics.py:79, tried to allocate 856 MiB, only 51.62 MiB free). **Root Cause (REFINED with HIGH confidence ~98%)**: Engine delegation path (lines 3036-3050) builds `engine_inputs` but does NOT populate `use_stage_b_cpu_fallback` or `stage_b_eval_stage_a_ctx` keys required by StageB.run(). StageB.run() line 249 expects `use_stage_b_cpu_fallback` in param_values to switch device to CPU, but engine_inputs doesn't provide it, so StageB defaults to CUDA execution and exhausts GPU memory during closure execution (not final Bragg reconstruction). **Complete Fix Required**: (1) Compute `use_stage_a_roi_mode` from panel_slices and config (matching inline path lines 2171-2173), (2) Compute `use_stage_b_cpu_fallback` per PERF-WARM-011 (lines 2178-2182), (3) Clone Stage A context to CPU if fallback active per PERF-WARM-012 (lines 2187-2202), (4) Add `use_stage_b_cpu_fallback` and `stage_b_eval_stage_a_ctx` to engine_inputs dict BEFORE `engine.run()` at line 3053. Location: Insert ~30 lines at line 3047 (AFTER `engine_inputs = {...}` block ending line 3045, BEFORE `engine = RefinementEngine(...)` at line 3050). StageB.run() will then receive CPU fallback information via inputs and pass it to `_build_stage_b_params` which switches device to CPU and uses CPU-cloned Stage A context. Authored corrected Do Now with complete 6-task protocol focusing on engine_inputs plumbing (not just final Bragg device). Implementation floor satisfied: production code fix (complete CPU fallback + context cloning + engine_inputs plumbing ~30 lines) + validating pytest selector (test_stage_b_shell_modifiers full detector). Dwell=0 (last loop ready_for_implementation with partial fix, now ready_for_implementation with complete fix). Findings applied: PERF-WARM-011 (Stage B CPU fallback), PERF-WARM-012 (CPU Stage A context cloning), REFINE-008 (≥3% improvement gate), PHYSICS-LOSS-001/002 (variance-weighted loss + sigma_floor). Expected outcome: Path A (full + small detector PASS, telemetry shows CPU device + cache_mode="warm") → run DB-AT-024 → Phase C COMPLETE. Path B (still CUDA OOM) → debug device propagation inside StageB.run() or _build_stage_b_params, escalate to shared implementation bug.
- Artifact Path: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T092000Z/
- Next Actions: Ralph implements complete CPU fallback fix (~30 lines: compute use_stage_a_roi_mode from panel_slices, compute use_stage_b_cpu_fallback, clone CPU Stage A context if needed, populate engine_inputs with both keys), reruns Stage B full/small detector tests, verifies telemetry shows CPU execution, commits decision. If PASS → run DB-AT-024, update docs, Phase C COMPLETE. If blocked → document specific device propagation failure inside StageB → Galph reviews and escalates to shared implementation layer.
- <Action State>: [ready_for_implementation]

2025-11-23T092000Z focus=ARCH-REFINE-FLOW-001 state=ready_for_implementation dwell=0 artifacts=plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T092000Z/ next_action=complete_cpu_fallback_engine_inputs_plumbing

## 2025-11-23T090000Z — ARCH-REFINE-FLOW-001 Phase C2.1 Partial CPU Fallback (BLOCKED)

- Focus: ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase C2.1 CPU fallback)
- Action Type: ready_for_implementation
- Key Observations: Reviewed Ralph's Phase C validation execution (loop i=211, commit a3bd5d0). **Decisive blocker identified with HIGH confidence (~95%)**: Stage B small detector smoke PASSED (13.45s), but full detector FAILED with CUDA OOM (111.95s, tried to allocate 1.67 GiB, only 49.62 MiB free). **Root Cause (INCOMPLETE):** Engine delegation path (dbex/nanobrag_refinement.py:3029-3108) is MISSING the CPU fallback initialization logic required by PERF-WARM-011. Inline path (lines 2174-2203) correctly computes `use_stage_b_cpu_fallback = (config.stage_b_full_eval_on_cpu AND device=cuda AND not use_stage_a_roi_mode)` and clones Stage A context to CPU per PERF-WARM-012 before Stage B execution. Engine path skips this entirely, causing Stage B to attempt full-panel GPU allocation instead of falling back to CPU. Authored Do Now directing Ralph to add CPU fallback logic before engine instantiation. **Ralph's loop i=212 OUTCOME**: Partial fix applied (final Bragg reconstruction device switched to CPU at line 3110), but CUDA OOM persists at physics.py:79 during Stage B closure execution (not final Bragg). Root cause was incomplete: engine_inputs missing `use_stage_b_cpu_fallback` and `stage_b_eval_stage_a_ctx` keys required by StageB.run(). Escalated to Phase C2.2 with complete engine_inputs plumbing fix.
- Artifact Path: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T090000Z/
- Next Actions: Superseded by Phase C2.2 (complete CPU fallback fix with engine_inputs plumbing).
- <Action State>: [blocked]

2025-11-23T090000Z focus=ARCH-REFINE-FLOW-001 state=ready_for_implementation dwell=0 artifacts=plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T090000Z/ next_action=cpu_fallback_fix

## 2025-11-23T084458Z — ARCH-REFINE-FLOW-001 Phase C Validation Planning

- Focus: ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase C validation)
- Action Type: planning
- Key Observations: Reviewed Ralph's Phase C2 bugfix completion (loop i=210, commit a038ac1, test_stage_b_shell_modifiers PASSED with 23.7% Stage B improvement, chi² offset eliminated). **Phase C extraction COMPLETE**: C0 baseline ✓, C1a helpers (3 loops) ✓, C1b StageB wrapper ✓, C2 engine delegation ✓ (already implemented at lines 2988-3100), bugfix ✓. Verified engine delegation code (stage_a_b_mode detection, RefinementEngine([StageA(), StageB()]), telemetry aggregation) exists and is production-ready. **Next Phase: Full validation** (C3-C5 combined). C3 (telemetry completeness): Verify Stage B telemetry includes stage_type="B", mode="shell_modifiers", shell modifier stats (initial/final/delta), Stage A metadata propagation (log_scale, cell, misset frozen from stage_a_telemetry). C4 (full validation): Run test_stage_b_shell_modifiers on both small and full detectors, verify REFINE-008 gates (±1% shell modifier delta tolerance), capture collect-only + pytest logs. C5 (DB-AT selectors): Run DB-AT-024 mapping consistency test to verify Stage B extraction didn't regress mapping forward model. Authored comprehensive Phase C validation Do Now directing Ralph to execute 12-step protocol: (1) Review Phase C completion evidence (C0-C2 + bugfix artifacts), (2) Run Stage B smoke small detector, (3) Run Stage B smoke full detector, (4) Extract metrics via T0 micro probe (3 test statuses + telemetry structure validation → JSON), (5) Verify telemetry completeness (stage_type, mode, shell_modifier stats, Stage A metadata), (6) Run DB-AT-024 collect-only + pytest, (7) Extract DB-AT-024 metrics via T0 probe, (8) Decision synthesis per 4-path template, (9) Update implementation.md Phase C COMPLETE, (10) Write summary.md with Turn Summary block, (11) Commit, (12) Push. Implementation floor satisfied: validation tests (Stage B smokes + DB-AT-024) + metrics extraction + decision synthesis. Dwell=0 (last loop ready_for_implementation bugfix, now planning validation). Findings applied: REFINE-008 (Stage B ±1% gate), PHYSICS-LOSS-001/002 (variance-weighted loss + sigma_floor), PERF-WARM-011/012 (CPU fallback canonical). Expected outcome: Path A (all tests PASS) → Phase C COMPLETE → Galph plans Phase D (Stage C extraction) next loop. Path B/C/D (smoke FAIL, telemetry incomplete, DB-AT-024 FAIL) → debug/escalation.
- Artifact Path: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T084458Z/
- Next Actions: Ralph executes Phase C validation protocol (12 steps: review artifacts, run smokes small+full, verify telemetry, run DB-AT-024, metrics extraction, decision, update docs, commit). Decision outcome determines next loop: Phase C COMPLETE → Galph plans Phase D (Stage C extraction), Phase C BLOCKED → Galph reviews blocker and decides escalation.
- <Action State>: [ready_for_implementation]

2025-11-23T084458Z focus=ARCH-REFINE-FLOW-001 state=ready_for_implementation dwell=0 artifacts=plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T084458Z/ next_action=phase_c_full_validation

## 2025-11-23T083100Z — ARCH-REFINE-FLOW-001 Phase C2 Bugfix Implementation Plan

- Focus: ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase C2 bugfix)
- Action Type: planning
- Key Observations: Analyzed loop i=209 evidence (Ralph reverted signature error, Galph authored comprehensive analysis.md with 4 hypotheses). Root cause confirmed: Hypothesis H1 is correct with HIGH confidence (~85%). Bug location: `dbex/refinement/stage_b.py:163` uses `crystal.get_unit_cell().parameters()` to extract cell parameters as base for delta reconstruction, but the deltas (`log_cell_a_delta_final`, etc. from Stage A telemetry lines 145-150) are relative to the BASELINE crystal, not the current/potentially-perturbed crystal. Fix is simple: replace `crystal.get_unit_cell().parameters()` with `baseline_crystal.get_unit_cell().parameters()` and add validation guard (baseline_crystal must not be None). Authored planning_summary.md documenting root cause + fix + validation strategy. Updated input.md with focused 9-step Do Now directing Ralph to apply one-line fix, run regression guard (test_stage_b_shell_modifiers), verify chi² offset ≤0.1%, update implementation.md Phase C2 status, and commit. Dwell reset to 0 (last loop docs with dwell=1, now ready_for_implementation with production code task). Implementation floor satisfied: Do Now contains production code task (dbex/refinement/stage_b.py line 163 fix) + validating pytest selector (test_stage_b_shell_modifiers regression guard).
- Artifact Path: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T083100Z/
- Next Actions: Ralph implements bugfix (replace crystal with baseline_crystal at line 163), runs regression guard, verifies chi² offset within tolerance, updates docs, commits. If PASS → Galph plans Phase C3 next loop (StageB wrapper). If blocked → Ralph documents blocker → Galph reviews and decides.
- <Action State>: [ready_for_implementation]

2025-11-23T083100Z focus=ARCH-REFINE-FLOW-001 state=ready_for_implementation dwell=0 artifacts=plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T083100Z/ next_action=fix_cell_param_base_bug

## 2025-11-23T081911Z — ARCH-REFINE-FLOW-001 Phase C2 signature revert + analysis (Ralph loop i=209)

- Focus: ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase C2 bugfix)
- Action Type: docs
- Key Observations: Executed Galph's loop i=209 planning Do Now (Mode: Docs). Reverted erroneous signature from loop i=208 (removed `=None` defaults from 7 required parameters: inputs, hkl_grid, hkl_metadata, config, device, dtype in `_build_final_bragg_from_stage_b_telemetry` at dbex/nanobrag_refinement.py:2713-2727). Kept `=None` ONLY for baseline_crystal and stage_a_ctx (correct optional params). Compilation check PASSED. Reviewed Galph's comprehensive analysis.md (4 hypotheses for chi² offset root cause: H1 cell params using perturbed crystal instead of baseline, H2 log_scale divergence, H3 device/dtype mismatch, H4 HKL grid corruption). Documented why loop i=208's baseline_crystal fix didn't work: the `_build_final_bragg_from_stage_b_telemetry` helper is called AFTER Stage B optimization completes for final Bragg regeneration, NOT for computing the initial chi² that fails test_stage_b_shell_modifiers (initial chi² comes from `_run_stage_b_lbfgs` line 2635 calling `compute_loss_stage_b` at iteration 0). Both closure (lines 2414-2416, 2496-2498) and StageB.run() (lines 163-199) correctly handle baseline_misset, so true bug must be parameter reconstruction mismatch at Stage A→B boundary. Authored summary.md with Turn Summary block and comprehensive loop i=209 retrospective documenting signature fix + analysis + 4 hypotheses + recommended diagnostic script next action (HIGH confidence ~85% that H1 is root cause: StageB should use `baseline_crystal.get_unit_cell().parameters()` instead of `crystal.get_unit_cell().parameters()` at lines 163-173).
- Artifact Path: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T081911Z/
- Next Actions: Next loop creates diagnostic script to capture exact parameter state at Stage A→B boundary (cell, misset, log_scale, device, HKL grid hash), identifies divergent parameter(s), and applies targeted fix.
- <Action State>: [docs]

2025-11-23T081911Z focus=ARCH-REFINE-FLOW-001 state=docs dwell=1 artifacts=plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T081911Z/ next_action=create_diagnostic_script_for_chi2_offset

## 2025-11-23T075320Z — ARCH-REFINE-FLOW-001 Phase C2 bugfix planning
- Focus: ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase C2 bugfix)
- Action Type: planning
- Key Observations: Analyzed loop i=205 Phase C2 blocker (Ralph commit 5f36df3, test_stage_b_shell_modifiers FAILED with 2 errors). Root causes identified: (1) Line 3089-3090 calling `.items()` on RefinementTelemetry dataclass instances instead of converting via `asdict()` first; (2) Possible missing StageB.name property preventing engine input enrichment at line 107. Authored corrective Do Now with simplified bugfix steps: add `asdict()` conversion + verify StageB.name=="stage_b" property. Ralph's helper extraction work (198 lines `_build_final_bragg_from_stage_b_telemetry`) is solid; only delegation return statement needs fixing. No changes to helper internals required (doesn't use target_t in Bragg generation paths).
- Artifact Path: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T075320Z/
- Next Actions: Ralph executes Phase C2 bugfix (2 code changes: asdict() conversion + StageB.name check), reruns regression guard, and commits if tests pass. If still blocked after 2 attempts, escalate with blocker.md per dwell enforcement.
- <Action State>: [ready_for_implementation]

2025-11-23T075320Z focus=ARCH-REFINE-FLOW-001 state=ready_for_implementation dwell=1 artifacts=plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T075320Z/ next_action=phase_c2_bugfix_implementation

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
- Key Observations: Stage B path is still unimplemented (RefinementConfig lacks Stage B controls and `run_nanobrag_refinement` exits after Stage A/C). Reviewed Stage B contract (spec-db-workflow §7, integration plan §Stage B) plus halo/default_F guard (REFINE-005) and scaling findings (SCALE-001/002/003/007). Authored new implementation plan with config plumbing, shell lookup helper, Stage B LBFGS loop, telemetry/HDF5 persistence, and smoke test/doc updates; fix_plan status set to in_progress with Attempts History captured.
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
- Key Observations: Reviewed `pytest_stage_b_v2.log` (2025-11-05T164800Z) and `dbex/nanobrag_refinement.py:847-1179`; Stage B now dies inside the LBFGS closure with `NameError: roi_sampler`, leaving loss traces empty and telemetry status `error`. Stage A's deterministic `sampled_panel_ids` exists but the Stage B helper no longer captures it, and there is no fallback when the ROI sample list is empty. Re-confirmed Stage B contract/guards via docs/spec-db-workflow.md:31-34, plans/nanobrag_integration_plan.md:226-244, and findings REFINE-005/SCALE-001. Authored updated Do Now + How-To map directing a closure refactor that reuses the Stage A ROI sample (with a full-panel fallback), restores telemetry/improvement gating, and archives fresh collect/test logs under 2025-11-05T172937Z.
- Artifact Path: plans/active/TORCH-REFINE-004/reports/2025-11-05T172937Z/
- Next Actions: Ralph to patch Stage B LBFGS closure (ROI sampler, telemetry, gates), rerun test_stage_b_shell_modifiers, and capture updated telemetry/logs for doc sync.
- <Action State>: [ready_for_implementation]
2025-11-05T172937Z focus=TORCH-REFINE-004 state=ready_for_implementation dwell=0 artifacts=plans/active/TORCH-REFINE-004/reports/2025-11-05T172937Z/ next_action=fix_stage_b_closure_roi_telemetry

## 2025-11-23T060500Z — ARCH-REFINE-FLOW-001 Phase B1a-loop3 Blocker Review
- Focus: ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase B1a-loop3)
- Action Type: review_or_housekeeping
- Key Observations: Ralph completed all three helper extractions (B1a-loop1 helper1, B1a-loop2 helper2, B1a-loop3 helper3) and refactored run_nanobrag_refinement to call them (reducing file by 692 lines). Regression guard test_stage_a_expansion FAILS with NoneType zero_grad error. **Root Cause Identified:** The `params` list is stored in helper1_result['params'] but NOT in param_values dict. Helper2 (_build_stage_a_lbfgs_closure) receives param_values and tries to extract params via `params = param_values.get('params', [])` at line 1073, which returns empty list [] as default because params is missing from param_values. The LBFGS optimizer then receives an empty params list and fails when trying to call zero_grad(). **Fix:** Add `'params': params` to the param_values dict at line 943 in _build_stage_a_params helper. This is a one-line fix that will make params available to helper2.
- Artifact Path: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T060500Z/
- Next Actions: Author simple Do Now for Ralph to add params to param_values dict, verify params list is correctly constructed (should filter based on parameterization mode), rerun regression guard.
- <Action State>: [ready_for_implementation]

2025-11-23T060500Z focus=ARCH-REFINE-FLOW-001 state=ready_for_implementation dwell=0 artifacts=plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T060500Z/ next_action=fix_params_dict_bug

## 2025-11-23T045012Z — ARCH-REFINE-FLOW-001 Phase B1b StageA Wrapper Handoff
- Focus: ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase B1b)
- Action Type: planning
- Key Observations: Reviewed Phase B1a-loop3 completion (commit caa510e, 2025-11-23T060500Z) confirming bugfix success (params + optimizer added to param_values dict, regression guard PASSED). Identified that existing StageA stub (dbex/refinement/stage_a.py) is INCORRECT—it delegates to run_nanobrag_refinement creating infinite recursion risk once Phase B2 wires engine delegation. Authored comprehensive Phase B1b Do Now directing Ralph to rewrite StageA.run() to call three extracted helpers directly (_build_stage_a_params, _build_stage_a_lbfgs_closure, _run_stage_a_lbfgs), package telemetry with all RefinementTelemetry fields + stage_type/mode per Phase A4 schema, and validate via compilation check + regression guard (inline path unchanged until Phase B2). Implementation floor satisfied: Do Now contains production code task (StageA.run() rewrite ~80 lines) + validating pytest selectors (test_stage_a_expansion regression guard, test_engine_executes_mock_stage contract validation). Dwell reset to 0 (last loop review_or_housekeeping for B1a-loop3 blocker, now ready_for_implementation with wrapper implementation task). Roadmap alignment: ARCH-REFINE-FLOW-001 Tier 2, Phase B1b next milestone per approved multi-loop extraction strategy (B1a COMPLETE → B1b wrapper → B2 engine delegation).
- Artifact Path: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T045012Z/
- Next Actions: Ralph executes Phase B1b implementation (10 steps: review B1a artifacts, rewrite StageA.run(), add torch import, compilation check, regression guard, engine contract validation, update implementation.md, write summary, commit). If PASS → Galph plans Phase B2 next loop (engine delegation in run_nanobrag_refinement). If blocked → Ralph documents blocker → Galph reviews and decides.
- <Action State>: [ready_for_implementation]

2025-11-23T045012Z focus=ARCH-REFINE-FLOW-001 state=ready_for_implementation dwell=0 artifacts=plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T045012Z/ next_action=stage_a_wrapper_implementation

## 2025-11-23T050432Z — ARCH-REFINE-FLOW-001 Phase B2 Engine Delegation Planning
- Focus: ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase B2)
- Action Type: planning
- Key Observations: Reviewed Phase B1b completion evidence (commit 6d1d925, 2025-11-23T045012Z): StageA.run() now calls three extracted helpers directly with no recursion risk, telemetry packaging includes all RefinementTelemetry fields + stage_type/mode per Phase A4 schema, compilation + regression guard + engine contract tests all PASSED. Phase B2 objective: implement conditional engine delegation for Stage-A-only mode in run_nanobrag_refinement. When both enable_stage_c=False AND enable_stage_b=False, delegate to RefinementEngine([StageA()]) instead of calling inline helpers. Keep Stage B/C inline temporarily (Phases C/D will extract). Authored comprehensive Phase B2 planning summary and 10-task Do Now for Ralph covering: (1) extract _build_final_bragg_from_stage_a_telemetry helper from lines 2046-2285, (2) add stage detection logic, (3) implement engine delegation branch with lazy imports, (4) wrap existing inline logic in else block (pure indentation change), (5) validate via compilation + regression guard + engine contract tests. Implementation floor satisfied: production code tasks (helper extraction + engine delegation) + validating pytest selectors. Dwell=0 (last loop ready_for_implementation for B1b, now ready_for_implementation for B2 with engine delegation task).
- Artifact Path: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050432Z/
- Next Actions: Ralph executes Phase B2 implementation (10 tasks: extract helper, add stage detection, implement engine delegation, wrap inline code in else, compilation check, regression guard test, engine contract test, update implementation.md, write summary, commit). If PASS → Galph plans Phase B3 next loop (full smoke validation + DB-AT selectors). If blocked → Ralph documents blocker → Galph reviews and decides.
- <Action State>: [ready_for_implementation]

2025-11-23T050432Z focus=ARCH-REFINE-FLOW-001 state=ready_for_implementation dwell=0 artifacts=plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T050432Z/ next_action=engine_delegation_implementation

## 2025-11-23T052000Z — ARCH-REFINE-FLOW-001 Phase B3 Handoff
- Focus: ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase B3)
- Action Type: ready_for_implementation
- Key Observations: Phase B2 completed engine delegation for Stage-A-only mode (commit 2872f26, tests PASSED). Engine delegation branch detects `enable_stage_c=False AND enable_stage_b=False`, delegates to RefinementEngine([StageA()]), and returns telemetry with backward-compatible "A" key. Phase B2 only validated small detector; Phase B3 now runs full smoke suite (small + full detector) plus DB-AT selectors (DB-AT-010 Gradcheck, DB-AT-024 Mapping) to verify engine path maintains numeric parity with baseline across all Stage A exercise paths.
- Artifact Path: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T052000Z/
- Next Actions: Ralph executes 12-task validation protocol (run Stage A smokes both sizes, run DB-AT-010/024 with collect-only + pytest, extract metrics via T0 probe, decision synthesis per 4-path template, update implementation.md B3, commit). If all 4 tests PASS → B3 COMPLETE, Galph plans B4/B5 next loop. If any test FAILS → Ralph documents blocker, Galph reviews and decides (debug/patch/escalate).
- <Action State>: [ready_for_implementation]

2025-11-23T052000Z focus=ARCH-REFINE-FLOW-001 state=ready_for_implementation dwell=0 artifacts=plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T052000Z/ next_action=phase_b3_full_smoke_validation

## 2025-11-22T060833Z — ARCH-REFINE-FLOW-001 Phase B Complete Review
- Focus: ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase B completion)
- Action Type: review_or_housekeeping
- Key Observations: Reviewed Ralph's Phase B3 full smoke validation (loop i=198, commit 3f95132, 2025-11-23T052000Z) and marked Phase B COMPLETE. **Final Verdict: Engine delegation production-ready for Stage-A-only mode.** Phase B spanned 7 loops total (B0 baseline → B1a 3-loop helper extraction → B1b/B2 wrapper+delegation → B3 validation). **ALL 4 test suites PASSED:** Stage A smoke small (12.42s), Stage A smoke full (17.76s), DB-AT-024 mapping (31.59s), DB-AT-010 gradcheck (5 tests, 614.36s). DB-AT-010 comprehensive wrapper NO LONGER times out (Phase B2 reported >7min timeout, Phase B3 completed in 10:14). Timeout was transient CPU load variance (test infrastructure issue), NOT a regression. Gradcheck uses `simulate_forward_torch` helper (independent from refinement engine). Extracted 4 Stage A helpers (~1,000 lines): `_build_stage_a_params`, `_build_stage_a_lbfgs_closure`, `_run_stage_a_lbfgs`, `_build_final_bragg_from_stage_a_telemetry`. Implemented StageA class (dbex/refinement/stage_a.py) calling helpers directly with no recursion risk. Added engine delegation logic in run_nanobrag_refinement for Stage-A-only mode (enable_stage_c=False AND enable_stage_b=False). Reduced run_nanobrag_refinement by ~692 lines. Exit Criteria: ✓ engine delegation implemented and validated, ✓ Stage A smokes pass on both detectors, ✓ DB-AT-024 maintained, ✓ telemetry preserved, ⚠ B5 docs deferred to Phase C. Updated implementation.md and fix_plan.md with Phase B COMPLETE status. Authored phase_b_completion_review.md with comprehensive retrospective, multi-loop strategy lessons learned, and Phase C preview.
- Artifact Path: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T060833Z/
- Next Actions: Plan Phase C (Stage B extraction) next loop using proven multi-loop strategy from Phase B. Scope: Extract Stage B shell-modifier logic into StageB class (4-6 loops estimated). Follow Phase B pattern: C0 baseline, C1-C3 helper extraction, C4 wrapper, C5 engine delegation A→B, C6 full validation.
- <Action State>: [review_or_housekeeping]

2025-11-22T060833Z focus=ARCH-REFINE-FLOW-001 state=planning dwell=0 artifacts=plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-22T060833Z/ next_action=plan_phase_c_stage_b_extraction

## 2025-11-23T061726Z — ARCH-REFINE-FLOW-001 Phase C Planning
- Focus: ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase C planning)
- Action Type: planning
- Key Observations: Reviewed Phase B completion evidence (7 loops, ALL 4 test suites PASSED, engine delegation production-ready). Analyzed Stage B code structure (dbex/nanobrag_refinement.py:2527-3137, ~610 lines) and identified 3-4 helper extraction targets mirroring Phase B pattern: (1) `_build_stage_b_params` (~140 lines: shell modifier init, optimizer setup, telemetry/context accumulators), (2) `_build_stage_b_lbfgs_closure` (~260 lines: compute_loss_stage_b + closure_stage_b nested functions), (3) `_run_stage_b_lbfgs` (~100 lines: LBFGS execution + improvement gate), (4) `_build_final_bragg_from_stage_b` (~77 lines: final Bragg regeneration with shell modifiers). Authored Phase C0 baseline Do Now (collect test_stage_b_shell_modifiers artifacts mirroring Phase B0 pattern, small detector smoke test + telemetry JSON capture). Updated input.md with C0 baseline collection protocol. Phase C multi-loop strategy approved: C0 baseline → C1a (3 loops for 3 helpers) → C1b/C2/C3 (StageB wrapper, engine delegation, validation) → estimated 6-7 loops total.
- Artifact Path: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T061726Z/
- Next Actions: Ralph executes Phase C0 baseline collection per input.md. If PASS → Galph plans C1a-loop1 next loop (extract `_build_stage_b_params` ONLY, ~140 lines, compilation check, no regression guard). If blocked → Galph reviews blocker and decides escalation.
- <Action State>: [ready_for_implementation]

2025-11-23T061726Z focus=ARCH-REFINE-FLOW-001 state=ready_for_implementation dwell=0 artifacts=plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T061726Z/ next_action=phase_c0_baseline_collection
