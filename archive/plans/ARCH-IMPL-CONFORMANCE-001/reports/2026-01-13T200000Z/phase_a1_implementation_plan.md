# ARCH-IMPL-CONFORMANCE-001 — Phase A.1 Implementation Plan

## Date: 2026-01-13T200000Z

## Scope

Step-by-step implementation guide for Ralph to execute in the next loop (i=109), creating the nucleus architecture test designed in Phase A.0 (nucleus_test_design.md).

## Loop Metadata

- **Mode**: TDD (write test first, validate it fails as expected)
- **ActionType**: implementation_ready (nucleus test implementation)
- **DecisionStatus**: exploring (baseline failure capture)
- **InitiativeType**: architecture
- **Focus**: [ARCH-IMPL-CONFORMANCE-001] Phase A.1 — Nucleus Architecture Test Implementation
- **Mapped Tests**: `tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale` (new)

## Implementation Checklist

### Pre-Implementation Search

Before writing code, search the codebase to:
1. Confirm `build_mapping_stage_a_context` API signature and import path
2. Confirm `build_final_bragg_from_stage_a_telemetry` API signature and import path
3. Verify `refGeom_small` fixture location and usage pattern
4. Check existing architecture test structure for import patterns and helpers

**Search commands**:
```bash
rg "def build_mapping_stage_a_context" --type py
rg "def build_final_bragg_from_stage_a_telemetry" --type py
rg "refGeom_small" tests/ --type py
```

### Step 1: Create Test File

**File**: `tests/architecture/test_scale_contracts.py` (new)

**Initial structure**:
```python
"""
Architecture enforcement tests for scaling and calibration contracts.

Tests in this module validate ARCH-CONTRACTs defined in:
- docs/architecture/calibration_scaling.md
- plans/active/ARCH-IMPL-CONFORMANCE-001/implementation.md

See also:
- SCALE-008 (docs/findings.md:322-339): Stage A vs mapping baseline alignment
- SCALE-009 (docs/findings.md:341-358): Reconstruction scaling parity
"""

import numpy as np
import pytest

# Imports will be added based on search results above
# Expected:
# from dbex.refinement.stage_a_utils import build_mapping_stage_a_context
# from dbex.refinement.reconstruction import build_final_bragg_from_stage_a_telemetry
# from dbex.data_load import DataLoad  # or similar fixture loader
# from conftest import refGeom_small  # or wherever fixture is defined
```

### Step 2: Implement Test Function

**Function signature**:
```python
def test_stage_a_vs_reconstruction_scale(refGeom_small):
    """
    ARCH-CONTRACT-002 enforcement: Stage A and reconstruction must produce
    identical sqrt-scaled outputs given identical geometry and calibration.

    See: plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T200000Z/nucleus_test_design.md

    Expected initial outcome: FAIL (exposes current duplicate scaling logic mismatch)
    Expected Phase B outcome: PASS (after canonical scaling_utils implementation)
    """
```

**Implementation steps** (inside function):

#### 2a. Load Fixture Data
```python
# Load refGeom_small fixture (geometry + calibration metadata)
# Exact pattern depends on search results from Step 1
# Example (adjust based on actual API):
data_load = DataLoad(refGeom_small)
geometry = data_load.geometry
calibration_metadata = data_load.calibration_metadata
trusted_mask = data_load.trusted_mask  # DIALS convention (True=trusted)

# Validate fixture has required calibration fields
assert "spot_scale_override" in calibration_metadata, (
    "refGeom_small fixture missing spot_scale_override"
)
assert calibration_metadata["spot_scale_override"] > 0, (
    "spot_scale_override must be positive"
)
```

#### 2b. Run Stage A Warm-Cache Path
```python
# Build Stage A warm-cache context (pre-initialized simulators)
# Exact API depends on search results; adapt as needed
stage_a_context = build_mapping_stage_a_context(
    geometry=geometry,
    calibration_metadata=calibration_metadata,
    # Additional args as needed (check actual API signature)
)

# Extract Stage A Bragg outputs (post-sqrt-scaling)
# Exact field name depends on Stage A context structure
bragg_stage_a = stage_a_context.bragg  # or .artifacts.bragg, or similar

# Compute masked mean (trusted pixels only)
masked_mean_stage_a = np.mean(bragg_stage_a[trusted_mask])
```

#### 2c. Run Reconstruction Cold Path
```python
# Build reconstruction Bragg from Stage A telemetry
# param_state="initial" forces zero-delta reconstruction
reconstruction_output = build_final_bragg_from_stage_a_telemetry(
    telemetry=stage_a_context.telemetry,  # or stage_a_context.get_telemetry()
    param_state="initial",  # zero refinement deltas
    calibration_metadata=calibration_metadata,
    # Additional args as needed (check actual API signature)
)

# Extract reconstruction Bragg outputs (post-sqrt-scaling)
bragg_reconstruction = reconstruction_output.bragg  # or .outputs.bragg, or similar

# Compute masked mean (same trusted pixels)
masked_mean_reconstruction = np.mean(bragg_reconstruction[trusted_mask])
```

#### 2d. Compare and Assert
```python
# Compute relative error
rel_error = abs(masked_mean_stage_a - masked_mean_reconstruction) / masked_mean_stage_a

# Tolerance from docs/spec-db-core.md:60-140
tolerance = 1e-6

# Assertion with diagnostic message
assert rel_error <= tolerance, (
    f"Stage A vs reconstruction masked mean mismatch (ARCH-CONTRACT-002):\n"
    f"  Stage A masked_mean:         {masked_mean_stage_a:.6e}\n"
    f"  Reconstruction masked_mean:  {masked_mean_reconstruction:.6e}\n"
    f"  Relative error:              {rel_error:.6e}\n"
    f"  Tolerance:                   {tolerance:.6e}\n"
    f"  Ratio (stage_a/recon):       {masked_mean_stage_a / masked_mean_reconstruction:.6f}\n"
    f"\n"
    f"This test enforces that Stage A and reconstruction apply sqrt(spot_scale_override)\n"
    f"identically via shared canonical API (Phase B deliverable).\n"
    f"Current FAIL expected until Phase B implementation complete.\n"
)
```

### Step 3: Handle API Uncertainties

If search results show API signatures differ from above template:
1. **Adapt imports and calls** to match actual implementation
2. **Document assumptions** in test docstring
3. **If API is unclear**, add a comment flagging the assumption and proceed with best-effort implementation

Example:
```python
# ASSUMPTION: build_mapping_stage_a_context returns object with .bragg and .telemetry
# If this fails, check dbex/refinement/stage_a_utils.py:build_mapping_stage_a_context
```

### Step 4: Run Test and Capture Baseline Failure

**Command**:
```bash
PYTEST_ADDOPTS='' pytest -xvs tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale 2>&1 | tee plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T200000Z/pytest_nucleus_baseline.log
```

**Expected outcome**: **FAIL** with assertion message showing:
- `masked_mean_stage_a` value
- `masked_mean_reconstruction` value
- `rel_error` (outside tolerance)
- Ratio (scale factor)

**If test PASSES unexpectedly**:
- Document in artifacts with metric values
- Hypothesis: duplicate scaling logic may already be aligned (Phase B may be simpler than expected)
- Escalate to supervisor for plan adjustment

**If test errors** (not assertion failure, but import/API error):
- Capture traceback
- Document blocking API issue
- Mark initiative `blocked_pending_api_clarification`
- Do NOT proceed to Phase B

### Step 5: Run pytest --collect-only

**Command**:
```bash
pytest --collect-only tests/architecture/test_scale_contracts.py 2>&1 | tee plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T200000Z/pytest_collect.log
```

**Expected output**: Should collect exactly 1 test:
```
<Module test_scale_contracts.py>
  <Function test_stage_a_vs_reconstruction_scale>
```

**Purpose**: Validate test is discoverable and will be included in test registry update (Phase A.3).

### Step 6: Store Artifacts

**Artifacts directory**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T200000Z/`

**Required files**:
1. `pytest_nucleus_baseline.log` — Full pytest output showing baseline FAIL with metrics
2. `pytest_collect.log` — pytest --collect-only output
3. `summary.md` — Loop summary (standard Ralph format)

**Optional files**:
- `metrics.json` — Structured metrics (masked_mean values, rel_error, ratio) if useful for later analysis

### Step 7: Update Ledgers

#### docs/fix_plan.md Attempts History
Add entry:
```
- 2026-01-13T200000Z: Phase A.1 nucleus test implementation. Created tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale. Test FAIL (baseline) with masked_mean_stage_a=<value>, masked_mean_reconstruction=<value>, rel_error=<value> (tolerance=1e-6). Next: Phase B canonical scaling_utils implementation. [architecture, exploring]
```

#### plans/active/ARCH-IMPL-CONFORMANCE-001/implementation.md
Mark Phase A.0 complete, A.1 complete:
```markdown
- [x] A0: **Nucleus / Test-first gate:** Identify or create a minimal architecture test...
- [x] A1: Extract all existing SCALE/ARCH findings... (deferred to kickoff loop 2026-01-13T150000Z)
```

Update status note:
```markdown
## Status: pending → in_progress
- Phase A.0 complete: nucleus test designed (2026-01-13T200000Z)
- Phase A.1 complete: nucleus test implemented, baseline FAIL captured (2026-01-13T200000Z)
- Next: Phase A.2 (extract SCALE/ARCH findings, identify duplicates) OR skip to Phase B (canonical API implementation) if A.2 already complete in kickoff loop
```

### Step 8: Git Commit

**Commit message**:
```
[ARCH-IMPL-CONFORMANCE-001 A.1] Add nucleus test (baseline FAIL)

Created tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale
to enforce Stage A vs reconstruction scaling contract (ARCH-CONTRACT-002).

Baseline FAIL captured: masked_mean rel_error=<value> (tolerance=1e-6).

Tests:
- pytest -xvs tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale

Artifacts: plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T200000Z/

Cross-refs:
- SCALE-008 (docs/findings.md:322-339)
- SCALE-009 (docs/findings.md:341-358)
- nucleus_test_design.md (this loop)
```

## Pitfalls to Avoid

1. **Importing from wrong module**: Use search results to confirm actual import paths; do not guess.

2. **Fixture not available**: If `refGeom_small` is not a pytest fixture but a data path, adapt to load data directly via `DataLoad` or similar helper.

3. **API mismatch**: If Stage A or reconstruction helper APIs differ from template, adapt to actual signatures and document assumptions.

4. **Test PASSES when expecting FAIL**: Do not assume this is wrong; capture metrics and escalate to supervisor.

5. **Hard-coding paths**: Use fixture-relative paths or helpers; do not hard-code absolute paths to data files.

6. **Skipping collect-only**: Always run `pytest --collect-only` to validate test is discoverable.

7. **No baseline metrics**: Ensure pytest log captures actual metric values (masked_mean, rel_error, ratio) for later analysis.

## Success Criteria (Phase A.1 Exit)

- [x] Test file created: `tests/architecture/test_scale_contracts.py`
- [x] Test function implemented: `test_stage_a_vs_reconstruction_scale`
- [x] Test runs to completion (FAIL or PASS, not error)
- [x] Baseline metrics captured in pytest log
- [x] `pytest --collect-only` log captured
- [x] Artifacts stored in reports directory
- [x] fix_plan.md updated with attempt entry
- [x] implementation.md updated (A0, A1 marked complete)
- [x] Git commit pushed

## Next Loop (Phase B Planning or Continuation)

After Phase A.1 complete, supervisor will decide:
- **Option 1**: Skip to Phase B (canonical scaling_utils implementation) if A.2-A.3 already complete in kickoff loop
- **Option 2**: Continue Phase A.2 (extract SCALE/ARCH findings, identify all duplicated code sites)
- **Option 3**: Escalate if nucleus test revealed unexpected blocker

Ralph's next loop will receive explicit `Do Now` for chosen path.

---

**Phase A.1 implementation plan complete. Ready for Ralph execution in loop i=109.**
