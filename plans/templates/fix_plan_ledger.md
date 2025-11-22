# DBEX Fix Plan Ledger

> Template: use this as the starting point for `docs/fix_plan.md`.  
> Replace placeholders (`YYYY-MM-DD`, `INITIATIVE-ID`, etc.) and prune example rows as the real ledger evolves.

**Last Updated:** YYYY-MM-DD

## Working Agreements
- **Status values:** `pending`, `in_progress`, `blocked`, `done`, `archived`.
- **Artifacts:** Store loop outputs in `plans/active/<initiative-id>/reports/<YYYY-MM-DDTHHMMSSZ>/`.
- **Attempts History:** After every Galph/Ralph loop on an initiative, append an Attempts History line with `mode`, `selector(s)`, key results, and:
  - `Metrics:` (if applicable), and
  - `Artifacts:` (reports directory path).
- **Archive policy:** When this file becomes unwieldy (≈500+ lines), move older, fully `done` initiatives and detailed Attempts History into `docs/fix_plan_archive.md`, keeping this ledger focused on current work.
- **Citation rule:** Whenever you touch a selector, gate, or plan row, note the relevant artifacts path here and in the corresponding `plans/active/<initiative-id>/reports/` tree.
- **Execution tiers:** Galph must prioritize lower-numbered tiers in the Execution Roadmap when choosing a focus, subject to dependencies and the WIP cap in `prompts/supervisor.md`.

---

## Execution Roadmap (Tiers)
> **Agent Rule:** Treat lower-numbered tiers as higher priority.  
> Within a tier, follow dependency chains and initiative `Priority:` fields.  
> Do **not** start a Tier N+1 initiative while a Tier N initiative is unblocked and not `done` (unless explicitly overridden and documented in Attempts History).

### Tier 1 (Highest): Core Physics & Stability
**Goal:** Ensure math is correct, the loss function matches the normative Spec, and critical smoke tests are green and stable.
- [INITIATIVE-ID] (Short Title) — *Status*
- [PHYSICS-LOSS-001] Implement variance-weighted loss function — *done*  <!-- example, adjust/remove in real ledger -->

### Tier 2: Geometry & Mapping Robustness
**Goal:** Eliminate zero-point discontinuities and mapping mismatches between legacy and torch backends.
- [INITIATIVE-ID] (Short Title) — *Status*
- [TORCH-REFINE-002E] Fix Stage A zero-point geometry discontinuity — *in_progress*  <!-- example -->

### Tier 3: Architectural Maturity
**Goal:** Refactor monolithic loops into maintainable engines with clear boundaries and testable seams.
- [INITIATIVE-ID] (Short Title) — *Status*

### Tier 4: Tooling, Observability & UX
**Goal:** Improve visualization, diagnostics, documentation, and quality-of-life tooling without changing core physics.
- [INITIATIVE-ID] (Short Title) — *Status*

> Adjust, rename, or add tiers as the program evolves, but keep the “lower number = higher priority” invariant stable for agents.

---

## Active / Pending Initiatives

### [INITIATIVE-ID] Title of Initiative
- Depends on: [DEPENDENCY-ID-1], [DEPENDENCY-ID-2]  <!-- Spec/docs/tests or other initiatives -->
- Status: pending
- Priority: High | Medium | Low  <!-- Local priority within tier -->
- Tier: 1 | 2 | 3 | 4  <!-- Mirror the Execution Roadmap tier -->
- Owner/Date: Unassigned
- Exit Criteria:
  1. Criterion 1 (tie to a specific Spec clause, e.g., `docs/spec-db-core.md §X.Y`).
  2. Criterion 2 (tie to a specific pytest selector or CLI command).
  3. Criterion 3 (telemetry/diagnostics requirement, if applicable).
- Working Plan: `plans/active/INITIATIVE-ID/implementation.md`
- Attempts History:
  * YYYY-MM-DDTHHMMSSZ (planning|implementation|review) — Short description of what changed; include `Metrics:` and `Artifacts:` suffixes when applicable.
    - Metrics: <optional key metrics summary>
    - Artifacts: `plans/active/INITIATIVE-ID/reports/YYYYMMDDTHHMMSSZ/`

---

## Suite Failures
> **Agent Rule:** Treat these as high-priority interrupts sourced from the `prompts/full_suite.md` sentinel.  
> Each failing test module gets **one** compact block (3–4 lines) that is updated in place by the full-suite loop.

### [Suite Failure][YYYY-MM-DD] tests/<module>.py — Priority: High — Status: pending
Repro: KMP_DUPLICATE_LIB_OK=TRUE pytest tests/<module>.py
Failures: <node_ids_or_error_signature>
Log: plans/active/FULL-SUITE-INITIATIVE-ID/reports/YYYYMMDDTHHMMSSZ/pytest.log

> When the full suite is re-run:
> - If the module still fails, update the existing block (date, failures, log path) instead of adding a new one.  
> - If the module is now clean and the corresponding work is complete, update `Status:` to `done` and optionally move the block (or its history) into `docs/fix_plan_archive.md`.

