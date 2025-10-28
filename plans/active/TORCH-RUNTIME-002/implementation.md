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

## Phase A — Runtime Docs & Flags
### Checklist
- [ ] A1: Ensure `KMP_DUPLICATE_LIB_OK=TRUE` and gradcheck flag are documented
- [ ] A2: Add “Common Pitfalls” for runtime to testing strategy

## Phase B — Selectors & Harness Seed
### Checklist
- [ ] B1: Add minimal DB-AT selector placeholder and document it
- [ ] B2: Capture a smoke artifact and reference it in the ledger

## Artifacts Index
- Reports root: `plans/active/TORCH-RUNTIME-002/reports/`
