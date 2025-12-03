# Findings Table Structural Repair Checklist
**Initiative**: FINDINGS-LEDGER-002
**Date**: 2025-12-03T11:51:57Z
**Purpose**: Line-by-line instructions to repair `docs/findings.md` table structure

## Overview

This checklist addresses the 3 classes of structural issues identified in the audit:
1. Duplicate finding IDs (3 instances)
2. Malformed table rows with unescaped pipes (5 instances)
3. Parser robustness (recommendation only)

## Pre-Flight Checks

- [ ] Backup current `docs/findings.md`: `cp docs/findings.md docs/findings.md.backup.$(date +%Y%m%d)`
- [ ] Search `docs/fix_plan.md` for references to duplicate IDs: `grep -n "REFINE-005\|REFINE-008\|REFINE-009" docs/fix_plan.md`
- [ ] Search plan reports for references: `rg -l "REFINE-005|REFINE-008|REFINE-009" plans/active/`

## Task 1: Renumber Duplicate IDs

### REFINE-005 (duplicate at line 61)

**Current state**:
- Line 34: `REFINE-005` — HKL interpolation (canonical, has code citations)
- Line 61: `REFINE-005` — Haloed grid implementation (duplicate, plan-only citations)

**Action**:
1. Decide on new ID for line 61 entry (recommend `REFINE-017` as next available)
2. Update line 61: Replace `| REFINE-005 |` with `| REFINE-017 |`
3. Search and replace in all consuming documents:
   - `docs/fix_plan.md`: Replace references to line 61's content with new ID
   - Plan reports under `plans/active/TORCH-REFINE-002*/`: Update citations
4. Add code citations to line 61 entry: `dbex/nanobrag_bridge.py:559-692, dbex/nanobrag_refinement.py:147-154`
   (these are already documented in the Summary but should be in Source column)

### REFINE-008 (duplicate at line 90)

**Current state**:
- Line 66: `REFINE-008` — Stage B acceptance gates (canonical)
- Line 90: `REFINE-008` — Per-reflection Fhkl modifiers with ASU mapping

**Action**:
1. Decide on new ID for line 90 entry (recommend `REFINE-018`)
2. Update line 90: Replace `| REFINE-008 |` with `| REFINE-018 |`
3. Search and replace in consuming documents:
   - `docs/fix_plan.md`: Check references to per-reflection mode work
   - Plan reports under `plans/active/TORCH-REFINE-004/`: Update citations

### REFINE-009 (duplicate at line 73)

**Current state**:
- Line 67: `REFINE-009` — Detector distance offset seeding (canonical)
- Line 73: `REFINE-009` — Stage B baseline initialization scope bugfix (RESOLVED)

**Action**:
1. Decide on new ID for line 73 entry (recommend `REFINE-019`)
2. Update line 73: Replace `| REFINE-009 |` with `| REFINE-019 |`
3. Search and replace in consuming documents:
   - Check `plans/active/ARCH-REFINE-FLOW-001/`: Update baseline bugfix references

## Task 2: Repair Malformed Table Rows

### Line 8: GEOMETRY-004 (18 cells detected)

**Issue**: Summary column contains unescaped pipes or inline tables breaking row structure.

**Action**:
1. Open `docs/findings.md` and navigate to line 8
2. Inspect Summary column for pipe characters inside code snippets, inline tables, or formulas
3. Replace literal `|` with HTML entity `&#124;` in non-structural contexts
4. Alternatively: Rewrite complex inline content to avoid pipes (e.g., use → instead of |)
5. Verify repair: Count pipes in row — should be exactly 6 (one `|` before ID, 5 separating columns, one `|` after Status)

**Expected structure** after repair:
```markdown
| GEOMETRY-004 | 2025-11-23 | geometry, crystal, parameterization, ub-realign | [Summary with no unescaped pipes] | [Source with path:line] | Active |
```

### Line 34: REFINE-005 (8 cells detected)

**Issue**: Summary column contains unescaped pipes.

**Action**: Same as GEOMETRY-004 above. After repair, verify Source column contains code citations matching the Summary content.

### Line 39: SCALE-003 (8 cells detected)

**Issue**: Summary column contains unescaped pipes.

**Action**: Same as above. Verify Source column has `dbex/nanobrag_bridge.py:843-1106`.

### Line 44: SCALE-007 (8 cells detected)

**Issue**: Summary column contains unescaped pipes, likely from code snippet `simulate_forward_once`.

**Action**: Same as above. Check if inline code like `|F|` or function signatures break the row.

### Line 57: SCALE-004 (8 cells detected)

**Issue**: Summary column contains unescaped pipes.

**Action**: Same as above. Verify Source column includes code and plan references.

## Task 3: Update Inventory Parser (Optional Enhancement)

**File**: `input.md` script template (or standalone script if created)

**Enhancement**: Add logic to skip header separator rows:
```python
# After splitting cells:
if all(c.strip() in ('', '---', '-' * len(c.strip())) for c in cells):
    continue  # Skip separator row
```

This prevents the `| --- | --- | ... |` row from appearing in `findings_inventory.json` as a finding with ID `"---"`.

## Post-Repair Validation

After completing all repairs:

1. [ ] Run the inventory parser again:
   ```bash
   export REPORT_TS=$(date -u +%Y-%m-%dT%H%M%SZ)
   mkdir -p plans/active/FINDINGS-LEDGER-002/reports/${REPORT_TS}
   python [parser script from input.md]
   ```

2. [ ] Verify output:
   ```bash
   python - <<'PY'
   import json, pathlib
   data = json.loads(pathlib.Path('plans/active/FINDINGS-LEDGER-002/reports/[NEW_TS]/findings_inventory.json').read_text())
   total = len(data)
   with_path_line = sum(1 for r in data if r['has_path_line'])
   duplicates = {}
   for r in data:
       duplicates.setdefault(r['id'], []).append(r)
   print(f"Total: {total}")
   print(f"With path:line: {with_path_line} ({100*with_path_line/total:.1f}%)")
   print(f"Duplicate IDs: {[k for k,v in duplicates.items() if len(v)>1]}")
   print(f"Malformed (ID='---' or empty source): {sum(1 for r in data if r['id']=='---' or r['source']=='')}")
   PY
   ```

3. [ ] Expected results:
   - Total: ~90 (depends on final count after renumbering)
   - With path:line: 100%
   - Duplicate IDs: `[]` (empty list)
   - Malformed: 0

4. [ ] Update `docs/fix_plan.md` Attempts History for FINDINGS-LEDGER-002:
   - Mark Phase A.2 **complete** with 100% citation coverage
   - Reference this repair checklist and new inventory timestamp

5. [ ] Commit changes:
   ```bash
   git add docs/findings.md plans/active/FINDINGS-LEDGER-002/reports/[NEW_TS]/
   git commit -m "FINDINGS-LEDGER-002 Phase A.2: Repair table structure, renumber duplicates, 100% citation coverage (tests: none)"
   git push
   ```

## Notes

- **Do not delete duplicate entries** — they contain distinct information. Renumber instead.
- **Preserve all Source column content** — even if it's only plan references, keep it for traceability.
- **Test parser after each repair** to confirm row structure is correct.
- **Coordinate with fix-plan ledger** — any ID changes must be reflected in `docs/fix_plan.md` and plan reports.

## Estimated Effort

- Duplicate ID renumbering + cross-reference updates: **30 minutes**
- Malformed row repairs (5 entries): **20 minutes**
- Validation + commit: **10 minutes**
- **Total: ~1 hour** (single focused session)

## Success Criteria

✅ Zero duplicate IDs in `docs/findings.md`
✅ All table rows have exactly 6 cells (ID | Date | Tags | Summary | Source | Status)
✅ `findings_inventory.json` shows 100% `has_path_line` coverage for all canonical entries
✅ Parser no longer picks up header separator as a finding
✅ `docs/fix_plan.md` references updated to match renumbered IDs
