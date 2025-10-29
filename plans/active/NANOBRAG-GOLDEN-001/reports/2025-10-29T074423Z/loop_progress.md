# NANOBRAG-GOLDEN-001 Loop Progress (2025-10-29T074423Z)

## Status: IN_PROGRESS

## Tasks Completed

### A2: DiffBragg Forward Capture Setup
- **Status**: IN_PROGRESS (refinement running in background)
- **Actions Taken**:
  1. Copied capture_forward.py, capture_torch_only.py from 2025-10-29T063817Z report
  2. Copied legacy dbex_diffbragg_gpu.h5 from 2025-10-29T063817Z report
  3. Created golden_dataset directory structure (logs/, legacy/full_panel/, metrics/)
  4. **BLOCKER IDENTIFIED**: MTZ conversion bug in capture_forward.py
     - Root cause: Famps numpy array passed to customized_copy, which expects flex.double
     - Error: `RuntimeError: Conversion of given type of miller_array to MTZ format is not supported.`
  5. **PATCH APPLIED** (per Environment Freeze exception policy):
     - Added `from scitbx.array_family import flex` import
     - Convert Famps to flex.double before customized_copy: `Famps_flex = flex.double(Famps)`
     - Documented in patch file: `capture_forward_mtz_flex.patch`
  6. Re-launched corrected capture_forward.py with KMP_DUPLICATE_LIB_OK=TRUE
  7. Refinement is progressing through macro cycles (observed 5+ cycles planned)

- **Artifacts**:
  - `capture_forward_mtz_flex.patch`: Documents flex.double conversion fix
  - `golden_dataset/logs/diffbragg_forward_corrected.log`: Live capture log (background job af1e3a)

### Pending Tasks

#### A3: Torch-Only Capture
- **Status**: BLOCKED (waiting for A2 DiffBragg capture to complete)
- **Requirements**: DiffBragg baseline tensors from A2

#### D1: Test Execution and Doc Sync
- **Status**: PENDING
- **Requirements**: Both A2 and A3 captures complete, canonical tensors staged

## Environment State
- **Python**: 3.9.23
- **torch**: 2.4.1+cu121
- **CUDA**: Available (GeForce RTX 3090, driver 570.195.03)
- **simtbx**: Patched (diffBraggCUDA.cu:708 fix applied in prior loop 2025-10-29T073200Z)
- **nanobrag_torch**: 0.1.0
- **Environment Freeze**: Compliant (no package installs/upgrades)

## Findings

### New Finding: MTZ-FLEX-001 (Candidate)
- **ID**: MTZ-FLEX-001
- **Tags**: configuration, mtz, flex-arrays, cctbx
- **Summary**: miller_array.customized_copy requires flex.double data arrays, not numpy.ndarray. Pass numpy arrays through `flex.double(arr)` conversion before calling customized_copy to avoid MTZ write failures.
- **Source**: capture_forward.py:174-179 (patched)
- **Status**: fix_applied
- **Rationale**: capture_forward.py accumulates refined amplitudes in a numpy array (Famps), then attempts to create a new miller_array via customized_copy. The cctbx/iotbx MTZ writer expects scitbx.array_family.flex types for all data/sigma arrays. Without conversion, as_mtz_dataset raises RuntimeError about unsupported conversion.

## Next Actions (Once A2 Completes)
1. Verify diffbragg_forward_corrected.log shows successful refinement completion
2. Confirm full-panel tensors written to golden_dataset/legacy/full_panel/
3. Execute capture_torch_only.py to generate canonical [panel, slow, fast] tensors
4. Run DB_AT_001 parity and forward equivalence selectors
5. Capture collect-only logs for both selectors
6. Update docs/TESTING_GUIDE.md §2.1 and docs/development/TEST_SUITE_INDEX.md
7. Add MTZ-FLEX-001 to docs/findings.md
8. Update fix_plan.md Attempts History with metrics and artifacts

## Time Estimate
- A2 DiffBragg capture: ~5-10 minutes remaining (based on prior 2101-iteration runs)
- A3 Torch capture: ~2-3 minutes
- D1 Test execution: ~2 minutes
- D1 Doc sync: ~1 minute
- Total remaining: ~10-16 minutes

## Risks
- If diffBragg refinement fails mid-cycle (unlikely given patched simtbx), will need to investigate
- Torch capture depends on DiffBragg outputs being in expected format
