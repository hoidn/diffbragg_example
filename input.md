# Ralph Input — Loop i=247

## Summary
Portfolio remains in stable maintenance mode. Status drift corrected in fix_plan.md. Awaiting user direction for unblock action.

## Focus
Portfolio Maintenance (no active initiative)

## Branch
`integration`

## Mapped Tests
none — maintenance mode (no implementation work)

## Artifacts
`plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-09T203900Z/`

---

## Do Now (Maintenance)

**Action Type:** Maintenance / Review

### Status Drift Corrections Applied This Loop (i=246)

1. **ARCH-SIM-CONSTRUCTION-001**: Detailed section (line 151) incorrectly showed `in_progress` — corrected to `blocked_pending_environment` to match roadmap and lifecycle_decision.md
2. **ARCH-GRADIENT-FLOW-001**: Detailed section (line 269) showed `unblocked` — corrected to `done` to match roadmap

### Portfolio Status

**Completed (Tier 0-3):**
- ARCH-GRADIENT-FLOW-001: **done** — 6/6 gradcheck tests PASS
- PERF-GPU-MEM-001: **done** — pixel_batch_size=32 threading validated
- DB-AT-SUITE-CARE-001: **done** — D.1-D.4 complete
- All roll-ups: closed (TORCH-CLI-BRIDGE, FORWARD-EQUIV-COVERAGE, MAP-SCALE-SYNC, TORCH-GEOMETRY-SYNC)
- Tooling/observability: ARCH-TELEMETRY-002, SPEC-SQUARE-PARTIALITY-001 done

**Blocked (requires external input):**
- **ARCH-SIM-CONSTRUCTION-001**: blocked_pending_environment — F_latt at 11% of expected amplitude (4206.5 vs 38,048); sincg bug in nanobrag_torch suspected; 39 loops exceeded budget
- **ARCH-REFACTOR-001**: blocked_pending_architecture (depends on ARCH-SIM-CONSTRUCTION-001)
- **PHYSICS-LOSS-CONSISTENCY**: pending (depends on ARCH-REFACTOR-001)
- **PERF-WARM-SIM-001**: blocked (Stage C panel-loss path diverges)

**Tier 4 (low priority, needs scoping):**
- SUPERVISOR: scoped_low_priority
- HARDEN-SUBMODULE-ROBUSTNESS, ORCH-ROBUST-001, ORCH-CLAUDE-PATH-FIX-001, ORCH-CLI-FALLBACK-001: pending stubs

### Recommended Unblock Action (User Choice)

Per `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T200000Z/lifecycle_decision.md`:

**Option A (Recommended)**: File sincg investigation request to nanobrag_torch maintainers
- Evidence: F_latt at 11% of expected amplitude
- Oversample=1 achieves 0.0005% error, proving HKL/beam correct
- Deficit appears in raw subpixel sum before omega application
- Request: Investigate sincg lattice factor computation in nanobrag_torch

**Option B**: Relax DB-AT-028/029 acceptance criteria (risk: masks physics bugs)

**Option C**: Prioritize Tier 4 orchestration work or new user-driven feature

---

## Maintenance Tasks (if proceeding)

1. **Inbox/Outbox Check**: Done — no new responses since Dec 8 18:38
2. **Fix Plan Hygiene**: Status drift corrected this loop
3. **Status**: Portfolio healthy, awaiting unblock

---

## Environment

- nanobrag_torch source: `/home/ollie/Documents/nanoBragg/src/nanobrag_torch`
- DBEX source: `/home/ollie/Documents/diffbragg_example`
- GPU: 24GB (OOM fix validated with pixel_batch_size=32)

---

## Pitfalls To Avoid

1. **DO NOT** start new implementation without supervisor approval
2. **DO NOT** make production code changes in maintenance mode
3. **DO** wait for user direction or external unblock

---

## If Blocked

N/A — maintenance mode is the expected state.

---

## Findings Applied (Mandatory)

No relevant findings — maintenance mode.

---

## Pointers

- `docs/fix_plan.md:16-124` — Execution Roadmap
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T200000Z/lifecycle_decision.md` — ARCH-SIM-CONSTRUCTION-001 blocking rationale + unblock options
- `galph_memory.md` — Latest loop i=246 entry
