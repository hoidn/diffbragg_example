#!/usr/bin/env python3
"""Plan Directory Inventory — Tier-2 Portfolio Audit Script

Generates authoritative inventory of plan directories under `plans/active/`,
cross-referencing with `docs/fix_plan.md` to detect drift and untracked initiatives.

Usage:
    python plan_inventory.py --out-dir <path>
    python plan_inventory.py --plans-root plans/active --fix-plan docs/fix_plan.md --out-dir <path>

Outputs:
    - inventory.json: Machine-readable list of plan metadata
    - inventory_missing.md: Human-readable summary of untracked initiatives

Per CLAUDE.md scriptization rules:
    - Idempotent and safe to rerun
    - Read-only for input sources (plans/active/, docs/fix_plan.md)
    - CLI defaults enable zero-friction reruns
    - No hardcoded timestamps or paths

References:
    - plans/active/PORTFOLIO-STATUS/implementation.md Phase A requirements
    - input.md Phase A1/A2 specification
"""

import argparse
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional


@dataclass
class PlanEntry:
    """Metadata for a single plan directory."""
    id: str
    in_fix_plan: bool
    has_implementation: bool
    last_report: Optional[str]
    status_hint: Optional[str]


def parse_fix_plan_ids(fix_plan_path: Path) -> set:
    """Extract plan IDs referenced in fix_plan.md.

    Looks for patterns like [PLAN-ID-123] in markdown headers and lists.
    """
    if not fix_plan_path.exists():
        return set()

    content = fix_plan_path.read_text()
    # Match [UPPERCASE-WORDS-NUMBERS] patterns
    pattern = r'\[([A-Z][A-Z0-9\-]+)\]'
    matches = re.findall(pattern, content)
    return set(matches)


def extract_status_hint(implementation_path: Path) -> Optional[str]:
    """Peek at implementation.md to derive status hint.

    Looks for Status: or Purpose: lines near the top of the file.
    Guards against empty/placeholder-only files.
    """
    if not implementation_path.exists():
        return None

    try:
        content = implementation_path.read_text()
        lines = [line.strip() for line in content.split('\n') if line.strip()]

        # Guard against placeholder-only files
        if not lines or len(content) < 50:
            return "placeholder_stub"

        # Look for Status: or Purpose: in first 20 non-empty lines
        for line in lines[:20]:
            if line.startswith('**Status:**'):
                # Extract value after Status:
                parts = line.split('**Status:**', 1)
                if len(parts) > 1:
                    return parts[1].strip()
            elif line.startswith('Status:'):
                parts = line.split('Status:', 1)
                if len(parts) > 1:
                    return parts[1].strip()
    except Exception:
        return "read_error"

    return None


def find_last_report(plan_dir: Path) -> Optional[str]:
    """Find the most recent report timestamp in plan_dir/reports/.

    Returns ISO8601 timestamp string or None if no reports exist.
    """
    reports_dir = plan_dir / "reports"
    if not reports_dir.exists():
        return None

    # Collect all timestamp-named subdirectories
    timestamps = []
    for item in reports_dir.iterdir():
        if item.is_dir():
            # Look for ISO8601-like patterns (YYYY-MM-DDTHH:MM:SSZ or similar)
            if re.match(r'\d{4}-\d{2}-\d{2}T\d{6}Z?', item.name):
                timestamps.append(item.name)

    if not timestamps:
        return None

    # Return the lexicographically latest (ISO8601 sorts correctly)
    return sorted(timestamps)[-1]


def inventory_plans(plans_root: Path, fix_plan_ids: set) -> List[PlanEntry]:
    """Scan plans_root and build inventory of all plan directories."""
    entries = []

    if not plans_root.exists():
        return entries

    for plan_dir in sorted(plans_root.iterdir()):
        if not plan_dir.is_dir():
            continue

        # Skip hidden directories and common non-plan subdirs
        if plan_dir.name.startswith('.') or plan_dir.name in ['__pycache__', 'templates']:
            continue

        plan_id = plan_dir.name
        implementation_path = plan_dir / "implementation.md"

        entry = PlanEntry(
            id=plan_id,
            in_fix_plan=plan_id in fix_plan_ids,
            has_implementation=implementation_path.exists(),
            last_report=find_last_report(plan_dir),
            status_hint=extract_status_hint(implementation_path) if implementation_path.exists() else None
        )
        entries.append(entry)

    return entries


def write_json_output(entries: List[PlanEntry], out_path: Path):
    """Write machine-readable inventory.json."""
    data = [asdict(entry) for entry in entries]
    out_path.write_text(json.dumps(data, indent=2))


def write_missing_md(entries: List[PlanEntry], out_path: Path):
    """Write human-readable inventory_missing.md summarizing untracked initiatives."""
    missing = [e for e in entries if not e.in_fix_plan]

    lines = [
        "# Untracked Plan Directories",
        "",
        f"**Count:** {len(missing)} initiatives not referenced in `docs/fix_plan.md`",
        "",
        "| Plan ID | Has Implementation | Last Report | Status Hint |",
        "|---------|-------------------|-------------|-------------|"
    ]

    for entry in missing:
        impl_status = "✓" if entry.has_implementation else "✗"
        last_report = entry.last_report if entry.last_report else "none"
        status_hint = entry.status_hint if entry.status_hint else "unknown"
        lines.append(f"| {entry.id} | {impl_status} | {last_report} | {status_hint} |")

    lines.append("")
    lines.append("## Remediation Guidance")
    lines.append("")
    lines.append("- **Has Implementation + Recent Reports:** Likely active; add to fix_plan.md")
    lines.append("- **No Implementation:** Consider archiving or removing")
    lines.append("- **Old Last Report (> 30 days):** Review for archival")
    lines.append("- **placeholder_stub Status:** Archive candidate")
    lines.append("")

    out_path.write_text('\n'.join(lines))


def main():
    parser = argparse.ArgumentParser(
        description="Inventory plan directories and cross-check with fix_plan.md"
    )
    parser.add_argument(
        '--plans-root',
        type=Path,
        default=Path('plans/active'),
        help='Root directory containing plan subdirectories (default: plans/active)'
    )
    parser.add_argument(
        '--fix-plan',
        type=Path,
        default=Path('docs/fix_plan.md'),
        help='Path to fix plan ledger (default: docs/fix_plan.md)'
    )
    parser.add_argument(
        '--out-dir',
        type=Path,
        required=True,
        help='Output directory for inventory.json and inventory_missing.md'
    )

    args = parser.parse_args()

    # Ensure output directory exists
    args.out_dir.mkdir(parents=True, exist_ok=True)

    # Parse fix plan IDs
    fix_plan_ids = parse_fix_plan_ids(args.fix_plan)

    # Build inventory
    entries = inventory_plans(args.plans_root, fix_plan_ids)

    # Write outputs
    json_path = args.out_dir / "inventory.json"
    missing_path = args.out_dir / "inventory_missing.md"

    write_json_output(entries, json_path)
    write_missing_md(entries, missing_path)

    print(f"Inventory complete:")
    print(f"  Total plans: {len(entries)}")
    print(f"  In fix_plan.md: {sum(1 for e in entries if e.in_fix_plan)}")
    print(f"  Missing from fix_plan.md: {sum(1 for e in entries if not e.in_fix_plan)}")
    print(f"  Output written to: {args.out_dir}")


if __name__ == '__main__':
    main()
