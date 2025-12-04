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
- [ ] B1: Migrate the Stage A baseline probe metrics into owner code:
    - Extend `RefinementConfig` / Stage A so an opt-in flag (or metrics path/env var) records the masked means, ROI Pearson stats, chi²/pixel, and ROI snippets currently computed inside `compare_stage_a_baseline.py`.
    - Add a typed payload (e.g., `StageABaselineMetrics`) to `StageAArtifacts` and a JSON dump hook so plan tools/tests can consume the metrics without rebuilding Stage A manually.
- [ ] B2: Refactor `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py` into a thin wrapper that simply loads the canonical dataset, flips the new Stage A debug flag, runs `RefinementEngine` (Stage A only), and persists the emitted telemetry/artifact bundle. No direct simulator/ROI math should remain.
- [ ] B3: Add/refresh pytest coverage (e.g., `tests/dbex/test_stage_a_smoke_parity.py::test_stage_a_baseline_metrics_dump`) plus rerun DB-AT-028/029 so the new telemetry path is proven decision-carrying. Once green, update `probe_inventory` to reclassify the script as thin wrapper and mark the Phase B tasks complete in docs/fix_plan.md.
    - Status 2025-12-28T150000Z: helper + standalone pytest exist, and the probe is now a thin wrapper, but `tests/dbex/test_stage_a_smoke_parity.py::stage_a_smoke_result` never toggles `enable_stage_a_baseline_metrics` nor honors the `DBEX_STAGE_A_BASELINE_METRICS_PATH` env knob. DB-AT-028/029 still emit metrics without Stage A baseline JSON, so parity evidence continues to depend on the deprecated probe. Next loop must wire the env/config plumbing, expose the resolved JSON path on the fixture result, and assert within the DB-AT selectors that the produced file matches the schema.

**Artifacts:** Updated source diffs, telemetry docs, and script tombstones stored under `plans/active/ARCH-PROBE-FREEZE-001/reports/<timestamp>/`.

## Phase C — Enforcement & Guardrails
- [ ] C1: Author `tests/architecture/test_probe_contracts.py::test_plan_scripts_only_wrap_owner_apis` that scans plan-local bins for forbidden modules/patterns (e.g., importing `torch`, reimplementing `simulate_forward_once`, performing ROI math) and fails when violations appear.
- [ ] C2: Update docs/diagnostic_script_policy and docs/TESTING_GUIDE.md with the new enforcement expectations and collection command for the architecture test (`pytest --collect-only tests/architecture/test_probe_contracts.py`).
- [ ] C3: Add CI/docs hooks (galph_prompt excerpt + findings) reminding future loops to add telemetry instead of scripts.

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
