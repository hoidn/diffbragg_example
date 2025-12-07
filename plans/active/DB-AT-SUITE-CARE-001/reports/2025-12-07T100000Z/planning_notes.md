# DB-AT-SUITE-CARE-001 Phase B.3 Planning Notes

**Loop**: i=134 (Galph)
**Date**: 2025-12-07T100000Z
**Initiative**: DB-AT-SUITE-CARE-001 — Acceptance Suite Upkeep
**Phase**: B.3 (Test Harness Import Fixes)

---

## Context

Loop i=133 (Ralph) executed Phase B.1+B.2:
- **Phase B.1**: BLOCKED by 2 collection errors when running DB-AT-010 verification
- **Phase B.2**: COMPLETE — validated 4/4 canonical refGeom assets with checksums

Collection errors prevent test execution, blocking DB-AT-010 status verification and downstream member plan work.

---

## Root Cause Analysis

**Error 1**: `tests/dbex/test_nanobrag_smoke.py:30`
- **Symptom**: `ImportError: cannot import name 'prepare_refinement_inputs' from 'dbex.nanobrag_bridge'`
- **Root cause**: ARCH-BRIDGE-RESP-001 Phase C.6 (2025-12-03T140000Z) moved `prepare_refinement_inputs` from `dbex.nanobrag_bridge` to `dbex.refinement.inputs`
- **Impact**: Test collection fails, DB-AT-010 verification blocked

**Error 2**: `tests/dbex/test_vis_triptych_smoke.py:7`
- **Symptom**: `ImportError: cannot import name 'plot_z_scores' from 'dbex.vis'`
- **Root cause**: Function renamed to `compute_z_scores` in `dbex/vis/__init__.py`
- **Impact**: Test collection fails, DB-AT-010 verification blocked

---

## Classification

**Initiative Type**: harness (test infrastructure fix)

**Failure Type**: Implementation bug (test imports lag architectural refactoring)

**ARCH Contract Violation**: ARCH-CONTRACT-TESTING-001 (Test registry synchronization)
- **Owner**: `tests/` module imports must track canonical module structure
- **Normative requirement**: Test imports must reflect current production module layout per TESTING-003

---

## Fix Strategy

**Scope**: Minimal harness-only fixes to unblock DB-AT-010 verification

**Fix 1**: Update test_nanobrag_smoke.py imports
- Split import statement: `prepare_refinement_inputs` + `RefinementInputs` from `dbex.refinement.inputs`
- Retain bridge helpers (`create_detector_config`, `create_beam_config`, `create_crystal_config`) from `dbex.nanobrag_bridge`
- Lines affected: 28-36

**Fix 2**: Update test_vis_triptych_smoke.py
- Rename `plot_z_scores` → `compute_z_scores` in import statement (line 7)
- Update 2 function call sites (lines 38, 45)
- Total: 3 lines affected

---

## Validation Plan

**Pre-commit validation**:
1. `pytest --collect-only tests -k DB_AT_010 --smoke-detector-size=full`
   - Exit criteria: Exit code 0, "0 errors", ≥5 tests collected

**Regression validation**:
1. `pytest -v tests/dbex/test_nanobrag_smoke.py` (Fix 1 regression check)
2. `pytest -v tests/dbex/test_vis_triptych_smoke.py` (Fix 2 regression check)
   - Exit criteria: Both PASS

---

## Decision Status

**DecisionStatus**: patch_ready
- Exact fix locations known (2 files, 4 edit operations)
- Validation strategy defined (collection check + 2 regression checks)
- Confidence: 1.0 (import errors are deterministic, fixes are mechanical)

---

## Next Steps

**Immediate (Loop i=134, Ralph)**:
1. Apply Fix 1 (test_nanobrag_smoke.py)
2. Apply Fix 2 (test_vis_triptych_smoke.py)
3. Run collection check (pytest --collect-only)
4. Run regression checks (both test files)
5. Create summary.md documenting Phase B.3 completion

**After Phase B.3 (Loop i=135+, Galph)**:
- Phase B.4: Re-run DB-AT-010 full verification with canonical flags (now unblocked)
- Phase B.5+: Coordinate member plan Phase A/B execution per dependency chain

---

## Cross-References

**Findings**:
- **TESTING-003**: Test harness broken imports violate registry synchronization
- **ARCH-BRIDGE-RESP-001**: Context for `prepare_refinement_inputs` move (Phase C.6)
- **RUNTIME-001**: DB-AT-010 canonical flags reminder

**ARCH Contracts**:
- **ARCH-CONTRACT-TESTING-001**: Test registry synchronization owner/enforcement
- **ARCH-CONTRACT-BRIDGE-001**: Bridge responsibility boundary (canonical location enforcement)

**Implementation.md**:
- `plans/active/DB-AT-SUITE-CARE-001/implementation.md` (Phase B tasks list)
- Phase B.1: Tier-0 escalation (BLOCKED by collection errors → escalated to Phase B.3)
- Phase B.2: Asset validation (COMPLETE, 4/4 assets validated)

**Prior Loop Artifacts**:
- `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T084500Z/summary.md` (Phase B.1+B.2 results)
- `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T084500Z/db_at_010_status_verification.md` (collection error evidence)
- `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T084500Z/asset_validation.md` (4/4 assets confirmed)

---

**Planning complete**: 2025-12-07T100000Z (Loop i=134, Galph)
**Next loop**: Ralph implements Phase B.3 fixes + validation
