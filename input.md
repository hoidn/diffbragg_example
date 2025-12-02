Summary: Finish the Stage B/C collector migration so telemetry flows through `StageResult` objects (no dict mutations) before re‑running the Stage B guard and Stage B/C smokes for parity proof.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-TELEMETRY-001 — Telemetry Observer Refactor
Branch: integration
Mapped tests:
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
Artifacts: plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T160900Z/
Do Now:
- Implement:
  * `dbex/refinement/telemetry_collectors.py::{StageBTelemetryCollector,StageCTelemetryCollector}` — teach both collectors to accept a `scope` argument (`baseline`, `panel`, `roi`, `final`), persist those labels plus the chi²/MSE tuples, carry variance-floor counters, and expose a canonical `to_legacy_dict()` (or reuse `StageResult.to_legacy_dict()`) so Stage B/C can serialize telemetry without poking the wrapped dataclass. Stage B also needs helper setters for `stage_b_baseline_rel_diff`, `stage_b_baseline_abs_diff`, and `stage_b_baseline_diff_path` so the parity guard still writes to typed storage.
  * `dbex/refinement/stage_b.py::{_build_lbfgs_closure,run}` and `dbex/refinement/stage_b_impl.py::_run_stage_b_lbfgs` — remove the legacy `telemetry_state` list/tuple mutations. Route every per-iteration sample and periodic validation through the collector, record baseline/final validations with explicit `scope` strings, let `_run_stage_b_lbfgs` call `collector.finalize()` once before rebuilding the best snapshot, and have `StageB.run` construct `StageResult`/`RefinementTelemetry` from the finalized collector output instead of splicing together dicts. `_check_stage_b_baseline_parity` should continue to grab the collector state (or its wrapped dataclass) to stash parity deltas.
  * `dbex/refinement/stage_c.py::{_build_stage_c_lbfgs_closure,run}` and `dbex/refinement/stage_c_impl.py::_run_stage_c_lbfgs` — apply the same conversion: closures emit observer events only, `_run_stage_c_lbfgs` relies on `StageCTelemetryCollector` for baseline/panel/final scopes and for `panel_diag` aggregation, and Stage C returns telemetry/artifacts via the finalized collector instead of mutating `telemetry_state`. Preserve REFINE-012’s validation-scope tagging and the PERF-WARM-SIM-001 panel diagnostic capture.
- Validate: capture the logs for every mapped selector inside the artifact directory (one `.log` per command) and spot-check the resulting `/torch_diagnostics` JSON to ensure Stage B/C chi² + masked-MSE traces are still emitted.
How-To Map:
1. Extend `StageBTelemetryCollector`/`StageCTelemetryCollector` so `on_validation(scope, chi2, payload)` records the scope, timestamped tuples, and any payload extras (Stage C panel diagnostics). Make `finalize()` build a `StageResult` plus a legacy dict view you can hand to `RefinementTelemetry`. Stage B’s collector should expose helpers for writing baseline parity diffs (`stage_b_baseline_rel_diff`, etc.) so `_check_stage_b_baseline_parity` no longer branches on dict vs dataclass.
2. Update `StageB._build_lbfgs_closure` and `_run_stage_b_lbfgs` to call `collector.on_step()`/`collector.on_validation()` everywhere the code currently appends to `loss_trace_*` or `chi_squared_trace_*`. Emit the initial baseline validation before LBFGS, route periodic validations through the collector, and let `StageB.run` call `collector.finalize()` to obtain telemetry/perf counters for `StageBArtifacts` + `RefinementTelemetry`. Restore the best parameter snapshot using the finalized payload instead of digging through `telemetry_state`.
3. Mirror the pattern for Stage C: closures stop mutating `telemetry_state`, `_run_stage_c_lbfgs` uses the collector for baseline/panel/final scopes (respecting `validation_scope` and panel diagnostics), and `StageC.run` consumes the finalized `StageResult`. Remove the lingering writes back into `StageCTelemetryState` so collectors are the single source of truth.
4. Run the mapped selectors, saving logs via `tee` into the artifact directory:
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload | tee plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T160900Z/pytest_stage_b_guard.log`
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T160900Z/pytest_stage_b_smoke.log`
   - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-TELEMETRY-001/reports/2025-12-03T160900Z/pytest_stage_c_smoke.log`
Pitfalls To Avoid:
- Do not mutate `telemetry_state` directly—collectors must be the only writers (ARCH-STAGE-CTX-001/002).
- Keep Stage B baseline parity guard wired through the collector so failing runs still emit `stage_b_baseline_diff_path`.
- Preserve variance-floor counters and perf traces; avoid calling `.item()` on tensors that still require grad.
- Stage C panel diagnostics and validation scope (REFINE-012) must flow through the collector payload so ROI vs panel gating stays intact.
- Environment is frozen; no new dependencies. Treat missing imports as blockers and log them in docs/fix_plan.md.
- Warm-cache paths must remain device-neutral; no `.cpu()`/`.cuda()` churn inside collectors or caches.
- Archive pytest logs in the artifacts directory even if a selector fails; stop immediately on the first failure.
If Blocked:
- If any selector shows telemetry drift, archive the failing log + `/torch_diagnostics` snapshot in the artifact directory, add an Attempts entry to docs/fix_plan.md, and halt for supervisor review instead of attempting speculative fixes.
Findings Applied:
- ARCH-STAGE-CTX-001 / ARCH-STAGE-CTX-002 — Typed contexts/collectors own telemetry; dict mutation is prohibited.
- PHYSICS-LOSS-001 — Variance-weighted χ² + sigma-floor clamp values must remain accurate in telemetry.
- PHYSICS-LOSS-003 — Stage B/C telemetry has to match Stage A semantics for downstream gates.
- REFINE-007 — Stage C improvement gate relies on consistent Stage A vs Stage C χ² history.
- REFINE-012 — Stage C must respect Stage A’s validation scope (`panel` vs `roi`) when emitting diagnostics.
Pointers:
- plans/active/ARCH-TELEMETRY-001/implementation.md:84 (Phase C checklist and scope notes for this loop).
- docs/fix_plan.md:410 (ARCH-TELEMETRY-001 Attempts History + artifact pointer).
- docs/spec-db-workflow.md §§6‑7 (telemetry observer + stage requirements).
- docs/spec-db-core.md §Objective Function & Variance Model (telemetry contents).
- docs/TESTING_GUIDE.md §2.1 (Stage B/C smoke commands and env knobs).
Next Up: Wire `dbex/io/writer.py` to the StageResult objects (Phase C.2) once the collectors own Stage B/C telemetry and the mapped selectors pass.
