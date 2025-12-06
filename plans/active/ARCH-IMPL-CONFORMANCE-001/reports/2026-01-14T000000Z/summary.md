# ARCH-IMPL-CONFORMANCE-001 Galph Turn Summary (Loop i=111 Planning)

## Date: 2026-01-14T000000Z

## Turn Type
Planning → implementation_ready

## Executive Summary

Phase A complete (A.0-A.2). Phase A.2 cold-path enforcement test confirmed 64.7% relative error (2.83x scale factor mismatch), validating hypothesis that reconstruction cold path (dbex/refinement/reconstruction.py:203-208) duplicates sqrt(spot_scale_override) scaling logic from Stage A (stage_a.py:442-443) but fails to receive calibration_metadata, resulting in drift.

Phase B.1-B.2 planning complete. Scoped canonical scaling utilities module with apply_sqrt_spot_scale function (numpy-only, 5 unit test cases) and calibration_metadata threading to reconstruction signature (backward-compatible default parameter).

DecisionStatus: patch_ready (canonical API design known from Phase A findings). Next loop delegates implementation to Ralph.

## Loop Context

### Focus Selector
[ARCH-IMPL-CONFORMANCE-001] — Architecture / Implementation Contract Alignment

### Initiative Type
architecture

### Action Type
planning

### Dwell Tracking
- Loop 1 for Phase B.1-B.2 planning
- Previous loop (i=110): Phase A.2 implementation (cold-path enforcement test)
- Total loops for ARCH-IMPL-CONFORMANCE-001: 5 (planning + 4 implementation)

### Lifecycle Compliance
- Phase A budget: 3 loops (A.0, A.1, A.2) — COMPLETE within budget
- Phase B.1-B.2 planning: 1 loop (this loop) — on schedule
- No stuck/blocked initiatives; ready for implementation

## Planning Outputs

### Primary Artifacts

1. **Phase B Planning Document** (`phase_b_planning.md`):
   - Canonical API specification (apply_sqrt_spot_scale function signature, docstring, implementation notes)
   - Unit test specification (5 test cases)
   - Reconstruction signature update (calibration_metadata parameter)
   - Cold-path extraction update (lines 203-208)
   - Validation plan (3 pytest selectors)
   - Risk mitigation (backward compatibility, import discipline)

2. **Implementation Plan Updates** (`implementation.md`):
   - Phase B checklist expanded (B.1-B.6 with Phase B.1-B.2 marked PLANNED)
   - Status Note updated (Phase A complete, Phase B.1-B.2 planned)

3. **input.md for Ralph Loop i=111**:
   - Summary: Implement canonical scaling utilities + thread calibration_metadata
   - Mode: none (production implementation)
   - ActionType: implementation_ready
   - DecisionStatus: patch_ready
   - Mapped Tests: test_apply_sqrt_spot_scale (new), test_stage_a_vs_reconstruction_scale (regression), test_stage_a_vs_reconstruction_scale_cold_path (baseline)
   - Do Now: 5-step implementation sequence with exact commands
   - Forbidden This Loop: No Stage A refactor, no call-site updates, no new probes
   - ARCH Contracts: ARCH-CONTRACT-001/002 with owner API specifications

### Ledger Updates

1. **docs/fix_plan.md Attempts History**:
   - Added 2026-01-14T000000Z entry documenting Phase B.1-B.2 planning scope, canonical API design, validation plan, artifacts path

2. **galph_memory.md**:
   - Updated focus=ARCH-IMPL-CONFORMANCE-001, state=implementation_ready, dwell=0
   - Documented Phase A completion (64.7% rel_error baseline)
   - Next action: phase_b1_b2_implementation
   - DecisionStatus: patch_ready

3. **plans/active/ARCH-IMPL-CONFORMANCE-001/implementation.md**:
   - Phase A Status Note: added Phase B.1-B.2 planning complete
   - Phase B checklist: marked B.1-B.2 as PLANNED
   - Phase B Notes: clarified infrastructure vs refactor split

## Phase B.1-B.2 Scope

### B.1 — Canonical Scaling Utility Module

**Deliverable**: `dbex/refinement/scaling_utils.py` (~80 lines)

**Function specification**:
```python
def apply_sqrt_spot_scale(
    bragg: np.ndarray,
    calibration_metadata: dict | None,
) -> np.ndarray:
    """Apply sqrt(spot_scale_override) scaling to raw simulator outputs.

    Canonical owner for ARCH-CONTRACT-002 post-run scaling pattern.
    """
```

**Implementation requirements**:
- Extract spot_scale_override from calibration_metadata.get('spot_scale_override')
- Return bragg * sqrt(spot_scale_override) if override > 0 else bragg unchanged
- Handle None metadata gracefully (scale = 1.0)
- Numpy-only (no torch dependencies)
- Docstring cites ARCH-CONTRACT-002, SCALE-002/008/009

**Unit test specification**:
- Module: `tests/dbex/refinement/test_scaling_utils.py`
- Test: `test_apply_sqrt_spot_scale`
- 5 test cases:
  1. No metadata (None) → scale = 1.0
  2. No spot_scale_override key → scale = 1.0
  3. spot_scale_override = 0 → scale = 1.0
  4. spot_scale_override = 3.2e17 → scale ≈ 5.66e8
  5. Shape preservation (panel mode vs single-panel)

### B.2 — calibration_metadata Threading

**Deliverable**: Update `dbex/refinement/reconstruction.py`

**Signature change** (line ~64):
```python
def build_final_bragg_from_stage_a_telemetry(
    ...,
    config: RefinementConfig,
    calibration_metadata: dict | None = None,  # NEW parameter
    ...
):
```

**Cold-path extraction update** (lines 203-208):
```python
# Precedence: explicit calibration_metadata param > config.calibration_metadata > None
effective_calibration_metadata = calibration_metadata or config.calibration_metadata
spot_scale_override = None
if effective_calibration_metadata is not None:
    spot_scale_override = effective_calibration_metadata.get('spot_scale_override')

sqrt_spot_scale = float(np.sqrt(spot_scale_override)) if spot_scale_override and spot_scale_override > 0 else 1.0
```

**Backward compatibility**:
- Default `calibration_metadata=None` preserves existing call sites
- Phase B.3-B.4 will update call sites explicitly

### Validation Plan

**3 pytest selectors** (all must run to completion):

1. **Unit test** (expect PASS):
   ```bash
   pytest -vv tests/dbex/refinement/test_scaling_utils.py::test_apply_sqrt_spot_scale
   ```

2. **Warm-cache regression** (expect PASS):
   ```bash
   pytest -vv tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale
   ```

3. **Cold-path baseline** (expect FAIL, refactor deferred):
   ```bash
   pytest -vv tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path
   ```

**Expected outcomes**:
- Unit test: PASS (all 5 test cases)
- Warm-cache regression: PASS (cache path unchanged)
- Cold-path baseline: FAIL (same 64.7% error, calibration_metadata not passed yet)

**Blocker conditions**:
- Unit test FAILS → mark Phase B.1 blocked, document error signature
- Warm-cache regression FAILS → mark Phase B.2 blocked, regression introduced
- Cold-path test PASSES unexpectedly → investigate, may skip Phase B.3-B.4 refactor

## Compliance Matrix

### Non-Negotiables Adherence

1. **No production edits by Galph**: ✅ Planning only, no code changes
2. **Evidence→Action contract**: ✅ Phase B planning specifies exact next production edit (dbex/refinement/scaling_utils.py::apply_sqrt_spot_scale) + validating pytest nodes (3 selectors)
3. **Dominant-hypothesis lock**: ✅ Confidence ≥0.7 (64.7% drift, calibration_metadata not threaded), DecisionStatus=patch_ready
4. **ARCH/Impl consistency gate**: ✅ ARCH-CONTRACT-001/002 cited, failure classified as architecture conformance (duplicated scaling logic)
5. **Arch conformance must create enforcement**: ✅ Phase A.1/A.2 enforcement tests already exist
6. **Type discipline**: ✅ architecture initiative, not bugfix (centralizing owner API, not changing semantics)

### Loop Discipline

- **Implementation floor**: ✅ Phase B.1-B.2 planning (1 loop) followed by implementation next loop (not docs-only sequence)
- **Dwell enforcement**: ✅ Loop 1 for Phase B planning, implementation delegated to loop i=111
- **Initiative budget**: ✅ Phase A: 3 loops (within budget), Phase B.1-B.2: 1 planning loop (on schedule)
- **Environment Freeze**: ✅ No environment changes requested

### Findings Paydown

- **SCALE-002** (applied): Canonical API encodes sqrt(spot_scale_override) pattern from SCALE-002
- **SCALE-008** (applied): Warm-cache baseline authority validated by Phase A.1 test
- **SCALE-009** (applied): Multi-factor parity issue (mask, N_cells, baseline, calibration threading) addressed by canonical API + threading
- **ARCH-FACTORY-001** (deferred): Calibration threading to factory out of scope for Phase B.1-B.2 (factory changes deferred to future initiative)
- **PROBE-FREEZE-001** (enforced): No plan-local probes requested; architecture enforcement tests used

## Decision Rationale

### Why Phase B.1-B.2 Before B.3-B.4?

**TDD Approach**: Establish infrastructure (canonical API + threading) before refactoring consumers.

**Benefits**:
1. Unit test validates canonical API in isolation (no consumer complexity)
2. Signature change introduces calibration_metadata parameter without breaking existing call sites (backward compatibility)
3. Cold-path test baseline preserved (FAIL expected until B.3-B.4 refactor)
4. Smaller loop scope reduces risk (2-step implementation vs 4-step refactor)

**Risks mitigated**:
- Signature change breaking call sites → default None parameter ensures backward compatibility
- Canonical API implementation bugs → unit test catches before consumer refactor
- Regression in warm-cache path → warm-cache regression test detects immediately

### Why Not Refactor Stage A in Phase B.1-B.2?

**Scope discipline**: Phase B.1-B.2 establishes infrastructure; Phase B.3-B.4 refactors consumers.

**Rationale**:
1. Stage A warm-cache path already works (Phase A.1 test passed)
2. Refactoring Stage A requires validation with Stage A smoke tests (larger scope)
3. Splitting into 2 loops (B.1-B.2 infrastructure, B.3-B.4 refactor) allows incremental validation

**Next loop**: Phase B.3-B.4 will refactor stage_a.py:442-443 and reconstruction.py:203-208 to use canonical API, expecting both Phase A.1/A.2 tests to PASS.

## Next Loop Delegation (Loop i=111)

### Mode
none (production implementation)

### ActionType
implementation_ready

### DecisionStatus
patch_ready

### Focus
[ARCH-IMPL-CONFORMANCE-001] Phase B.1-B.2 — Canonical API + Calibration Threading

### Mapped Tests
- `tests/dbex/refinement/test_scaling_utils.py::test_apply_sqrt_spot_scale` (new, expect PASS)
- `tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale` (regression, expect PASS)
- `tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path` (baseline, expect FAIL)

### Exit Criteria
1. Unit test PASS (all 5 test cases)
2. Warm-cache regression PASS (no regressions)
3. Cold-path baseline FAIL (same 64.7% error, refactor deferred)
4. Artifacts written to reports directory
5. Summary.md documents outcome, metrics, next actions

### Forbidden
- No Stage A refactor (defer to B.3)
- No reconstruction consumer refactor (defer to B.4)
- No call-site updates (backward compatibility)
- No new probes

### Artifacts Path
`plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T000000Z/`

## Cross-References

- **Phase A.2 Summary**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T230000Z/summary.md`
- **Phase A.1 Outcome**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T220000Z/phase_a1_outcome_analysis.md`
- **Phase A Kickoff**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T150000Z/summary.md`
- **Implementation Plan**: `plans/active/ARCH-IMPL-CONFORMANCE-001/implementation.md`
- **Fix Plan Entry**: docs/fix_plan.md §[ARCH-IMPL-CONFORMANCE-001]

---

**Turn complete. Phase B.1-B.2 planning artifacts ready for Ralph implementation loop i=111.**
