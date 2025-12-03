# Input for Ralph — Loop 2025-12-02T234500Z

## Summary
Housekeeping: Archive completed initiatives and compact fix_plan.md

## Mode
Docs

## InitiativeType
housekeeping (review_or_housekeeping)

## Focus
HOUSEKEEPING-001 — Fix Plan Archive & Compact

## Branch
integration

## Mapped tests
none — documentation-only

## Artifacts
plans/active/PORTFOLIO-STATUS/reports/2025-12-02T234500Z/

## Do Now

**Context:** Per <documentation_sweep/> step 6 and <end_of_loop_hygiene/>, fix_plan.md has grown to 160KB (>3× the 50KB threshold). Four initiatives are marked "done" and ready for archive. All Tier 0 initiatives are either complete or blocked by environment dependencies (DIAG/ARCH-SIM stuck).

**Primary Task:** Archive completed initiatives and compact fix_plan.md

### Steps

1. **Create archive file** at `docs/fix_plan_archive_2025-12-02.md`
   - Header: "# Fix Plan Archive — 2025-12-02"
   - Note: "This archive contains completed initiatives moved from docs/fix_plan.md on 2025-12-02 to reduce main ledger size."

2. **Move these initiatives** (with full Attempts History) to archive:
   - ARCH-BRIDGE-RESP-001 (Writer / bridge responsibility split) — done 2025-12-03T093500Z
   - ARCH-REFINE-001 (Refine Engine Modularization + Torch IO context) — done 2025-12-01T161600Z
   - ARCH-STAGE-CONTEXT-001 (Stage context + engine artifact boundary) — done 2025-12-02T160500Z
   - ARCH-ENGINE-ARTIFACTS-001 (Engine artifact channel & Bragg unification) — done 2025-12-02T185000Z

3. **Replace in fix_plan.md** with compact references:
   ```markdown
   - [ARCH-BRIDGE-RESP-001] — **archived** (2025-12-03, see docs/fix_plan_archive_2025-12-02.md)
   - [ARCH-REFINE-001] — **archived** (2025-12-01, see docs/fix_plan_archive_2025-12-02.md)
   - [ARCH-STAGE-CONTEXT-001] — **archived** (2025-12-02, see docs/fix_plan_archive_2025-12-02.md)
   - [ARCH-ENGINE-ARTIFACTS-001] — **archived** (2025-12-02, see docs/fix_plan_archive_2025-12-02.md)
   ```

4. **Update cross-references** in remaining initiatives that mention archived items

5. **Verify file size** reduction: `wc -c docs/fix_plan.md` should be <120KB

## How-To Map

```bash
# Create archive header
cat > docs/fix_plan_archive_2025-12-02.md <<'EOF'
# Fix Plan Archive — 2025-12-02

This archive contains completed initiatives moved from `docs/fix_plan.md` on 2025-12-02T234500Z to reduce main ledger size per <documentation_sweep/> step 6 (triggered at >50KB).

**Archival Policy:** Initiatives marked "done" with all exit criteria met and no active dependencies are moved here. Cross-references in active plans point to this archive.

---

EOF

# Extract and move initiatives (manual for accuracy)
# Use editor to:
# 1. Find each initiative section in docs/fix_plan.md
# 2. Cut full section (including Attempts History)
# 3. Paste into archive
# 4. Replace with compact reference in fix_plan.md

# Verify
wc -c docs/fix_plan.md
grep -c "archived.*2025-12-02" docs/fix_plan.md  # should be 4
```

## Pitfalls To Avoid

- **Do NOT** modify active/blocked initiatives (DIAG, ARCH-SIM, ARCH-REFACTOR-001)
- **Do NOT** lose cross-references (update pointers in active plans)
- **Do NOT** archive initiatives with active dependencies
- Preserve full Attempts History in archive (needed for retrospectives)
- Keep tier structure intact in fix_plan.md

## If Blocked

If any archived initiative has unexpected active references:
1. Document the blocker in artifacts/summary.md
2. Leave that initiative in fix_plan.md
3. Continue with other archives

## Findings Applied

- POLICY-001 (Environment Freeze): No code changes, docs only
- Housekeeping cadence per <documentation_sweep/> step 6

## Pointers

- Spec: docs/index.md (housekeeping not spec-governed)
- Template: plans/templates/fix_plan_ledger.md
- Archive precedent: None (first archive operation)

## Next Up

After housekeeping:
- Update galph_memory with portfolio status
- Consider alternative strategies for DIAG/ARCH-SIM environment blockers
