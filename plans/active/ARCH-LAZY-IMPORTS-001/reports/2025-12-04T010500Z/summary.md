# ARCH-LAZY-IMPORTS-001 Phase B.3 Stage Wrapper Cleanup — 2025-12-04T010500Z

## Objective
Hoist inline imports from Stage A/C LBFGS closure bodies to module scope per ARCH-ENGINE-002 eager-import hygiene, eliminating per-iteration import overhead.

## Changes Made

### dbex/refinement/stage_a.py
- **Module scope additions** (lines 25-52):
  - Added `json`, `os`, `sys` imports
  - Added config factory imports: `create_detector_config`, `create_beam_config`, `create_crystal_config` from `dbex.refinement.config_factories`
  - Added `compute_baseline_misset_deg` from `dbex.nanobrag_bridge`

- **Inline imports removed**:
  - Line 207: Removed `import os` from panel diagnostics block
  - Lines 749-750: Removed `import json` and `from pathlib import Path` from telemetry JSON writer
  - Line 757: Removed `import sys` from exception handler
  - Lines 822-823: Removed `import json` and `from pathlib import Path` from lifecycle JSON writer
  - Line 833: Removed `import sys` from exception handler

### dbex/refinement/stage_c.py
- **Module scope additions** (lines 25-26):
  - Added `os` import (already had `math` at module scope)

- **Inline imports removed**:
  - Line 209: Removed `import os` from panel diagnostics block
  - Lines 233-235: Removed `Detector`, `Crystal`, `Simulator`, and config factory imports from `compute_loss_stage_c` (added comment noting module-scope location)
  - Line 781: Removed `import math` from stage_a_final_cell computation

## Verification

### Import Hygiene Check
```bash
rg -n "^\s+import " dbex/refinement/{stage_a,stage_c}.py | grep -v derive_orientation | grep -v quaternion_to_matrix
```
**Result**: Zero matches (only geometry helpers remain lazy per ARCH-ENGINE-002 exceptions)

### Test Results

All three mapped selectors **PASSED**:

1. **test_stage_a_expansion** (DBEX_SMOKE_DETECTOR_SIZE=small)
   - Runtime: 49.60s
   - Status: ✅ PASSED
   - Validates: Stage A expansion with eager imports

2. **test_stage_a_engine_delegation_telemetry**
   - Runtime: 48.64s
   - Status: ✅ PASSED
   - Validates: Stage A telemetry with eager imports

3. **test_stage_c_detector_microslip** (DBEX_SMOKE_DETECTOR_SIZE=small)
   - Runtime: 40.48s
   - Status: ✅ PASSED
   - Note: Previously failed with ARCH-TELEMETRY-001 collector issue; now passes due to upstream fix

## Metrics

- **Import overhead eliminated**: Config factories, stdlib modules (json/os/sys/math), and model classes (Detector/Crystal/Simulator) now loaded once at module initialization instead of per LBFGS iteration
- **Architecture compliance**: Stage A/C wrappers now fully comply with ARCH-ENGINE-002 eager-import hygiene
- **Behavior preservation**: All three smoke tests pass with identical semantics to pre-refactor code

## Artifacts
- `pytest_stage_a_expansion.log` (49.60s, 1/1 passed)
- `pytest_stage_a_engine_telemetry.log` (48.64s, 1/1 passed)
- `pytest_stage_c_smoke.log` (40.48s, 1/1 passed)

## Next Actions
Phase B.3 complete. All Stage A/B/C modules now expose closure dependencies at module scope. Phase C (process-noise cleanup: docstring/spec citation sweep) deferred pending supervisor scope decision.
