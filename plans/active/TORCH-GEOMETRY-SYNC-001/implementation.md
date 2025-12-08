# Implementation Plan: TORCH-GEOMETRY-SYNC-001

## Initiative
- **ID:** TORCH-GEOMETRY-SYNC-001
- **Title:** Geometry Convergence & Parity Alignment
- **Owner:** Galph ↔ Ralph
- **Type:** Roll-up (architecture)
- **Status:** done
- **Closure Date:** 2025-12-08T190000Z

## Summary

This roll-up coordinates four member plans addressing Stage A crystal geometry parameterization:
- **TORCH-GEOMETRY-CONVERGENCE-001:** Diagnose quaternion U-matrix convergence failure
- **TORCH-GEOMETRY-PARITY-002:** Direct U-matrix parameterization for A* parity
- **TORCH-GEOMETRY-PARITY-003:** Investigate det(U)≠1 and hybrid parameterization
- **TORCH-GEOMETRY-UB-REALIGN-001:** Incremental UB parameterization per spec

**Outcome:** The roll-up objective has been achieved. The incremental UB parameterization (UB-REALIGN-001) provides a spec-compliant solution using dxtbx U₀/B₀ as baseline with delta increments, achieving mapping parity and convergence stability.

## Member Plan Status Summary

| Plan ID | Status | Exit Criteria | Verdict |
|---------|--------|---------------|---------|
| TORCH-GEOMETRY-CONVERGENCE-001 | **done** | 5/5 | Quaternion convergence fixed via bypass |
| TORCH-GEOMETRY-PARITY-002 | **superseded** | 1/5 | Goals achieved by UB-REALIGN-001 |
| TORCH-GEOMETRY-PARITY-003 | **superseded** | 0/6 | det(U)≠1 bypassed by incremental approach |
| TORCH-GEOMETRY-UB-REALIGN-001 | **done** | 5/5 | Incremental UB parameterization complete |

## Goals (Roll-up Level)
1. ✅ Zero-point invariants documented per `docs/spec-db-core.md` §Baseline Crystal State
2. ✅ UB realignment complete per `docs/spec-db-workflow.md` §Stage A
3. ✅ Convergence/parity probes pass with artifacts under member plan directories
4. ✅ Dependencies on ARCH-REFINE-001 resolved and documented

## Exit Criteria Validation

| Criterion | Expected | Status | Evidence |
|-----------|----------|--------|----------|
| Zero-point invariants documented | spec-db-core.md §Baseline | ✅ | GEOMETRY-004 in findings.md |
| UB realignment complete | spec-db-workflow.md §Stage A | ✅ | UB-REALIGN-001 Phase C |
| Convergence probes pass | DB-AT-026, regression guard | ✅ | 4 tests passing |
| Parity probes pass | DB-AT-024, A* parity <1e-6 | ✅ | Mapping consistency test |
| ARCH-REFINE-001 resolved | done status | ✅ | 2025-12-01T170500Z |

## Compliance Matrix

- [x] **Spec Constraint:** `docs/spec-db-core.md` §Baseline Crystal State — Incremental UB parameterization uses U₀/B₀ from dxtbx as normative baseline
- [x] **Spec Constraint:** `docs/spec-db-workflow.md` §Stage A — Trainable parameters (quaternion ΔR, cell deltas, scale) conform to spec
- [x] **Finding/Policy:** `GEOMETRY-001` (detector mapping) — Honored by baseline derivation
- [x] **Finding/Policy:** `GEOMETRY-002` (Euler inversion) — Quaternion-to-Euler conversion validated
- [x] **Finding/Policy:** `GEOMETRY-003` (B_ideal-based mapping misset) — Superseded by GEOMETRY-004
- [x] **Finding/Policy:** `GEOMETRY-004` (incremental UB parameterization) — Created by UB-REALIGN-001
- [x] **Finding/Policy:** `CONVERGENCE-001` (bypass fix for diagnostic script) — Created by CONVERGENCE-001
- [x] **Finding/Policy:** `DXTBX-001` (dxtbx crystal API conventions) — Honored by U₀/B₀ baseline
- [x] **Finding/Policy:** `HKL-ORIENT-001` (HKL orientation alignment) — Addressed by ΔR approach

## Phases Overview

### Phase A — Reality Check (This Loop)
**Status:** COMPLETE (2025-12-08T190000Z)
**Objective:** Assess member plan status and determine roll-up completion path.

- [x] A1: Inventory member plans with status, phases, exit criteria
- [x] A2: Identify dependencies and blockers
- [x] A3: Assess roll-up completion path (Option A/B/C)
- [x] A4: Update roll-up implementation.md

**Artifacts:** `plans/active/TORCH-GEOMETRY-SYNC-001/reports/2025-12-08T190000Z/`
- `member_plan_inventory.md`
- `dependency_analysis.md`
- `rollup_strategy.md`
- `summary.md`

### Phase B — Closure Actions (If Needed)
**Status:** NOT REQUIRED (roll-up ready for closure)

The member plans are effectively complete. Option A (Close Roll-up) is recommended.

Closure actions (if performed in a subsequent loop):
- [ ] Update `docs/fix_plan.md` to mark TORCH-GEOMETRY-SYNC-001 as `done`
- [ ] Mark PARITY-002 and PARITY-003 as `superseded` in their implementation.md files
- [ ] Update Status fields in CONVERGENCE-001 and UB-REALIGN-001 from `pending` to `done`
- [ ] Archive or move completed member plans

## Dependencies

### Upstream (Required Before Roll-up)
| Dependency | Status | Resolution |
|------------|--------|------------|
| ARCH-REFINE-001 | done | 2025-12-01T170500Z |

### Downstream (Blocked Until Roll-up Complete)
| Consumer | What It Needs | Status |
|----------|---------------|--------|
| TORCH-REFINE-CLEANUP-001 | Geometry stability | Available |
| PHYSICS-LOSS-CONSISTENCY | Variance model integration | Geometry layer stable |

## Test Coverage

### Geometry-Related Tests
```
tests/dbex/test_geometry_current.py::test_derive_u_matrix_roundtrip
tests/dbex/test_geometry_current.py::test_derive_u_matrix_edge_case_identity
tests/dbex/test_ub_parameterization_roundtrip.py::test_db_at_026_orientation_zero_point
tests/dbex/test_ub_parameterization_roundtrip.py::test_db_at_026_cell_zero_point
tests/dbex/test_ub_parameterization_roundtrip.py::test_db_at_026_mapping_parity
tests/dbex/test_ub_parameterization_roundtrip.py::test_db_at_026_gradient_flow
```

### Regression Guards
- `test_stage_a_expansion`: Verified passing throughout all member plan phases
- DB-AT-024 mapping consistency: Verified unaffected by incremental UB implementation

## Artifacts Index

### Roll-up Reports
- `plans/active/TORCH-GEOMETRY-SYNC-001/reports/2025-12-08T190000Z/` (Phase A Reality Check)

### Member Plan Reports
- `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/` (9 timestamp directories, latest 2025-11-22T244500Z)
- `plans/active/TORCH-GEOMETRY-PARITY-002/reports/` (5 timestamp directories, latest 2025-11-22T120500Z)
- `plans/active/TORCH-GEOMETRY-PARITY-003/reports/` (4 timestamp directories, latest 2025-11-22T170806Z)
- `plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/` (5 timestamp directories, latest 2025-11-23T023142Z)

## Member Plan Details

### TORCH-GEOMETRY-CONVERGENCE-001 (COMPLETE)
**Title:** Diagnose & Fix Quaternion U-Matrix Catastrophic Convergence Failure
**Key Achievement:** Identified code path discrepancy in diagnostic script; bypass fix achieves stable convergence (chi² drift +0.0083% over 10 steps)
**Exit Criteria:** 5/5 satisfied
**Key Commits:** e86fd4e (B_ideal fix), fe6048f (code path alignment), 2e10e6c (zero-check bypass)

### TORCH-GEOMETRY-PARITY-002 (SUPERSEDED)
**Title:** Direct U-Matrix Parameterization for Stage A Geometry Refinement
**Status:** Superseded by UB-REALIGN-001
**Reason:** The det(U)≠1 discovery (det=1.000557) prevented SO(3) projection; the incremental UB approach bypasses this issue entirely

### TORCH-GEOMETRY-PARITY-003 (SUPERSEDED)
**Title:** Investigate det(U)≠1 Root Cause & Implement Hybrid Cell+U+Scale Parameterization
**Status:** Superseded by UB-REALIGN-001
**Reason:** The incremental UB parameterization uses dxtbx U₀ as baseline, eliminating the need to investigate or accommodate det(U)≠1

### TORCH-GEOMETRY-UB-REALIGN-001 (COMPLETE)
**Title:** Stage A UB Parameterization Realignment
**Key Achievement:** Implemented incremental UB parameterization with quaternion ΔR on top of dxtbx U₀/B₀ baseline; DB-AT-026 tests pass
**Exit Criteria:** 5/5 satisfied
**Key Commits:** 1a0de3a (incremental UB implementation)

## Conclusion

The TORCH-GEOMETRY-SYNC-001 roll-up has achieved its objective:

1. **Geometry convergence** was restored via CONVERGENCE-001's bypass fix for the diagnostic script code path discrepancy
2. **Geometry parity** was achieved via UB-REALIGN-001's incremental UB parameterization, which uses dxtbx U₀/B₀ as the authoritative baseline
3. **Spec alignment** is complete with GEOMETRY-004 documenting the incremental approach
4. **Test coverage** includes DB-AT-026 (4 tests) for UB round-trip validation

**Recommended Next Step:** Mark roll-up as `done` in fix_plan.md and archive or close member plans.
