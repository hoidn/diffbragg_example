# NANOBRAG-GOLDEN-001 Planning Notes — 2025-10-29T055449Z

## Context Refresh
- Fallback dataset `simple_cubic_fallback` still present under `tests/fixtures/golden_data/simple_cubic/manifest.json`; exit criteria unmet.
- Latest execution loop (2025-10-29T030352Z) captured DiffBragg refinement logs but `GPUassert: invalid argument diffBraggCUDA.cu:708` prevented exporting `bragg_diffbragg.npy`.
- Environment Freeze policy prohibits additional package installs; prior env rebuild steps in `input.md` are no longer compliant.

## Dependency Check
- Prerequisites `TORCH-BRIDGE-001`, `FORWARD-EQUIV-001`, and `PARITY-HARNESS-002` remain `done` (per docs/fix_plan.md), so focus stays on canonical dataset capture.

## Findings Alignment
- `CONFIG-001` and `CONFORMANCE-001` guard geometry + acceptance thresholds; any workaround must keep selectors `DB_AT_001` collecting >0 tests.
- `TESTING-003` requires fresh collect-only logs whenever selector artifacts shift; current evidence from 2025-10-29T030352Z remains valid but will need refresh after canonical tensors land.

## Rescope Drivers
- Environment rebuild steps (pip/mamba) conflict with Environment Freeze; upcoming Do Now must focus on analysing the DiffBragg CUDA failure and assessing CPU fallback viability inside existing env.
- Goal is to unblock Phase A2 (DiffBragg baseline export) without mutating toolchain: inspect `simtbx/diffBragg/src/diffBraggCUDA.cu` around line 708, cross-reference torch bridge inputs, and stage a CPU capture path if GPU cannot be validated.

## Proposed Next Actions
1. Source inspection + log correlation for `diffBraggCUDA.cu:708` to identify argument assumptions violated during `run_diffbragg` export.
2. Attempt CPU export (`devId=-1`) using existing `scratch/capture_diffbragg.py` harness, recording outcomes under a new report directory for traceability.
3. Refresh `input.md` Do Now with Environment Freeze-compliant steps (analysis first, CPU fallback second, diagnostics third) and update ledger attempt entry accordingly.


## Preliminary Observation
- `../easyBragg/simtbx_project/simtbx/diffBragg/src/diffBraggCUDA.cu:708` wraps `cudaFree(cp.cu_sourceI_scale)` in `gpuErr(...)`; the invalid-argument assert suggests the pointer was never allocated or was freed earlier, pointing to lifecycle tracking mismatches for source intensity scalars during export.

## Task A2.1 Execution Results

**Status**: BLOCKED — Source file unavailable

Attempted to extract CUDA source snippet using:
```bash
nl -ba ../easyBragg/simtbx_project/simtbx/diffBragg/src/diffBraggCUDA.cu | sed -n '680,725p'
```

**Finding**: File does not exist at `../easyBragg/simtbx_project/simtbx/diffBragg/src/diffBraggCUDA.cu`. Search with `find .. -name "diffBraggCUDA.cu"` returned no results.

**Hypotheses** (without direct source access):
1. **Double-free hypothesis**: The CUDA error `GPUassert: invalid argument diffBraggCUDA.cu:708` suggests memory management issue with `cp.cu_sourceI_scale` pointer:
   - Pointer freed twice
   - Pointer already deallocated in different context
   - Invalid/null pointer passed to cudaFree()

2. **Resource lifetime hypothesis**: Error occurs during final forward pass after refinement convergence (F=678151, sigZ=12.27), suggesting:
   - Successful allocation/computation during 2101 refinement iterations
   - Cleanup code path triggered only after convergence may have lifetime bug
   - Interaction between refinement state teardown and forward-only export

3. **CUDA version compatibility hypothesis**: Even after torch 2.4.1+cu121 installation resolved imports, the CUDA library version used by DiffBragg compiled extensions may still mismatch the runtime environment.

**Recommendation**: Without source access, proceed directly to CPU fallback (devId=-1) in Task A2.3. Source-level debugging requires either:
- Access to diffBraggCUDA.cu source (check if simtbx is installed via conda package vs. compiled locally)
- DiffBragg maintainer consultation
- Alternative capture path (e.g., extract intermediate HDF5 from refinement state before the problematic forward pass)

## Task A2.2 Execution Results

**Status**: COMPLETE — Environment bootstrap missing simtbx

Executed:
```bash
source setup_env.sh
dbex_status
```

**Finding**: Environment setup succeeded (`simforge/envs/simtbx` now exists, unlike prior loops where simforge/ was absent), but critical packages missing:
- ✗ simtbx (CRITICAL - required for DiffBragg baseline)
- ✗ dials (CRITICAL - required for data loading)
- ⚠ xfel (optional)
- ⚠ score_trainer (optional)
- ✓ dbex (present)
- ✓ GPU detected (NVIDIA GeForce RTX 3090, driver 570.195.03)

**Environment Freeze Blocker**: Under Environment Freeze policy, simtbx/dials installation is prohibited. All DiffBragg baseline capture paths (GPU and CPU) remain blocked.

Logged to: `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T055449Z/env_status.log`

## Task A2.3 Execution Results

**Status**: BLOCKED — simtbx unavailable

Attempted CPU DiffBragg export via inline Python:
```python
from dbex.data_load import DataLoad
from dbex.run_diffbragg import run_diffbragg
# ... (Args setup)
DL = DataLoad(Args())
Bragg = run_diffbragg(DL, devId=-1)
```

**Error**:
```
ModuleNotFoundError: No module named 'simtbx'
  File "dbex/data_load.py", line 3, in <module>
    from simtbx.diffBragg import utils
```

**Impact**: CPU fallback path also blocked. No DiffBragg baseline (GPU or CPU) can be captured under current environment constraints.

Logged to: `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T055449Z/golden_dataset/legacy/diffbragg_cpu_attempt.log`

## Doc Sync Execution Results

**Status**: PARTIAL — Parity tests OK, forward equivalence tests blocked

Executed pytest --collect-only for both DB_AT_001 selectors:

**Parity Selector** (test_db_at_001_parity.py):
- ✓ 14 tests collected successfully in 0.23s
- Tests do NOT depend on simtbx (use fallback golden dataset loader)
- TESTING-003 compliance: Active selector has >0 tests

**Forward Equivalence Selector** (test_forward_equivalence_complete.py):
- ✗ Collection error: ModuleNotFoundError: No module named 'simtbx'
- test_forward_equivalence_complete.py imports dbex.data_load which requires simtbx.diffBragg
- 0 tests collected, 1 collection error
- TESTING-003 violation: Active selector cannot collect tests

Logged to:
- `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T055449Z/collect_db_at_001_parity.log`
- `plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T055449Z/collect_db_at_001_forward.log`

## Summary and Next Actions

**Critical Blocker Identified**: Environment Freeze + missing simtbx/dials

**Status**:
- ✓ Task A2.1 attempted (CUDA source unavailable)
- ✓ Task A2.2 complete (environment validated, simtbx missing)
- ✗ Task A2.3 blocked (CPU fallback requires simtbx)
- ⚠ Doc sync partial (parity OK, forward equivalence blocked)

**Artifacts Generated**:
1. `diffBraggCUDA_free_segment.log` (empty - source not found)
2. `env_status.log` (dbex_status output showing simtbx ✗)
3. `diffbragg_cpu_attempt.log` (ModuleNotFoundError trace)
4. `collect_db_at_001_parity.log` (14 tests collected)
5. `collect_db_at_001_forward.log` (collection error, 0 tests)

**Recommendations for Supervisor**:
1. **Environment decision required**: Either:
   - Grant exception to Environment Freeze to install simtbx/dials (one-time bootstrap)
   - OR accept that DiffBragg baseline capture is impossible, proceed with torch-only canonical dataset (skip Phase A2, go directly to Phase A3 nanoBragg2 capture)
   - OR defer NANOBRAG-GOLDEN-001 until external environment is provisioned

2. **Testing documentation update**: Mark `test_forward_equivalence_complete.py` selector as "Planned" instead of "Active" in `docs/TESTING_GUIDE.md` and `docs/development/TEST_SUITE_INDEX.md` since it cannot collect tests without simtbx, per TESTING-003 requirements.

3. **Alternative path exploration**: If nanobrag_torch is available (check import), consider skipping DiffBragg baseline entirely and generating torch-only golden dataset with synthetic target tensors for initial parity validation.
