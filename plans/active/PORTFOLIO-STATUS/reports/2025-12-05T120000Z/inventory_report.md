# Plan Directory Inventory Report — 2025-12-05T120000Z

## Executive Summary

The automated plan inventory script (`plan_inventory.py`) has completed its initial audit of `plans/active/`, revealing significant drift between active plan directories and `docs/fix_plan.md` coverage.

## Key Findings

- **Total plan directories:** 55
- **Tracked in fix_plan.md:** 15 (27%)
- **Missing fix_plan coverage:** 40 (73%)
- **Lacking implementation.md:** 4 directories

## Breakdown by Category

### Tracked Initiatives (15)
These initiatives have entries in `docs/fix_plan.md`:
- ARCH-BRIDGE-RESP-001, ARCH-ENGINE-ARTIFACTS-001, ARCH-LAZY-IMPORTS-001
- ARCH-REFACTOR-001, ARCH-REFINE-001, ARCH-REFINE-FLOW-001
- ARCH-SIM-CONSTRUCTION-001, ARCH-STAGE-CONTEXT-001, ARCH-TELEMETRY-001
- DIAG-NANOBRAGG-OVERSAMPLE-001, DOC-RUNTIME-004, PERF-WARM-SIM-001
- PORTFOLIO-STATUS (this initiative), TORCH-API-ALIGN-001, TORCH-REFINE-004

### Untracked Initiatives (40)
See `inventory_missing.md` for the complete table. Notable patterns:

**Active with Recent Reports (candidate for fix_plan.md addition):**
- MAP-SCALE-001 through MAP-SCALE-005 (November 2025)
- TORCH-GEOMETRY-* series (November 2025)
- TOOLING-VIS-001, PHYSICS-LOSS-001, REPORT-NANOBRAG-STATUS-001

**Archive Candidates:**
- ARCH-REFRACTOR-001 (typo duplicate, explicitly marked archived in stub)
- HARDEN-SUBMODULE-ROBUSTNESS, ORCH-* series (no implementation.md)
- SUPERVISOR (meta-coordination, no implementation.md)
- Older DB-AT-* initiatives (early November, possibly superseded)

**In-Progress but Untracked:**
- TORCH-BRIDGE-001 (status: in_progress, last report Oct 2025)
- TORCH-CLI-003 (status: in_progress, last report Oct 2025)

## Comparison to Ad-Hoc Snapshot (2025-12-05T083500Z)

The earlier manual snapshot identified 38 missing initiatives. The automated script now reports 40, with the discrepancy explained by:
- More precise pattern matching for plan IDs in `docs/fix_plan.md`
- Inclusion of meta-directories (SUPERVISOR, ORCH-*)
- Detection of typo/duplicate entries (ARCH-REFRACTOR-001)

## Recommendations

1. **Immediate Actions (Phase B):**
   - Archive ARCH-REFRACTOR-001 (explicitly marked as superseded)
   - Remove or document the 4 directories lacking implementation.md
   - Classify MAP-SCALE-* and TORCH-GEOMETRY-* series for bulk fix_plan entry or archival

2. **Fix Plan Updates (Phase B3):**
   - Add entries for active initiatives with recent reports (November 2025 onwards)
   - Mark stale initiatives (early November or October with no recent activity) for archival review

3. **Automation (Phase C3):**
   - Wire this script into regular portfolio audits
   - Add to `plans/active/PORTFOLIO-STATUS/bin/README.md` with rerun instructions
   - Update `docs/fix_plan.md` Working Agreements to mandate reruns on plan additions

## Artifacts Reference

- **Raw outputs:** `inventory.json`, `inventory_missing.md` (this directory)
- **Script location:** `plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py`
- **Previous snapshot:** `plans/active/PORTFOLIO-STATUS/reports/2025-12-05T083500Z/` (ad-hoc manual listing)
