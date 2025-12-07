# MAP-SCALE-SYNC-001 Roll-up Scoping (Loop i=127 Galph Planning)

## Context

**Previous state** (from galph_memory.md loop i=126):
- PHYSICS-LOSS-001 closed with `done_with_environment_caveat`
- All Tier 0 items done/archived/blocked
- Next action: Tier 1 focus selection (candidates: MAP-SCALE-SYNC-001, DB-AT-SUITE-CARE-001)

**Focus selection rationale:**
MAP-SCALE-SYNC-001 chosen over DB-AT-SUITE-CARE-001 because:
1. **Higher impact**: Calibration correctness affects all downstream physics (PHYSICS-LOSS-CONSISTENCY depends on it)
2. **Dependency unlocking**: PHYSICS-LOSS-001 listed MAP-SCALE-SYNC-001 as dependency (fix_plan.md:379); now that PHYSICS-LOSS-001 is done, we must close the calibration loop
3. **Concrete scope**: 5 member plans with clear implementation.md files
4. **Recent activity**: MAP-SCALE-001/002/004 have November 2025 completion artifacts
5. **Portfolio momentum**: Tier 1 progress after PHYSICS-LOSS-001 closure

## Member Plan Status Survey

### MAP-SCALE-001 — Zero-iteration mapping scale alignment
- **Status**: ✅ **DONE** (all phases A/B/C/D complete)
- **Latest report**: 2025-11-04T233500Z
- **Key deliverables**:
  - Phase A/B: Diagnosed scale mismatch, validated √spot_scale post-sim scaling strategy
  - Phase C: Prepared implementation Do Now for DB-AT-024 acceptance
  - Phase D: Integrated DiffBragg calibration + sample clipping (N_cells), DB-AT-024 thresholds met (corr≥0.2, localization≥0.90)
- **Exit criteria**: All 3/3 met per implementation.md lines 12-15
- **Artifacts**: `plans/active/MAP-SCALE-001/reports/2025-11-04T220000Z/` (final DB-AT-024 validation)
- **Next action**: Archive or mark for closure verification

### MAP-SCALE-002 — Nanobrag CLI calibration parity
- **Status**: ✅ **DONE** (all phases A/B/C/D complete)
- **Latest report**: Not checked (no reports/ directory found)
- **Key deliverables**:
  - Phase A: Confirmed CLI backend calibration/sample clipping gaps (2025-11-04T233500Z analysis)
  - Phase B: Added `--torch-config`, `--refined-mtz` CLI args; propagated calibration to beam/crystal configs
  - Phase C: Added regression coverage (`test_nanobrag_backend_runs_simulator`)
  - Phase D: Documentation sync (TESTING_GUIDE, TEST_SUITE_INDEX)
- **Exit criteria**: All 3/3 met per implementation.md lines 21-22
- **Artifacts**: Likely under `plans/active/MAP-SCALE-002/reports/` (directory not found, may need creation or verification)
- **Next action**: Archive or verify artifacts exist

### MAP-SCALE-003 — CLI Refined Structure Factor Telemetry
- **Status**: ⏳ **PENDING** (all phases A/B/C unchecked)
- **Scope**: Expose structure-factor provenance (raw vs refined MTZ) through CLI telemetry
- **Exit criteria** (from implementation.md):
  1. `run_nanobrag_backend` + `_write_torch_outputs` surface hkl_source, reflection count, mean amplitude, MTZ path
  2. Regression coverage exercises `--refined-mtz` path, asserts `load_refined_mtz` feeds `build_structure_factor_grid`, telemetry marks refined provenance
  3. Documentation updates (TESTING_GUIDE, TEST_SUITE_INDEX) + artifacts captured
- **Dependencies**: MAP-SCALE-002 (CLI plumbing for `--refined-mtz`)
- **Blocking**: None (MAP-SCALE-002 is done)
- **Next action**: Start Phase A planning or implementation

### MAP-SCALE-004 — Zero-iteration telemetry parity
- **Status**: ✅ **DONE** (all phases A/B/C complete)
- **Latest report**: Not checked
- **Key deliverables**:
  - Phase A: Audited `simulate_forward_once` telemetry design (implementation.md lines 25-29)
  - Phase B: Updated bridge helpers to return telemetry, extended DB_AT_024 assertions
  - Phase C: Documentation sync (TESTING_GUIDE, findings.md)
- **Exit criteria**: All 3/3 met per implementation.md lines 17-22
- **Artifacts**: Likely under `plans/active/MAP-SCALE-004/reports/`
- **Next action**: Archive or verify artifacts

### MAP-SCALE-005 — CLI refined telemetry enforcement
- **Status**: ⏳ **PENDING** (all phases A/B/C unchecked)
- **Scope**: Harden CLI to fail fast when `--refined-mtz` requested but not consumed (SCALE-007 guardrail)
- **Exit criteria** (from implementation.md):
  1. `run_nanobrag_backend` raises clear error when refined MTZ ingestion fails or telemetry reports `raw` after refined request
  2. Regression coverage exercises both success path (refined) and failure path
  3. Documentation updates (TESTING_GUIDE, TEST_SUITE_INDEX, findings.md SCALE-007)
- **Dependencies**: MAP-SCALE-003 (telemetry contract must exist to enforce it)
- **Blocking**: MAP-SCALE-003 (cannot enforce telemetry until it's implemented)
- **Next action**: Blocked until MAP-SCALE-003 complete

## Roll-up Initiative Scope

**Goal**: Synchronize calibration ladder initiatives (MAP-SCALE-001—005) to ensure:
1. Calibration precedence documented per spec-db-workflow.md "Calibration & Unit Conventions"
2. Sigma provenance work tracked with artifact pointers (already satisfied by PHYSICS-LOSS-001 closure)
3. Spot-scale alignment complete per config_crosswalk.md (MAP-SCALE-001/002/004 satisfy this)

**Current state**:
- **Complete**: MAP-SCALE-001, MAP-SCALE-002, MAP-SCALE-004 (3/5 member plans)
- **Pending**: MAP-SCALE-003, MAP-SCALE-005 (2/5 member plans)
- **Dependency chain**: MAP-SCALE-003 (telemetry) → MAP-SCALE-005 (enforcement)

**Exit criteria analysis** (from fix_plan.md:367-376):
1. ✅ **Calibration precedence documented** — Satisfied by MAP-SCALE-001/002 (spec-db-workflow.md §4, config_crosswalk.md §2)
2. ✅ **Sigma provenance tracked** — Satisfied by PHYSICS-LOSS-001 closure (Phases E/F/G/H/I)
3. ⏳ **Spot-scale alignment complete** — Partially satisfied (MAP-SCALE-001/002/004 done, MAP-SCALE-003/005 remain)

## Decision: Focus on MAP-SCALE-003

**Rationale**:
1. **Unblocks MAP-SCALE-005**: Telemetry contract must exist before enforcement can be implemented
2. **Smallest scope**: 3 phases (A/B/C) vs roll-up consolidation overhead
3. **Clear deliverables**: CLI + zero-iteration telemetry for structure-factor provenance
4. **Concrete next action**: Phase A planning (telemetry design audit)

**Alternative considered**: Roll-up closure planning
- **Rejected because**: 2/5 member plans still pending; premature to close roll-up
- **Better approach**: Complete MAP-SCALE-003 → MAP-SCALE-005 → then close roll-up

## Next Loop Plan (i=128 Ralph)

**Focus**: MAP-SCALE-003 Phase A (Telemetry Design)

**Deliverables**:
1. Audit `_write_torch_outputs` current diagnostics schema
2. Trace refined MTZ loading path (`load_refined_mtz` → `build_structure_factor_grid`)
3. Define telemetry metadata schema (hkl_source, reflection count, mean amplitude, MTZ path)
4. Confirm downstream consumers (tests, DB_AT_024) can access telemetry without breaking artifacts
5. Document planning decisions in `plans/active/MAP-SCALE-003/reports/2025-12-07T150000Z/planning_notes.md`

**Mapped tests**: None (planning loop, no production changes)

**Artifacts path**: `plans/active/MAP-SCALE-003/reports/2025-12-07T150000Z/`

**Decision status**: exploring (telemetry design audit)

**Action type**: planning

**Initiative type**: spec_change (telemetry contract extension)

## References

- **Fix plan entry**: docs/fix_plan.md:360-376 (MAP-SCALE-SYNC-001 ledger)
- **Member plan implementations**:
  - plans/active/MAP-SCALE-001/implementation.md (done)
  - plans/active/MAP-SCALE-002/implementation.md (done)
  - plans/active/MAP-SCALE-003/implementation.md (pending Phase A)
  - plans/active/MAP-SCALE-004/implementation.md (done)
  - plans/active/MAP-SCALE-005/implementation.md (blocked pending MAP-SCALE-003)
- **Spec references**:
  - docs/spec-db-workflow.md §4 (Calibration & Unit Conventions)
  - docs/config_crosswalk.md §2 (Structure-factor parameter mapping)
  - docs/spec-db-tracing.md §2 (Torch diagnostics expectations)
- **Findings**: SCALE-001, SCALE-002, SCALE-003, SCALE-004, SCALE-005, SCALE-006, SCALE-007
- **Dependencies**: PHYSICS-LOSS-001 (done), MAP-SCALE-002 (done)
