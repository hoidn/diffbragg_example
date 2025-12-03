# FINDINGS-LEDGER-002 — Planning Notes (2025-12-03T11:27:09Z)

## Context
- Problems ledger entry (“identify stale plans / track missing initiatives”) is now limited to knowledge-base maintenance; PORTFOLIO-STATUS is complete, but `docs/findings.md` has not received a structured audit since the new roll-up sections landed.
- `docs/index.md` and `docs/fix_plan.md` both rely on findings IDs to keep the doc graph consistent. Several entries in `docs/findings.md` still lack status flags or path:line annotations (e.g., SCALE-005, PERF-WARM-013), and none of them list downstream consumers.
- `plans/active/FINDINGS-LEDGER-002/implementation.md` was only a stub; the initiative could not progress until Goals/Exit Criteria were defined.

## Decisions
- Promote the stub into a full implementation plan with three phases (Audit → Cross-linking → Cadence & Tooling) and explicit exit criteria tied to `docs/index.md`, `docs/fix_plan.md`, and the Working Agreements.
- Treat all deliverables as documentation artifacts (no production code). Any helper scripts will live under `plans/active/FINDINGS-LEDGER-002/bin/` and follow the Environment Freeze exception policy if they ever need to touch vendored code.
- Capture audit output in both Markdown and JSON so future automation (e.g., plan inventory guard) can consume findings coverage data.

## Immediate Next Steps
1. **Phase A kick-off (next loop):**
   - Re-read `docs/findings.md`, enumerate IDs/tags/status/path coverage.
   - Produce `findings_inventory.json` + `findings_audit.md` under a fresh timestamped reports directory.
   - Update any entries missing `path:line` or status metadata.
2. Begin wiring cross-links once the audit data exists; update fix-plan roll-ups to cite the relevant finding IDs.
3. Draft cadence language for `docs/index.md` / `docs/fix_plan.md` while Phase A evidence is fresh.

## References
- docs/index.md — Knowledge Base Ledger guidance
- docs/fix_plan.md — Tier 1 entry for FINDINGS-LEDGER-002, Plan Directory Inventory appendix
- docs/findings.md — Ledger under audit
- docs/prompt_sources_map.json — lists the findings ledger as a primary prompt source
