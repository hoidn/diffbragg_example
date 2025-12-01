2025-12-01T08:09:03Z focus=ARCH-REFINE-001 state=planning dwell=1 action=planning artifacts=plans/active/ARCH-REFINE-001/reports/2025-12-01T080903Z/ next_action=ready_for_implementation
- Stage A helper stack (StageAContext, quaternion utils, `_build_stage_a_*`) still lives inside `dbex.nanobrag_refinement`, forcing StageA/StageB wrappers to import the monolith and blocking full engine delegation. Tonight's plan splits those helpers into a refinement-owned module, reuses it from the inline path, and keeps telemetry/perf counters intact per PHYSICS-LOSS-001 + PERF-WARM-001.
- Do Now handed to Ralph: relocate the helpers/dataclasses + quaternion math into `dbex/refinement/` (no new circular imports), update all consumers (StageA, inline LBFGS, tools), then rerun the Stage A expansion + engine telemetry selectors plus the Stage B shell smoke to ensure parameter reconstruction and warm caches survive.
Action State: ready_for_implementation
2025-12-01T084505Z focus=ARCH-REFINE-001 state=ready_for_implementation dwell=2 action=planning artifacts=plans/active/ARCH-REFINE-001/reports/2025-12-01T084505Z/ next_action=ready_for_implementation
- Planned Phase A.2 Stage B helper extraction (new stage_b_impl module, ASU/shell utilities move, StageB+inline imports) and refreshed Do Now/tests accordingly.
- Updated docs/fix_plan.md Attempts History plus input.md (Do Now + How-To Map) so Ralph can execute helper migration with Stage B shell/per-reflection smokes.
Action State: ready_for_implementation
2025-12-01T090517Z focus=ARCH-REFINE-001 state=ready_for_implementation dwell=2 action=planning artifacts=plans/active/ARCH-REFINE-001/reports/2025-12-01T090517Z/ next_action=Implement stage_c_impl + rerun Stage C smoke
- Scoped Stage C helper extraction (stage_c_impl) so Stage C inline/wrapper paths stop importing dbex.nanobrag_refinement and warm-cache retargeting lives beside Stage A/B helper modules; documented plan + env/test wiring.
- Updated docs/fix_plan.md Attempts History with Phase A.3 notes and rewrote input.md (Do Now, How-To Map, pitfalls) directing Ralph to create stage_c_impl, relocate `_retarget_stage_a_detectors`, and run `test_stage_c_detector_microslip`.
- No evidence runs this loop; artifacts carry planning/writeups only so next loop must implement code + execute the Stage C smoke selector.
Action State: ready_for_implementation
2025-12-01T092807Z focus=ARCH-REFINE-001 state=ready_for_implementation dwell=2 action=planning artifacts=plans/active/ARCH-REFINE-001/reports/2025-12-01T092807Z/ next_action=Implement engine-only Stage B/C path + rerun merged smokes
- Drove Phase A.4 scoping: confirmed run_nanobrag_refinement still defaults to the inline Stage B/C branch whenever Stage C is enabled, and outlined removal steps (engine-only routing, stage list guards, final Bragg reconstruction per stage).
- Planned the StageC.run + RefinementEngine updates needed to propagate `_run_stage_c_lbfgs`' bragg buffer, and documented the CLI/test churn (drop `--use-engine-delegation`, always run through the engine) plus the combined Stage B/C smoke selector.
- Retrospective (loops 2025-12-01T080903Z..T090517Z): prior Do Nows were followed (Stage A/B/C helper moves merged), only outstanding issue is the legacy inline branch; no hygiene/telemetry drift observed.
Action State: ready_for_implementation
2025-12-01T095317Z focus=ARCH-REFINE-001 state=ready_for_implementation dwell=2 action=planning artifacts=plans/active/ARCH-REFINE-001/reports/2025-12-01T095317Z/ next_action=Repair Stage A telemetry baselines + rerun Stage C smoke
- Stage B/C pytest log shows Stage A `loss_trace_full` often empty (IndexError in Stage B smoke) and Stage C gate sees 0.00% improvement + 2.6% chi² offset; attempted to rerun a reproduction script but missing `sp.proc/refGeom_small/refGeom_small.expt` blocked fresh evidence in this workspace.
- New Do Now directs Ralph to patch `dbex/refinement/stage_a_impl.py::_run_stage_a_lbfgs` so Stage A baseline/final chi² samples are always recorded before Stage C runs, add guards in `StageC.run`/engine telemetry to enforce equality with Stage A final, and re-run the small-detector Stage B/C smoke selector capturing logs under the new report directory.
Action State: ready_for_implementation
2025-12-01T101946Z focus=ARCH-REFINE-001 state=planning dwell=3 action=evidence_collection artifacts=plans/active/ARCH-REFINE-001/reports/2025-12-01T100847Z/ next_action=Restore refGeom_small assets then rerun Stage B/C probe
- Authored the reusable telemetry probe (plans/active/ARCH-REFINE-001/bin/capture_stage_c_stage_a_probe.py) and attempted to replay the Stage C smoke config, but it immediately failed because `sp.proc/refGeom_small/{refGeom_small.expt,refGeom_small.refl,refGeom_small_mask.pkl}` are missing in this workspace.
- Logged the dataset gap + probe output in docs/fix_plan.md and the new report directory; Stage A zero-improvement diagnosis remains blocked until the small-detector bundle is regenerated per docs/data_dependency_manifest.md.
Action State: blocked
2025-12-01T103900Z focus=ARCH-REFINE-001 state=ready_for_implementation dwell=0 action=planning artifacts=plans/active/ARCH-REFINE-001/reports/2025-12-01T103325Z/ next_action=Wire panel-mode Stage A validations + rerun Stage C smoke
- Regenerated refGeom_small, reran the Stage A/C telemetry probe, and captured three regimes: ROI sampling (0.00% improvement), ROI fraction 1.0 (still ~0%), and forced panel mode (57.4% drop with Stage C initial matching Stage A final). Script now exposes `--roi-sample-fraction` / `--stage-a-roi-mode` knobs so future loops can compare behaviors.
- Root cause identified: Stage A baseline/final validations stay on the ROI subset, so the Stage C gate never sees improvement. New Do Now tells Ralph to add a StageA/RefinementConfig flag (auto-triggered when Stage C runs or ROI count ≤32) so `_build_stage_a_lbfgs_closure`/`_run_stage_a_lbfgs` evaluate the panel path for baseline/periodic/final validations while closures remain ROI-sampled; validation selector = Stage C small smoke.
Action State: ready_for_implementation
2025-12-01T105916Z focus=ARCH-REFINE-001 state=ready_for_implementation dwell=1 action=planning artifacts=plans/active/ARCH-REFINE-001/reports/2025-12-01T105916Z/ next_action=Auto-disable small-detector Stage A ROI mode + rerun Stage B/C smokes
- Logged REFINE-010 (docs/findings.md) after the stage_c_stage_a_probe traces proved ROI-mode LBFGS never improves on refGeom_small even with roi_sample_fraction=1.0, while panel mode drops chi² by 57%.
- Updated docs/fix_plan.md with the new Stage A ROI auto-panel Do Now plus telemetry evidence, rewrote input.md with the explicit Stage A implementation + Stage B/C validation plan, and captured this loop's summary stub under the new report directory.
Action State: ready_for_implementation
2025-12-01T112335Z focus=ARCH-REFINE-001 state=ready_for_implementation dwell=2 action=planning artifacts=plans/active/ARCH-REFINE-001/reports/2025-12-01T112335Z/ next_action=Fix Stage C warm-cache gradient tensors + rerun Stage B/C smoke
- Stage C small-detector smoke still fails because `_retarget_stage_a_detectors` (dbex/refinement/stage_c_impl.py:39-86) converts the bounded offsets into floats, so the warm-cache panel path detaches `distance_offset_raw` and PyTorch aborts with `element 0 of tensors does not require grad` (see plans/active/ARCH-REFINE-001/reports/2025-12-01T105916Z/pytest_stage_bc_small_v3.log).
- Logged GRADIENT-004, refreshed docs/fix_plan.md with the tensor-preserving Stage C plan, and rewrote input.md directing Ralph to patch the warm-cache retargeter and rerun the small-detector Stage B/C smokes under plans/active/ARCH-REFINE-001/reports/2025-12-01T112335Z/.
Action State: ready_for_implementation
2025-12-01T115900Z focus=ARCH-REFINE-001 state=ready_for_implementation dwell=0 action=planning artifacts=plans/active/ARCH-REFINE-001/reports/2025-12-01T115900Z/ next_action=Wire RefinementContext builder + stage refactor (Phase B.1)
- Closed the GRADIENT-004 loop (docs/findings.md now marked Resolved) and advanced the fix plan into Phase B by scoping RefinementContext scaffolding with explicit implementation/test bullets plus env guardrails.
- Rewrote input.md with the new Do Now (RefinementContext builder, engine/stage wiring, Stage A/B/C smokes) and captured the artifacts path for Ralph; this turn must hand off implementation so the next loop can write code immediately.
Action State: ready_for_implementation
2025-12-01T121200Z focus=ARCH-REFINE-001 state=ready_for_implementation dwell=1 action=planning artifacts=plans/active/ARCH-REFINE-001/reports/2025-12-01T121200Z/ next_action=Patch Stage A telemetry reconstruction + rerun Stage smokes
- Stage A smoke still crashes because `_build_final_bragg_from_stage_a_telemetry` passes `log_cell_a_delta`/`angle_alpha_raw` kwargs into `create_crystal_config`, which only accepts the override dict + misset tensors (see plans/active/ARCH-REFINE-001/reports/2025-12-01T115900Z/pytest_stage_a.log and dbex/nanobrag_refinement.py:321-339).
- Updated docs/fix_plan.md + input.md so Ralph clamps the Stage A deltas, builds `crystal_overrides`/`misset_deg_override` before calling `create_crystal_config`, and replays the Stage A/B/C small-detector smokes with telemetry under the new report directory to prove the context refactor stayed loss-neutral.
Action State: ready_for_implementation
2025-12-01T121221Z focus=ARCH-REFINE-001 state=ready_for_implementation dwell=2 action=planning artifacts=plans/active/ARCH-REFINE-001/reports/2025-12-01T121221Z/ next_action=Implement JobContext scaffolding + rerun Stage smokes/CLI selector
- Cleared the Phase B.1 blocker in docs/fix_plan.md and scoped Phase B.2 so JobContext (args/DataLoad/calibration/sigma/HKL metadata) can accompany the existing RefinementContext through the engine inputs.
- Rewrote input.md with the JobContext Do Now, explicit stage-smoke env wiring, and CLI selector so Ralph can land the dataclass + CLI/engine changes immediately.
Action State: ready_for_implementation
- Scoped Phase B.3 shared HKL context wiring: documented how CLI `build_structure_factor_grid` outputs (`asu_map`, halo metadata, HKL index grids) must be promoted into `RefinementContext`, StageB warm-cache code, and StageC retargeters, and captured the test/env plan so the next loop can implement immediately.
- Updated docs/fix_plan.md, input.md, and the report plan file with the new Do Now, Stage B/C smoke selectors, artifact path, and spec references (spec-db-workflow §§53-61, REFINE-005/REFINE-010).
Action State: ready_for_implementation
2025-12-01T123044Z focus=ARCH-REFINE-001 state=ready_for_implementation dwell=0 action=planning artifacts=plans/active/ARCH-REFINE-001/reports/2025-12-01T123044Z/ next_action=Thread asu_map/halo metadata through Stage B/C and rerun small-detector smokes
2025-12-01T130955Z focus=ARCH-REFINE-001 state=ready_for_implementation dwell=1 action=planning artifacts=plans/active/ARCH-REFINE-001/reports/2025-12-01T130955Z/ next_action=Implement factory wiring + rerun Stage B/C smokes
- Scoped Phase B.4 so Stage A/B final Bragg reconstruction helpers call create_unified_simulator on their cold paths, recorded the selector/env plan, and linked the work to ARCH-FACTORY-001 + REFINE-005/010 in docs/fix_plan.md.
- Replaced input.md with the factory-specific Do Now, collect-only + telemetry capture commands, and pitfalls covering CPU fallback and the "no factory inside closures" rule so Ralph can implement immediately next loop.
Action State: ready_for_implementation
2025-12-01T140500Z focus=ARCH-REFINE-001 state=ready_for_implementation dwell=2 action=planning artifacts=plans/active/ARCH-REFINE-001/reports/2025-12-01T140500Z/ next_action=Land B.5 context + CPU fallback tests then rerun targeted pytest module set
- Logged Phase B.5 in docs/fix_plan.md: unit-test updates for `RefinementEngine` (context enforcement), new `tests/dbex/test_refinement_context.py` covering JobContext/RefinementContext builders, and a mocked `_build_stage_b_params` CPU fallback test to lock in PERF-WARM-011/012 behavior per findings REFINE-010 + GRADIENT-003.
- Rewrote input.md pointing Ralph at the three test files (engine nucleus, context builders, CPU fallback), detailed collect-only + pytest commands, pitfalls (tests-only loop, no real CUDA allocations), and capture plan for the new artifact directory `plans/active/ARCH-REFINE-001/reports/2025-12-01T140500Z/`.
Action State: ready_for_implementation
2025-12-01T131510Z focus=ARCH-REFINE-001 state=ready_for_implementation dwell=2 action=planning artifacts=plans/active/ARCH-REFINE-001/reports/2025-12-01T131510Z/ next_action=Consolidate telemetry dataclass + rerun Stage B/C smokes
- Advanced Phase C.1 by recording the telemetry dataclass consolidation plan in docs/fix_plan.md: drop the duplicate `RefinementTelemetry` from `dbex/nanobrag_refinement.py`, point all stage wrappers/tests/tools at `dbex.refinement.stage`, and revalidate `/torch_diagnostics` selectors to prove the shared schema stays intact (per DIAGNOSTICS-001 + PHYSICS-LOSS-001).
- Rewrote input.md with the new production Do Now (nanobrag module cleanup, stage wrapper import updates, CLI telemetry test adjustments) plus the Stage B/C smoke + CLI telemetry + engine contract selectors and artifact paths under `plans/active/ARCH-REFINE-001/reports/2025-12-01T131510Z/`.
Action State: ready_for_implementation
2025-12-01T132921Z focus=ARCH-REFINE-001 state=ready_for_implementation dwell=0 action=planning artifacts=plans/active/ARCH-REFINE-001/reports/2025-12-01T132921Z/ next_action=Extract torch writer + rerun CLI telemetry selectors
- Logged Phase C.2 in docs/fix_plan.md: move `_write_torch_outputs` into `dbex/io/writer.py`, rewire `run_nanobrag_backend`, and update CLI tests to patch the shared module while preserving DIAGNOSTICS-001/PHYSICS-LOSS-001 contracts.
- Rewrote input.md with the new Do Now, mapped CLI selectors (refined MTZ telemetry + torch diagnostics metadata), env knobs, pitfalls, and artifacts path `plans/active/ARCH-REFINE-001/reports/2025-12-01T132921Z/`.
- No evidence collection this loop; artifacts directory reserved for the implementation run.
Action State: ready_for_implementation
2025-12-01T134542Z focus=ARCH-REFINE-001 state=ready_for_implementation dwell=1 action=planning artifacts=plans/active/ARCH-REFINE-001/reports/2025-12-01T134542Z/ next_action=Move gradcheck helpers into dbex.physics then rerun DB-AT-010
- Advanced Phase C.3 planning: docs/fix_plan.md now records the physics-helper extraction plan (new `dbex/physics/forward.py` + loss relocation), and the implementation checklist marks C1/C3 complete with C2 ready for execution.
- Replaced input.md with a code-ready Do Now covering the new physics modules, bridge re-exports, DB-AT-010 test updates, and the selector commands/artifacts Ralph must run to validate the move.
Action State: ready_for_implementation
2025-12-01T140937Z focus=ARCH-REFINE-001 state=ready_for_implementation dwell=2 action=planning artifacts=plans/active/ARCH-REFINE-001/reports/2025-12-01T140725Z/ next_action=Land Phase C.4 writer/doc-sync + CLI telemetry selector
- Logged the C.4 scope in docs/fix_plan.md (alias removal, CLI test guard, architecture/docs refresh) and marked the implementation plan's C2 checkbox complete so the ledger matches reality.
- Rewrote input.md with the writer/doc sync Do Now, mapped env commands, pitfalls, and explicit collect-only/full pytest selectors plus instructions to capture docs_diff.md for architecture edits.
Action State: ready_for_implementation
2025-12-01T142116Z focus=ARCH-REFINE-001 state=ready_for_implementation dwell=0 action=planning artifacts=plans/active/ARCH-REFINE-001/reports/2025-12-01T142116Z/ next_action=Ship writer/physics IDLs then rerun CLI telemetry + DB-AT-010
- Logged Phase D.1 in docs/fix_plan.md: new IDL files for dbex/io/writer.py and dbex/physics/{forward,loss}.py, docstring cross-references, module_map links, and the telemetry/gradcheck validation plan with explicit commands/env vars.
- Rewrote input.md to hand Ralph a docs-mode Do Now covering the new IDLs, docstring updates, module_map edits, and the CLI telemetry + DB-AT-010 selectors with artifact capture instructions.
Action State: ready_for_implementation
2025-12-01T144200Z focus=ARCH-REFINE-001 state=planning dwell=1 action=planning artifacts=plans/active/ARCH-REFINE-001/reports/2025-12-01T144500Z/ next_action=Stage A tooling/doc cleanup + run DB-AT-027 + telemetry smokes
- Logged Phase D.2 in docs/fix_plan.md: remove the obsolete `use_engine_delegation` flag from Stage A tooling/TOOLING-VIS-001 drivers, refresh architecture + testing docs, and revalidate DB-AT-027 + Stage A telemetry selectors under the new timestamp.
- Updated implementation plan Phase D checklist (D1/D3/D4 now complete, D2 focused on flag cleanup) and rewrote input.md with production Do Now + mapped pytest commands so Ralph can implement immediately.
Action State: ready_for_implementation
- Recorded Phase D.2 completion in docs/fix_plan.md and the implementation plan so the ledger reflects the Stage A tooling/docs/tests already merged, with pointers to plans/active/ARCH-REFINE-001/reports/2025-12-01T144500Z/.
- Planned Phase D.5 by drafting the architecture_doc_update.md deliverable, mapping the new artifacts path, refreshing Stage A selector commands, and rewriting input.md so Ralph can publish the ledger immediately.
Action State: ready_for_implementation
2025-12-01T150955Z focus=ARCH-REFINE-001 state=ready_for_implementation dwell=0 action=planning artifacts=plans/active/ARCH-REFINE-001/reports/2025-12-01T150955Z/ next_action=Publish architecture_doc_update.md + docs_diff, update docs/fix_plan.md, rerun Stage A parity + telemetry selectors
- Scoped Phase E (Stage B baseline parity) in implementation.md, marking earlier phase checklists complete and capturing the new E1–E3 tasks tied to REFINE-FLOW-001.
- Logged the Phase E.1 plan in docs/fix_plan.md and rewrote input.md with the production Do Now (stage_b_impl/stage_b.py instrumentation + Stage B/C small-detector smoke).
Action State: ready_for_implementation
2025-12-01T151425Z focus=ARCH-REFINE-001 state=ready_for_implementation dwell=1 action=planning artifacts=plans/active/ARCH-REFINE-001/reports/2025-12-01T151425Z/ next_action=Land Stage B baseline parity instrumentation/guard and rerun Stage B/C smokes
2025-12-01T153327Z focus=ARCH-REFINE-001 state=ready_for_implementation dwell=2 action=planning artifacts=plans/active/ARCH-REFINE-001/reports/2025-12-01T153327Z/ next_action=Implement per-panel Stage B parity JSON + rerun Stage B/C smokes
- Stage B guard now reports `stage_b_baseline_rel_diff`, but the JSON payload is still a stub (no per-panel breakdown, hard-coded artifacts path), so REFINE-FLOW-001 diagnostics remain unusable when the guard fires.
- Updated docs/fix_plan.md with the new Phase E.1 refinement scope, rewrote input.md (Do Now + How-To Map + pitfalls/tests), and reserved the 2025-12-01T153327Z artifacts directory so Ralph can code + validate next loop.
Action State: ready_for_implementation
- Scoped Phase E.2 parity fix: Stage A must now treat Stage B enablement the same as Stage C for panel-mode baseline/final validations so REFINE-FLOW-001 stays green even when ROI counts exceed the threshold. Logged the plan in docs/fix_plan.md (2025-12-01T160850Z) with the artifact path and re-marked Phase E.1 as complete in implementation.md; rewrote input.md with a code-ready Do Now covering the Stage A toggle, the smoketest threshold tweak, and the Stage B/C validation commands.
Action State: ready_for_implementation
2025-12-01T160850Z focus=ARCH-REFINE-001 state=ready_for_implementation dwell=0 action=planning artifacts=plans/active/ARCH-REFINE-001/reports/2025-12-01T160850Z/ next_action=Implement Stage A panel-toggle for Stage B + rerun Stage B/C smokes with tightened threshold
2025-12-01T161600Z focus=ARCH-REFINE-001 state=ready_for_implementation dwell=1 action=planning artifacts=plans/active/ARCH-REFINE-001/reports/2025-12-01T161600Z/ next_action=Extract Stage B parity helper + rerun guard/smokes
- Logged Phase E.3 plan: factor the REFINE-FLOW-001 guard into a helper, rewire the CPU fallback test to exercise the diff payload directly, and rerun the Stage B/C small smokes with telemetry under the new timestamp.
- Updated docs/fix_plan.md, implementation.md, and input.md with the helper/test scope, env commands, artifacts path, and guard-focused pitfalls so Ralph can implement immediately.
Action State: ready_for_implementation
2025-12-01T170500Z focus=ARCH-REFINE-001 state=planning dwell=2 action=planning artifacts=plans/active/ARCH-REFINE-001/reports/2025-12-01T170500Z/ next_action=switch_focus->PERF-WARM-SIM-001 Phase D.4 telemetry validation
- Closed Phase E by verifying Stage B guard telemetry + updating docs/fix_plan and marked REFINE-FLOW-001 resolved; initiative exit criteria now satisfied.
- Added PERF-WARM-SIM-001 D.4 Do Now (Stage C telemetry script + small/full smokes) so Ralph can resume warm-cache validation immediately.
Action State: ready_for_implementation
2025-12-01T171800Z focus=PERF-WARM-SIM-001 state=blocked dwell=0 action=implementation artifacts=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T171800Z/ next_action=supervisor_root_cause_analysis
**CRITICAL FINDING**: Full detector Stage C warm-cache test FAILED with chi-squared regression (0.0664% > 0.05% tolerance) immediately after ARCH-REFINE-001 Phase E.2 changes (2025-12-01T161600Z). Small detector PASSED (early_stop, -0.0631% improvement, 99.99999% detector offset reduction).
**Root Cause Hypothesis (95% confidence)**: Phase E.2 modified Stage A to force panel-mode baseline/final validations when Stage B OR Stage C is enabled (dbex/refinement/stage_a.py:210-224). Prior successful runs (2025-11-21T174147Z) used ROI mode for full detector (92 ROIs) and showed +59.9% improvement (χ² 250M→100M). Current run uses panel mode for full detector and shows -0.0664% regression (χ² 210.7M→210.8M). The 19% lower initial χ² + regression pattern suggests panel-mode validation may be interfering with Stage C warm-cache retargeting or creating a mismatch in the Stage A→Stage C handoff for high-ROI-count configurations.
**Evidence Trail**:
1. Small detector (29 ROIs, below auto-panel threshold): PASSED with panel mode
2. Full detector (92 ROIs, above threshold): FAILED with panel mode + regression
3. Historical baseline (2025-11-21T174147Z, pre-Phase E.2): PASSED with ROI mode + massive improvement
4. No PERF-WARM-SIM-001 code changes between 2025-11-21T174147Z and now
5. ARCH-REFINE-001 Phase E.2 (2025-12-01T161600Z) = only intervening change
**Blocker Classification**: Implementation defect (suspected), not gate calibration. Stage C warm-cache path for full detector is broken after Phase E.2 Stage A panel-mode changes.
**Immediate Action Required**: Supervisor must investigate whether:
(a) Panel-mode Stage A final validation produces different χ² baseline than ROI-mode (breaking Stage C initial-value continuity)
(b) Stage C warm-cache retargeting (`dbex/refinement/stage_c_impl.py:39-86`) has panel-mode edge case
(c) Auto-panel threshold (currently ≤32 ROIs) should be raised or disabled for Stage C flows
**Artifacts**: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T171800Z/ (summary.md, small detector telemetry captured, full detector pytest log shows regression failure signature)
Action State: blocked
2025-12-01T163900Z focus=PERF-WARM-SIM-001 state=planning dwell=1 action=planning artifacts=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T163900Z/ next_action=ready_for_implementation
- Root-caused the Stage C smoke regression as a telemetry domain mismatch once Stage A started forcing panel baselines; Stage C still reports ROI-only chi² so the REFINE-007 gate compares different populations.
- Logged REFINE-011 in docs/findings.md and refreshed docs/fix_plan.md/input.md with the plan to plumb Stage A’s `force_panel_validation` flag into Stage C and rerun the smokes (small + full).
- No code changes yet—implementation plus smoketest reruns are queued for Ralph under the new artifact path.
Action State: ready_for_implementation
2025-12-01T163900Z focus=PERF-WARM-SIM-001 state=ready_for_implementation dwell=2 action=implementation artifacts=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T163900Z/ next_action=investigate_full_detector_regression
**PARTIAL SUCCESS**: Implemented REFINE-011 validation scope alignment (Stage A→Stage C). Small detector test PASSED, confirming the validation_scope plumbing works correctly. Full detector test FAILED with 0.067% chi² regression (exceeds 0.05% gate).
**Implementation Summary**: 
- Tagged Stage A telemetry with `validation_scope` field in perf_counters (dbex/refinement/stage_a.py:367)
- Threaded `force_panel_validation` through Stage C context chain (stage_c_impl.py, stage_c.py)
- Added `force_panel_eval` parameter to `compute_loss_stage_c` with bypass logic at line 486
- Wired force_panel_eval to all full validation calls (periodic + initial + final)
**Test Results**:
- Small detector (29 ROIs): PASSED ✓ — validation scope alignment working as designed
- Full detector (92 ROIs, 60 panels): FAILED ✗ — Stage A final χ²=2.1071e+08, Stage C final χ²=2.1085e+08 (0.067% regression vs 0.05% gate)
**Root Cause Hypothesis (60% confidence)**: The full validation mode switch affects optimizer trajectory. Prior runs used ROI-mode for full validations (sampled subset), new runs use panel-mode (entire panel). The periodic full validations (every 5 iterations) guide the "best parameters" snapshot logic via different loss values, possibly selecting a different local minimum. The 0.067% regression may be inherent to the correct (panel-mode) evaluation metric, previously hidden by the ROI-vs-panel scope mismatch.
**Alternative Hypothesis (30% confidence)**: Small numerical precision issue in panel-mode full validation accumulation or variance floor handling for 60-panel configuration that doesn't manifest in single-panel small detector.
**Evidence Against Implementation Bug**: 
1. Small detector passes with same code path
2. Logic review shows correct bypass: `use_roi_mode_this_eval = stage_c_roi_mode_active and not (is_full and force_panel_eval)` 
3. All force_panel_eval calls properly wired
4. Telemetry threading confirmed via code inspection
**Artifacts**: Small detector telemetry captured, full detector pytest log shows clean execution except final gate failure. No HKL interpolation errors in full detector run beyond one "out of range" warning.
**Recommended Next Actions**:
1. **Immediate**: Supervisor review of whether 0.067% regression is acceptable given correct metric alignment (SPEC adherence vs gate relaxation trade-off)
2. **Short-term**: Capture Stage C chi²  trace from full detector run to see if optimization is converging or diverging
3. **Long-term**: Investigate whether detector offset optimization parameters (max_distance_delta_mm, tolerance_change) need adjustment for panel-mode validation regime
Action State: partial_success
2025-12-01T170326Z focus=PERF-WARM-SIM-001 state=planning dwell=1 action=planning artifacts=plans/active/PERF-WARM-SIM-001/reports/2025-12-01T170326Z/ next_action=ready_for_implementation
- Logged REFINE-012 and updated docs/fix_plan.md with the new Phase D.4 ROI-mode gating plan (disable Stage C ROI closures when Stage A forces panel validations, rerun Stage C smokes, capture telemetry via summarizer) plus refreshed commands/artifact paths.
- Rewrote input.md with the new Do Now, mapped tests, and How-To map so Ralph can implement the Stage C ROI-mode change and rerun the smokes immediately.
Action State: ready_for_implementation
