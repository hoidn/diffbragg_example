# NANOBRAG-GOLDEN-001 Loop Summary (2025-10-29T094859Z)

## Status: BLOCKED - HKL Range Mismatch

## Actions Completed

### A3: Miller Index Projection Fix
**File**: `nanobrag_torch/simulator.py:196-205`

**Changes**:
1. Reverted from reciprocal vector projection (`rot_a_star` · `scattering_angstrom`) to real-space vector projection (`rot_a` · `scattering`)
2. Removed incorrect Å^-1 unit conversion (line 200 deleted)
3. Updated per nanoBragg.c lines 3108-3110: `h = dot_product(a, scattering)` where `a` is in meters and `scattering` is in m^-1

**Rationale**:
- nanoBragg.c uses real-space vectors `a,b,c` (meters) dotted with scattering vector (m^-1)
- Uses crystallographic identity: `a · (h·a* + k·b* + l·c*) = h` due to orthogonality `a·a*=1, a·b*=0, etc.`
- Dimensional analysis: meters × m^-1 = dimensionless ✓

### A3: Enhanced HKL Diagnostics
**File**: `nanobrag_torch/simulator.py:220-239`

**Changes**:
1. Added HKL bounds logging: `h0_min`, `h0_max`, `k0_min`, `k0_max`, `l0_min`, `l0_max`
2. Restructured output: `[HKL stats] h=[min,max] k=[min,max] l=[min,max] hit_rate=N/M (%)`
3. Kept logging bounded to one line per panel (input.md:34 requirement)

**Example output**:
```
[HKL stats] h=[18,48] k=[14,53] l=[23,61] hit_rate=0/6224001 (0.00%)
```

## Blocker Discovered

### Root Cause: HKL Range Mismatch
**Observed Behavior**:
- Computed Miller indices: h ∈ [18, 48], k ∈ [14, 53], l ∈ [23, 61]
- Structure factor grid: h ∈ [-24, 24], k ∈ [-28, 28], l ∈ [-31, 31]
- Result: **0% hit rate** — ALL 6.2M pixel lookups fall outside grid bounds

**Evidence**:
1. `torch_hkl_debug.json`: Grid bounds h_min=-24, h_max=24, k_min=-28, k_max=28, l_min=-31, l_max=31
2. Canonical capture log: `[HKL stats] h=[18,48] k=[14,53] l=[23,61] hit_rate=0/6224001 (0.00%)`
3. torch output: `min=0.0, max=0.0, mean=0.0, nonzero=0` (all zeros)

**Analysis**:
- The HKL range is **shifted positive** (~30 indices offset) from the grid center
- This suggests either:
  1. Sign error in scattering vector or lattice vectors
  2. Missing coordinate transformation (detector vs lab frame)
  3. Structure factor grid indexed incorrectly
  4. Beam geometry inversion (incident ↔ diffracted swap)

**Dimensional Verification**:
- Real-space vectors: Angstroms (from `get_rotated_real_vectors`) → meters (×1e-10 at simulator.py:873)
- Scattering vector: m^-1 (from simulator.py:158: `(diffracted - incident) / wavelength_meters`)
- Dot product: meters × m^-1 = dimensionless ✓
- **Dimensions are correct; issue is in coordinate system or sign conventions**

## Artifacts Generated
- `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T094859Z/canonical_capture.log` (897 KB)
- `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T094859Z/torch_hkl_debug.json`
- `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T094859Z/golden_dataset/legacy/bragg_diffbragg.npy` (max=36144.45)
- `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T094859Z/golden_dataset/torch/bragg_torch.npy` (max=0.00)
- `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T094859Z/golden_dataset/metrics.json`

## Metrics
- DiffBragg baseline: max=36144.45, 97,131 nonzero pixels
- Torch baseline: max=0.00, 0 nonzero pixels (BLOCKED)
- Structure factor grid: 69,614 reflections, 100% in-range initially
- HKL hit rate: 0.00% (0/6,224,001 pixels)
- Median correlation: NaN
- Localization success: 0.0%

## Next Actions
1. **Investigate HKL offset**: Compare nanoBragg.c trace output with torch trace for same pixel to identify sign/coordinate mismatch
2. **Verify structure factor grid indexing**: Check if grid h_min/h_max are being applied correctly in `crystal.get_structure_factor()`
3. **Check beam geometry**: Verify `incident_beam_direction` and `diffracted_beam_unit` orientations match nanoBragg.c conventions
4. **Alternative hypothesis**: Structure factor grid may need to be centered differently or use different indexing convention

## Findings to Document
- **HKL-PROJ-001**: Miller index projection requires real-space vectors (not reciprocal), per nanoBragg.c:3108-3110 and crystallographic orthogonality identity
- **HKL-RANGE-001**: Computed HKL range [18-48, 14-53, 23-61] falls completely outside structure factor grid [-24 to 24, -28 to 28, -31 to 31], causing 0% hit rate despite correct dimensional analysis
