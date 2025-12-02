Summary: Introduce typed refinement context dataclasses so Stage A stops passing giant dicts/parameter lists into the LBFGS helpers while preserving current warm-cache behavior.
Mode: none
InitiativeType: architecture
Focus: ARCH-STAGE-CONTEXT-001 — Stage context + engine artifact boundary
Branch: integration
Mapped tests:
- pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small
- pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small
Artifacts: plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T010500Z/{collect_stage_a_small.log,pytest_stage_a_small.log,collect_stage_b_small.log,pytest_stage_b_small.log,summary.md}

Do Now:
- Implement: `dbex/refinement/context.py::RefinementSharedContext` & `StageATelemetryState` — create a new module that defines dataclasses wrapping the shared refinement objects (detector, beam, crystal, RefinementInputs, HKL tensors, config, sigma-floor cache, baseline references, device/dtype) plus typed telemetry accumulators (lists for loss/chi² traces, perf counters). Provide `.from_inputs(...)` constructors and helper methods that keep tensors on the configured device/dtype.
- Implement: `dbex/refinement/stage_a_impl.py::{_build_stage_a_lbfgs_closure,_run_stage_a_lbfgs}` — update these helpers to accept the new dataclasses instead of 11 positional arguments + mutable dicts. Maintain a compatibility shim so existing dict-based callers continue to work (i.e., accept either dataclass instance or mapping), and update internal references to use attribute access rather than `stage_a_context['canonical_baseline']`. Preserve warm-cache invariants (`StageAROIEntry` remains untouched) and make sure telemetry lists are accessed via the dataclass.
- Implement: `dbex/refinement/stage_a.py::StageA.run` — build a `RefinementSharedContext` from the current inputs/config, thread it through helper calls, and keep the fallback path that accepts legacy dict inputs for downstream callers. Emit the new context metadata in telemetry (e.g., `telemetry['context_schema_version']="v1"`) so engine smoke tests can assert the transition.
- Validate: Collect `--collect-only` + full runs for Stage A expansion and Stage B shell smokes (small detector) to prove signatures stayed stable. Save collect-only logs, pytest output, and any new helper patches under the artifact path above.

How-To Map:
1. Add context module — create `dbex/refinement/context.py` with the new dataclasses and helper constructors. Export them via `__all__` so stage modules can import without circular dependencies.
2. Stage A helper refactor — edit `dbex/refinement/stage_a_impl.py` so `_build_stage_a_lbfgs_closure` and `_run_stage_a_lbfgs` accept a `StageAExecutionContext`/`RefinementSharedContext` plus the typed telemetry state instead of the current `(crystal, detector, beam, inputs, hkl_grid, hkl_metadata, config, sigma_floor_sq_cache, device, dtype, baseline_crystal)` signature.
3. Stage A wrapper update — change `dbex/refinement/stage_a.py::StageA.run` to construct the new dataclasses, thread them into helper calls, and include the compatibility shim for dict inputs so CLI paths keep working.
4. Collect-only (Stage A) — `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small > plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T010500Z/collect_stage_a_small.log`
5. Stage A smoke — `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T010500Z/pytest_stage_a_small.log`
6. Collect-only (Stage B) — `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small > plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T010500Z/collect_stage_b_small.log`
7. Stage B smoke — `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T010500Z/pytest_stage_b_small.log`

Pitfalls To Avoid:
- Keep Environment Freeze: no pip installs or simulator rebuilds; this is pure Python refactoring.
- Preserve Stage A warm-cache semantics (`StageAROIEntry` and `StageAContext` members must stay identical and continue to live on the correct device/dtype).
- Don’t drop the dict-based compatibility shim until Stage B/C and CLI callers migrate; raising on legacy inputs would strand PERFWARM work.
- Watch for circular imports—`dbex/refinement/context.py` must not import stage modules.
- Telemetry schema must remain stable; make sure the dataclass exports convert back to the existing dict structure before hitting `RefinementTelemetry`.
- Any default values for dataclass lists should use `default_factory=list` to avoid shared mutable state.

If Blocked:
- If the refactor exposes a missing dependency (e.g., a helper still expects raw dicts), capture the stack trace plus the offending call tree, drop a note in `plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T010500Z/blocked.md`, and halt edits so we can schedule a compatibility shim instead of partial refactors.
- If either smoketest crashes due to type mismatches (AttributeError, dataclass serialization, etc.), revert any unmerged helper signature changes, archive the failing logs in the artifacts path, and update docs/fix_plan.md + galph_memory.md to flag the blocker before attempting further code changes.

Findings Applied (Mandatory):
- ARCH-ENGINE-002 — Stage wrappers must conform to the RefinementStage protocol; the new context dataclasses cannot break telemetry or engine wiring.
- ARCH-STAGE-CTX-001 — Addresses the documented data clumps / mutable dict telemetry across Stage helpers.
- REFINE-FLOW-001 — Keep Stage B baseline parity telemetry untouched while reshaping Stage A contexts.

Pointers:
- dbex/refinement/stage_a_impl.py:1222 — current `_build_stage_a_lbfgs_closure` signature that needs to switch to the new dataclasses.
- dbex/refinement/stage_a.py:36 — StageA wrapper that unpacks dicts; refactor here to construct `RefinementSharedContext`.
- docs/spec-db-workflow.md:30 — Stage contract requirements you must honor when introducing the shared context/telemetry schema.

Next Up (optional):
- Phase A.3 will extend the same dataclasses to Stage B and Stage C helpers so the engine can delete the remaining stage-specific caches; log any insights that will make that follow-up easier.
