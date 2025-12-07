#!/usr/bin/env python3
"""
Add consumer metadata to findings.md table
Phase B.2 of FINDINGS-LEDGER-002
"""

import re
import sys

# Mapping of findings to their consumers from input.md lines 69-81
CONSUMER_MAP = {
    # TORCH-REFINE-CLEANUP-001
    'REFINE-001': ['TORCH-REFINE-CLEANUP-001', 'ARCH-REFACTOR-001'],  # dual consumers
    'REFINE-002': ['TORCH-REFINE-CLEANUP-001'],
    'REFINE-003': ['TORCH-REFINE-CLEANUP-001'],
    'REFINE-006': ['TORCH-REFINE-CLEANUP-001'],
    'REFINE-009': ['TORCH-REFINE-CLEANUP-001'],
    'REFINE-010': ['TORCH-REFINE-CLEANUP-001'],
    'GRADIENT-001': ['TORCH-REFINE-CLEANUP-001'],
    'REFINE-016': ['TORCH-REFINE-CLEANUP-001'],

    # MAP-SCALE-SYNC-001
    'SCALE-001': ['MAP-SCALE-SYNC-001'],
    'SCALE-002': ['MAP-SCALE-SYNC-001'],
    'SCALE-003': ['MAP-SCALE-SYNC-001'],
    'SCALE-004': ['MAP-SCALE-SYNC-001'],
    'SCALE-005': ['MAP-SCALE-SYNC-001'],
    'SCALE-006': ['MAP-SCALE-SYNC-001'],
    'SCALE-007': ['MAP-SCALE-SYNC-001'],

    # PERF-WARM-SIM-001
    **{f'PERF-WARM-{i:03d}': ['PERF-WARM-SIM-001'] for i in range(1, 14)},
    'REFINE-007': ['PERF-WARM-SIM-001'],
    'REFINE-011': ['PERF-WARM-SIM-001'],
    'REFINE-012': ['PERF-WARM-SIM-001'],

    # TORCH-GEOMETRY-SYNC-001
    'GEOMETRY-001': ['TORCH-GEOMETRY-SYNC-001'],
    'GEOMETRY-002': ['TORCH-GEOMETRY-SYNC-001'],
    'GEOMETRY-003': ['TORCH-GEOMETRY-SYNC-001'],
    'GEOMETRY-004': ['TORCH-GEOMETRY-SYNC-001'],
    'CONFIG-001': ['TORCH-GEOMETRY-SYNC-001'],
    'DXTBX-001': ['TORCH-GEOMETRY-SYNC-001'],
    'HKL-ORIENT-001': ['TORCH-GEOMETRY-SYNC-001'],
    'CONVERGENCE-001': ['TORCH-GEOMETRY-SYNC-001'],

    # PHYSICS-LOSS-CONSISTENCY
    'PHYSICS-LOSS-001': ['PHYSICS-LOSS-CONSISTENCY'],
    'PHYSICS-LOSS-002': ['PHYSICS-LOSS-CONSISTENCY'],
    'PHYSICS-LOSS-003': ['PHYSICS-LOSS-CONSISTENCY'],
    'PHYSICS-LOSS-004': ['PHYSICS-LOSS-CONSISTENCY'],
    'PHYSICS-LOSS-005': ['PHYSICS-LOSS-CONSISTENCY'],

    # ARCH-REFACTOR-001 (additional, REFINE-001 already listed above)
    'ARCH-ENGINE-002': ['ARCH-REFACTOR-001'],
    'ARCH-ENGINE-003': ['ARCH-REFACTOR-001'],
    'ARCH-FACTORY-001': ['ARCH-REFACTOR-001'],
    'ARCH-FACTORY-003': ['ARCH-REFACTOR-001'],

    # ARCH-STAGE-CONTEXT-CONSOLIDATION
    'ARCH-STAGE-CTX-001': ['ARCH-STAGE-CONTEXT-CONSOLIDATION'],
    'ARCH-STAGE-CTX-002': ['ARCH-STAGE-CONTEXT-CONSOLIDATION'],

    # DB-AT-SUITE-CARE-001
    'TESTING-003': ['DB-AT-SUITE-CARE-001'],
    'RUNTIME-001': ['DB-AT-SUITE-CARE-001'],
    'DIAGNOSTICS-001': ['DB-AT-SUITE-CARE-001'],
    'MASKING-001': ['DB-AT-SUITE-CARE-001'],

    # FORWARD-EQUIV-COVERAGE-001
    'PARITY-001': ['FORWARD-EQUIV-COVERAGE-001'],
    'MANIFEST-001': ['FORWARD-EQUIV-COVERAGE-001'],

    # ARCH-IMPL-CONFORMANCE-001 (already linked per input.md)
    'CONFORMANCE-001': ['ARCH-IMPL-CONFORMANCE-001'],

    # TORCH-API-ALIGN-001 (retrospective)
    'MODEL-001': ['TORCH-API-ALIGN-001'],
}

def process_findings_file(path):
    """Add consumer metadata to findings.md table rows"""
    with open(path, 'r') as f:
        lines = f.readlines()

    modified = []
    updated_count = 0

    # Pattern to match table rows: | ID | Date | Tags | Summary | Source | Status |
    row_pattern = re.compile(r'^\| ([A-Z0-9-]+) \|')

    for line in lines:
        match = row_pattern.match(line)
        if match:
            finding_id = match.group(1)
            if finding_id in CONSUMER_MAP and '**Consumers:**' not in line:
                # Split the line into columns
                parts = line.rstrip('|\n').split('|')
                if len(parts) >= 6:  # ID, Date, Tags, Summary, Source, Status + leading/trailing |
                    # Summary is at index 4 (0-based: empty, ID, Date, Tags, Summary)
                    summary_idx = 4
                    consumers = ', '.join(CONSUMER_MAP[finding_id])
                    # Append consumer metadata to summary
                    parts[summary_idx] = parts[summary_idx].rstrip() + f' **Consumers:** {consumers}.'
                    line = '|'.join(parts) + '|\n'
                    updated_count += 1

        modified.append(line)

    with open(path, 'w') as f:
        f.writelines(modified)

    return updated_count

if __name__ == '__main__':
    findings_path = 'docs/findings.md'
    count = process_findings_file(findings_path)
    print(f"Updated {count} findings with consumer metadata")
    print(f"Total findings in consumer map: {len(CONSUMER_MAP)}")
