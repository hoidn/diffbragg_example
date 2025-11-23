### Turn Summary
Validated Phase C extraction: Stage B small detector smoke PASSED but full detector FAILED with CUDA OOM due to missing CPU fallback logic in engine delegation path.
Root cause identified at high confidence (95%): lines 3029-3108 skip CPU fallback initialization that inline path computes at lines 2174-2184; fix requires 4-10 line addition before engine instantiation.
Next: implement CPU fallback in engine delegation path following reference pattern, then rerun full validation suite.
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T084458Z/ (pytest_stage_b_small.log, pytest_stage_b_full.log, collect_db_at_024.log, phase_c_decision.md)

---

### Turn Summary (Galph, Loop i=211)
Completed Phase C extraction (helpers + wrapper + engine delegation + bugfix) and authored full validation protocol for Stage B smokes (small/full detectors) + DB-AT-024 mapping parity.
Next: Ralph executes 12-step validation (run tests, extract metrics, decision synthesis); if all PASS → Phase C COMPLETE → plan Phase D (Stage C extraction) next loop.
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T084458Z/ (input.md, summary.md)

---

## Loop i=211 Planning Summary

**Objective:** Validate Phase C Stage B extraction completion via comprehensive test suite (smokes + DB-AT selectors).

**Context:**
Phase C extraction is COMPLETE:
- **C0**: Baseline artifacts collected (2025-11-23T061726Z)
- **C1a**: 3 helpers extracted in 3 sub-loops (i=200-202):
  - `_build_stage_b_params` (~184 lines)
  - `_build_stage_b_lbfgs_closure` (~317 lines, TWO nested functions)
  - `_run_stage_b_lbfgs` (~118 lines)
- **C1b**: StageB wrapper class implemented (2025-11-22T230000Z, commit visible in fix_plan line 205)
- **C2**: Engine delegation A→B already implemented (verified dbex/nanobrag_refinement.py:2988-3100)
  - `stage_a_b_mode = (not config.enable_stage_c and config.enable_stage_b)`
  - `RefinementEngine(stages=[StageA(), StageB()])`
  - Telemetry aggregation via engine.run()
- **Bugfix**: Cell param base bug fixed (loop i=210/Ralph, commit a038ac1)
  - Problem: StageB.run() line 163 used `crystal.get_unit_cell().parameters()` (current/perturbed) instead of `baseline_crystal.get_unit_cell().parameters()` (baseline)
  - Fix: Added baseline_crystal validation guard + replacement at line 163
  - Validation: test_stage_b_shell_modifiers PASSED with 23.7% Stage B improvement, chi² offset eliminated

**Remaining Phase C Tasks (from implementation.md:208-211):**
- **C3**: Ensure Stage B telemetry complete (stage_type, mode, shell_modifier stats, Stage A metadata propagation)
- **C4**: Rerun test_stage_b_shell_modifiers on small + full detectors, verify REFINE-008 gates
- **C5**: Execute DB-AT selectors (DB-AT-024 mapping parity)

**Validation Strategy:**
Comprehensive 12-step protocol combining C3/C4/C5 tasks in single loop:
1. Review Phase C completion evidence (artifacts, code review)
2. Run Stage B smoke small detector (~15s expected)
3. Run Stage B smoke full detector (~20s expected, CPU fallback per PERF-WARM-011)
4. Extract smoke metrics via T0 inline probe (test status + telemetry structure)
5. Verify telemetry completeness (stage_type, mode, shell_modifier stats, Stage A frozen params)
6. Run DB-AT-024 collection check (verify selector active)
7. Run DB-AT-024 mapping parity (~30s expected)
8. Extract DB-AT-024 metrics via T0 inline probe
9. Decision synthesis per 4-path template (A: COMPLETE, B: smoke FAIL, C: telemetry incomplete, D: DB-AT-024 FAIL)
10. Update implementation.md Phase C status (mark C3/C4/C5 complete if Path A)
11. Write summary.md with Turn Summary block
12. Commit and push

**Decision Tree:**
```
┌─ All 3 tests PASS + telemetry complete?
│  ├─ YES → Path A: Phase C COMPLETE → Galph plans Phase D (Stage C extraction) next loop
│  └─ NO  → Check which failed:
│     ├─ Stage B smoke → Path B: Debug execution (engine delegation wiring, helper signatures, baseline_crystal parameter)
│     ├─ Telemetry incomplete → Path C: Fix telemetry (StageB.run() packaging code, Stage A metadata propagation)
│     └─ DB-AT-024 → Path D: Mapping regression (bridge helpers verification, HKL grid comparison)
```

**Expected Outcome:**
Path A (HIGH confidence ~80%):
- Stage B smokes PASS on both detectors (small ~15s, full ~20s CPU fallback)
- Stage B improvement ≥3% per REFINE-008 calibrated gate
- Telemetry complete: stage_type="B", mode="shell_modifiers", shell_modifier_<n> param_deltas with initial/final/delta, Stage A frozen params (log_scale, cell, misset)
- DB-AT-024 PASSED: median correlation ≥0.2, localization ≥90%
- Phase C marked COMPLETE (2025-11-23T084458Z)
- Next loop: Galph plans Phase D (Stage C extraction following proven multi-loop strategy)

**Risk Assessment:**
- **Stage B smoke failure risk**: LOW (~10%) — bugfix just verified (loop i=210 PASSED), engine delegation code exists (verified via grep), StageB wrapper exists (ls confirmed)
- **Telemetry incomplete risk**: MEDIUM (~30%) — StageB.run() may not package all required fields (stage_type, mode, shell_modifier stats) per Phase A4 schema
- **DB-AT-024 failure risk**: LOW (~5%) — bridge helpers unchanged during Phase C extraction, HKL grid unaffected by Stage B refactoring

**Findings Applied:**
- REFINE-008 (Stage B ±1% gate calibrated to ≥3% improvement)
- PHYSICS-LOSS-001/002 (variance-weighted loss + sigma_floor guard)
- PERF-WARM-011/012 (CPU fallback for canonical Stage B, warm cache reuse)
- TESTING-003 (collection verification before pytest execution)
- CONFORMANCE-001 (KMP_DUPLICATE_LIB_OK=TRUE)
- RUNTIME-001 (NANOBRAGG_DISABLE_COMPILE=1)

**Artifacts:**
- `input.md` (12-task Do Now with full validation protocol)
- `summary.md` (this file, Turn Summary prepended)

**Next Actions:**
Ralph executes Phase C validation protocol. Decision outcome determines next loop:
- **Path A (all tests PASS)**: Galph plans Phase D (Stage C extraction) next loop
- **Path B (smoke FAIL)**: Galph reviews blocker and debugs execution
- **Path C (telemetry incomplete)**: Galph reviews telemetry gaps and plans fix
- **Path D (DB-AT-024 FAIL)**: Galph reviews mapping regression and escalates if needed
