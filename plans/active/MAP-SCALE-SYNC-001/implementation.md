# MAP-SCALE-SYNC-001 — Calibration Ladder Synchronization

## Initiative
- ID: MAP-SCALE-SYNC-001
- Title: Calibration Ladder Synchronization (MAP-SCALE-001—005)
- Status: in_progress (2025-12-07)
- Type: spec_change (calibration conventions)

## Goals
Synchronize calibration ladder initiatives (MAP-SCALE-001—005) to ensure:
1. Calibration precedence documented per spec-db-workflow.md "Calibration & Unit Conventions"
2. Sigma provenance work tracked with artifact pointers
3. Spot-scale alignment complete per config_crosswalk.md

## Non-Goals
- Implementing new calibration physics (member plans handle implementation)
- Changing acceptance thresholds (SPEC governs those)
- Environment modifications (Environment Freeze applies)

## Exit Criteria (from fix_plan.md:367-376)
1. ✅ Calibration precedence documented per docs/spec-db-workflow.md §4 (satisfied by MAP-SCALE-001/002)
2. ✅ Sigma provenance work tracked with artifact pointers (satisfied by PHYSICS-LOSS-001 closure)
3. ⏳ Spot-scale alignment complete per docs/config_crosswalk.md (MAP-SCALE-001/002/004 done, MAP-SCALE-003/005 remain)

## Member Plan Status

### Completed (3/5):
- **MAP-SCALE-001** — Zero-iteration mapping scale alignment ✅ DONE (Phases A/B/C/D complete, 2025-11-04)
- **MAP-SCALE-002** — Nanobrag CLI calibration parity ✅ DONE (Phases A/B/C/D complete)
- **MAP-SCALE-004** — Zero-iteration telemetry parity ✅ DONE (Phases A/B/C complete)

### Pending (2/5):
- **MAP-SCALE-003** — CLI Refined Structure Factor Telemetry ⏳ PENDING (all phases unchecked)
  - **Next action**: Phase A telemetry design audit
  - **Blocking**: None (MAP-SCALE-002 dependency satisfied)
- **MAP-SCALE-005** — CLI refined telemetry enforcement ⏳ PENDING (all phases unchecked)
  - **Next action**: Blocked until MAP-SCALE-003 complete
  - **Blocking**: MAP-SCALE-003 (telemetry contract must exist to enforce)

## Dependency Chain
```
MAP-SCALE-001 (done) ──┐
                       ├──> PHYSICS-LOSS-001 (done)
MAP-SCALE-002 (done) ──┘

MAP-SCALE-002 (done) ──> MAP-SCALE-003 (pending) ──> MAP-SCALE-005 (pending)
                              ↑
                              └── Current focus (Phase A planning)

MAP-SCALE-004 (done) ──> (independent, done)
```

## Current Phase: Scoping and MAP-SCALE-003 Planning

**Focus**: MAP-SCALE-003 Phase A (Telemetry Design)

**Deliverables for next loop (i=128 Ralph)**:
1. Audit `_write_torch_outputs` current diagnostics schema
2. Trace refined MTZ loading path (load_refined_mtz → build_structure_factor_grid)
3. Define telemetry metadata schema (hkl_source, reflection count, mean amplitude, MTZ path)
4. Confirm downstream consumers (tests, DB_AT_024) can access telemetry without breaking artifacts
5. Document planning decisions in `plans/active/MAP-SCALE-003/reports/2025-12-07T150000Z/`

## References
- **Fix plan entry**: docs/fix_plan.md:360-376
- **Member plans**: plans/active/MAP-SCALE-00{1,2,3,4,5}/implementation.md
- **Spec references**:
  - docs/spec-db-workflow.md §4 — Calibration & Unit Conventions
  - docs/config_crosswalk.md §2 — Structure-factor parameter mapping
  - docs/spec-db-tracing.md §2 — Torch diagnostics expectations
- **Findings**: SCALE-001, SCALE-002, SCALE-003, SCALE-004, SCALE-005, SCALE-006, SCALE-007
- **TESTING_GUIDE**: docs/TESTING_GUIDE.md §2 (selector registry)
- **Architecture**: docs/architecture/calibration_scaling.md

## Risks / Deferrals
- **Roll-up closure**: Deferred until MAP-SCALE-003/005 complete (2/5 member plans pending)
- **Artifact verification**: MAP-SCALE-002/004 completion artifacts not yet verified (reports/ directories may need audit)
- **Environment freeze**: All telemetry work must operate within existing runtime (no package upgrades)
