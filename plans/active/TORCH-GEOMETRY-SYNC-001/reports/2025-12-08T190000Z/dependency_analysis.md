# Dependency Analysis for TORCH-GEOMETRY-SYNC-001

**Date:** 2025-12-08T190000Z
**Author:** Ralph
**Loop:** i=167
**Mode:** Evidence Collection (Phase A Reality Check)

---

## Member Plan Dependency Graph

```
PARITY-002 ──escalated──► PARITY-003 ──superseded-by──► UB-REALIGN-001
     │                         │                              │
     │                         │                              │
     └──escalated──► CONVERGENCE-001 ◄───────────────────────┘
                          │
                          └── consumed findings ──► UB-REALIGN-001
```

---

## 1. Inter-Member Dependencies

### TORCH-GEOMETRY-CONVERGENCE-001
**Upstream Dependencies:** None (root investigation)
**Downstream Consumers:**
- UB-REALIGN-001: Consumed CONVERGENCE-001 verdict to inform parameterization design
- PARITY-003: Would have consumed root cause analysis (but PARITY-003 was superseded)

**Status:** COMPLETE — no outstanding dependency chains

### TORCH-GEOMETRY-PARITY-002
**Upstream Dependencies:** None (original investigation)
**Downstream Consumers:**
- PARITY-003: Escalated from PARITY-002's det(U)≠1 discovery
- CONVERGENCE-001: Escalated from PARITY-002's catastrophic convergence failure (CC→-0.045)

**Status:** SUPERSEDED — dependencies resolved by alternate paths

### TORCH-GEOMETRY-PARITY-003
**Upstream Dependencies:**
- PARITY-002 Phase C1: Received det(U)≠1 escalation
- CONVERGENCE-001: Was waiting for viability verdict

**Downstream Consumers:** None (superseded before producing outputs)

**Status:** SUPERSEDED — UB-REALIGN-001 bypass approach eliminated need

### TORCH-GEOMETRY-UB-REALIGN-001
**Upstream Dependencies:**
- CONVERGENCE-001: Consumed verdict that quaternion U-matrix is viable under bypass
- Implicit: Lessons from PARITY-002/003 investigations

**Downstream Consumers:** None (terminal plan in dependency chain)

**Status:** COMPLETE — all upstream dependencies satisfied

---

## 2. External Dependencies (Tier 0 Blockers)

### ARCH-REFACTOR-001 (Stage A/B/C context + observer pattern)
**Status:** `done` (2025-12-01T170500Z)
**Impact on TORCH-GEOMETRY-SYNC-001:** ✅ RESOLVED

- Per `docs/fix_plan.md` line 38: "Done (2025-12-01T161600Z: Phase A-E code landed)"
- The Stage A context modularization was a prerequisite for clean UB parameterization wiring
- UB-REALIGN-001 Phase B successfully wired into the refactored context

### ARCH-GRADIENT-FLOW-001
**Status:** Not found in fix_plan.md active entries
**Impact on TORCH-GEOMETRY-SYNC-001:** ✅ NOT A BLOCKER

- This dependency was hypothesized but never materialized
- Gradient flow for incremental UB parameters validated via DB-AT-026 Test 4

---

## 3. Upstream Plan Dependencies

### Dependencies FROM the Roll-up (TORCH-GEOMETRY-SYNC-001)
| Upstream Plan | Relationship | Status |
|---------------|--------------|--------|
| ARCH-REFINE-001 | Required Stage helpers | ✅ done |
| ARCH-REFACTOR-001 | Required Stage modularization | ✅ done (equivalent to ARCH-REFINE-001) |

### Dependencies ON the Roll-up (from other plans)
| Downstream Plan | What It Needs | Status |
|-----------------|---------------|--------|
| TORCH-REFINE-CLEANUP-001 | Geometry stability | ✅ Available (UB-REALIGN-001 complete) |
| PHYSICS-LOSS-CONSISTENCY | Variance model integration | ✅ Geometry layer stable |

---

## 4. Blocker Assessment

### Current Blockers: NONE

All member plans are either:
1. **Complete** (CONVERGENCE-001, UB-REALIGN-001) — no blockers
2. **Superseded** (PARITY-002, PARITY-003) — blockers no longer relevant

### Historical Blockers (Resolved)

| Blocker | Affected Plan | Resolution |
|---------|---------------|------------|
| det(U)≠1 preventing SO(3) projection | PARITY-002, PARITY-003 | UB-REALIGN-001 bypass (incremental ΔR from baseline) |
| Quaternion convergence failure | CONVERGENCE-001 | Phase C6 zero-check bypass fix |
| B_ideal computation mismatch | CONVERGENCE-001 | Phase A3/B5 code path alignment |
| ARCH-REFACTOR-001 context | UB-REALIGN-001 | Upstream plan completed |

---

## 5. Cross-Reference Dependencies

### Finding Dependencies
| Finding ID | Required By | Status |
|------------|-------------|--------|
| GEOMETRY-001 | All member plans | Active |
| GEOMETRY-002 | All member plans | Active |
| GEOMETRY-003 | PARITY-002, CONVERGENCE-001 | Active (superseded by GEOMETRY-004) |
| GEOMETRY-004 | UB-REALIGN-001 | Active (created) |
| CONVERGENCE-001 | CONVERGENCE-001 | Active (created) |
| DXTBX-001 | PARITY-003, UB-REALIGN-001 | Active |
| HKL-ORIENT-001 | UB-REALIGN-001 | Active |

### Test Dependencies
| Test ID | Plan | Status |
|---------|------|--------|
| DB-AT-024 | PARITY-002, UB-REALIGN-001 | PASSING |
| DB-AT-026 | UB-REALIGN-001 | PASSING (4 tests) |
| test_stage_a_expansion | All member plans | PASSING |

---

## 6. Summary: Dependency Graph Status

```
┌─────────────────────────────────────────────────────────────────┐
│                  TORCH-GEOMETRY-SYNC-001                         │
│                     (Roll-up Plan)                               │
├─────────────────────────────────────────────────────────────────┤
│  Member Plans:                                                   │
│  ┌──────────────────────┐  ┌──────────────────────┐             │
│  │ CONVERGENCE-001      │  │ UB-REALIGN-001       │             │
│  │ Status: COMPLETE ✓   │  │ Status: COMPLETE ✓   │             │
│  │ Exit Criteria: 5/5   │  │ Exit Criteria: 5/5   │             │
│  └──────────────────────┘  └──────────────────────┘             │
│                                                                  │
│  ┌──────────────────────┐  ┌──────────────────────┐             │
│  │ PARITY-002           │  │ PARITY-003           │             │
│  │ Status: SUPERSEDED   │  │ Status: SUPERSEDED   │             │
│  │ (by UB-REALIGN-001)  │  │ (by UB-REALIGN-001)  │             │
│  └──────────────────────┘  └──────────────────────┘             │
├─────────────────────────────────────────────────────────────────┤
│  External Dependencies:                                          │
│  • ARCH-REFINE-001: RESOLVED ✓                                   │
│  • ARCH-GRADIENT-FLOW-001: NOT A BLOCKER ✓                       │
│                                                                  │
│  Blockers: NONE                                                  │
│  Pending Work: NONE                                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Conclusion

**All dependencies are resolved.** The roll-up has no outstanding blockers:

1. **CONVERGENCE-001** and **UB-REALIGN-001** are complete with all exit criteria satisfied
2. **PARITY-002** and **PARITY-003** are superseded — their objectives were achieved via the incremental UB approach
3. **Upstream dependencies** (ARCH-REFINE-001) are complete
4. **No downstream blockers** are pending resolution

**Recommendation:** The roll-up can proceed to closure.
