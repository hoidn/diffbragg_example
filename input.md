Summary: Fix the canonical capture JSON serialization failure and land the DB_AT_001 canonical dataset plus parity harness updates for NANOBRAG-GOLDEN-001.
Mode: Parity
Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
Branch: integration
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001; KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001
Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T082521Z/{capture_forward.py,capture_forward_patches.patch,golden_dataset/,metrics/,collect_db_at_001_forward.log,collect_db_at_001_parity.log}
Do Now:
  1. NANOBRAG-GOLDEN-001.A2 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Create the 2025-10-29T082521Z report scaffold, correct the 2025-10-29T080253Z attempts log to note the JSON TypeError, and patch capture_forward.py with a recursive numpy/torch→Python conversion helper; tests: none — evidence-only.
  2. NANOBRAG-GOLDEN-001.A2+A3 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Run the patched capture_forward.py to regenerate DiffBragg and torch tensors, confirming bragg_diffbragg.npy, bragg_torch.npy, target_panel_0.npy, loss_mask_panel_0.npy, config JSON, and metrics.json land under the new report with canonical_capture.log archived; tests: none — evidence-only.
  3. NANOBRAG-GOLDEN-001.B1+B2+C1 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Replace the fallback fixture assets with the canonical tensors (copy `.npy`/JSON into tests/fixtures/golden_data/simple_cubic/, refresh manifest/metadata, update parity loader/tests to drop synthetic noise and consume canonical outputs) and verify with KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001; KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001.
  4. NANOBRAG-GOLDEN-001.D2 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Add MTZ-FLEX-001, TORCH-API-001, TORCH-CUDA-001, and TORCH-JSON-001 findings to docs/findings.md with supporting citations, and cross-link updated artifact paths in docs/TESTING_GUIDE.md plus docs/development/TEST_SUITE_INDEX.md; tests: none — evidence-only.
  Implement: tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke (validate with KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001)
Priorities & Rationale:
- docs/spec-db-core.md:32 — Canonical tensors must maintain `[panel, slow, fast]` ordering, so capture outputs and fixtures need strict shape validation.
- docs/spec-db-conformance.md:23 — DB_AT_001 acceptance thresholds (correlation ≥0.2, localization ≥90%) drive the parity harness update once canonical tensors are in place.
- docs/forward_equivalence.md:21 — DiffBragg baseline generation precedes torch capture, justifying the rerun of capture_forward.py.
- docs/config_crosswalk.md:22 — Detector/beam/crystal mappings guide metadata fields in manifest.json and config_torch.json.
- docs/TESTING_GUIDE.md:87 — Active DB_AT_001 selectors require fresh collect-only logs referencing the new canonical dataset artifacts.
How-To Map:
- `report_root=plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T082521Z` and `mkdir -p "$report_root"/{golden_dataset/{legacy,torch,logs},metrics}` to stage the new evidence tree.
- `cp plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T080253Z/capture_forward.py "$report_root"/` then edit to add a `to_native()` helper that converts numpy scalars/arrays and torch tensors to Python primitives before JSON dumps; refresh `$report_root/capture_forward_patches.patch` via diff --full-index.
- Update `docs/fix_plan.md` Attempts History entry for 2025-10-29T080253Z to record the JSON serialization crash and note rerun scheduled for 2025-10-29T082521Z.
- `CUDA_VISIBLE_DEVICES=0 KMP_DUPLICATE_LIB_OK=TRUE libtbx.python "$report_root"/capture_forward.py |& tee "$report_root"/golden_dataset/logs/canonical_capture.log` and confirm the command exits 0.
- `ls -lh "$report_root"/golden_dataset/{legacy,torch}` and `sha256sum "$report_root"/golden_dataset/{legacy/bragg_diffbragg.npy,torch/bragg_torch.npy,torch/target_panel_0.npy,torch/loss_mask_panel_0.npy}` to capture provenance.
- `python - <<'PY'` helper to rewrite `tests/fixtures/golden_data/simple_cubic/manifest.json` and `metadata.json` with new filenames, checksums, and provenance keys based on `$report_root/golden_dataset` outputs.
- Copy canonical tensors into fixtures: `cp "$report_root"/golden_dataset/legacy/bragg_diffbragg.npy tests/fixtures/golden_data/simple_cubic/bragg_diffbragg.npy` and analogous commands for torch/target/loss_mask, updating `.gitignore` exemptions if needed.
- Adjust `tests/fixtures/parity_loader.py` and `tests/dbex/test_db_at_001_parity.py` to point at the new filenames/config fields, removing synthetic noise injections.
- Run parity selectors: `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001 |& tee "$report_root"/collect_db_at_001_parity.log` and forward equivalence selector similarly for `collect_db_at_001_forward.log`.
- Sync doc tables with new artifact timestamps: edit `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` to reference the 2025-10-29T082521Z logs; append new findings in `docs/findings.md`.
Pitfalls To Avoid:
- Do not trust the 2025-10-29T080253Z summary; re-run capture because JSON serialization aborted and left tensors missing.
- Ensure the numpy→Python converter handles nested dict/list structures so no float32/int64 remnants reach json.dump.
- Keep canonical `.npy` files synchronized between plan artifacts and fixtures; avoid leaving stale fallback filenames in manifest.json.
- Preserve `[panel, slow, fast]` orientation when saving torch tensors; stacking in the wrong axis will break parity metrics.
- Remove synthetic noise/xfail scaffolding only after verifying canonical metrics exceed thresholds; otherwise retain defensive xfail messaging.
- When copying large tensors, avoid accidental CRLF conversions or truncation; use `cp` with `--preserve=mode` if needed.
- Track sha256 checksums before updating manifest to prevent mismatch assertions in load_golden_data.
- Record collect-only logs under the new timestamp before editing documentation to prevent doc/test drift.
- Do not modify the frozen conda environment; treat module import failures as blockers per Environment Freeze policy.
- Retain capture_forward_patches.patch alongside the script to satisfy Environment Freeze exception documentation.
Environment: Frozen simtbx environment; no package installs or rebuilds allowed. Missing imports or CUDA errors must be logged as blockers rather than patched via dependency changes.
If Blocked: Archive failing logs under `$report_root` (e.g., canonical_capture.log, pytest outputs), append a blocked attempt to docs/fix_plan.md with error signature, and set next_action to `switch_focus` in galph_memory until the blocker is cleared.
Findings Applied (Mandatory):
- CONFIG-001 — Bridges dxtbx geometry to torch configs; informs metadata fields and mask polarity when copying canonical tensors.
- PARITY-001 — Requires deterministic ROI ordering and artifact emission for parity debugging during manifest/test updates.
- DIFFBRAGG-001 — Confirms repaired simtbx build remains valid before trusting DiffBragg outputs from capture_forward.py.
- TESTING-003 — Mandates updated collect-only evidence and documentation sync for DB_AT_001 selectors once fixtures change.
- MASKING-001 — Loss mask coverage expectations (~0.21%) guide parity sanity checks after swapping datasets.
