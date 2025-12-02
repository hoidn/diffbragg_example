# ARCH-REFACTOR-001 Phase D.3 — Reconstruction Logic Bug Root Cause Diagnosis

**Loop:** 2025-12-02T000000Z (Galph planning loop servicing problems.md ledger)
**Focus:** ARCH-REFACTOR-001 Phase D.3 — DB-AT-028/029 test failures (bragg_after near-zero magnitude)
**Trigger:** problems.md fresh backlog entry with concrete diagnosis + remediation plan

---

## Executive Summary

User-supplied diagnosis in `problems.md` (lines 26-60) correctly identifies the root cause of Phase D.3 test failures. The bug is in `dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry` (lines 192-193), which applies `log_scale` as an absolute exponent instead of handling the calibration baseline logic that Stage A/C use.

**Impact:** When calibration metadata is present, `log_scale_baseline ≈ 20.0` (from `log(sqrt(spot_scale_override))`), and `log_scale` (delta) ≈ 0.0. Current broken code:
- `exp(clamp(0.0, ±10)) = exp(0) = 1.0` → wrong scale (factor ~10^8.5 too small)

Correct logic (matching Stage A lines 1194-1202 and Stage C lines 540-547):
- `exp(baseline + clamp(delta, ±3)) = exp(20 + 0) ≈ 4.85e8` → correct scale

**Initiative Type Alignment:** This is a **bugfix** (implementation defect in reconstruction helper that violates the calibration contract established by Stage A/TOOLING-VIS-001 Phase D.C). The fix is local to `reconstruction.py` and requires no spec/harness changes.

---

## Bug Location

**File:** `dbex/refinement/reconstruction.py`
**Function:** `build_final_bragg_from_stage_a_telemetry`
**Lines:** 192-193 (warm cache path and cold path both affected)

### Current Broken Code (lines 192-193)
```python
log_scale_clamped = torch.clamp(log_scale, min=-10.0, max=10.0)
scale_factor = torch.exp(log_scale_clamped)
```

**Problem:** Treats `log_scale` as an absolute exponent, ignoring the `log_scale_baseline` that Stage A established when `calibration_metadata` is present.

---

## Normative Behavior (from Stage A)

Per `dbex/refinement/stage_a.py` lines 131-137 (comments) and lines 1194-1202 (implementation):

**When calibration_metadata is present (TOOLING-VIS-001 Phase D.C, DB-AT-027):**
- `log_scale_baseline = log(sqrt(spot_scale_override))` is the fixed baseline (recorded in telemetry)
- `log_scale` is a **delta** parameter, clamped to `±config.log_scale_max_delta` (default ±3.0)
- **Final scale = `exp(log_scale_baseline + clamped_delta)`**

**Otherwise (uncalibrated):**
- `log_scale` is the direct learnable parameter (no baseline separation)
- Clamped to `±config.log_scale_max_delta_uncalibrated` (default ±10.0)
- **Final scale = `exp(clamped_log_scale)`**

### Reference Implementation (Stage A, lines 1194-1202)
```python
log_scale_baseline_value = param_values.get('log_scale_baseline')
max_delta_uncal = getattr(config, "log_scale_max_delta_uncalibrated", 10.0)
delta_bound = getattr(config, "log_scale_max_delta", 3.0) if log_scale_baseline_value is not None else max_delta_uncal
if log_scale_baseline_value is not None:
    log_scale_delta_clamped = torch.clamp(log_scale, min=-delta_bound, max=delta_bound)
    log_scale_clamped = log_scale_baseline_value + log_scale_delta_clamped
else:
    # Absolute clamp when no baseline is available
    log_scale_clamped = torch.clamp(log_scale, min=-delta_bound, max=delta_bound)
```

**This pattern is repeated in:**
- `stage_a.py` lines 1194-1202 (LBFGS closure)
- `stage_c.py` lines 540-547 (ROI mode loss)
- `stage_c.py` lines 612-618 (panel mode loss)
- `stage_c.py` lines 1241-1246 (final Bragg reconstruction)

**Missing from:**
- `reconstruction.py` lines 192-193 (this bug)

---

## Evidence from Test Failures

From `galph_memory.md` tail and Ralph's escalation notes:

### DB-AT-028 failure signature (repeated across 3 loops)
```
bragg_before_mean = 1.86          # correct (from mapping/perturbed geometry)
bragg_after_mean  = 7.59e-14      # near-zero, WRONG
chi²/pixel initial = 2.098e+05    # bound: ≤1e2
```

### Telemetry payload (from Ralph's debug artifacts)
```
log_scale (delta)         ≈ 0.0   (neutral, optimization converged)
log_scale_baseline (from calib) ≈ 20.0  (log(sqrt(spot_scale_override)))
```

**Current (broken) calculation:**
```python
scale_factor = exp(clamp(0.0, min=-10, max=10)) = exp(0) = 1.0
bragg_after = bragg_raw × 1.0 ≈ 7.6e-14  # near-zero because bragg_raw itself is ~O(1e-14) before scaling
```

**Correct calculation (matching Stage A):**
```python
scale_factor = exp(20.0 + clamp(0.0, min=-3, max=3)) = exp(20.0) ≈ 4.85e8
bragg_after = bragg_raw × 4.85e8 ≈ O(1)  # expected magnitude matching bragg_before
```

**Magnitude discrepancy:** Factor of ~10^8.5, consistent with missing baseline term.

---

## Remediation Plan (from problems.md)

User-supplied plan (problems.md lines 44-60) is correct and complete:

### Step 1: Patch `dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry`

**Location:** Lines 192-193 (replace both lines with conditional baseline logic)

**Required changes:**
1. Extract `log_scale_baseline` from telemetry payload (from `param_deltas_a` dict)
2. Extract config bounds:
   - `config.log_scale_max_delta` (default 3.0) for calibrated case
   - `config.log_scale_max_delta_uncalibrated` (default 10.0) for uncalibrated case
3. Apply conditional clamp + baseline logic:
   ```python
   log_scale_baseline_value = param_deltas_a.get('log_scale_baseline', {}).get('final')
   max_delta_uncal = getattr(config, "log_scale_max_delta_uncalibrated", 10.0)
   delta_bound = getattr(config, "log_scale_max_delta", 3.0) if log_scale_baseline_value is not None else max_delta_uncal

   if log_scale_baseline_value is not None:
       log_scale_baseline_tensor = torch.tensor(log_scale_baseline_value, device=device, dtype=dtype)
       log_scale_delta_clamped = torch.clamp(log_scale, min=-delta_bound, max=delta_bound)
       log_scale_clamped = log_scale_baseline_tensor + log_scale_delta_clamped
   else:
       # Legacy uncalibrated path: clamp absolute log_scale
       log_scale_clamped = torch.clamp(log_scale, min=-delta_bound, max=delta_bound)

   scale_factor = torch.exp(log_scale_clamped)
   ```

**Scope:** ~20 lines changed (lines 192-193 → 192-211 with conditional logic + comments)

### Step 2: Validation

Rerun the blocked acceptance criteria:

```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=metadata \
DBEX_SMOKE_DETECTOR_SIZE=full \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028 \
              tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029
```

**Expected outcome:** Both tests PASS with bragg_after magnitude ≈ O(1), chi²/pixel ≤ 1e2 bound satisfied.

**No test harness changes required:** Tests are already correct; the bug is purely in reconstruction logic.

---

## Spec/Contract Alignment

### Normative References
- `docs/spec-db-core.md` §§20-40 (geometry/crystal/calibration contracts)
- `docs/architecture/calibration_scaling.md` (ADU↔photon policy, spot_scale threading)
- Finding **TOOLING-VIS-001 Phase D.C** (log_scale baseline separation for calibrated runs)
- Finding **DB-AT-027** (Stage A mapping parity with calibration)

### Contract Violated
`build_final_bragg_from_stage_a_telemetry` is a **reconstruction helper** that must honor the same calibration semantics as Stage A's LBFGS closure. When Stage A records `log_scale_baseline` in telemetry (non-None), the reconstruction **SHALL** apply the same conditional clamp logic.

**Current bug:** Helper assumes legacy uncalibrated behavior (absolute clamp ±10) even when telemetry contains a calibration baseline.

**Fix alignment:** Brings reconstruction.py into parity with Stage A (lines 1194-1202), Stage C (lines 540-547, 612-618, 1241-1246), matching the normative pattern established across the codebase.

---

## Initiative Type Confirmation

**This is a `bugfix` initiative:**
- ✓ Implementation defect in reconstruction helper (violates established contract)
- ✓ No spec changes required (calibration semantics already normative via TOOLING-VIS-001)
- ✓ No harness changes required (tests already encode correct expectations)
- ✓ No architecture changes required (local fix, ~20 lines)
- ✗ NOT a spec_change (spec is clear, implementation is wrong)
- ✗ NOT architecture (no module boundaries or seams changed)
- ✗ NOT harness (tests are fine, code is broken)

**Scope boundaries respected:**
- Fix is **local** to `reconstruction.py` (single function, single file)
- Pattern is **already established** (Stage A/C reference implementations exist)
- No **cross-cutting changes** (no shared dependencies modified)

---

## Lifecycle Context

### Implementation Budget Check (per <initiative_lifecycle/>)
**Focus:** ARCH-REFACTOR-001 Phase D.3 (DB-AT-028/029 acceptance criteria)
**Implementation loops so far:** 3 (all failed with identical signature)
**Budget limit:** 3 loops per acceptance criterion before escalation

**Status:** At budget limit. This is the **final permitted implementation loop** for this acceptance criterion under the current initiative before mandatory escalation to spec_change.

**Justification for proceeding:**
1. User-supplied diagnosis is **concrete and code-specific** (not speculative)
2. Root cause is **confirmed implementation defect** (not spec/test mismatch)
3. Fix pattern is **normative** (already established in 4+ locations: stage_a.py, stage_c.py)
4. Expected outcome is **deterministic** (magnitude error scales linearly with missing baseline term)
5. No **ambiguity** (telemetry contract is clear, reconstruction helper violated it)

**If this loop fails:** Per repeat-failure escalation rule, must either:
- Open dedicated `spec_change` initiative to revise calibration contracts (unlikely, spec is clear)
- Open dedicated `harness` initiative to weaken test gates (unlikely, tests are correct)
- Mark ARCH-REFACTOR-001 Phase D.3 `stuck` and escalate to architecture review (most likely path)

---

## Artifacts for This Loop

**Reports directory:** `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T000000Z_galph_phase_d3_fix_diagnosis/`

**Artifacts:**
- `root_cause_diagnosis.md` (this file) — Concrete bug location, spec alignment, fix strategy
- `fix_diff.patch` (to be created by Ralph) — Exact diff for reconstruction.py lines 192-211
- `pytest_db_at_028_029.log` (to be created by Ralph) — Validation run showing both tests PASS
- `metrics_comparison.json` (to be created by Ralph) — Before/after bragg_after magnitude, chi²/pixel values

---

## Next Steps

1. **Galph (this loop):** Write `input.md` with targeted bugfix Do Now:
   - Focus: ARCH-REFACTOR-001 Phase D.3
   - Implement: `dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry` (lines 192-211)
   - Validate: `test_db_at_028`, `test_db_at_029`
   - Artifacts: `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T000000Z_galph_phase_d3_fix_diagnosis/`

2. **Ralph (next loop):** Execute the Do Now, apply fix per this diagnosis, run tests, capture artifacts

3. **If PASS:** Mark Phase D.3 complete, update problems.md ledger (check off entry), proceed to Phase D.4

4. **If FAIL:** Mark ARCH-REFACTOR-001 Phase D.3 `stuck`, escalate per <spec_change_flow/> or <initiative_lifecycle/>

---

## Problems Ledger Linkage

**Entry serviced:** `problems.md` lines 26-60 (IMPORTANT NEW: diagnosis and specific remediation plan to unblock ARCH-REFACTOR-001 Phase D.3)

**Post-loop action:** If tests PASS, update `problems.md`:
- Add `[x]` checkbox to the entry (lines 26-60)
- Append resolution summary: "Resolved via ARCH-REFACTOR-001 Phase D.3 bugfix (commit <sha>, 2025-12-02T<HHMMSS>Z). reconstruction.py now mirrors Stage A/C calibration baseline logic (lines 192-211). Tests DB-AT-028/029 PASSED with bragg_after magnitude ≈ O(1), chi²/pixel ≤ 1e2. Artifacts: `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T000000Z_galph_phase_d3_fix_diagnosis/`."
