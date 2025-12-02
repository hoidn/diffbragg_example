# Input for Ralph — ARCH-REFACTOR-001 Phase D.3 Reconstruction Logic Bugfix

**Summary:** Fix calibration baseline logic in reconstruction helper so bragg_after magnitude matches bragg_before

**Mode:** none (targeted bugfix)

**InitiativeType:** bugfix

**Focus:** ARCH-REFACTOR-001 — Refinement Engine Modularization & Physics Separation

**Branch:** integration

**Mapped tests:**
- `tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028`
- `tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029`

**Artifacts:** `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T000000Z_galph_phase_d3_fix_diagnosis/`

---

## Do Now

### Context

Problems ledger entry (lines 26-60) provided concrete diagnosis of the Phase D.3 test failures: `build_final_bragg_from_stage_a_telemetry` in `dbex/refinement/reconstruction.py` (lines 192-193) applies `log_scale` as an absolute exponent, ignoring the `log_scale_baseline` that Stage A established when calibration metadata is present.

**Root cause:** Missing conditional baseline logic that Stage A (lines 1194-1202) and Stage C (lines 540-547, 612-618, 1241-1246) use.

**Impact:** When `log_scale_baseline ≈ 20.0` (from calibration) and `log_scale` (delta) ≈ 0.0:
- Current broken: `exp(0) = 1.0` → bragg_after ≈ 7.6e-14 (near-zero)
- Correct: `exp(20 + 0) ≈ 4.85e8` → bragg_after ≈ O(1) matching bragg_before

**Spec alignment:** Calibration semantics are normative per TOOLING-VIS-001 Phase D.C and DB-AT-027. Reconstruction helper violated this contract.

**Full diagnosis:** `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T000000Z_galph_phase_d3_fix_diagnosis/root_cause_diagnosis.md`

---

### Implement

**File:** `dbex/refinement/reconstruction.py`
**Function:** `build_final_bragg_from_stage_a_telemetry`
**Lines:** 192-193 (replace with conditional baseline logic, ~192-211 after expansion)

**Exact changes:**

1. **Extract baseline from telemetry** (before line 192):
   ```python
   # Extract log_scale_baseline from Stage A telemetry (TOOLING-VIS-001 Phase D.C, DB-AT-027)
   # When calibration metadata supplied the baseline, apply the same conditional clamp logic as Stage A
   log_scale_baseline_value = param_deltas_a.get('log_scale_baseline', {}).get('final')
   ```

2. **Replace lines 192-193** with conditional clamp + baseline logic:
   ```python
   # Apply Stage A's log-scale clamp logic (matching stage_a.py lines 1194-1202)
   # When calibration metadata is present:
   #   log_scale_baseline = log(sqrt(spot_scale_override)) is the fixed baseline
   #   log_scale is a delta parameter, clamped to ±config.log_scale_max_delta (default ±3)
   #   Final scale = exp(log_scale_baseline + clamped_delta)
   # Otherwise (uncalibrated):
   #   log_scale is the direct learnable parameter, clamped to ±config.log_scale_max_delta_uncalibrated (default ±10)
   #   Final scale = exp(clamped_log_scale)
   max_delta_uncal = getattr(config, "log_scale_max_delta_uncalibrated", 10.0)
   delta_bound = getattr(config, "log_scale_max_delta", 3.0) if log_scale_baseline_value is not None else max_delta_uncal

   if log_scale_baseline_value is not None:
       # Calibrated path: add baseline to clamped delta
       log_scale_baseline_tensor = torch.tensor(log_scale_baseline_value, device=device, dtype=dtype)
       log_scale_delta_clamped = torch.clamp(log_scale, min=-delta_bound, max=delta_bound)
       log_scale_clamped = log_scale_baseline_tensor + log_scale_delta_clamped
   else:
       # Uncalibrated path: clamp absolute log_scale (legacy behavior)
       log_scale_clamped = torch.clamp(log_scale, min=-delta_bound, max=delta_bound)

   scale_factor = torch.exp(log_scale_clamped)
   ```

3. **Device/dtype safety:** Ensure `log_scale_baseline_tensor` uses the same `device` and `dtype` as other tensors in the function (already available as function parameters).

**Pattern reference:** Copy the exact conditional structure from:
- `stage_a.py` lines 1194-1202 (canonical reference)
- `stage_c.py` lines 540-547 (ROI mode)
- `stage_c.py` lines 612-618 (panel mode)
- `stage_c.py` lines 1241-1246 (Stage C final Bragg)

**Scope:** ~20 lines (lines 192-193 replaced with ~192-211 including comments)

**No other changes required:** This is a local bugfix; no imports, no test changes, no other modules touched.

---

### Validation

Run the blocked acceptance criteria with full detector + metadata sigma source:

```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=metadata \
DBEX_SMOKE_DETECTOR_SIZE=full \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028 \
              tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029 | \
  tee plans/active/ARCH-REFACTOR-001/reports/2025-12-02T000000Z_galph_phase_d3_fix_diagnosis/pytest_db_at_028_029.log
```

**Expected outcome:** Both tests PASS
- `bragg_after_mean ≈ O(1)` (not near-zero)
- `chi²/pixel initial ≤ 1e2` (bound satisfied)
- `median ROI correlation after ≥ 0.1` (passing gate)

**Capture metrics:**
```bash
python -c "
import json
import h5py

# Extract metrics from test artifacts (adjust path as needed)
# Example: read bragg_before_mean, bragg_after_mean, chi_sq_pixel from HDF5 diagnostics
# Save as JSON for comparison

metrics = {
    'bragg_before_mean': 1.86,  # from test fixture
    'bragg_after_mean': None,   # extract from passing test run
    'chi_sq_pixel_initial': None,  # extract from passing test
    'log_scale_baseline': None,  # extract from telemetry
    'log_scale_delta': None,     # extract from telemetry
    'scale_factor_applied': None  # extract from debug output
}

# TODO: populate from actual test run
with open('plans/active/ARCH-REFACTOR-001/reports/2025-12-02T000000Z_galph_phase_d3_fix_diagnosis/metrics_comparison.json', 'w') as f:
    json.dump(metrics, f, indent=2)
"
```

---

## How-To Map

### Step 1: Read the function context
```bash
# Read current broken implementation (lines 140-199)
# Focus on lines 192-193 (the bug) and surrounding device/dtype/config context
```

### Step 2: Apply the fix
1. Extract `log_scale_baseline_value` from `param_deltas_a` dict (before line 192)
2. Replace lines 192-193 with the conditional baseline logic shown above (~192-211)
3. Preserve all surrounding code (detector loop, panel shape, simulator setup)

### Step 3: Validate locally
Run the two acceptance tests and verify PASS status:
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=metadata \
DBEX_SMOKE_DETECTOR_SIZE=full \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028 \
              tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029
```

### Step 4: Capture artifacts
- Save pytest output to `pytest_db_at_028_029.log`
- Create `fix_diff.patch` showing the exact changes
- Extract metrics (bragg_after magnitude, chi²/pixel) to `metrics_comparison.json`
- Optional: Add debug print to show `log_scale_baseline_value`, `delta_bound`, `log_scale_clamped` values

---

## Pitfalls To Avoid

1. **Do NOT change test expectations** — Tests are correct; code is broken
2. **Do NOT weaken gates** — This is a bugfix, not a spec_change
3. **Do NOT modify Stage A/B/C** — Fix is local to reconstruction.py only
4. **Preserve device/dtype neutrality** — Use `device` and `dtype` parameters when constructing `log_scale_baseline_tensor`
5. **Match reference pattern exactly** — Copy conditional structure from stage_a.py:1194-1202 verbatim
6. **Do NOT skip telemetry extraction** — Must read `log_scale_baseline` from `param_deltas_a` dict
7. **Handle None/missing baseline gracefully** — When `log_scale_baseline_value is None`, use uncalibrated path (legacy ±10 clamp)
8. **Respect config attributes** — Use `getattr(config, "log_scale_max_delta", 3.0)` and `getattr(config, "log_scale_max_delta_uncalibrated", 10.0)` with defaults
9. **Do NOT add new imports** — All required modules (torch) already imported
10. **Environment Freeze** — Do not install packages; if torch missing, mark blocked (should not happen, torch already available)

---

## If Blocked

1. **Missing telemetry field:** If `param_deltas_a['log_scale_baseline']` does not exist, check Stage A telemetry structure. Field should be present when `calibration_metadata` is provided to Stage A. If missing, escalate (this would be a different bug in Stage A telemetry serialization).

2. **Tests still fail with same signature:** If bragg_after is still near-zero after applying fix:
   - Verify `log_scale_baseline_value` is being extracted correctly (add debug print)
   - Verify conditional branch is taken (add debug print: "Using calibrated path" vs "Using uncalibrated path")
   - Check that `log_scale_baseline_tensor` has expected value (~20.0)
   - Escalate to Galph with debug output; may indicate deeper bug in telemetry payload

3. **Tests fail with different signature:** Capture new failure mode in Attempts History and escalate.

4. **Import errors:** Should not occur (torch already imported). If it does, mark blocked and record error signature.

---

## Findings Applied

**Relevant findings from knowledge base:**
- **TOOLING-VIS-001 Phase D.C** — Log_scale baseline separation for calibrated runs
- **DB-AT-027** — Stage A mapping parity with calibration metadata
- **ARCH-FACTORY-001** — Unified simulator factory (cold path context)
- **GRADIENT-004** — Warm cache path constraints (warm path context)
- **REFINE-015** — Stage C must mirror Stage A's log-scale clamp logic (establishes normative pattern)

**Adherence notes:**
- Fix aligns reconstruction.py with the normative pattern established in Stage A/C (REFINE-015)
- Preserves calibration semantics from TOOLING-VIS-001 Phase D.C and DB-AT-027
- No changes to factory or warm cache logic (ARCH-FACTORY-001, GRADIENT-004 constraints unaffected)

---

## Pointers

**Spec/Architecture:**
- `docs/spec-db-core.md` §§20-40 — Geometry/crystal/calibration contracts
- `docs/architecture/calibration_scaling.md` — ADU↔photon policy, spot_scale threading
- `plans/active/ARCH-REFACTOR-001/implementation.md` — Phase D checklist (D.3 currently in_progress)

**Code References:**
- `dbex/refinement/reconstruction.py:192-193` — Bug location (current broken code)
- `dbex/refinement/stage_a.py:1194-1202` — Canonical reference implementation
- `dbex/refinement/stage_c.py:540-547` — ROI mode reference
- `dbex/refinement/stage_c.py:612-618` — Panel mode reference
- `dbex/refinement/stage_c.py:1241-1246` — Stage C final Bragg reference

**Testing:**
- `docs/TESTING_GUIDE.md` §2 — Authoritative test selectors
- `tests/dbex/test_stage_a_smoke_parity.py:test_db_at_028` — Acceptance criterion 1
- `tests/dbex/test_stage_a_smoke_parity.py:test_db_at_029` — Acceptance criterion 2

**Diagnosis:**
- `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T000000Z_galph_phase_d3_fix_diagnosis/root_cause_diagnosis.md` — Full root cause analysis, spec alignment, lifecycle context

**Fix-Plan:**
- `docs/fix_plan.md` — ARCH-REFACTOR-001 entry (Tier 0, in_progress)
- `problems.md` lines 26-60 — User-supplied diagnosis serviced this loop

---

## Next Up (optional)

If you finish early and both tests pass:
1. Run broader Stage A parity suite to ensure no regressions:
   ```bash
   pytest -vv tests/dbex/test_stage_a_smoke_parity.py --smoke-detector-size=full
   ```

2. Check if any other reconstruction helpers need the same fix:
   - `build_final_bragg_from_stage_b_telemetry` (reconstruction.py:~400) — should already be correct (references Stage B telemetry)
   - `_stage_c_bragg_full` (if still exists) — check if it mirrors Stage C's baseline logic

Do NOT proceed to Phase D.4 or D.5 without explicit approval from Galph.

---

## Doc Sync Plan

**Not required this loop** — No tests added/renamed, no selector changes. Fix is internal to reconstruction.py.

If tests pass, Galph will update:
- `docs/fix_plan.md` — Mark Phase D.3 complete, log attempt with PASS status
- `problems.md` — Check off ledger entry (lines 26-60) with resolution summary
- `galph_memory.md` — Record loop outcome, artifact path, next action (Phase D.4)

---

## Mapped Tests Guardrail

Both selectors collect >0 tests:
```bash
pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028
pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029
```

Expected: 1 test each (2 total). If 0, report collection failure.

---

## Normative Math/Physics

**Do NOT paraphrase spec equations.** Refer to exact spec sections:
- Calibration baseline semantics: `docs/spec-db-core.md` §§20-40
- Log_scale delta clamping: `docs/architecture/calibration_scaling.md` (TOOLING-VIS-001 Phase D.C)
- Variance-weighted loss (not directly affected by this fix): `docs/spec-db-core.md` §§57-68

Ralph should read these sections directly if math/physics questions arise.
