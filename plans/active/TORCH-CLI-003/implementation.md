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
- [ ] A0: Author minimal CLI test file `tests/dbex/test_refine_one_cli.py` (parser/help and backend switch), run `pytest --collect-only` and save log under reports path; register selector in testing docs.
- [ ] A1: Add `--backend` option and plumb to execution path
- [ ] A2: Wire torch path to `nanobrag_bridge` and model run (guarded behind flag)

### Validation & Artifacts
- Selectors: `pytest -v tests/dbex/test_refine_one_cli.py`
- Artifacts path: `plans/active/TORCH-CLI-003/reports/<timestamp>/`

## Phase B — Diagnostics & Docs
### Checklist
- [ ] B1: Log minimal diagnostics for torch path; update CLI help
- [ ] B2: Update docs/index.md entry and confirm smoke selector

### Validation & Artifacts
- Selector compliance: `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_refine_one_cli.py | tee "$ART/collect_cli.log"`
- Doc sync: Update `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` with CLI selector and reference artifact path.

## Artifacts Index
- Reports root: `plans/active/TORCH-CLI-003/reports/`
