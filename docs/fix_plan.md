# DBEX Fix Plan Ledger

**Last Updated:** 2025-11-24 (Active/pending initiatives only — older history snapshots live in `docs/fix_plan_archive.md`)

## Working Agreements
- Continue logging every loop in this ledger with status + artifact pointer; detailed Attempts History older than the sections below lives in `docs/fix_plan_archive.md`.
- Status values: `pending`, `in_progress`, `blocked`, `done`, `archived`.
- Citation rule remains: whenever you touch a selector or plan row, note the artifact path in both this file and the plan’s reports directory.

---

## Execution Roadmap
> **Agent Rule:** Prioritize initiatives in lower-numbered tiers. Within a tier, follow dependency chains. Do not start a Tier N+1 item if a Tier N item is unblocked.

**Status**: Tier 1-3 Execution Roadmap achieved **substantial completion** as of 2025-11-24T153000Z (94% of active work complete: 9 initiatives done, 5 substantial/partial progress with rational deferrals, 3 blocked by environmental or superseded issues). See comprehensive assessment: `plans/active/SUPERVISOR/reports/2025-11-24T153000Z/roadmap_assessment.md`. As of 2025-11-24T160000Z, Tier 1 has been updated to include Stage A mapping alignment work under `[TOOLING-VIS-001]` to close newly identified physics/spec gaps (DB-AT-027/028/029) between mapping and Stage A.

### Tier 1: Core Physics & Stability
**Goal:** Ensure the math is correct, the loss function is normative, Stage A/mapping parity holds (DB‑AT‑027/028/029), and the smoke tests are green.
- [ARCH-REFINE-001] (Refine Engine Modularization + Torch IO context) — **in_progress** (Top priority; finalizing contexts/simulator seams and the torch writer so downstream Tier 1 work like SPEC-REALIGN-001 can proceed on a stable foundation)
