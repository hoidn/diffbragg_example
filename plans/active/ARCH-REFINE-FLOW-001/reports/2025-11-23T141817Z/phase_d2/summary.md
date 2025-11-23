### Turn Summary
Planned Phase D2 (StageC class wrapper) by authoring comprehensive Do Now directing Ralph to implement dbex/refinement/stage_c.py following proven StageB pattern from Phase C1b.
Phase D1c complete with all 3 Stage C helpers extracted and wired successfully (commit 7a92a87, net reduction 124 lines, both regression tests PASSED); wrapper will call helpers directly and package telemetry with stage_type="C" + mode="detector_offsets".
Next: Ralph implements StageC class (~400 lines mirroring StageB structure), validates via compilation check + regression guards (small+full detector) + engine contract test.
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/phase_d2/ (input.md protocol, galph_memory.md state)

---

## Phase D2 Planning Summary

### Context
- **Initiative**: ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine
- **Phase**: D2 (StageC Wrapper Class)
- **Loop**: i=230 (Galph planning)
- **Timestamp**: 2025-11-23T141817Z
- **FSM State**: ready_for_implementation (dwell=0, continuing from Phase D1c completion)

### What Was Done

#### 1. Reviewed Phase D1c Completion
- **Status**: Phase D1c COMPLETE (loop i=229, commit 7a92a87, 2025-11-23T141817Z)
- **Test Results**: Both Stage C regression tests PASSED
  - Small detector: PASS (exit code 0)
  - Full detector: PASS (exit code 0)
- **Helper Extraction Complete**: All 3 Stage C helpers extracted and wired
  - D1a: `_build_stage_c_params` (156 lines, 30 return keys)
  - D1b: `_build_stage_c_lbfgs_closure` (298 lines, returns tuple of 2 callables)
  - D1c: `_run_stage_c_lbfgs` (296 lines, LBFGS execution + final Bragg + telemetry)
- **Code Reduction**: Net reduction 124 lines (removed 420 lines inline code, inserted ~296 lines helper + ~150 lines wiring)
- **Bugfixes Applied**: Fixed dict key mismatches (target_t, loss_mask_t, sigma_readout_t, misset_deg_for_crystal), added missing lazy imports to helper2 (create_detector_config, create_crystal_config), defined `_apply_baseline_detector_prior` inline (18 lines)

#### 2. Updated Implementation Plan
- Marked Phase D1c checklist item COMPLETE in `plans/active/ARCH-REFINE-FLOW-001/implementation.md:231-240`
- Added detailed D1c completion metadata: helper signatures, lines extracted, net reduction, bugfixes, artifacts path, both regression tests PASSED

#### 3. Updated galph_memory.md
- Appended Phase D2 planning entry (2025-11-23T141817Z)
- FSM transition: ready_for_implementation (dwell=0, last loop ready_for_implementation D1c wiring, now ready_for_implementation D2 wrapper)
- Key observations: All 3 Stage C helpers extracted and wired successfully, StageC wrapper will follow proven StageB pattern (Phase C1b, dbex/refinement/stage_b.py:1-438)

#### 4. Authored Phase D2 Do Now Protocol
Created comprehensive 10-step Do Now in `input.md` directing Ralph to implement StageC class wrapper:

**Implementation Steps** (10 total):
1. Review Phase D1c artifacts (commit 7a92a87 diff, helper signatures, decision.md Path A)
2. Create dbex/refinement/stage_c.py following StageB template (file header, imports, class skeleton)
3. Implement StageC class skeleton (__init__, name property, configure method)
4. Implement StageC.run() method signature (docstring, config guard, lazy imports)
5. Import helpers + unpack inputs (lazy imports inside run() to prevent circular deps)
6. Rebuild Stage A final parameters from telemetry (extract from param_deltas, rebuild tensors on device)
7. Call all 3 Stage C helpers:
   - STEP 1: `_build_stage_c_params` → param_values dict
   - STEP 2: Build telemetry_state + stage_c_context dicts
   - STEP 3: `_build_stage_c_lbfgs_closure` → (compute_loss, closure) tuple
   - STEP 4: `_run_stage_c_lbfgs` → result_c dict
8. Package telemetry (RefinementTelemetry with all fields + stage_type="C" + mode="detector_offsets")
9. Validation protocol (3 tests):
   - Compilation check (import dbex.refinement.stage_c)
   - Regression guard small detector (test_stage_c_detector_microslip, MUST PASS)
   - Regression guard full detector (test_stage_c_detector_microslip, MUST PASS)
   - Engine contract test (test_engine_executes_mock_stage, MUST PASS)
10. Decision synthesis + commit (metrics.json, decision.md, update implementation.md, write summary.md, commit/push)

**Validation Protocol**:
- Compilation check: `python -c "import dbex.refinement.stage_c; from dbex.refinement.stage_c import StageC; print('Compilation: PASS')"`
- Regression guards: Both small + full detector tests MUST PASS with canonical environment flags (AUTHORITATIVE_CMDS_DOC, DBEX_SMOKE_DETECTOR_SIZE, DBEX_SMOKE_SIGMA_SOURCE=cli_override, KMP_DUPLICATE_LIB_OK, NANOBRAGG_DISABLE_COMPILE)
- Engine contract: test_engine_executes_mock_stage MUST PASS (validates RefinementStage protocol compliance)

**Decision Synthesis** (4-Path Template):
- **Path A** (All tests PASS): StageC wrapper SUCCESSFUL → Phase D3-D5 next loop (DB-AT selectors, registry sync, mark Phase D COMPLETE)
- **Path B** (Compilation FAIL): Circular import or helper signature mismatch → debug imports, rerun validation
- **Path C** (Regression FAIL): Helper calls mismatch inline wiring → compare against dbex/nanobrag_refinement.py:3824-4328, fix dict keys
- **Path D** (Engine contract FAIL): RefinementStage protocol violation → verify all 3 protocol methods implemented, check return type is dict

#### 5. Key Implementation Decisions

**1. Follow StageB Pattern Exactly**:
- Template source: dbex/refinement/stage_b.py:1-438 (Phase C1b, proven wrapper pattern)
- Mirror structure: __init__, name property, configure method, run method with lazy imports
- Key differences: Stage C optimizes `distance_offset_raw` (n_panels trainable offsets) instead of `shell_modifier_raw` (n_shells), Stage C requires baseline_detector (NOT optional), param_deltas_c structure is dict with panel IDs as keys

**2. Lazy Imports Inside run() Method**:
- Import helpers (nanobrag_refinement, nanobrag_bridge, nanobrag_torch) inside run() to prevent circular deps
- Mirror StageB lines 89-102 (lazy import placement prevents module-level circular import)

**3. Rebuild Stage A Parameters from Telemetry**:
- Extract log_scale, cell deltas, angle deltas, misset from `stage_a_telemetry['param_deltas']['<key>']['final']`
- Rebuild as tensors on device/dtype (mirror StageB lines 144-192)
- Apply log deltas: `cell_a_tensor = cell_params[0] * torch.exp(log_cell_a_delta)`
- Apply angle deltas: `cell_alpha_tensor = cell_params[3] + torch.tanh(angle_alpha_raw) * max_angle_delta`

**4. Call All 3 Helpers Sequentially**:
- Helper 1: `_build_stage_c_params` → param_values dict (30 keys including distance_offset_raw, optimizer, telemetry accumulators)
- Helper 2: `_build_stage_c_lbfgs_closure` → (compute_loss, closure) tuple
- Helper 3: `_run_stage_c_lbfgs` → result_c dict (status, message, telemetry, bragg_full)

**5. Package Telemetry Per RefinementStage Protocol**:
- Build RefinementTelemetry object with all fields (optimizer, stage, history_size, max_iter, tolerances, roi_sample_fraction, loss/chi²/mse traces, param_deltas, status, message, perf_counters, canonical_* fields)
- PHYSICS-LOSS-001: Dual loss metrics (chi_squared_trace_*, masked_mse_trace_*)
- PHYSICS-LOSS-002: Variance floor (variance_floor_value, variance_floor_clamp_fraction)
- REFINE-007: Detector offset deltas in param_deltas_c (distance_offset_raw: {initial, final, delta} per panel)
- Convert to dict: `telemetry_output = asdict(telemetry_c)`
- Add Phase A4 stage identification: `telemetry_output["stage_type"] = "C"; telemetry_output["mode"] = "detector_offsets"`

#### 6. Findings Applied
- **REFINE-007** (docs/findings.md:58): Stage C gate (≥80% offset reduction OR ≤±0.05mm final, ≤0.05% χ² regression) — preserve improvement gate logic + param_deltas_c telemetry
- **PHYSICS-LOSS-001** (docs/findings.md:20): Variance-weighted loss dual metrics — telemetry MUST include chi_squared_trace_sample/full/best AND masked_mse_trace_sample/full/best
- **PHYSICS-LOSS-002** (docs/findings.md:21): Sigma floor guard — telemetry MUST include variance_floor_value and variance_floor_clamp_fraction
- **PERF-WARM-006** (docs/findings.md:37): Stage C warm cache reuses Stage A detector configs — pass stage_a_ctx to _build_stage_c_params helper
- **POLICY-001** (docs/findings.md:66): Environment Freeze — do NOT modify dependencies, only create new wrapper file dbex/refinement/stage_c.py
- **RUNTIME-001** (docs/findings.md:29): Disable torch.compile for smoke tests — set NANOBRAGG_DISABLE_COMPILE=1 in all pytest commands
- **CONFORMANCE-001** (docs/findings.md:28): Environment flags for canonical tests — use AUTHORITATIVE_CMDS_DOC, DBEX_SMOKE_DETECTOR_SIZE, DBEX_SMOKE_SIGMA_SOURCE=cli_override, KMP_DUPLICATE_LIB_OK

#### 7. Pitfalls Documented
1. **Circular Imports**: Use lazy imports (import inside run() method) for nanobrag_refinement, nanobrag_bridge, nanobrag_torch modules
2. **Dict Key Mismatches**: Verify helper calls use exact param names from helper signatures (same bugs as D1c wiring)
3. **Frozen Stage A Parameters**: Extract from telemetry param_deltas['<key>']['final'], rebuild as tensors on device
4. **baseline_detector Requirement**: Stage C REQUIRES baseline_detector (NOT optional), raise ValueError if missing
5. **Telemetry Schema Alignment**: Use asdict(RefinementTelemetry(...)) to ensure all fields present, add stage_type/mode AFTER asdict conversion
6. **Device/Dtype Consistency**: Rebuild all Stage A tensors with correct device/dtype from config
7. **Lazy Import Scoping**: DO NOT import helpers at module level, only inside run() method
8. **param_deltas_c Structure**: distance_offset_raw is DICT with panel IDs as keys (per-panel deltas)
9. **Regression Test Environment**: All environment flags MUST be set for canonical tests
10. **Engine Contract**: StageC MUST implement RefinementStage protocol (name property, configure method, run method returning dict)

### Decision Tree (4 Paths)

Ralph's Phase D2 execution will determine next loop direction:

- **Path A (All Tests PASS)**: StageC wrapper SUCCESSFUL, protocol compliance validated
  - Galph plans Phase D3-D5 next loop (DB-AT selectors, registry sync, findings update, mark Phase D COMPLETE)
  - Estimated timeline: 1-2 loops for comprehensive validation

- **Path B (Compilation FAIL)**: Circular import or helper signature mismatch
  - Ralph debugs import traceback, verifies lazy import placement, checks helper names
  - Do NOT proceed to D3-D5 until compilation clean

- **Path C (Regression FAIL)**: Helper calls mismatch inline wiring
  - Ralph compares StageC.run() vs dbex/nanobrag_refinement.py:3824-4328, fixes dict keys
  - Do NOT proceed to D3-D5 until both regression tests PASS

- **Path D (Engine Contract FAIL)**: RefinementStage protocol violation
  - Ralph verifies all 3 protocol methods implemented, checks return type is dict
  - Do NOT proceed to D3-D5 until contract test PASS

### Comparison: StageC vs StageB Wrapper Complexity

| Aspect | StageB (Phase C1b) | StageC (Phase D2) | Delta |
|--------|-------------------|------------------|-------|
| **Wrapper Lines** | 438 lines | ~400 lines (estimated) | -9% |
| **Optimized Parameters** | shell_modifier_raw (n_shells) | distance_offset_raw (n_panels) | Similar |
| **baseline_detector** | Optional | REQUIRED | Higher constraint |
| **param_deltas Structure** | Single dict (shell modifiers) | Dict of dicts (per-panel offsets) | More complex |
| **Telemetry Fields** | 30 fields (RefinementTelemetry) | 30 fields (RefinementTelemetry) | Same |
| **Lazy Imports** | 3 modules (nanobrag_refinement, nanobrag_bridge, nanobrag_torch) | 3 modules (same) | Same |
| **Helper Calls** | 3 helpers (params, closure, LBFGS) | 3 helpers (same pattern) | Same |
| **Regression Tests** | 2 tests (small + full detector) | 2 tests (small + full detector) | Same |
| **Engine Contract** | 1 test (test_engine_executes_mock_stage) | 1 test (same) | Same |
| **Risk** | MEDIUM (shell modifiers, HKL grid) | MEDIUM (detector offsets, per-panel deltas) | **Similar** |

### Findings Applied

- **REFINE-007** (docs/findings.md:58): Stage C gate = "stable detector offset" (≥80% offset reduction OR ≤±0.05mm final, ≤0.05% χ² regression) — wrapper preserves improvement gate logic + param_deltas_c telemetry
- **PHYSICS-LOSS-001/002** (docs/findings.md:20,21): Variance-weighted loss + sigma_floor — telemetry includes dual metrics + variance floor stats
- **PERF-WARM-006** (docs/findings.md:37): Stage C warm cache reuses Stage A detector configs — pass stage_a_ctx to helper
- **POLICY-001** (docs/findings.md:66): Environment Freeze — wrapper-only creation, no env changes
- **RUNTIME-001** (docs/findings.md:29): Disable torch.compile for smoke tests — NANOBRAGG_DISABLE_COMPILE=1 in all pytest commands
- **CONFORMANCE-001** (docs/findings.md:28): Environment flags for canonical tests — AUTHORITATIVE_CMDS_DOC + detector size + sigma override + KMP workaround

### Spec Alignment

- **docs/spec-db-workflow.md §7**: Refinement Protocol Architecture (RefinementStage protocol definition)
- **docs/spec-db-workflow.md §7.5**: Stage C detector offset refinement specification
- **docs/spec-db-runtime.md**: Device/dtype neutrality requirements
- **docs/architecture/pytorch_design.md**: RefinementEngine protocol architecture
- **docs/pytorch_runtime_checklist.md**: Telemetry schema + perf counters contract

### Next Loop Preview

**If Path A (All Tests PASS)**:
- **Loop i=231**: Galph plans Phase D3-D5 (validation + registry sync)
- **Strategy**: Run DB-AT selectors (DB-AT-021/DB-AT-024 as applicable for Stage C), update test registry (TESTING_GUIDE.md §2, TEST_SUITE_INDEX.md), verify collection logs, mark Phase D COMPLETE
- **Validation**: Ensure all Stage C smoke tests + DB-AT selectors PASS, no selector collects 0 tests
- **Expected Outcome**: Phase D COMPLETE → Phase E orchestration hooks next (stage registry/config knobs in RefinementEngine)

**If Path B/C/D (Compilation/Regression/Contract FAIL)**:
- Ralph debugs blocker
- Escalates to Galph with error signature + root cause hypothesis
- Do NOT proceed to D3-D5 until D2 clean

### Implementation Floor Compliance

✅ **FSM enforcement satisfied**:
- Last loop (i=229): ready_for_implementation (Phase D1c wiring)
- This loop (i=230): ready_for_implementation (Phase D2 wrapper implementation)
- Do Now includes: production code task (StageC class wrapper ~400 lines) + validation protocol (compilation + 3 tests) + decision synthesis (4-path template)
- Dwell remains 0 (continuing ready_for_implementation mode)

### Artifacts Structure

```
plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T141817Z/
├── phase_d1c/
│   ├── compilation_check.log
│   ├── pytest_stage_c_small.log
│   ├── pytest_stage_c_full.log
│   ├── decision.md (Path A: both tests PASS)
│   ├── metrics.json
│   └── summary.md
└── phase_d2/
    ├── compilation_check.log (expected from Ralph)
    ├── pytest_stage_c_small.log (expected from Ralph)
    ├── pytest_stage_c_full.log (expected from Ralph)
    ├── pytest_engine_contract.log (expected from Ralph)
    ├── decision.md (expected from Ralph, 4-path synthesis)
    ├── metrics.json (expected from Ralph, T0 probe)
    └── summary.md (this file — Galph's planning summary + expected Ralph Turn Summary)
```

### Confidence Assessment

- **Phase D2 protocol completeness**: VERY HIGH (99%)
- **StageC wrapper success**: HIGH (90% — proven StageB pattern, similar complexity)
- **Compilation + all tests PASS**: VERY HIGH (95% — wrapper not yet wired into inline path, no behavior change)
- **Overall Phase D completion**: MEDIUM-HIGH (75% — depends on D3-D5 validation passing)

### Timeline Estimate

- **Phase D2 (this loop)**: StageC wrapper implementation + validation (1 loop, ~2-3 hours wall time)
- **Phase D3-D5 (next loop, if Path A)**: DB-AT validation + registry sync (1-2 loops, ~3-6 hours wall time)
- **Total Phase D estimate**: 2-3 loops (~5-9 hours wall time) if wrapper implementation clean

### Roadmap Progress

**Tier 1 (Core Physics & Stability)**: ✅ COMPLETE
- ✅ TORCH-GEOMETRY-CONVERGENCE-001 (quaternion U-matrix convergence)
- ✅ TORCH-GEOMETRY-UB-REALIGN-001 (incremental UB parameterization)
- ✅ PHYSICS-LOSS-001 (variance-weighted loss)
- ✅ REFINE-SMOKE-CANONICAL (Stage B/C convergence)

**Tier 2 (Architectural Maturity)**: 🔄 IN PROGRESS (85% complete)
- ✅ ARCH-REFINE-FLOW-001 Phase A (Stage Interface & Engine Skeleton)
- ✅ ARCH-REFINE-FLOW-001 Phase B (Stage A Extraction)
- ✅ ARCH-REFINE-FLOW-001 Phase C (Stage B Extraction)
- ✅ ARCH-REFINE-FLOW-001 Phase D0-D1c (Stage C Extraction: Baseline + All Helpers)
- ⏳ **ARCH-REFINE-FLOW-001 Phase D2 (StageC Class Wrapper) — CURRENT FOCUS**
- ⬜ ARCH-REFINE-FLOW-001 Phase D3-D5 (Validation + Registry Sync)
- ⬜ ARCH-REFINE-FLOW-001 Phase E (Orchestration Hooks)

**Tier 3 (Feature Completeness)**: ⬜ PENDING
- ⬜ TORCH-REFINE-004 (Stage B Per-Reflection Mode) — blocked on Phase E
- ⬜ PERF-WARM-SIM-001 (Warm Simulator) — deferred until engine refactor complete

### Notes

- **No production code changes this loop** — planning only (Galph authored input.md)
- **Implementation floor satisfied** — Do Now contains production code task (StageC wrapper ~400 lines) + validation (3 tests)
- **FSM discipline maintained** — dwell=0, continuing ready_for_implementation mode
- **Pattern reuse** — Phase D2 mirrors Phase C1b proven wrapper methodology
- **Risk mitigation** — 4-path decision tree handles all wrapper outcome scenarios
- **Simplification** — Wrapper-only creation (no engine delegation yet, deferred to Phase E if needed)
