Summary: Launch ARCH-TELEMETRY-001 by introducing a `RefinementObserver` interface and wiring Stage A to emit telemetry through a typed collector instead of mutating dicts.
Mode: none
InitiativeType: architecture
Focus: ARCH-TELEMETRY-001 — Telemetry Observer Refactor
Branch: integration
Mapped tests:
- KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
- KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_stage_a_engine_delegation_telemetry::test_stage_a_engine_delegation_telemetry
Artifacts: plans/active/ARCH-TELEMETRY-001/reports/2025-12-02T191500Z/

Do Now:
- Implement: dbex/refinement/interfaces.py::RefinementObserver / StageResult — Create (or extend) the refinement interfaces module with a `Protocol` that defines `on_step`, `on_validation`, and `finalize` hooks plus `StagePerfCounters`+`StageResult` dataclasses. Document the spec references (docs/spec-db-workflow.md telemetry clauses, PHYSICS-LOSS-001 chi² invariants) and add helpers to serialize the dataclass payload back into the legacy telemetry dict so downstream consumers stay stable until later phases.
- Implement: dbex/refinement/stage_a.py::_build_lbfgs_closure / StageA.run — Introduce a `StageATelemetryCollector` (in a new helper such as `dbex/refinement/telemetry_collectors.py`) that implements `RefinementObserver` by updating the existing `StageATelemetryState`. Thread this collector through closure creation instead of passing `telemetry_state` dicts, replace the direct `loss_trace_*` / `chi_squared_trace_*` append calls with `collector.on_step`/`collector.on_validation`, and make StageA return a `StageResult` that still exposes the legacy dict for writer/tests.
- Implement: dbex/refinement/context.py::StageATelemetryState helpers — Add small utility methods (e.g., `record_step`, `record_validation`, read-only views) so the collector can interact with the dataclass without leaking internal lists. Remove any Stage-A-only dict compatibility layers that the observer supersedes.
- Implement: tests/dbex/test_stage_a_engine_delegation_telemetry + tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion — Update assertions to expect a `StageResult`/collector-driven telemetry path (no direct dict mutation) and add coverage ensuring `StageResult.telemetry` still contains the REFINE-007/PHYSICS-LOSS metrics.

How-To Map:
1. Code: Add `dbex/refinement/interfaces.py` containing `RefinementObserver`, `StagePerfCounters`, and `StageResult`, plus any serialization helpers noted above.
2. Code: Add `dbex/refinement/telemetry_collectors.py` (or similar) with `StageATelemetryCollector` that wraps `StageATelemetryState`; instantiate it inside `StageA.configure`/`StageA.run` and pass it down to `_build_lbfgs_closure` so the LBFGS closure emits observer events instead of touching lists directly.
3. Tests: `export KMP_DUPLICATE_LIB_OK=TRUE; pytest -v tests/dbex/test_stage_a_engine_delegation_telemetry::test_stage_a_engine_delegation_telemetry | tee plans/active/ARCH-TELEMETRY-001/reports/2025-12-02T191500Z/pytest_stage_a_engine.log`
4. Tests: `export KMP_DUPLICATE_LIB_OK=TRUE DBEX_SMOKE_DETECTOR_SIZE=small; pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion | tee plans/active/ARCH-TELEMETRY-001/reports/2025-12-02T191500Z/pytest_stage_a_smoke.log`

Pitfalls To Avoid:
- Preserve `/torch_diagnostics` schema and naming; collector output must serialize to exactly the same dict keys per docs/spec-db-interfaces.md.
- Do not touch Stage B/C telemetry paths yet; they still rely on the current dataclass/dict shims.
- Keep observer callbacks allocation-free (no `.item()` on tensors still needed by autograd, no extra tensor copies).
- Maintain trusted-mask and variance-floor counters; PHYSICS-LOSS-001 requires these stats even while refactoring.
- Environment freeze applies: do not add new dependencies or regenerate toolchains.

If Blocked:
- If Stage A smoketests fail because a telemetry field is missing or renamed, capture the failing pytest log plus the serialized telemetry dict/StageResult in `plans/active/ARCH-TELEMETRY-001/reports/2025-12-02T191500Z/telemetry_failure.md`, update docs/fix_plan.md Attempts History with the evidence, and pause implementation so we can realign the telemetry contract before touching Stage B/C.

Findings Applied (Mandatory):
- ARCH-STAGE-CTX-001 — Stage telemetry must be owned by typed contexts/collectors.
- ARCH-STAGE-CTX-002 — Stage B baseline parity guard exposed dict-mutation hazards; Stage A collector must avoid the same trap.
- PHYSICS-LOSS-001 — Variance-weighted chi² logging and sigma-floor stats must stay spec-compliant through the refactor.

Pointers:
- plans/active/ARCH-TELEMETRY-001/implementation.md:1-96 — initiative goals, compliance matrix, and Phase A/B tasks that this Do Now covers.
- docs/fix_plan.md:16-95 — roadmap placement and exit criteria for ARCH-TELEMETRY-001.
- problems.md:74-125 — observer-pattern problem statement from the ledger.
- dbex/refinement/stage_a.py:60-820 — current Stage A closure logic where telemetry mutation lives today.

Next Up (optional):
1. Port Stage B to the observer path and remove `_check_stage_b_baseline_parity` dict hacks (Phase C.1).
2. Refactor `dbex/io/writer.py` to consume `StageResult` dataclasses once all stages emit them (Phase C.2).
