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
from typing import List, Optional, Tuple


DEFAULT_ROLLUP_CONFIG = Path('plans/active/PORTFOLIO-STATUS/rollups.json')


@dataclass
class PlanEntry:
    """Metadata for a single plan directory."""
    id: str
    in_fix_plan: bool
    has_implementation: bool
    last_report: Optional[str]
    status_hint: Optional[str]
    bucket: Optional[str] = None
    rollup_coverage: List[str] = None

    def __post_init__(self):
        """Initialize mutable defaults."""
        if self.rollup_coverage is None:
            self.rollup_coverage = []


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


def apply_rollup_coverage(entries: List[PlanEntry], rollup_config: dict, fix_plan_ids: set) -> None:
    """Apply roll-up coverage to plan entries.

    For each plan directory that appears in a roll-up's member list, record that
    roll-up ID in the entry's rollup_coverage field IF the roll-up ID itself
    exists in fix_plan_ids (meaning the roll-up section is present in the ledger).

    Modifies entries in place.

    Args:
        entries: List of PlanEntry objects to update
        rollup_config: Dict mapping roll-up IDs to lists of member plan IDs
        fix_plan_ids: Set of IDs found in docs/fix_plan.md
    """
    # Build reverse mapping from member plan ID to roll-up IDs that cover it
    member_to_rollups = {}
    for rollup_id, members in rollup_config.items():
        # Only count roll-ups that already have sections in fix_plan.md
        if rollup_id not in fix_plan_ids:
            continue
        for member_id in members:
            if member_id not in member_to_rollups:
                member_to_rollups[member_id] = []
            member_to_rollups[member_id].append(rollup_id)

    # Apply coverage to matching entries
    for entry in entries:
        if entry.id in member_to_rollups:
            entry.rollup_coverage = member_to_rollups[entry.id]


def compute_bucket(entry: PlanEntry) -> str:
    """Classify plan entry into bucket per classification.md rules.

    Buckets:
    - tracked_via_rollup: has rollup_coverage from ledger roll-up sections
    - active_missing: has_implementation=True, in_fix_plan=False, no rollup coverage
    - archive_ready: status_hint mentions "archive" or "duplicate"
    - missing_plan: has_implementation=False
    """
    if not entry.has_implementation:
        return "missing_plan"

    # Check for archive hints in status
    if entry.status_hint and ("archive" in entry.status_hint.lower() or
                              "duplicate" in entry.status_hint.lower() or
                              "superseded" in entry.status_hint.lower()):
        return "archive_ready"

    # Roll-up coverage counts as tracked
    if entry.rollup_coverage:
        return "tracked_via_rollup"

    if entry.has_implementation and not entry.in_fix_plan:
        return "active_missing"

    # Default for plans already in fix_plan or other edge cases
    return "tracked"


def load_rollup_config(config_path: Path) -> dict:
    """Load roll-up configuration from JSON file.

    Expected format: {"ROLLUP-ID": ["MEMBER-1", "MEMBER-2", ...], ...}
    """
    if not config_path.exists():
        return {}

    try:
        return json.loads(config_path.read_text())
    except Exception:
        return {}


def resolve_rollup_config(user_supplied: Optional[Path]) -> Tuple[Path, bool]:
    """Resolve the rollup config path, enforcing the automation guard.

    Returns a tuple of (path, auto_loaded_flag). Raises FileNotFoundError if
    neither a user-supplied path nor the default guard path exists.
    """
    if user_supplied:
        expanded = user_supplied.expanduser()
        if not expanded.exists():
            raise FileNotFoundError(
                f"Rollup config not found at {expanded}. "
                "Pass a valid path via --rollup-config."
            )
        return expanded, False

    default_path = DEFAULT_ROLLUP_CONFIG
    if default_path.exists():
        return default_path, True

    raise FileNotFoundError(
        f"No rollup config provided and default {default_path} not found. "
        "Rerun plan_inventory.py with --rollup-config <path> to satisfy the automation guard."
    )


def inventory_plans(plans_root: Path, fix_plan_ids: set) -> List[PlanEntry]:
    """Scan plans_root and build inventory of all plan directories.

    Note: Bucket classification is deferred until after apply_rollup_coverage runs,
    since rollup membership affects bucket assignment.
    """
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
        # Bucket will be computed after apply_rollup_coverage in main()
        entries.append(entry)

    return entries


def write_json_output(entries: List[PlanEntry], out_path: Path):
    """Write machine-readable inventory.json."""
    data = [asdict(entry) for entry in entries]
    out_path.write_text(json.dumps(data, indent=2))


def write_missing_md(entries: List[PlanEntry], out_path: Path):
    """Write human-readable inventory_missing.md summarizing untracked initiatives.

    Excludes plans that are covered via roll-up sections, as they are effectively
    tracked even if their individual IDs don't appear in the ledger.
    """
    # Filter out plans with rollup coverage
    missing = [e for e in entries if not e.in_fix_plan and not e.rollup_coverage]

    lines = [
        "# Untracked Plan Directories",
        "",
        f"**Count:** {len(missing)} initiatives not referenced in `docs/fix_plan.md` or roll-up sections",
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
    lines.append("**Note:** Plans covered via roll-up sections are excluded from this report.")
    lines.append("")

    out_path.write_text('\n'.join(lines))


def write_rollup_report(rollup_config: dict, entries: List[PlanEntry], fix_plan_ids: set, out_path: Path):
    """Write rollup_report.md summarizing roll-up coverage.

    For each roll-up ID:
    - List member plan directories
    - Report last-report timestamp span (earliest to latest)
    - Note whether fix_plan.md already has a section for this roll-up
    """
    lines = [
        "# Roll-Up Coverage Report",
        "",
        "Summary of plan directory roll-ups and their fix_plan.md coverage status.",
        ""
    ]

    # Create lookup from plan_id to entry
    entry_map = {e.id: e for e in entries}

    for rollup_id, members in sorted(rollup_config.items()):
        lines.append(f"## {rollup_id}")
        lines.append("")
        lines.append(f"**Member Plans:** {', '.join(members)}")
        lines.append("")

        # Collect report timestamps from member plans
        timestamps = []
        missing_members = []
        for member_id in members:
            if member_id in entry_map:
                entry = entry_map[member_id]
                if entry.last_report:
                    timestamps.append(entry.last_report)
            else:
                missing_members.append(member_id)

        if timestamps:
            timestamps_sorted = sorted(timestamps)
            earliest = timestamps_sorted[0]
            latest = timestamps_sorted[-1]
            if earliest == latest:
                lines.append(f"**Last Report Span:** {latest}")
            else:
                lines.append(f"**Last Report Span:** {earliest} to {latest}")
        else:
            lines.append("**Last Report Span:** No reports found")

        lines.append("")

        # Check if fix_plan.md has a section for this roll-up
        has_section = rollup_id in fix_plan_ids
        lines.append(f"**Fix-Plan Coverage:** {'✓ Section exists' if has_section else '✗ Missing section'}")
        lines.append("")

        if missing_members:
            lines.append(f"**Missing Member Directories:** {', '.join(missing_members)}")
            lines.append("")

        lines.append("---")
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
        '--rollup-config',
        type=Path,
        default=None,
        help='Path to rollup config JSON file. Defaults to plans/active/PORTFOLIO-STATUS/rollups.json when omitted.'
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

    # Resolve rollup config path (guardrails)
    try:
        rollup_config_path, auto_loaded = resolve_rollup_config(args.rollup_config)
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc

    rollup_config = load_rollup_config(rollup_config_path)
    if not rollup_config:
        raise SystemExit(
            f"Rollup config at {rollup_config_path} is empty or invalid. "
            "Repair the JSON file before rerunning plan_inventory.py."
        )

    # Build inventory
    entries = inventory_plans(args.plans_root, fix_plan_ids)

    # Apply rollup coverage and recompute buckets
    apply_rollup_coverage(entries, rollup_config, fix_plan_ids)
    for entry in entries:
        entry.bucket = compute_bucket(entry)

    # Write outputs
    json_path = args.out_dir / "inventory.json"
    missing_path = args.out_dir / "inventory_missing.md"

    write_json_output(entries, json_path)
    write_missing_md(entries, missing_path)

    # Write rollup report
    rollup_path = args.out_dir / "rollup_report.md"
    write_rollup_report(rollup_config, entries, fix_plan_ids, rollup_path)

    # Compute bucket statistics for console output
    rollup_covered = sum(1 for e in entries if e.rollup_coverage)
    active_missing = sum(1 for e in entries if e.bucket == "active_missing")

    print(f"Inventory complete:")
    print(f"  Total plans: {len(entries)}")
    print(f"  In fix_plan.md: {sum(1 for e in entries if e.in_fix_plan)}")
    print(f"  Covered via rollups: {rollup_covered}")
    print(f"  Active missing: {active_missing}")
    print(f"  Roll-ups configured: {len(rollup_config)}")
    if auto_loaded:
        print(f"  [guard] Auto-loaded rollup config from {rollup_config_path}")
    else:
        print(f"  [guard] Using rollup config from {rollup_config_path}")
    print(f"  Output written to: {args.out_dir}")


if __name__ == '__main__':
    main()
