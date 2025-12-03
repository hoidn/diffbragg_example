# Input for Ralph — ARCH-ENGINE-ARTIFACTS-001 Phase B.2 (Parity Validation)

## Summary
Create parity tests proving Stage A and Stage B artifacts match reconstruction helper outputs within ≤1e-6 relative MSE.

## Mode
TDD

## InitiativeType
architecture

## Focus
ARCH-ENGINE-ARTIFACTS-001 — RefinementEngine artifact channel & final-Bragg unification

## Branch
integration

## Mapped tests
```bash
# New tests to create:
pytest -vv tests/dbex/test_artifact_parity.py::test_stage_a_artifact_matches_helper
pytest -vv tests/dbex/test_artifact_parity.py::test_stage_b_artifact_matches_helper_shell_mode
```

## Artifacts
`plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-05T040000Z/`

## Do Now

**Context:** Phase A confirmed that Stage A, B, and C all emit `bragg_full` artifacts when terminal. Now we need **validation** that the artifact path produces identical output to the reconstruction helper path per Exit Criterion #2 (≤1e-6 relative MSE).

**Your task:** Create a new test module with parity tests for Stage A and Stage B.

### Step 1: Create `tests/dbex/test_artifact_parity.py`

Module structure:
```python
"""
Parity tests for ARCH-ENGINE-ARTIFACTS-001: Validate artifact bragg_full matches reconstruction helpers.

Per Exit Criterion #2: Stage artifacts must match helper outputs within ≤1e-6 relative MSE.
"""

import numpy as np
import pytest
import torch
from dbex.refinement.engine import RefinementEngine
from dbex.refinement.stage_a import StageA
from dbex.refinement.stage_b import StageB
from dbex.refinement.reconstruction import (
    build_final_bragg_from_stage_a_telemetry,
    build_final_bragg_from_stage_b_telemetry,
)
from dbex.refinement.context import build_refinement_context, build_job_context
from dbex.refinement.config import RefinementConfig
# Import fixtures and helpers as needed
```

### Step 2: Implement `test_stage_a_artifact_matches_helper`

**Pattern:**
1. Load `refGeom_small` dataset (use existing fixture patterns from `test_torch_refine_smoke.py`)
2. Build `RefinementConfig` with:
   - `enable_stage_b=False`, `enable_stage_c=False` (Stage A only → A is terminal)
   - Small detector, device/dtype from env
3. Build contexts via `build_refinement_context` and `build_job_context`
4. Instantiate `RefinementEngine` with `[StageA()]` only
5. Run: `engine.run({"context": refinement_context})`
6. Extract artifact: `artifact_bragg = engine.artifacts["stage_a"].bragg_full`
7. Call helper directly:
   ```python
   helper_bragg = build_final_bragg_from_stage_a_telemetry(
       telemetry_a=engine._telemetry["stage_a"],  # or extract from return value
       # ... (pass all required args matching stage_a.py:2022-2051 pattern)
   )
   ```
8. **Assert parity:**
   ```python
   assert artifact_bragg is not None, "Stage A artifact bragg_full should be populated when terminal"
   assert artifact_bragg.shape == helper_bragg.shape
   assert artifact_bragg.dtype == helper_bragg.dtype

   abs_diff = np.abs(artifact_bragg - helper_bragg)
   rel_diff = abs_diff / (np.abs(helper_bragg) + 1e-10)
   max_abs = abs_diff.max()
   max_rel = rel_diff.max()
   rms_rel = np.sqrt(np.mean(rel_diff**2))

   print(f"Stage A parity: max_abs={max_abs:.3e}, max_rel={max_rel:.3e}, rms_rel={rms_rel:.3e}")

   assert np.allclose(artifact_bragg, helper_bragg, rtol=1e-6, atol=0), \
       f"Stage A artifact parity failed: max_rel={max_rel:.3e} exceeds 1e-6"
   ```

### Step 3: Implement `test_stage_b_artifact_matches_helper_shell_mode`

**Pattern (similar to Stage A, but with Stage B):**
1. Load `refGeom_small` dataset
2. Build `RefinementConfig` with:
   - `enable_stage_b=True`, `enable_stage_c=False` (Stage B terminal)
   - `stage_b_n_shells=5` (shell mode)
   - `stage_b_mode="shell"`
3. Instantiate `RefinementEngine` with `[StageA(), StageB()]`
4. Run engine
5. Extract artifact: `artifact_bragg = engine.artifacts["stage_b"].bragg_full`
6. Call helper: `build_final_bragg_from_stage_b_telemetry` (match stage_b.py:1713-1728 pattern)
7. Assert parity with same metrics as Stage A

**Note:** Stage B helper requires many arguments. Inspect `stage_b.py:1693-1728` for the exact call signature and where each argument comes from.

### Step 4: Validation Commands

Run both tests:
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE \
DBEX_SMOKE_SIGMA_SOURCE=metadata \
DBEX_SMOKE_DETECTOR_SIZE=small \
pytest -vv tests/dbex/test_artifact_parity.py -s
```

Capture log:
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE \
DBEX_SMOKE_SIGMA_SOURCE=metadata \
DBEX_SMOKE_DETECTOR_SIZE=small \
pytest -vv tests/dbex/test_artifact_parity.py -s \
  > plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-05T040000Z/pytest_parity.log 2>&1
```

### Step 5: Document Results

Create `plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-05T040000Z/summary.md`:

If PASSED:
```markdown
### Turn Summary
Created parity tests proving Stage A and Stage B artifacts match reconstruction helpers within ≤1e-6 relative MSE.
Both tests PASSED: Stage A parity (max_rel=X.XXe-Y), Stage B shell mode parity (max_rel=X.XXe-Y).
Next: Phase B.2 complete, ready for Phase C orchestrator cleanup (remove fallback branches).
Artifacts: plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-05T040000Z/ (pytest_parity.log)
```

If FAILED:
```markdown
### Turn Summary
Created parity tests for artifact validation, but tests FAILED with divergence exceeding tolerance.
Stage [A|B] parity failed: max_rel=X.XXe-Y exceeds 1e-6 threshold (shapes match, dtype correct).
Captured debug diagnostics showing divergence at [specific location]; may need reconstruction helper bugfix or artifact emission correction.
Artifacts: plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-05T040000Z/ (pytest_parity.log, debug output)
```

## How-To Map

### Creating parity test structure
1. Copy fixture patterns from `tests/dbex/test_torch_refine_smoke.py` (dataset loading, config building)
2. Use `RefinementEngine` directly (not `run_nanobrag_refinement` facade)
3. Extract telemetry from `engine._telemetry` dict or return value
4. Pass all helper arguments matching the stage's artifact emission code path

### Helper call signatures
- Stage A helper: `dbex/refinement/reconstruction.py:148-166` (cold path) or `196-265` (warm cache)
- Stage B helper: `dbex/refinement/reconstruction.py:269-520`
- Match argument names and sources to stage_a.py:2022-2051 and stage_b.py:1693-1728

### Debug if tests fail
1. Print shapes, dtypes, means, maxes for both artifact and helper outputs
2. Find argmax of absolute difference: `np.unravel_index(abs_diff.argmax(), abs_diff.shape)`
3. Print pixel values at divergence point
4. Check if device (CPU vs CUDA) or dtype (float32 vs float64) mismatch

## Pitfalls To Avoid

1. **Don't use facade**: Call `RefinementEngine` directly, not `run_nanobrag_refinement` (we're testing the low-level artifact path)
2. **Match helper args exactly**: The reconstruction helpers have many arguments—inspect the stage code to see where each comes from
3. **Device/dtype neutrality**: Ensure both artifact and helper use same device/dtype (spec: float32 CPU-resident numpy)
4. **Terminal flag**: Stage A/B only populate bragg_full when terminal (set enable_stage_c=False for B terminal)
5. **Telemetry extraction**: Use `engine._telemetry["stage_a"]` to get the telemetry object for helper call (private attribute is okay for tests)

## If Blocked

**If helper signatures are unclear:**
- Read `dbex/refinement/stage_a.py:2022-2051` (Stage A artifact emission)
- Read `dbex/refinement/stage_b.py:1693-1728` (Stage B artifact emission)
- These show exactly how to call the helpers

**If parity tests fail:**
- Do NOT proceed to Phase C
- Capture full debug output (shapes, dtypes, sample values)
- Create `debug_parity_failure.md` in artifacts dir with:
  - Which test failed (A or B)
  - Max absolute and relative errors
  - Argmax location of divergence
  - Sample pixel values at divergence point
  - Device/dtype of both outputs

## Findings Applied (Mandatory)

- ARCH-ENGINE-ARTIFACTS-001 Phase A.0-A.3: Artifact infrastructure exists, Stage C confirmed populated
- ARCH-STAGE-CONTEXT-001 Phase D: Stage A/B conditionally populate bragg_full when terminal
- REFINE-FLOW-001: Stage B baseline parity gates (use for tolerance reference)
- GRADIENT-003: Stage B CPU fallback constraints (may need separate test later)

## Pointers

**Implementation references:**
- Stage A artifact emission: `dbex/refinement/stage_a.py:2022-2051`
- Stage B artifact emission: `dbex/refinement/stage_b.py:1687-1730`
- Reconstruction helpers: `dbex/refinement/reconstruction.py:148-520`

**Test patterns to reuse:**
- Dataset loading: `tests/dbex/test_torch_refine_smoke.py` fixture patterns
- Config building: `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
- Engine usage: `tests/dbex/test_refinement_engine.py::test_engine_executes_mock_stage`

**Spec citations:**
- docs/spec-db-workflow.md §§33-45 (engine contract, artifact flow)
- docs/spec-db-core.md §§85-90 (Bragg tensor contracts: float32, CPU-resident)
- ARCH-ENGINE-ARTIFACTS-001 Exit Criterion #2: ≤1e-6 relative MSE parity

## Next Up (optional)

If you finish early:
- Add `test_stage_b_artifact_matches_helper_cpu_fallback` for GRADIENT-003 coverage
- Add `test_stage_b_artifact_matches_helper_per_reflection_mode` for TORCH-REFINE-004 coverage

## Doc Sync Plan

Not needed for Phase B (tests only, no production code changes).
