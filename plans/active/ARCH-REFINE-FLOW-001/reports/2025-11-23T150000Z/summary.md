### Turn Summary
Planned Phase D1a (Stage C helper extraction) by authoring comprehensive Do Now directing Ralph to extract `_build_stage_c_params` helper (~120 lines) from inline Stage C code.
Phase D0 baseline complete with both Stage C smoke tests PASSED (small 16.0s, full 40.83s); helper extraction follows proven Phase B/C multi-loop pattern (params → closure → LBFGS + wiring).
Helper will initialize detector offset parameters, optimizer, warm cache/ROI flags, performance counters, and 30 return dict keys per specification; nested function `_apply_baseline_detector_prior` stays inline (handled in D1c).
Next: Ralph extracts helper, validates compilation + regression guard, then Galph plans Phase D1b closure extraction if Path A (both PASS).
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T150000Z/ (input.md protocol, galph_memory.md state)

---

## Phase D1a Planning Summary

### Context
- **Initiative**: ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine
- **Phase**: D1a (Stage C Params Helper Extraction)
- **Loop**: i=227 (Galph planning)
- **Timestamp**: 2025-11-23T150000Z
- **FSM State**: ready_for_implementation (dwell=0, continuing from Phase D0 baseline)

### What Was Done

#### 1. Reviewed Phase D0 Completion
- **Status**: Phase D0 baseline capture COMPLETE (loop i=226, 2025-11-23T143000Z)
- **Test Results**: Both Stage C smoke tests PASSED
  - Small detector: 16.0s (PASS)
  - Full detector: 40.83s (PASS)
- **Bugfixes Applied**: Two blocking bugs fixed in D0
  - UnboundLocalError from redundant `RefinementTelemetry` import (line 3170)
  - NameError for `baseline_detector_distances` (lines 3830-3834)
- **Decision**: Path A (both PASS → Phase D1 ready)
- **Baseline Artifacts**: Captured under plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T143000Z/baseline/

#### 2. Analyzed Inline Stage C Code Structure
- **Total Scope**: Lines 3824-4328 in `dbex/nanobrag_refinement.py` (~504 lines)
- **D1a Target**: Lines 3828-3919 (parameter initialization + optimizer + telemetry accumulators, ~90 lines)
- **D1b Target**: Lines 3921-4295 (nested `compute_loss_stage_c` + `closure_stage_c`, ~374 lines)
- **D1c Target**: Lines 4296-4328 + wiring (LBFGS execution + telemetry aggregation + call site integration, ~32 lines + wiring)

#### 3. Authored Phase D1a Do Now Protocol
Created comprehensive 11-step extraction protocol in `input.md`:

**Extraction Steps** (11 total):
1. Create helper function at line ~2700 (after Stage B helpers)
2. Extract `baseline_detector_distances` computation (lines 3830-3834, NameError fix from D0)
3. Extract Stage A parameter freezing (lines 3836-3838, `p.requires_grad = False` loop)
4. Extract `distance_offset_raw` initialization (lines 3840-3844, trainable torch.zeros)
5. Extract warm cache logic (lines 3845-3851, `stage_c_use_warm_cache` conditional)
6. Extract performance counters (lines 3852-3854, mutable list accumulators)
7. Extract ROI mode logic (lines 3855-3870, `roi_slices_by_pid` + counts)
8. **SKIP** `_apply_baseline_detector_prior` nested function (handled in D1c wiring)
9. Extract LBFGS optimizer (lines 3889-3897, torch.optim.LBFGS construction)
10. Extract telemetry accumulators (lines 3899-3919, loss traces, chi² traces, variance floor stats)
11. Return dict with 30 keys (all parameters, flags, counters, accumulators)

**Helper Signature Specification**:
- **Function Name**: `_build_stage_c_params`
- **Parameters** (11): config, device, dtype, n_panels, baseline_detector, detector, sampled_panel_ids, panel_slices, stage_a_ctx, sigma_floor_sq_cache, params
- **Return Type**: `Dict[str, Any]`
- **Return Keys** (30): distance_offset_raw, stage_c_params, stage_c_optimizer, baseline_detector_distances, warm cache flags (2), ROI mode flags/counts (5), performance counters (3), loss trace accumulators (5), chi² trace accumulators (3), masked_mse trace accumulators (3), variance floor stats (2), sigma_floor_sq_tensor_stage_c

**Validation Protocol** (5 checks):
1. Compilation check via `python -c "import dbex.nanobrag_refinement"`
2. Regression guard (Stage C smoke small detector, should PASS unchanged)
3. Helper signature matches specification
4. All 30 dict keys present in return value
5. Approximately 90-120 lines extracted from inline code

**Decision Synthesis** (4-Path Template):
- **Path A** (Compilation PASS + Regression PASS): Helper extraction SUCCESSFUL → Phase D1b next loop
- **Path B** (Compilation FAIL): Syntax/import error → debug, fix, retest
- **Path C** (Regression FAIL): Test infrastructure issue → investigate, revert if confirmed
- **Path D** (Signature mismatch): Missing/incorrect keys → fix return dict, retest

#### 4. Key Extraction Decisions

**1. Skip Nested Function Extraction**:
- `_apply_baseline_detector_prior` (lines 3872-3887) stays inline for now
- Rationale: Nested function references local scope (baseline_detector_distances, distance_offset_raw); calling logic better handled during D1c wiring
- Simplifies D1a extraction (removes ~16 lines of complexity)

**2. Freeze Stage A Parameters Inside Helper**:
- Lines 3836-3838 loop (`for p in params: p.requires_grad = False`) moves into helper
- Rationale: Stage C freezes Stage A gradients before training detector offsets; logically part of Stage C parameter initialization

**3. Extract Telemetry Accumulators Early**:
- Lines 3899-3919 (loss/chi²/masked_mse traces, variance floor stats) extracted in D1a
- Rationale: These are initialization (empty lists, tuples with infinity values), not closure logic; belong in params helper per Phase B pattern

**4. Return 30 Dict Keys**:
- Comprehensive return dict ensures D1c wiring has all required state
- Mirrors Phase B `_build_stage_b_params` pattern (28 keys)
- Includes mutable accumulators (lists) to support closure mutation

#### 5. Updated State Tracking
- **galph_memory.md**: Added Phase D1a planning entry (2025-11-23T150000Z)
- **FSM transition**: ready_for_implementation (dwell=0, continuing from D0 baseline)
- **Artifacts path**: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T150000Z/phase_d1a/

### Decision Tree (4 Paths)

Ralph's Phase D1a execution will determine next loop direction:

- **Path A (Compilation PASS + Regression PASS)**: Helper extraction SUCCESSFUL
  - Galph plans Phase D1b next loop (extract `_build_stage_c_lbfgs_closure` ~400 lines)
  - Estimated timeline: 2-3 more loops (D1b closure extraction, D1c wiring + validation)

- **Path B (Compilation FAIL)**: Syntax error or import error
  - Ralph debugs syntax, fixes imports, retests compilation
  - Do NOT proceed to D1b until compilation clean

- **Path C (Regression FAIL)**: Test infrastructure issue (should not happen, helper not wired)
  - Ralph investigates test regression
  - Reverts extraction if confirmed
  - Escalates to Galph with blocker report

- **Path D (Signature Mismatch)**: Missing or incorrect return keys
  - Ralph fixes return dict to match specification (all 30 keys)
  - Retests compilation + regression
  - Do NOT proceed to D1b until signature correct

### Phase D Multi-Loop Strategy

**Loop i=225 (Complete)**: Phase D0 baseline capture
- Collection check (1 test collected)
- Small detector PASS (16.0s)
- Full detector PASS (40.83s)
- Decision: Path A → Phase D1 ready

**Loop i=227 (Current)**: Phase D1a params helper extraction
- Extract `_build_stage_c_params` (~120 lines)
- Compilation check + regression guard
- Decision synthesis (Path A/B/C/D)

**Loop i=228 (Next, if Path A)**: Phase D1b closure helper extraction
- Extract `_build_stage_c_lbfgs_closure` (~400 lines)
- Nested functions: `compute_loss_stage_c` + `closure_stage_c`
- Compilation check + regression guard (helper still not wired)

**Loop i=229 (Estimated, if D1b PASS)**: Phase D1c LBFGS execution + wiring
- Extract `_run_stage_c_lbfgs` (~50 lines)
- Wire all three helpers into `run_nanobrag_refinement`
- Remove inline Stage C code (lines 3824-4328, ~504 lines reduction)
- Validate Stage C smoke (small + full detectors, both must PASS)

**Loop i=230 (Estimated, if D1c PASS)**: Phase D2 StageC class wrapper
- Implement `StageC.run()` calling extracted helpers
- Plug into RefinementEngine
- Update telemetry schema with stage_type='C'

**Loop i=231 (Estimated, if D2 PASS)**: Phase D3-D5 validation
- DB-AT selectors (DB-AT-021, DB-AT-024 as applicable)
- Test registry sync (TESTING_GUIDE.md, TEST_SUITE_INDEX.md)
- Mark Phase D COMPLETE

### Comparison: Stage C vs Stage B Extraction Complexity

| Aspect | Stage B (Phase C) | Stage C (Phase D) | Delta |
|--------|------------------|------------------|-------|
| **Total Lines** | ~600 lines | ~504 lines | -16% |
| **Params Helper** | 184 lines (C1a) | ~120 lines (D1a) | -35% |
| **Closure Helper** | 317 lines (C1b) | ~400 lines (D1b) | +26% |
| **LBFGS Helper** | 119 lines (C1c) | ~50 lines (D1c) | -58% |
| **Complexity** | Shell modifiers (20-50 shells), CPU fallback, HKL grid device routing | Detector offsets (n_panels), single device path, no CPU fallback | **Simpler** |
| **Loops** | 7 total (B0 baseline, B1a 3-loop extraction, B1b/B2/B3) | 5-6 estimated (D0 baseline, D1a/D1b/D1c extraction, D2/D3-D5 validation) | -1 to -2 loops |
| **Risk** | MEDIUM-HIGH (CPU fallback bugs, HKL grid transfer corruption) | MEDIUM (detector offset stability, simpler scope) | **Lower** |

### Findings Applied

- **REFINE-007** (docs/findings.md:43): Stage C gate = "stable detector offset" (chi² improvement optional) — helper preserves telemetry for offset tracking
- **PHYSICS-LOSS-001/002** (docs/findings.md:20,21): Variance-weighted loss + sigma_floor — helper extracts `sigma_floor_sq_tensor_stage_c` initialization
- **POLICY-001** (docs/findings.md:66): Environment Freeze — helper extraction only, no env changes
- **TESTING-003** (docs/findings.md:56): Test registry updates deferred to D1c (no selector changes in D1a)
- **CONFORMANCE-001** (docs/findings.md:28): Canonical environment flags for regression guard
- **RUNTIME-001** (docs/findings.md:29): `NANOBRAGG_DISABLE_COMPILE=1` set for Stage C smoke

### Spec Alignment

- **docs/spec-db-workflow.md §7**: Stage C definition (detector offset refinement)
- **docs/spec-db-runtime.md**: Device/dtype neutrality preserved in helper signature
- **docs/spec-db-core.md**: Variance-weighted loss contract (telemetry accumulators extracted)
- **docs/architecture/pytorch_design.md**: RefinementStage protocol (preparing for StageC class in D2)

### Next Loop Preview

**If Path A (Compilation PASS + Regression PASS)**:
- **Loop i=228**: Galph plans Phase D1b (closure helper extraction)
- **Strategy**: Extract `_build_stage_c_lbfgs_closure` (~400 lines)
  - Nested `compute_loss_stage_c` function (~300 lines, variance-weighted loss logic)
  - Nested `closure_stage_c` function (~100 lines, LBFGS closure wrapper)
  - Preserve lexical scope captures (Stage A params, Stage C params, telemetry accumulators)
  - Maintain lazy imports (nanobrag_bridge, nanobrag_torch inside nested functions)
- **Validation**: Compilation check + regression guard (helper still not wired)
- **Expected Outcome**: Both checks PASS → Phase D1c wiring next loop

**If Path B/C/D (Compilation/Regression/Signature FAIL)**:
- Ralph debugs blocker
- Escalates to Galph with error signature + root cause hypothesis
- Do NOT proceed to D1b until D1a clean

### Implementation Floor Compliance

✅ **FSM enforcement satisfied**:
- Last loop (i=226): ready_for_implementation (Phase D0 baseline)
- This loop (i=227): ready_for_implementation (Phase D1a helper extraction)
- Do Now includes: production code task (helper extraction ~120 lines) + validation protocol (compilation + regression) + decision synthesis (4-path template)
- Dwell remains 0 (continuing ready_for_implementation mode)

### Artifacts Structure

```
plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T150000Z/
├── phase_d1a/
│   ├── compilation_check.log (expected from Ralph)
│   ├── pytest_stage_c_regression.log (expected from Ralph)
│   ├── helper_diff.patch (expected from Ralph)
│   ├── decision.md (expected from Ralph, 4-path synthesis)
│   ├── metrics.json (expected from Ralph, T0 probe)
│   └── summary.md (expected from Ralph, Turn Summary + detailed summary)
└── summary.md (this file — Galph's planning summary)
```

### Confidence Assessment

- **Phase D1a protocol completeness**: VERY HIGH (99%)
- **Helper extraction success**: HIGH (90% — simpler than Stage B, proven pattern)
- **Compilation + regression PASS**: VERY HIGH (95% — helper not wired, no behavior change)
- **Overall Phase D completion**: MEDIUM-HIGH (75% — depends on D1b closure extraction complexity)

### Timeline Estimate

- **Phase D1a (this loop)**: Helper extraction + validation (1 loop, ~1-2 hours wall time)
- **Phase D1b (next loop, if Path A)**: Closure extraction + validation (1 loop, ~2-3 hours wall time)
- **Phase D1c (loop i=229)**: LBFGS extraction + wiring + validation (1 loop, ~3-4 hours wall time)
- **Phase D2 (loop i=230)**: StageC class wrapper (1 loop, ~2-3 hours wall time)
- **Phase D3-D5 (loop i=231)**: DB-AT validation + registry sync (1-2 loops, ~3-6 hours wall time)
- **Total Phase D estimate**: 5-6 loops (~12-18 hours wall time) if all extraction steps clean

### Roadmap Progress

**Tier 1 (Core Physics & Stability)**: ✅ COMPLETE
- ✅ TORCH-GEOMETRY-CONVERGENCE-001 (quaternion U-matrix convergence)
- ✅ TORCH-GEOMETRY-UB-REALIGN-001 (incremental UB parameterization)
- ✅ PHYSICS-LOSS-001 (variance-weighted loss)
- ✅ REFINE-SMOKE-CANONICAL (Stage B/C convergence)

**Tier 2 (Architectural Maturity)**: 🔄 IN PROGRESS (75% complete)
- ✅ ARCH-REFINE-FLOW-001 Phase A (Stage Interface & Engine Skeleton)
- ✅ ARCH-REFINE-FLOW-001 Phase B (Stage A Extraction)
- ✅ ARCH-REFINE-FLOW-001 Phase C (Stage B Extraction)
- ✅ ARCH-REFINE-FLOW-001 Phase D0 (Stage C Baseline)
- ⏳ **ARCH-REFINE-FLOW-001 Phase D1a (Stage C Helper Extraction) — CURRENT FOCUS**
- ⬜ ARCH-REFINE-FLOW-001 Phase D1b/D1c (Closure + LBFGS + Wiring)
- ⬜ ARCH-REFINE-FLOW-001 Phase D2 (StageC Class Wrapper)
- ⬜ ARCH-REFINE-FLOW-001 Phase D3-D5 (Validation + Registry Sync)
- ⬜ ARCH-REFINE-FLOW-001 Phase E (Orchestration Hooks)

**Tier 3 (Feature Completeness)**: ⬜ PENDING
- ⬜ TORCH-REFINE-004 (Stage B Per-Reflection Mode) — blocked on Phase E
- ⬜ PERF-WARM-SIM-001 (Warm Simulator) — deferred until engine refactor complete

### Notes

- **No production code changes this loop** — planning only (Galph authored input.md)
- **Implementation floor satisfied** — Do Now contains production code task (helper extraction) + validation
- **FSM discipline maintained** — dwell=0, continuing ready_for_implementation mode
- **Pattern reuse** — Phase D1a mirrors Phase B1a/C1a proven extraction methodology
- **Risk mitigation** — 4-path decision tree handles all extraction outcome scenarios
- **Simplification** — Skip `_apply_baseline_detector_prior` extraction (handle in D1c reduces D1a complexity)
