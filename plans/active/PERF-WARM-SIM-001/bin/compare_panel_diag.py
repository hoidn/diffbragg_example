#!/usr/bin/env python
"""
Compare Stage A vs Stage C panel-loss diagnostics.

PERF-WARM-SIM-001 Phase D.4: Pinpoint where Stage C diverges from Stage A by
comparing per-panel chi², mask, sigma, and target checksums.

Usage:
    python compare_panel_diag.py \
      --stage-a-json path/to/stage_a_panel_diag.json \
      --stage-c-json path/to/stage_c_panel_diag.json \
      --label <detector_size> \
      --out-dir path/to/output/
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any


def load_panel_diag(path: Path) -> Dict[str, Any]:
    """Load panel diagnostics JSON."""
    with open(path, 'r') as f:
        return json.load(f)


def align_panels(stage_a_panels: List[Dict], stage_c_panels: List[Dict]) -> List[Dict]:
    """Align Stage A and Stage C panel diagnostics by panel_id."""
    stage_a_by_id = {p['panel_id']: p for p in stage_a_panels}
    stage_c_by_id = {p['panel_id']: p for p in stage_c_panels}

    aligned = []
    all_panel_ids = sorted(set(stage_a_by_id.keys()) | set(stage_c_by_id.keys()))

    for panel_id in all_panel_ids:
        pa = stage_a_by_id.get(panel_id)
        pc = stage_c_by_id.get(panel_id)

        if pa is None or pc is None:
            print(f"Warning: panel_id={panel_id} missing from {'Stage C' if pa else 'Stage A'}", file=sys.stderr)
            continue

        chi2_a = pa['chi_squared']
        chi2_c = pc['chi_squared']
        delta_abs = chi2_c - chi2_a
        delta_rel = (delta_abs / chi2_a) * 100.0 if chi2_a != 0 else 0.0

        aligned.append({
            'panel_id': panel_id,
            'stage_a_chi2': chi2_a,
            'stage_c_chi2': chi2_c,
            'delta_abs': delta_abs,
            'delta_rel_pct': delta_rel,
            'stage_a_masked_pixels': pa['masked_pixels'],
            'stage_c_masked_pixels': pc['masked_pixels'],
            'stage_a_mask_true_count': pa['mask_true_count'],
            'stage_c_mask_true_count': pc['mask_true_count'],
            'stage_a_target_sum': pa['target_sum'],
            'stage_c_target_sum': pc['target_sum'],
            'stage_a_sigma_sum': pa['sigma_sum'],
            'stage_c_sigma_sum': pc['sigma_sum'],
        })

    return aligned


def compute_summary(aligned: List[Dict]) -> Dict[str, Any]:
    """Compute summary statistics."""
    if not aligned:
        return {
            'n_panels': 0,
            'total_chi2_delta_abs': 0.0,
            'mean_chi2_delta_rel_pct': 0.0,
            'max_chi2_delta_rel_pct': 0.0,
            'min_chi2_delta_rel_pct': 0.0,
        }

    deltas_rel = [p['delta_rel_pct'] for p in aligned]
    deltas_abs = [p['delta_abs'] for p in aligned]

    return {
        'n_panels': len(aligned),
        'total_chi2_delta_abs': sum(deltas_abs),
        'mean_chi2_delta_rel_pct': sum(deltas_rel) / len(deltas_rel),
        'max_chi2_delta_rel_pct': max(deltas_rel),
        'min_chi2_delta_rel_pct': min(deltas_rel),
        'panels_with_delta': aligned,
    }


def format_markdown_summary(summary: Dict[str, Any], label: str) -> str:
    """Format summary as Markdown."""
    lines = [
        f"## Panel Diagnostics Comparison ({label})",
        "",
        f"- **Panels compared**: {summary['n_panels']}",
        f"- **Total χ² delta (abs)**: {summary['total_chi2_delta_abs']:.2f}",
        f"- **Mean χ² delta (rel)**: {summary['mean_chi2_delta_rel_pct']:.4f}%",
        f"- **Max χ² delta (rel)**: {summary['max_chi2_delta_rel_pct']:.4f}%",
        f"- **Min χ² delta (rel)**: {summary['min_chi2_delta_rel_pct']:.4f}%",
        "",
        "### Top 10 Divergent Panels (by relative δχ²)",
        "",
        "| Panel ID | Stage A χ² | Stage C χ² | Δ (abs) | Δ (rel %) |",
        "|----------|------------|------------|---------|-----------|",
    ]

    # Sort by absolute relative delta descending
    panels = summary['panels_with_delta']
    top_panels = sorted(panels, key=lambda p: abs(p['delta_rel_pct']), reverse=True)[:10]

    for p in top_panels:
        lines.append(
            f"| {p['panel_id']:8d} | {p['stage_a_chi2']:12.2f} | {p['stage_c_chi2']:12.2f} | "
            f"{p['delta_abs']:+9.2f} | {p['delta_rel_pct']:+9.4f} |"
        )

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Compare Stage A vs Stage C panel diagnostics")
    parser.add_argument('--stage-a-json', required=True, help='Path to stage_a_panel_diag.json')
    parser.add_argument('--stage-c-json', required=True, help='Path to stage_c_panel_diag.json')
    parser.add_argument('--label', default='', help='Label for this comparison (e.g., "small" or "full")')
    parser.add_argument('--out-dir', required=True, help='Output directory for JSON and Markdown')
    args = parser.parse_args()

    stage_a_path = Path(args.stage_a_json)
    stage_c_path = Path(args.stage_c_json)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not stage_a_path.exists():
        print(f"Error: {stage_a_path} does not exist", file=sys.stderr)
        sys.exit(1)
    if not stage_c_path.exists():
        print(f"Error: {stage_c_path} does not exist", file=sys.stderr)
        sys.exit(1)

    stage_a_data = load_panel_diag(stage_a_path)
    stage_c_data = load_panel_diag(stage_c_path)

    aligned = align_panels(stage_a_data['panels'], stage_c_data['panels'])
    summary = compute_summary(aligned)

    # Write JSON output
    json_filename = f"panel_diag_compare_{args.label}.json" if args.label else "panel_diag_compare.json"
    json_path = out_dir / json_filename
    with open(json_path, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"JSON summary written to {json_path}")

    # Print Markdown summary
    markdown = format_markdown_summary(summary, args.label)
    print("\n" + markdown)

    # Optionally write Markdown to file
    md_filename = f"panel_diag_compare_{args.label}.md" if args.label else "panel_diag_compare.md"
    md_path = out_dir / md_filename
    with open(md_path, 'w') as f:
        f.write(markdown)
    print(f"\nMarkdown summary written to {md_path}")


if __name__ == '__main__':
    main()
