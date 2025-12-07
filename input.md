# Input for Ralph — Loop i=120

## Summary
FINDINGS-LEDGER-002 Phase B.2: Establish reciprocal cross-links between docs/findings.md and docs/fix_plan.md to reach ≥78% consumer coverage (58 of 74 Active findings).

## Metadata
- **Mode:** Docs
- **ActionType:** implementation_ready
- **DecisionStatus:** patch_ready
- **InitiativeType:** housekeeping/docs
- **Focus:** [FINDINGS-LEDGER-002] — Findings Ledger Upkeep & Knowledge Base Maintenance
- **Branch:** integration
- **Mapped tests:** none — docs-only (doc graph consistency validated by crosslink_matrix regeneration)
- **Artifacts:** `plans/active/FINDINGS-LEDGER-002/reports/2025-12-07T060000Z/` (Phase B.1 complete), new artifacts → `plans/active/FINDINGS-LEDGER-002/reports/2025-12-07T080000Z/`

## Findings Applied (Mandatory)
**No relevant findings** — this initiative IS the findings maintenance work.

## ARCH Contracts (mandatory)
**N/A** — documentation-only initiative, no production code changes.

## Do Now

**Context:**
Phase B.1 complete (2025-12-07T060000Z): consumer mapping delivered, 9/74 Active findings (12.2%) have explicit fix-plan consumers, 64 orphaned. Phase B.2 strategy defined in `plans/active/FINDINGS-LEDGER-002/reports/2025-12-07T060000Z/planning_notes.md` lines 122-237.

**Implement Phase B.2 — Reciprocal Annotations:**

1. **Update `docs/fix_plan.md` initiative descriptions** (Tier 1 & Tier 2) with explicit "Governed by" lines:

   **Tier 1 updates:**
   - **[TORCH-REFINE-CLEANUP-001]** (line ~40): Add "**Governed by:** REFINE-001, REFINE-002, REFINE-003, REFINE-006, REFINE-009, REFINE-010, GRADIENT-001, REFINE-016"
   - **[MAP-SCALE-SYNC-001]** (line ~37): Add "**Governed by:** SCALE-001, SCALE-002, SCALE-003, SCALE-004, SCALE-005, SCALE-006, SCALE-007"
   - **[TORCH-GEOMETRY-SYNC-001]** (line ~39): Add "**Governed by:** GEOMETRY-001, GEOMETRY-002, GEOMETRY-003, GEOMETRY-004, CONFIG-001, DXTBX-001, HKL-ORIENT-001, CONVERGENCE-001"
   - **[DB-AT-SUITE-CARE-001]** (line ~36): Add "**Governed by:** TESTING-003, RUNTIME-001, DIAGNOSTICS-001, MASKING-001"
   - **[FORWARD-EQUIV-COVERAGE-001]** (line ~43): Add "**Governed by:** PARITY-001, MANIFEST-001"

   **NEW Tier 1 initiative (insert after PHYSICS-LOSS-001 line ~38):**
   ```markdown
   - [PHYSICS-LOSS-CONSISTENCY] (Physics Loss Function Alignment) — **pending**.
     - **Governed by:** PHYSICS-LOSS-001, PHYSICS-LOSS-002, PHYSICS-LOSS-003, PHYSICS-LOSS-004, PHYSICS-LOSS-005
     - **Goal:** Align Stage A/B/C chi-squared computation, enforce sigma-floor guard, unify sigma-map ingestion contract, harvest DIALS external_lookup metadata.
     - **Exit Criteria:** All stages use identical variance-weighted denominator per spec-db-core.md:57-68; telemetry persists both chi_squared + masked_mse; sigma-floor enforcement validated via unit tests; sigma-map/external_lookup ingestion contracts tested.
     - **Dependencies:** ARCH-REFACTOR-001 (Stage A/B/C context + observer pattern provides hooks for unified loss computation).
   ```

   **Tier 2 updates:**
   - **[ARCH-REFACTOR-001]** (line ~27): Add "**Governed by:** REFINE-001, ARCH-ENGINE-002, ARCH-ENGINE-003, ARCH-FACTORY-001, ARCH-FACTORY-003"
   - **[PERF-WARM-SIM-001]** (line ~62): Add "**Governed by:** PERF-WARM-001, PERF-WARM-002, PERF-WARM-003, PERF-WARM-004, PERF-WARM-005, PERF-WARM-006, PERF-WARM-007, PERF-WARM-008, PERF-WARM-009, PERF-WARM-010, PERF-WARM-011, PERF-WARM-012, PERF-WARM-013, REFINE-007, REFINE-011, REFINE-012"

   **NEW Tier 2 initiative (insert after ARCH-STAGE-CONTEXT-001 line ~63):**
   ```markdown
   - [ARCH-STAGE-CONTEXT-CONSOLIDATION] (Stage Context Parameter Consolidation) — **pending**.
     - **Governed by:** ARCH-STAGE-CTX-001, ARCH-STAGE-CTX-002
     - **Depends on:** ARCH-REFACTOR-001 (Phases A-C complete — Stage A/B/C helpers now own their logic)
     - **Goal:** Replace 10–15 positional arguments in Stage helper signatures with single typed `context` parameter (extend StageAContext/StageBContext/StageCContext dataclasses); eliminate telemetry dict mutations in Stage B baseline parity guard by exposing typed setter methods.
     - **Exit Criteria:** Stage A/B/C `_build_*_params` and `_run_*_lbfgs` accept single context parameter; telemetry updates use dataclass property assignment or setter methods; enforcement test validates context immutability guarantees.
     - **Working Plan:** to be created under `plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/implementation.md`
   ```

2. **Update `docs/findings.md` table** with Consumer metadata:
   - For each finding now governed by an initiative, append " **Consumers:** [INITIATIVE-ID]" to the Summary column.
   - Format example (GEOMETRY-001, table line ~5):
     ```markdown
     | GEOMETRY-001 | 2025-10-28 | geometry, detector, dxtbx | Bridge MUST derive beam center and detector vectors exactly per dxtbx mapping; reject non-square pixel pitch. **Consumers:** TORCH-GEOMETRY-SYNC-001. | docs/spec-db-core.md:35 | Active |
     ```
   - Apply to **58 findings** (see consumer mapping in `plans/active/FINDINGS-LEDGER-002/reports/2025-12-07T060000Z/crosslink_matrix.md` lines 84-200 + Phase B.2 expansions).

   **Specific consumer assignments** (grouped by initiative):
   - **TORCH-REFINE-CLEANUP-001:** REFINE-001, REFINE-002, REFINE-003, REFINE-006, REFINE-009, REFINE-010, GRADIENT-001, REFINE-016
   - **MAP-SCALE-SYNC-001:** SCALE-001, SCALE-002, SCALE-003, SCALE-004, SCALE-005, SCALE-006, SCALE-007
   - **PERF-WARM-SIM-001:** PERF-WARM-001 through PERF-WARM-013, REFINE-007, REFINE-011, REFINE-012
   - **TORCH-GEOMETRY-SYNC-001:** GEOMETRY-001, GEOMETRY-002, GEOMETRY-003, GEOMETRY-004, CONFIG-001, DXTBX-001, HKL-ORIENT-001, CONVERGENCE-001
   - **PHYSICS-LOSS-CONSISTENCY:** PHYSICS-LOSS-001, PHYSICS-LOSS-002, PHYSICS-LOSS-003, PHYSICS-LOSS-004, PHYSICS-LOSS-005
   - **ARCH-REFACTOR-001:** REFINE-001 (already listed under TORCH-REFINE-CLEANUP-001, dual consumers OK), ARCH-ENGINE-002, ARCH-ENGINE-003, ARCH-FACTORY-001, ARCH-FACTORY-003
   - **ARCH-STAGE-CONTEXT-CONSOLIDATION:** ARCH-STAGE-CTX-001, ARCH-STAGE-CTX-002
   - **DB-AT-SUITE-CARE-001:** TESTING-003, RUNTIME-001, DIAGNOSTICS-001, MASKING-001
   - **FORWARD-EQUIV-COVERAGE-001:** PARITY-001, MANIFEST-001
   - **ARCH-IMPL-CONFORMANCE-001:** CONFORMANCE-001 (already linked)
   - **TORCH-API-ALIGN-001:** MODEL-001 (retrospective, initiative done but finding still Active — add consumer note)

3. **Regenerate consumer mapping artifacts** to validate ≥78% coverage:
   - Run `python plans/active/FINDINGS-LEDGER-002/reports/2025-12-07T060000Z/map_consumers.py` (or equivalent grep/script) against updated `docs/fix_plan.md`.
   - Capture output to `plans/active/FINDINGS-LEDGER-002/reports/2025-12-07T080000Z/consumer_map_v2.json`.
   - Update `crosslink_matrix.md` summary stats (expect ~58 findings with consumers, 78.4% coverage).

4. **Update FINDINGS-LEDGER-002 implementation.md:**
   - Mark Phase B.1 checkbox DONE.
   - Mark Phase B.2 "Reciprocal Annotations" subtask DONE.
   - Update Phase B.3 status: "DEFERRED — archive/retire candidates require pytest validation (CLI-001/002, CONFIG-002/003, REFINE-014, SCALE-003)".

5. **Commit hygiene:**
   - Write Phase B.2 summary to `plans/active/FINDINGS-LEDGER-002/reports/2025-12-07T080000Z/summary.md`.
   - Update `docs/fix_plan.md` Attempts History for FINDINGS-LEDGER-002 with Phase B.2 completion timestamp + artifact path.

**Validation:**
- Consumer coverage ≥78% (58 of 74 Active findings with explicit fix-plan consumers).
- Reciprocal links: each cited finding includes "Consumers: [INITIATIVE-ID]" in findings.md.
- Roll-up completeness: all major finding clusters map to documented initiatives.
- No production code changes (docs-only per Environment Freeze).

## Forbidden This Loop
- No production code edits (`dbex/`, `src/`, `tests/` source modules).
- No environment modifications.
- No pytest runs (validation deferred to Phase B.3).

## How-To Map
**N/A** — documentation edits only, no test runs.

## Pitfalls To Avoid
1. **Type discipline:** This is housekeeping/docs work (no spec_change, no architecture code changes).
2. **Doc consistency:** Update both findings.md AND fix_plan.md in the same loop to keep doc graph synchronized.
3. **Initiative naming:** New initiatives ([PHYSICS-LOSS-CONSISTENCY], [ARCH-STAGE-CONTEXT-CONSOLIDATION]) must follow fix-plan ID conventions (uppercase, hyphens, descriptive).
4. **Coverage validation:** Regenerate consumer_map after edits to confirm ≥78% before committing.
5. **Findings table format:** Preserve markdown table alignment when adding Consumer metadata to Summary column (avoid breaking table structure).
6. **Cross-refs:** Ensure findings.md consumer citations match initiative IDs in fix_plan.md exactly (no typos).
7. **Deferral documentation:** Phase B.3 archive/retire candidates must stay Active until pytest validation confirms code fixes landed.

## If Blocked
- If findings.md table editing breaks markdown format, revert and append Consumer metadata as separate bullet points under each finding entry.
- If consumer_map regeneration script fails, manually verify ≥58 findings have consumer citations via `grep -c "Consumers:" docs/findings.md`.
- If fix_plan.md line numbers drift during editing, use section headers (e.g., "### Tier 1: Core Physics & Stability") to locate insertion points.
- Record any blockers in `plans/active/FINDINGS-LEDGER-002/reports/2025-12-07T080000Z/blockers.md` and mark Phase B.2 as in_progress (not done).

## Doc Sync Plan
**N/A** — no test additions or renames this loop.
