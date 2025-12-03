# Phase B3 Roll-Up Sections — Notes and TODOs

## Completion Summary

- **Completed:** All 13 roll-up sections added to `docs/fix_plan.md` (lines 203-416)
- **Validation:** `rollup_report.md` shows "✓ Section exists" for all 13 roll-ups
- **Script Run:** `plan_inventory.py --rollup-config` executed successfully, generating inventory.json, inventory_missing.md, and rollup_report.md

## Roll-Ups Added

1. **DB-AT-SUITE-CARE-001** — 7 member plans (DB-AT-002/010/020/021/022/023/024)
2. **MAP-SCALE-SYNC-001** — 5 member plans (MAP-SCALE-001—005)
3. **PHYSICS-LOSS-001** — 1 member plan
4. **TORCH-GEOMETRY-SYNC-001** — 4 member plans (TORCH-GEOMETRY-CONVERGENCE-001, TORCH-GEOMETRY-PARITY-002/003, TORCH-GEOMETRY-UB-REALIGN-001)
5. **TORCH-REFINE-CLEANUP-001** — 5 member plans (TORCH-REFINE-001/002/002D/002E/003)
6. **TORCH-CLI-BRIDGE-ROLLUP-001** — 3 member plans (TORCH-BRIDGE-001, TORCH-CLI-003/004)
7. **FORWARD-EQUIV-COVERAGE-001** — 3 member plans (FORWARD-EQUIV-001/002, PARITY-HARNESS-002)
8. **TOOLING-VIS-001** — 1 member plan
9. **DOCS-ROADMAP-001** — 1 member plan
10. **RUNTIME-VEC-001** — 1 member plan
11. **REPORT-NANOBRAG-STATUS-001** — 1 member plan
12. **NANOBRAG-GOLDEN-001** — 1 member plan
13. **ARCH-SPLIT-001** — 1 member plan (review for archival)

## Spec Citations Included

Each roll-up section includes:
- Dependencies
- Initiative type
- Exit criteria tied to spec clauses from:
  - `docs/spec-db-conformance.md`
  - `docs/spec-db-workflow.md`
  - `docs/spec-db-core.md`
  - `docs/spec-db-interfaces.md`
  - `docs/spec-db-vis.md`
  - `docs/spec-db-runtime.md`
  - `docs/TESTING_GUIDE.md`
  - `docs/development/testing_strategy.md`
  - `docs/config_crosswalk.md`
  - `docs/forward_equivalence.md`
  - `docs/architecture.md`
- Member plan directory paths
- Attempts History linking to classification artifact (2025-12-05T150000Z/classification.md)

## Residual TODOs

None identified during this loop. The roll-up sections are now synchronized with the roll-up config and properly documented. Future work will involve:

1. Consolidating status from individual member plan reports into roll-up Attempts History
2. Updating member-plan-specific exit criteria as those plans progress
3. Maintaining alignment between `rollups.json` and fix_plan.md headings when roll-up IDs change

## Metrics

- Files touched: 2 (`docs/fix_plan.md`, `plans/active/PORTFOLIO-STATUS/implementation.md`)
- Lines added to fix_plan.md: ~214 lines (13 roll-up sections)
- Script outputs: 3 files (inventory.json, inventory_missing.md, rollup_report.md)
- Validation: 13/13 roll-ups show "✓ Section exists"
