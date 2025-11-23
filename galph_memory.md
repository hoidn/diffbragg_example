
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
- Key Observations: Reviewed Phase B1a-loop3 completion (commit caa510e, 2025-11-23T060500Z) confirming bugfix success (params + optimizer added to param_values dict, regression guard PASSED). Identified that existing StageA stub (dbex/refinement/stage_a.py) is INCORRECT—it delegates to run_nanobrag_refinement creating infinite recursion risk once Phase B2 wires engine delegation. Authored comprehensive Phase B1b Do Now directing Ralph to rewrite StageA.run() to call three extracted helpers directly (_build_stage_a_params, _build_stage_a_lbfgs_closure, _run_stage_a_lbfgs), package telemetry with all RefinementTelemetry fields + stage_type/mode per Phase A4 schema, and validate via compilation check + regression guard (inline path unchanged until Phase B2). Implementation floor satisfied: Do Now contains production code task (StageA.run() rewrite) + validating pytest selectors (test_stage_a_expansion regression guard, test_engine_executes_mock_stage contract validation). Dwell reset to 0 (last loop review_or_housekeeping for B1a-loop3 blocker, now ready_for_implementation with wrapper implementation task).
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
