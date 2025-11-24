# Focus Selection Decision (Loop i=251) — 2025-11-24T055458Z

## Context

- **Last loop (i=250):** Ralph detected stale input.md (TORCH-API-ALIGN-001 Phase A1 already complete)
- **Tier 1:** ✓ COMPLETE (all items done 2025-11-23)
- **Tier 2:** ✓ COMPLETE (ARCH-REFINE-FLOW-001, TORCH-API-ALIGN-001 done 2025-11-24T004500Z)
- **Tier 3:** Multiple initiatives PENDING, all UNBLOCKED

## Execution Roadmap Analysis

Per docs/fix_plan.md Execution Roadmap § Tier 3:
- **PERF-WARM-SIM-001:** Explicitly marked "highest priority Tier 3 item" after Tier 2 completion
- Status: Pending, UNBLOCKED 2025-11-24T004500Z
- Phase D: D1-D3 code COMPLETE (commit 1bdeca3), D4 validation BLOCKED

## PERF-WARM-SIM-001 Phase D Status Review

**D1-D3 Implementation (2025-11-23T180000Z):**
- ✓ D1: Extended StageAContext with roi_panel_map
- ✓ D2: Implemented _retarget_stage_a_detectors helper
- ✓ D3: Refactored Stage C warm branches
- Code compiles cleanly, implementation correct

**D4 Validation Blocker (2025-11-23T190000Z):**
- **ORIGINAL blocker (routing):** ✓ RESOLVED
  - Fixed telemetry key mapping (stage_a → "A")
  - Fixed engine_inputs structure
  - Fixed Stage C enrichment
  - Both test_stage_a_expansion and test_stage_c_detector_microslip now EXECUTE

- **NEW blocker (Stage C chi-squared):** ✗ ACTIVE
  - Stage C initial chi²: 2.918e+08
  - Stage A final chi²: 2.909e+08
  - Gap: 0.94e+06 (0.32%) exceeds ±2.9e+05 tolerance (0.1%)
  - **NOT a routing issue** — Stage C implementation defect

## Decision Analysis

### Option A: Continue PERF-WARM-SIM-001 (Debug Stage C chi-squared)
**Pros:**
- Highest priority focus per Execution Roadmap
- Incremental progress: D1-D3 code correct, routing unblocked
- Clear next step: investigate Stage C detector/HKL state preservation

**Cons:**
- May require 1-2 loops to debug
- Could be a deeper Stage C refactoring issue

**Estimated Effort:** 1-2 loops (evidence gathering + targeted fix)

### Option B: Mark Phase D Partial Complete + Switch Focus
**Pros:**
- Respects incremental progress principle (Stage A delegation works)
- Separates concerns (detector reuse logic vs Stage C initialization)

**Cons:**
- Leaves Phase D incomplete
- Defers validation of D1-D3 code

### Option C: Create New Initiative (STAGE-C-CHI2-001)
**Pros:**
- Clear separation of concerns per Layered-scope guard
- Allows parallel tracking

**Cons:**
- Adds complexity to fix_plan
- PERF-WARM-SIM-001 remains blocked

## VERDICT: **Option A — Continue PERF-WARM-SIM-001 Phase D (Debug Stage C chi-squared)**

### Rationale:
1. **Roadmap Priority:** PERF-WARM-SIM-001 is highest Tier 3 priority
2. **Incremental Progress:** D1-D3 code correct, routing unblocked → now validate
3. **Focus Continuity:** Last two supervisor loops (i=249, i=250) were on this focus
4. **Dwell Status:** dwell=0 for this focus (last loop i=250 was Ralph stale input verification, not Galph planning)
5. **Implementation Floor:** Next loop MUST be ready_for_implementation (evidence gathering + targeted fix)
6. **Root Cause Hypothesis:** Stage C context initialization bug (detector state preservation, HKL grid cloning, param_values mismatch) — likely fixable in 1 loop

### Next Action:
**Evidence Gathering Mode** — Galph gathers evidence on Stage C chi-squared mismatch:
1. Review Stage C initialization code (dbex/nanobrag_refinement.py Stage C warm branch + compute_loss_stage_c)
2. Compare Stage A final telemetry vs Stage C initial setup (params, detector configs, HKL grids)
3. Identify most likely cause (detector distance not preserved? HKL grid stale? param mismatch?)
4. Formulate hypothesis + 1-loop targeted fix OR escalate to separate initiative if multi-loop

### FSM State:
- **Current:** gathering_evidence
- **Dwell:** 0 (transitioning to this focus from Tier 2 completion)
- **Artifacts:** plans/active/PERF-WARM-SIM-001/reports/2025-11-24T055458Z/

## Findings Applied:
- POLICY-001 (Environment Freeze, code-only fixes)
- PERF-WARM-013 (Stage C instantiation overhead — D1-D3 addressed this)
- ARCH-ENGINE-002 (telemetry packaging pattern — routing fixed)

## References:
- docs/fix_plan.md:Execution Roadmap Tier 3
- galph_memory.md:2025-11-23T190000Z (blocker diagnosis + recommendations)
- plans/active/PERF-WARM-SIM-001/reports/2025-11-23T190000Z/summary.md
- plans/active/PERF-WARM-SIM-001/implementation.md:Phase D Status
