Summary: Replace the fallback simple_cubic tensors with a canonical nanoBragg2 DB-AT-001 golden dataset and prep the parity harness to enforce real thresholds.
Mode: Parity
Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
Branch: integration
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001
Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T023547Z/{notes.md,golden_dataset/,collect_db_at_001.log}
Do Now:
  1. NANOBRAG-GOLDEN-001 A1 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Validate nanobrag_torch availability and confirm refGeom inputs/structure-factor assets exist; capture import checks under the new reports directory. tests: none — environment validation only
  2. NANOBRAG-GOLDEN-001 A2 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Run the DiffBragg forward-only path to export `bragg_diffbragg.npy` plus config snapshots into `golden_dataset/legacy/`. tests: none — capture via CLI command and log output
  3. NANOBRAG-GOLDEN-001 A3+B1 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Extend `scripts/generate_simple_cubic_golden.py` to invoke nanobrag_torch, regenerate canonical tensors/manifest under `golden_dataset/torch/`, and update checksum metadata. tests: none — generator execution produces artifacts
  4. NANOBRAG-GOLDEN-001 C1+C2 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Swap DB_AT_001 parity harness to the canonical dataset, remove synthetic noise, and enforce correlation/localization thresholds while recording metrics + artifacts. tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001
  5. NANOBRAG-GOLDEN-001 C3 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Update docs/TESTING_GUIDE.md §2, docs/development/TEST_SUITE_INDEX.md, and docs/index.md with new artifact paths; capture collect-only evidence for the selector and stage ledger/doc updates. tests: KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001
Priorities & Rationale:
- docs/spec-db-core.md:20-41 — Canonical tensors must honor `[panel, slow, fast]` ordering and detector geometry contracts during regeneration.
- docs/spec-db-conformance.md:23-26 — DB_AT_001 thresholds drive the parity harness updates once real data replaces the fallback tensors.
- docs/forward_equivalence.md:21-52 — Forward-only capture requirements define the DiffBragg/torch baseline artifacts and diagnostics to persist.
- plans/nanobrag_integration_plan.md:23-88 — Bridge responsibilities and simulator invocation guidance scope the generator rewrite and config exports.
- docs/TESTING_GUIDE.md:74-85 & docs/development/TEST_SUITE_INDEX.md:13-14 — Selector documentation must stay synchronized with the new artifact paths and evidence.
How-To Map:
- Validate environment: python -c "import nanobrag_torch, torch; print('nanobrag_torch ok', torch.__version__)" | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T023547Z/golden_dataset/env_check.log
- Confirm inputs present: ls refGeom.expt refGeom.refl scaled.mtz 747_mask.pkl | tee -a plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T023547Z/golden_dataset/env_check.log
- Capture DiffBragg baseline: python -m dbex.refine_one --backend diffbragg -e refGeom.expt -r refGeom.refl -i 0 -o plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T023547Z/golden_dataset/legacy/dbex_diffbragg.h5 -m 747_mask.pkl -z scaled.mtz | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T023547Z/golden_dataset/legacy/diffbragg_forward.log
- Generate canonical tensors (after script update): python scripts/generate_simple_cubic_golden.py --output plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T023547Z/golden_dataset/torch/ | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T023547Z/golden_dataset/torch/generator.log
- Run parity harness: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001 | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T023547Z/pytest_db_at_001.log
- Collect-only evidence: KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001 | tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T023547Z/collect_db_at_001.log
Pitfalls To Avoid:
- Forgetting KMP_DUPLICATE_LIB_OK=TRUE before invoking pytest or nanobrag_torch-backed scripts.
- Overwriting fallback tensors without archiving canonical outputs under the initiative reports directory.
- Neglecting `[panel, slow, fast]` ordering or mask alignment when stitching per-panel tensors.
- Leaving manifest checksums stale after regenerating `.npy` files.
- Running torch simulator without validating structure-factor provenance (DiffBragg vs HKL grid).
- Allowing large intermediate artifacts outside `plans/active/NANOBRAG-GOLDEN-001/reports/` (keep repo clean).
- Removing parity xfail guards without ensuring thresholds actually pass or documenting a residual gap.
- Failing to update docs/prompt map with the new canonical dataset reference.
If Blocked:
- If nanobrag_torch import fails or simulator binaries are unavailable, capture the traceback in `golden_dataset/env_check.log`, mark NANOBRAG-GOLDEN-001 blocked in docs/fix_plan.md Attempts History with the failure reason, log the block in galph_memory, and coordinate on acquiring the dependency before proceeding.
Findings Applied (Mandatory):
- CONFORMANCE-001 — Keeps DB_AT_001 selector thresholds and env flag aligned when swapping to canonical data.
- CONFIG-001 — Ensures bridge-generated configs remain faithful during DiffBragg/nanobrag capture.
- MASKING-001 — Interprets sparse loss mask coverage correctly when evaluating metrics.
- PARITY-001 — Preserves deterministic first-divergence diagnostics alongside new canonical tensors.
- TESTING-003 — Drives collect-only evidence and doc sync so selector status remains authoritative.
Doc Sync Plan (Mandatory):
- DB_AT_001 selector (`tests/dbex/test_db_at_001_parity.py -k DB_AT_001`): run KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001, store the log at plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T023547Z/collect_db_at_001.log, then update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md with the new artifact path.
