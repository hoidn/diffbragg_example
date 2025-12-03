# Input — ARCH-SIM-CONSTRUCTION-001 Phase C.1 Corrective Fix

## Summary
Apply missing `sqrt_spot_scale` multiplication to simulator output in reconstruction helper.

## Mode
Parity

## InitiativeType
architecture

## Focus
[ARCH-SIM-CONSTRUCTION-001] — Simulator Construction Convention Alignment (Training vs Reconstruction)

## Branch
integration

## Mapped Tests
- tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity
- tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity

## Artifacts
plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T010500Z/

---

## Do Now

### Context

Your Phase C.1 implementation (commit a00d42c7) correctly extracted `sqrt_spot_scale` from `spot_scale_override` at reconstruction.py:152 and threaded beam calibration metadata (beam_flux, exposure, beamsize_mm) to the factory, but you **forgot to apply the sqrt_spot_scale multiplication** to the simulator output.

**Evidence:**
- Test metrics show `bragg_after_mean = 5711.08` (expected ~0.24)
- Missing factor ~23,800 ≈ sqrt(spot_scale_override) = sqrt(3.105e17) ≈ 5.57e8
- DB-AT-028: chi²/pixel initial still 1.084e+05 (vs ≤1e2 spec)
- DB-AT-029: ROI correlation before still -0.050 (vs ≥0.2 floor)

**Stage A Reference Pattern (stage_a.py:442-443):**
```python
sqrt_spot_scale = float(np.sqrt(spot_scale_override)) if spot_scale_override > 0 else 1.0
bragg_stack_scaled = bragg_stack * sqrt_spot_scale  # Explicit post-run multiplication
```

### Implement

**File:** `dbex/refinement/reconstruction.py`

**1. Apply sqrt_spot_scale multiplication (line 239):**

Change:
```python
bragg_scaled = bragg_panel * scale_factor
```

To:
```python
bragg_scaled = bragg_panel * scale_factor * sqrt_spot_scale
```

**Rationale:** Stage A applies sqrt(spot_scale_override) as an **explicit post-run multiplication** separate from the exp(log_scale_baseline) scaling. The baseline is embedded in the learnable log_scale parameter's zero-point, while the sqrt multiplication is applied to the raw simulator output to match mapping conventions (SCALE-009, TOOLING-VIS-001 Phase D.E).

---

## How-To Map

### 1. Edit reconstruction.py

```bash
# Line 239: Add sqrt_spot_scale multiplication
# Old: bragg_scaled = bragg_panel * scale_factor
# New: bragg_scaled = bragg_panel * scale_factor * sqrt_spot_scale
```

Use the Edit tool to update line 239.

### 2. Validate with DB-AT-028/029

```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
DBEX_SMOKE_SIGMA_SOURCE=metadata
DBEX_SMOKE_DETECTOR_SIZE=full
KMP_DUPLICATE_LIB_OK=TRUE
NANOBRAGG_DISABLE_COMPILE=1

pytest -xvs tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity \
              tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity \
  > plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T010500Z/pytest_db_at_028_029_fixed.log 2>&1
```

### 3. Capture metrics

After tests run (PASS or FAIL), extract metrics from the test fixture for comparison:

```bash
# Extract metrics from test outputs (if tests emit JSON or you can add a fixture.write_text() call)
# Look for bragg_after_mean, chi2_per_pixel_initial, roi_cc_median_before
# Expected after fix:
#   bragg_after_mean ≈ 0.24 (not 5711)
#   chi2_per_pixel_initial ≤ 100 (not 1e5)
#   roi_cc_median_before ≥ 0.2 (not -0.05)
```

If tests emit metrics JSON (check test_stage_a_smoke_parity.py for fixture logic), copy them to the artifacts directory. Otherwise, note the test outcomes in summary.md.

---

## Pitfalls To Avoid

1. **Do not remove sqrt_spot_scale calculation (line 152)** — you correctly extracted it; just need to apply it.
2. **Do not modify scale_factor logic (lines 227-236)** — the exp(log_scale_baseline + delta) calculation is correct; this is an **additional** multiplication.
3. **Environment freeze** — do not install packages; treat missing imports as blockers.
4. **Device/dtype neutrality** — sqrt_spot_scale is a Python float (scalar multiplication), no tensor device issues.
5. **Warm vs cold path** — both paths converge at the same sim.run() loop (lines 237-240), so one fix covers both.

---

## If Blocked

If tests still FAIL after applying the multiplication:
1. Capture the new metrics (bragg_after_mean, chi2, ROI corr) in `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T010500Z/debug_metrics_postfix.json`
2. Note in Attempts History whether the magnitude improved (bragg_after should drop from 5711 to ~0.24)
3. If magnitude is still wrong, check whether sqrt_spot_scale = 1.0 (calibration metadata missing or spot_scale_override = None)

---

## Findings Applied

- **SCALE-009** (docs/findings.md:42): Reconstruction helpers must apply `sqrt(spot_scale_override)` as explicit post-run scaling, matching Stage A convention (stage_a.py:442-443). The baseline value `log(sqrt(spot_scale_override))` is used for the learnable delta parameter's zero-point, not as a substitute for the physical multiplication.

---

## Pointers

- **Spec:** docs/spec-db-core.md §§20-40 (calibration threading)
- **Spec:** docs/architecture/calibration_scaling.md (spot_scale application timing)
- **Stage A Reference:** dbex/refinement/stage_a.py:442-443 (sqrt_spot_scale multiplication)
- **Factory Contract:** dbex/refinement/helpers.py::create_unified_simulator (spot_scale_override parameter usage)
- **Fix Plan:** docs/fix_plan.md — Row [ARCH-SIM-CONSTRUCTION-001]
- **Debug Analysis:** plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T010500Z/debug_analysis.md
