Summary: Promote the sigma metadata embedding helper into `dbex.tools.embed_sigma_external_lookup` so metadata fixtures/tests stop relying on the plan-local probe script (Problems ledger “Freeze plan-local probe scripts…”).
Mode: none
ActionType: implementation_ready
DecisionStatus: localized
InitiativeType: architecture
Focus: ARCH-PROBE-FREEZE-001 — Probe Freeze & Logging Consolidation
Branch: integration
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/sp_proc/test_sigma_metadata_fixture.py
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_STAGE_A_BASELINE_METRICS_PATH=plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-29T010000Z/db_at_metrics_dir DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small --smoke-sigma-source=metadata
Artifacts: plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-29T010000Z/
Findings Applied (Mandatory):
  - PHYSICS-LOSS-005 — metadata sigma tiles must register as `external_lookup`; migrating the embedding helper keeps provenance inside production owners.
  - PHYSICS-LOSS-001 — sigma provenance + variance telemetry belong to owner modules, not plan scripts; exposing the helper via `dbex.tools` satisfies this finding while obeying diagnostic_script_policy.
Pointers:
  - plans/active/ARCH-PROBE-FREEZE-001/implementation.md:30-80 — Phase B roadmap (new B4 sigma embedding migration tasks).
  - plans/active/PHYSICS-LOSS-001/bin/embed_sigma_external_lookup.py:1-210 — legacy shadow pipeline that must shrink to a thin wrapper.
  - dbex/data_load.py:1-150 — `load_sigma_readout_map` helper used by both the old script and the new owner module.
  - docs/TESTING_GUIDE.md:90-150 — sigma metadata workflow + current instructions referencing the plan script.
  - tests/sp_proc/test_sigma_metadata_fixture.py:1-140 — manifest/fixture guard that must continue to pass once the tool migrates.
ARCH Contracts (mandatory):
  - prompts/supervisor.md:272-309 — diagnostic_script_policy; owner module/API: `dbex.tools`/canonical CLIs; failure type: architecture conformance (shadow pipeline duplicating production semantics).
  - docs/spec-db-core.md:32-68 — sigma provenance contract; owner module/API: `dbex.data_load` + calibration helpers; failure type: implementation bug (metadata embedding lives outside the owner, breaking provenance guarantees).
Do Now (hard validity contract)
1. Implement: `dbex/tools/embed_sigma_external_lookup.py::main` — move the plan-script logic (arg parsing, sigma map loading, ExperimentList cloning, external_lookup injection, report/manifest writing) into a new owner CLI under `dbex/tools/`. Provide reusable helpers so future scripts/tests can import the embedding function directly.
2. Implement: `plans/active/PHYSICS-LOSS-001/bin/embed_sigma_external_lookup.py` — reduce to a thin compatibility shim that imports the new tool (`from dbex.tools import embed_sigma_external_lookup as tool`) and delegates to `tool.main()`.
3. Implement: `docs/TESTING_GUIDE.md` (sigma metadata section), `sp.proc/README.md`, and the skip/diagnostic text in `tests/conftest.py`, `tests/dbex/test_mapping_consistency.py`, `tests/dbex/test_artifact_parity.py`, and `tests/dbex/test_torch_refine_smoke.py` — update all instructions to reference `python -m dbex.tools.embed_sigma_external_lookup` (mention the plan path only as a legacy alias) and ensure error messages stay actionable.
Mapped Validation (pytest):
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest -vv tests/sp_proc/test_sigma_metadata_fixture.py
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_STAGE_A_BASELINE_METRICS_PATH=plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-29T010000Z/db_at_metrics_dir DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small --smoke-sigma-source=metadata
Artifacts deliverables:
  - CLI help output + summary in `plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-29T010000Z/tool_migration_notes.md` documenting the new entry point.
  - `pytest_sp_proc_sigma_metadata_fixture.log` and `pytest_stage_a_metadata_smoke.log` under the same artifacts directory.
  - Copy of the refreshed Stage A baseline metrics JSON for the metadata run (in `db_at_metrics_dir/`).
Forbidden This Loop:
  - no new plan-local probe scripts or telemetry forks — all functionality must live in `dbex.tools` + owner helpers.
  - do not rewrite or regenerate `sp.proc/idx-0000_sigma_metadata.*` in-place; use temporary outputs for validation.
How-To Map:
  1. Start from the current plan script, migrate its helpers (sigma tensor loading, manifest writer, ExperimentList mutation) into `dbex/tools/embed_sigma_external_lookup.py`, expose a `main()` that mirrors today’s CLI flags, and add a module docstring linking to ARCH-PROBE-FREEZE-001.
  2. Replace the plan script with a compatibility shim that imports the new tool and calls its `main()` so historical instructions keep working while the owner logic lives in `src/`.
  3. Update docs + skip messaging to reference the new CLI, then run the mapped pytest commands capturing logs + Stage A baseline metrics into the reserved artifact directory.
Pitfalls To Avoid:
  - Do not modify the canonical `sp.proc/idx-0000_sigma_metadata.*` fixtures during testing; write to a temp path instead.
  - Keep CLI signatures/backwards compatibility so existing automation (manifest scripts, docs) keep working.
  - Avoid importing heavy torch/dxtbx modules at import time in the new tool; gate them under `main()` to preserve CLI responsiveness.
  - Make sure manifest/report generation preserves SHA256 digest schema (schema_version, command, file metadata) so regression tests stay valid.
  - Don’t drop the `lookup_key` flag — Stage A smokes still expect pedestal entries.
  - Ensure the Stage A metadata smoke command sets `DBEX_SMOKE_SIGMA_SOURCE=metadata`; otherwise Stage A won’t exercise the new embedding path.
If Blocked:
  - Document the blocker in `plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-29T010000Z/blockers.md`, update `docs/fix_plan.md` Attempts History with evidence, and ping Galph before touching any plan-local scripts.
Doc Sync Plan (Conditional): Not required — no pytest selectors are being renamed; documentation updates are covered in Do Now step 3.
