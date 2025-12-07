# DB-AT-SUITE-CARE-001 Phase B.1+B.2 Planning Notes

**Loop**: i=133 (Galph)
**Date**: 2025-12-07T084500Z
**Focus**: DB-AT-SUITE-CARE-001 Phase B (Portfolio Coordination & Asset Validation)
**Tasks This Loop**: B.1 (DB-AT-010 status verification) + B.2 (Centralized asset validation)

## Context

- **Tier 0 status**: All items done/archived/blocked
- **Tier 1 status**: MAP-SCALE-SYNC-001 closed (i=132); DB-AT-SUITE-CARE-001 Phase A complete (i=131); next natural step is Phase B
- **Phase A audit** (i=131): classified DB-AT-010 as "blocked" per 2025-11-04T232350Z regression report
- **BUT**: DB-AT-010 verification (2025-11-05T000200Z) shows all tests PASSING with correct flags
- **Issue**: Phase A audit based on stale data; member_plan_status_audit.md needs correction

## Focus Selection Rationale

**Why DB-AT-SUITE-CARE-001 Phase B over other Tier 1 items?**
1. Natural continuation after Phase A planning (i=131)
2. High-leverage coordination task (dereferences 5 downstream member plans)
3. Phase B.1 (DB-AT-010 verification) resolves audit stale data issue quickly
4. Phase B.2 (asset validation) is independent, non-blocking evidence gathering
5. Other Tier 1 items are pending (no in_progress items blocking portfolio)

**Why B.1+B.2 together in one loop?**
- Both are evidence-only verification tasks (no production changes)
- DB-AT-010 verification is ~10min pytest run + report authoring
- Asset validation is <5min file checks + checksum computation
- Combined effort ~20min implementation + 10min doc authoring
- Batching reduces loop overhead and accelerates portfolio velocity

## Task Scoping

### B.1 — DB-AT-010 Status Verification

**Objective**: Re-run DB-AT-010 with canonical flags to confirm current status (PASSING vs BLOCKED)

**Why this task?**
- dependency_chain.md identified DB-AT-010 Phase D as "Tier-0 blocker"
- BUT member_plan_status_audit.md used stale report (2025-11-04T232350Z regression hypothesis)
- Later verification (2025-11-05T000200Z) shows tests PASS
- Fresh verification with correct flags resolves ambiguity

**Canonical command** (from TESTING_GUIDE.md:235):
```
env KMP_DUPLICATE_LIB_OK=TRUE \
    DBAT010_ARTIFACT_DIR=plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T084500Z/db_at_010_verification \
    NANOBRAGG_DISABLE_COMPILE=1 \
    pytest -v tests -k DB_AT_010 --smoke-detector-size=full
```

**Critical flag**: `--smoke-detector-size=full` (without this, tests fail with UsageError per conftest.py:399 guard)

**Deliverable**: `db_at_010_status_verification.md` documenting:
- Test execution (exit code, collected/passed/failed counts)
- Current status (PASSING vs BLOCKED)
- Audit correction (update member_plan_status_audit.md classification if tests pass)

**Expected outcome**: Tests PASS (per 2025-11-05T000200Z precedent); "blocked" classification corrected to "done"

### B.2 — Centralized Asset Validation

**Objective**: Check workspace root for 4 canonical refGeom assets and emit shared validation artifact

**Why this task?**
- 5 member plans (DB-AT-020/021/022/023/024) all require same refGeom assets
- dependency_chain.md identified this as shared prerequisite for Phase A→B transitions
- Centralizing check avoids redundant file validation across 5 plans
- Shared artifact dereferrests downstream member plan Phase A1 tasks

**Assets to check**:
1. `refGeom.expt` — DIALS experiment model (detector, beam, crystal geometry)
2. `refGeom.refl` — DIALS reflection table (bbox, panel IDs, miller indices)
3. `scaled.mtz` — Structure factor amplitudes (H, K, L, F, SIGF)
4. `747_mask.pkl` — Trusted pixel mask (panel, slow, fast boolean array)

**Validation steps**:
- File existence check (`[ -f "$asset" ]`)
- File size (bytes)
- SHA256 checksum (portable: `sha256sum` Linux OR `shasum -a 256` macOS)

**Deliverable**: `asset_validation.md` documenting:
- X/4 assets found (with location, size, checksum)
- Y/4 assets missing (with mitigation options if any missing)

**Expected outcome**: Unknown (assets may or may not exist in workspace root); if missing, document gaps for provisioning coordination

## Compliance Checks

### Findings Applied
- **TESTING-003**: Asset validation produces structured artifact for member plans to reference
- **RUNTIME-001**: DB-AT-010 verification uses canonical flags per TESTING_GUIDE
- **DIAGNOSTICS-001**: Reports emit structured markdown (not just pytest logs)

### ARCH Contracts
- **ARCH-CONTRACT-TESTING-001**: Resolves stale status classification in member_plan_status_audit.md (TEST_SUITE_INDEX.md is canonical registry)

### Non-Negotiables Compliance
- **Evidence→Action contract**: Both B.1 and B.2 produce concrete next actions (DB-AT-010 status determines Phase D escalation; asset check determines Phase B.4 readiness)
- **No production edits by Galph**: This is pure verification/evidence gathering (harness initiative type)
- **Type discipline**: harness work (no spec changes, no architecture refactors sneaking in)

## Risk Assessment

**Low risk**:
- DB-AT-010 verification: Tests already pass per 2025-11-05T000200Z; just confirming with fresh run
- Asset validation: Read-only file checks; no environment changes

**Potential blockers**:
1. DB-AT-010 tests fail (escalate to Phase D per dependency_chain.md)
2. RefGeom assets missing (coordinate provisioning or create synthetic dataset)
3. Pytest hangs (timeout + investigate environment flags)

**Mitigation**:
- DB-AT-010 failure: Document signature, mark B.1 blocked, delegate to DB-AT-010 Phase D dedicated loop
- Assets missing: Document gaps, complete B.2 with mitigation options (provision / synthetic / alternative dataset)
- No mid-loop pivots: If blocked, finish B.2 and return control to Galph for replanning

## Next Loop Decision Tree

**If DB-AT-010 PASS + All 4 assets FOUND**:
→ Proceed to Phase B.4 (Member plan Phase A execution in parallel: DB-AT-002/020/021/022/023)

**If DB-AT-010 PASS + Assets MISSING**:
→ Coordinate asset provisioning, then proceed to Phase B.4

**If DB-AT-010 FAIL + Assets FOUND/MISSING**:
→ Escalate to DB-AT-010 Phase D dedicated loop (Tier-0 blocker per dependency_chain.md)

**If DB-AT-010 PASS + FORWARD-EQUIV-002 artifacts unchecked**:
→ Optional: Execute Phase B.3 (FORWARD-EQUIV-002 artifact check) before Phase B.4

## Artifacts This Loop

**Mandatory**:
- `db_at_010_status_verification.md` (B.1 deliverable)
- `asset_validation.md` (B.2 deliverable)
- `summary.md` (loop summary with next steps decision)
- `planning_notes.md` (this file)

**Optional**:
- `pytest_db_at_010_verification.log` (full pytest output, referenced by db_at_010_status_verification.md)
- `db_at_010_exit_code.txt` (exit code capture for programmatic checks)

---

**Planning completed by**: Galph (Loop i=133)
**Next actor**: Ralph (executes B.1+B.2 per input.md Do Now)
