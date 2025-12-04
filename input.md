Summary: Add an architecture enforcement test plus docs so plan-local probe scripts stay thin wrappers (growth-cap guard + shim delegation checks).
Mode: Docs
ActionType: implementation_ready
DecisionStatus: localized
InitiativeType: architecture
Focus: ARCH-PROBE-FREEZE-001 — Probe Freeze & Logging Consolidation
Branch: integration
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/architecture/test_probe_contracts.py
Artifacts: plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-31T010000Z/
Findings Applied (Mandatory): No relevant findings — enforcing diagnostic_script_policy directly via architecture test
Pointers:
  - plans/active/ARCH-PROBE-FREEZE-001/implementation.md:80-150 — Phase C guardrails + required enforcement behaviors
  - docs/fix_plan.md:840-880 — Attempts history + new Phase C.1 planning entry for this loop
  - prompts/supervisor.md:254-309 — Scriptization + diagnostic_script_policy contracts referenced by the new test
ARCH Contracts (mandatory):
  - Diagnostic Script Policy (prompts/supervisor.md:254-309) — Owner: dbex.tools.*, dbex.refinement telemetry APIs; failure type: architecture conformance (plan scripts re-implement physics instead of owner modules).
  - Telemetry/Data Flow (docs/architecture/data_telemetry_flow.md:42-118) — Owner: dbex.refinement.stage_a/stage_b/stage_c; failure type: implementation bug (probe growth hides telemetry instead of instrumenting owner path).
  - Module Map (docs/architecture/module_map.md:30-95) — Owner: dbex.tools + calibration modules are sole producers for CLI helpers; failure type: architecture conformance (shadow pipelines outside owner package).
Do Now (hard validity contract)
1. Implement: `tests/architecture/test_probe_contracts.py::test_plan_bin_growth_cap` — walk `plans/active/**/bin/*.py`, compute LOC, and fail when a script exceeds 400 LOC unless it appears in a hard-coded `GROWTH_CAP_EXCEPTIONS` list. Seed the allowlist with the current offenders (13 paths):
   - plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulate_forward_once_vs_reconstruction.py
   - plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulator_outputs.py
   - plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline_legacy.py
   - plans/active/ARCH-SIM-HKL-BOUNDS-001/bin/inspect_hkl_projection.py
   - plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/bin/trace_simulator_mismatch.py
   - plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py
   - plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py
   - plans/active/TOOLING-VIS-001/bin/compare_stage_a_mapping_parity.py
   - plans/active/TOOLING-VIS-001/bin/generate_stage_a_refgeom_roi_triptychs_adam.py
   - plans/active/TOOLING-VIS-001/bin/probe_mapping_roi_triptychs.py
   - plans/active/TOOLING-VIS-001/bin/probe_scale_chain.py
   - plans/active/TORCH-REFINE-002E/bin/compare_mapping_vs_stage_a_forward.py
   - plans/active/TORCH-REFINE-002E/bin/probe_crystal_matrix_parity.py
   Document the allowlist inline (commented with plan IDs) so new scripts cannot bypass the cap silently.
2. Implement: `tests/architecture/test_probe_contracts.py::test_probe_shims_delegate_to_owner_clis` — ensure the shim scripts delivered in Phase B stay minimal. Parse each file (`plans/active/PHYSICS-LOSS-001/bin/embed_sigma_external_lookup.py`, `plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py`, `plans/active/TOOLING-VIS-001/bin/capture_smoke_calibration.py`) and assert their AST contains only import statements plus an `if __name__ == "__main__"` block that calls the canonical `dbex.tools.*.main`. Fail if any function/class definitions creep in.
3. Implement: docs/TESTING_GUIDE.md + artifacts — add a subsection under the architecture/maintenance section describing the new enforcement test, how to run it (`pytest -vv tests/architecture/test_probe_contracts.py`), how to maintain the allowlists, and where to stash logs. Capture the pytest execution log plus a short summary.md under `plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-31T010000Z/` outlining the growth-cap scan output and shim assertions.
Forbidden This Loop:
  - no new plan-local diagnostic scripts or instrumentation; enforcement must come solely from pytest + docs.
  - do not raise the 400 LOC threshold — only use the explicit allowlist for unavoidable legacy scripts.
  - do not edit nanobrag_torch or other production simulators in this loop (focus is enforcement tooling only).
Mapped tests are mandatory; rerun until passing:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/architecture/test_probe_contracts.py | tee plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-31T010000Z/pytest_probe_contracts.log
How-To Map:
  1. Implement both pytest cases plus helper functions/constants in `tests/architecture/test_probe_contracts.py` (new file) with docstrings referencing prompts/supervisor.md §9–10 and plans/active/ARCH-PROBE-FREEZE-001/implementation.md.
  2. Update docs/TESTING_GUIDE.md (architecture/maintenance section) to describe the new enforcement test, its allowlists, and where to put artifacts/logs. Mention that failures mean either the growth cap was exceeded or shim structure changed.
  3. Create `plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-31T010000Z/` with `summary.md`, the pytest log, and any helper listings if the test emits actionable output.
Pitfalls To Avoid:
  - Do not rely on git-ignored files; use `pathlib.Path.rglob` inside `tests/architecture` with `followlinks=False` and `sort()` for determinism.
  - Keep allowlists minimal and documented — every exception entry must cite the plan/initiative driving cleanup.
  - Ensure shim detection tolerates the `sys.path` manipulation blocks already in those files but rejects extra helper functions.
  - Avoid importing repo modules inside the test body; use stdlib (`ast`, `pathlib`, `textwrap`) to keep the architecture test dependency-light.
  - Remember to normalize paths (e.g., `Path(...).as_posix()`) so assertions work on all platforms.
  - Update docs/TESTING_GUIDE.md in the same loop; documentation drift is treated as noncompliant.
  - Store pytest output under the artifacts directory; missing logs will be treated as incomplete evidence.
  - Do not modify existing plan scripts while adding the enforcement test; this loop only adds the guard + docs.
If Blocked: Document the blocker in `plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-31T010000Z/blockers.md`, update docs/fix_plan.md attempts with evidence, and ping Galph only after attaching the failing pytest log + list of problematic scripts.
Doc Sync Plan: After code passes, run `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest --collect-only tests/architecture/test_probe_contracts.py > plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-31T010000Z/pytest_collect.log` so test registries capture the new node.
