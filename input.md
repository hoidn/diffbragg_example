Summary: Instrument DB_AT_001 parity harness with first-divergence diagnostics and refresh docs/test evidence.
Mode: Parity
Focus: PARITY-HARNESS-002 — Implement DB-AT parity harness tests
Branch: integration
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py; KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001
Artifacts: plans/active/PARITY-HARNESS-002/reports/2025-10-29T020937Z/
Do Now:
  1. PARITY-HARNESS-002.D1 (plans/active/PARITY-HARNESS-002/implementation.md) — Extend parity utilities to compute per-ROI metrics, capture first-divergence metadata, and wire artifact emission into the DB_AT_001 parity smoke; tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py
  2. PARITY-HARNESS-002.D2 (plans/active/PARITY-HARNESS-002/implementation.md) — Record new durable lessons plus append fix_plan Attempts History with Metrics:/Artifacts: placeholders referencing the 2025-10-29T020937Z run; tests: none — docs/ledger updates
  3. PARITY-HARNESS-002.C3 (plans/active/PARITY-HARNESS-002/implementation.md) — Sync docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md with first-divergence artifacts and refreshed collect-only evidence; tests: KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001
Priorities & Rationale:
- docs/spec-db-conformance.md:23-26 — DB_AT_001 must enforce correlation/localization thresholds while emitting diagnostics, so new first-divergence metrics strengthen xfail evidence.
- docs/forward_equivalence.md:30-52 — ROI metric and trace capture guidance drive the per-ROI scan and artifact layout.
- docs/spec-db-tracing.md:10-19 — Normative first-divergence workflow requires instrumentation that pinpoints the earliest mismatch.
- docs/TESTING_GUIDE.md:84 and docs/development/TEST_SUITE_INDEX.md:14 — Parity selector documentation must stay in sync with artifacts/log counts.
- docs/spec-db-core.md:20-40 — Geometry/pixel ordering invariants constrain how we compute ROI metrics and produce artifacts.
How-To Map:
- export KMP_DUPLICATE_LIB_OK=TRUE
- mkdir -p plans/active/PARITY-HARNESS-002/reports/2025-10-29T020937Z/parity_harness
- pytest -v tests/dbex/test_db_at_001_parity.py | tee plans/active/PARITY-HARNESS-002/reports/2025-10-29T020937Z/pytest_db_at_001.log
- pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001 | tee plans/active/PARITY-HARNESS-002/reports/2025-10-29T020937Z/collect_db_at_001.log
- python - <<'PY'
import json, pathlib
path = pathlib.Path('plans/active/PARITY-HARNESS-002/reports/2025-10-29T020937Z/parity_harness/first_divergence.json')
if path.exists():
    print(json.dumps(json.loads(path.read_text()), indent=2))
PY
Pitfalls To Avoid:
- Reusing the 2025-10-29T015235Z artifact directory instead of writing to 2025-10-29T020937Z.
- Letting RNG seeding drift, which would make first-divergence selection non-deterministic.
- Dropping manifest checksum or metadata fields from new artifact payloads.
- Converting the DB_AT_001 xfail into a hard failure when thresholds are unmet.
- Forgetting to regenerate collect-only evidence before updating docs.
- Omitting Metrics:/Artifacts: lines in docs/fix_plan.md for the new attempt.
- Leaving TESTING_GUIDE/TEST_SUITE_INDEX parity rows stale after instrumentation changes.
- Allowing new ROI metrics to ignore the loss mask (must respect sparse coverage per spec).
- Writing oversized tensors outside the parity_harness/ subdirectory or committing artifacts.
If Blocked:
- If per-ROI analysis cannot run (e.g., SciPy import issues), log the failure reason, capture stderr under reports/2025-10-29T020937Z/, mark docs/fix_plan.md entry `blocked`, and update galph_memory before pivoting.
- If golden fixtures fail checksum validation, rerun the generator or note the discrepancy as a blocker in fix_plan Attempts History and pause implementation.
Findings Applied (Mandatory):
- CONFORMANCE-001 — Plan enforces DB_AT_001 thresholds and diagnostic artifact policy during parity runs.
- GEOMETRY-001 — ROI analysis honors `[panel, slow, fast]` ordering and square-pixel guards.
- MASKING-001 — Metrics interpretation accounts for sparse loss mask coverage.
- DIAGNOSTICS-001 — Artifact capture aligns with `/torch_diagnostics` metadata expectations.
- TESTING-003 — Collect-only proof and doc sync remain part of closure.
Doc Sync Plan (Mandatory):
- KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001 | tee plans/active/PARITY-HARNESS-002/reports/2025-10-29T020937Z/collect_db_at_001.log — update docs/TESTING_GUIDE.md §2 parity row and docs/development/TEST_SUITE_INDEX.md Active table with new artifact paths and counts.
