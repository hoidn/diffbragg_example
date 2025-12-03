# Findings Ledger Audit Report — Phase A Verification
**Date**: 2025-12-03T11:51:57Z
**Initiative**: FINDINGS-LEDGER-002
**Phase**: A.2 (Verification & Issue Identification)
**Auditor**: Ralph

## Executive Summary

This audit verifies the citation coverage of `docs/findings.md` following the prior Phase A.2 completion (2025-12-03T113129Z). The ledger contains **106 logical finding entries** across 91 valid table rows (excluding header/separator). While the prior audit reported 100% citation compliance for accessible entries, this verification pass identified **critical structural issues** that must be addressed before the ledger can support automation or serve as a reliable knowledge base.

### Critical Issues Found
1. **Duplicate Finding IDs**: 3 ID collisions (REFINE-005, REFINE-008, REFINE-009)
2. **Malformed Table Rows**: 5 entries have unescaped pipe characters in Summary column, breaking parsers
3. **Parser Artifacts**: Header separator row (`---`) is being picked up as a finding entry

### Citation Coverage (Valid Entries Only)
- **Total parseable findings**: 81 (excludes 7 malformed + 3 duplicates mapped to earlier entries)
- **With `path:line` citations**: 80 (98.8%)
- **Missing citations**: 1 (1.2% — REFINE-005 duplicate at line 61)

## Detailed Findings

### Issue 1: Duplicate Finding IDs

Three finding IDs appear multiple times in the ledger, violating the unique-ID requirement:

| ID | Line Numbers | Status |
| --- | --- | --- |
| REFINE-005 | 34 (code citations), 61 (plan-only) | Line 34 is canonical; line 61 needs renumbering |
| REFINE-008 | 66 (Stage B acceptance), 90 (per-reflection mode) | Line 66 is canonical; line 90 needs renumbering |
| REFINE-009 | 67 (detector telemetry), 73 (Stage B scope bugfix) | Line 67 is canonical; line 73 needs renumbering |

**Recommendation**: Renumber duplicate entries as REFINE-005a / REFINE-017, REFINE-008a / REFINE-018, REFINE-009a / REFINE-019 respectively, and update all referencing documents (`fix_plan.md`, plan reports) to use the new IDs.

### Issue 2: Malformed Table Rows (Unescaped Pipes)

Five entries contain unescaped pipe characters (`|`) in the Summary column, breaking the Markdown table structure and causing parsers to split them into 8–18 cells instead of 6:

| Line | ID | Issue | Cell Count |
| --- | --- | --- | --- |
| 8 | GEOMETRY-004 | Inline code or table syntax | 18 cells |
| 34 | REFINE-005 | Inline code or table syntax | 8 cells |
| 39 | SCALE-003 | Inline code or table syntax | 8 cells |
| 44 | SCALE-007 | Inline code or table syntax | 8 cells |
| 57 | SCALE-004 | Inline code or table syntax | 8 cells |

**Root Cause**: These entries likely contain inline tables, code snippets with `|` operators, or Markdown pipe syntax that wasn't escaped.

**Recommendation**: Manual inspection + repair required. Replace literal pipes in Summary text with HTML entity `&#124;` or rewrap code/table content to avoid breaking the row structure.

### Issue 3: Parser Artifact (Header Separator)

The table header separator row (`| --- | --- | ... |`) is being picked up as a finding entry by the simple split-based parser in `input.md`. This is a known limitation of the provided script template.

**Recommendation**: Update parser to skip rows where all cells match the pattern `^-+$`.

### Citation Coverage Analysis

After filtering out malformed rows and duplicates, **80 of 81 valid findings (98.8%)** have `path:line` citations. The single missing citation is:

- **REFINE-005** (duplicate entry at line 61): Source column contains only plan references (`plans/active/TORCH-REFINE-002/reports/2025-11-05T035905Z/blocked.md, plans/active/TORCH-REFINE-002D/reports/2025-11-05T083500Z/summary.md`), no code pointers.

However, **this is a duplicate ID**—the canonical REFINE-005 entry at line 34 has proper citations (`dbex/nanobrag_bridge.py:559-692, ...`). Once the duplicate is renumbered, citation coverage will be 100% for canonical entries.

## Findings Inventory

The machine-readable inventory has been generated at:
```
plans/active/FINDINGS-LEDGER-002/reports/2025-12-03T115157Z/findings_inventory.json
```

**Caveat**: This JSON reflects the parser's view of the table, which includes the structural issues noted above. It contains:
- 88 entries (including separator row and malformed entries)
- Parser artifacts where Source column is truncated (e.g., `"source": "F"` for REFINE-005)
- Duplicate IDs mapped to separate JSON objects

The inventory is **not suitable for automation** until the table structure is repaired.

## Blockers for Phase B (Cross-Linking)

The structural issues identified in this audit are **blocking** for Phase B work:

1. **Duplicate IDs prevent unambiguous cross-referencing**: Fix-plan entries referencing "REFINE-008" could mean either the Stage B acceptance finding or the per-reflection mode finding.
2. **Malformed rows break tooling**: Any automation (e.g., cross-link validators, coverage dashboards) will fail or produce garbage when parsing these entries.
3. **Parser fragility**: The simple split-based parser in `input.md` cannot handle inline tables/code, requiring either table repairs or a more robust parser.

**Recommendation**: Open a **housekeeping sub-initiative** to:
1. Renumber duplicate IDs and update all consumers
2. Manually repair the 5 malformed table rows
3. Update parser script to skip separator rows
4. Regenerate inventory and revalidate 100% citation coverage

Then proceed to Phase B (cross-linking).

## Artifacts

- **Inventory (raw)**: `plans/active/FINDINGS-LEDGER-002/reports/2025-12-03T115157Z/findings_inventory.json`
  ⚠️ Contains parser artifacts; use with caution until table structure is repaired
- **Audit Report**: This file

## Next Actions

1. **Immediate**: Document these findings in `docs/fix_plan.md` Attempts History for FINDINGS-LEDGER-002
2. **Short-term**: Create `plans/active/FINDINGS-LEDGER-002/reports/2025-12-03T115157Z/table_repair_checklist.md` with line-by-line repair instructions
3. **Before Phase B**: Execute table repairs, regenerate inventory, and revalidate citation coverage

## Compliance Status

🔴 **BLOCKED**: Phase A.2 cannot be marked complete due to:
- Duplicate IDs violating unique-ID requirement
- Malformed table rows preventing reliable parsing
- Parser artifact in inventory

Once table structure is repaired and inventory regenerated, Phase A.2 can be marked **COMPLETE** with 100% citation coverage for all canonical findings.
