# Input for Ralph — Loop i=186

## Summary
Execute TORCH-REFINE-CLEANUP-001 Phase A (Member Plan Reality Check) to audit 6 TORCH-REFINE member plans and classify remaining work.

## Focus
**TORCH-REFINE-CLEANUP-001** — Stage A/B/C Refinement Probes Consolidation Roll-up

## Branch
`integration`

## Mapped Tests
- Selector: `pytest --collect-only tests/dbex/test_torch_refine_smoke.py` (inventory existing selectors)
- No test execution this loop — planning/audit only

## Artifacts
`plans/active/TORCH-REFINE-CLEANUP-001/reports/2025-12-08T150000Z/`

---

## Do Now

**Focus Item:** TORCH-REFINE-CLEANUP-001 Phase A (Member Plan Reality Check)

### Implement: Phase A Tasks (Audit & Classification)

**A1: Audit each member plan's implementation.md**
Read and verify completion status for:
- `plans/active/TORCH-REFINE-001/implementation.md` — Expected: Phase A complete, B/C pending
- `plans/active/TORCH-REFINE-002/implementation.md` — Expected: Phases 1-3 complete, Phase 4 delegated to 002D
- `plans/active/TORCH-REFINE-002D/implementation.md` — Expected: Phase 0-1 complete, Phase 2-3 pending
- `plans/active/TORCH-REFINE-002E/implementation.md` — Expected: Phase A largely complete, Phase B partial, Phase C pending
- `plans/active/TORCH-REFINE-003/implementation.md` — Expected: All phases pending
- `plans/active/TORCH-REFINE-004/implementation.md` — Expected: All phases complete

**A2: Identify blocking dependencies**
Cross-reference with `docs/fix_plan.md` Tier 0 status:
- ARCH-GRADIENT-FLOW-001: `blocked_pending_upstream` — affects 002E gradient work
- ARCH-SIM-CONSTRUCTION-001: `blocked_pending_environment` — affects DB-AT-028/029 acceptance criteria
Document which pending phases are gated on these blockers.

**A3: Classify remaining work**
For each pending phase, assign one of:
- **revive**: Can proceed now (no Tier 0 blockers, low complexity)
- **blocked**: Requires Tier 0 resolution first
- **deferred**: Low priority, can wait indefinitely

**A4: Author member_plan_status_audit.md**
- File: `plans/active/TORCH-REFINE-CLEANUP-001/reports/2025-12-08T150000Z/member_plan_status_audit.md`
- Include:
  - Status matrix (from implementation.md §Member Plans)
  - Dependency map (which plans block which)
  - Classification for each pending phase (revive/blocked/deferred)
  - Recommendation for Phase B decisions

**A5: Author summary.md**
- File: `plans/active/TORCH-REFINE-CLEANUP-001/reports/2025-12-08T150000Z/summary.md`
- Include:
  - Phase A completion confirmation
  - Key findings (e.g., TORCH-REFINE-004 ready for archive)
  - Next steps (Phase B portfolio decision)

### Validating Selector
```bash
# Capture collect-only for refinement smoke tests
pytest --collect-only tests/dbex/test_torch_refine_smoke.py > plans/active/TORCH-REFINE-CLEANUP-001/reports/2025-12-08T150000Z/collect_refine_smoke.log 2>&1
```

---

## How-To Map

```bash
# Artifacts directory (already created)
# plans/active/TORCH-REFINE-CLEANUP-001/reports/2025-12-08T150000Z/

# Read each member plan implementation.md (already done by Galph — verify checkboxes)

# Author member_plan_status_audit.md with classification matrix

# Author summary.md

# Capture collect-only
KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only tests/dbex/test_torch_refine_smoke.py > plans/active/TORCH-REFINE-CLEANUP-001/reports/2025-12-08T150000Z/collect_refine_smoke.log 2>&1
```

---

## Pitfalls To Avoid

1. **DO NOT** run full test suite — collect-only only for inventory
2. **DO NOT** modify production code — this is planning/audit only
3. **DO NOT** modify member plan implementation.md files this loop — audit only
4. **DO** verify completion status against actual checkboxes in implementation.md
5. **DO** cross-reference fix_plan.md for current Tier 0 blocker status
6. **DO** use exact timestamp for artifacts path (2025-12-08T150000Z)
7. **DO** document blocking dependency chain clearly

---

## If Blocked

If any member plan implementation.md is missing or corrupted:
1. Document the gap in summary.md
2. Note which plans could not be audited
3. Keep TORCH-REFINE-CLEANUP-001 status as `in_progress`

---

## Findings Applied (Mandatory)

| Finding ID | Adherence |
|------------|-----------|
| REFINE-001 | Stage A nucleus warm-start + clamp pattern |
| REFINE-002 | 0.1% nucleus baseline gate |
| GRADIENT-001 | Tensor overrides preserve autograd (crystal_overrides passthrough) |
| TESTING-003 | collect-only evidence captured |

---

## Pointers

| Document | Relevance |
|----------|-----------|
| `plans/active/TORCH-REFINE-CLEANUP-001/implementation.md` | Phase A checklist |
| `docs/fix_plan.md:55-57` | TORCH-REFINE-CLEANUP-001 ledger entry |
| `docs/fix_plan.md:22-33` | Tier 0 blockers status |
| `plans/active/TORCH-REFINE-00X/implementation.md` | Member plans to audit |
| `tests/dbex/test_torch_refine_smoke.py` | Refinement smoke selectors |

---

## Next Up (Optional)

If Phase A completes early:
1. Begin Phase B.1: Confirm TORCH-REFINE-004 ready for archive
2. Draft deferral notes for blocked phases
