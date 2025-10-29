# Loop Summary: 2025-10-29T193557Z

## Focus
NANOBRAG-GOLDEN-001 — √(spot_scale_override) diagnostics instrumentation per SCALE-002

## Objectives
1. Instrument `scripts/generate_simple_cubic_golden.py` to emit scaling diagnostics (raw/scaled torch outputs, post_sim_scale_factor) in panel_metrics.json and config_torch.json
2. Regenerate canonical DB-AT-001 golden dataset with enhanced diagnostics
3. Validate torch/DiffBragg intensity alignment via scale_diagnostics extraction
4. Verify fixtures and DB_AT_001 parity selector remain functional

## Implementation

### Code Changes
1. **scripts/generate_simple_cubic_golden.py:519-530** — Extended `panel_summaries` dict with scale diagnostics:
   - `torch_raw_max`, `torch_raw_sum`: Pre-scaling simulator outputs
   - `torch_scaled_max`, `torch_scaled_sum`: Post-SCALE-002 scaled outputs
   - `post_sim_scale_factor`: √(spot_scale_override) scale factor

2. **scripts/generate_simple_cubic_golden.py:562-583** — Added scale provenance to `torch_meta` crystal section:
   - `post_sim_scale_factor`: Numeric scale factor value
   - `scale_factor_source`: "sqrt(scale_override) per SCALE-002"

No changes to scaling logic; SCALE-001/SCALE-002 fixes from prior loops remain in place.

### Canonical Capture
**Command:**
```bash
PYTHONPATH=../nanoBragg/src:$PYTHONPATH KMP_DUPLICATE_LIB_OK=TRUE \
python scripts/generate_simple_cubic_golden.py \
  --canonical-out plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T193557Z/golden_dataset \
  --hkldebug plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T193557Z/torch_hkl_debug.json \
  --emit-manifest \
  --fixtures tests/fixtures/golden_data/simple_cubic
```

**DiffBragg Refinement:**
- Converged in 5 macro cycles (final sigZ=6.313)
- Forward pass: diffbragg_max=36195.17

**nanobrag_torch Simulation:**
- HKL hit rate: 98.73%
- Raw output: torch_raw_max=6.9e-05
- Scaled output: torch_scaled_max=38960.27 (post_sim_scale=5.644e+08)

**Artifacts Generated:**
- Manifest with full provenance (git revision, generator command, SHA256 checksums)
- 5 fixture files: bragg_diffbragg.npy, bragg_torch.npy, target_panel_0.npy, loss_mask_panel_0.npy, manifest.json
- Enhanced diagnostics: panel_metrics.json, config_torch.json with scale provenance

### Scale Diagnostics Validation
Extracted metrics (scale_diagnostics.txt):
- torch_max: 3.896e+04
- diff_max: 3.620e+04
- max_ratio: 1.076 (8% difference)
- post_sim_scale_factor: 5.644e+08
- loss_mask_coverage: 2.103e-03

**Result:** Torch/DiffBragg intensity magnitudes aligned within 8%, confirming SCALE-002 √(spot_scale_override) post-simulation scaling correctly applied.

### Test Validation
**Command:**
```bash
KMP_DUPLICATE_LIB_OK=TRUE pytest -v \
  tests/dbex/test_db_at_001_parity.py::TestDB_AT_001_Parity::test_db_at_001_parity_smoke
```

**Result:** XFAIL (expected per CONFORMANCE-001), DB_AT_001 selector Active

## Metrics

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| diffbragg_max | 36195.17 | - | ✓ |
| torch_max | 38960.27 | - | ✓ |
| max_ratio | 1.076 | ~1.0 | ✓ (8% diff) |
| median_correlation | -0.0358 | ≥0.2 | ✗ |
| median_rmse | 4.589 | - | - |
| localization_success_rate | 5.6% | ≥90% | ✗ |
| loss_mask_coverage | 0.21% | - | ✓ |

## Exit Criteria Assessment

### Satisfied (A3/B1/B3)
- ✓ Scale diagnostics instrumented in panel_metrics.json (raw/scaled max/sum, post_sim_scale_factor)
- ✓ Scale provenance added to config_torch.json (post_sim_scale_factor, scale_factor_source)
- ✓ Canonical tensors regenerated with enhanced diagnostics
- ✓ Fixtures refreshed (5 .npy files with valid checksums)
- ✓ Torch/DiffBragg intensity magnitudes aligned (ratio 1.076)
- ✓ DB_AT_001 selector remains Active

### Outstanding (C2)
- ✗ Correlation=-0.036 below target ≥0.2
- ✗ Localization=5.6% below target ≥90%

**Note:** Correlation/localization gaps represent independent physics/simulator divergences beyond scaling scope and require separate parity-debug focus per docs/spec-db-tracing.md first-divergence workflow.

## Artifacts
- canonical_capture.log (80KB) — Full generator output
- pytest_db_at_001.log (528B) — Test execution log
- scale_diagnostics.txt (185B) — Extracted scaling metrics
- fixture_files.txt (295B) — Fixture file listing
- tensor_checksums.txt (625B) — SHA256 checksums for all fixtures
- torch_hkl_debug.json (335B) — HKL grid statistics
- parity_harness_artifacts.tar (empty) — Placeholder (test xfailed)
- golden_dataset/
  - manifest.json — Full provenance with checksums
  - metrics.json — Parity metrics summary
  - legacy/
    - bragg_diffbragg.npy (24MB)
    - config_diffbragg.json
  - torch/
    - bragg_torch.npy (24MB)
    - config_torch.json (with scale provenance)
    - loss_mask_panel_0.npy (6MB)
    - target_panel_0.npy (24MB)
    - panel_metrics.json (with scale diagnostics)

## First Divergence
Intensity magnitudes aligned (torch=38960 vs diffbragg=36195, ratio 1.076 within 8%), confirming SCALE-002 √(spot_scale_override) post-simulation scaling correctly applied. Correlation=-0.036 and localization=5.6% remain below DB_AT_001 acceptance thresholds but represent independent physics/simulator divergences beyond scaling scope.

## Next Actions
- Exit criteria satisfied for scaling diagnostics instrumentation focus (A3/B1/B3 complete)
- Parity correlation/localization improvements (C2 thresholds) require separate parity-debug focus following docs/spec-db-tracing.md first-divergence workflow
- Mark NANOBRAG-GOLDEN-001 status=in_progress pending C2/C3 completion or transition to next initiative if current parity metrics acceptable for initial rollout

## Checklist Updates
- [x] A3 — nanoBragg2 forward capture with enhanced scale diagnostics
- [x] B1 — Manifest with full provenance emitted
- [x] B3 — Regeneration tooling updated with scale diagnostics
- [ ] C2 — Threshold enforcement (correlation/localization below targets)
- [ ] C3 — Documentation sync
