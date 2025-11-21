# DBEX Fix Plan Ledger (Condensed)

> Full historical attempts and retired initiatives now live in `docs/fix_plan_archive.md`.

## Working Agreements
- Every loop updates this ledger (focus status + artifact pointer) and archives detailed notes under `plans/active/<id>/reports/<timestamp>/`.
- Status options: pending · in_progress · blocked · done · archived. If a selector collects 0 tests, downgrade or fix before closing.
- When blockers or major evidence emerge, summarize here with a single bullet and store full traces in the reports directory.

---

## Active Initiatives

### [PHYSICS-LOSS-001] Variance-weighted loss rollout
- **Depends on:** docs/spec-db-core.md (Variance Model)
- **Status:** in_progress — variance-weighted Stage A/B done; DIALS sigma harvest + Stage C validation outstanding.
- **Next Actions:** Implement sigma-floor telemetry + shared chi-squared helper; rerun Stage A/B/C smokes and DB-AT-010; unblock dependent initiatives (ARCH-REFINE-FLOW-001, TOOLING-VIS-001).
- **Latest Evidence:** plans/active/PHYSICS-LOSS-001/reports/2025-11-21T010127Z/ (Stage B NaN guard failure, Stage C unit mismatch).

### [PERF-SMOKE-DETSIZE] Small-detector smoke fixture & parity guard
- **Depends on:** docs/spec-db-workflow.md (Stage Smoke Dataset Policy)
- **Status:** in_progress — small-detector assets and guard landed; canonical Stage B/C smokes still failing.
- **Next Actions:** Keep canonical runs blocked until REFINE-SMOKE-CANONICAL fixes the implementation; otherwise maintain docs in sync.
- **Latest Evidence:** plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T035150Z/ (callchain snapshot + tap points showing Stage B LBFGS bug and Stage C telemetry gap).

### [REFINE-SMOKE-CANONICAL] Canonical Stage B/C repairs
- **Depends on:** docs/spec-db-workflow.md §§Stage B/C, Stage Smoke Dataset Policy
- **Status:** pending — implementation bug confirmed; plan drafted to repair Stage B LBFGS + Stage C offset telemetry.
- **Exit Criteria:** Stage B canonical smoke passes without LBFGS errors or χ² regression; Stage C proves ≥80 % offset reduction with honest telemetry.
- **Latest Evidence:** plans/active/REFINE-SMOKE-CANONICAL/reports/2025-11-21T042222Z/ (smoke logs, telemetry JSON, diagnosis).

---

## Blocked or Pending Initiatives (summary only)
- **ARCH-REFINE-FLOW-001**, **TOOLING-VIS-001**, **PERF-WARM-SIM-001**, etc. — see `docs/fix_plan_archive.md` for historical detail. These depend on PHYSICS-LOSS-001 and remain pending until variance-weighted loss and canonical smokes are healthy.

## Archive Pointer
- Detailed Attempts History, earlier initiatives, and retired efforts are preserved verbatim in `docs/fix_plan_archive.md` for reference.
