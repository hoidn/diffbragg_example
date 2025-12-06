# ARCH-IMPL-CONFORMANCE-001 Phase B.1-B.2 Planning

## Date: 2026-01-14T000000Z

## Context

Phase A complete (A.0-A.2). Phase A.2 cold-path enforcement test confirmed 64.7% relative error (2.83x scale factor mismatch) between Stage A warm-cache and reconstruction cold path, validating hypothesis of duplicated sqrt(spot_scale_override) scaling logic drift.

**Root cause**: Reconstruction cold path (dbex/refinement/reconstruction.py:88-223) receives `spot_scale_override=None` because `calibration_metadata` is not threaded from config to cold-path reconstruction logic.

## Phase B.1-B.2 Scope

**Goal**: Create canonical scaling utilities and thread calibration_metadata to reconstruction cold path, establishing infrastructure for Phase B.3-B.4 refactor.

**Approach**: Minimal canonical API that encapsulates sqrt(spot_scale_override) pattern; update reconstruction signature to accept calibration_metadata; do NOT refactor Stage A or reconstruction consumers yet (defer to B.3-B.4).

**Exit Criteria**:
1. `dbex/refinement/scaling_utils.py` exists with `apply_sqrt_spot_scale` function
2. Unit test for `apply_sqrt_spot_scale` passes
3. `build_final_bragg_from_stage_a_telemetry` signature accepts `calibration_metadata` parameter
4. Calibration metadata threaded to cold-path sqrt_spot_scale extraction (lines 203-208)
5. Phase A.2 cold-path test still FAILS (expected, refactor not yet applied)
6. No regressions in Phase A.1 warm-cache test (cache path unchanged)

## Implementation Plan

### B.1 — Canonical Scaling Utility Module

**File**: `dbex/refinement/scaling_utils.py` (new, ~80 lines)

**Function signature**:
```python
def apply_sqrt_spot_scale(
    bragg: np.ndarray,
    calibration_metadata: dict | None,
) -> np.ndarray:
    """Apply sqrt(spot_scale_override) scaling to raw simulator outputs.

    Canonical owner for ARCH-CONTRACT-002 post-run scaling pattern.

    Args:
        bragg: Raw simulator outputs, shape [n_panels, slow, fast] or [slow, fast]
        calibration_metadata: Dict with 'spot_scale_override' key (optional)

    Returns:
        Scaled bragg array (same shape as input)

    Contract:
        - If spot_scale_override present and > 0: multiply by sqrt(spot_scale_override)
        - Otherwise: return bragg unchanged (scale factor = 1.0)
        - Never returns None or modifies input in-place

    Spec Reference:
        docs/spec-db-core.md:60-140 (calibration threading)
        docs/architecture/calibration_scaling.md:14 (post-simulation sqrt scaling)

    Finding References:
        SCALE-002, SCALE-008, SCALE-009

    Consumers (Phase B.3-B.4 will refactor to use this):
        - dbex/refinement/stage_a.py:442-443
        - dbex/refinement/reconstruction.py:203-208
        - dbex/vis/mapping.py (simulate_forward_once path)
    """
```

**Implementation notes**:
- Extract `spot_scale_override` from `calibration_metadata.get('spot_scale_override')`
- Return `bragg * sqrt_spot_scale` where `sqrt_spot_scale = sqrt(override)` if override > 0 else 1.0
- Handle None metadata gracefully (scale = 1.0)
- Type hints: use `np.ndarray` (no torch dependency in this module)
- Docstring must cite ARCH-CONTRACT-002, SCALE-002/008/009

**Unit test**: `tests/dbex/refinement/test_scaling_utils.py::test_apply_sqrt_spot_scale`

Test cases:
1. No metadata (None) → scale = 1.0
2. No spot_scale_override key → scale = 1.0
3. spot_scale_override = 0 → scale = 1.0
4. spot_scale_override = 3.2e17 → scale = sqrt(3.2e17) ≈ 5.66e8
5. Shape preservation (panel mode vs single-panel)

### B.2 — Thread calibration_metadata to Reconstruction

**File**: `dbex/refinement/reconstruction.py`

**Changes**:
1. Update `build_final_bragg_from_stage_a_telemetry` signature (line ~64):
   ```python
   def build_final_bragg_from_stage_a_telemetry(
       ...,
       config: RefinementConfig,
       calibration_metadata: dict | None = None,  # NEW parameter
       ...
   ):
   ```

2. Update cold-path sqrt_spot_scale extraction (lines 203-208):
   ```python
   # Extract spot_scale_override for post-run scaling (ARCH-CONTRACT-002)
   # Precedence: explicit calibration_metadata param > config.calibration_metadata > None
   effective_calibration_metadata = calibration_metadata or config.calibration_metadata
   spot_scale_override = None
   if effective_calibration_metadata is not None:
       spot_scale_override = effective_calibration_metadata.get('spot_scale_override')

   sqrt_spot_scale = float(np.sqrt(spot_scale_override)) if spot_scale_override and spot_scale_override > 0 else 1.0
   ```

3. Add docstring update citing ARCH-CONTRACT-002 and Phase B.1 canonical API

**Call-site updates** (Phase B.1-B.2 scope):
- DO NOT update call sites yet (defer to B.3-B.4)
- Default `calibration_metadata=None` ensures backward compatibility
- Cold-path test will still FAIL (calibration_metadata not passed yet)

**Rationale**: Establish infrastructure without changing behavior; Phase B.3-B.4 will refactor consumers to pass calibration_metadata and use canonical API.

## Validation Plan

### Phase A.1 Regression Check (warm-cache)
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale
```

**Expected**: PASS (cache path unchanged)

### Phase A.2 Baseline Persistence (cold-path)
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path
```

**Expected**: FAIL (same 64.7% error, refactor not yet applied)

### Unit Test (canonical API)
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE \
pytest -vv tests/dbex/refinement/test_scaling_utils.py::test_apply_sqrt_spot_scale
```

**Expected**: PASS (all 5 test cases)

## Artifacts Plan

**Artifacts root**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T000000Z/`

Files to capture:
- `pytest_phase_b1_unit.log` (scaling_utils unit test)
- `pytest_phase_a1_regression.log` (warm-cache regression check)
- `pytest_phase_a2_baseline.log` (cold-path baseline persistence)
- `phase_b1_implementation_summary.md` (this loop's summary)

## Risks and Mitigations

### Risk: Signature Change Breaking Existing Call Sites
**Impact**: Reconstruction helper called from multiple locations; adding required parameter could break them.

**Mitigation**: Use default `calibration_metadata=None` to preserve backward compatibility. Phase B.3-B.4 will update call sites explicitly.

### Risk: Unit Test Imports torch Dependencies
**Impact**: Scaling utilities should be numpy-only to avoid circular imports or heavy dependencies.

**Mitigation**: `apply_sqrt_spot_scale` uses only numpy; unit test may import torch fixtures but helper itself is torch-free.

### Risk: Cold-Path Test Still Failing After B.1-B.2
**Impact**: Expectation management — this phase establishes infrastructure, not fix.

**Mitigation**: Explicitly document in planning and summary that Phase A.2 test will still FAIL; Phase B.3-B.4 refactor required to fix.

## Next Loop (B.3-B.4) Preview

**Scope**: Refactor Stage A and reconstruction to use `apply_sqrt_spot_scale` canonical API.

**Changes**:
1. stage_a.py:442-443 → call `apply_sqrt_spot_scale(bragg_stack, config.calibration_metadata)`
2. reconstruction.py:203-208 → call `apply_sqrt_spot_scale(bragg_final, effective_calibration_metadata)`
3. Update reconstruction call sites to pass `calibration_metadata` parameter
4. Run both Phase A.1 and A.2 tests
5. **Expected**: Both tests PASS after refactor

**Exit Criteria**: Phase A.1 (warm-cache) and A.2 (cold-path) enforcement tests both PASS with rel_error <= 1e-6.

## Cross-References

- **Phase A.2 summary**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T230000Z/summary.md`
- **Phase A kickoff planning**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T150000Z/summary.md`
- **Implementation plan**: `plans/active/ARCH-IMPL-CONFORMANCE-001/implementation.md`
- **Code references**:
  - `dbex/refinement/stage_a.py:442-443` (original sqrt scaling pattern)
  - `dbex/refinement/reconstruction.py:203-208` (cold path duplicate)
  - `tests/architecture/test_scale_contracts.py` (Phase A.1/A.2 enforcement tests)

---

**Phase B.1-B.2 planning complete. Ready for implementation loop.**
