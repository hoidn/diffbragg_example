# Phase B2b(i) refine_one CLI Wiring — Reverification Status

## Context

Ralph received input.md requesting Phase B2b(i) work (wire refine_one CLI panel loop to factory). However, git history shows this work was **already completed** in commit `7a3d3ab` (2025-11-23T240000Z loop).

## Code Status Verification

**Commit:** `7a3d3ab` — TORCH-API-ALIGN-001 Phase B2b(i): Factory wiring (refine_one CLI)

**Files Modified:**
- `dbex/refine_one.py` lines 438-461: Panel loop wired to `create_unified_simulator` factory
- Config creation preserved (lines 407-436) for downstream Stage A refinement

**Code Changes Applied:**
1. ✓ Factory import added at function scope (line 439): `from dbex.refinement.helpers import create_unified_simulator`
2. ✓ Manual Detector/Crystal instantiation removed (previously lines 439-440)
3. ✓ Manual HKL attachment removed (previously lines 447-448)
4. ✓ beam_config branching eliminated (previously lines 451-465)
5. ✓ Factory call replaces 41 lines with 18 lines (net -23 lines)
6. ✓ sqrt_scale_value from factory used for post-run scaling (line 460)
7. ✓ Config creation PRESERVED for downstream Stage A refinement (crystal_config needed at line 510)

## Test Reverification Results

**Date:** 2025-11-23T240000Z (Ralph loop i=245)

### DB-AT-024 Mapping Parity Regression Guard
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_DETECTOR_SIZE=full \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBAT024_ARTIFACT_DIR=plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T240000Z \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke
```

**Result:** ✅ **PASSED** (31.88s, 1 passed, 6 warnings)
- Mapping parity UNCHANGED
- Factory wiring introduces zero regression

### Stage A Expansion Smoke Test
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_DETECTOR_SIZE=small \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
```

**Result:** ✅ **PASSED** (12.45s, 1 passed, 5 warnings)
- refine_one CLI forward simulation + Stage A refinement unaffected
- Telemetry structure correct

## Implementation Plan Status

**File:** `plans/active/TORCH-API-ALIGN-001/implementation.md` line 65

**Current Status:**
```
- [x] B2: Replace duplicate wiring — COMPLETE 2025-11-24T000000Z
  - B2a forward helpers COMPLETE 2025-11-23T220000Z (-56 lines)
  - B2b(i) refine_one CLI COMPLETE 2025-11-23T240000Z (-23 lines)
  - B2b(ii) scope clarification: no forward-only panel loops exist in nanobrag_refinement
```

## Fix Plan Ledger Status

**File:** `docs/fix_plan.md` line 68

**Attempts History Entry:**
> 2025-11-23T240000Z (implementation) — **Phase B2b(i) refine_one CLI Wiring COMPLETE — DB-AT-024 PASSED, Stage A Smoke PASSED.** [... full entry documenting completion ...]

## Supervisor Scope Clarification

**Commit:** `f7ea9c9` — SUPERVISOR: TORCH-API-ALIGN-001 Phase B2 complete — scope clarification

**Decision:** Phase B2 is **COMPLETE**. Phase B2b(ii) is NOT APPLICABLE (no forward-only panel loops exist in `nanobrag_refinement.py`). All 12 Simulator instantiations in `nanobrag_refinement.py` are categorized as:
- **Category A (7):** Refinement closures requiring autograd (MUST NOT wire to factory)
- **Category B (2):** Post-refinement forward models (low-priority, deferred)
- **Category C (3):** Stage A warm-cache context (PERF-WARM-SIM-001 scope)

## Verdict

**Phase B2b(i) Status:** ✅ **COMPLETE** (commit 7a3d3ab, validated 2025-11-23T240000Z)

**Phase B2 Status:** ✅ **COMPLETE** (supervisor scope clarification commit f7ea9c9)

**Test Status:** ✅ **ALL PASSING** (reverified 2025-11-23T240000Z Ralph loop i=245)
- DB-AT-024: PASSED (31.88s)
- Stage A expansion: PASSED (12.45s)

**Exit Criterion #1:** ✅ **SATISFIED**
> Unified simulator factory validates shape/dtype/device and is used by forward helpers (zero-iter + torch-grad paths), refine_one, and panel loops in nanobrag_refinement.

**Interpretation:** All **forward-only** paths use factory. Refinement closures correctly excluded per GRADIENT-001 (autograd graph preservation requirement).

## Next Actions

**Immediate:** No code changes required. Phase B2b(i) work requested in input.md is already complete and validated.

**Next Phase:** Phase B3 — ExperimentModel adapter implementation
- Add adapter path constructing ExperimentModel(..., param_init="frozen")
- Behind explicit flag (default OFF)
- Parity-first approach
- Validate via Phase A3 parity test (test_experiment_parity.py::test_parity_small_fixture)

## Artifacts

**This Reverification Loop (2025-11-23T240000Z Ralph i=245):**
- `phase_b2b_i_reverification.md` (this file)
- `pytest_db_at_024_reverify.log` (DB-AT-024 test log, 31.88s, PASSED)
- `pytest_stage_a_expansion_reverify.log` (Stage A smoke log, 12.45s, PASSED)

**Original Phase B2b(i) Loop (2025-11-23T240000Z Ralph i=243):**
- `phase_b2b_i_decision.md` (original implementation decision)
- `pytest_db_at_024.log` (original test log, 31.85s, PASSED)
- `pytest_stage_a_expansion.log` (original test log, 12.37s, PASSED)
- `summary.md` (original turn summary)

## Confidence

**HIGH** (~99%) that Phase B2b(i) is complete and stable:
1. ✅ Code changes present in current HEAD (commit 7a3d3ab)
2. ✅ Tests PASSED in original loop (31.85s, 12.37s)
3. ✅ Tests PASSED in reverification (31.88s, 12.45s)
4. ✅ Implementation plan checklist marked complete
5. ✅ Fix plan ledger documents completion
6. ✅ Supervisor scope clarification confirms Phase B2 complete
7. ✅ Zero regressions observed
