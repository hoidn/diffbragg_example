# MAP-SCALE-SYNC-001 Roll-up Scoping — Loop i=127 Galph Summary

## Turn Summary

Selected MAP-SCALE-SYNC-001 (Calibration Ladder Synchronization) from Tier 1 after PHYSICS-LOSS-001 closure.
Scoped roll-up initiative: 3/5 member plans done (MAP-SCALE-001/002/004), 2/5 pending (MAP-SCALE-003/005).
Delegated MAP-SCALE-003 Phase A planning to Ralph: telemetry schema design audit (5 deliverables: schema audit, MTZ flow trace, telemetry schema, consumer compatibility, planning notes).
Next loop (i=128): Ralph implements Phase A, produces artifacts under `plans/active/MAP-SCALE-003/reports/2025-12-07T150000Z/`.

## Focus Selection Rationale

**Chosen**: MAP-SCALE-SYNC-001 (Tier 1, spec_change)
**Alternatives considered**: DB-AT-SUITE-CARE-001 (Tier 1, harness)

**Why MAP-SCALE-SYNC-001**:
1. **Higher impact**: Calibration correctness affects all downstream physics (PHYSICS-LOSS-CONSISTENCY depends on it)
2. **Dependency unlocking**: PHYSICS-LOSS-001 listed MAP-SCALE-SYNC-001 as dependency; now PHYSICS-LOSS-001 is closed
3. **Concrete scope**: 5 member plans with clear implementation.md files, 3 already done
4. **Recent activity**: MAP-SCALE-001/002/004 have November 2025 completion artifacts
5. **Portfolio momentum**: Continues Tier 1 progress after PHYSICS-LOSS-001 closure

## Roll-up Status Survey

### Completed (3/5)
- **MAP-SCALE-001**: ✅ All phases A/B/C/D complete (zero-iteration scale alignment, DB-AT-024 thresholds met)
- **MAP-SCALE-002**: ✅ All phases A/B/C/D complete (CLI calibration parity, --refined-mtz plumbing)
- **MAP-SCALE-004**: ✅ All phases A/B/C complete (zero-iteration telemetry parity)

### Pending (2/5)
- **MAP-SCALE-003**: ⏳ Phase A pending (CLI refined structure-factor telemetry design)
  - **Status**: Selected for next loop (i=128)
  - **Blocking**: None (MAP-SCALE-002 dependency satisfied)
- **MAP-SCALE-005**: ⏳ All phases pending (CLI refined telemetry enforcement)
  - **Blocking**: MAP-SCALE-003 (telemetry contract must exist to enforce)

### Dependency Chain
```
MAP-SCALE-002 (done) → MAP-SCALE-003 (Phase A next) → MAP-SCALE-005 (blocked)
```

## Exit Criteria Analysis (fix_plan.md:367-376)

1. ✅ **Calibration precedence documented** — Satisfied by MAP-SCALE-001/002 (spec-db-workflow.md §4)
2. ✅ **Sigma provenance tracked** — Satisfied by PHYSICS-LOSS-001 closure (Phases E/F/G/H/I)
3. ⏳ **Spot-scale alignment complete** — Partial (MAP-SCALE-001/002/004 done, MAP-SCALE-003/005 remain)

**Roll-up closure**: Deferred until MAP-SCALE-003/005 complete (2/5 member plans pending)

## Planning Artifacts Created

1. **Roll-up implementation.md**: `plans/active/MAP-SCALE-SYNC-001/implementation.md`
   - Member plan status (3 done, 2 pending)
   - Dependency chain diagram
   - Exit criteria tracking
   - Current phase: MAP-SCALE-003 Phase A scoping

2. **Planning notes**: `plans/active/MAP-SCALE-SYNC-001/reports/2025-12-07T140000Z/planning_notes.md`
   - Member plan survey with latest reports
   - Focus decision analysis (MAP-SCALE-003 chosen)
   - Next loop deliverables (5 Phase A artifacts)

3. **input.md**: Comprehensive Do Now for Ralph (i=128)
   - ActionType: planning
   - Mode: Docs
   - DecisionStatus: exploring
   - InitiativeType: spec_change
   - 5 Phase A deliverables (schema audit, MTZ trace, telemetry schema, consumer compatibility, planning notes)
   - 3 ARCH-CONTRACTs cited (CALIBRATION-001, WRITER-001, STRUCTURE-FACTORS-001)
   - 5 Findings applied (SCALE-003/004/006/007, TESTING-003)
   - 10 Pitfalls enumerated (type discipline, parity-first, no stacking, evidence→action, findings paydown, ARCH conformance, scriptization, environment freeze, loop discipline)

4. **galph_memory.md**: Updated with loop i=127 entry
   - Focus: MAP-SCALE-SYNC-001
   - State: planning
   - Dwell: 0 (new Tier 1 focus)
   - Next action: map_scale_003_phase_a_planning

## Compliance Checks

### Non-negotiables Applied
- ✅ No production edits by Galph (planning only)
- ✅ Parity-first: MAP-SCALE-003 telemetry must align with MAP-SCALE-004 precedent
- ✅ Evidence→Action: input.md specifies 5 concrete deliverables + Phase B next action requirement
- ✅ Findings paydown: SCALE-003/004/006/007 all cited with implementation guidance
- ✅ ARCH conformance: 3 relevant ARCH-CONTRACTs identified (CALIBRATION-001, WRITER-001, STRUCTURE-FACTORS-001)
- ✅ Type discipline: MAP-SCALE-SYNC-001 correctly typed as spec_change (telemetry contract extension)
- ✅ Loop discipline: First planning loop for this focus (dwell=0), next must implement OR switch

### Loop Discipline
- **Dwell**: 0 (new focus selected from Tier 1)
- **Planning loops**: 1/2 max consecutive (this is first planning loop for MAP-SCALE-SYNC-001)
- **Next loop requirements**: Ralph must complete Phase A planning OR mark blocked and escalate to Galph
- **Implementation floor**: Next loop after this can be planning again (2/2 max), then must delegate implementation OR switch focus

### FSM State
- **Current**: planning (MAP-SCALE-003 Phase A design audit)
- **DecisionStatus**: exploring (telemetry schema design)
- **Next state**: Either (a) ready_for_implementation (Phase B), or (b) planning (Phase A extension if blocked), or (c) focus switch

## Next Action (Loop i=128 Ralph)

**Focus**: MAP-SCALE-003 Phase A (CLI Refined Structure Factor Telemetry)

**Deliverables** (all under `plans/active/MAP-SCALE-003/reports/2025-12-07T150000Z/`):
1. `schema_audit.md` — Current `/torch_diagnostics` HDF5 schema + extension points
2. `mtz_flow_trace.md` — `load_refined_mtz` → `build_structure_factor_grid` call chain with file:line anchors
3. `telemetry_schema.md` — 4 required fields (hkl_source, hkl_n_reflections, hkl_mean_amplitude, hkl_path) + fallback rules
4. `consumer_compatibility.md` — Regression/acceptance test impact analysis
5. `planning_notes.md` — Synthesis + Phase B next action recommendation

**Validation**: None (planning loop, no pytest execution)

**Mode**: Docs (no production changes, code reading only)

**Block scenarios**:
- Schema extension conflicts (backward compatibility)
- MTZ flow trace incomplete (missing functions)
- Consumer incompatibility (breaking test changes required)

**Resolution**: Document block in planning_notes.md, escalate to Galph for spec_change/harness scoping

## References

- **Fix plan entry**: docs/fix_plan.md:360-376 (MAP-SCALE-SYNC-001 ledger)
- **Member implementations**:
  - plans/active/MAP-SCALE-001/implementation.md (done)
  - plans/active/MAP-SCALE-002/implementation.md (done)
  - plans/active/MAP-SCALE-003/implementation.md (Phase A next)
  - plans/active/MAP-SCALE-004/implementation.md (done)
  - plans/active/MAP-SCALE-005/implementation.md (blocked pending MAP-SCALE-003)
- **Spec references**:
  - docs/spec-db-workflow.md:125-158 (Calibration & Unit Conventions)
  - docs/spec-db-tracing.md:85-120 (Torch diagnostics expectations)
  - docs/config_crosswalk.md:75-95 (Structure-factor parameter mapping)
- **Architecture**:
  - docs/architecture/calibration_scaling.md:45-78 (Calibration threading)
  - docs/architecture/dbex/io/writer.idl.md:55-85 (Writer diagnostics contract)
- **Findings**: SCALE-001, SCALE-002, SCALE-003, SCALE-004, SCALE-005, SCALE-006, SCALE-007
- **Galph memory**: galph_memory.md:1-7 (loop i=127 entry)
