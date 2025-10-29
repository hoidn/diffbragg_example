Summary: Prepare DB_AT_001 to compare DiffBragg vs torch forward passes and capture parity diagnostics.
Mode: Parity
Focus: FORWARD-EQUIV-001 — Forward equivalence smoke validation
Branch: integration
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE python3 -m pytest -v tests -k DB_AT_001
Artifacts: plans/active/FORWARD-EQUIV-001/reports/2025-10-29T013411Z/forward_equiv/
Do Now:
  1. FORWARD-EQUIV-001.A1 (plans/active/FORWARD-EQUIV-001/implementation.md) — Validate refGeom assets and golden parity dataset availability; log findings in reports/2025-10-29T013411Z/notes_planning.md; tests: none.
  2. FORWARD-EQUIV-001.A2-A4 (plans/active/FORWARD-EQUIV-001/implementation.md) — Capture DiffBragg and torch baseline tensors/configs and establish forward_equiv/{legacy,torch} artifact layout; tests: none.
  3. FORWARD-EQUIV-001.B1-B3 (plans/active/FORWARD-EQUIV-001/implementation.md) — Implement ROI metrics + xfail policy and persist metrics.json, roi_metrics.csv, overlays/traces; tests: KMP_DUPLICATE_LIB_OK=TRUE python3 -m pytest -v tests/dbex/test_forward_equivalence.py -k DB_AT_001.
  4. FORWARD-EQUIV-001.C1-C3 (plans/active/FORWARD-EQUIV-001/implementation.md) — Sync selector docs, update spec references, and refresh ledger Metrics/Artifacts; tests: KMP_DUPLICATE_LIB_OK=TRUE python3 -m pytest --collect-only -q tests -k DB_AT_001.
Priorities & Rationale:
- CONFORMANCE-001 (`docs/spec-db-conformance.md:18-33`) mandates DB_AT selectors capture parity metrics with KMP_DUPLICATE_LIB_OK=TRUE, so steps B/C focus on metric helpers, xfail policy, and documentation sync.
- CONFIG-001 (`docs/config_crosswalk.md:15-95`) and DXTBX-001 (`dbex/nanobrag_bridge.py:120-399`) require us to reuse bridge hydrations for both DiffBragg and torch paths to ensure geometry consistency in Phase A/B helpers.
- MASKING-001 (`docs/spec-db-workflow.md:24-29`) highlights sparse loss mask coverage, guiding B1 metric calculations to avoid treating low coverage as failure.
- TESTING-003 (`docs/TESTING_GUIDE.md:56-68`) requires selector collection evidence; Do Now step 4 records collect-only logs and syncs docs.
- docs/forward_equivalence.md:12-98 defines acceptance thresholds and artifact layout, informing the structure of A2-A4 and B2-B3 deliverables.
How-To Map:
- `export KMP_DUPLICATE_LIB_OK=TRUE`
- `python3 -m pytest -v tests/dbex/test_forward_equivalence.py -k DB_AT_001`
- `python3 -m pytest --collect-only -q tests -k DB_AT_001 > plans/active/FORWARD-EQUIV-001/reports/2025-10-29T013411Z/forward_equiv/collect_db_at_001.log`
- `python3 -m pytest -v tests/dbex/test_db_at_001_parity.py > plans/active/FORWARD-EQUIV-001/reports/2025-10-29T013411Z/forward_equiv/pytest_db_at_001.log`
- `python3 -m pytest -v tests/dbex/test_nanobrag_smoke.py > plans/active/FORWARD-EQUIV-001/reports/2025-10-29T013411Z/forward_equiv/pytest_smoke.log`
Pitfalls To Avoid:
- Forgetting to seed the torch stub RNG, leading to non-reproducible metrics.
- Overwriting existing parity manifest tests; keep manifest integrity suite intact.
- Failing to capture artifact paths in pytest output/logs for ledger references.
- Letting DB_AT_001 fail hard when thresholds miss; enforce xfail with diagnostics.
- Skipping collect-only evidence or doc sync, violating TESTING-003.
- Neglecting KMP_DUPLICATE_LIB_OK=TRUE, causing OMP duplicate library crashes.
- Writing artifacts outside `forward_equiv/`, breaking policy.
If Blocked:
- If DiffBragg forward capture fails, document error, downgrade status to blocked in docs/fix_plan.md, and log issue in attempts history before pivoting.
- If refGeom assets absent, run README Step 5 to regenerate or record TODO in docs/fix_plan.md and galph_memory.md; pause further work until assets restored.
Findings Applied (Mandatory):
- CONFORMANCE-001 — Plan enforces selector parity metrics and environment flag.
- CONFIG-001 — Bridge hydration reused to ensure consistent geometry across backends.
- MASKING-001 — Loss mask coverage expectations shape metric interpretation.
- TESTING-003 — Collect-only evidence and doc sync explicitly scheduled.
Doc Sync Plan (Mandatory):
- Selector `DB_AT_001`: `KMP_DUPLICATE_LIB_OK=TRUE python3 -m pytest --collect-only -q tests -k DB_AT_001 > plans/active/FORWARD-EQUIV-001/reports/2025-10-29T013411Z/forward_equiv/collect_db_at_001.log`; update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md entries with artifact path.
- Smoke companion selector (nanobrag bridge): `KMP_DUPLICATE_LIB_OK=TRUE python3 -m pytest --collect-only -q tests/dbex/test_nanobrag_smoke.py > plans/active/FORWARD-EQUIV-001/reports/2025-10-29T013411Z/forward_equiv/collect_smoke.log`; cross-check docs already referencing selector stay accurate.
