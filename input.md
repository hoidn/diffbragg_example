Summary: Replace Stage A’s anonymous `telemetry_state` dict with the typed `StageATelemetryState` dataclass so LBFGS closures stop mutating opaque dicts and the telemetry payloads stay schema-aligned for RefinementEngine.
Mode: none
InitiativeType: architecture
Focus: ARCH-STAGE-CONTEXT-001 — Stage Context + Engine Artifact Boundary
Branch: integration
Mapped tests:
- tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small
- tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry
Artifacts: plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T073800Z/

Do Now:
- FocusItem: ARCH-STAGE-CONTEXT-001 Phase B.3.1 — Stage A telemetry-state dataclass.
- Expand: `dbex/refinement/context.py::StageATelemetryState` so it owns every accumulator currently stuffed into `telemetry_state` (iteration counter, loss/chi²/masked-mse traces, perf counters, variance-floor stats, sigma_floor tensor, telemetry_step_counter, lifecycle logs, best snapshot tuples, optional `panel_loss_diag`). Use explicit attributes with sensible defaults (`field(default_factory=list)` for traces, `List[int]` wrappers for mutable counters) and document each field in the docstring.
- Rewire: `_build_stage_a_lbfgs_closure` and `_run_stage_a_lbfgs` to construct and mutate a `StageATelemetryState` instead of a raw dict. The closure should read/write via dot notation (e.g., `telemetry_state.loss_trace_full.append(...)`). Provide a temporary compatibility shim so StageA.run treats both dataclass and dict inputs (e.g., `if isinstance(telemetry_state, StageATelemetryState): ... else: ...`) until downstream tooling catches up.
- Integrate: Update `StageA.run` to propagate the dataclass through StageResult (no behavior changes) and keep the env-gated panel diagnostics by exposing a `panel_loss_diag` list on the dataclass. Ensure `RefinementTelemetry` assembly still writes the same schema (chi² traces, perf counters, variance-floor stats, canonical fields). Do not touch Stage B/C telemetry yet.
- Validate:
  1. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md mkdir -p plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T073800Z`
  2. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T073800Z/pytest_stage_a_small.log`
  3. `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T073800Z/pytest_engine_telemetry.log`

How-To Map:
- Keep the mutable list-wrappers (e.g., `iteration_count = [0]`, `telemetry_step_counter = [0]`) so closures can mutate by reference; expose them as dataclass attributes instead of dict keys.
- Add helper methods on `StageATelemetryState` if needed (e.g., `as_mapping()` or `update_from_dict()`) to ease compatibility, but prefer updating callers to use attributes directly.
- Preserve existing lazy-import pattern and perf counters; only replace the storage container.
- When updating StageA.run, thread the dataclass through StageResult / RefinementTelemetry without changing the HDF5 schema; unit tests (`test_stage_a_engine_delegation_telemetry`) will catch schema drift.
- Use the canonical env flags shown above for both pytest nodes so artifacts remain comparable with prior loops.

Pitfalls To Avoid:
- Do not refactor Stage B/C telemetry yet; focus solely on Stage A. Future B3.2 loops will handle the other stages.
- Keep the panel-diagnostics hook (`DBEX_STAGE_C_PANEL_DIAG_DIR`) working by exposing `panel_loss_diag` on the dataclass; the PERF-WARM-SIM-001 tooling depends on those JSON snapshots.
- Maintain variance-floor and sigma_floor tensor references—replacing them with copies will break PERF-WARM caching.
- Avoid renaming telemetry fields serialized into `RefinementTelemetry`; match the existing schema so downstream tests and writers stay stable.
- No environment changes—if imports fail, record the signature in docs/fix_plan.md per Environment Freeze.

If Blocked:
- If the dataclass conversion reveals hidden schema consumers (e.g., external tooling still expects dict semantics), capture the failure (stack trace + context) in `plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T073800Z/blocked.md`, link it in docs/fix_plan.md, and stop so we can reconsider the migration plan.
- If either mapped test regresses, archive the failing logs under the artifact path and note the diff from prior telemetry in docs/fix_plan.md before stopping.

Findings Applied (Mandatory):
- ARCH-STAGE-CTX-001 — Stage helpers must stop mutating anonymous dicts; this delivers the typed telemetry state called out in the finding.
- ARCH-ENGINE-002 — RefinementEngine relies on stable telemetry schema; ensure the dataclass still produces the canonical `/torch_diagnostics` payloads.
- PHYSICS-LOSS-001/002 — Variance-weighted loss telemetry (chi² traces, variance-floor clamp metrics) must remain intact while refactoring.

Pointers:
- dbex/refinement/context.py:533-610 — existing `StageATelemetryState` stub to expand with the remaining fields/methods.
- dbex/refinement/stage_a_impl.py:705-1500 — current `telemetry_state` dict construction/mutation sites that need to shift to the dataclass.
- dbex/refinement/stage_a.py:140-210 and 930-1015 — StageA.run unpacking + RefinementTelemetry assembly that must switch to the dataclass-aware code path.

Next Up (optional):
- After Stage A telemetry is typed, plan Phase B.3.2 to migrate Stage B/C telemetry dicts before tackling the engine writer changes.
