# MAP-SCALE-SYNC-001 Closure Summary

## Initiative
- **ID**: MAP-SCALE-SYNC-001
- **Title**: Calibration Ladder Synchronization (MAP-SCALE-001—005)
- **Type**: spec_change (calibration conventions roll-up)
- **Status**: ✅ **DONE** (2025-12-07T024500Z)

## Exit Criteria Assessment

### 1. Calibration precedence documented
**Status**: ✅ **SATISFIED**

**Evidence**:
- `docs/spec-db-workflow.md` §4 "Calibration & Unit Conventions" normative section established
- `docs/architecture/calibration_scaling.md` precedence rules documented (torch_config > CLI)
- Delivered by: MAP-SCALE-001 (Phase D, 2025-11-04) + MAP-SCALE-002 (Phase D)

### 2. Sigma provenance work tracked
**Status**: ✅ **SATISFIED**

**Evidence**:
- PHYSICS-LOSS-001 closed with `done_with_environment_caveat` status (i=126, 2025-12-07)
- All phases A-I complete (canonical variance-weighted loss, sigma-floor telemetry)
- Sigma-map provenance ingestion contract implemented
- Cross-referenced by MAP-SCALE-001/002 in fix_plan dependencies

### 3. Spot-scale alignment complete
**Status**: ✅ **SATISFIED**

**Evidence**:
- MAP-SCALE-001 (Zero-iteration mapping scale alignment): ✅ DONE (Phases A/B/C/D, 2025-11-04)
- MAP-SCALE-002 (Nanobrag CLI calibration parity): ✅ DONE (Phases A/B/C/D)
- MAP-SCALE-003 (CLI Refined Structure Factor Telemetry): ✅ DONE (Phase B, i=127, 2025-12-07)
- MAP-SCALE-004 (Zero-iteration telemetry parity): ✅ DONE (Phases A/B/C)
- MAP-SCALE-005 (CLI refined telemetry enforcement): ✅ DONE (Phase B, i=130, 2025-12-07)

All member plans complete per `docs/config_crosswalk.md` §2 alignment requirements.

## Member Plan Status Summary

| Plan ID | Title | Status | Completion Date | Artifacts |
|---------|-------|--------|-----------------|-----------|
| MAP-SCALE-001 | Zero-iteration mapping scale alignment | ✅ DONE | 2025-11-04 | plans/active/MAP-SCALE-001/reports/ |
| MAP-SCALE-002 | Nanobrag CLI calibration parity | ✅ DONE | (Nov 2025) | plans/active/MAP-SCALE-002/reports/ |
| MAP-SCALE-003 | CLI Refined Structure Factor Telemetry | ✅ DONE | 2025-12-07 (i=127) | plans/active/MAP-SCALE-003/reports/2025-12-07T180000Z/ |
| MAP-SCALE-004 | Zero-iteration telemetry parity | ✅ DONE | (Nov 2025) | plans/active/MAP-SCALE-004/reports/ |
| MAP-SCALE-005 | CLI refined telemetry enforcement | ✅ DONE | 2025-12-07 (i=130) | plans/active/MAP-SCALE-005/reports/2025-12-07T000000Z/ |

**Final Roll-up Status**: 5/5 member plans complete ✅

## Key Deliverables Across Member Plans

### Calibration Contracts (SCALE-001 through SCALE-007)
1. **SCALE-001**: Zero-iteration baseline alignment (mapping → Stage A)
2. **SCALE-002**: Simulator calibration threading contract
3. **SCALE-003**: Calibration metadata threading to RefinementConfig
4. **SCALE-004**: HKL telemetry provenance (hkl_source field)
5. **SCALE-005**: Spot-scale override parameter mapping
6. **SCALE-006**: Refined structure factor grid alignment
7. **SCALE-007**: CLI telemetry enforcement guardrail (ARCH-CONTRACT-CALIBRATION-001)

### Architectural Documentation
- **ARCH-CONTRACT-CALIBRATION-001**: CLI refined MTZ fail-fast contract
  - Owner: `dbex/refine_one.py::run_nanobrag_backend`
  - Regression coverage: test_refined_mtz_missing_file_fails_fast, test_refined_mtz_telemetry_provenance
  - Documented: `docs/architecture/calibration_scaling.md:26-38`

### Test Coverage
- CLI metadata telemetry: `tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata`
- CLI refined MTZ enforcement: `tests/dbex/test_refine_one_cli.py::test_refined_mtz_missing_file_fails_fast`
- CLI refined telemetry provenance: `tests/dbex/test_refine_one_cli.py::test_refined_mtz_telemetry_provenance`
- Mapping smoke acceptance: `tests/dbex/test_stage_a_smoke_parity.py::test_db_at_024_mapping_smoke`

## Dependencies Satisfied

**Upstream**:
- ARCH-REFACTOR-001 (Phases A-C complete, RefinementContext/Config types available)
- ARCH-STAGE-CONTEXT-001 (typed contexts delivered)

**Downstream unblocked**:
- PHYSICS-LOSS-CONSISTENCY (Tier 1, calibration ladder now stable)

## Governance References

**Governed by Findings**:
- SCALE-001 through SCALE-007 (all Active status in findings.md)

**Normative SPEC**:
- `docs/spec-db-workflow.md` §4 — Calibration & Unit Conventions
- `docs/spec-db-tracing.md` §2 — Torch diagnostics expectations
- `docs/config_crosswalk.md` §2 — Structure-factor parameter mapping

**ARCH Contracts**:
- ARCH-CONTRACT-CALIBRATION-001 (refined MTZ enforcement)

## Attempts History Summary

### Phase 1: Planning and Scoping (i=126-127)
- i=126: PHYSICS-LOSS-001 closure (sigma provenance complete)
- i=127: MAP-SCALE-003 Phase A planning + Phase B implementation
  - Galph selected MAP-SCALE-SYNC-001 from Tier 1 after PHYSICS-LOSS-001 closure
  - Scoped MAP-SCALE-003 Phase A (telemetry design audit)
  - Ralph delivered Phase B (CLI plumbing verification, test assertions validated)

### Phase 2: MAP-SCALE-005 Execution (i=129-130)
- i=129 (Galph): MAP-SCALE-005 Phase A planning
  - Shortlist narrowed to MAP-SCALE-005 (4/5 member plans done)
  - Reality check revealed enforcement already implemented
- i=129 (Ralph): MAP-SCALE-005 Phase A complete (CRITICAL DISCOVERY)
  - CLI guard exists at refine_one.py:382-389 (no silent fallback)
  - Revised Phase B scope: validation + documentation only
- i=130 (Galph): MAP-SCALE-005 Phase B transition
  - DecisionStatus: exploring → patch_ready
  - Scoped regression tests + ARCH-CONTRACT formalization
- i=130 (Ralph): MAP-SCALE-005 Phase B complete
  - 2 regression tests added (4 PASSED)
  - ARCH-CONTRACT-CALIBRATION-001 formalized
  - SCALE-007 findings updated with CLI enforcement note

### Phase 3: Roll-up Closure (i=131, this loop)
- All 5/5 member plans confirmed complete
- Exit criteria 3/3 satisfied
- Portfolio steering: select next Tier 1 focus (DB-AT-SUITE-CARE-001)

## Artifacts Index

### Member Plan Reports
- **MAP-SCALE-001**: `plans/active/MAP-SCALE-001/reports/` (Phases A-D)
- **MAP-SCALE-002**: `plans/active/MAP-SCALE-002/reports/` (Phases A-D)
- **MAP-SCALE-003**: `plans/active/MAP-SCALE-003/reports/2025-12-07T180000Z/` (Phase B)
- **MAP-SCALE-004**: `plans/active/MAP-SCALE-004/reports/` (Phases A-C)
- **MAP-SCALE-005**:
  - Phase A: `plans/active/MAP-SCALE-005/reports/2025-12-06T235959Z/`
  - Phase B: `plans/active/MAP-SCALE-005/reports/2025-12-07T000000Z/`

### Roll-up Reports
- **Closure**: `plans/active/MAP-SCALE-SYNC-001/reports/2025-12-07T024500Z/`

## Next Steps

1. ✅ Mark MAP-SCALE-SYNC-001 status: `pending` → `done` in docs/fix_plan.md
2. ✅ Update PHYSICS-LOSS-001 status: `pending` → `done` (already closed i=126)
3. ✅ Archive MAP-SCALE-SYNC-001 implementation.md with closure notes
4. ✅ Portfolio steering: Select DB-AT-SUITE-CARE-001 for Phase A planning (Tier 1 focus)

## Recommendations

### Archival Candidates
- ARCH-REFINE-001 (Tier 1, marked "Ready to archive once downstream initiatives pick up")
  - Downstream MAP-SCALE-SYNC-001 now complete
  - Consider archiving in next ledger hygiene pass

### Documentation Hygiene
- fix_plan.md size: 405KB (exceeds 50KB threshold)
  - Consider archiving fully-done Tier 1 sections (ARCH-REFINE-001, MAP-SCALE-SYNC-001) to `docs/fix_plan_archive.md`

---

**Closure Date**: 2025-12-07T024500Z
**Closed By**: Galph (supervisor, loop i=131)
**Final Status**: ✅ DONE — All 3/3 exit criteria satisfied, 5/5 member plans complete
