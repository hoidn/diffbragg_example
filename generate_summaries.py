#!/usr/bin/env python3
"""
Generate missing markdown summaries for agent iterations.

Scans raw logs, identifies missing summaries, and generates them in parallel.
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import json

BRANCH_PREFIX = "integration"
COUNT = 30
ROLES = ["galph", "ralph"]
MAX_CONCURRENCY = 8

def find_iterations(branch_prefix, roles):
    """Find all iteration numbers from raw logs."""
    iterations = set()

    for role in roles:
        log_dir = Path(f"logs/{branch_prefix}/{role}")
        if not log_dir.exists():
            continue

        for log_file in log_dir.glob("iter-*.log"):
            match = re.match(r"iter-(\d+)_", log_file.name)
            if match:
                iterations.add(int(match.group(1)))

    return sorted(iterations)

def find_existing_summaries(branch_prefix, role):
    """Find existing summaries for a role."""
    existing = set()
    summary_dir = Path(f"logs/{branch_prefix}/{role}-summaries")

    if not summary_dir.exists():
        return existing

    for summary_file in summary_dir.glob("iter-*-summary.md"):
        match = re.match(r"iter-(\d+)_", summary_file.name)
        if match:
            existing.add(int(match.group(1)))

    return existing

def find_missing_summaries(branch_prefix, roles, count):
    """Identify missing summaries for the last N iterations."""
    all_iterations = find_iterations(branch_prefix, roles)
    recent_iterations = all_iterations[-count:] if len(all_iterations) > count else all_iterations

    missing = []
    for role in roles:
        existing = find_existing_summaries(branch_prefix, role)
        for iteration in recent_iterations:
            if iteration not in existing:
                missing.append((role, iteration))

    return missing, recent_iterations

def get_log_file_for_iteration(branch_prefix, role, iteration):
    """Find the most recent log file for a given iteration."""
    log_dir = Path(f"logs/{branch_prefix}/{role}")
    pattern = f"iter-{iteration:05d}_*.log"

    matching_files = sorted(log_dir.glob(pattern))
    if matching_files:
        return matching_files[-1]  # Return most recent
    return None

def main():
    """Main entry point."""
    print(f"Scanning logs for branch: {BRANCH_PREFIX}")
    print(f"Looking for last {COUNT} iterations")
    print(f"Roles: {', '.join(ROLES)}")
    print()

    missing, recent_iterations = find_missing_summaries(BRANCH_PREFIX, ROLES, COUNT)

    print(f"Found {len(recent_iterations)} iterations total")
    print(f"Recent iterations: {min(recent_iterations)} to {max(recent_iterations)}")
    print()

    # Group by role for reporting
    by_role = defaultdict(list)
    for role, iteration in missing:
        by_role[role].append(iteration)

    print("Missing summaries by role:")
    for role in ROLES:
        missing_iters = sorted(by_role[role])
        print(f"  {role}: {len(missing_iters)} missing")
        if missing_iters:
            print(f"    Iterations: {missing_iters[:10]}" +
                  (f"... +{len(missing_iters)-10} more" if len(missing_iters) > 10 else ""))
    print()

    # Output JSON for processing
    output = {
        "branch_prefix": BRANCH_PREFIX,
        "missing": [{"role": role, "iteration": iter,
                     "log_file": str(get_log_file_for_iteration(BRANCH_PREFIX, role, iter))}
                    for role, iter in missing],
        "total_missing": len(missing),
        "recent_iterations": recent_iterations
    }

    with open("missing_summaries.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"Total missing summaries: {len(missing)}")
    print(f"Saved details to missing_summaries.json")

    return 0

if __name__ == "__main__":
    sys.exit(main())
