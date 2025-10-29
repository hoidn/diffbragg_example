# NANOBRAG-GOLDEN-001 Loop Summary — 2025-10-29T055449Z

## Objective
Frame an Environment Freeze–compliant recovery plan for NANOBRAG-GOLDEN-001 by diagnosing the diffBragg CUDA free() failure and staging a CPU fallback capture for the canonical dataset.

## Mode
Docs (analysis-focused, no code changes)

## Tasks Executed

### Task A2.1: CUDA Source Inspection
**Status**: BLOCKED — Source file unavailable

- Attempted to extract `../easyBragg/simtbx_project/simtbx/diffBragg/src/diffBraggCUDA.cu` lines 680-725
- **Finding**: File does not exist in filesystem
- **Impact**: Cannot perform direct source-level debugging of `cudaFree(cp.cu_sourceI_scale)` assertion at line 708

**Hypotheses Documented**:
1. Double-free hypothesis (pointer lifecycle bug)
2. Resource lifetime hypothesis (cleanup after refinement convergence)
3. CUDA version compatibility hypothesis (compiled extensions vs runtime mismatch)

**Recommendation**: Source-level debugging requires either simtbx source access, DiffBragg maintainer consultation, or alternative capture path.

### Task A2.2: Environment Status Logging
**Status**: COMPLETE — Environment bootstrap missing simtbx

**Executed**:
```bash
source setup_env.sh
dbex_status
```

**Environment Validation Results**:
- ✓ `simforge/envs/simtbx` conda environment now exists (unlike prior loops where simforge/ was absent)
- ✓ Environment activation successful
- ✓ GPU detected: NVIDIA GeForce RTX 3090, driver 570.195.03
- ✓ dbex package installed and importable
- ✗ simtbx NOT installed (CRITICAL blocker)
- ✗ dials NOT installed (CRITICAL blocker)
- ⚠ xfel optional (not present)
- ⚠ score_trainer optional (not present)

**Critical Finding**: Under Environment Freeze policy, simtbx/dials installation is prohibited. All DiffBragg baseline capture paths (GPU and CPU) remain blocked.

**Artifacts**: `env_status.log`

### Task A2.3: CPU Fallback Capture
**Status**: BLOCKED — simtbx unavailable

**Attempted**:
```python
from dbex.data_load import DataLoad
from dbex.run_diffbragg import run_diffbragg
# ...
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

**Artifacts**: `golden_dataset/legacy/diffbragg_cpu_attempt.log`

### Doc Sync: Collect-Only Logs
**Status**: PARTIAL — Parity tests OK, forward equivalence tests blocked

**DB_AT_001 Parity Selector** (`test_db_at_001_parity.py`):
- ✓ 14 tests collected successfully in 0.23s
- ✓ Tests do NOT depend on simtbx (use fallback golden dataset loader)
- ✓ TESTING-003 compliance: Active selector has >0 tests
- **Artifact**: `collect_db_at_001_parity.log`

**DB_AT_001 Forward Equivalence Selector** (`test_forward_equivalence_complete.py`):
- ✗ Collection error: ModuleNotFoundError: No module named 'simtbx'
- ✗ test_forward_equivalence_complete.py imports dbex.data_load which requires simtbx.diffBragg
- ✗ 0 tests collected, 1 collection error
- ✗ TESTING-003 violation: Active selector cannot collect tests
- **Artifact**: `collect_db_at_001_forward.log`

**Documentation Updates Applied**:
- `docs/TESTING_GUIDE.md` §2.1: Downgraded "Forward equivalence (DB_AT_001)" selector from Active → Planned with BLOCKED status and blocker explanation
- `docs/development/TEST_SUITE_INDEX.md`: Updated both module table and acceptance profile table with blocked status, new collection log references, and TESTING-003 citation
- Updated "Parity harness (DB_AT_001)" collection log references to point to new artifact location (2025-10-29T055449Z)

## Metrics Summary

| Metric | Value |
|--------|-------|
| Do Now tasks attempted | 3/3 |
| CUDA source extracts succeeded | 0/1 (file not found) |
| Env validations completed | 1/1 (simtbx/dials missing) |
| CPU baseline exports succeeded | 0/1 (ModuleNotFoundError) |
| Collect-only commands successful | 1/2 (14 parity tests, 0 forward tests) |
| Artifact files generated | 6 |
| Documentation files updated | 2 |

## Artifacts Generated

1. `planning_notes.md` — Comprehensive task execution notes, hypotheses, recommendations
2. `diffBraggCUDA_free_segment.log` — Empty (source file not found)
3. `env_status.log` — dbex_status output showing simtbx ✗, dials ✗
4. `golden_dataset/legacy/diffbragg_cpu_attempt.log` — ModuleNotFoundError trace
5. `collect_db_at_001_parity.log` — 14 tests collected successfully
6. `collect_db_at_001_forward.log` — 0 tests collected, 1 import error
7. `loop_summary.md` — This document

## Critical Blocker

**Environment Freeze + missing simtbx/dials**

Under the Environment Freeze key policy (CLAUDE.md), runtime toolchain modifications are prohibited during loops. The current environment lacks simtbx and dials packages, both critical dependencies for:
- DataLoad (dbex/data_load.py imports simtbx.diffBragg.utils)
- DiffBragg baseline capture (GPU and CPU paths)
- test_forward_equivalence_complete.py test collection

## Recommendations for Supervisor

### 1. Environment Decision (Choose One Path)

**Option A**: Grant Environment Freeze Exception
- Allow one-time bootstrap installation of simtbx/dials in simforge/envs/simtbx
- Unblocks Phase A2 (DiffBragg baseline capture)
- Requires external coordination or bootstrap script

**Option B**: Torch-Only Dataset (Skip DiffBragg Baseline)
- Accept that DiffBragg baseline capture is impossible
- Proceed directly to Phase A3 (nanoBragg2 forward capture)
- Generate torch-only canonical dataset with synthetic target tensors for initial parity validation
- Update implementation plan to skip Phase A2

**Option C**: Defer Initiative
- Pause NANOBRAG-GOLDEN-001 until external environment is provisioned with simtbx/dials
- Continue with other initiatives that don't require DiffBragg

### 2. Testing Documentation (COMPLETED)

✓ Marked `test_forward_equivalence_complete.py` selector as "Planned" instead of "Active" in both:
- `docs/TESTING_GUIDE.md` §2.1
- `docs/development/TEST_SUITE_INDEX.md` (module and acceptance profile tables)

Per TESTING-003 requirements, selectors with 0 tests collected due to import errors must be downgraded from Active status. Documentation now accurately reflects the blocker with collection log references.

### 3. Alternative Path Exploration

If nanobrag_torch is available (previous loop 2025-10-29T030352Z confirmed version 0.1.0 installed), consider:
- Skipping DiffBragg baseline entirely
- Generating torch-only golden dataset using existing nanobrag_torch installation
- Creating synthetic target tensors for initial parity validation
- Revisiting DiffBragg comparison after environment resolution

## Spec Compliance Notes

- `docs/spec-db-core.md:20-41` — Canonical tensors must preserve `[panel, slow, fast]` ordering
- `docs/spec-db-conformance.md:23-26` — DB_AT_001 acceptance requires trustworthy DiffBragg baseline (currently blocked)
- `docs/forward_equivalence.md:21-55` — Phase 1 mandates paired DiffBragg/torch artifacts with metrics (DiffBragg side blocked)
- `docs/nanobrag_api.md:21-83` — Simulator config mappings must align with dxtbx metadata
- `docs/findings.md#CONFIG-001` — Detector/beam/crystal normalization enforced
- `docs/findings.md#TESTING-003` — Selector status transitions require >0 tests collected (compliance maintained)

## Next Actions for Galph

1. **Review recommendations** and choose environment decision path (A, B, or C)
2. **Update input.md** with chosen path and Environment Freeze-compliant Do Now tasks
3. **Consider alternative approach**: If Option B (torch-only), authorize Phase A3 execution independently of Phase A2
4. **Update implementation plan** (`plans/active/NANOBRAG-GOLDEN-001/implementation.md`) to reflect chosen path and mark A2 as blocked or skipped

## Status Transition

- **Before Loop**: NANOBRAG-GOLDEN-001 status = in_progress, Phase A2 pending
- **After Loop**: NANOBRAG-GOLDEN-001 status = in_progress (blocked on environment decision), Phase A2 blocked pending supervisor decision, documentation synchronized per TESTING-003
