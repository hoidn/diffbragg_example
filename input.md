Summary: Move Stage A baseline diagnostic metrics into owner telemetry and shrink compare_stage_a_baseline.py into a thin wrapper over RefinementEngine so DB-AT evidence no longer depends on a shadow pipeline.
Mode: Parity
ActionType: implementation_ready
DecisionStatus: localized
InitiativeType: architecture
Focus: ARCH-PROBE-FREEZE-001 — Probe Freeze & Logging Consolidation
Branch: integration
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_stage_a_baseline_metrics_dump
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts: plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-28T010000Z/
Findings Applied (Mandatory): No relevant findings — telemetry gap tracked via probe inventory
Pointers:
  - plans/active/ARCH-PROBE-FREEZE-001/implementation.md:55-97 — Phase B checklist describing Stage A telemetry migration + probe refactor scope.
  - prompts/supervisor.md:252-309 — diagnostic_script_policy thin-wrapper rule that the existing probe violates.
  - docs/architecture/data_telemetry_flow.md:1-120 — Stage A/mapping telemetry owner contract for parity metrics.
ARCH Contracts (mandatory):
  - prompts/supervisor.md:252-309 (diagnostic_script_policy) — Owner: supervisor policy / plan directory guard. Failure: architecture conformance (shadow pipeline re-implements simulator semantics).
  - docs/architecture/data_telemetry_flow.md:40-120 (Stage A telemetry ownership) — Owner: dbex.refinement.stage_a / telemetry collectors. Failure: architecture conformance (parity metrics exist only in probe scripts, not in the owner API).
Do Now (hard validity contract)
1. Implement: `dbex/refinement/config.py::RefinementConfig`, `dbex/refinement/stage_a.py::StageA.run`, and `dbex/refinement/artifacts.py::StageAArtifacts` — add an opt-in Stage A baseline metrics hook controlled by a new config flag/env var. The hook should compute the masked/unmasked means, chi²-per-pixel, ROI Pearson stats, and ROI snippets currently emitted by `compare_stage_a_baseline.py`, stash the payload on StageAArtifacts (e.g., `baseline_metrics` dataclass), and optionally dump JSON when `config.stage_a_baseline_metrics_path` (or env `DBEX_STAGE_A_BASELINE_METRICS_PATH`) is set. Wire the collector to use canonical owner helpers only (`simulate_forward_once`, `build_mapping_stage_a_context`, `RefinementInputs`) so no new shadow pipelines appear.
2. Implement: `dbex/refinement/telemetry_baseline.py::collect_stage_a_baseline_metrics` (new helper) — factor the ROI/mapping math out of the probe into a production helper that Stage A can call. The helper should accept `StageAContext`, `RefinementInputs`, telemetry deltas, and optional mapping config, return a serializable dict, and expose schema versioning. Document the JSON schema in a short module docstring so tooling/tests can lock onto it.
3. Implement: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py::main` — refactor the probe into a thin wrapper that (a) loads the canonical refGeom dataset via `DataLoad`/`prepare_refinement_inputs`, (b) configures Stage A with the new metrics flag/path, (c) runs `RefinementEngine` with Stage A only, and (d) writes out the Stage A artifact bundle (baseline metrics + provenance) without duplicating simulator/ROI math. Preserve existing CLI flags (geometry mode, output path) but forward them into config/environment instead of recomputing physics.
4. Implement: `tests/dbex/test_stage_a_smoke_parity.py::test_stage_a_baseline_metrics_dump` (or adjacent test) — add pytest coverage that sets the new config/env flag, runs the Stage A smoke fixture, and asserts that the JSON payload exists, contains the ROI summary fields, and matches the telemetry structure. Extend the existing DB-AT-028/029 selector to assert that the metrics file is produced when the flag is set so parity evidence stays decision-carrying.
Mapped Validation (pytest):
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_stage_a_baseline_metrics_dump
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts deliverables:
  - JSON + summary dumped by the new Stage A telemetry hook under `plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-28T010000Z/`
  - pytest logs for the new baseline metrics test and the DB-AT selectors
Forbidden This Loop:
  - No new plan-local probe scripts or extensions to existing probes; reuse Stage A / mapping owner APIs exclusively.
  - Do not fork additional diagnostics outside the production telemetry hook (no duplicated ROI math in new helpers).
How-To Map:
  1. Add the config/env plumbing + helper module under `dbex/refinement/telemetry_baseline.py`, update StageAArtifacts/StageA.run, and expose the JSON dump path.
  2. Refactor the probe script to call `RefinementEngine` with the Stage A metrics flag, saving only the emitted artifact bundle; update docs/comments to describe the new usage.
  3. Add the pytest coverage + rerun DB-AT-028/029 with the metrics flag enabled, capturing artifacts in the report directory.
Pitfalls To Avoid:
  - Do not compute ROI stats inside plan scripts once the helper exists — only Stage A/production code may perform that math.
  - Keep the new telemetry hook disabled by default to avoid perf regressions; guard everything behind the debug flag/env var.
  - Ensure Stage A writes CPU-friendly JSON (lists/floats) — no raw torch tensors in artifacts.
  - Update StageAArtifacts + writer paths carefully to avoid breaking existing consumers; add default `None` for new fields.
  - Remember Environment Freeze: no package installs; use only in-repo helpers (`simulate_forward_once`, etc.).
If Blocked:
  - Record the blocker in `plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-28T010000Z/blockers.md`, update docs/fix_plan.md Attempts History, and ping Galph before adding any new diagnostic probes. If Stage A lacks the necessary telemetry, switch focus or open a dedicated `ARCH-IMPL-CONFORMANCE` item.
Doc Sync Plan (Conditional): After landing the new pytest, run `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py` and add the node to `docs/development/TEST_SUITE_INDEX.md` under the DB-AT selector section.
