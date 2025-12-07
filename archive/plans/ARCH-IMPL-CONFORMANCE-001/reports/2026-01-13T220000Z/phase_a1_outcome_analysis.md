# ARCH-IMPL-CONFORMANCE-001 Phase A.1 Outcome Analysis

## Date: 2026-01-13T220000Z

## Executive Summary

Phase A.1 nucleus test (`test_stage_a_vs_reconstruction_scale`) implemented and executed. **Outcome: PASS** (unexpected). Test validates ARCH-CONTRACT-001 (Stage A vs reconstruction parity) for the **warm-cache path**, where reconstruction receives `stage_a_ctx` and returns the cached `bragg_zero_iter` directly.

**Key Finding**: ARCH-SIM-CONSTRUCTION-001 Phase C.8 cache optimization ensures perfect parity when reconstruction operates in warm-cache mode. However, **cold-path scenario** (no `stage_a_ctx` provided) remains unvalidated and may still contain duplicated scaling logic.

## Test Implementation Review

### Test Specification
- **Module**: `tests/architecture/test_scale_contracts.py` (new, 158 lines)
- **Function**: `test_stage_a_vs_reconstruction_scale`
- **Fixture**: `refgeom_dataload` (refGeom_small)
- **Tolerance**: 1e-6 relative error (per docs/spec-db-core.md:60-140)

### Test Execution Path
1. Build Stage A warm-cache context via `build_mapping_stage_a_context`
2. Extract `bragg_stage_a` from `stage_a_ctx.bragg_zero_iter`
3. Compute `masked_mean_stage_a` over trusted pixels
4. Call `build_final_bragg_from_stage_a_telemetry` with:
   - `param_state="initial"` (zero deltas)
   - `stage_a_ctx=stage_a_ctx` **(warm-cache mode)**
5. Compute `masked_mean_reconstruction` over same trusted pixels
6. Assert `rel_error <= 1e-6`

### Actual Outcome
- **Status**: PASSED
- **Metrics**:
  - `masked_mean_stage_a = 2.128348e+00`
  - `masked_mean_reconstruction = 2.128348e+00`
  - `rel_error = 0.000000e+00`
  - `ratio = 1.000000`
- **Cache Behavior**: `[ARCH-SIM-CONSTRUCTION-001 CACHE HIT] Returning cached zero-iteration Bragg stack for param_state='initial'`

## Root Cause: Warm-Cache Fast Path

### Code Analysis
`dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry` lines 83-86:

```python
if param_state == "initial" and stage_a_ctx is not None and hasattr(stage_a_ctx, 'bragg_zero_iter') and stage_a_ctx.bragg_zero_iter is not None:
    print(f"[ARCH-SIM-CONSTRUCTION-001 CACHE HIT] Returning cached zero-iteration Bragg stack for param_state='initial' (shape={stage_a_ctx.bragg_zero_iter.shape})")
    return np.array(stage_a_ctx.bragg_zero_iter, copy=True)
```

**Interpretation**: When reconstruction is called with `param_state="initial"` AND `stage_a_ctx` is provided, it **bypasses all simulator construction and scaling logic** and returns the cached Bragg stack directly from Stage A context.

**Why test passes**: Stage A and reconstruction return **bitwise-identical** outputs because reconstruction literally returns Stage A's cached array (with a copy). No independent computation occurs.

## Contract Satisfaction Assessment

### ARCH-CONTRACT-001 (Stage A vs Reconstruction Scaling Parity)
**Status**: **PARTIALLY SATISFIED** (warm-cache path only)

**Satisfied scenarios**:
- ✅ Reconstruction with `stage_a_ctx` + `param_state="initial"` (cache hit)
- ✅ DB-AT-027/028/029 acceptance tests (use warm-cache path via mapping context)

**Unsatisfied scenarios** (cold path):
- ❌ Reconstruction with `stage_a_ctx=None` (no cache available)
- ❌ Reconstruction with `param_state="final"` (cache bypassed, rebuilds from telemetry deltas)
- ❌ Direct calls to reconstruction helper from tools/scripts that don't provide Stage A context

**Evidence**: Cold-path code (lines 88-223) still contains duplicated scaling/calibration logic:
1. Sqrt scaling pattern (lines ~195-217, matches stage_a.py:442-443)
2. Beam calibration threading (lines ~170, matches stage_a_utils.py:267)
3. Baseline alignment logic (lines ~392-445, duplicates Stage A masked-mean computation)

### ARCH-CONTRACT-002 (Post-Run Scaling Pattern)
**Status**: **NOT SATISFIED** (duplicated logic still exists)

**Duplicates identified** (per module_inventory.md):
- `dbex/refinement/stage_a.py:442-443` (original)
- `dbex/refinement/reconstruction.py:~195-217` (cold path duplicate)

**Canonical owner**: Not yet implemented (proposed `dbex.refinement.scaling_utils.apply_sqrt_spot_scale`)

### ARCH-CONTRACT-003 (Mapping → Stage A Baseline Override)
**Status**: **NOT VALIDATED** (test does not exercise baseline handoff)

Test uses `build_mapping_stage_a_context` but does not verify:
- Whether mapping-adjusted baseline is preserved in `calibration_metadata`
- Whether Stage A defers to mapping baseline when `log_scale_baseline_source="mapping_masked_mean_adjustment"`
- Whether reconstruction honors the same precedence rule

## Implications for Phase B

### Phase B Scope Re-Assessment

**Original Phase B plan** (from 2026-01-13T150000Z/summary.md):
- B.1: Create `dbex.refinement.scaling_utils` with canonical scaling helpers
- B.2: Enhance factory to accept `calibration_metadata` and thread beam fields internally
- B.3: Refactor Stage A to use canonical API
- B.4: Refactor reconstruction to use canonical API
- B.5: Add enforcement tests
- B.6: Update docs and findings

**Revised assessment**:
- **B.1-B.2 remain valid** — Canonical utilities still needed to eliminate duplicates
- **B.3 may be lower priority** — Stage A warm-cache path is the primary code path for acceptance tests
- **B.4 is critical** — Reconstruction cold path still duplicates logic (lines 88-223)
- **B.5 needs expansion** — Add cold-path enforcement test (Phase A.2)
- **B.6 remains valid** — Update SCALE-008/009 findings to reflect cache optimization

### Recommended Path Forward

**Option 1: Skip to Phase B Implementation** (canonical API + cold-path enforcement)
- Rationale: Phase A.1 nucleus test already validates warm-cache contract. Cold-path contract needs implementation work, not more baseline detection.
- Next loop: Implement `scaling_utils.py` canonical API + refactor reconstruction cold path + add cold-path enforcement test.
- Risk: Larger scope, may take 2-3 loops to complete Phase B fully.

**Option 2: Add Phase A.2 Cold-Path Enforcement Test First** (TDD approach)
- Rationale: Establish cold-path baseline failure before implementing canonical API, ensuring B.4 implementation is validated.
- Next loop: Implement `test_stage_a_vs_reconstruction_scale_cold_path` that forces reconstruction to bypass cache (set `stage_a_ctx=None`), expect FAIL showing duplicated logic drift.
- Benefit: Smaller, focused loop; establishes clear Phase B exit criteria.
- Risk: Adds one more planning/evidence loop before implementation.

**Recommendation**: **Option 2** (TDD approach)
- More disciplined architecture enforcement (test-first)
- Validates that cold path truly has drift (assumption, not yet proven)
- Clearer Phase B exit criteria (both warm + cold tests must pass)
- Aligns with nucleus_test_design.md intent (baseline detector → canonical API → enforcement gate)

## Phase A.2 Test Design (Cold-Path Enforcement)

### Test Specification

**Test name**: `test_stage_a_vs_reconstruction_scale_cold_path`

**Difference from A.1 nucleus test**:
- Call `build_final_bragg_from_stage_a_telemetry` with **`stage_a_ctx=None`** to force cold-path reconstruction
- Reconstruction must rebuild Bragg stack from scratch (no cache)
- If duplicated scaling logic has drifted, this will expose it

**Expected outcome**: **FAIL** (exposes cold-path drift)

**Metrics to capture**:
- `masked_mean_stage_a` (from warm-cache path)
- `masked_mean_reconstruction_cold` (from cold path, no cache)
- `rel_error` (likely > 1e-6 if drift exists)
- `ratio` (scale factor showing magnitude of drift)

**Fixture**: Same `refgeom_dataload` (refGeom_small)

**Implementation note**: May need to construct telemetry manually (cannot reuse `stage_a_ctx.telemetry` if testing cold path from scratch). Check existing test patterns in `tests/dbex/` for telemetry construction.

### Success Criteria (Phase A.2 Exit)

- [ ] Cold-path test implemented in `test_scale_contracts.py`
- [ ] Test runs to completion (FAIL or PASS, not error)
- [ ] Baseline metrics captured (masked_mean divergence, ratio)
- [ ] Artifacts stored under `2026-01-13T220000Z/` or next timestamp
- [ ] If test **PASSES** (no drift), document finding and skip Phase B.4 refactor
- [ ] If test **FAILS** (drift confirmed), proceed to Phase B implementation

## Ledger Updates Required

### docs/fix_plan.md Attempts History
Add entry:
```
- 2026-01-13T220000Z: Phase A.1 outcome analysis. Nucleus test PASSED (unexpected) due to ARCH-SIM-CONSTRUCTION-001 Phase C.8 cache optimization ensuring warm-cache parity. Cold-path scenario (stage_a_ctx=None) remains unvalidated. Proposed Phase A.2: add cold-path enforcement test to establish baseline drift before Phase B canonical API implementation. Artifacts: plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T220000Z/. [architecture, planning]
```

### plans/active/ARCH-IMPL-CONFORMANCE-001/implementation.md
- [x] A0: Nucleus test designed (2026-01-13T200000Z)
- [x] A1: Nucleus test implemented, **PASSED** (warm-cache parity validated) (2026-01-13T210000Z)
- [ ] A2: **Cold-path enforcement test** — Add `test_stage_a_vs_reconstruction_scale_cold_path` to validate cold-path contract (next loop)

Update Status Note:
```markdown
## Status: in_progress
- Phase A.0 complete: nucleus test designed (2026-01-13T200000Z)
- Phase A.1 complete: nucleus test implemented, PASSED (warm-cache parity confirmed via cache optimization) (2026-01-13T210000Z)
- Phase A.1 analysis complete: cold-path scenario identified as unvalidated, Phase A.2 planned (2026-01-13T220000Z)
- Next: Phase A.2 — cold-path enforcement test implementation (TDD before Phase B canonical API)
```

### docs/findings.md Updates (deferred to Phase B.6)
- **SCALE-008**: Add cross-reference to `test_stage_a_vs_reconstruction_scale` enforcement test
- **SCALE-009**: Update to reflect multi-factor parity issue (mask, N_cells, baseline, cache optimization)
- **ARCH-FACTORY-001**: Note that factory calibration threading is still duplicated in reconstruction cold path

## Next Loop Recommendation

**Mode**: TDD (write test first, expect FAIL)

**ActionType**: implementation_ready (cold-path enforcement test)

**DecisionStatus**: exploring (baseline drift detection for cold path)

**Focus**: [ARCH-IMPL-CONFORMANCE-001] Phase A.2 — Cold-Path Enforcement Test

**Do Now**:
1. Implement `test_stage_a_vs_reconstruction_scale_cold_path` in `tests/architecture/test_scale_contracts.py`
2. Force cold-path reconstruction by calling `build_final_bragg_from_stage_a_telemetry` with `stage_a_ctx=None`
3. Run test and capture baseline metrics (expect FAIL showing drift)
4. Store artifacts under `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/<timestamp>/`
5. If FAIL: proceed to Phase B canonical API implementation
6. If PASS: document finding, skip Phase B.4, adjust Phase B scope

**Mapped Tests**: `tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path` (new)

**Artifacts**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/<timestamp>/pytest_cold_path_baseline.log`, `cold_path_metrics.json`

**Findings Applied**: SCALE-008, SCALE-009, ARCH-FACTORY-001

**ARCH Contracts**: ARCH-CONTRACT-001 (cold-path validation), ARCH-CONTRACT-002 (duplicated scaling logic detection)

## Cross-References

- **Phase A.1 nucleus test**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T210000Z/`
- **Phase A.0 nucleus design**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T200000Z/nucleus_test_design.md`
- **Phase A kickoff planning**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T150000Z/summary.md`
- **ARCH-SIM-CONSTRUCTION-001 cache optimization**: `plans/active/ARCH-SIM-CONSTRUCTION-001/` (Phase C.8 context)
- **Code references**:
  - `dbex/refinement/reconstruction.py:83-86` (cache fast-path)
  - `dbex/refinement/reconstruction.py:88-223` (cold-path duplicated logic)
  - `tests/architecture/test_scale_contracts.py:24-158` (Phase A.1 nucleus test)

---

**Analysis complete. Phase A.2 cold-path enforcement test recommended for next loop (TDD approach before Phase B implementation).**
