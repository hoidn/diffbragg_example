# SPEC-SQUARE-PARTIALITY-001 Phase A Summary

**Loop:** i=158 (Ralph)
**Date:** 2025-12-08T070000Z
**Mode:** Docs
**Focus:** SPEC-SQUARE-PARTIALITY-001 Phase A — Clarify SQUARE Lattice Physics

## Phase A Completion Status

All Phase A tasks complete:

| Task | Status | Notes |
|------|--------|-------|
| A0 | DONE | Created `physics_summary.md` documenting peak vs integrated scaling |
| A1 | DONE | Updated `docs/findings.md::SIM-CONSTR-PARTIALITY-001` with Resolution section |
| A2 | DONE | No spec update needed (spec-db-core.md contains no conflicting text) |
| A3 | DONE | This summary.md |

## Key Documentation Updates

### physics_summary.md (A0)
Created `plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T070000Z/physics_summary.md` documenting:
- Peak intensity at exact Bragg: proportional to `(Na * Nb * Nc)^2`
- Integrated/summed intensity: proportional to `Na * Nb * Nc` (linear)
- Mathematical basis from sincg function properties
- Reference to maintainer response

### SIM-CONSTR-PARTIALITY-001 Finding (A1)
Updated `docs/findings.md` line 168:
- Added "**Resolution (2025-12-08)**" section with clear physics statement
- Demoted old `(Na*Nb*Nc)^2` integrated expectation to "**Historical context (demoted)**"
- Promoted linear `Na*Nb*Nc` as the "**Enforceable requirement**"
- Changed status from "Active" to "Resolved (physics clarified 2025-12-08; test updates in Phase B)"
- Added `inbox/nanobrag_torch_response_2025_12_08.md` to references
- Added `SPEC-SQUARE-PARTIALITY-001` to Consumers

### spec-db-core.md (A2)
No update required. Searched spec for SQUARE/sincg/Na/Nb/Nc patterns; found no text implying `(Na*Nb*Nc)^2` for integrated intensity. The spec mentions only "single lattice envelope" (scope) and "Ncells_def is out of scope" (non-goal).

## Artifacts

- `plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T070000Z/physics_summary.md` — Physics clarification
- `plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T070000Z/summary.md` — This file
- `docs/findings.md` line 168 — Updated SIM-CONSTR-PARTIALITY-001 finding
- `plans/active/SPEC-SQUARE-PARTIALITY-001/implementation.md` — Phase A checklist marked complete

## Next Steps (Phase B)

Phase B will update tests and probes:
1. B1: Update `tests/architecture/test_nanobrag_partiality.py` to expect linear scaling
2. B2: Update probe script comments to reflect new contract
3. B3: Run partiality tests and capture logs
4. B4: Verify no other tests enforce incorrect scaling

## Findings Applied

- **SIM-CONSTR-PARTIALITY-001**: Updated to demote historical context, promote linear scaling
- **PROBE-FREEZE-001**: Complied — no new plan-local probes created

### Turn Summary
Phase A docs-only loop completed: created physics_summary.md documenting SQUARE lattice peak vs integrated scaling, updated SIM-CONSTR-PARTIALITY-001 finding with Resolution section demoting historical `(Na*Nb*Nc)^2` integrated expectation to context and promoting linear `Na*Nb*Nc` as enforceable requirement, verified spec-db-core.md needs no changes. Phase B (test updates) is next loop.

Artifacts: `plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T070000Z/` — physics_summary.md, summary.md
