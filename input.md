Summary: Restore canonical Stage B smoke by forcing panel-scope validations even when ROI closures are active so shell modifiers remain within the ±1% REFINE-008 gate and telemetry logs for both detector sizes.
Mode: Perf
Focus: PERF-WARM-SIM-001 — Warm simulator; eliminate per-iteration re-instantiation
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small; tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=full
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T142700Z/

Do Now:
- Focus Item: PERF-WARM-SIM-001
- Implement: dbex/nanobrag_refinement.py::run_nanobrag_refinement — Add a panel-evaluation path for Stage B initial/periodic/final validations that always iterates the full detector (reusing StageAContext simulators) while keeping ROI-mode closures for perf telemetry; ensure the best snapshot and telemetry param_deltas come from the panel evaluation so canonical shell modifiers stay within ±1%.
- Test: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T142700Z/telemetry_stage_b_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T142700Z/pytest_stage_b_small.log
- Re-test: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=full DBEX_SMOKE_TELEMETRY_PATH=plans/active/PERF-WARM-SIM-001/reports/2025-11-21T142700Z/telemetry_stage_b_full.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=full | tee plans/active/PERF-WARM-SIM-001/reports/2025-11-21T142700Z/pytest_stage_b_full.log
- Script: python plans/active/PERF-WARM-SIM-001/bin/summarize_stage_b_roi.py --telemetry plans/active/PERF-WARM-SIM-001/reports/2025-11-21T142700Z/telemetry_stage_b_small.json --telemetry plans/active/PERF-WARM-SIM-001/reports/2025-11-21T142700Z/telemetry_stage_b_full.json --out plans/active/PERF-WARM-SIM-001/reports/2025-11-21T142700Z/stage_b_roi_summary.json
- Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T142700Z/

How-To Map:
1. In `run_nanobrag_refinement`, introduce a `force_panel_eval` flag (or similar) so `compute_loss_stage_b` can reuse ROI sampling for closures but unconditionally iterate all panels (via `stage_a_ctx.simulators` when warm) for `is_full=True` validations; keep perf counters, clamp logic, and telemetry field names unchanged.
2. Ensure the initial, periodic, and post-optimization validations call the panel path so `best_params_snapshot_b` reflects detector-wide loss; document the new behavior inline so later refactors keep panel-scoped evidence.
3. Leave ROI perf counters untouched (`roi_mode="roi"`, sampled counts) but confirm `telemetry.param_deltas` mirrors the panel evaluation output before `_record_stage_telemetry()` flushes.
4. Re-run the Stage B smoke twice (small + full) with the env vars above so fresh telemetry/logs land in the new artifacts directory and prove the ±1% gate passes with panel-scoped validations.
5. Execute the ROI summary script to consolidate both telemetry files, then update docs/findings.md (PERF-WARM-009) and docs/fix_plan.md Attempts History with the new metrics and log references once shell modifiers stay near identity again.

Pitfalls To Avoid:
- Do not relax the strict ±1% REFINE-008 assertion; the fix must keep modifiers near identity rather than weaken the gate.
- Preserve ROI perf counters so findings PERF-WARM-005/008 remain accurate; panel validations should not overwrite ROI telemetry fields.
- Keep Stage B variance-weighted chi-squared math unchanged; only the evaluation footprint may change.
- Ensure panel evaluations still reuse StageAContext simulators to avoid re-instantiating Detector/Simulator stacks.
- Do not change Stage C or Stage A behaviors while touching `run_nanobrag_refinement`.
- Avoid adding randomness to panel selection—full evaluations must deterministically cover every panel.
- Capture telemetry even if an assertion fails; never swallow `_record_stage_telemetry` exceptions.
- No environment/toolchain edits (Environment Freeze).

If Blocked:
- Save failing pytest output and any partial telemetry JSON as `plans/active/PERF-WARM-SIM-001/reports/2025-11-21T142700Z/blockers.txt`, note the stack trace plus `telemetry.param_deltas` snapshot in docs/fix_plan.md, update galph_memory.md, and stop touching Stage B until the blocker is recorded.

Findings Applied (Mandatory):
- PERF-WARM-005 — ROI sampling stays tied to the warm cache; verify perf counters (`roi_mode`/counts) survive the panel validation path.
- PERF-WARM-006 — Stage B must continue reusing StageAContext detectors/masks; the new panel path should still lean on cached simulators.
- PERF-WARM-007 — Canonical Stage B smoke must keep logging perf counters so telemetry asserts remain meaningful.
- PERF-WARM-008 — ROI mode is expected on both detector sizes; recheck the telemetry JSON shows `roi_mode="roi"` alongside the new panel-validation outputs.
- PERF-WARM-009 — Documented that panel-scope validations are required to keep shell modifiers within ±1%; this fix implements that guidance.

Pointers:
- dbex/nanobrag_refinement.py:1595-1887 — Stage B ROI sampling and validation loop to adjust.
- tests/dbex/test_torch_refine_smoke.py:876-1138 — Stage B smoke gate enforcing ±1% shell modifier tolerances.
- plans/active/PERF-WARM-SIM-001/bin/summarize_stage_b_roi.py — Summarizes telemetry to confirm ROI/perf counters and modifiers.
- plans/active/PERF-WARM-SIM-001/reports/2025-11-21T125551Z/pytest_stage_b_full.log:1785-1794 — Current failure signature (`shell_0_modifier` clamp).
- docs/spec-db-workflow.md:39-74 — Normative Stage B requirements (structure-factor refinements, interpolation).

Next Up (optional): If time remains, rerun the canonical Stage C smoke to ensure detector-offset telemetry still reflects the warmed Stage A context after the Stage B change.

Doc Sync Plan: None (no new selectors introduced).

Mapped Tests Guardrail: `pytest --collect-only tests/dbex/test_torch_refine_smoke.py -k test_stage_b_shell_modifiers` already reports 1 node; reruns reuse this selector with different `--smoke-detector-size` values.

Hard Gate: Do not call this initiative done until both Stage B telemetry files record `cache_mode="warm"`, `roi_mode="roi"`, ROI totals {29,92}, and every shell modifier stays within ±1% (telemetry + summary JSON) while the canonical test passes without relaxing assertions.

Normative Math/Physics: Stage B must continue minimizing the variance-weighted chi-squared defined in docs/spec-db-core.md §§32-68 (telemetry chi-squared/Masked-MSE fields must match panel evaluations).
