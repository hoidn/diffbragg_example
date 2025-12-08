# Input for Ralph — Loop i=187

## Summary
Execute TORCH-REFINE-CLEANUP-001 Phase B (Portfolio Decision & Archival) — archive TORCH-REFINE-004, update blocked/revive member plan statuses, and sync ledger.

## Focus
**TORCH-REFINE-CLEANUP-001** — Stage A/B/C Refinement Probes Consolidation Roll-up

## Branch
`integration`

## Mapped Tests
- Selector: `pytest --collect-only tests/dbex/test_torch_refine_smoke.py` (verify no regressions from archive)
- No test execution this loop — docs/ledger closure only

## Artifacts
`plans/active/TORCH-REFINE-CLEANUP-001/reports/2025-12-08T200000Z/`

---

## Do Now

**Focus Item:** TORCH-REFINE-CLEANUP-001 Phase B (Portfolio Decision & Archival)

### Implement: Phase B Tasks (Archive + Ledger Updates)

**B1: Archive TORCH-REFINE-004**
```bash
# Move TORCH-REFINE-004 to archive
mv plans/active/TORCH-REFINE-004 archive/plans/TORCH-REFINE-004
```

Author closure summary at `archive/plans/TORCH-REFINE-004/closure_summary.md`:
- Status: All phases complete (2025-11-24T140000Z)
- Exit criteria: 4/4 met (per-reflection mode operational, ASU mapping, shell mode fallback, telemetry complete)
- Reports: 16 summary.md files in reports directory
- Tests: `test_stage_b_shell_modifiers`, `test_stage_b_per_reflection_smoke` (both PASS)

**B2: Queue revive-classified phases**
Update `docs/fix_plan.md` TORCH-REFINE-CLEANUP-001 entry with revive priority queue:
- TORCH-REFINE-002D: Priority HIGH — Remove xfail, restore ≥0.2% Stage A gate (remaining: P2.1-P2.2, P3.1-P3.2)
- TORCH-REFINE-001: Priority MEDIUM — Phase B full-trace telemetry, Phase C CLI wiring (remaining: B1-B2, C1-C2)

**B3: Update blocked member plan implementation.md files**
Add deferral/blocked rationale to:

1. `plans/active/TORCH-REFINE-002E/implementation.md` — Add status note:
   ```
   ## Status Update (2025-12-08)
   **Blocked on:** ARCH-GRADIENT-FLOW-001 (blocked_pending_upstream)
   - Phase B/C gradient work requires resolution of Jacobian magnitude/sign discrepancy
   - Escalation: `inbox/to_nanobrag_gradient_magnitude_2025_12_07.md`
   - Phase A diagnostics complete — geometry encoding gap understood
   ```

2. `plans/active/TORCH-REFINE-003/implementation.md` — Add status note:
   ```
   ## Status Update (2025-12-08)
   **Blocked on:** Stage A gate restoration
   - Depends on TORCH-REFINE-002D (xfail removal) and TORCH-REFINE-002E (gradient flow)
   - Will unblock once 002D restores ≥0.2% improvement gate
   ```

3. `plans/active/TORCH-REFINE-002/implementation.md` — Add delegation note:
   ```
   ## Status Update (2025-12-08)
   **Status:** done (delegated to TORCH-REFINE-002D)
   - Phases 1-3 complete
   - Phase 4 (HKL perturbation) tracked in TORCH-REFINE-002D
   ```

**B4: Update fix_plan.md TORCH-REFINE-CLEANUP-001 entry**
Add Attempts History entry:
```
* 2025-12-08T200000Z (Loop i=187, Ralph) — **Phase B complete**: B1: Archived TORCH-REFINE-004 with closure summary. B2: Documented revive priority queue (002D HIGH, 001 MEDIUM). B3: Updated blocked member plan implementation.md files (002E, 003, 002) with status notes. B4: Updated fix_plan entry. Touched: Phase B (B1-B4). Tests: collect-only verification. Artifacts: `plans/active/TORCH-REFINE-CLEANUP-001/reports/2025-12-08T200000Z/`.
```

**B5: Update implementation.md Phase B checkboxes**
Mark B1-B4 as complete in `plans/active/TORCH-REFINE-CLEANUP-001/implementation.md`.

**B6: Author summary.md**
- File: `plans/active/TORCH-REFINE-CLEANUP-001/reports/2025-12-08T200000Z/summary.md`
- Include Phase B completion confirmation and next steps (Phase C smoke test validation)

### Validating Selector
```bash
# Verify TORCH-REFINE-004 archive moved correctly
ls -la archive/plans/TORCH-REFINE-004/

# Capture collect-only for refinement smoke tests (should still collect 6)
KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only tests/dbex/test_torch_refine_smoke.py > plans/active/TORCH-REFINE-CLEANUP-001/reports/2025-12-08T200000Z/collect_refine_smoke.log 2>&1
```

---

## How-To Map

```bash
# B1: Archive TORCH-REFINE-004
mv plans/active/TORCH-REFINE-004 archive/plans/TORCH-REFINE-004
# Author closure_summary.md

# B2-B4: Update docs/fix_plan.md, member plan implementation.md files

# B5: Update TORCH-REFINE-CLEANUP-001/implementation.md checkboxes

# B6: Author summary.md

# Validation
ls -la archive/plans/TORCH-REFINE-004/
KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only tests/dbex/test_torch_refine_smoke.py > plans/active/TORCH-REFINE-CLEANUP-001/reports/2025-12-08T200000Z/collect_refine_smoke.log 2>&1
```

---

## Pitfalls To Avoid

1. **DO NOT** delete any files — move to archive only
2. **DO NOT** modify production code — this is ledger/docs only
3. **DO NOT** change test files — preserve test selectors
4. **DO** use exact paths for archive (`archive/plans/TORCH-REFINE-004/`)
5. **DO** verify archive contents exist after move
6. **DO** preserve all reports directories in archive
7. **DO** update all 3 blocked member plan implementation.md files (002E, 003, 002)
8. **DO** add Attempts History entry with artifact path

---

## If Blocked

If archive move fails (permissions, path issues):
1. Document the error in summary.md
2. Keep TORCH-REFINE-004 in plans/active/
3. Mark B1 as blocked with error message
4. Continue with B2-B4 (can complete independently)

---

## Findings Applied (Mandatory)

| Finding ID | Adherence |
|------------|-----------|
| REFINE-001 | Stage A nucleus warm-start + clamp pattern (documented in 002D revive queue) |
| REFINE-002 | 0.1% nucleus baseline gate (002D priority: restore ≥0.2% gate) |
| GRADIENT-001 | Tensor overrides preserve autograd (002E blocked rationale) |
| TESTING-003 | collect-only evidence captured |
| PROBE-FREEZE-001 | No new scripts created (archive move only) |

---

## Pointers

| Document | Relevance |
|----------|-----------|
| `plans/active/TORCH-REFINE-CLEANUP-001/implementation.md:49-56` | Phase B checklist |
| `plans/active/TORCH-REFINE-CLEANUP-001/reports/2025-12-08T150000Z/member_plan_status_audit.md` | Classification matrix |
| `docs/fix_plan.md:55-57` | TORCH-REFINE-CLEANUP-001 ledger entry |
| `plans/active/TORCH-REFINE-004/implementation.md` | Archive candidate verification |

---

## Next Up (Optional)

If Phase B completes early:
1. Begin Phase C.1: Run Stage A/B smoke selectors to confirm no regressions
2. Verify collect-only still shows 6 tests after archive move
