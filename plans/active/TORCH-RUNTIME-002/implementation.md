# Implementation Plan — TORCH-RUNTIME-002

ID: TORCH-RUNTIME-002
Title: Author torch runtime checklist + testing harness seed
Owner: Unassigned
Status: pending

## Goals
- Establish canonical environment flags, selectors, and artifact policy for pytest runs.
- Seed parity/runtime selectors and capture example artifacts.

## Phases Overview
- Phase A — Runtime Docs & Flags
- Phase B — Selectors & Harness Seed

## Exit Criteria
1. `docs/TESTING_GUIDE.md` documents smoke/acceptance commands and environment flags.
2. Minimal pytest selector (or placeholder) captured for DB-AT parity suites.
3. Artifact example captured under the initiative’s reports directory.
4. Ledger entry includes Metrics/Artifacts lines referencing the recorded run or TODO.
5. Test registry synchronized: `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` reflect the current selector set; `pytest --collect-only` logs for documented selectors are saved under `plans/active/TORCH-RUNTIME-002/reports/<timestamp>/`.

## Phase A — Runtime Docs & Flags
### Checklist
- [x] A1: Ensure `KMP_DUPLICATE_LIB_OK=TRUE` and gradcheck flag are documented
- [x] A2: Add "Common Pitfalls" for runtime to testing strategy

## Phase B — Selectors & Harness Seed
### Checklist
- [x] B1: Add minimal DB-AT selector placeholder and document it
- [x] B2: Capture a smoke artifact and reference it in the ledger

### Validation & Artifacts
- Selector compliance (planned placeholders expected to collect 0):
  - `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q -k DB_AT_001 | tee "$ART/collect_DB_AT_001.log"`
  - `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q -k DB_AT_002 | tee "$ART/collect_DB_AT_002.log"`
- Doc sync: ensure Testing Guide §2 and Test Suite Index mirror selectors and status.

## Artifacts Index
- Reports root: `plans/active/TORCH-RUNTIME-002/reports/`
