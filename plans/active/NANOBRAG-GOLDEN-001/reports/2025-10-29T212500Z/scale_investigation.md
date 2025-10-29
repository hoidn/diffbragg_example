# Scale Investigation - NANOBRAG-GOLDEN-001

## Date: 2025-10-29T212500Z

## Objective
Remove double-scaling in canonical capture per SCALE-001 finding to fix DB_AT_001 parity.

## What Was Changed
Modified `scripts/generate_simple_cubic_golden.py::build_structure_factor_grid()` (lines 96-120):
- **Removed**: `amps = amps * np.sqrt(float(scale_override))` multiplication
- **Updated**: Docstring to clarify that DiffBragg handles scaling internally
- **Result**: Structure factors now used as-is from MTZ without any scaling applied

## Observed Results

### Previous Behavior (WITH sqrt(scale_override) scaling)
- scale_override = 3.185e+17
- sqrt(scale_override) = 5.64e+08
- DiffBragg max: 3.62e+04
- Torch max: 2.19e+13
- **Ratio (torch/diffbragg): ~6e+08** ← Matches the sqrt multiplier!
- **Problem**: Torch intensities inflated by ~6×10^8 relative to DiffBragg

### Current Behavior (WITHOUT any scaling)
- scale_override = 3.185e+17 (ignored)
- Structure factors: min=1.546, max=518.3, mean=47.41
- DiffBragg max: 36164.9
- Torch max: 6.914e-05
- **Ratio (torch/diffbragg): ~1.9e-09** ← Torch now TOO SMALL!
- **Problem**: Torch intensities underestimated by ~5×10^08 relative to DiffBragg

## Analysis

The results suggest that:

1. **Previous Implementation WAS Wrong**: Applying sqrt(scale_override) to structure factors caused torch output to be ~6×10^8 too high, confirming SCALE-001 diagnosis.

2. **Current Implementation ALSO Has Issues**: Removing all scaling causes torch to be ~5×10^8 too low.

3. **Hypothesis**: nanobrag_torch and DiffBragg handle intensity scaling differently:
   - DiffBragg: Applies `spot_scale_override` internally during forward pass (line 365: `spot_scale_override=mdl_parm["scale"]`)
   - nanobrag_torch: May NOT apply any scaling automatically, OR scales differently via flux/exposure/other parameters

## Evidence
- Structure factor grid stats: min=0.000e+00, max=5.183e+02, mean=1.876e+01, nonzero=69614
- HKL hit rate: 98.73% (6144865/6224001 reflections)
- Beam config: flux=1.0e12, beamsize_mm=1.0, exposure=1.0
- RAW torch output: max=6.914329e-05, mean=3.819114e-10, nonzero=5622327

## Status
**Blocked** - Need clarification on nanobrag_torch scaling model:

### Questions for nanobrag_torch maintainer:
1. Does nanobrag_torch internally apply any scale factor to structure factors?
2. Should flux/exposure/beamsize be adjusted to account for DiffBragg's spot_scale_override?
3. Is there a separate scale parameter that should be used post-simulation?
4. What is the expected relationship between structure factor amplitudes and output intensities?

### Alternative Investigation Paths:
1. Check nanobrag_torch source code for internal scaling logic
2. Compare DiffBragg's spot_scale_override application with torch's flux/exposure handling
3. Test if scaling can be applied post-simulation (multiply torch output by scale_override)
4. Review any nanobrag_torch documentation on intensity calibration

## Next Actions
- Document this finding in `docs/findings.md` as SCALE-002
- Mark NANOBRAG-GOLDEN-001 as blocked pending scaling model clarification
- Consider consulting with nanobrag_torch maintainer or reviewing source code

## Artifacts
- Canonical capture log: `canonical_capture.log`
- Torch config: `golden_dataset/torch/config_torch.json`
- DiffBragg config: `golden_dataset/legacy/config_diffbragg.json`
- Parity metrics: `golden_dataset/metrics.json`
- Test results: `pytest_db_at_001.log`
