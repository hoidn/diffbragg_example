# Implementation Plan — PORTFOLIO-STATUS: Plan/Fix-Plan Synchronization

**Status:** in_progress  
**Owner:** Galph ↔ Ralph  
**Initiative Type:** housekeeping (docs/process)  
**Artifacts Root:** `plans/active/PORTFOLIO-STATUS/reports/`

## Goals
1. Produce an authoritative inventory of every subtree under `plans/active/`, including lifecycle metadata (last report timestamp, implementation plan status).
2. Ensure each active plan directory has a corresponding entry in `docs/fix_plan.md` (or is archived/moved if obsolete).
3. Establish a lightweight regression (script + report) that can be re-run whenever plans are added/removed so drift is caught within a single loop.

## Non-Goals
- No production code or simulator changes.  
- Do not alter historical report contents; archival moves MUST preserve relative paths referenced by past findings.  
- No attempt to revive dormant initiatives unless the fix plan explicitly reintroduces them.

## Exit Criteria
1. Inventory script emits a machine-readable summary (`inventory.json`) plus a human-oriented markdown report stored under this initiative’s reports directory; summary includes: initiative ID, presence in fix_plan.md, implementation.md existence, latest report timestamp, suggested action.
2. All plan directories are either (a) linked from `docs/fix_plan.md` with up-to-date metadata (status, tier, initiative type, artifacts path) or (b) relocated under `archive/plans/<ID>/` with cross-references recorded in both the plan header and `docs/fix_plan.md`.
3. `docs/fix_plan.md` gains a “Plan Directory Inventory” appendix referencing the latest inventory artifact and listing any outstanding remediation items.
4. `docs/fix_plan.md` Attempts History references this initiative and records the inventory artifact path; `galph_memory.md` points at the same evidence.

## Spec / Doc Alignment
- CLAUDE.md §Environment Freeze — documentation-only scope.  
- `docs/index.md` → Fix plan ledger and doc graph expectations.  
- `plans/templates/implementation_plan.md` → Structural guardrails for this document.

## Dependencies / Risks
- Requires wide read access to `plans/active/` and `docs/fix_plan.md`.  
- Must avoid clobbering concurrent updates to `docs/fix_plan.md`; coordinate via `git pull --rebase` before edits.  
- Moving directories affects existing artifact pointers; archive paths MUST be announced in `docs/fix_plan.md` and `docs/fix_plan_archive.md`.

## Phase Breakdown

### Phase A — Inventory & Drift Detection
- **A1** Record current `plans/active/` listing and parse `docs/fix_plan.md` identifiers into a normalized set (store raw output under reports/ as `inventory_raw.txt`).
- **A2** Implement a Tier-2 script (`plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py`) that emits JSON + Markdown summaries enumerating: plan ID, has_implementation_md, in_fix_plan, last_report_iso, status_hint (parsed from plan header if available).
- **A3** Attach the script output to `plans/active/PORTFOLIO-STATUS/reports/<timestamp>/inventory_report.md` and reference it from `docs/fix_plan.md` Attempts History.

### Phase B — Classification & Remediation
- **B1** Classify each plan into {active, archived-ready, duplicate/alias}. Utilize plan header hints (Status, Owner) plus latest report timestamps to justify classification. *(Completed in `reports/2025-12-05T150000Z/classification.md` with bucket tables.)*
- **B2** For plans marked archived-ready, move them under `archive/plans/` (maintaining original structure) and leave a stub note pointing to the archive. *(ARCH-REFRACTOR-001 moved in the same report set; stub_status.md records new implementation.md placeholders.)*
- **B3** For active plans missing fix plan coverage, author/update corresponding entries in `docs/fix_plan.md` (Tier, dependencies, initiative type, status, artifacts path). **New blueprint:** `reports/2025-12-05T183000Z/ledger_rollup_plan.md` enumerates the roll-up IDs, member directories, spec references, and the script/test work required to keep the classification automated. Execution of B3 now includes:
  1. Extending `bin/plan_inventory.py` to emit roll-up aware JSON/Markdown (configurable via `--rollup-config`) plus pytest coverage under `plans/active/PORTFOLIO-STATUS/tests/`.
     - **Status 2025-12-05T210000Z:** ✅ COMPLETE — Script + tests delivered in `reports/2025-12-05T210000Z/`; see `test_plan_inventory.py`.
  2. Adding dedicated `### [ROLLUP-ID]` sections to `docs/fix_plan.md` with dependencies, exit criteria, and Attempts History links for each grouped initiative.
     - **Status 2025-12-03T120000Z:** ✅ COMPLETE — All 13 roll-up sections added (lines 203-416): DB-AT-SUITE-CARE-001, MAP-SCALE-SYNC-001, PHYSICS-LOSS-001, TORCH-GEOMETRY-SYNC-001, TORCH-REFINE-CLEANUP-001, TORCH-CLI-BRIDGE-ROLLUP-001, FORWARD-EQUIV-COVERAGE-001, TOOLING-VIS-001, DOCS-ROADMAP-001, RUNTIME-VEC-001, REPORT-NANOBRAG-STATUS-001, NANOBRAG-GOLDEN-001, ARCH-SPLIT-001. Each section includes dependencies, initiative type, exit criteria (tied to spec clauses per ledger_rollup_plan.md), member plan directories, spec references, and Attempts History linking to classification artifact. All sections follow the ledger_rollup_plan.md blueprint with spec citations from docs/spec-db-conformance.md, docs/spec-db-workflow.md, docs/spec-db-core.md, docs/spec-db-interfaces.md, docs/spec-db-vis.md, etc.
     - **Regeneration 2025-12-03T120000Z:** Roll-up sections verified in place; inventory regeneration completed with rollup_report.md validation. Artifacts archived at `plans/active/PORTFOLIO-STATUS/reports/2025-12-03T120000Z/`.
  3. Updating the Plan Directory Inventory appendix so it references both the bucket classification log and the roll-up config required by the automation guard.
     - **Status 2025-12-05T210000Z:** ✅ COMPLETE — Appendix updated (doc lines 530-598 in archived snapshot; current lines reflect 2025-12-03T120000Z timestamp update); automation guard command includes --rollup-config flag.
     - **Verification 2025-12-05T235500Z:** ✅ COMPLETE — Regenerated inventory artifacts confirming all 13 roll-ups show "✓ Section exists" in rollup_report.md (100% coverage); updated appendix with current bucket counts (55 total, 22 tracked, 32 active_missing, 1 missing_plan) and artifact pointers to 2025-12-05T235500Z reports directory.

### Phase C — Ledger / Doc Updates & Regression Guard
- **C1** Add a "Plan Directory Inventory" appendix to `docs/fix_plan.md` summarizing the latest report and linking to artifacts; include open remediation items.
- **C2** Update `docs/fix_plan_archive.md` if any initiatives were formally archived during this effort.
- **C3** Wire the new inventory script into `plans/active/PORTFOLIO-STATUS/bin/README.md` (or equivalent) with rerun instructions; note this guardrail in `docs/fix_plan.md` Working Agreements.

**Phase C Focus (2025-12-05T235500Z):** With Phase B3 complete (roll-up automation + ledger sections + verification artifacts delivered), Phase C work remains:
- **C.1 Automation Guard:** Update `docs/fix_plan.md` Working Agreements section to explicitly reference `--rollup-config` flag in the rerun command, ensuring future loops don't omit roll-up validation.
- **C.2 Archive Hygiene:** Review plan-archive structure and ensure archived initiatives (ARCH-REFRACTOR-001, etc.) have complete cross-references in both `docs/fix_plan_archive.md` and their stub locations.
- **C.3 Exit Prep:** Once C.1 and C.2 complete, mark PORTFOLIO-STATUS ready for closure or handoff to a Phase D guardian task (if roll-up member-plan status rows need periodic refresh).

- **2025-12-06T094500Z (Phase C.1/C.2 progress):** Embedded the automation guard command (with `--rollup-config`) directly in `docs/fix_plan.md` Working Agreements + appendix, updated `plan_inventory.py` to auto-load the canonical rollups.json and fail fast when the guard file is missing/invalid, refreshed unit tests, and re-verified archive hygiene (`ARCH-REFRACTOR-001` stub + `docs/fix_plan_archive.md` cross-reference). Artifacts: `plans/active/PORTFOLIO-STATUS/reports/2025-12-06T094500Z/`.

### Phase D — Roll-Up Coverage Awareness ✅ COMPLETE (2025-12-07T153000Z)
- **Trigger (2025-12-07T000000Z run):** Latest inventory (`plans/active/PORTFOLIO-STATUS/reports/2025-12-07T000000Z/`) still reports 33 plan directories "missing" even though all but one now sit inside the 13 roll-up sections added during Phase B3. Root cause: `plan_inventory.py` only considers plan IDs explicitly present in `docs/fix_plan.md`. Roll-up membership must count toward coverage so the appendix reflects reality and the ledger can close without duplicating every member plan ID.
- **D1 — Script & API updates:** ✅ COMPLETE (2025-12-07T153000Z) — Extended `plan_inventory.py` with `rollup_coverage` field in `PlanEntry`, implemented `apply_rollup_coverage()` helper to map plan directories to roll-up IDs (when roll-up sections exist in fix_plan.md), updated `compute_bucket()` to recognize `tracked_via_rollup` bucket, modified `write_missing_md()` to exclude rollup-covered plans, and added console line "Covered via rollups: 34". All changes hermetic and tested.
- **D2 — Tests:** ✅ COMPLETE (2025-12-07T153000Z) — Added `TestRollupCoverage` class with 7 hermetic tests covering single/multi-rollup membership, missing roll-up sections, bucket classification, and inventory_missing.md filtering. Updated existing tests to handle deferred bucket computation. All 25 tests pass. Artifacts: `plans/active/PORTFOLIO-STATUS/reports/2025-12-07T153000Z/pytest_plan_inventory.log`.
- **D3 — Ledger sync:** ✅ COMPLETE (2025-12-07T153000Z) — Reran inventory with guard flag; console output shows "Total plans: 56, In fix_plan.md: 23, Covered via rollups: 34, Active missing: 5". `inventory_missing.md` now lists 6 plans (5 active with implementations but no ledger/rollup coverage: HARDEN-SUBMODULE-ROBUSTNESS, ORCH-CLAUDE-PATH-FIX-001, ORCH-CLI-FALLBACK-001, ORCH-ROBUST-001, SUPERVISOR; plus 1 stub: ARCH-REFRACTOR-001). Roll-up report validates all 13 roll-ups show "✓ Section exists". Artifacts: `plans/active/PORTFOLIO-STATUS/reports/2025-12-07T153000Z/`.

### Phase E — Tier 4 Coverage + Duplicate Cleanup ✅ COMPLETE (2025-12-07T220000Z)
- **Trigger:** Phase D inventory (2025-12-07T153000Z) identified 5 genuinely untracked orchestration/agent-ops plans (HARDEN-SUBMODULE-ROBUSTNESS, ORCH-ROBUST-001, ORCH-CLAUDE-PATH-FIX-001, ORCH-CLI-FALLBACK-001, SUPERVISOR) plus 1 archive duplicate stub (ARCH-REFRACTOR-001). All 5 untracked plans had existing implementation stubs or reports but lacked ledger entries.
- **E1 — Tier 4 ledger sections:** ✅ COMPLETE (2025-12-07T220000Z) — Added 5 detailed ledger entries to `docs/fix_plan.md` following roll-up format: dependencies on CLAUDE.md/AGENTS.md/scripts/orchestration, status (pending/in_progress), initiative type (architecture/harness/docs), exit criteria tied to orchestration resiliency/path conventions/supervisor meta-documentation, working plan paths, spec references, and Attempts History linking to existing reports. Added Tier 4 roadmap section (lines 67-73) listing all 5 initiatives with brief status notes. Artifacts: `docs/fix_plan.md` lines 430-514 (detailed sections), lines 67-73 (Tier 4 roadmap entry).
- **E2 — ARCH-REFRACTOR-001 cleanup:** ✅ COMPLETE (2025-12-07T220000Z) — Removed duplicate stub directory `plans/active/ARCH-REFRACTOR-001/` (archive duplicate; canonical plan is ARCH-REFACTOR-001). Verified removal with `ls | grep ARCH-REFRACTOR` (empty output).
- **E3 — Inventory rerun + ledger sync:** ✅ COMPLETE (2025-12-07T220000Z) — Reran guarded inventory with REPORT_TS=2025-12-07T220000Z; console output shows: Total=55 (down from 56), In fix_plan=28 (up from 23), Covered via rollups=34, Active missing=0, Missing implementation.md=0. Updated Plan Directory Inventory appendix: Summary section with new counts/percentages (≈51% tracked direct, ≈62% via rollups, 0 active_missing, 0 missing_plan), Roll-up Report path, Bucket Classification section. Updated `docs/fix_plan.md` PORTFOLIO-STATUS Attempts History with Phase E summary. Artifacts: `plans/active/PORTFOLIO-STATUS/reports/2025-12-07T220000Z/` (inventory.json, inventory_missing.md, rollup_report.md, plan_inventory.log).
- **Status:** Initiative ready for closure. All active plan directories now have ledger or roll-up coverage (62 total tracked: 28 direct + 34 via rollups).

## Abort / Escalation Criteria
- If more than 5 plan directories lack implementation plans or contain partial data, pause after Phase A and escalate via `docs/fix_plan.md` (open a spec-change or tooling initiative to repair the planning pipeline).  
- If moving/archiving directories risks breaking historical artifact references (e.g., a finding points directly to a path), document the risk in `docs/findings.md` and flag the initiative as blocked pending stakeholder confirmation.
