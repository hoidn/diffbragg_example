# NANOBRAG-GOLDEN-001 Loop Summary (2025-10-29T080253Z)

## Status: COMPLETE

All Do Now tasks from input.md (2025-10-29T080253Z) executed successfully:
- A1: Environment evidence captured
- A2+A3: Canonical DiffBragg + torch forward tensors captured (with 4 patches applied)
- D1: Metrics archived, DB_AT_001 collect-only logs refreshed

## Key Achievements

### 1. Environment Evidence (A1)
- Created 2025-10-29T080253Z report directory structure
- Captured Python 3.9.23, nanobrag_torch 0.1.0, simtbx.diffBragg paths
- Recorded simtbx_diffBragg_ext.so md5 checksum

### 2. Canonical Tensor Capture (A2+A3)
Successfully captured canonical DiffBragg and torch forward tensors after applying 4 critical patches:

**Patch 1 (MTZ-FLEX-001)**: MTZ conversion fix
- Added `from scitbx.array_family import flex`
- Convert Famps numpy array to `flex.double(Famps)` before `customized_copy`
- Root cause: cctbx MTZ writer requires flex types, not numpy arrays

**Patch 2 (TORCH-API-001)**: polarization_fraction removal
- Removed `polarization_fraction` parameter from BeamConfig instantiation
- Root cause: nanobrag_torch BeamConfig API doesn't have this attribute

**Patch 3 (TORCH-CUDA-001)**: numpy→CUDA tensor assignment
- Changed `grid[...] = amp` to `grid[...] = float(amp)`
- Root cause: Cannot assign numpy.float32 scalar directly to torch CUDA tensor

**Patch 4 (TORCH-JSON-001)**: JSON serialization for numpy types
- Changed `list(np.asarray(..., dtype=np.float32))` to `[float(x) for x in ...]`
- Root cause: JSON encoder cannot serialize numpy.float32 objects in lists

**Output Files:**
- `golden_dataset/legacy/bragg_diffbragg.npy` (24M)
- `golden_dataset/legacy/config_diffbragg.json`
- `golden_dataset/torch/bragg_torch.npy` (24M)
- `golden_dataset/torch/target_panel_0.npy` (24M)
- `golden_dataset/torch/loss_mask_panel_0.npy` (6M)
- `golden_dataset/torch/config_torch.json`

### 3. Metrics Archive (D1)
- Generated `golden_dataset/metrics.json` with partial metrics:
  - loss_mask_coverage: 0.21%
  - n_panels: 1
  - correlation/RMSE: placeholders (require parity harness execution)
- Created `metrics/metrics_summary.md`

### 4. Test Evidence (D1)
Refreshed DB_AT_001 collect-only logs:
- Forward equivalence: 1 test collected (0.98s)
- Parity harness: 14 tests collected (0.23s)
- Both selectors Active per TESTING-003 (>0 tests)

## Metrics Summary

- **Patches applied**: 4/4 (MTZ flex, polarization API, CUDA assignment, JSON serialization)
- **DiffBragg baseline**: 1/1 captured (24M bragg_diffbragg.npy)
- **Torch forward capture**: 1/1 completed (24M + 24M target + 6M mask)
- **Tests collected**: 15 total (1 forward + 14 parity)
- **Import failures**: 0
- **Documentation**: All patches documented in capture_forward_patches.patch

## Artifacts

All artifacts stored under `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T080253Z/`:

```
├── environment_status.md
├── capture_forward.py (patched)
├── capture_forward_patches.patch
├── loop_progress.md
├── summary.md (this file)
├── golden_dataset/
│   ├── legacy/
│   │   ├── bragg_diffbragg.npy (24M)
│   │   └── config_diffbragg.json
│   ├── torch/
│   │   ├── bragg_torch.npy (24M)
│   │   ├── target_panel_0.npy (24M)
│   │   ├── loss_mask_panel_0.npy (6M)
│   │   └── config_torch.json
│   ├── metrics.json
│   └── logs/
│       └── canonical_capture.log
├── metrics/
│   └── metrics_summary.md
├── collect_db_at_001_forward.log
└── collect_db_at_001_parity.log
```

## Findings Documented

Four new candidate findings for `docs/findings.md`:

1. **MTZ-FLEX-001**: miller_array.customized_copy requires flex.double data arrays
2. **TORCH-API-001**: BeamConfig does not have polarization_fraction attribute
3. **TORCH-CUDA-001**: Cannot assign numpy scalars directly to CUDA tensors
4. **TORCH-JSON-001**: JSON encoder requires Python floats, not numpy types

## Next Actions (For Supervisor)

All A1-A2-A3-D1 tasks complete. Supervisor to decide:
1. Add new findings (MTZ-FLEX-001, TORCH-API-001, TORCH-CUDA-001, TORCH-JSON-001) to `docs/findings.md`
2. Proceed with Phase B: Manifest & verification (implementation.md)
3. Proceed with Phase C: Parity harness integration (implementation.md)

## Environment Freeze Compliance

All patches applied under Environment Freeze exception policy:
- Patches target locally available capture script (not external packages)
- All changes documented with rationale and root cause
- Patch files saved for reproducibility
- No external package installs or upgrades performed
