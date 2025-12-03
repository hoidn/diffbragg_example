# Plan Directory Classification — 2025-12-05

Source inventory: `plans/active/PORTFOLIO-STATUS/reports/2025-12-05T120000Z/inventory.json`

## Buckets

| Bucket | Criteria | Count | Plan IDs (abridged) |
| --- | --- | --- | --- |
| Active initiatives missing fix_plan coverage | `has_implementation` ✓ and no ledger entry | 34 | `DB-AT-002`, `DB-AT-010`, `DB-AT-020–024`, `FORWARD-EQUIV-00{1,2}`, `MAP-SCALE-001–005`, `PHYSICS-LOSS-001`, `TOOLING-VIS-001`, `TORCH-BRIDGE-001`, `TORCH-CLI-003/004`, `TORCH-GEOMETRY-*`, `TORCH-REFINE-00*`, `DOCS-ROADMAP-001`, `RUNTIME-VEC-001`, `REPORT-NANOBRAG-STATUS-001`, `ARCH-SPLIT-001`, `NANOBRAG-GOLDEN-001`, `PARITY-HARNESS-002` |
| Archive-ready / superseded | Status hint mentions archive or directory is a typo copy | 1 | `ARCH-REFRACTOR-001` (duplicate of ARCH-REFACTOR-001) |
| Missing implementation plans | Directory exists but lacks `implementation.md`; needs stub or archival before re-entering ledger | 5 | `HARDEN-SUBMODULE-ROBUSTNESS`, `ORCH-CLAUDE-PATH-FIX-001`, `ORCH-CLI-FALLBACK-001`, `ORCH-ROBUST-001`, `SUPERVISOR` |

## Recommended Next Actions

1. **Author fix-plan entries for grouped initiatives**
   - Stage the `DB-AT` suite (002/010/020–024) under a single Tier 1 testing initiative that references their reports and initiative directories.
   - Create a `MAP-SCALE` roll-up entry referencing all five plan directories.
   - Mirror the same treatment for `TORCH-GEOMETRY-*`, `TORCH-REFINE-*`, and the CLI/bridge efforts so the ledger has explicit owners.
2. **Archive duplicates**
   - `ARCH-REFRACTOR-001` contains only an archived stub pointing to the correct plan. Move it under `archive/plans/` and replace it with a README stub referencing ARCH-REFACTOR-001.
3. **Decide fate of empty plans**
   - Draft lightweight implementation plans (or archive the directories) for the `ORCH-*`, `HARDEN-*`, and `SUPERVISOR` scaffolding so future ledger entries can reference real plan docs.
4. **Update docs/fix_plan.md**
   - Capture the bucket counts in the Plan Directory Inventory appendix and add explicit todo bullets for each bucket above.

## Detailed Tables

### Active Initiatives Missing Ledger Entries

| Plan ID | Last Report | Notes |
| --- | --- | --- |
| ARCH-SPLIT-001 | – | Split prototype never recorded in ledger; review before archive |
| DB-AT-002 | 2025-11-04T050000Z | Determinism profile acceptance tests |
| DB-AT-010 | 2025-11-05T000200Z | Gradcheck suite |
| DB-AT-020 | 2025-11-04T052000Z | Reflection ingestion |
| DB-AT-021 | 2025-11-04T060900Z | Mask polarity |
| DB-AT-022 | 2025-11-04T055500Z | Background semantics |
| DB-AT-023 | 2025-11-04T065500Z | Calibration policy |
| DB-AT-024 | 2025-11-04T070000Z | Mapping consistency |
| DOCS-ROADMAP-001 | 2025-11-24T150000Z | Roadmap docs refresh |
| FORWARD-EQUIV-001 | 2025-10-29T013411Z | DiffBragg vs torch parity harness |
| FORWARD-EQUIV-002 | 2025-11-04T043500Z | End-to-end forward smoke |
| MAP-SCALE-001 | 2025-11-04T233500Z | Calibration ladder, part 1 |
| MAP-SCALE-002 | 2025-11-05T030000Z | Calibration ladder, part 2 |
| MAP-SCALE-003 | 2025-11-05T150000Z | Calibration ladder, part 3 |
| MAP-SCALE-004 | 2025-11-06T010000Z | Calibration ladder, part 4 |
| MAP-SCALE-005 | 2025-11-06T050000Z | Calibration ladder, part 5 |
| NANOBRAG-GOLDEN-001 | 2025-11-04T030000Z | Golden dataset capture |
| PARITY-HARNESS-002 | 2025-10-29T022212Z | Harness framework for parity cases |
| PHYSICS-LOSS-001 | 2025-11-21T083500Z | Variance/telemetry corrections |
| REPORT-NANOBRAG-STATUS-001 | 2025-11-05T184233Z | Status report generator |
| RUNTIME-VEC-001 | 2025-11-04T080000Z | Vectorization runtime checks |
| TOOLING-VIS-001 | 2025-11-26T050500Z | Mapping-aligned visuals |
| TORCH-BRIDGE-001 | 2025-10-28T233500Z | Bridge refactor |
| TORCH-CLI-003 | 2025-10-29T003751Z | CLI backend flag |
| TORCH-CLI-004 | 2025-11-04T222435Z | CLI telemetry |
| TORCH-GEOMETRY-CONVERGENCE-001 | 2025-11-22T252000Z | Geometry convergence probes |
| TORCH-GEOMETRY-PARITY-002 | 2025-11-22T120500Z | Geometry parity follow-ups |
| TORCH-GEOMETRY-PARITY-003 | 2025-11-22T170806Z | Geometry parity diagnostics |
| TORCH-GEOMETRY-UB-REALIGN-001 | 2025-11-23T023142Z | UB realignment tooling |
| TORCH-REFINE-001 | 2025-11-05T024454Z | Stage A nucleus |
| TORCH-REFINE-002 | 2025-11-05T044720Z | Stage A/B telemetry |
| TORCH-REFINE-002D | 2025-11-05T093000Z | Stage A instrumentation |
| TORCH-REFINE-002E | 2025-11-22T120000Z | Stage A mapping parity |
| TORCH-REFINE-003 | 2025-11-06T130000Z | Stage C scaffolding |

### Archive Candidate

| Plan ID | Reason |
| --- | --- |
| ARCH-REFRACTOR-001 | Duplicated spelling of ARCH-REFACTOR-001; plan stub already says "All updates should be made in the main plan" |

### Missing Implementation Plan

| Plan ID | Next Step |
| --- | --- |
| HARDEN-SUBMODULE-ROBUSTNESS | Either author implementation.md or move under `archive/plans/` |
| ORCH-CLAUDE-PATH-FIX-001 | Author actual plan or delete placeholder |
| ORCH-CLI-FALLBACK-001 | Same as above |
| ORCH-ROBUST-001 | Same as above |
| SUPERVISOR | Convert to living plan (meta-initiative) or archive |
