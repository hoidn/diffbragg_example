# NANOBRAG-GOLDEN-001 Loop Summary (2025-10-29T082521Z)

## Status: PARTIAL

Canonical tensor capture completed with JSON serialization fix, but torch simulator producing all-zero output requires debugging before parity test integration can proceed.

## Tasks Completed

### A2: Patch capture_forward.py (JSON serialization fix)
- **Status**: COMPLETE
- Added recursive `to_native()` helper to convert numpy/torch types to Python primitives
- Wrapped all 4 `json.dump()` calls to prevent `TypeError: Object of type float32 is not JSON serializable`
- Documented patches in `capture_forward_patches.patch`

### A2+A3: Run canonical tensor capture
- **Status**: COMPLETE (with blocker discovered)
- DiffBragg refinement converged successfully (5 macro cycles)
- All JSON files written without serialization errors
- Generated canonical tensors:
  - `bragg_diffbragg.npy` (24M, SHA256: 06fd77...)
  - `bragg_torch.npy` (24M, SHA256: ca9476...)
  - `target_panel_0.npy` (24M, SHA256: 3ae4d0...)
  - `loss_mask_panel_0.npy` (6M, SHA256: 7fa321...)
- Config JSON files: `config_diffbragg.json`, `config_torch.json`, `panel_metrics.json`

### B1: Update fixture manifest
- **Status**: PARTIAL
- Copied all canonical tensors to `tests/fixtures/golden_data/simple_cubic/`
- Updated `manifest.json`:
  - Changed `dataset_name` from `simple_cubic_fallback` to `DB_AT_001_canonical`
  - Added `bragg_diffbragg` and `bragg_torch` entries with checksums/shapes
  - Updated `loss_mask` dtype to `uint8`
  - Bumped version from `1.0.0` to `1.1.0`

## Critical Blocker Identified

**Torch simulator producing all-zero output**

- `metrics.json` shows:
  - `torch_max: 0.0`
  - `median_correlation: NaN`
  - `localization_success_rate: 0.0`
- DiffBragg baseline has non-zero intensities (`diffbragg_max: 36195.17`)
- nanobrag_torch forward pass did not generate Bragg peaks despite successful config/structure-factor setup

**Root cause TBD**: Possible issues include:
- Config error (beam, detector, crystal parameters)
- Scale parameter missing/incorrect
- Flux/beam intensity mismatch
- Structure-factor grid not properly loaded
- nanobrag_torch API bug or compatibility issue

## Tasks Blocked

### B2-C3: Parity test integration
- **Status**: BLOCKED
- Parity loader (`tests/fixtures/parity_loader.py:224`) expects single `bragg_panel_{panel_id}.npy`
- Manifest now references dual baselines (`bragg_diffbragg` + `bragg_torch`)
- Test (`tests/dbex/test_db_at_001_parity.py:708`) needs refactor to:
  1. Load both `bragg_diffbragg` and `bragg_torch` from manifest
  2. Compare torch vs diffbragg instead of bragg vs target
  3. Handle [panel, slow, fast] shape (1, 2527, 2463) vs (2527, 2463)

### D1-D2: Testing and documentation sync
- **Status**: BLOCKED
- Cannot run parity tests until torch zero-output issue resolved
- Documentation sync depends on test results

## Metrics

- **Patches Applied**: 1 (TORCH-JSON-001 recursive to_native() helper)
- **JSON Dumps Wrapped**: 4/4
- **Capture Runs**: 1/1 succeeded (exit 0)
- **Canonical Tensors Written**: 4/4 (bragg_diffbragg, bragg_torch, target, loss_mask)
- **Manifest Updated**: 1/1
- **Critical Blockers**: 1 (torch zero-output)

## Artifacts

All artifacts stored under `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T082521Z/`:

- `capture_forward.py` — Patched capture script with to_native() helper
- `capture_forward_patches.patch` — Diff showing JSON serialization fix
- `golden_dataset/legacy/`:
  - `bragg_diffbragg.npy` (24M)
  - `config_diffbragg.json`
- `golden_dataset/torch/`:
  - `bragg_torch.npy` (24M, **all zeros**)
  - `target_panel_0.npy` (24M)
  - `loss_mask_panel_0.npy` (6M)
  - `config_torch.json`
  - `panel_metrics.json`
- `golden_dataset/logs/canonical_capture.log` — Full capture run log
- `golden_dataset/metrics.json` — Parity metrics showing torch zero-output issue

## Next Actions

1. **Debug torch zero-output** (priority):
   - Inspect `config_torch.json` for parameter errors
   - Verify structure-factor grid `hkl_data` is non-zero
   - Check beam flux, detector distance, oversample params
   - Review nanobrag_torch API for scale/intensity requirements
   - Consider adding debug prints to capture script to inspect simulator state

2. **Refactor parity loader and tests**:
   - Update `load_golden_data()` to load both bragg_diffbragg and bragg_torch
   - Modify `test_db_at_001_parity_smoke()` to compare torch vs diffbragg
   - Handle shape differences ([panel, slow, fast] vs [slow, fast])

3. **Document findings**:
   - Add TORCH-JSON-001 to `docs/findings.md` with to_native() pattern
   - Note torch zero-output issue (tentative ID: NANOBRAG-ZERO-001)

4. **Rerun parity tests** once blocker resolved

## Findings Applied

- **CONFIG-001**: Detector/beam/crystal config mapping guides metadata fields
- **PARITY-001**: Deterministic ROI ordering and artifact emission for debugging
- **DIFFBRAGG-001**: Confirmed patched simtbx build remains valid
- **TESTING-003**: Updated manifest requires collect-only evidence refresh
- **MASKING-001**: Loss mask coverage (~0.21%) validates as expected

## Environment State

- **Python**: 3.9.23
- **torch**: 2.4.1+cu121
- **CUDA**: Available (GeForce RTX 3090)
- **simtbx**: Patched (diffBraggCUDA.cu:708 fix from 2025-10-29T073200Z)
- **nanobrag_torch**: 0.1.0
- **Environment Freeze**: Compliant (no package installs/upgrades)

## Time Spent

- Patch development: ~5 minutes
- Capture run: ~2 minutes
- Manifest update: ~3 minutes
- Documentation: ~5 minutes
- **Total**: ~15 minutes
