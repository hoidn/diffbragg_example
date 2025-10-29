# Implementation Plan Template (Phased)

> Copy this file to `plans/active/<initiative-id>/implementation.md` and customize.

## Initiative
- ID: <initiative-id>
- Title: <short title>
- Owner: <name>
- Status: pending | in_progress | blocked | done | archived

## Goals
- <goal 1>
- <goal 2>

## Phases Overview
- Phase A — <name>: <one-line objective>
- Phase B — <name>: <one-line objective>
- Phase C — <name>: <one-line objective>

## Exit Criteria
1. <criterion 1>
2. <criterion 2>
3. <criterion 3>
4. Test registry synchronized: `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` reflect any new/changed tests; `pytest --collect-only` logs for documented selectors are saved under `plans/active/<initiative-id>/reports/<timestamp>/`. Do not close the initiative if any selector marked "Active" collects 0 tests.

## Phase A — <name>
### Checklist
- [ ] A1: <task> (owner, expected artifacts)
- [ ] A2: <task>
- [ ] A3: <task>

### Notes & Risks
- <risk 1>

## Phase B — <name>
### Checklist
- [ ] B1: <task>
- [ ] B2: <task>

### Notes & Risks
- <risk 2>

## Phase C — <name>
### Checklist
- [ ] C1: <task>
- [ ] C2: <task>

### Notes & Risks
- <risk 3>

## Artifacts Index
- Reports root: `plans/active/<initiative-id>/reports/`
- Latest run: `<YYYY-MM-DDTHHMMSSZ>/`
