# Implementation Plan — FINDINGS-LEDGER-002

ID: FINDINGS-LEDGER-002
Title: Extend knowledge base with torch experiment lessons
Owner: Unassigned
Status: in_progress

## Goals
- Review recent torch bridge and CLI artifacts to extract durable lessons.
- Expand `docs/findings.md` with well-scoped entries that reference authoritative specs and code.
- Cross-link new findings into operational docs so future loops can rely on them.
- Capture evidence and keep the fix-plan ledger/tests registry in sync.

## Exit Criteria
1. At least three new findings added to `docs/findings.md` with IDs, tags, summaries, and spec/code citations.
2. Each new finding is referenced from the relevant operational docs (`docs/TESTING_GUIDE.md`, `docs/architecture.md`, or similar) and indexed in `docs/prompt_sources_map.json` if needed.
3. Artifact summary (`summary.md`) recorded under `plans/active/FINDINGS-LEDGER-002/reports/<timestamp>/` detailing reviewed sources and resulting updates.
4. `docs/fix_plan.md` Attempts History updated with Metrics/Artifacts lines referencing the collected evidence.

## Phase A — Artifact Survey
### Checklist
- [ ] A1: Inventory existing reports under `plans/active/TORCH-BRIDGE-001/` and `plans/active/TORCH-CLI-003/`; capture key metrics and diagnostics (e.g., `smoke_metrics.json`, `pytest_cli.log`).
- [ ] A2: Extract candidate lessons (geometry, runtime, CLI diagnostics) into a working notes file; ensure coverage across bridge + CLI domains.
- [ ] A3: Validate that proposed findings do not duplicate existing ledger entries (`docs/findings.md`).

### Validation & Artifacts
- Commands: `ls plans/active/TORCH-BRIDGE-001/reports/*`, `ls plans/active/TORCH-CLI-003/reports/*`
- Notes Artifact: `$ART/notes_phase_a.md`

## Phase B — Findings Drafting
### Checklist
- [ ] B1: Define new finding IDs, tags, and summaries mapped to source specs/code (minimum three entries).
- [ ] B2: Update `docs/findings.md` with drafted entries; preserve table formatting.
- [ ] B3: Self-review for clarity and spec/code citation accuracy; adjust wording to match ledger style.

### Validation & Artifacts
- Commands: `python scripts/orchestration/check_input.py --validate-findings docs/findings.md` (if available), manual formatting review.
- Document Artifact: `$ART/findings_diff.log` (`git diff docs/findings.md`).

## Phase C — Cross-References & Registry
### Checklist
- [ ] C1: Add cross-links to new findings within `docs/TESTING_GUIDE.md`, `docs/development/testing_strategy.md`, or `docs/architecture.md` where applicable.
- [ ] C2: Ensure `docs/index.md` and `docs/prompt_sources_map.json` still reference the knowledge base accurately; update if new sections introduced.
- [ ] C3: Capture `pytest --collect-only` evidence for any selectors referenced by new findings (max 2 selectors) and store logs.

### Validation & Artifacts
- Commands:
  - `pytest --collect-only -q <selector>` per selector referenced (respecting env vars).
  - `git diff docs/TESTING_GUIDE.md docs/development/TEST_SUITE_INDEX.md docs/index.md docs/prompt_sources_map.json`
- Artifact paths: `$ART/collect_<selector>.log`, `$ART/doc_updates.log`

## Phase D — Ledger & Evidence Sync
### Checklist
- [ ] D1: Update `docs/fix_plan.md` Attempts History with Metrics (counts of new findings/selectors) and Artifacts (reports path).
- [ ] D2: Save `summary.md` enumerating lessons, cross-links, and verification commands to `$ART/summary.md`.
- [ ] D3: Verify repo status clean except intended changes; ensure new findings referenced in `galph_memory.md` entry.

### Validation & Artifacts
- Commands: `git status --short`, `ls $ART`
- Artifact: `$ART/summary.md`

## Artifacts Index
- Reports root: `plans/active/FINDINGS-LEDGER-002/reports/`
