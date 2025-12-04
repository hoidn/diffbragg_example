# Implementation Plan: ARCH-PROBE-FREEZE-001

## Initiative
- ID: ARCH-PROBE-FREEZE-001
- Title: Probe Freeze & Logging Consolidation
- Owner: Galph ↔ Ralph
- Initiative Type: architecture (probe policy + enforcement)
- Spec / Policy Owners: docs/diagnostic_script_policy (galph_prompt §10), docs/spec-db-core.md §§20-40 (owner APIs), docs/architecture/data_telemetry_flow.md
- Status: pending
- Tier: 0 (Problems Ledger directive)

## Goal
Stop the growth of shadow pipelines under `plans/active/**/bin`, migrate decision-carrying measurements into production-owner APIs + telemetry hooks, and add enforcement/tests so new probes call the canonical APIs instead of re-encoding simulator/mapping semantics.

## Non-Goals
- Changing acceptance thresholds or DB-AT specs.
- Removing lightweight helper scripts that only wrap an owner API (thin wrappers remain allowed once cataloged).
- Refactoring production modules beyond what is required to expose the necessary logging hooks.

## Exit Criteria
1. Inventory of all plan-local probe scripts complete with classifications (thin wrapper vs shadow pipeline) and artifacts stored under `plans/active/ARCH-PROBE-FREEZE-001/reports/<timestamp>/probe_inventory.{md,json}`.
2. For every script flagged as shadow pipeline, either (a) delete/migrate it to production logging/tests, or (b) document an explicit exception (owner, rationale, expiry) approved in docs/fix_plan.md.
3. Production logging/telemetry updated so Stage A/ mapping / reconstruction capture the measurements previously re-derived by probes (ROI stats, HKL coverage, partiality, etc.).
4. Enforcement landed: architecture test or static check under `tests/architecture/test_probe_contracts.py` that fails when a new plan-local script imports forbidden modules or reimplements owner semantics (per diagnostic_script_policy).
5. Problems Ledger entry "Freeze plan-local probe scripts in favor of parallel logging" annotated as tracked + resolved once enforcement + migration complete.

## Dependencies
- Relies on docs/diagnostic_script_policy compliance rules.
- Blocks future probe instrumentation under ARCH-SIM-CONSTRUCTION-001 and related initiatives.
- Coordinated with FINDINGS-LEDGER-002 so new findings reference the enforcement artifacts.

## Phase A — Catalog & Risk Assessment
- [x] A1: Walk every `plans/active/**/bin/*.py` and `bin/*.sh` script, record purpose, owner initiative, touched modules, and whether it duplicates simulator/mapping physics.
- [x] A2: Produce `probe_inventory.md` summarizing counts by initiative + classification, and highlight any scripts exceeding thin-wrapper limits (per diagnostic script policy growth caps).
- [x] A3: Cross-reference docs/fix_plan.md + galph_memory.md entries to see which probes are still decision-carrying vs obsolete (2025-12-28 loop: ARCH-SIM-CONSTRUCTION-001 baseline probe picked as the first migration target for Phase B because it drives DB-AT-027/028/029 evidence).

**Artifacts:**
- `plans/active/ARCH-PROBE-FREEZE-001/reports/<timestamp>/probe_inventory.md`
- `plans/active/ARCH-PROBE-FREEZE-001/reports/<timestamp>/probe_inventory.json`

## Phase B — Migration & Logging Hooks
- [x] B1: Migrate the Stage A baseline probe metrics into owner code:
    - Extend `RefinementConfig` / Stage A so an opt-in flag (or metrics path/env var) records the masked means, ROI Pearson stats, chi²/pixel, and ROI snippets currently computed inside `compare_stage_a_baseline.py`.
    - Add a typed payload (e.g., `StageABaselineMetrics`) to `StageAArtifacts` and a JSON dump hook so plan tools/tests can consume the metrics without rebuilding Stage A manually.
- [x] B2: Refactor `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py` into a thin wrapper that simply loads the canonical dataset, flips the new Stage A debug flag, runs `RefinementEngine` (Stage A only), and persists the emitted telemetry/artifact bundle. No direct simulator/ROI math should remain.
- [x] B3: Add/refresh pytest coverage (e.g., `tests/dbex/test_stage_a_smoke_parity.py::test_stage_a_baseline_metrics_dump`) plus rerun DB-AT-028/029 so the new telemetry path is proven decision-carrying. Once green, update `probe_inventory` to reclassify the script as thin wrapper and mark the Phase B tasks complete in docs/fix_plan.md.
    - Status 2025-12-29T010000Z: `stage_a_smoke_result` now resolves `DBEX_STAGE_A_BASELINE_METRICS_PATH`, threads `enable_stage_a_baseline_metrics=True`, surfaces the JSON path + payload on the fixture, and DB-AT-028/029 assert + archive the owner-generated metrics. `docs/TESTING_GUIDE.md` documents the workflow, so parity evidence no longer depends on the plan script.
- [x] B4: Promote the sigma embedding helper into the production tree so metadata fixtures no longer depend on the 250-line plan script `plans/active/PHYSICS-LOSS-001/bin/embed_sigma_external_lookup.py`.
    - Author `dbex/tools/embed_sigma_external_lookup.py` with a reusable CLI (`main()`) and helpers that encapsulate loading sigma maps (`load_sigma_readout_map`), cloning ExperimentLists, populating `imageset.external_lookup`, and writing the provenance report/manifest. The logic currently in the plan script should migrate here verbatim (no behavior drift).
    - Convert the plan-local script into a thin compatibility shim that simply imports the new tool (`from dbex.tools import embed_sigma_external_lookup as tool`) and delegates to `tool.main()` so future updates happen in the owner module.
    - Update documentation + hints (`docs/TESTING_GUIDE.md` §1.4, `sp.proc/README.md`, skip guidance in `tests/conftest.py`, `tests/dbex/test_mapping_consistency.py`, `tests/dbex/test_artifact_parity.py`, `tests/dbex/test_torch_refine_smoke.py`, etc.) to point at the canonical entry point `python -m dbex.tools.embed_sigma_external_lookup` and note that the plan path is now only an alias.
    - Validation: rerun `pytest -vv tests/sp_proc/test_sigma_metadata_fixture.py` and the Stage A metadata smoke selector (small detector is acceptable) with `DBEX_SMOKE_SIGMA_SOURCE=metadata` to prove the new tool still produces fixtures that Stage A recognizes as `sigma_readout_provenance="external_lookup"`.
- [x] B5: Collapse `plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py` into a thin wrapper over a canonical owner CLI so mapping/calibration diagnostics run inside production modules instead of a 600+ LOC plan script.
    - Add a reusable helper module (e.g., `dbex/calibration/config_variants.py`) that materializes calibration variants (spot_scale overrides, N_cells removal, etc.) and mirrors the dataset resolver logic currently copied from `tests/conftest.py`.
    - Author `dbex/tools/mapping_dataset_metrics.py` that exposes `main()` with the existing CLI surface (case selection, ROI artifact emission, diff computation) but routes everything through `build_mapping_stage_a_context`, the new calibration variant helpers, and owner plotting utilities. Export an importable `run_mapping_dataset_metrics(cases, config)` function so future probes/tests can call it programmatically.
    - Reduce the plan script to a compatibility shim (`from dbex.tools import mapping_dataset_metrics as tool; tool.main()`) and update documentation/plan notes so all references point at `python -m dbex.tools.mapping_dataset_metrics`.
    - Validation: run the canonical metadata cases (e.g., `metadata_raw`, `metadata_calibrated`) via the new CLI under `DBEX_SMOKE_SIGMA_SOURCE=metadata` and capture `mapping_dataset_metrics.json`, ROI artifact samples, and the console log under the reserved report directory so investigators can trust the new owner path.
- [x] B6: Promote `plans/active/TOOLING-VIS-001/bin/capture_smoke_calibration.py` into a canonical calibration tool so DiffBragg smoke bundles are generated by owner modules rather than a 300+ LOC plan script.
    - Introduce `dbex/calibration/smoke_capture.py` (helpers) plus `dbex/tools/capture_smoke_calibration.py` (CLI) that expose the existing flags (`--expt`, `--refl`, `--mask`, `--mtz`, `--out-config`, `--refined-mtz-out`, `--manifest`, macro-cycle controls) via `python -m dbex.tools.capture_smoke_calibration`.
    - Reduce the plan-local script to a shim (`from dbex.tools import capture_smoke_calibration as tool; tool.main()`) and update authoritative docs (`docs/data_dependency_manifest.md`, TOOLING-VIS-001 implementation notes, `dbex/tools/README.md`) so operators invoke the owner CLI.
    - Validation: run the canonical metadata capture twice (full detector and refGeom_small) writing configs + optional refined MTZ + manifests + logs under `plans/active/ARCH-PROBE-FREEZE-001/reports/<timestamp>/capture_{full,small}/`. Leave tracked `sp.proc/calibration/*.json/.mtz` untouched—the goal is to prove the new owner CLI reproduces the bundle end-to-end with SHA256 evidence.
    - Status 2025-12-30T150000Z: ✅ Complete — helpers/CLI landed, shim reduced to 36 LOC, docs updated, dual validation logs captured (`plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-30T150000Z/{capture_full,capture_small}/`).

**Artifacts:** Updated source diffs, telemetry docs, and script tombstones stored under `plans/active/ARCH-PROBE-FREEZE-001/reports/<timestamp>/`.

## Phase C — Enforcement & Guardrails
- [x] C1: Author `tests/architecture/test_probe_contracts.py::test_plan_scripts_only_wrap_owner_apis` that enforces diagnostic_script_policy mechanically. **Complete (2025-12-31T010000Z)** — tests/architecture module now contains `test_plan_bin_growth_cap` (400 LOC cap + explicit `GROWTH_CAP_EXCEPTIONS` allowlist) and `test_probe_shims_delegate_to_owner_clis` (AST guard for the new shims). Docs/TESTING_GUIDE.md gained execution guidance, and artifacts live under `plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-31T010000Z/`.
- [ ] C2: Finalize policy docs so the mechanical guard becomes canonical guidance.
    - Expand `prompts/supervisor.md::diagnostic_script_policy` with an explicit reference to `tests/architecture/test_probe_contracts.py`, allowlist maintenance rules, shim roster, and artifact expectations so future supervisors interpret the guard correctly.
    - Cross-check `docs/TESTING_GUIDE.md` section that describes the enforcement test (added 2025-12-31) once the prompt updates land to keep the two sources in sync.
- [ ] C3: Add CI/docs hooks (galph_prompt excerpt + findings) reminding future loops to add telemetry instead of scripts.
    - Introduce a new knowledge-base entry in `docs/findings.md` (e.g., PROBE-FREEZE-001) that cites the architecture test, diagnostic policy section, and the requirement to migrate probes into owner telemetry before extending plan scripts.
    - Update `docs/fix_plan.md`/Problems Ledger references once the finding is live so CI + planning tooling cross-link to the enforcement test.

**Exit Artifact:** Architecture test log + enforcement summary under `plans/active/ARCH-PROBE-FREEZE-001/reports/<timestamp>/`.

## Risks & Mitigations
- **Risk:** Deleting scripts before telemetry exists breaks ongoing investigations.
  - *Mitigation:* Phase B requires telemetry landing before script retirement; note dependencies in docs/fix_plan.md.
- **Risk:** Architecture test over-matches legitimate thin wrappers.
  - *Mitigation:* Start with allowlist (owner APIs, CLI entry points). Document exemptions explicitly.
- **Risk:** Environment Freeze prevents necessary telemetry patches.
  - *Mitigation:* Follow CLAUDE.md exception path (patch file, findings entry, rebuild tag) for any nanobrag_torch edits.

## Artifacts Root
`plans/active/ARCH-PROBE-FREEZE-001/reports/`
