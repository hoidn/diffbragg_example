# MAP-SCALE-001 Loop Summary: Refined Structure Factor Plan (2025-11-04T120500Z)

## Objective
Finalize the MAP-SCALE-001 prep work by specifying how Ralph should source DiffBragg-refined structure factors (`Fopt`) for the zero-iteration helper so DB_AT_024 can enforce its thresholds without an xfail.

## Current Evidence
- Applying √spot_scale from `config_torch.json` alone overshoots Bragg intensities by ~2.3e4× (plans/active/MAP-SCALE-001/reports/2025-11-04T110000Z/mapping_metrics.json).
- Canonical golden dataset (`bragg_torch.npy`) uses refined `Fopt` values that are ~9.4e4× smaller than the raw MTZ amplitudes (plans/active/MAP-SCALE-001/reports/2025-11-04T084948Z/golden_comparison.json).
- DiffBragg refinement already emits the refined MTZ (`_temp.mtz`) during `scripts/generate_simple_cubic_golden.py` and `dbex/run_diffbragg.py`; the file is currently discarded after artifact generation.

## Remediation Strategy
1. **Persist refined Fopt fixture**
   - Update `scripts/generate_simple_cubic_golden.py` to retain the refined MTZ as `refined_structure_factors.mtz` alongside existing fixtures and enumerate it in `manifest.json`.
   - Copy the generated MTZ into `tests/fixtures/golden_data/simple_cubic/` for DB_AT_024.
2. **Load refined amplitudes in tests**
   - Extend `tests/dbex/test_mapping_consistency.py` to prefer the refined MTZ when present (keep fallback to `scaled.mtz`).
   - Pass the refined amplitudes into `simulate_forward_once` so the helper receives `Fopt` instead of raw `|F|`.
3. **Enforce acceptance thresholds**
   - Remove the provisional xfail and assert corr ≥ 0.2 and localization ≥ 0.90 using the refined inputs.
   - Archive updated metrics (JSON/CSV) under the new artifact directory.

## Validation Plan
- Targeted test: `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBAT024_ARTIFACT_DIR=plans/active/MAP-SCALE-001/reports/2025-11-04T120500Z pytest -v tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke --maxfail=1`
- Expect corr≈0.99 and localization≈0.94 (matching canonical golden dataset metrics).

## Documentation / Ledger Updates
- Update `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` once the selector passes without xfail.
- Add an Attempts History row in `docs/fix_plan.md` (this loop) referencing this summary and the refined-structure-factor plan.

## Next Actions
Hand the attached Do Now to Ralph to implement the refined structure factor plumbing and re-run DB_AT_024.
