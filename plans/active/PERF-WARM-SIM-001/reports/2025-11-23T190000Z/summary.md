### Turn Summary
Fixed engine delegation telemetry routing blockers unblocking PERF-WARM-SIM-001 Phase D validation; three related issues resolved (telemetry key mapping, engine_inputs structure, Stage C enrichment).
Both test_stage_a_expansion and test_stage_c_detector_microslip now execute without KeyErrors (previously blocked by missing 'refinement_inputs' and 'stage_a_telemetry' keys).
Next: Stage C shows chi-squared mismatch (assertion failure, not a routing blocker); issue escalated to Galph for investigation.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-23T190000Z/ (pytest_stage_a_expansion.log, pytest_stage_c_full.log, summary.md)

## Previous Turn Summary (Galph Planning)
Diagnosed and scoped trivial 5-line fix for engine delegation telemetry key mismatch blocking PERF-WARM-SIM-001 Phase D validation.
Ralph's Phase D detector reuse implementation (commit 1bdeca3, D1-D3 tasks) is code-complete and correct; blocker is ARCH-REFINE-FLOW-001 Phase E regression where commit 9bbd1e8 enabled engine delegation for all smoke tests but telemetry returns lowercase stage names while tests expect uppercase keys.
Next: Ralph applies mapping dict `stage_name_map = {"stage_a": "A", "stage_b": "B", "stage_c": "C"}` at line 4489 + mapping logic at line 4494, validates with test_stage_c_detector_microslip (primary blocker) and test_stage_a_expansion (regression guard).
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-23T190000Z/ (input.md supervisor handoff)

---

## Blocker Resolution Details

### Issues Found and Fixed (3 blockers, not just telemetry keys)

**Issue 1: Telemetry Key Mapping (Galph's diagnosis)**
- **Location:** `dbex/nanobrag_refinement.py:4487-4497`
- **Problem:** Engine returns lowercase stage names ("stage_a"), tests expect uppercase ("A")
- **Fix:** Added mapping dict + applied at line 4496-4497
- **Validation:** Both tests now receive correct uppercase keys

**Issue 2: Engine Inputs Structure Bug (discovered during fix)**
- **Location:** `dbex/nanobrag_refinement.py:4438-4448`
- **Problem:** engine_inputs dict decomposed RefinementInputs into fields, but stages expect `inputs['refinement_inputs']` namedtuple
- **Symptom:** `KeyError: 'refinement_inputs'` at stage_a.py:107
- **Fix:** Wrapped inputs as `"refinement_inputs": inputs` (line 4440)
- **Validation:** Stage A now executes successfully

**Issue 3: Stage C Enrichment Missing (discovered during Stage C test)**
- **Location:** `dbex/refinement/engine.py:104-120`
- **Problem:** Engine only enriched Stage B with stage_a_telemetry, not Stage C
- **Symptom:** `KeyError: 'stage_a_telemetry'` at stage_c.py:114
- **Fix:** Extended enrichment to Stage C (line 107) + added stage_b_telemetry (lines 117-120)
- **Validation:** Stage C now receives required telemetry dicts

### Test Results

**test_stage_a_expansion (regression guard):**
- Status: ✓ PASSED (17.99s)
- Telemetry keys: "A" (correct uppercase)
- No KeyErrors

**test_stage_c_detector_microslip (primary blocker):**
- Status: ✗ FAILED (72.56s) - NEW failure mode
- Telemetry keys: "A", "C" (correct uppercase)
- Routing: ✓ Both stages execute without KeyErrors
- **New issue:** Chi-squared mismatch assertion
  - `Stage C initial chi²: 2.918e+08`
  - `Stage A final chi²: 2.909e+08`
  - Tolerance: ±2.9e+05 (0.1%)
  - Actual gap: 0.94e+06 (0.32%)
  - **NOT a routing blocker** - Stage C implementation validation issue

### Phase D Validation Status

**UNBLOCKED:** Engine delegation routing now works correctly
- Telemetry keys map properly (lowercase → uppercase)
- Engine inputs structured correctly (RefinementInputs wrapped)
- Stage enrichment propagates prior telemetry (A→C, A→B→C workflows)

**NEW BLOCKER (separate issue):** Stage C chi-squared initialization mismatch
- This is an implementation bug in Stage C detector reuse logic
- NOT related to telemetry routing infrastructure
- Requires investigation of Stage C context initialization (detector states, cached HKL grids)

### Files Modified

1. `dbex/nanobrag_refinement.py` (2 changes):
   - Lines 4489-4490: Telemetry key mapping dict
   - Lines 4496-4497: Applied mapping
   - Line 4440: Fixed engine_inputs structure

2. `dbex/refinement/engine.py` (1 change):
   - Lines 107, 117-120: Stage C enrichment

### Recommendation for Galph

The original blocker (telemetry routing) is **resolved**. A new blocker emerged (Stage C chi-squared mismatch) that requires separate investigation:

**Option A (Debug Stage C):** Investigate why Stage C initial chi² != Stage A final chi²
- Likely causes: Detector state not preserved, HKL grid not cloned, param_values mismatch
- Estimated effort: 1-2 loops (debugging + fix)

**Option B (Defer Stage C validation):** Mark Phase D as "routing unblocked, Stage C validation pending"
- Commit current fixes (routing works, tests execute)
- Open new initiative for Stage C chi-squared investigation
- Ralph can proceed with other tasks

**Option C (Partial Phase D completion):** Accept Stage A-only engine delegation as Phase D deliverable
- Stage A engine delegation: ✓ WORKS
- Stage C engine delegation: ✗ BLOCKED by chi-squared mismatch
- Mark Phase D as "partial complete" per CLAUDE.md incremental progress principles
