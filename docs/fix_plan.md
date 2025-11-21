# DBEX Fix Plan Ledger (Summary)

Per supervisor rules (`prompts/supervisor.md`) this file lists the **current** focus areas, their status, and the artifact pointer for the latest evidence. Full Attempts History, retired initiatives, and detailed notes remain in `docs/fix_plan_archive.md` so we still satisfy the “document every loop” requirement without duplicating hundreds of lines here.

## Working Agreements (condensed)
- Update this ledger every loop with status + artifact path; archive long-form notes under `plans/active/<initiative-id>/reports/<timestamp>/`.
- Status vocabulary: `pending`, `in_progress`, `blocked`, `done`, `archived`.
- If an “Active” selector collects 0 tests after changes, downgrade/fix before closing the initiative.
- When blockers arise, summarize them here and capture the full evidence bundle in the referenced reports directory.

## Active Initiatives
| ID | Scope | Status | Latest Evidence | Immediate Next Action |
| --- | --- | --- | --- | --- |
| PHYSICS-LOSS-001 | Variance-weighted loss + telemetry plumbing | **in_progress** (blocked on canonical smokes) | `plans/active/PHYSICS-LOSS-001/reports/2025-11-21T010127Z/` | Land shared chi-squared helper + sigma-floor telemetry, rerun Stage A/B/C smokes + DB-AT-010, then unblock dependents (ARCH-REFINE-FLOW-001, TOOLING-VIS-001). |
| PERF-SMOKE-DETSIZE | Small-detector smoke fixture & parity guard | **in_progress** | `plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T035150Z/` | Maintain small-detector path; keep canonical runs blocked until REFINE-SMOKE-CANONICAL repairs Stage B/C implementation. |
| REFINE-SMOKE-CANONICAL | Canonical Stage B/C repairs | **pending** | `plans/active/REFINE-SMOKE-CANONICAL/reports/2025-11-21T042222Z/` | Fix Stage B LBFGS `nonlocal` scope + Stage C detector-offset telemetry, rerun canonical smokes, feed results back to PERF-SMOKE-DETSIZE/PHYSICS-LOSS. |
| PERF-WARM-SIM-001 | Stage A warm cache + perf telemetry | **in_progress** | `plans/active/PERF-WARM-SIM-001/reports/2025-11-05T221200Z/` | Implement Stage A context cache, capture before/after timings per working plan, and update tests/docs. |
| ARCH-REFINE-FLOW-001 | Protocol-based refinement engine | **pending** (blocked by PHYSICS-LOSS-001) | `plans/active/ARCH-REFINE-FLOW-001/implementation.md` | Resume once variance-weighted loss + canonical smokes are green; then refactor `run_nanobrag_refinement` into stage protocol per plan. |
| TOOLING-VIS-001 | Standardized torch diagnostics visuals | **pending** (blocked by PHYSICS-LOSS-001) | `plans/active/TOOLING-VIS-001/implementation.md` | After PHYSICS-LOSS exits, implement shared visualization helpers and update CLI outputs. |
| DOCS-ROADMAP-001 | Thin `nanobrag_integration_plan.md` | **pending** | `plans/active/DOCS-ROADMAP-001/implementation.md` | Rewrite plan per spec references once upstream initiatives stabilize. |

## Notes on Other Initiatives
- Larger historical items (MAP-SCALE, FORWARD-EQUIV, DB-AT-* smoke gates, etc.) plus closed/archived efforts remain in `docs/fix_plan_archive.md`. Reference that file when you need the complete Attempts History per prompt guidance.
- If any “pending” item above becomes active, move it into the table with a fresh evidence pointer and summarize new blockers/results here.

## Archive Pointer
- `docs/fix_plan_archive.md` — verbatim copy of the previous full ledger, retaining narrative Attempts History for every initiative.
