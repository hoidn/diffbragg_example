# Phase 8 Assessment — Default Enforcement & E2E Validation

**Initiative:** TORCH-REFINE-004 (Stage B Per-Reflection Mode Migration)

**Date:** 2025-11-24T095000Z

**Mode:** Planning (supervisor loop, assessment + decision)

**Objective:** Assess Phase 7 completion, identify remaining work for spec compliance (per-reflection as default), plan Phase 8/9 execution.

---

## Executive Summary

**Phase 7 Status:** ✓ COMPLETE (commit 936d6e0, 2025-11-24T092549Z)
- ASU-based per-reflection modifiers integrated into Stage B loop
- Dynamic optimizer selection (LBFGS < 10K params, Adam ≥ 10K params)
- Mode branching architecture (per_reflection vs shell)
- **However:** test_stage_b_per_reflection_smoke **fell back to shell mode** because crystal_symmetry unavailable in test fixture

**Critical Gap Identified:** Spec Violation
- **spec-db-workflow.md:59:** "Per-reflection Fhkl multipliers mapped to unique ASU indices **SHALL be the default (Parity Mode)**"
- **Current state:** Shell mode is default (`stage_b_mode` parameter defaults to "shell" in RefinementConfig)
- **Exit Criterion #1 STATUS:** ❌ NOT MET — per-reflection not yet default, not yet validated end-to-end

**Remaining Work:**
1. **Phase 8a — Fix test fixture:** Ensure `crystal_symmetry` is present in test fixture so per-reflection path actually runs
2. **Phase 8b — Default enforcement:** Change RefinementConfig default to `stage_b_mode="per_reflection"`
3. **Phase 8c — E2E validation:** Validate full per-reflection convergence (not just fallback)
4. **Phase 9 — Documentation:** Update test registry, add REFINE-006 finding

---

## 1. Phase 7 Completion Analysis

### What Was Delivered (commit 936d6e0)

**Code Changes (~271 lines):**
1. ASU mode initialization in `_build_stage_b_params` (~40 lines)
2. Dynamic optimizer selection (~32 lines)
3. ASU modifier application in closure (~29 lines)
4. ASU telemetry fields (~35 lines dynamic attachment)
5. Test suite: `test_stage_b_per_reflection_smoke` (~135 lines)

**Validation Results:**
- ✓ Compilation passed
- ✓ Phase 6 unit tests passed (5/5, 1.04s)
- ✓ Shell mode regression passed (13.66s)
- ⚠️ Per-reflection smoke: **fallback to shell mode verified** (crystal_symmetry unavailable)
- ✓ Collection check passed

**Findings Applied:** REFINE-001/002/005, SCALE-001/002, PHYSICS-LOSS-001, POLICY-001, ARCH-ENGINE-002, spec:59/60/61/107

### What Was NOT Validated

**Critical:** Per-reflection path never actually executed in validation
- Test fixture lacks `crystal_symmetry` in hkl_metadata
- `compute_hkl_asu_map` falls back to shell mode per spec:60
- **No end-to-end validation** that per-reflection modifiers actually work

**Risk Assessment:** MEDIUM-HIGH
- Code is implemented but untested in production path
- ASU map computation, modifier initialization, and application are proven via unit tests (Phase 6)
- But full optimization loop (Adam with ASU modifiers, convergence, telemetry) is unvalidated

---

## 2. Exit Criteria Gap Analysis

### Exit Criterion #1: Per-reflection as default (spec-db-workflow.md §7)
**Status:** ❌ NOT MET
- **Requirement:** Per-reflection SHALL be the default
- **Current:** Shell mode is default
- **Gap:** 1-line config change + full E2E validation

### Exit Criterion #2: Shell mode available as fallback
**Status:** ✓ MET
- Shell mode preserved behind `stage_b_mode="shell"` config
- Fallback logic validated (spec:60 compliance)

### Exit Criterion #3: Smoke tests validate convergence and telemetry
**Status:** ⚠️ PARTIALLY MET
- Shell mode convergence: ✓ validated
- Per-reflection convergence: ❌ not validated (fallback occurred)
- Per-reflection telemetry: ❌ not validated (fallback occurred)

### Exit Criterion #4: Documentation updated
**Status:** ❌ NOT MET
- Phase 9 deferred

---

## 3. Root Cause — Test Fixture Missing crystal_symmetry

### Investigation

**Test Fixture:** `tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke`
- Uses `small` detector configuration from smoke test infrastructure
- HKL grid built via existing Stage A smoke test path
- **Issue:** `hkl_metadata` dict does not include `crystal_symmetry` key

**Where crystal_symmetry Comes From:**
- Loaded from MTZ file via cctbx.miller in production paths
- MTZ contains space group, unit cell, symmetry operations
- Smoke tests use synthetic fixtures (golden_data + nanobrag_torch forward model)

**Options to Fix:**
1. **Option A (Minimal):** Mock crystal_symmetry in test fixture
   - Add `from cctbx import sgtbx` to test
   - Create synthetic `crystal.symmetry(unit_cell=..., space_group_symbol="P1")`
   - Inject into hkl_metadata dict before Stage B call
   - **Pros:** Fast (<30 min), isolated test change, no production code impact
   - **Cons:** Test diverges from production reality (synthetic symmetry)

2. **Option B (Production):** Use real MTZ file in smoke test
   - Extend smoke test infrastructure to load MTZ from `golden_data/refGeom/`
   - Extract crystal_symmetry from MTZ via cctbx.miller
   - **Pros:** Test matches production reality exactly
   - **Cons:** Higher complexity (~1-2 hours), may require MTZ file preparation

3. **Option C (Hybrid):** Extract crystal_symmetry from existing Stage A fixtures
   - Stage A already uses `derive_u_matrix_from_mosflm_a_star` which takes `dxtbx_crystal`
   - dxtbx_crystal has `.get_crystal_symmetry()` method
   - Extract and cache in test setup
   - **Pros:** Reuses existing production code path, no new MTZ dependency
   - **Cons:** Requires understanding existing fixture plumbing

---

## 4. Decision Tree — Phase 8 Scope

### Option A: Minimal Fix + Default Enforcement (Recommended)
**Scope:**
1. **Phase 8a:** Fix test fixture (Option A: mock crystal_symmetry, P1 space group)
2. **Phase 8b:** Change default to per_reflection in RefinementConfig
3. **Phase 8c:** Validate per-reflection smoke test (chi² improvement, telemetry fields)
4. **Phase 8d:** Add shell-mode explicit test (`test_stage_b_shell_explicit`) validating fallback
5. **Phase 8e:** Run full regression suite (Stage A/B shell smokes + per-reflection)

**Estimated Effort:** 1 loop (~2-3 hours)
- Fixture fix: 30 min
- Default change: 5 min
- Validation protocol: 1.5 hours
- Decision synthesis: 30 min

**Risk:** LOW
- Mock symmetry is simple (P1 space group, unit cell from fixture)
- Default change is 1-line
- Validation reuses existing test harness

**Confidence:** HIGH (~85%)

### Option B: Production-Grade MTZ Integration
**Scope:**
1. Extract crystal_symmetry from golden_data MTZ files
2. Extend smoke test infrastructure to load MTZ
3. Same 8b-8e as Option A

**Estimated Effort:** 2-3 loops (~4-6 hours)
**Risk:** MEDIUM (MTZ file availability, cctbx loading complexity)
**Confidence:** MEDIUM (~70%)

### Option C: Defer Default Enforcement (NOT Recommended)
**Rationale:** Would leave spec violation (spec:59) unresolved
**Impact:** Exit Criterion #1 remains NOT MET

---

## 5. Recommendation

**APPROVE Option A: Minimal Fix + Default Enforcement**

**Justification:**
1. **Incremental progress:** Unblock per-reflection validation quickly
2. **Spec compliance:** Achieve spec:59 (per-reflection SHALL be default) in single loop
3. **Low risk:** Mock symmetry is straightforward, no production code changes
4. **Test coverage:** Validate both per-reflection path AND explicit shell fallback

**Next Loop Action Type:** ready_for_implementation
- Satisfies implementation floor (production code task: 1-line default change + test fixture fix)
- Validating pytest selector: test_stage_b_per_reflection_smoke (must PASS with per-reflection path)

**Decision Confidence:** HIGH (~85%)

---

## 6. Phase 8 Implementation Checklist

### 8.1 Fix Test Fixture (test_stage_b_per_reflection_smoke)
- [ ] Import `from cctbx import sgtbx, crystal as cctbx_crystal`
- [ ] Create synthetic crystal_symmetry (P1 space group, unit cell from Stage A baseline)
- [ ] Inject into `hkl_metadata` dict with key `"crystal_symmetry"`
- [ ] Verify ASU map computation succeeds (n_asu_unique > 0)

### 8.2 Default Enforcement
- [ ] Change `dbex/nanobrag_refinement.py::RefinementConfig` field `stage_b_mode` default from `"shell"` to `"per_reflection"`

### 8.3 Validation Protocol (5 steps)
1. [ ] Compilation check (`from dbex.nanobrag_refinement import RefinementConfig`)
2. [ ] Phase 6 unit regression (`pytest tests/dbex/test_stage_b_asu_mapping.py -v`)
3. [ ] Per-reflection smoke (`pytest tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke -vv`)
   - Assert ASU telemetry fields present (n_asu_unique, optimizer_type, asu_modifier_stats)
   - Assert optimizer_type matches n_asu threshold (Adam if n_asu ≥ 10K)
   - Assert chi² improvement vs Stage A
4. [ ] Shell explicit test (`test_stage_b_shell_explicit` with config.stage_b_mode="shell")
5. [ ] Full regression suite (Stage A, Stage B shell legacy, Stage B per-reflection)

### 8.4 Decision Synthesis
**Path A (all tests PASS):** Phase 8 ✓ COMPLETE, proceed to Phase 9 (docs)
**Path B (per-reflection smoke FAIL):** Debug ASU map/optimizer/telemetry, max 2 retry cycles
**Path C (regression FAIL):** Rollback default change, debug compatibility
**Path D (crystal_symmetry fixture FAIL):** Escalate to Option B (MTZ integration) or Option C Hybrid

---

## 7. Artifacts Plan

**Output Directory:** `plans/active/TORCH-REFINE-004/reports/2025-11-24T095000Z/`

**Expected Files:**
- `compilation_check.log` — Import validation
- `pytest_phase6_regression.log` — Unit test regression (5 tests)
- `pytest_per_reflection_smoke.log` — Per-reflection E2E validation
- `pytest_shell_explicit.log` — Shell mode explicit test
- `pytest_full_regression.log` — Combined regression suite
- `decision.json` — Decision synthesis (Path A/B/C/D)
- `summary.md` — Turn Summary (per prompt requirements)

---

## 8. Findings to Apply

**Existing:**
- REFINE-001/002/005 (LBFGS scale, acceptance gate, halo mandatory)
- SCALE-001/002 (unscaled structure factors, global post-simulation factor)
- PHYSICS-LOSS-001 (variance-weighted loss)
- POLICY-001 (Environment Freeze, cctbx available)
- ARCH-ENGINE-002 (lazy imports)
- spec:59 (per-reflection SHALL be default)
- spec:60 (shell mode fallback permitted)
- spec:61 (tricubic + halo mandatory)
- spec:107 (optimizer flexibility LBFGS/Adam)

**New (Phase 8):**
- Test fixture pattern: mock crystal_symmetry for ASU validation

---

## 9. Risk Mitigation

**R1: Mock symmetry invalid (P1 space group mismatch)**
- **Likelihood:** LOW
- **Mitigation:** Validate mock symmetry matches Stage A baseline unit cell
- **Fallback:** Extract from dxtbx_crystal (Option C Hybrid)

**R2: ASU map computation time in test**
- **Likelihood:** LOW
- **Mitigation:** Phase 6 unit tests already validated runtime < 10s for P1 ~125 voxels
- **Fallback:** Use smaller HKL grid in test fixture

**R3: Adam optimizer convergence different from LBFGS**
- **Likelihood:** MEDIUM
- **Mitigation:** Validate chi² improvement vs Stage A, not absolute chi² value
- **Fallback:** Document optimizer-specific convergence patterns in REFINE-006

**R4: Telemetry schema divergence**
- **Likelihood:** LOW
- **Mitigation:** Phase 7 already added dynamic telemetry fields, tested in shell mode
- **Fallback:** Extend telemetry validation assertions

---

## 10. Estimated Timeline

**Single Loop Delivery (Option A):** ~2-3 hours

**Breakdown:**
- Phase 8.1 (fixture fix): 30 min
- Phase 8.2 (default change): 5 min
- Phase 8.3 (validation): 1.5 hours (5-step protocol, ~15-20 min per test)
- Phase 8.4 (decision synthesis): 30 min
- Artifacts + commit: 15 min

**Confidence:** HIGH (~85%) — straightforward fixture fix, 1-line default change, validation reuses existing harness

---

## 11. Next Actions

**For Ralph (next loop, ready_for_implementation):**
1. Read this assessment + checklist 8.1-8.4
2. Implement fixture fix (mock crystal_symmetry in test_stage_b_per_reflection_smoke)
3. Change RefinementConfig default to per_reflection
4. Execute 5-step validation protocol
5. Decision synthesis (Path A/B/C/D)
6. Write summary.md with Turn Summary
7. Commit "TORCH-REFINE-004 Phase 8: Default enforcement + per-reflection validation — tests: run"
8. Push and return control to Galph

**For Galph (after Phase 8 complete):**
- Assess Exit Criteria 1-4 status
- Plan Phase 9 (documentation: TESTING_GUIDE.md, TEST_SUITE_INDEX.md, REFINE-006 finding)
- Consider initiative closure if all exit criteria met

---

## 12. Decision

**APPROVE ready_for_implementation: Phase 8 (Option A — Minimal Fix + Default Enforcement)**

**Confidence:** HIGH (~85%)

**Dwell Status:** dwell=0 planning (first planning loop for Phase 8 after Phase 7 completion)

**Implementation Floor:** Satisfied (production code task: 1-line default change, test fixture modification, validation protocol)

**State Transition:** `state=ready_for_implementation` for next loop
