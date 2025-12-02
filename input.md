Summary: Introduce StageResult + StageArtifacts so Stage A/B/C return typed artifacts and the engine/writer stop scraping private caches for warm-context, shell metadata, and final Bragg tensors.
Mode: none
InitiativeType: architecture
Focus: ARCH-STAGE-CONTEXT-001 — Stage Context + Engine Artifact Boundary
Branch: integration
Mapped tests:
- tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry
- tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small
- tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small
Artifacts: plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T030800Z/

Do Now:
- Implement: Stand up the artifact scaffolding.
  1. Create `dbex/refinement/artifacts.py` with dataclasses for `StageAArtifacts` (warm StageAContext payload + `context_schema_version`), `StageBArtifacts` (shell_edges/indices, n_shells, stage_b baseline/parity stats, per-reflection ASU stats), and `StageCArtifacts` (final `bragg_full` array).
  2. In `dbex/refinement/stage.py`, add a `StageResult` dataclass that carries `RefinementTelemetry` plus an optional artifact; update `__all__` so stages can import it.
  3. Update `dbex/refinement/stage_a.py::StageA.run`, `stage_b.py::StageB.run`, and `stage_c.py::StageC.run` to return `StageResult(...)` instead of raw dicts. Each stage should instantiate the appropriate artifact class (Stage A: stash `stage_a_ctx`, Stage B: stash shell metadata/parity extras, Stage C: stash `bragg_full`) and keep the existing telemetry content unchanged.
- Implement: Rewire the engine to traffic artifacts instead of private caches.
  1. In `dbex/refinement/engine.py`, replace `_stage_a_ctx_cache`, `_stage_b_shell_edges`, `_stage_c_bragg_full`, etc., with a single `self._artifacts: Dict[str, StageArtifact]`. When a stage returns a `StageResult`, cache its artifacts, convert its telemetry (use `StageResult.telemetry` directly when already a `RefinementTelemetry`), and continue to enrich the telemetry with `engine_protocol`/`stage_modes`.
  2. When preparing inputs for downstream stages, pull the warm context from `StageAArtifacts` instead of `_stage_a_ctx_cache`. After Stage B runs, take the parity/shell metadata from `StageBArtifacts` and set the corresponding attributes on the telemetry object so existing tests that call `getattr(telemetry, "stage_b_baseline_rel_diff")` keep working.
  3. Add a read-only `artifacts` property so callers like `run_nanobrag_refinement` can fetch `engine.artifacts["stage_c"].bragg_full`.
- Implement: Update `dbex/nanobrag_refinement.py` to consume the new artifact map.
  1. Stage-A-only branch: replace `getattr(engine, "_stage_a_ctx_cache", None)` with the Stage A artifact payload and pass it to `_build_final_bragg_from_stage_a_telemetry`.
  2. Stage A→B branch: fetch Stage A + Stage B artifacts when reconstructing final Bragg and when preparing CPU fallback contexts; no direct access to `_stage_*` attributes should remain.
  3. Stage A→B→C branch: read the final Bragg tensor from `engine.artifacts["stage_c"]` and delete the `_stage_c_bragg_full` usage.
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md` for each command.
  1. Stage A telemetry guard — `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_engine_delegation_telemetry | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T030800Z/pytest_stage_a_engine.log`.
  2. Stage B shell smoke (small detector) — `DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T030800Z/telemetry_stage_b_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T030800Z/pytest_stage_b_small.log`.
  3. Stage C detector smoke (small detector — full run still blocked by PERF-WARM-SIM-001) — `DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T030800Z/telemetry_stage_c_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --smoke-detector-size=small | tee plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T030800Z/pytest_stage_c_small.log`.

How-To Map:
1. `mkdir -p plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T030800Z` before running tests so logs/telemetry land in the reserved directory.
2. Run the three commands listed in Validate (collect logs/telemetry exactly as shown; re-export `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md` if your shell resets between invocations).
3. If you need to inspect Stage artifacts interactively, use `python - <<'PY'` to load `RefinementEngine.artifacts` after a dry run (no code changes necessary) but do not check in helper scripts.

Pitfalls To Avoid:
- Do not change `/torch_diagnostics` or `RefinementTelemetry` schemas; all stage-specific extras must still appear exactly where current tests expect them.
- Keep Stage B baseline guard evidence intact (REFINE-FLOW-001): telemetry must still expose `stage_b_baseline_rel_diff`, `stage_b_baseline_abs_diff`, and `stage_b_baseline_diff_path`.
- Preserve Stage C ROI/warm-cache behavior; this refactor must not touch `roi_mode`, `validation_scope`, or the trusted-mask plumbing that PERF-WARM-SIM-001 monitors.
- Maintain device/dtype neutrality when moving artifacts around; Stage A context tensors are reused across devices, so never call `.to()` implicitly.
- Stage B per-reflection mode is already flaky; do not touch per-reflection code paths beyond the mechanical artifact plumbing.
- No environment modifications: if imports break, stop and document the blocker instead of installing packages.

If Blocked:
- If the new artifact plumbing surfaces missing metadata (e.g., Stage B needs shell indices but the artifact returns `None`), archive the failing telemetry/logs in `plans/active/ARCH-STAGE-CONTEXT-001/reports/2025-12-02T030800Z/blocked.md`, note the failure signature in docs/fix_plan.md, and halt for supervisor guidance.
- If any mapped pytest selector fails for a new reason, capture the log/telemetry in the artifacts directory, mention the selector and error in galph_memory.md, and do not proceed with additional code changes.

Findings Applied (Mandatory):
- ARCH-STAGE-CTX-001 — Remove the 10–15 argument data clumps by emitting typed Stage artifacts.
- ARCH-ENGINE-002 / ARCH-ENGINE-003 — Keep the engine protocol/telemetry enrichment intact while swapping the plumbing underneath.
- REFINE-FLOW-001 — Stage B parity diagnostics must persist through the artifact refactor.

Pointers:
- plans/active/ARCH-STAGE-CONTEXT-001/implementation.md:69 — Phase B checklist describing the StageArtifacts/StageResult work.
- docs/fix_plan.md:86 — Fix-plan entry + next actions for ARCH-STAGE-CONTEXT-001 (includes the reserved artifact path).
- docs/spec-db-workflow.md:50 — Engine contract (ordered stages, no hardcoded Stage A→B→C flow) that the refactor must continue to honor.
- docs/data_dependency_manifest.md:34 — Stage smoke dataset/env overrides referenced in the How-To map commands.
- problems.md:18 — Ledger entry this initiative resolves (Stage contexts / engine artifact boundary).
