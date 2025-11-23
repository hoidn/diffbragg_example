### Turn Summary
Planned Phase D (Stage C Extraction) kickoff by authoring Phase D0 baseline collection protocol following proven Phase B/C multi-loop pattern.
Ralph will run test_stage_c_detector_microslip on small and full detectors to capture baseline artifacts before helper extraction begins.
Phase C (Stage B Extraction) is complete with engine delegation validated; next milestone is Stage C detector offset logic extraction (~250 lines estimated).
Next: Ralph executes Phase D0 baseline (collection check + 2 smoke tests + telemetry capture + decision synthesis), then Galph plans Phase D1 helper extraction if baseline passes.
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T143000Z/ (input.md protocol, galph_memory.md state)

## Phase D Planning Summary

### Context
- **Initiative**: ARCH-REFINE-FLOW-001 — Protocol-based Refinement Engine
- **Phase**: D0 (Stage C Baseline Artifacts)
- **Loop**: i=225 (Galph planning)
- **Timestamp**: 2025-11-23T143000Z
- **FSM State**: ready_for_implementation (dwell=0, transitioned from planning dwell=2)

### What Was Done

#### 1. Reviewed Phase C Completion
- Phase C (Stage B Extraction): **COMPLETE** (2025-11-23T140500Z)
- Engine delegation validated for `stage_a_b_mode` (lines 3057-3180)
- Stage B smoke PASSED (small detector, 23.7% improvement)
- DB-AT-024 PASSED (no regression from CPU fallback deferral)
- Test registry synchronized with CPU limitation documented

#### 2. Analyzed Phase D Scope
- **Target**: Stage C (detector offset refinement) extraction
- **Estimated scope**: ~250 lines inline Stage C code (simpler than Stage B)
- **Location**: `dbex/nanobrag_refinement.py` lines ~3880-4130 (inline path)
- **Pattern**: Follow proven Phase B/C multi-loop extraction (baseline → helpers → wrapper → validation)

#### 3. Authored Phase D0 Protocol
Created comprehensive 8-step baseline collection protocol in `input.md`:
1. Review Phase C completion evidence
2. Collection check (verify 2 Stage C tests exist)
3. Run Stage C small detector baseline
4. Run Stage C full detector baseline
5. Decision synthesis (4-path template: A/B/C/D)
6. Update implementation.md Phase D section
7. Write summary.md with Turn Summary
8. Commit and push artifacts

#### 4. Updated State Tracking
- **galph_memory.md**: Added Phase D0 planning entry
- **FSM transition**: planning (dwell=2) → ready_for_implementation (dwell=0)
- **Artifacts path**: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T143000Z/baseline/

### Decision Tree (4 Paths)

Ralph's Phase D0 execution will determine next loop direction:

- **Path A (Both PASS)**: Stage C baseline captured → Galph plans Phase D1 (helper extraction, 2-3 loops estimated)
- **Path B (Small PASS, Full FAIL)**: Baseline partial → Galph reviews full detector failure, decides small-only extraction vs debug (mirrors Stage B CPU fallback pattern)
- **Path C (Both FAIL)**: Stage C blocked → Galph defers Phase D, proceeds to Phase E (orchestration hooks) without Stage C extraction
- **Path D (Collection FAIL)**: Test infrastructure issue → Galph escalates with collection log analysis

### Key Differences from Phase B/C

**Simpler Scope**:
- Stage C: Detector origin offsets only (3 DOFs: x, y, z per panel)
- Stage B: Shell modifiers (20-50 shells) + CPU fallback + HKL grid handling
- Stage C: No CPU fallback complexity (single device path)

**Gate Criteria**:
- Stage C: "Stable detector offset" (REFINE-007) — offsets should not diverge, chi² improvement optional
- Stage B: ≥3% chi² improvement (REFINE-008) — mandatory convergence gate
- Stage C acceptance is MORE LENIENT (stability vs improvement)

**Risk Assessment**:
- Stage C smoke failure: MEDIUM (~30% — detector offset refinement historically less stable)
- Baseline capture failure: LOW (~5% — infrastructure issues only)
- Helper extraction complexity: LOW (~20% — simpler scope than Stage B)

### Findings Applied

- **REFINE-007** (Stage C Gate): Stable detector offset (not chi² improvement)
- **PHYSICS-LOSS-001/002** (Variance-Weighted Loss): Stage C inherits from inline implementation
- **POLICY-001** (Environment Freeze): Baseline-only loop, no environment changes
- **TESTING-003** (Selector Transitions): Collection confirms tests exist before extraction
- **CONFORMANCE-001** (DB-AT Environment): Canonical flags for Stage C smoke

### Spec Alignment

- **docs/spec-db-workflow.md §7**: Stage C definition (detector offset refinement)
- **docs/spec-db-runtime.md**: Device/dtype neutrality preserved
- **docs/spec-db-core.md**: Variance-weighted loss contract maintained

### Next Loop Preview

**If Path A (both PASS)**:
- **Loop i=226**: Galph plans Phase D1 (Stage C helper extraction)
- **Strategy**: Multi-loop pattern (likely 2 loops: helper extraction + wrapper, simpler than Stage B's 3-loop pattern)
- **Estimated helpers**: 2-3 functions (~250 lines total)
  1. `_build_stage_c_params` (~80 lines: detector offset init + optimizer)
  2. `_build_stage_c_lbfgs_closure` (~120 lines: compute_loss + closure)
  3. `_run_stage_c_lbfgs` (~50 lines: optimizer.step + validation)
- **Validation**: Stage C smoke (small+full) + DB-AT selectors

**If Path B/C/D**:
- Galph reviews blocker evidence
- Decides: defer Phase D (proceed to Phase E) vs debug Stage C vs small-only extraction

### Implementation Floor Compliance

✅ **FSM enforcement satisfied**:
- Last loop (i=224): docs-only (planning, dwell=2)
- This loop (i=225): ready_for_implementation with production artifact tasks
- Do Now includes: test execution + telemetry capture + decision synthesis
- Dwell resets to 0 after this loop completes

### Artifacts Structure

```
plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T143000Z/
├── baseline/
│   ├── pytest_collect_stage_c.log (collection check)
│   ├── pytest_stage_c_small.log (small detector test)
│   ├── pytest_stage_c_full.log (full detector test)
│   ├── telemetry_stage_c_small.json (if captured)
│   ├── telemetry_stage_c_full.json (if captured)
│   ├── metrics_stage_c_small.json (extracted metrics)
│   ├── metrics_stage_c_full.json (extracted metrics)
│   ├── decision.md (4-path verdict)
│   └── summary.md (Ralph's Turn Summary + detailed summary)
└── summary.md (this file — Galph's planning summary)
```

### Confidence Assessment

- **Phase D0 protocol completeness**: VERY HIGH (98%)
- **Baseline capture success**: HIGH (70% — Stage C may fail but capture will succeed)
- **Phase D1 readiness (if Path A)**: HIGH (85% — proven extraction pattern)
- **Overall Phase D completion**: MEDIUM (60% — depends on Stage C stability)

### Timeline Estimate

- **Phase D0 (this loop)**: Baseline capture (1 loop, ~30min wall time)
- **Phase D1-D2 (if Path A)**: Helper extraction + wrapper (2-3 loops, ~6-9 hours)
- **Phase D3-D5**: Validation + DB-AT checks (1-2 loops, ~3-6 hours)
- **Total Phase D estimate**: 4-6 loops (~12-18 hours) if Stage C baseline passes

### Roadmap Progress

**Tier 1 (Core Physics & Stability)**: COMPLETE
- ✅ TORCH-GEOMETRY-CONVERGENCE-001 (quaternion U-matrix convergence)
- ✅ TORCH-GEOMETRY-UB-REALIGN-001 (incremental UB parameterization)
- ✅ PHYSICS-LOSS-001 (variance-weighted loss)
- ✅ REFINE-SMOKE-CANONICAL (Stage B/C convergence)

**Tier 2 (Architectural Maturity)**: IN PROGRESS
- ✅ ARCH-REFINE-FLOW-001 Phase A (Stage Interface & Engine Skeleton)
- ✅ ARCH-REFINE-FLOW-001 Phase B (Stage A Extraction)
- ✅ ARCH-REFINE-FLOW-001 Phase C (Stage B Extraction)
- ⏳ **ARCH-REFINE-FLOW-001 Phase D (Stage C Extraction) — CURRENT FOCUS**
- ⬜ ARCH-REFINE-FLOW-001 Phase E (Orchestration Hooks)

**Tier 3 (Feature Completeness)**: PENDING
- ⬜ TORCH-REFINE-004 (Stage B Per-Reflection Mode) — blocked on Phase E
- ⬜ PERF-WARM-SIM-001 (Warm Simulator) — deferred until engine refactor complete

### Notes

- **No production code changes this loop** — baseline capture only
- **Implementation floor satisfied** — production artifact task (telemetry) + test execution
- **FSM discipline maintained** — dwell reset after 2 consecutive planning loops
- **Pattern reuse** — Phase D0 mirrors Phase B0/C0 baseline protocols exactly
- **Risk mitigation** — 4-path decision tree handles all baseline outcome scenarios
