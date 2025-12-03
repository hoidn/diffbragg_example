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
  2. Adding dedicated `### [ROLLUP-ID]` sections to `docs/fix_plan.md` with dependencies, exit criteria, and Attempts History links for each grouped initiative.
  3. Updating the Plan Directory Inventory appendix so it references both the bucket classification log and the roll-up config required by the automation guard.

### Phase C — Ledger / Doc Updates & Regression Guard
- **C1** Add a “Plan Directory Inventory” appendix to `docs/fix_plan.md` summarizing the latest report and linking to artifacts; include open remediation items.
- **C2** Update `docs/fix_plan_archive.md` if any initiatives were formally archived during this effort.
- **C3** Wire the new inventory script into `plans/active/PORTFOLIO-STATUS/bin/README.md` (or equivalent) with rerun instructions; note this guardrail in `docs/fix_plan.md` Working Agreements.

## Abort / Escalation Criteria
- If more than 5 plan directories lack implementation plans or contain partial data, pause after Phase A and escalate via `docs/fix_plan.md` (open a spec-change or tooling initiative to repair the planning pipeline).  
- If moving/archiving directories risks breaking historical artifact references (e.g., a finding points directly to a path), document the risk in `docs/findings.md` and flag the initiative as blocked pending stakeholder confirmation.
