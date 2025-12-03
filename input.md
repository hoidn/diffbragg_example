# Input for Ralph — Loop 2025-12-03T112709Z

## Summary
Kick off FINDINGS-LEDGER-002 Phase A by auditing every entry in `docs/findings.md`, fixing missing `path:line` citations/statuses where needed, and capturing the results in a machine-readable inventory plus an audit report under this initiative’s reports tree.

## Mode
Docs

## InitiativeType
housekeeping

## Focus
FINDINGS-LEDGER-002 — Findings ledger upkeep and knowledge base maintenance

## Branch
integration

## Mapped tests
none — docs-only

## Artifacts
plans/active/FINDINGS-LEDGER-002/reports/${REPORT_TS}/  *(set `REPORT_TS` per How-To Map)*

## Do Now
1. **Implement: docs/findings.md — Phase A.2 audit fixes**  
   - Review every row in the findings table and ensure the `Source` column includes at least one repo-relative `path:line` citation (code, spec, or plan).  
   - Where the citation or `Status` cell is missing/outdated, add the correct reference (e.g., `dbex/refinement/stage_c.py:174`) and update the status to reflect current reality (`Active`, `Resolved`, etc.).  
   - Note any entries you cannot conclusively update inside the audit report (next steps) instead of leaving TODOs inline.
2. **Implement: plans/active/FINDINGS-LEDGER-002/reports/<REPORT_TS>/findings_inventory.json — Structured coverage data**  
   - Create a timestamped report directory (see How-To Map) and write a JSON file listing each finding with fields such as `id`, `date`, `tags`, `status`, `has_path_line`, and `notes`.  
   - Populate `has_path_line` based on the audited `docs/findings.md` content so we can track citation coverage programmatically.
3. **Implement: plans/active/FINDINGS-LEDGER-002/reports/<REPORT_TS>/findings_audit.md — Narrative summary**  
   - Summarize the audit: total findings, how many required citation fixes, how many remain deferred, and any follow-ups needed for Phase B (cross-linking).  
   - Reference the JSON inventory file so future loops can diff coverage easily.

## How-To Map
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
export REPORT_TS=$(date -u +%Y-%m-%dT%H%M%SZ)
mkdir -p plans/active/FINDINGS-LEDGER-002/reports/${REPORT_TS}

# Parse docs/findings.md into a JSON skeleton you can refine by hand
env REPORT_TS=${REPORT_TS} python - <<'PY'
import json, os, pathlib
rows = []
for line in pathlib.Path('docs/findings.md').read_text().splitlines():
    if not line.startswith('|') or line.startswith('| ID'):
        continue
    cells = [c.strip() for c in line.strip().strip('|').split('|')]
    if cells[0] in ('ID', ''):
        continue
    source = cells[4]
    rows.append({
        'id': cells[0],
        'date': cells[1],
        'tags': [t.strip() for t in cells[2].split(',') if t.strip()],
        'status': cells[5],
        'summary': cells[3],
        'source': source,
        'has_path_line': ':' in source,  # adjust after manual review
        'notes': ''
    })
path = pathlib.Path('plans/active/FINDINGS-LEDGER-002/reports') / os.environ['REPORT_TS'] / 'findings_inventory.json'
path.write_text(json.dumps(rows, indent=2) + '\n')
PY

# After updating docs/findings.md and the JSON file, document the audit
$EDITOR plans/active/FINDINGS-LEDGER-002/reports/${REPORT_TS}/findings_audit.md
```
- Update `findings_inventory.json` if you override `has_path_line` or add notes during the manual audit.  
- Keep the Markdown table aligned (pipes + header separator) when editing `docs/findings.md`.

## Pitfalls To Avoid
- Do not reorder or renumber finding IDs; only update the citation/status cells in-place.
- Use repo-relative `path:line` syntax (e.g., `dbex/refinement/stage_c.py:174`) so downstream tooling can jump directly to the source.
- When a finding truly lacks a code/spec anchor, record the gap in `findings_audit.md` instead of inventing a placeholder citation.
- Preserve the existing table header and column alignment; mismatched pipes will break downstream parsers.
- Keep the doc changes ASCII-only and coordinate with fix-plan updates if a status change implies follow-up work elsewhere.

## If Blocked
If you cannot confirm a citation for a finding (e.g., the underlying code moved or no longer exists), stop editing that row, record the issue in `findings_audit.md` (include the finding ID and suspected source), and set the JSON entry’s `notes` field accordingly. Surface the unresolved items at the top of the audit report so we can decide whether to open a new initiative or retire the finding before continuing.

## Findings Applied
No relevant findings in the knowledge base.

## Pointers
- `plans/active/FINDINGS-LEDGER-002/implementation.md:1` — Phase breakdown and Exit Criteria for this initiative.
- `plans/active/FINDINGS-LEDGER-002/reports/2025-12-03T112709Z/planning_notes.md:1` — Context for the new plan and immediate next steps.
- `docs/findings.md:1` — Knowledge base ledger to audit.
- `docs/fix_plan.md:45` — Tier 1 entry describing FINDINGS-LEDGER-002 obligations.
- `docs/index.md:48` — Knowledge Base Ledger guidance referenced in Working Agreements.

## Next Up (optional)
If time remains after completing the audit, start mapping active findings to their consuming fix-plan entries (Phase B) so cross-linking work can begin in the following loop.
