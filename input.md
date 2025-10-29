**Summary**: Refresh the canonical DB_AT_001 fixtures and parity harness so tests operate on the captured DiffBragg↔torch tensors with complete manifest provenance.

**Mode**: Parity

**Focus**: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset

**Branch**: integration

**Mapped tests**: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001

**Artifacts**: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T181603Z/

**Do Now (hard validity contract)**
- Focus Item: NANOBRAG-GOLDEN-001 (A2, A3, B1, B2, C1)
- Implement: scripts/generate_simple_cubic_golden.py::generate_simple_cubic_golden; tests/fixtures/parity_loader.py::load_golden_data; tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity.test_db_at_001_parity_smoke
- Validate: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001
- Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T181603Z/implementation/

**Priorities & Rationale**
- CONFIG-001 & docs/spec-db-core.md:20-41 — Loader updates must honor `[panel, slow, fast]` ordering and mask polarity when ingesting the canonical stacks.
- docs/spec-db-conformance.md:23-26 & CONFORMANCE-001 — Canonical manifest provenance (actual command, git rev, checksums) is required before enforcing DB_AT_001 thresholds.
- docs/TESTING_GUIDE.md:86-87 & TESTING-003 — Keep the Active parity selector collecting >0 tests with refreshed fixtures and logs.
- docs/forward_equivalence.md:21-53 — Parity harness needs paired DiffBragg vs torch tensors to compute correlation/localization metrics without synthetic noise.
- docs/nanobrag_api.md:22-44 & HKL-ORIENT-001 — Preserve the corrected beam orientation and panel conventions when regenerating tensors so HKL coverage stays valid.

**How-To Map**
1. `apply_patch` scripts/generate_simple_cubic_golden.py to capture `sys.argv` as the generator command, resolve `git rev-parse HEAD`, add manifest self-checksums, and ensure fixture copy writes bool masks.
2. `apply_patch` tests/fixtures/parity_loader.py to load both DiffBragg and torch tensors from the canonical stack, extend `GoldenData`, and validate bool masks/shapes per the manifest.
3. `apply_patch` tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity.test_db_at_001_parity_smoke to consume canonical tensors (no RNG noise), enforce DB_AT_001 thresholds, and write artifacts under `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T181603Z/parity_harness/`.
4. `PYTHONPATH=../nanoBragg/src:$PYTHONPATH KMP_DUPLICATE_LIB_OK=TRUE python scripts/generate_simple_cubic_golden.py --canonical-out plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T181603Z/golden_dataset --hkldebug plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T181603Z/torch_hkl_debug.json --emit-manifest --fixtures tests/fixtures/golden_data/simple_cubic | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T181603Z/implementation/canonical_capture.log`
5. `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001 | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T181603Z/implementation/pytest_db_at_001.log`
6. Copy manifest/metrics/roi CSV plus sha256 summaries into the implementation directory for ledger evidence and update docs/fix_plan.md + docs/findings.md accordingly.

**Pitfalls To Avoid**
- Do not mutate the environment; missing imports must block and be logged.
- Keep bool mask dtype when saving/loading; uint8 fallbacks violate CONFIG-001.
- Ensure manifest references every tensor (including itself) so validation passes.
- Avoid reintroducing synthetic noise in parity tests; use canonical tensors only.
- Collect pytest artifacts under the new timestamped directory for ledger compliance.
- Confirm `.npy` fixtures land in git-tracked paths; do not relax `.gitignore` broadly.
- Watch for HKL coverage regressions in torch_hkl_debug.json and log deviations.
- Stop if nanobrag_torch import fails; record the error and mark the focus blocked.
- Keep parity selector assertions aligned with docs/spec-db-conformance.md:23-26 thresholds.
- Verify `pytest --collect-only` still finds the DB_AT_001 node before exiting the loop.

**If Blocked**
- Capture the failure log under plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T181603Z/implementation/, mark NANOBRAG-GOLDEN-001 `blocked` in docs/fix_plan.md with error signature + Metrics/Artifacts placeholders, append the block to galph_memory, and notify the supervisor before pivoting.

**Findings Applied (Mandatory)**
- CONFIG-001 — Maintains dxtbx→nanobrag mapping (pixel pitch, mask polarity) during fixture refresh.
- CONFORMANCE-001 — Manifest provenance + checksum validation keep DB_AT_001 thresholds meaningful.
- TESTING-003 — Active selector evidence (collect + pytest log) stays current after fixture updates.
- HKL-ORIENT-001 — Generator changes must preserve incident-vector negation fix for valid HKL coverage.
- PARITY-001 — Canonical tensors + artifacts enable deterministic first-divergence tracing when thresholds fail.
