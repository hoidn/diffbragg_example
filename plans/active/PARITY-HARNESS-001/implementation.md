# Implementation Plan — PARITY-HARNESS-001

## Initiative
- ID: PARITY-HARNESS-001
- Title: Author DB-AT parity harness specs
- Owner: Unassigned
- Status: in_progress

## Goals
- Translate Spec DB parity acceptance tests (DB-AT-001/002) into actionable harness documentation and checklists.
- Synchronize parity documentation across spec shards, testing guides, and prompt sources.

## Phases Overview
- Phase A — Evidence Audit: inventory existing parity specs, selectors, and artifacts to ground the harness scope.
- Phase B — Harness Blueprint: author normative parity harness spec and phased checklist aligned with DB-AT requirements.
- Phase C — Cross-Doc Sync: propagate references to the new harness doc and update prompt/source maps.

## Exit Criteria
1. Normative harness specification for DB-AT-001 and DB-AT-002 documented with datasets, metrics, and tolerance targets (`docs/spec-db-conformance.md:10-36`, `docs/development/testing_strategy.md:1-160`).
2. `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` entries for `DB_AT_001`/`DB_AT_002` include commands, env flags, and artifact expectations consistent with the harness spec.
3. `docs/index.md` and `docs/prompt_sources_map.json` reference the harness specification and this implementation plan.
4. Artifact report captures evidence of doc updates and selector synchronization under `plans/active/PARITY-HARNESS-001/reports/<timestamp>/`.

## Phase A — Evidence Audit
### Checklist
- [ ] A1: Catalog current parity guidance across `docs/spec-db-conformance.md`, `docs/development/testing_strategy.md`, and `docs/TESTING_GUIDE.md`; note gaps vs exit criteria.
- [ ] A2: Inspect prior parity-related artifacts (`plans/active/TORCH-BRIDGE-001/`, `plans/active/TORCH-CLI-003/`) for reusable metrics or lessons to anchor the harness spec.
- [ ] A3: Define artifact strategy (`reports/<timestamp>/`) for parity harness documentation (log commands, summary.md blueprint).

### Notes & Risks
- Golden datasets (`nanoBragg2/tests/golden_data/`) may be missing locally; document mitigations if unavailable.

## Phase B — Harness Blueprint
### Checklist
- [ ] B1: Draft `docs/parity_harness_spec.md` (or equivalent) detailing inputs, commands, and evaluation metrics for DB-AT-001/002, citing spec shards.
- [ ] B2: Encode phased harness rollout tasks in this implementation plan (update checklist statuses, add sub-items if needed).
- [ ] B3: Prepare metrics/trace capture template (e.g., `metrics.json` schema) and reference it within the harness spec.

### Notes & Risks
- Ensure diagnostics align with tracing requirements (`docs/spec-db-tracing.md:15-60`) to avoid divergent workflows.

## Phase C — Cross-Doc Sync
### Checklist
- [ ] C1: Update `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` entries for DB-AT-001/002 with finalized harness details and selectors.
- [ ] C2: Add harness references to `docs/index.md` and `docs/prompt_sources_map.json`; confirm prompt discoverability.
- [ ] C3: Capture final evidence report (`summary.md`, `doc_diffs.log`) under `plans/active/PARITY-HARNESS-001/reports/<timestamp>/` and update `docs/fix_plan.md` Attempts History with Metrics/Artifacts lines.

### Notes & Risks
- Keep documentation updates synchronized to avoid conflicting instructions across prompts.

## Artifacts Index
- Reports root: `plans/active/PARITY-HARNESS-001/reports/`
- Latest run: Pending (`<YYYY-MM-DDTHHMMSSZ>/`)
