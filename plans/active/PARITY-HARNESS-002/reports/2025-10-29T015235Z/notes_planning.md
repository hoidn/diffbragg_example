# PARITY-HARNESS-002 Planning Notes — 2025-10-29T015235Z

## Reality Check
- TORCH-BRIDGE-001 and FORWARD-EQUIV-001 marked done in `docs/fix_plan.md`; parity harness can reuse bridge fixtures and forward metrics helpers.
- Existing DB_AT_001 manifest tests (3 passing) confirmed via `plans/active/PARITY-HARNESS-002/reports/2025-10-29T010131Z/pytest_DB_AT_001.log`; selector currently exercises only manifest integrity.
- Golden dataset manifest checksum (`df88c7d2…`) matches recorded `checksums.txt`; verified with `sha256sum` spot check.
- No metrics helper or parity artifacts currently emitted; `tests/dbex/test_db_at_001_parity.py` lacks DiffBragg vs torch comparisons.

## Key References
- `docs/spec-db-conformance.md:23-26` (DB_AT_001 thresholds and xfail policy)
- `docs/forward_equivalence.md:30-53` (ROI metrics, localization rules)
- `docs/spec-db-core.md:20-40` (pixel ordering, square pixel guard)
- `docs/spec-db-tracing.md:10-24` (artifact + trace layout requirements)
- Findings: CONFORMANCE-001, GEOMETRY-001, MASKING-001, DIAGNOSTICS-001, TESTING-003

## Plan Outline
1. Implement `compute_parity_metrics()` to mirror forward-equivalence calculations and expose deterministic metrics for stub simulators (B1).
2. Add artifact writers under `reports/<ts>/parity_harness/` capturing metrics JSON/CSV, overlay placeholders, and manifest checksum (B2).
3. Extend DB_AT_001 parity test to run DiffBragg/torch forward passes, call metrics helper, and conditional-xfail when stub results miss thresholds; seed RNG for reproducibility (B3).
4. Synchronize testing docs, ledger, and selector evidence once metrics-based parity test is in place (C3).

## Risks & Mitigations
- Torch simulator still stubbed → enforce `xfail` with diagnostic reason and commit artifact paths for post-stub analysis.
- Metrics helper may require ROI sampling; reuse sampling fraction (20%) from forward-equivalence harness to keep runtime reasonable.
- Trace hooks not yet wired; capture TODO in Phase D if trace API unavailable.

## Next Actions
- Execute Do Now checklist in `input.md` (B1-B3, C3) with logs stored under `plans/active/PARITY-HARNESS-002/reports/2025-10-29T015235Z/`.
- Update `docs/fix_plan.md` Attempts History upon completion with Metrics/Artifacts lines referencing new logs.
