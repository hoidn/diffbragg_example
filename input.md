# Phase C0 — Baseline Stage B Artifacts Collection

## Summary
Collect baseline Stage B artifacts (test_stage_b_shell_modifiers smoke test with small detector) before Phase C extraction begins.

## Mode
none (evidence collection)

## Focus
ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine (Phase C0 baseline)

## Branch
integration

## Mapped Tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` (smoke, small detector)
- Collection verification: `pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers`

## Artifacts
`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T061726Z/baseline/`

## Do Now

Execute Phase C0 baseline artifact collection (mirror Phase B0 pattern from loop i=192):

1. **Create artifacts directory:**
   ```bash
   mkdir -p plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T061726Z/baseline
   cd plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T061726Z/baseline
   ```

2. **Collection verification:**
   ```bash
   pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
     > pytest_collect_stage_b.log 2>&1
   ```
   - Verify `1 test collected` in log
   - Archive log in baseline/

3. **Run Stage B smoke test (small detector):**
   ```bash
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
     -v --tb=short --smoke-detector-size=small \
     > pytest_stage_b_small.log 2>&1
   ```
   - Capture exit code
   - Archive full log in baseline/

4. **Extract telemetry (if test PASSED):**
   ```bash
   python3 -c "
   import json
   import h5py
   import sys

   try:
       with h5py.File('output/torch_refine_smoke_small.h5', 'r') as f:
           if 'torch_diagnostics' in f:
               telem = dict(f['torch_diagnostics'].attrs)
               # Extract Stage B telemetry if present
               if 'refinement_telemetry' in f:
                   ref_telem = json.loads(f['refinement_telemetry'].attrs.get('json', '{}'))
                   if 'B' in ref_telem:
                       stage_b_telem = ref_telem['B']
                       print(json.dumps(stage_b_telem, indent=2))
                       with open('plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T061726Z/baseline/telemetry_stage_b_small.json', 'w') as out:
                           json.dump(stage_b_telem, out, indent=2)
                       sys.exit(0)
           print('No Stage B telemetry found', file=sys.stderr)
           sys.exit(1)
   except Exception as e:
       print(f'Error extracting telemetry: {e}', file=sys.stderr)
       sys.exit(1)
   "
   ```
   - Archive telemetry JSON in baseline/

5. **Write baseline summary:**
   Create `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T061726Z/baseline/summary.md` with:
   - Test result (PASS/FAIL)
   - Exit code
   - Key Stage B telemetry metrics (if available):
     - status ("ok"/"early_stop"/"error")
     - improvement (Stage B final vs Stage A final)
     - shell modifier deltas
     - perf_counters (cache_mode, roi_mode, ROI counts)
   - File sizes and paths

6. **Update implementation.md:**
   Mark Phase C0 baseline COMPLETE in `plans/active/ARCH-REFINE-FLOW-001/implementation.md` line ~179:
   ```markdown
   - [x] C0: Baseline Stage B artifacts (small-detector run + telemetry) recorded before refactor. ✓ COMPLETE (2025-11-23T061726Z)
   ```

7. **Write Turn Summary:**
   Append to `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T061726Z/summary.md`:
   ```markdown
   ### Turn Summary
   Collected baseline Stage B artifacts for Phase C extraction (test_stage_b_shell_modifiers smoke small detector).
   Test result: [PASS/FAIL]. Stage B telemetry: [status, improvement, shell modifiers].
   Next: Galph plans Phase C1a-loop1 (extract `_build_stage_b_params` helper ~140 lines).
   Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T061726Z/baseline/ (pytest_collect_stage_b.log, pytest_stage_b_small.log, telemetry_stage_b_small.json, summary.md)
   ```

8. **Commit:**
   ```bash
   git add plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T061726Z/baseline/
   git add plans/active/ARCH-REFINE-FLOW-001/implementation.md
   git commit -m "ARCH-REFINE-FLOW-001 Phase C0: Stage B baseline artifacts — tests: [result]"
   git push
   ```

## How-To Map

```bash
# Step 1: Create artifacts directory
mkdir -p plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T061726Z/baseline
cd plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T061726Z/baseline

# Step 2: Collection verification
pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers > pytest_collect_stage_b.log 2>&1
grep -E "1 test collected|test_stage_b_shell_modifiers" pytest_collect_stage_b.log

# Step 3: Run Stage B smoke (small detector)
cd /home/ollie/Documents/diffbragg_example
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
  -v --tb=short --smoke-detector-size=small \
  > plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T061726Z/baseline/pytest_stage_b_small.log 2>&1
echo "Exit code: $?"

# Step 4: Extract telemetry (run Python snippet from project root)
# (See Do Now step 4 for Python code)

# Step 5: Write baseline/summary.md
# (Manual - summarize test results + telemetry metrics)

# Step 6: Update implementation.md
# (Mark C0 COMPLETE)

# Step 7: Write Turn Summary to summary.md
# (Prepend to plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T061726Z/summary.md)

# Step 8: Commit and push
git add plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T061726Z/
git add plans/active/ARCH-REFINE-FLOW-001/implementation.md
git commit -m "ARCH-REFINE-FLOW-001 Phase C0: Stage B baseline artifacts — tests: [result from step 3]"
git push
```

## Pitfalls To Avoid

1. **Environment:** Freeze enforced. Do not install/upgrade packages. If missing dependencies block, record error signature in fix_plan.md and mark blocked.
2. **Test collection:** MUST verify `1 test collected` before running pytest. If 0 collected, selector is broken—document and escalate to Galph.
3. **Telemetry extraction:** HDF5 path may differ. Check actual output path from pytest log (look for "Writing HDF5" or similar).
4. **Device/dtype neutrality:** Stage B uses CPU fallback for canonical runs (PERF-WARM-011/012). Small detector may run on CUDA—both modes are valid.
5. **Shell modifier gate:** Stage B improvement is effectively zero (~6.4e-8% per REFINE-008). Status "early_stop" with <1e-6 improvement is EXPECTED and CORRECT.
6. **Baseline detector:** Stage B test may not use baseline_detector arg—check test harness. Baseline artifact collection is for CODE snapshot, not geometry verification.
7. **Turn Summary persistence:** Write Turn Summary block to both your response AND `plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T061726Z/summary.md` (prepend, not append).

## If Blocked

**Scenario A: Test FAILS**
- Archive full pytest log + traceback
- Extract error signature (last 50 lines)
- Create `baseline/blocker.md` with:
  - Failure mode (exception type, line number)
  - Suspected root cause
  - Minimal repro steps
- Mark Phase C0 BLOCKED in implementation.md
- Commit artifacts and blocker doc
- Summarize in Turn Summary

**Scenario B: Collection returns 0 tests**
- Verify selector syntax: `test_stage_b_shell_modifiers` (no typo)
- Check if test was renamed/moved
- Document in blocker.md
- Escalate to Galph

**Scenario C: HDF5 telemetry missing**
- Stage B may not emit HDF5 in current code
- Archive pytest log showing test completion
- Note in summary.md: "Telemetry extraction deferred—HDF5 path TBD"
- Proceed with C0 COMPLETE (pytest log is sufficient baseline)

## Findings Applied

- **REFINE-005**: Stage B requires halo-padded HKL grid (hkl_metadata['has_halo']=True) — baseline should enforce or document if missing
- **REFINE-008**: Stage B shell modifier ±1% gate, ~6.4e-8% improvement ceiling — early_stop is EXPECTED
- **PHYSICS-LOSS-001/002**: Variance-weighted loss + sigma_floor guard — telemetry should show variance_floor_clamp_fraction
- **PERF-WARM-011/012**: CPU fallback for canonical (full detector), CUDA for small — cache_mode/roi_mode in perf_counters
- **CONFORMANCE-001**: KMP_DUPLICATE_LIB_OK=TRUE environment flag required
- **RUNTIME-001**: NANOBRAGG_DISABLE_COMPILE=1 for gradient/test stability
- **TESTING-003**: Collection verification mandatory before pytest run

## Pointers

- **Implementation plan:** plans/active/ARCH-REFINE-FLOW-001/implementation.md:179 (Phase C0 checklist)
- **Phase B baseline reference:** plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T030000Z/baseline/ (pattern to mirror)
- **Stage B contract:** docs/spec-db-workflow.md:31-34 (shell modifiers)
- **Test harness:** tests/dbex/test_torch_refine_smoke.py:660-900 (test_stage_b_shell_modifiers)
- **Stage B inline code:** dbex/nanobrag_refinement.py:2527-3137 (extraction target for Phase C1a)
- **Findings ledger:** docs/findings.md (REFINE-005/008, PERF-WARM-011/012, PHYSICS-LOSS-001/002)
- **Test registry:** docs/TESTING_GUIDE.md §2, docs/development/TEST_SUITE_INDEX.md

## Next Up

If C0 baseline collection succeeds:
- Galph will plan C1a-loop1 (extract `_build_stage_b_params` helper ~140 lines)
- Similar to Phase B1a-loop1 pattern (extract one helper, verify compilation, no regression guard until all helpers wired)

If C0 blocked:
- Document blocker in baseline/blocker.md
- Galph reviews and decides escalation path (debug/simplify/defer)
