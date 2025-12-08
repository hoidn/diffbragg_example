# Implementation Plan — TORCH-CLI-003

ID: TORCH-CLI-003
Title: Wire torch backend flag into CLI
Owner: Unassigned
Status: in_progress

## Goals
- Introduce a backend flag in `dbex.refine_one` to select between DiffBragg and `nanobrag_torch`.
- Maintain output compatibility and document usage.

## Phases Overview
- Phase A — CLI Flag & Wiring
- Phase B — Diagnostics & Docs

## Exit Criteria
1. `dbex.refine_one` accepts `--backend {diffbragg,nanobrag}` with default `diffbragg`.
2. Torch branch emits `Bragg` tensor and diagnostics matching legacy layout.
3. Update docs/index.md entry for CLI to reflect backend flag.
4. Entry validated by running torch CLI smoke.
5. Test registry synchronized: `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` reflect new/changed CLI tests; `pytest --collect-only` logs for documented selectors are saved under `plans/active/TORCH-CLI-003/reports/<timestamp>/`. Do not close if any selector marked "Active" collects 0 tests.

## Phase A — CLI Flag & Wiring
### Checklist
- [x] A0: Author minimal CLI test file `tests/dbex/test_refine_one_cli.py` (parser/help and backend switch), run `pytest --collect-only` and save log under reports path; register selector in testing docs.
- [x] A1: Add `--backend` option and plumb to execution path
- [x] A2: Wire torch path to `nanobrag_bridge` and model run (guarded behind flag)

### Validation & Artifacts
- Selectors: `pytest -v tests/dbex/test_refine_one_cli.py`
- Artifacts path: `plans/active/TORCH-CLI-003/reports/<timestamp>/`

## Phase B — Diagnostics & Docs
### Checklist
- [x] B1: Log minimal diagnostics for torch path; update CLI help
- [x] B2: Update docs/index.md entry and confirm smoke selector

### Validation & Artifacts
- Selector compliance: `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_refine_one_cli.py | tee "$ART/collect_cli.log"`
- Doc sync: Update `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` with CLI selector and reference artifact path.

## Phase C — Registry & Ledger Sync
### Checklist
- [x] C1: Capture passing `pytest -v tests/dbex/test_refine_one_cli.py` run (with `KMP_DUPLICATE_LIB_OK=TRUE`), archive log, and update checklist statuses for A0–B2 once evidence confirmed.
- [x] C2: Sync `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` with CLI selector and environment requirements; rerun `--collect-only` and artifact logs.
- [x] C3: Update `docs/fix_plan.md` Attempts History with Metrics/Artifacts lines and reference the new report timestamp; ensure CLI smoke command documented in `docs/spec-db-interfaces.md` status note.

### Validation & Artifacts
- Execution: `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_refine_one_cli.py | tee "$ART/pytest_cli.log"`
- Collection: `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_refine_one_cli.py | tee "$ART/collect_cli.log"`
- Docs: Record diff summary (`git diff --stat`) and update ledger entries referencing `$ART`.

## Artifacts Index
- Reports root: `plans/active/TORCH-CLI-003/reports/`
