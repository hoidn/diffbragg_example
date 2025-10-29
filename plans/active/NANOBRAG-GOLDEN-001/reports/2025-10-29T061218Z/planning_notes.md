# 2025-10-29T061218Z — Planning Notes (NANOBRAG-GOLDEN-001)

## Reality Check
- `tests/fixtures/golden_data/simple_cubic/manifest.json` still advertises `dataset_name: "simple_cubic_fallback"`, confirming the canonical nanoBragg2 tensors have not been captured yet.
- `python3 -c "import nanobrag_torch"` and `python3 -c "import simtbx"` both raise `ModuleNotFoundError`, so neither dependency required for Phase A2/A3 is present in the frozen runtime.
- The `python` shim is absent on PATH (`bash: python: command not found`), so all diagnostics must rely on `python3`.

## Constraints & Blockers
- Environment Freeze (CLAUDE.md) forbids installing or upgrading packages mid-loop. With `simtbx` and `nanobrag_torch` both missing, the DiffBragg baseline export (Phase A2) and nanoBragg capture (Phase A3) are hard-blocked.
- Prior attempt logs (2025-10-29T055449Z) already show `test_forward_equivalence_complete.py` failing during collection because `dbex.data_load` imports `simtbx`. The blocker persists and must be documented as the current stopping condition.

## Documentation Drift
- `docs/TESTING_GUIDE.md` §2 still lists “Forward equivalence smoke” as **Active** in the first taxonomy table, even though §2.1 and `docs/development/TEST_SUITE_INDEX.md` correctly downgrade the selector to **Planned** with the same ModuleNotFoundError evidence. The taxonomy table needs to be aligned with the blocked status to satisfy TESTING-003 consistency.

## Proposed Next Steps
1. **A1 diagnostics** — Capture fresh environment evidence (PATH, `python3 --version`, failed imports, `setup_env.sh` activation) and archive it under this report to close the loop on missing dependencies without violating Environment Freeze.
2. **A2 evidence refresh** — Re-run `pytest --collect-only` for `test_db_at_001_parity.py -k DB_AT_001` (expected to collect 14 tests) and `test_forward_equivalence_complete.py -k DB_AT_001` (expected to error) so the latest artifacts document both the passing parity selector and the DiffBragg blocker.
3. **Ledger/doc updates** — Mark `NANOBRAG-GOLDEN-001` as `blocked` in `docs/fix_plan.md` with the return condition “simtbx + nanobrag_torch available under Environment Freeze exception,” update Attempts History with the new evidence paths, and reconcile the taxonomy table in `docs/TESTING_GUIDE.md` with the blocked status.
