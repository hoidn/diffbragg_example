#!/usr/bin/env python3
"""Phase B.1 consumer mapping: find which fix-plan initiatives reference each Active finding."""

import json
import re
import subprocess
from pathlib import Path
from collections import defaultdict

REPO_ROOT = Path(__file__).resolve().parents[5]
FINDINGS_MD = REPO_ROOT / "docs/findings.md"
FIX_PLAN_MD = REPO_ROOT / "docs/fix_plan.md"
INVENTORY_JSON = REPO_ROOT / "plans/active/FINDINGS-LEDGER-002/reports/2025-12-03T120250Z/findings_inventory.json"
OUTPUT_JSON = Path(__file__).parent / "consumer_map.json"

def load_active_findings():
    """Load Active findings from the inventory JSON."""
    with open(INVENTORY_JSON) as f:
        inventory = json.load(f)
    return [entry for entry in inventory if entry["status"] == "Active"]

def search_fix_plan_for_finding(finding_id):
    """Grep fix_plan.md for references to the finding ID."""
    try:
        result = subprocess.run(
            ["grep", "-n", finding_id, str(FIX_PLAN_MD)],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip().split("\n")
        return []
    except subprocess.TimeoutExpired:
        return []

def extract_initiative_from_line(line):
    """Extract initiative ID from a fix_plan.md line."""
    # Pattern: [INITIATIVE-ID]
    match = re.search(r'\[([A-Z\-0-9]+)\]', line)
    if match:
        return match.group(1)
    return None

def main():
    active_findings = load_active_findings()
    print(f"Loaded {len(active_findings)} Active findings from inventory.")

    consumer_map = {}

    for finding in active_findings:
        finding_id = finding["id"]
        print(f"Searching for {finding_id}...", end=" ")

        matches = search_fix_plan_for_finding(finding_id)
        consumers = []

        for match in matches:
            # Extract line number and content
            if ":" in match:
                line_num, content = match.split(":", 1)
                initiative = extract_initiative_from_line(content)
                if initiative and initiative != finding_id:
                    consumers.append({
                        "initiative": initiative,
                        "line": int(line_num),
                        "context": content.strip()[:100]
                    })

        # Deduplicate by initiative
        unique_consumers = []
        seen_initiatives = set()
        for c in consumers:
            if c["initiative"] not in seen_initiatives:
                unique_consumers.append(c)
                seen_initiatives.add(c["initiative"])

        consumer_map[finding_id] = {
            "summary": finding["summary"][:80] + "..." if len(finding["summary"]) > 80 else finding["summary"],
            "tags": finding["tags"],
            "consumers": unique_consumers,
            "consumer_count": len(unique_consumers)
        }

        print(f"{len(unique_consumers)} consumer(s)")

    # Write output
    with open(OUTPUT_JSON, "w") as f:
        json.dump(consumer_map, f, indent=2)

    print(f"\nConsumer map written to {OUTPUT_JSON}")

    # Stats
    no_consumer = [fid for fid, data in consumer_map.items() if data["consumer_count"] == 0]
    has_consumer = [fid for fid, data in consumer_map.items() if data["consumer_count"] > 0]

    print(f"\nStats:")
    print(f"  Active findings: {len(active_findings)}")
    print(f"  With consumers: {len(has_consumer)}")
    print(f"  No consumers: {len(no_consumer)}")

    if no_consumer:
        print(f"\nOrphaned findings (no fix-plan consumers):")
        for fid in sorted(no_consumer):
            print(f"  - {fid}")

if __name__ == "__main__":
    main()
