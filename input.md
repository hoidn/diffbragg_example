Summary: Repoint DB-AT-001 parity smoke to the new nanobrag backend run and capture fresh artifacts/metrics.
Mode: Parity
Focus: NANOBRAG-BACKEND-002 — Replace CLI torch backend stub with nanobrag_torch simulator
Branch: integration
Mapped tests: tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke
Artifacts: plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T033317Z/

Do Now:
- Focus NANOBRAG-BACKEND-002
  - Implement: tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke (move parity artifact path to 2025-11-04T033317Z under NANOBRAG-BACKEND-002 and retain checksum guard)
  - Validate: KMP_DUPLICATE_LIB_OK=TRUE AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke
  - Artifacts: plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T033317Z/

How-To Map:
1. export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md; export KMP_DUPLICATE_LIB_OK=TRUE (parity selectors require both, per docs/TESTING_GUIDE.md §1.1).
2. Edit tests/dbex/test_db_at_001_parity.py:767 to point `artifact_dir` at plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T033317Z/parity_harness; keep existing manifest checksum assertion untouched.
3. KMP_DUPLICATE_LIB_OK=TRUE AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -v tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke | tee plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T033317Z/pytest_db_at_001.log
   • Expect correlation ≥0.20 and localization ≥0.90; if thresholds fail, do not clear xfail.
4. KMP_DUPLICATE_LIB_OK=TRUE AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_db_at_001_parity.py -k DB_AT_001 | tee plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T033317Z/collect_db_at_001_parity.log
5. Confirm parity artifacts landed (metrics.json, metrics.csv, predicted.npy, target.npy, first_divergence.json) via ls plans/active/NANOBRAG-BACKEND-002/reports/2025-11-04T033317Z/parity_harness/parity_harness
6. Update docs/TESTING_GUIDE.md:87 and docs/development/TEST_SUITE_INDEX.md:14 to reference the new artifact/log paths and refreshed metrics; record same metrics + artifacts in docs/fix_plan.md Attempts History once the test passes.

Pitfalls To Avoid:
- Do not scale structure factors inside build_structure_factor_grid (SCALE-001) or reintroduce sqrt scaling before the simulator.
- Keep sqrt(spot_scale_override) applied post-simulation only; unexpected scaling shifts parity metrics (SCALE-002).
- Preserve manifest checksum assertion; changing the expected hash violates MANIFEST-001 and masks corrupted fixtures.
- Maintain CPU execution for the parity run; switching devices can disturb determinism noted in docs/pytorch_runtime_checklist.md.
- Capture pytest/collect logs under the 2025-11-04T033317Z report; stale paths break TESTING-003 compliance.
- Leave pytest.xfail guard logic unchanged unless thresholds genuinely pass; premature removal regresses diagnostics expectations.
- No environment/package installs—Environment Freeze applies; if nanobrag_torch import fails, stop and record blocker.

If Blocked:
- Capture the failure output, record metrics.json (even if below thresholds), and append a blocked entry to docs/fix_plan.md with the pytest selector and error text.
- Leave parity artifacts in place for triage and flag the issue in galph_memory.md; do not downgrade thresholds without supervisor signoff.

Findings Applied (Mandatory):
- SCALE-001 — Structure factors remain unscaled prior to simulation; parity metrics assume this behavior.
- SCALE-002 — Apply sqrt(spot_scale_override) post-sim; validate resulting Bragg intensities against thresholds.
- GEOMETRY-002 — Analytic detector Euler inversion must remain intact while running parity smoke.
- HKL-ORIENT-001 — Incident beam vector stays source→sample; do not modify loader defaults.
- MANIFEST-001 — Honor checksum validation when loading canonical golden data.
- TESTING-003 — Log pytest + collect-only outputs and sync documentation in the same loop.

Pointers:
- docs/fix_plan.md:93 — Current Attempts History entry outlining parity validation next steps.
- plans/active/NANOBRAG-BACKEND-002/implementation.md:47 — Phase C checklist and notes for parity/doc sync.
- tests/dbex/test_db_at_001_parity.py:767 — Artifact directory constant to update.
- docs/TESTING_GUIDE.md:87 — Parity harness documentation that must be kept in sync post-run.
- docs/development/TEST_SUITE_INDEX.md:14 — Test index entry listing parity harness selector/log locations.

Next Up (optional):
1. Regenerate nanobrag CLI HDF5 outputs with `--backend nanobrag` and compare ROI diagnostics to DB_AT_001 metrics if time permits.
