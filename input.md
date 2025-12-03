# Input for Ralph (Loop i=455)

## Summary
Force explicit 3-fold oversampling in simulate_forward_once and reconstruction paths to resolve 5,586× raw output magnitude discrepancy (ARCH-SIM-CONSTRUCTION-001 Phase C.4).

## Mode
Parity

## InitiativeType
architecture

## Focus
ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment

## Branch
integration

## Mapped tests
```
tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity
tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_roi_correlation_sanity
```

## Artifacts
```
plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T235959Z/
├── galph_root_cause_final_oversampling.md (Galph analysis)
├── pytest_db_at_028_029.log (validation)
├── summary.md (implementation outcome)
└── metrics_comparison.json (before/after raw output comparison)
```

---

## Do Now

### Context

Ralph's Phase C.3 diagnostic probe (commit 8159de9a, loop i=454) definitively identified the root cause of DB-AT-028/029 failures:

**Oversampling configuration mismatch:**
- Path A (`simulate_forward_once`): 3072×3072 panel → auto-selects **3-fold oversampling** → raw mean 1.714e-09
- Path B (reconstruction cold path): 1024×1024 detector → auto-selects **1-fold oversampling** → raw mean 9.574e-03
- Raw ratio A/B = 1.79e-07 (**5,586× discrepancy**)

`DetectorConfig` has parameter `oversample: int = -1` (default = auto-select based on pixel count). Different detector sizes trigger different auto-selection, causing magnitude divergence unrelated to scale_factor logic.

**Fix:** Add explicit `oversample=3` parameter to both paths so they use identical oversampling configuration.

### Implementation Steps

#### 1. Update `create_detector_config` Signature

**File:** `dbex/refinement/config_factories.py`
**Function:** `create_detector_config` (starts line 48)

**Changes:**
- Add parameter `oversample: int = -1` to function signature (after `roi_bbox`)
- Forward it to `DetectorConfig` constructor (line ~214-227)

**Code pattern:**
```python
def create_detector_config(
    panel,
    beam,
    trusted_mask: Optional[np.ndarray] = None,
    distance_mm_override: Optional['torch.Tensor'] = None,
    roi_bbox: Optional[Tuple[int, int, int, int]] = None,
    oversample: int = -1,  # ← NEW: explicit oversampling control
) -> DetectorConfig:
    # ... existing logic ...

    return DetectorConfig(
        distance_mm=distance_mm,
        pixel_size_mm=px_fast_mm,
        spixels=slow_px,
        fpixels=fast_px,
        beam_center_s=beam_center_s,
        beam_center_f=beam_center_f,
        beam_center_source="explicit",
        detector_convention=DetectorConvention.DIALS,
        detector_rotx_deg=detector_rotx_deg,
        detector_roty_deg=detector_roty_deg,
        detector_rotz_deg=detector_rotz_deg,
        mask_array=mask_array,
        oversample=oversample  # ← NEW: forward parameter
    )
```

**Docstring update:** Add parameter documentation:
```
oversample: Oversampling factor (1, 2, 3, ...). Default -1 = auto-select based on detector size.
           Use explicit value (e.g., 3) to force consistent oversampling across detector configs.
```

#### 2. Update `simulate_forward_once` Call Site

**File:** `dbex/nanobrag_bridge.py`
**Function:** `simulate_forward_once` (starts line ~1362)
**Target line:** ~1406 (inside panel loop, `create_detector_config` call)

**Change:**
```python
# Before:
detector_config = create_detector_config(
    panel=panel,
    beam=beam,
    trusted_mask=inputs.trusted_mask[panel_id]
)

# After:
detector_config = create_detector_config(
    panel=panel,
    beam=beam,
    trusted_mask=inputs.trusted_mask[panel_id],
    oversample=3  # ← NEW: force 3-fold oversampling for parity with reconstruction
)
```

**Rationale:** Ensure auto-select doesn't vary based on panel pixel count.

#### 3. Update Reconstruction Cold Path Call Site

**File:** `dbex/refinement/reconstruction.py`
**Function:** `build_final_bragg_from_stage_a_telemetry` (starts line 28)
**Target line:** ~190 (inside `else` block for cold path)

**Change:**
```python
# Before:
detector_config = create_detector_config(detector[pid], beam=beam)

# After:
detector_config = create_detector_config(
    detector[pid],
    beam=beam,
    oversample=3  # ← NEW: force 3-fold oversampling matching simulate_forward_once
)
```

**Rationale:** Match `simulate_forward_once` oversampling exactly.

#### 4. Run Validation Tests

**Command:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=metadata \
DBEX_SMOKE_DETECTOR_SIZE=full \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv \
  tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity \
  tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_roi_correlation_sanity \
  --tb=short \
  2>&1 | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T235959Z/pytest_db_at_028_029.log
```

**Expected outcomes:**
- `bragg_after_mean ≈ 0.24` (matching `bragg_before_mean`, not 1.025e-05)
- `chi²/pixel initial ≤ 1e2` (not 1e5)
- `median ROI correlation before ≥ 0.2` (not -0.05)
- Both tests PASS

#### 5. Capture Metrics Comparison

Create `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T235959Z/metrics_comparison.json` with:
```json
{
  "before_fix": {
    "bragg_after_mean": 1.025e-05,
    "chi2_per_pixel_initial": 108400,
    "roi_cc_median_before": -0.05,
    "oversample_path_a": "auto (3-fold for 3072²)",
    "oversample_path_b": "auto (1-fold for 1024²)",
    "raw_ratio": 1.79e-07
  },
  "after_fix": {
    "bragg_after_mean": "(capture from test output)",
    "chi2_per_pixel_initial": "(capture from test output)",
    "roi_cc_median_before": "(capture from test output)",
    "oversample_path_a": "explicit 3-fold",
    "oversample_path_b": "explicit 3-fold",
    "raw_ratio": "(should be ~1.0 ± 0.1)"
  }
}
```

Extract values from test artifact JSON files emitted by DB-AT-028/029.

---

## How-To Map

### 1. Edit config_factories.py
```bash
# Add oversample parameter to create_detector_config signature (line 48-54)
# Forward it to DetectorConfig constructor (line ~214-227)
# Update docstring with parameter documentation
```

### 2. Edit nanobrag_bridge.py
```bash
# Update create_detector_config call at line ~1406
# Add oversample=3 parameter
```

### 3. Edit reconstruction.py
```bash
# Update create_detector_config call at line ~190
# Add oversample=3 parameter
```

### 4. Run tests
```bash
# Execute pytest command above, capture log to artifacts directory
```

### 5. Extract metrics
```bash
# Read DB-AT-028/029 artifact JSON files (location in test output)
# Create metrics_comparison.json with before/after values
```

### 6. Write summary
```bash
# Create summary.md documenting:
# - Code changes (3 files, 6 lines net)
# - Test outcomes (PASS/FAIL + metrics)
# - Before/after raw output comparison
# - Next action (mark Phase C.4 complete OR escalate if still failing)
```

---

## Pitfalls To Avoid

1. **DO NOT** change oversample logic in nanobrag_torch itself (external dependency; environment freeze)
2. **DO NOT** hard-code oversample in `DetectorConfig` constructor call sites other than the two specified (simulate_forward_once, reconstruction)
3. **DO** keep `oversample=-1` default in `create_detector_config` signature (backward compatibility for other call sites)
4. **DO** use identical `oversample=3` value in both paths (asymmetry will reintroduce discrepancy)
5. **DO** verify tests run with `DBEX_SMOKE_DETECTOR_SIZE=full` (full panel required to trigger original auto-select logic)
6. **DO** check that `bragg_before` and `bragg_after` magnitudes now match (ratio ≈ 1.0 ± 0.2, not 23,000×)

---

## If Blocked

If tests still FAIL after this fix with similar magnitude discrepancy:

1. **Capture debug evidence:**
   - Add temporary print statements in both paths showing `detector_config.oversample` value
   - Verify both simulators report "auto-selected 3-fold oversampling" (or explicit 3-fold)
   - Capture raw simulator outputs (should now match within 10%)

2. **Record block in Attempts History:**
   - Note: "Phase C.4 oversample fix applied, but tests still fail with [symptoms]"
   - Capture full pytest log and metrics_comparison.json showing post-fix state
   - Per `<initiative_lifecycle/>` hard rule, this is attempt #4 for DB-AT-028/029
   - **Escalation required:** Mark ARCH-SIM-CONSTRUCTION-001 `stuck`, open new diagnostic initiative

3. **Alternative hypothesis:**
   - If oversampling now matches but magnitudes still differ, investigate detector pixel count mismatch (why did probe show 1024² vs 3072²?)
   - Check if test harness provides cropped/binned detector to reconstruction helper
   - Trace detector[pid].get_image_size() in both paths

---

## Findings Applied

**SCALE-009** (docs/findings.md:42): Stage A applies `sqrt(spot_scale_override)` post-run (stage_a.py:442-443); reconstruction must match this pattern. This fix addresses the **underlying detector config mismatch** that caused different oversampling auto-selection, which in turn caused raw magnitude divergence that overshadowed the scaling logic alignment.

---

## Pointers

- **Spec:** docs/spec-db-core.md §§20-40 (calibration contracts)
- **Architecture:** docs/architecture/calibration_scaling.md (spot_scale threading)
- **IDL:** docs/architecture/dbex/nanobrag_bridge.idl.md (future: document oversample contract)
- **Test selectors:** docs/TESTING_GUIDE.md §2.1 (DB-AT-028/029 acceptance criteria)
- **Probe evidence:** plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T220000Z/probe_run.log (Ralph's diagnostic probe)
- **Galph analysis:** plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T235959Z/galph_root_cause_final_oversampling.md

---

## Next Up

If Phase C.4 completes successfully (tests PASS):
- **Phase D.1:** Document factory oversample contract in IDL
- **Phase D.2:** Close ARCH-SIM-CONSTRUCTION-001, unblock ARCH-REFACTOR-001 Phase D.3

If Phase C.4 fails (tests still fail after fix):
- **Escalation:** Per `<initiative_lifecycle/>`, mark ARCH-SIM-CONSTRUCTION-001 `stuck` (4th attempt)
- **New initiative:** Open diagnostic task to investigate detector pixel count mismatch hypothesis
