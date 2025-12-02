Summary: Break Stage C helper dictionaries into a typed StageCContext so we can delete `stage_c_impl.py` without passing 15 positional arguments around the LBFGS closures.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-REFACTOR-001 — Refinement Engine Modularization & Physics Separation
Branch: integration
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-12-04T120500Z/
Do Now:
  - Implement: dbex/refinement/context.py::StageCContext — add a dataclass alongside `RefinementSharedContext` and `StageCTelemetryState` that owns Stage C’s stage-specific state (warm-cache flags, cache/ROI counts, baseline detector distances, sampled panel ids, ROI slices, validation scope, perf counter snapshot, `_apply_baseline_detector_prior` callback). Keep it device/dtype neutral and document that it is the typed replacement for the old `stage_c_context_dict`.
  - Implement: dbex/refinement/stage_c.py::StageC._build_lbfgs_closure — require a `StageCContext` instance (in addition to `RefinementSharedContext`) instead of the loose dict, drop the optional legacy kwargs, and update `StageC.run` to instantiate/populate the dataclass right after `_build_stage_c_params` returns. The StageC class should pass the context object through to `_build_stage_c_params`, `_build_lbfgs_closure`, and `_run_stage_c_lbfgs`, and it should expose the context’s perf counters/ROI metadata in the telemetry it returns.
  - Implement: dbex/refinement/stage_c_impl.py::{_build_stage_c_params,_run_stage_c_lbfgs} — update both helpers so they accept `StageCContext` rather than a dict (adjust the compatibility shim for `RefinementSharedContext` while you’re there). Replace every `stage_c_context['foo']`/`stage_c_context.get('foo')` call with property access on the dataclass, and ensure the observer/collector code still routes baseline/final validations exactly as before. The helpers should no longer mutate dicts; they should read/update the dataclass (which holds mutable containers for counters by design).
  - Keep the public API of StageC results identical: `StageC.run` should still return the same telemetry dicts/stage artifacts so `ARCH-TELEMETRY-001` consumers stay untouched. This step is just the typed-context breakout before we delete `_impl` entirely.
How-To Map:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/dbex/test_stage_b_cpu_fallback.py::test_stage_b_baseline_guard_diff_payload | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-04T120500Z/pytest_stage_b_guard.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-REFACTOR-001/reports/2025-12-04T120500Z/pytest_stage_c_smoke.log
Pitfalls To Avoid:
  - Do not resurrect the untyped `stage_c_context_dict`; the whole point is to make Stage C closures consume typed state (ARCH-STAGE-CTX-001).
  - Leave Stage B/A code untouched; StageCContext must live alongside existing contexts without altering their imports.
  - Keep `_apply_baseline_detector_prior` callable inside the dataclass rather than reintroducing global state; warm-cache logic depends on it (PERF-WARM-013).
  - StageC telemetry/observer plumbing (ARCH-TELEMETRY-001) is fragile—do not reintroduce dict mutation or skip collector hooks when refactoring signatures.
  - Ensure the new dataclass is serializable to logs (repr friendly); do not shove large tensors into attributes that will end up in debug strings.
  - Maintain Environment Freeze: stdlib only in the new dataclass and no import side effects.
  - Tests must be run with the exact env flags listed above; Stage C smoke still requires `DBEX_SMOKE_SIGMA_SOURCE=cli_override` so we stay on the calibrated path.
  - Keep the Stage C improvement gate semantics unchanged (REFINE-007); this refactor should not tweak the early-stop thresholds.
If Blocked:
  - If StageCContext needs fields that are currently minted inside `_build_stage_c_params` (e.g., ROI slice maps) and lifting them breaks warm-cache behavior, stop, capture the failing signature plus the partial dataclass in `plans/active/ARCH-REFACTOR-001/reports/2025-12-04T120500Z/blocker.md`, and @ me before attempting deeper surgery.
  - If the typed context ripples into Stage B/A compilation errors, revert to the previous commit, attach the pytest failure and stack trace to the same artifacts directory, and document the regression in docs/fix_plan.md so we can resize the scope.
Findings Applied (Mandatory):
  - ARCH-STAGE-CTX-001 — Stage helpers must consume typed contexts (no 11-parameter data clumps or dict mutation).
  - ARCH-ENGINE-002 — Stage wrappers remain the canonical entrypoints; keep telemetry schema untouched while refactoring internals.
Pointers:
  - dbex/refinement/stage_c.py:700-930 — current StageC.run path that still builds `stage_c_context_dict` and passes it into `_build_stage_c_params`/`_run_stage_c_lbfgs`.
  - dbex/refinement/stage_c_impl.py:224-430 & 520-900 — helper functions that still accept `stage_c_context` dicts and mutate them throughout LBFGS setup/teardown.
  - dbex/refinement/context.py:418-620 — existing context/telemetry dataclasses to mirror when adding `StageCContext`.
Next Up:
  - Once `StageCContext` is landed and proven, the next Phase C increment is to inline `_build_stage_c_params`/`_run_stage_c_lbfgs` into StageC and delete `stage_c_impl.py` entirely.
