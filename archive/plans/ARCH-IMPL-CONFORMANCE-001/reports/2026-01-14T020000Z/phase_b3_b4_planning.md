# ARCH-IMPL-CONFORMANCE-001 Phase B.3-B.4 Planning

## Date: 2026-01-14T020000Z

## Context

Phase B.1-B.2 complete (loop i=111):
- ✅ Canonical `apply_sqrt_spot_scale` API delivered (11/11 unit tests PASS)
- ✅ `calibration_metadata` parameter threaded to reconstruction signature
- ✅ Warm-cache regression test PASSED (Phase A.1)
- ✅ Cold-path baseline test FAILED as expected (Phase A.2: 64.7% rel_error, 2.83x scale factor drift)

**Root cause validated**: Reconstruction cold path at lines 213-221 contains duplicated sqrt(spot_scale_override) extraction logic that drifted from Stage A pattern (lines 442-443). Both paths need to delegate to canonical `apply_sqrt_spot_scale` API.

## Phase B.3-B.4 Scope

**Goal**: Refactor Stage A and reconstruction to use canonical `apply_sqrt_spot_scale` API, eliminating duplicated scaling logic and passing cold-path enforcement test.

**Exit Criteria**:
1. Stage A (stage_a.py:442-443) uses `apply_sqrt_spot_scale(bragg_stack, config.calibration_metadata)`
2. Reconstruction (reconstruction.py:213-221) uses `apply_sqrt_spot_scale(bragg_panel, effective_calibration_metadata)`
3. Phase A.1 warm-cache test PASSES (regression check)
4. Phase A.2 cold-path test PASSES (rel_error <= 1e-6, was 64.7%)
5. No behavior changes to existing call sites (backward compatibility maintained)

## Implementation Plan

### B.3 — Refactor Stage A to Use Canonical API

**File**: `dbex/refinement/stage_a.py`

**Current code** (lines 438-444):
```python
# Apply spot_scale_override per SCALE-002 (sqrt factor)
# Extract spot_scale_override from calibration_metadata when present
spot_scale_override = 1.0
if config.calibration_metadata is not None:
    spot_scale_override = config.calibration_metadata.get("spot_scale_override", 1.0)
sqrt_spot_scale = float(np.sqrt(spot_scale_override)) if spot_scale_override > 0 else 1.0
bragg_stack_scaled = bragg_stack * sqrt_spot_scale
```

**Refactored code**:
```python
# Apply spot_scale_override per SCALE-002 (sqrt factor) using canonical API
# ARCH-CONTRACT-002: delegate to owner module (ARCH-IMPL-CONFORMANCE-001 Phase B.3)
from dbex.refinement.scaling_utils import apply_sqrt_spot_scale

bragg_stack_np = bragg_stack.detach().cpu().numpy()
bragg_stack_scaled_np = apply_sqrt_spot_scale(bragg_stack_np, config.calibration_metadata)
bragg_stack_scaled = torch.from_numpy(bragg_stack_scaled_np).to(
    device=bragg_stack.device, dtype=bragg_stack.dtype
)
```

**Rationale**:
- Converts torch tensor to numpy for canonical API (numpy-only, no torch deps)
- Preserves device/dtype by reconverting to torch after scaling
- Replaces 7 lines of duplicated logic with single API call
- Maintains exact same scaling behavior (identity refactor)

**Import location**: Top of stage_a.py with other dbex.refinement imports (around line 28-35)

### B.4 — Refactor Reconstruction to Use Canonical API

**File**: `dbex/refinement/reconstruction.py`

**Current code** (lines 213-221):
```python
# Extract spot_scale_override for post-run scaling (matches stage_a.py:442-443, SCALE-009)
# Phase B.2 (ARCH-IMPL-CONFORMANCE-001): Thread calibration_metadata parameter
# effective_calibration_metadata prioritizes explicit parameter over config default
effective_calibration_metadata = calibration_metadata or config.calibration_metadata
spot_scale_override = None
if effective_calibration_metadata is not None:
    spot_scale_override = effective_calibration_metadata.get('spot_scale_override')

sqrt_spot_scale = float(np.sqrt(spot_scale_override)) if spot_scale_override and spot_scale_override > 0 else 1.0
```

**Refactored code**:
```python
# ARCH-CONTRACT-002: Use canonical API for post-run scaling (ARCH-IMPL-CONFORMANCE-001 Phase B.4)
from dbex.refinement.scaling_utils import apply_sqrt_spot_scale

# Thread calibration_metadata parameter (Phase B.2)
# Prioritize explicit parameter over config default
effective_calibration_metadata = calibration_metadata or config.calibration_metadata
```

**Additional changes**:
- Replace direct `* sqrt_spot_scale` multiplications with `apply_sqrt_spot_scale` calls at:
  - Line ~506: `bragg_scaled = apply_sqrt_spot_scale(bragg_panel * scale_factor * baseline_alignment_factor, effective_calibration_metadata)`
  - Any other `* sqrt_spot_scale` patterns in the cold-path reconstruction section

**Note**: The cold path contains complex logic interleaving scale_factor, baseline_alignment_factor, and sqrt_spot_scale. We'll apply the canonical API at the final multiplication site to preserve the existing order of operations.

**Import location**: Top of reconstruction.py with other dbex.refinement imports (around line 23-26)

## Validation Plan

### Phase A.1 Regression Check (warm-cache)
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale
```

**Expected**: PASS (cache path uses Stage A artifacts, no cold-path exercise)

### Phase A.2 Contract Validation (cold-path)
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path
```

**Expected**: PASS (rel_error <= 1e-6, was 64.7% before refactor)

### Stage A Smoke Regression
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=metadata \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_stage_a_smoke_parity
```

**Expected**: PASS (Stage A behavior unchanged)

## Artifacts Plan

**Artifacts root**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T020000Z/`

Files to capture:
- `pytest_phase_a1_regression.log` (warm-cache regression)
- `pytest_phase_a2_validation.log` (cold-path contract validation)
- `pytest_stage_a_smoke.log` (Stage A smoke regression)
- `phase_b3_b4_implementation_summary.md` (this loop's summary)

## Risks and Mitigations

### Risk: Torch ↔ NumPy Conversion Overhead in Stage A Hot Path
**Impact**: Stage A runs simulators in tight LBFGS loop; extra conversions could degrade performance.

**Mitigation**: This conversion happens ONCE per Stage A run (zero-iteration baseline only, not per LBFGS step). Performance impact negligible. Future optimization: extend canonical API to accept torch.Tensor with numpy fallback.

### Risk: Cold-Path Reconstruction Complexity
**Impact**: Reconstruction cold path interleaves multiple scale factors (scale_factor, baseline_alignment_factor, sqrt_spot_scale). Incorrect application order could break parity.

**Mitigation**: Apply canonical API at final multiplication site only (after scale_factor × baseline_alignment_factor). This preserves existing order of operations. Phase A.2 test validates end-to-end parity.

### Risk: Call Sites Not Passing calibration_metadata Yet
**Impact**: Phase B.2 added parameter but didn't update call sites. Cold-path test might still fail if reconstruction doesn't receive calibration_metadata.

**Analysis**: Phase A.2 test explicitly passes `calibration_metadata=None` and forces cold path (stage_a_ctx=None), so reconstruction falls back to `config.calibration_metadata`. This should work. If test still fails after refactor, next loop must audit call sites.

**Mitigation**: Phase B.3-B.4 focuses on API usage. If Phase A.2 still fails, Phase B.5 will audit/update call sites to pass calibration_metadata explicitly.

## Call Site Audit (Deferred to B.5 if Needed)

**Production call sites** (from grep results):
1. `dbex/refinement/stage_a.py:2182` — Stage A terminal artifact construction
2. `dbex/refinement/telemetry_baseline.py:148` — Baseline telemetry reconstruction

**Test call sites**:
1. `tests/architecture/test_scale_contracts.py:119, 254` — Architecture enforcement tests
2. `tests/dbex/test_artifact_parity.py:189, 457, 598` — Artifact parity tests
3. `tests/dbex/test_stage_a_mapping_equiv.py:264` — Mapping equivalence
4. `tests/dbex/test_stage_a_smoke_parity.py:316, 340` — Smoke parity

**Assumption**: All production call sites inherit `config.calibration_metadata` correctly. If Phase A.2 test passes after B.3-B.4, no call-site updates needed. If test still fails, Phase B.5 will update call sites to pass `calibration_metadata` explicitly.

## Implementation Sequence

1. **Stage A refactor** (B.3):
   - Add import: `from dbex.refinement.scaling_utils import apply_sqrt_spot_scale` (top of file)
   - Replace lines 438-444 with canonical API call (torch ↔ numpy conversion)
   - Update docstring/comments to cite ARCH-CONTRACT-002 and Phase B.3

2. **Reconstruction refactor** (B.4):
   - Add import: `from dbex.refinement.scaling_utils import apply_sqrt_spot_scale` (top of file)
   - Keep `effective_calibration_metadata` assignment (line 216, Phase B.2 work)
   - Delete lines 217-221 (duplicated sqrt_spot_scale extraction logic)
   - Find `* sqrt_spot_scale` multiplication sites in cold path (~line 506)
   - Replace with `apply_sqrt_spot_scale(bragg_value, effective_calibration_metadata)` calls
   - Update docstring to cite ARCH-CONTRACT-002 and Phase B.4

3. **Run validation tests**:
   - Phase A.1 regression (warm-cache)
   - Phase A.2 validation (cold-path, expect PASS now)
   - Stage A smoke regression (behavior unchanged)

4. **Write artifacts**:
   - Capture pytest logs to reports directory
   - Write implementation summary with metrics, next actions

## Expected Outcomes

### Phase A.1 (warm-cache): PASS
- Relative error <= 1e-6
- Uses Stage A artifacts (bragg_zero_iter cached)
- No cold-path exercise

### Phase A.2 (cold-path): PASS (improvement from 64.7% → <0.0001%)
- Relative error <= 1e-6 (was 64.7%)
- Cold-path reconstruction now uses same sqrt(spot_scale_override) logic as Stage A
- Scale factor alignment confirmed (was 2.83x drift, now 1.0x ± 1e-6)

### Stage A Smoke: PASS (no regression)
- Stage A behavior unchanged (canonical API is identity refactor)
- Chi² / ROI metrics within tolerance

## Next Steps (Phase B.5-B.6)

If Phase A.2 PASSES after B.3-B.4:
- Phase B.5: Update docs (findings.md SCALE-008/009, TESTING_GUIDE.md, TEST_SUITE_INDEX.md)
- Phase B.6: ARCH-CONTRACT-003 validation (Mapping → Stage A baseline override, if in scope)

If Phase A.2 still FAILS after B.3-B.4:
- Phase B.5: Audit call sites, update to pass `calibration_metadata` explicitly
- Investigate any remaining discrepancies in cold-path reconstruction logic

## Cross-References

- **Phase B.1-B.2 summary**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T000000Z/summary.md`
- **Phase B.1-B.2 planning**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T000000Z/phase_b_planning.md`
- **Phase A.2 summary**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T230000Z/summary.md`
- **Implementation plan**: `plans/active/ARCH-IMPL-CONFORMANCE-001/implementation.md`
- **Canonical API**: `dbex/refinement/scaling_utils.py:35-111`
- **Stage A scaling**: `dbex/refinement/stage_a.py:438-444`
- **Reconstruction scaling**: `dbex/refinement/reconstruction.py:213-221`

---

**Phase B.3-B.4 planning complete. Ready for implementation loop i=112.**
