# Input for Ralph — Loop 2025-12-05T083500Z

## Summary
Author the reusable plan-directory inventory script, run it to capture an authoritative report, and update `docs/fix_plan.md` with a Plan Inventory appendix so every `plans/active/` subtree is tracked explicitly.

## Mode
Docs

## InitiativeType
housekeeping

## Focus
PORTFOLIO-STATUS — Plan/Fix-Plan synchronization & archive hygiene

## Branch
integration

## Mapped tests
none — docs-only

## Artifacts
plans/active/PORTFOLIO-STATUS/reports/2025-12-05T120000Z/

## Do Now

1. **Phase A1/A2 — plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py**  
   Create the Tier-2 script described in the implementation plan. Requirements:  
   - Inputs: `--plans-root` (default `plans/active`), `--fix-plan` (default `docs/fix_plan.md`), `--out-dir` (required).  
   - Outputs: `inventory.json` (list of `{id,in_fix_plan,has_implementation,last_report,status_hint}`) plus `inventory_missing.md` summarizing the initiatives absent from fix_plan.  
   - Derive `status_hint` by peeking at the first non-empty line of each `implementation.md` when present (e.g., detect “Status:” or “Purpose”).  
   - Script should be idempotent and safe to rerun; document CLI usage in the module docstring per CLAUDE.md scriptization rules.

2. **Phase A3 — Run the script / capture artifacts**  
   - `mkdir -p plans/active/PORTFOLIO-STATUS/reports/2025-12-05T120000Z/`  
   - Execute the new script with default inputs, writing outputs into the artifact directory (see How-To Map).  
   - Add a short narrative `inventory_report.md` describing the high-level counts (e.g., “38 plan directories missing fix_plan coverage; 4 directories lack implementation.md”). Reference the raw JSON/Markdown outputs and cite the pre-existing ad-hoc snapshot (2025-12-05T083500Z) for continuity.

3. **Phase C1 (partial) — Update docs/fix_plan.md**  
   - Add a “Plan Directory Inventory” appendix near the bottom summarizing the latest report (timestamp + artifact path) and listing the top remediation buckets (active-but-untracked, archived-ready, missing implementation).  
   - Extend the Working Agreements near the top so future contributors know to rerun `plan_inventory.py` whenever a plan directory is added/removed.  
   - Mention the new automation guard in Attempts History under PORTFOLIO-STATUS and point to the new artifact path.

## How-To Map

```bash
timestamp=2025-12-05T120000Z
report_dir=plans/active/PORTFOLIO-STATUS/reports/$timestamp
mkdir -p "$report_dir"
python plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py \
  --plans-root plans/active \
  --fix-plan docs/fix_plan.md \
  --out-dir "$report_dir"
python - <<'PY'
from pathlib import Path
report_dir = Path("plans/active/PORTFOLIO-STATUS/reports/2025-12-05T120000Z")
missing = (report_dir / "inventory_missing.md").read_text()
Path(report_dir / "inventory_report.md").write_text(
    "# Inventory Summary\n\n" +
    "- Latest script output recorded above\n" +
    "- Snapshot counts: " + str(missing.count('\\n')) + " entries missing fix_plan coverage\n"
)
PY
```

## Pitfalls To Avoid

- Script must be read-only for `plans/active/` and `docs/fix_plan.md`; do **not** rename or delete plan directories yet.
- Keep CLI defaults so future loops can rerun the tool without hunting for flags; avoid hard-coding timestamps inside the script.
- When parsing `implementation.md`, guard against files that only contain placeholders (e.g., “archived stub”) so the script doesn’t crash on empty content.
- Do not add or remove fix-plan initiatives beyond the appendix update in this loop—classification/archival happens in Phase B after inventory lands.
- Preserve the artifacts created earlier today (2025-12-05T083500Z); the new script should supersede them, not delete them.

## If Blocked

- If any plan directory is unreadable or lacks permissions, log the failure inside `inventory_report.md`, keep the script output for the remaining directories, and annotate `docs/fix_plan.md` appendix with a “blocked directories” bullet referencing the error.
- If Python dependencies are missing, halt immediately (Environment Freeze) and record the stack trace in the artifact folder; let Galph decide on a remediation path before retrying.

## Findings Applied

No relevant findings in the knowledge base (docs/findings.md search for “plan” / “portfolio” surfaced only geometry/physics items).

## Pointers

- `plans/active/PORTFOLIO-STATUS/implementation.md:1` — Goals, exit criteria, and Phase A checklist for this initiative.
- `docs/fix_plan.md:24` — Tier 0 entry describing PORTFOLIO-STATUS scope and expected artifacts.

## Next Up

1. Once the appendix exists, classify the 38 missing initiatives into “archived-ready” vs “needs new fix-plan entry” (Phase B1/B3).  
2. For directories lacking `implementation.md`, decide whether to archive them under `archive/plans/` or draft fresh plans before reintroducing them to the fix plan.
