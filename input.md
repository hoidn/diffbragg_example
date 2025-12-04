Summary: Wire the Stage A baseline metrics hook into the DB-AT-028/029 smoke fixture so the acceptance selectors consume the production telemetry (no more probe math) and assert that the JSON payload lands under the artifacts directory.
Mode: Parity
ActionType: implementation_ready
DecisionStatus: localized
InitiativeType: architecture
Focus: ARCH-PROBE-FREEZE-001 — Probe Freeze & Logging Consolidation
Branch: integration
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_stage_a_baseline_metrics_dump
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_STAGE_A_BASELINE_METRICS_PATH=plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-28T150000Z/db_at_metrics_dir DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts: plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-28T150000Z/
Findings Applied (Mandatory): No relevant findings — closing the probe freeze gap documented in `probe_inventory.md`.
Pointers:
  - plans/active/ARCH-PROBE-FREEZE-001/implementation.md:33-54 — Phase B.3 notes showing DB-AT selectors still rely on probe outputs.
  - dbex/refinement/stage_a.py:2134-2199 — Existing baseline metrics hook that Stage A emits when `enable_stage_a_baseline_metrics` is True.
  - dbex/refinement/telemetry_baseline.py:1-170 — Helper that computes the schema v1 payload we need the tests to consume.
  - tests/dbex/test_stage_a_smoke_parity.py:70-520 — Stage A smoke fixture + DB-AT-028/029 selectors (currently oblivious to the new telemetry).
  - docs/TESTING_GUIDE.md:1-140 — Canonical env-flag documentation that must mention the new `DBEX_STAGE_A_BASELINE_METRICS_PATH` workflow.
ARCH Contracts (mandatory):
  - prompts/supervisor.md:272-309 (diagnostic_script_policy) — Owner: supervisor policy; failure type: architecture conformance (DB-AT evidence still flows through a shadow pipeline instead of owner telemetry).
  - docs/architecture/data_telemetry_flow.md:1-120 (Stage A telemetry ownership) — Owner: `dbex.refinement.stage_a`; failure type: architecture conformance (acceptance selectors ignore the owner telemetry and recompute ROI stats externally).
Do Now (hard validity contract)
1. Implement: `tests/dbex/test_stage_a_smoke_parity.py::stage_a_smoke_result` — accept `request`, resolve a baseline metrics path from `DBEX_STAGE_A_BASELINE_METRICS_PATH` or the calling test’s artifact dir (`DBAT028_ARTIFACT_DIR` / `DBAT029_ARTIFACT_DIR`), flip `config.enable_stage_a_baseline_metrics=True`, and stash both `stage_a_artifacts.baseline_metrics` and the resolved JSON path on the fixture result so downstream tests can assert against them.
2. Implement: `tests/dbex/test_stage_a_smoke_parity.py::{test_db_at_028_loss_scale_sanity,test_db_at_029_structure_parity}` — after `_artifact_dir(...)` resolves, require that the Stage A baseline metrics file exists whenever the fixture surfaced a path, load the JSON (schema v1 from `collect_stage_a_baseline_metrics`), compare it to the in-memory `baseline_metrics`, and persist a copy under the artifact tree so parity evidence no longer depends on `compare_stage_a_baseline.py`.
3. Implement: `docs/TESTING_GUIDE.md` (env var section) — document the new `DBEX_STAGE_A_BASELINE_METRICS_PATH` knob (dir vs file semantics, how the DB-AT selectors derive filenames, and the expectation that parity loops set it before running Stage A smokes).
Mapped Validation (pytest):
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_stage_a_baseline_metrics_dump
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_STAGE_A_BASELINE_METRICS_PATH=plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-28T150000Z/db_at_metrics_dir DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts deliverables:
  - Stage A baseline metrics JSON(s) emitted by the acceptance tests under `plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-28T150000Z/`
  - pytest logs for `test_stage_a_baseline_metrics_dump` and the DB-AT-028/029 run that proves the selectors now read the owner telemetry
Forbidden This Loop:
  - no new plan-local probe scripts or extensions; the DB-AT selectors must consume Stage A’s telemetry hook
  - do not bypass `collect_stage_a_baseline_metrics` or re-implement ROI stats in tests/scripts
How-To Map:
  1. Add a helper in `tests/dbex/test_stage_a_smoke_parity.py` to resolve the baseline metrics file given an env override or per-test artifact directory (append `<test_name>_stage_a_baseline_metrics.json` when a directory is provided). Use it inside `stage_a_smoke_result` to set the config flag and record both the resolved `Path` and the `StageAArtifacts.baseline_metrics` dict in the returned result.
  2. Update `test_db_at_028_loss_scale_sanity` and `test_db_at_029_structure_parity` to check the returned `baseline_metrics`/`baseline_metrics_path`, assert the JSON exists + matches schema v1, and copy the file into each test’s artifact tree so DB-AT evidence includes the production metrics.
  3. Refresh `docs/TESTING_GUIDE.md` to describe the new env var and how DB-AT runners should set it (include the exact pytest command from this Do Now) so future loops don’t fall back to the shadow pipeline.
Pitfalls To Avoid:
  - Don’t hard-code baseline metrics filenames; make them unique per test so runs don’t clobber each other.
  - Avoid importing torch/numpy-heavy modules into helper scripts outside the production path; keep logic inside Stage A/test modules.
  - Ensure the fixture still works when the env knob is unset (baseline metrics optional outside parity runs).
  - Don’t write torch tensors directly to JSON — use the serializable dict Stage A already emits.
  - Preserve the existing DB-AT telemetry artifacts (metrics JSON, mapping diagnostics) while adding the new file so historical comparisons remain valid.
If Blocked:
  - Capture the blocker in `plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-28T150000Z/blockers.md`, update docs/fix_plan.md Attempts History, and ping Galph before reintroducing any plan-local probe logic. If Stage A fails to emit the metrics due to missing context, pause and document instead of adding new instrumentation.
Doc Sync Plan (Conditional): Not required — test node names stay the same; only their behavior changes.
