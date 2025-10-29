Summary: Chart the canonical DB_AT_001 capture recovery so the torch baseline produces non-zero intensities and the parity harness can switch off the fallback tensors.
Mode: Parity
Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
Branch: integration
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001
Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T084244Z/{canonical_capture.log,torch_panel_metrics.json,pytest_db_at_001.log}
Do Now:
  - NANOBRAG-GOLDEN-001:
    - Implement: scripts/generate_simple_cubic_golden.py::generate_simple_cubic_golden (A3/B1/B2/C1) — replace the fallback generator with the canonical DiffBragg+nanobrag capture pipeline, add HKL sanity instrumentation, and emit torch/diffbragg tensors plus provenance under the new report root.
    - Validate: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001
    - Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T084244Z/{canonical_capture.log,torch_panel_metrics.json,pytest_db_at_001.log}
Priorities & Rationale:
- docs/spec-db-core.md:20-54 — Canonical capture must honor `[panel, slow, fast]` tensors, square-pixel guards, and mask polarity when writing fixtures.
- docs/spec-db-conformance.md:23-26 — DB_AT_001 thresholds (correlation ≥0.2, localization ≥0.9) dictate parity assertions once the torch baseline produces real peaks.
- docs/nanobrag_api.md:22-44 — Detector/beam/crystal config rules shape the torch simulator inputs we emit from the redesigned generator.
- docs/forward_equivalence.md:46-52 — Capture workflow needs to log metrics/overlays that parity and forward-equivalence selectors consume.
- docs/config_crosswalk.md:23-72 — Mapping dxtbx geometry to `TorchDetectorConfig`/`TorchCrystalConfig` ensures HKL indices land in-range so torch output is non-zero.
How-To Map:
- `report_root=plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T084244Z` ; `mkdir -p "$report_root"/golden_dataset/{legacy,torch,logs}` to stage capture artifacts.
- Add CLI flags to `scripts/generate_simple_cubic_golden.py` (`--canonical-out`, `--hkldebug`) then run `CUDA_VISIBLE_DEVICES=0 KMP_DUPLICATE_LIB_OK=TRUE python scripts/generate_simple_cubic_golden.py --canonical-out "$report_root"/golden_dataset --hkldebug "$report_root"/torch_hkl_debug.json |& tee "$report_root"/canonical_capture.log`.
- Within the script, log HKL in-range ratios and peak stats to `$report_root/torch_panel_metrics.json`; inspect with `jq '.torch_peaks' "$report_root"/torch_panel_metrics.json` to confirm non-zero maxima.
- Copy emitted tensors into fixtures: `cp "$report_root"/golden_dataset/legacy/bragg_diffbragg.npy tests/fixtures/golden_data/simple_cubic/bragg_diffbragg.npy` and analogous commands for torch/target/loss_mask/config JSON.
- Update `tests/fixtures/parity_loader.py` to load `bragg_diffbragg.npy` / `bragg_torch.npy` dual baselines and adjust checksum validation; refactor `tests/dbex/test_db_at_001_parity.py` to compare torch vs diffbragg without synthetic noise.
- Recompute manifest/metadata via `python scripts/generate_simple_cubic_golden.py --emit-manifest "$report_root"/golden_dataset --fixtures tests/fixtures/golden_data/simple_cubic` so SHA256 entries match copied tensors.
- Run parity selector: `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001 |& tee "$report_root"/pytest_db_at_001.log` and capture metrics for docs.
- If HKL debug shows out-of-range >5%, adjust crystal orientation (e.g., inject DiffBragg UMAT into `TorchCrystalConfig.misset_deg`) and rerun until peaks appear.
Pitfalls To Avoid:
- Do not leave fallback filenames in manifest.json; checksum validation will fail immediately.
- Keep `mask_array` dtype float32 with values {0,1}; boolean arrays will break serialization in the torch config JSON.
- Ensure HKL metadata reflects refined min/max; off-by-one errors zero out structure factors.
- Preserve `[panel, slow, fast]` ordering when stacking torch panels before saving `.npy`.
- Avoid running capture without `CUDA_VISIBLE_DEVICES=0`; the existing torch build expects GPU and silently degrades on CPU.
- Capture both DiffBragg and torch metrics in the same report; missing diffbragg baseline blocks parity comparisons.
- Do not downgrade Environment Freeze by editing `nanobrag_torch`; instrumentation belongs in our generator.
- Verify collect-only logs after manifest changes to satisfy TESTING-003 before touching docs.
- Keep canonical tensors out of git LFS unless policy updated; use plan artifacts plus fixture copies only.
If Blocked:
- If torch output remains zero after orientation fixes, archive `torch_hkl_debug.json` + `canonical_capture.log`, append a blocked attempt to docs/fix_plan.md with the error signature, set focus status to `blocked`, and request guidance before further retries.
- If pytest DB_AT_001 still xfails due to low correlation, retain fallback fixtures, log metrics, and pivot to documenting the blocker in docs/findings.md plus galph_memory.
Findings Applied (Mandatory):
- CONFIG-001 — Guides detector/beam/crystal mapping so HKL indices stay in-range when building Torch configs.
- PARITY-001 — Requires deterministic ROI ordering and artifact emission for parity harness updates.
- DIFFBRAGG-001 — Confirms the rebuilt DiffBragg extension is the baseline we rely on before copying tensors.
- MASKING-001 — Loss mask coverage expectations (~0.21%) inform sanity checks on captured tensors.
- TESTING-003 — Forces collect-only verification and documentation sync after selector updates.
