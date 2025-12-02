Summary: Finish the Stage C telemetry collector migration so the small-detector smoketest records a sample loss trace and the final validation, then prove Stage B/C parity selectors stay green.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-TELEMETRY-001 — Telemetry Observer Refactor
Branch: integration
Mapped tests:
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload | tee plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T210000Z/pytest_stage_b_guard.log
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T210000Z/pytest_stage_b_smoke.log
- AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T210000Z/pytest_stage_c_smoke.log
Artifacts: plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T210000Z/
Do Now:
- Implement:
  * `dbex/refinement/stage_c_impl.py::_run_stage_c_lbfgs` — stop snapshotting telemetry via a legacy dict before the final observer events. Move the `collector.finalize()`/`StageResult.to_legacy_dict()` work to the end of the function, remove the old `legacy_telemetry_dict` plumbing, and build `RefinementTelemetry` directly from the collector/StageResult objects so the closing validation and panel diagnostics are recorded. While you are in there, add a fallback to emit a single sampled iteration whenever LBFGS exits without running the closure (so `loss_trace_sample` is never empty).
  * `dbex/refinement/stage_c.py::{_build_lbfgs_closure, run}` — keep routing baseline, periodic, and final validations through the collector payload (panel diagnostics included) and delete the remaining dict-based telemetry references. Make sure `_build_lbfgs_closure` (or a small helper it calls) can seed the collector with a baseline sample when the optimizer short-circuits so the smoketest gate has data.
  * `dbex/refinement/telemetry_collectors.py::StageCTelemetryCollector` — if needed, add a tiny helper (e.g., `record_baseline_sample`) to keep the Stage C code lean, but leave the existing `on_step/on_validation/finalize` contract untouched.
- Validate by running the mapped selectors above with the canonical env flags, teeing each run into the artifact directory. Stop immediately on the first failure and keep the log + any JSON diff for supervisor review.
How-To Map:
1. In `_run_stage_c_lbfgs`, reorganize the finish block so you only call `collector.finalize()` once everything (final validation + improvement gate) has run. Instead of copying fields out of `legacy_telemetry_dict`, unpack the returned `StageResult`/`StageCTelemetry` dataclasses and use them to populate `RefinementTelemetry`. If `collector.state.perf_closure_evals[0] == 0`, call a helper to push a single sample based on the baseline metrics before finalizing.
2. In `_build_stage_c_lbfgs_closure`, keep using `collector.on_step`/`collector.on_validation` but route the panel-diagnostics payload exclusively through those calls (no direct writes to `telemetry_state.panel_loss_diag`). If you add a helper to seed the collector when LBFGS never iterates, call it right after the baseline validation so the smoketest sees `loss_trace_sample` length ≥ 1.
3. After the code edits, rerun the Stage B guard, Stage B shell smoke, and Stage C detector microslip smoke with the commands above, capturing logs via `tee` into `plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T210000Z/`.
Pitfalls To Avoid:
- Do not reintroduce telemetry dict shims; StageResult/collectors must be the sole telemetry source per ARCH-STAGE-CTX-001/002.
- Keep panel diagnostics optional and only write them when the env var requests it (don’t regress PERF-WARM-SIM-001 logging).
- Honor REFINE-012: Stage C full validations still need to respect Stage A’s panel/ROI scope, so don’t short-circuit those paths while chasing the telemetry fix.
- Leave the CHAOS tests untouched; limit code changes to Stage C + collectors unless the compiler forces you elsewhere.
If Blocked:
- If any mapped selector fails, keep the failing log (plus any diff JSON) under the artifact directory, add a short note to docs/fix_plan.md Attempts History, and stop rather than guessing.
Findings Applied (Mandatory):
- ARCH-STAGE-CTX-001 — typed Stage contexts/collectors only (docs/findings.md).
- ARCH-STAGE-CTX-002 — Stage B/C parity guards must consume collector telemetry.
- PHYSICS-LOSS-001 / PHYSICS-LOSS-003 — variance-weighted χ² telemetry must stay spec-compliant.
- REFINE-012 — Stage C validations must match Stage A scope.
Pointers:
- docs/spec-db-workflow.md (§Pipeline + Stage C notes), docs/spec-db-core.md (§Objective Function & Variance Model).
- plans/active/ARCH-TELEMETRY-001/implementation.md (Phase C checklist) and docs/fix_plan.md attempts history.
- dbex/refinement/stage_c_impl.py, dbex/refinement/stage_c.py, dbex/refinement/telemetry_collectors.py.
Next Up: Once Stage C telemetry is green, proceed to Phase C.2 (writer consuming StageResult directly) per the plan.
Doc Sync Plan: none — selectors unchanged, registry already covers them.
Mapped Tests Guardrail: existing selectors already collect >0 tests; no new tests required before implementation.
Hard Gate: Treat any Stage B/C regression as a stop-ship; do not land telemetry changes without green runs and captured logs.
Normative Math/Physics: See docs/spec-db-core.md §Objective Function & Variance Model for the variance-weighted χ² definition to keep intact.
