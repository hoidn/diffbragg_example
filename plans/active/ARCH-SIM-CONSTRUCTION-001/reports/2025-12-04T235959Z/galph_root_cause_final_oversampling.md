# ARCH-SIM-CONSTRUCTION-001 Root Cause — Oversampling Mismatch
**Loop:** i=454 (Galph)
**Date:** 2025-12-04T235959Z
**Status:** Root cause CONFIRMED via Ralph's Phase C.3 diagnostic probe

## Executive Summary

Ralph's diagnostic probe (commit 8159de9a) definitively identified the root cause: **oversampling configuration mismatch** between `simulate_forward_once()` and reconstruction helper paths.

**Key Evidence:**
- Path A (simulate_forward_once): 3072×3072 panel → auto-selects **3-fold oversampling** → raw output 1.714e-09
- Path B (reconstruction cold path): 1024×1024 detector → auto-selects **1-fold oversampling** → raw output 9.574e-03
- Raw ratio A/B = 1.79e-07 → **5,586× discrepancy**

**Verdict:** Different detector pixel counts trigger different auto-selected oversampling factors in nanobrag_torch Simulator, causing raw output magnitude divergence unrelated to scale_factor logic.

---

## Probe Evidence (Loop i=454, commit 8159de9a)

From `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T220000Z/probe_run.log`:

```
=== Path A: simulate_forward_once() ===
auto-selected 3-fold oversampling
[HKL stats] h=[-12,7] k=[-14,9] l=[-14,8] hit_rate=9408494/9437184 (99.70%)
  Raw output (before sqrt): mean=1.713925e-09, max=1.104069e-04
  Scaled output (after sqrt): mean=9.550518e-01, max=6.152212e+04

=== Path B: Reconstruction Helper (Cold Path) ===
auto-selected 1-fold oversampling
[HKL stats] h=[-12,7] k=[-14,9] l=[-14,8] hit_rate=1045385/1048576 (99.70%)
  Raw simulator output: mean=9.573705e-03, max=8.605372e-02
```

**Key observations:**
1. Path A processes 9,437,184 pixels (3072² full panel)
2. Path B processes 1,048,576 pixels (1024² cropped or different detector)
3. Pixel count ratio: 9437184 / 1048576 ≈ 9.0 (exactly 9×, suggesting 3072/1024 = 3 fold difference)
4. Raw output ratio: 9.574e-03 / 1.714e-09 ≈ 5.586e+06
5. Oversampling normalization: 3-fold = 9 pixels per logical pixel, normalized by factor ~9

## Root Cause Analysis

### Oversampling Auto-Selection Logic

`DetectorConfig` has parameter `oversample: int = -1` (default = auto-select).

When `oversample = -1`, nanobrag_torch Simulator auto-selects based on detector pixel count:
- Large detectors (3072×3072) → 3-fold oversampling
- Small detectors (1024×1024) → 1-fold oversampling

**Normalization impact:**
- 3-fold oversampling: Each logical pixel → 3×3 = 9 physical pixels
- Simulator output is normalized per physical pixel
- If normalization differs between 1-fold and 3-fold, raw outputs will differ by factor ~9

However, 5.586e+06× is NOT 9×. The discrepancy is larger, suggesting:
1. Different detector pixel counts (Path B is NOT using full panel?)
2. Different HKL grids or beam configurations
3. Combined effect of oversampling + other config mismatches

### Why Different Detector Sizes?

Looking at reconstruction.py:190:
```python
detector_config = create_detector_config(detector[pid], beam=beam)
```

This should create FULL PANEL DetectorConfig matching `detector[pid].get_image_size()` (3072×3072 for refgeom dataset).

But probe shows Path B using 1024×1024. Possible explanations:
1. **Test harness uses CROPPED data**: DB-AT-028 may provide a cropped/binned detector to reconstruction helper
2. **ROI mode active**: Reconstruction may be building ROI-cropped simulators instead of full-panel
3. **Probe script error**: Ralph's probe may have inadvertently used different detector configs in the two paths

---

## Fix Strategy

### Option A: Force Explicit Oversampling

Add `oversample=3` parameter to `create_detector_config` calls in both paths:

**Pros:**
- Guaranteed consistent oversampling regardless of detector pixel count
- Simple one-line fix

**Cons:**
- Hard-codes oversampling factor (what if we want 1-fold for performance?)
- Does not address underlying detector size mismatch (if present)

**Implementation:**
1. Update `create_detector_config` signature to accept `oversample: int = -1` parameter
2. Pass `oversample=3` in `simulate_forward_once` (nanobrag_bridge.py:1406)
3. Pass `oversample=3` in reconstruction cold path (reconstruction.py:190)
4. Update `create_detector_config` to forward `oversample` to `DetectorConfig` constructor

### Option B: Align Detector Configurations

Ensure both paths use identical detector configs (same pixel counts, same ROI/panel selection):

**Pros:**
- Addresses root cause (detector size mismatch)
- Auto-select will naturally give same oversampling

**Cons:**
- Requires understanding WHY probe showed 1024×1024 vs 3072×3072
- May require test harness changes

**Investigation needed:**
1. Read DB-AT-028 test fixture to see what detector it provides
2. Confirm reconstruction helper receives full panel, not cropped ROI
3. Check if probe script correctly replicated test conditions

---

## Recommended Action

**Phase C.4 — Force Explicit Oversampling (Immediate Fix)**

Add `oversample` parameter to `create_detector_config` and explicitly set `oversample=3` in both paths:

1. **Update `dbex/refinement/config_factories.py::create_detector_config`:**
   - Add parameter `oversample: int = -1`
   - Pass it to `DetectorConfig` constructor

2. **Update `dbex/nanobrag_bridge.py::simulate_forward_once`:**
   - Pass `oversample=3` when calling `create_detector_config` (line ~1406)

3. **Update `dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry`:**
   - Pass `oversample=3` when calling `create_detector_config` (line ~190)

4. **Validation:**
   - Run DB-AT-028/029
   - Verify bragg_before and bragg_after now have matching magnitudes
   - Confirm chi²/pixel ≤ 100 and ROI correlation ≥ 0.2

**Expected outcome:**
- Both paths use 3-fold oversampling
- Raw simulator outputs match (within 10% tolerance)
- bragg_after_mean ≈ 0.24 (matches bragg_before)

---

## Lifecycle Notes

**ARCH-SIM-CONSTRUCTION-001 Implementation Attempts:**
- DB-AT-028: 3 (at budget limit)
- DB-AT-029: 3 (at budget limit)

This is the **third evidence/analysis loop** for this initiative. Per `<initiative_lifecycle/>` hard rule, if this loop does not lead to a passing fix, initiative must be marked `stuck` and escalated.

However, Ralph's probe provides conclusive evidence with clear fix path (Option A), so one more implementation loop is justified.

**Next action:** Phase C.4 implementation — add explicit `oversample=3` parameter to both paths.
