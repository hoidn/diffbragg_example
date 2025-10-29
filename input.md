Summary: Restore the canonical DB_AT_001 capture so nanobrag_torch outputs non-zero panels by propagating the DiffBragg scale and verifying parity evidence lands in the current report root.
Mode: Parity
Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
Branch: integration
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001
Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T091339Z/{planning_notes.md,canonical_capture.log,torch_panel_metrics.json,pytest_db_at_001.log}
Do Now:
  - NANOBRAG-GOLDEN-001:
    - Implement: scripts/generate_simple_cubic_golden.py::generate_simple_cubic_golden (A3) — log raw torch intensities, inject the DiffBragg global scale into the torch capture path, and ensure `.npy` tensors land in the 2025-10-29T091339Z/golden_dataset/ tree before copying to fixtures.
    - Validate: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001
    - Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T091339Z/{canonical_capture.log,torch_panel_metrics.json,pytest_db_at_001.log}
Priorities & Rationale:
- docs/spec-db-core.md:20 — Canonical tensors must retain `[panel, slow, fast]` ordering and trusted mask polarity when we rewrite the generator.
- docs/spec-db-conformance.md:23 — DB_AT_001 parity thresholds (corr ≥0.2, localization ≥0.9) require a physically scaled torch baseline before we switch fixtures.
- docs/config_crosswalk.md:70 — Torch lacks `no_Nabc_scale`, so DiffBragg’s global scale has to be propagated during capture to avoid zero intensities.
- docs/forward_equivalence.md:46 — Re-running capture must emit metrics that satisfy forward-equivalence smoke expectations before parity passes.
- docs/TESTING_GUIDE.md:86 — DB_AT_001 selector remains Active; successful collect + run evidence is mandatory after regenerating tensors.
How-To Map:
- `report_root=plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T091339Z`; ensure directory exists for new artifacts.
- `CUDA_VISIBLE_DEVICES=0 KMP_DUPLICATE_LIB_OK=TRUE python scripts/generate_simple_cubic_golden.py --canonical-out "$report_root"/golden_dataset --hkldebug "$report_root"/torch_hkl_debug.json |& tee "$report_root"/canonical_capture.log`
- Inspect raw simulator stats with `jq '.[] | {panel_id, torch_max, torch_sum}' "$report_root"/golden_dataset/torch/panel_metrics.json` to confirm non-zero panels.
- Copy regenerated tensors into fixtures once non-zero: `cp "$report_root"/golden_dataset/torch/bragg_torch.npy tests/fixtures/golden_data/simple_cubic/bragg_torch.npy` (repeat for diffbragg, target, loss_mask) and refresh manifest checksums.
- Run parity validation: `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001 |& tee "$report_root"/pytest_db_at_001.log`
Pitfalls To Avoid:
- Do not double-apply the global scale; multiply torch tensors exactly once before persistence.
- Keep mask tensors float32 {0,1} to avoid boolean serialization issues in torch configs.
- Ensure HKL metadata matches the refined bounds; off-by-one indices will zero panels again.
- Don’t overwrite the fallback manifest until new SHA256 values are captured and logged.
- Avoid running capture on CPU—the current nanobrag_torch build expects CUDA and may silently return zeros otherwise.
- Preserve DiffBragg baseline copies when re-running; parity still compares against the legacy tensor.
- Keep plan artifacts under the 2025-10-29T091339Z root so ledger references stay coherent.
If Blocked:
- If torch output stays zero after scaling, archive the new `canonical_capture.log`, snapshot raw tensor stats, mark focus `blocked` in docs/fix_plan.md with the error signature, and escalate via galph_memory plus Findings entry.
- If pytest selector fails due to threshold gaps, preserve metrics, keep fallback fixtures intact, and log the regression before pivoting.
Findings Applied (Mandatory):
- CONFIG-001 — Geometry/config mapping constraints steer ROI/mask validation during capture.
- DIFFBRAGG-001 — Confirms the DiffBragg baseline remains trustworthy before scaling torch outputs.
- PARITY-001 — Requires deterministic ROI metrics and artifact emission when regenerating tensors.
- MASKING-001 — Loss mask coverage expectations (~0.21%) inform sanity checks on regenerated data.
- TESTING-003 — Forces collect/run evidence and documentation sync for the DB_AT_001 selector after fixture updates.
