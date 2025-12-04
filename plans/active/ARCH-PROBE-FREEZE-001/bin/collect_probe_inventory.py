#!/usr/bin/env python3
"""
Thin-wrapper CLI to catalog plan-local probe scripts.

Usage:
    python plans/active/ARCH-PROBE-FREEZE-001/bin/collect_probe_inventory.py \
        --out plans/active/ARCH-PROBE-FREEZE-001/reports/<timestamp>/probe_inventory_raw.json

Complies with diagnostic_script_policy: only pathlib/os/json/re (read-only).
No simulator/mapping/physics imports.
"""
import argparse
import json
import re
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Collect plan-local probe script inventory")
    parser.add_argument("--out", required=True, help="Output JSON path")
    args = parser.parse_args()

    # Script is at plans/active/ARCH-PROBE-FREEZE-001/bin/collect_probe_inventory.py
    # parents[0] = bin, parents[1] = ARCH-PROBE-FREEZE-001, parents[2] = active, parents[3] = plans, parents[4] = repo_root
    repo_root = Path(__file__).resolve().parents[4]
    plans_root = repo_root / "plans" / "active"

    scripts = []

    # Walk plans/active/**/bin/*.{py,sh}
    for script_path in plans_root.glob("*/bin/*"):
        if not script_path.is_file():
            continue
        if script_path.suffix not in {".py", ".sh"}:
            continue

        # Extract initiative_id from path
        relative = script_path.relative_to(plans_root)
        initiative_id = relative.parts[0] if relative.parts else "unknown"

        # Read file content
        try:
            content = script_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            # Record error but continue
            scripts.append({
                "script_path": str(script_path.relative_to(repo_root)),
                "initiative_id": initiative_id,
                "language": script_path.suffix[1:],
                "error": f"Failed to read: {e}",
                "imports_torch": None,
                "calls_owner_api": None,
                "lines_of_code": None,
            })
            continue

        # Count lines (excluding blanks/comments)
        lines = content.splitlines()
        loc = sum(1 for ln in lines if ln.strip() and not ln.strip().startswith("#"))

        # Check for torch import
        imports_torch = bool(re.search(r'^\s*import\s+torch\b', content, re.MULTILINE) or
                             re.search(r'^\s*from\s+torch\b', content, re.MULTILINE))

        # Check for common owner API calls (dbex, nanobrag_torch)
        calls_owner_api = bool(re.search(r'\bdbex\.', content) or
                               re.search(r'\bnanobrag_torch\.', content) or
                               re.search(r'\bfrom\s+dbex\b', content) or
                               re.search(r'\bfrom\s+nanobrag_torch\b', content))

        scripts.append({
            "script_path": str(script_path.relative_to(repo_root)),
            "initiative_id": initiative_id,
            "language": script_path.suffix[1:],
            "imports_torch": imports_torch,
            "calls_owner_api": calls_owner_api,
            "lines_of_code": loc,
        })

    # Sort by initiative then path
    scripts.sort(key=lambda x: (x["initiative_id"], x["script_path"]))

    # Write output
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w") as f:
        json.dump({"scripts": scripts, "total_count": len(scripts)}, f, indent=2)

    print(f"Cataloged {len(scripts)} scripts -> {out_path}")


if __name__ == "__main__":
    main()
