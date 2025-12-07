# Implementation Plan — FINDINGS-LEDGER-002

> Maintain `docs/findings.md` as the authoritative knowledge base, keep the doc graph synchronized with the fix-plan ledger, and establish a recurring maintenance cadence so durable lessons remain actionable.

## Initiative
- **ID:** FINDINGS-LEDGER-002
- **Title:** Findings Ledger Upkeep & Knowledge Base Maintenance
- **Owner:** Supervisor (Galph) ↔ Implementation (Ralph)
- **Initiative Type:** housekeeping / docs
- **Status:** planned
- **Artifacts Root:** `plans/active/FINDINGS-LEDGER-002/reports/`

## Goals
1. Audit every entry in `docs/findings.md` to ensure it carries (a) a stable ID, (b) `path:line` citations back to code/specs, (c) relevant tags, and (d) an explicit status (`Active`, `Resolved`, `Deferred`) that matches reality (§Knowledge Base Ledger in `docs/index.md` and Working Agreements in `docs/fix_plan.md`).
2. Cross-link findings with the fix-plan ledger so each high-impact lesson is referenced from the initiatives it governs (e.g., DIAG, ARCH, TORCH roll-ups) and stale findings are retired or migrated to `docs/fix_plan_archive.md`.
3. Establish a repeatable maintenance cadence (schedule + checklist + artifact template) so future loops can re-run the audit without re-inventing the workflow; surface the cadence in `docs/index.md` / `docs/fix_plan.md` Working Agreements.
4. Capture the audit results in machine-readable form (JSON/CSV under this initiative’s reports tree) to keep plan-inventory automation accurate and to unblock future scripting (e.g., plan inventory script referencing findings coverage).

## Non-Goals
- No production code, simulator, or CLI changes (documentation-only scope per CLAUDE.md Environment Freeze).
- No speculative additions to `docs/findings.md` without traceable evidence; this initiative curates existing knowledge rather than inventing new findings.
- No attempt to automate the entire knowledge base during Phase A; automation hooks belong in Phase C after manual audit establishes ground truth.

## Exit Criteria
1. **Ledger Integrity:** Every entry in `docs/findings.md` includes at least one `path:line` citation (file:line format) and a status flag that matches the latest evidence; an audit report under `plans/active/FINDINGS-LEDGER-002/reports/<ts>/findings_audit.md` lists coverage stats and any deferred fixes.
2. **Cross-Linking:** Each active finding is referenced from the relevant fix-plan section(s) (including roll-up blocks) or an explicit note is recorded in the audit report explaining why no consumer exists; reciprocal links from fix-plan items point back to the finding IDs.
3. **Cadence & Guardrails:** `docs/index.md` (Knowledge Base Ledger section) and `docs/fix_plan.md` Working Agreements describe the maintenance cadence, rerun command, and artifact expectations (e.g., “rerun FINDINGS-LEDGER-002 Phase C checklist quarterly”); cadence checklist stored under `plans/active/FINDINGS-LEDGER-002/bin/` or `reports/`.
4. **Automation Artifact:** Machine-readable inventory (`findings_inventory.json`) capturing ID, tags, status, `path:line` coverage, and cross-link targets lives in this initiative’s reports directory and is referenced from `docs/fix_plan.md` Attempts History.

## Spec / Doc Alignment
- `docs/index.md` (Knowledge Base Ledger section) — defines authoritative rules for findings and their use in planning loops.
- `docs/fix_plan.md` — Working Agreements demand cross-linking specs ↔ architecture ↔ plans ↔ tests; this initiative keeps the findings leg of that graph accurate.
- `docs/prompt_sources_map.json` — lists `docs/findings.md` as a primary reference; maintenance work ensures the prompt source remains trustworthy.
- `docs/TESTING_GUIDE.md` / `docs/development/TEST_SUITE_INDEX.md` — must stay synchronized when findings describe selector gaps or new guardrails.

## Dependencies / Risks
- Requires wide read/write access to `docs/findings.md`, `docs/fix_plan.md`, and plan roll-up sections; coordinate via `git pull --rebase` to avoid stomping other ledger edits.
- Risk: findings may lag behind current code/spec reality; plan must include explicit remediation steps or deferrals to prevent “forever active” entries.
- Automation risk: introducing scripts under this initiative must respect Environment Freeze (documented exceptions only) and live under `plans/active/FINDINGS-LEDGER-002/bin/`.

## Context Priming
- Read: `docs/findings.md`, `docs/fix_plan.md` Tier 0–4 entries, `docs/index.md` (docs hub), `docs/prompt_sources_map.json`.
- Related initiatives: PORTFOLIO-STATUS (plan inventory), DOCS-ROADMAP-001 (documentation governance), FINDINGS referenced throughout DIAG/ARCH/TORCH plans.

## Phase Breakdown

### Phase A — Ledger Audit & Coverage Baseline
Goal: produce a complete, cited inventory of the current findings ledger.
- **A1 — Nucleus / Scope Confirmation:** Re-read `docs/index.md` Knowledge Base Ledger guidance, enumerate required metadata fields, and confirm acceptance criteria with fix-plan Working Agreements.
- **A2 — Audit Pass:** Walk every entry in `docs/findings.md`, capture metadata into `findings_inventory.json`, flag missing/mismatched `path:line` citations, stale statuses, or obsolete tags. Store narrative findings in `reports/<ts>/findings_audit.md`.
- **A3 — Gap Remediation:** For audit items marked high-priority (missing citations, wrong status), update `docs/findings.md` or open spin-off initiatives (e.g., DOCS-ROADMAP-001) with clear TODOs. Record deferrals in the audit report.

**Artifacts:** `reports/<ts>/findings_audit.md`, `reports/<ts>/findings_inventory.json`, `reports/<ts>/findings_inventory.csv`.

### Phase B — Cross-Linking & Fix-Plan Integration
Goal: ensure every active finding has a home in the fix-plan ledger and vice versa.

**Status:** B.1 complete (2025-12-07T060000Z), B.2 complete (2025-12-07T080000Z)

- **B1 — Map Consumers (DONE 2025-12-07T060000Z):** For each active finding, list the fix-plan section(s) and plan directories it influences (roll-up IDs, Tier 0 items, etc.).
  - **Result:** 9 of 74 Active findings (12.2%) have explicit fix-plan consumers; 64 findings (86.5%) are orphaned.
  - **Artifacts:** `reports/2025-12-07T060000Z/{consumer_map.json, crosslink_matrix.md, planning_notes.md, map_consumers.py}`
  - **Key insight:** Most orphans are pattern findings (GEOMETRY-*, CONFIG-*, TESTING-*, PERF-WARM-*) governing multiple initiatives implicitly or via plan-local docs rather than top-level fix_plan.md text.

- **B2 — Reciprocal Annotations (DONE 2025-12-07T080000Z):** Updated `docs/fix_plan.md` Tier 1 & Tier 2 initiatives with "Governed by" lines citing governing findings. Created 2 new initiatives: [PHYSICS-LOSS-CONSISTENCY] (Tier 1, 5 findings), [ARCH-STAGE-CONTEXT-CONSOLIDATION] (Tier 2, 2 findings). Updated `docs/findings.md` table with "**Consumers:** [INITIATIVE-ID]." metadata for 58 findings. **Result:** 78.4% consumer coverage (58/74 Active findings), exceeding ≥78% target.
  - **Artifacts:** `plans/active/FINDINGS-LEDGER-002/reports/2025-12-07T080000Z/` (summary.md, consumer_map_v2.json, add_consumers.py)
  - **Metrics:** 7 existing initiatives updated + 2 new initiatives created; 58 findings annotated; docs-only (no production code changes)

- **B3 — Archive / Retire (DEFERRED):** Move obsolete findings into an "Archived" section (or `docs/fix_plan_archive.md` if they're redundant) with rationale; ensure plan inventory no longer treats them as active blockers.
  - **Candidates:** CLI-001/002, CONFIG-002/003, REFINE-014, SCALE-003 (validate via pytest before retiring).

**Artifacts:** `reports/<ts>/crosslink_matrix.md`, `consumer_map.json`, fix-plan updates citing artifact paths.

### Phase C — Cadence, Tooling, and Working Agreements
Goal: bake the maintenance workflow into documented guardrails.
- **C1 — Cadence Definition:** Author a checklist (e.g., quarterly) covering rerun command (`python plans/active/FINDINGS-LEDGER-002/bin/findings_inventory.py ...` or manual steps), artifact expectations, and sign-off procedure. Reference it in `docs/index.md` + `docs/fix_plan.md`.
- **C2 — Automation Hook (Optional/Tier-2):** If warranted, implement a small helper script under `plans/active/FINDINGS-LEDGER-002/bin/` that emits `findings_inventory.json` to reduce manual toil. Document usage + tests.
- **C3 — Guardrail Update:** Update Working Agreements / plan inventory instructions so the cadence becomes part of the broader doc graph (similar to the plan inventory guard).

**Artifacts:** Cadence checklist (`reports/<ts>/cadence.md`), optional bin scripts + tests, fix-plan Working Agreements updates.

## Compliance & Controls
- **Environment Freeze:** Documentation-only changes; any helper scripts live under initiative `bin/` and respect the targeted bugfix exception documentation rules (patch files, findings updates, env tags) if they ever touch vendored code.
- **Doc Consistency Guard:** Update `docs/findings.md`, `docs/fix_plan.md`, and `docs/index.md` in the same loop to keep the doc graph synchronized when changes land.

## Artifacts Index
- Reports root: `plans/active/FINDINGS-LEDGER-002/reports/`
- Latest planning session: to be created with timestamped directories per loop (e.g., `plans/active/FINDINGS-LEDGER-002/reports/2025-12-03T112709Z/`).

## Notes
- Initiative created during PORTFOLIO-STATUS Phase C to remove the final `missing_plan` bucket entry; this document now promotes the stub into a scoped plan ready for implementation.
- Coordinate with DOCS-ROADMAP-001 when cadence changes overlap with broader doc governance work.
