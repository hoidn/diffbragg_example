# PERF-WARM-SIM-001 Loop 2025-12-01T214200Z Summary

## Turn Summary
Implemented REFINE-016 trusted-mask gating in Stage C by threading `stage_a_ctx.trusted_masks_t` into both ROI and panel-mode loss computation paths, mirroring Stage A's mask intersection logic (stage_a_impl.py:1348-1350, 1550-1552).
Full-detector test still failed REFINE-007 chi² gate (+0.067% regression, identical to all prior loops), but fixture inspection revealed all trusted masks are `np.ones` (100% trusted), disproving the trusted-mask hypothesis.
BLOCKED per repeat-failure guard (5 consecutive failures with same signature); escalating to supervisor with revised root-cause candidates (panel-id mismatch, sigma discrepancy, loss_mask staleness, precision drift, or best-snapshot logic).
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T214200Z/ (pytest logs, telemetry JSONs, collect logs)

## Implementation Details

### Changes Made
- **dbex/refinement/stage_c_impl.py:547-556** (ROI mode): Added trusted-mask gate using `stage_a_ctx.trusted_masks_t[pid, slow_slice, fast_slice]` (warm) or tensorized `inputs.trusted_mask[pid]` (cold), applying `torch.logical_and` before `_compute_variance_weighted_loss`.
- **dbex/refinement/stage_c_impl.py:589-606** (panel mode): Added trusted-mask gate using `stage_a_ctx.trusted_masks_t[panel_ids]` (warm) or stacked tensorized masks (cold), applying `torch.logical_and` to `mask_subset` before loss computation.
- Comments reference REFINE-016 and cite Stage A parity (stage_a_impl.py:1348-1350, 1550-1552).

### Test Results
- **Small detector**: PASSED all gates (0.000% chi² change, 99.999994% offset reduction)
- **Full detector**: FAILED REFINE-007 chi² gate (Stage A=2.1071e+08, Stage C=2.1085e+08, +0.067% identical to 2025-12-01T163900Z/170326Z/204500Z/210900Z)

### Root-Cause Analysis
Inspected `tests/dbex/test_torch_refine_smoke.py:311`: trusted masks are `np.ones(image_size[::-1], dtype=bool)` — ALL pixels trusted. The trusted-mask gating implementation is CORRECT but has NO effect on this test fixture because there are no untrusted pixels to exclude. The repeating 0.067% regression must stem from a different cause:
- Panel-ids mismatch (Stage C validations may sample different panels than Stage A final)
- Sigma_readout tensor discrepancy (device/dtype/source)
- Loss_mask staleness or preprocessing difference
- Numerical precision drift in warm-cache simulator state
- Best-snapshot vs final chi² logging mismatch (REFINE-013)

### Evidence
- Telemetry (`telemetry_stage_c_full.json`): cache_mode=warm, roi_mode=roi, validation_scope=panel, chi² flat across iterations (210848512.0 at iter 0/5/10)
- Stage A final chi² from telemetry: 2.10706464e+08
- Delta: +0.0674% (above 0.05% gate)
- Detector offsets: 99.999994% reduction, max final=0.00000001 mm (PASSING offset gates)

### Recommendation
Per repeat-failure guard, DO NOT attempt further implementation fixes without supervisor escalation. Run callchain analysis on `compute_loss_stage_c` to pinpoint the 0.067% divergence source (panel iteration, mask application, sigma usage, or accumulation). Add telemetry to Stage C iteration=0 to dump panel_ids, mask/sigma/target checksums, and per-panel chi² breakdown for bit-for-bit comparison with Stage A final validation.

The REFINE-016 trusted-mask implementation should be RETAINED in the codebase as it enforces correct Stage A/Stage C parity for real-world data with untrusted pixels, even though it doesn't resolve this specific test fixture's regression.
