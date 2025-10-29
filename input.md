**Summary**: Regenerate the canonical DB_AT_001 tensors, wire them into fixtures with manifest provenance, and confirm the parity harness exercises the bool-masked dataset.

**Mode**: Parity

**Focus**: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset

**Branch**: integration

**Mapped tests**: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001

**Artifacts**: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T110900Z/

**Do Now (hard validity contract)**
- Focus Item: NANOBRAG-GOLDEN-001 (A2, A3, B1, B2)
- Implement: scripts/generate_simple_cubic_golden.py::generate_simple_cubic_golden and tests/fixtures/parity_loader.py::load_golden_data — add bool-mask export + manifest emission + fixture loader updates so canonical tensors replace the fallback dataset end-to-end.
- Prep: PYTHONPATH=../nanoBragg/src:$PYTHONPATH KMP_DUPLICATE_LIB_OK=TRUE python scripts/generate_simple_cubic_golden.py --canonical-out plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T110900Z/golden_dataset --hkldebug plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T110900Z/torch_hkl_debug.json --emit-manifest --fixtures tests/fixtures/golden_data/simple_cubic (captures DiffBragg + torch tensors and refreshes manifest/metadata after code changes).
- Validate: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001
- Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T110900Z/

**Priorities & Rationale**
- Finding HKL-ORIENT-001 + docs/nanobrag_api.md:22-44 — Maintain the corrected incident-beam orientation while regenerating tensors so HKL coverage stays in-range in the canonical capture.
- Finding CONFIG-001 + docs/spec-db-core.md:20-41 — Fixture refresh must preserve `[panel, slow, fast]` ordering and bool mask polarity when bridging configs back into parity loader.
- Finding CONFORMANCE-001 + docs/spec-db-conformance.md:23-26 — DB_AT_001 acceptance hinges on canonical baselines with manifest provenance; without it the acceptance selector remains non-actionable.
- Finding TESTING-003 + docs/TESTING_GUIDE.md:63-88 — Active selector `KMP_DUPLICATE_LIB_OK=TRUE ... -k DB_AT_001` must continue to collect >0 tests with updated fixtures and fresh artifact logs.
- docs/forward_equivalence.md:21-53 & Finding PARITY-001 — Paired DiffBragg/torch metrics and first-divergence evidence must be regenerated whenever the dataset changes to keep parity debugging deterministic.

**How-To Map**
1. Edit scripts/generate_simple_cubic_golden.py::generate_simple_cubic_golden (and helper CLI glue) to emit bool-mask `.npy`, manifest JSON, checksum table, and optional fixture copy when `--emit-manifest/--fixtures` flags are supplied (use apply_patch).
2. Update tests/fixtures/parity_loader.py::load_golden_data to load new manifest schema, coerce loss masks to bool, and surface provenance strings for parity tests (apply_patch).
3. Narrow `.gitignore` so canonical fixture `.npy` files under tests/fixtures/golden_data/simple_cubic/ are tracked while other `.npy` artifacts remain ignored.
4. `mkdir -p plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T110900Z/golden_dataset` (ensure clean artifact staging for regenerated tensors and manifests).
5. `PYTHONPATH=../nanoBragg/src:$PYTHONPATH KMP_DUPLICATE_LIB_OK=TRUE python scripts/generate_simple_cubic_golden.py --canonical-out plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T110900Z/golden_dataset --hkldebug plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T110900Z/torch_hkl_debug.json --emit-manifest --fixtures tests/fixtures/golden_data/simple_cubic | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T110900Z/canonical_capture.log`
6. Snapshot generated manifest/metadata/metrics via `cp` or `python - <<'PY'` helpers into the artifact directory (sha256 summary, metrics.json, roi_metrics.csv) for ledger linking.
7. `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001 | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T110900Z/pytest_db_at_001.log`
8. Update docs/fix_plan.md Attempts History with new metrics/paths and log durable lessons in docs/findings.md if new pitfalls emerge.

**Pitfalls To Avoid**
- Do not regress mask dtype: persist bool (`np.bool_`) in fixtures and manifests or loader assertions will fail.
- Keep `[panel, slow, fast]` ordering intact when slicing torch stacks; avoid accidental transpose or squeeze.
- Ensure `.gitignore` exceptions stay scoped to simple_cubic fixtures so other captured `.npy` logs remain ignored.
- Preserve HKL metadata when saving manifest; missing bounds will break parity loader sanity checks.
- Run generator after code edits; stale captures from earlier loops will not include manifest changes.
- Stop immediately if nanobrag_torch import or CUDA init fails—log the error, mark the initiative blocked, and do not attempt environment changes.
- Record canonical_capture.log and pytest log under the new artifact directory for ledger compliance.
- Verify parity loader unit tests still reference bool masks; adjust assertions before running pytest to prevent false negatives.
- Avoid editing unrelated tests/docs in the same loop to keep scope under the work-in-progress cap.
- Keep sha256 calculations consistent (newline-terminated JSON) so manifest validation in tests passes.

**If Blocked**
- Capture the failure log (e.g., ImportError stack trace) into plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T110900Z/, mark NANOBRAG-GOLDEN-001 as `blocked` in docs/fix_plan.md with the error signature, and append the block to galph_memory.
- Defer to supervisor guidance and pivot to the highest-priority unblocked item only after documenting the block in docs/findings.md Attempts History with Metrics/Artifacts placeholders.

**Findings Applied (Mandatory)**
- HKL-ORIENT-001 — Generator changes must retain the corrected beam orientation so regenerated tensors populate the HKL grid.
- CONFIG-001 — Fixture copy + loader update will follow the documented dxtbx→nanobrag mapping, keeping mask polarity and geometry contracts intact.
- CONFORMANCE-001 — Canonical dataset + manifest refresh is required to keep DB_AT_001 acceptance meaningful.
- TESTING-003 — Plan includes fresh pytest collection evidence to maintain Active selector compliance.
- PARITY-001 — Regenerating parity artifacts ensures first-divergence traces remain deterministic with the new tensors.
