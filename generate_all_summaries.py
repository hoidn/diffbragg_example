#!/usr/bin/env python3
"""
Generate all missing summaries in parallel batches.
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

MAX_CONCURRENCY = 8


def generate_summary_task(task):
    """Generate a single summary."""
    role = task['role']
    iteration = task['iteration']
    log_file = task['log_file']

    # Generate output filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_file = f"logs/integration/{role}-summaries/iter-{iteration:05d}_{timestamp}-summary.md"

    # Check if already exists
    output_path = Path(output_file)
    if output_path.exists():
        return {'status': 'skipped', 'file': output_file, 'reason': 'already exists'}

    # Run worker
    try:
        result = subprocess.run(
            ['python', 'summary_worker.py', log_file, output_file, role, str(iteration)],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            return {'status': 'created', 'file': output_file, 'role': role, 'iteration': iteration}
        else:
            return {'status': 'failed', 'file': output_file, 'error': result.stderr}
    except Exception as e:
        return {'status': 'failed', 'file': output_file, 'error': str(e)}


def main():
    # Load missing summaries
    with open('missing_summaries.json', 'r') as f:
        data = json.load(f)

    tasks = data['missing']
    print(f"Processing {len(tasks)} missing summaries...")
    print(f"Max concurrency: {MAX_CONCURRENCY}")
    print()

    created = []
    skipped = []
    failed = []

    # Process in parallel
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENCY) as executor:
        futures = {executor.submit(generate_summary_task, task): task for task in tasks}

        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()

            if result['status'] == 'created':
                created.append(result)
                print(f"[{i}/{len(tasks)}] Created: {result['file']}")
            elif result['status'] == 'skipped':
                skipped.append(result)
                print(f"[{i}/{len(tasks)}] Skipped: {result['file']}")
            else:
                failed.append(result)
                print(f"[{i}/{len(tasks)}] Failed: {result['file']} - {result.get('error', 'unknown')}")

    # Summary
    print()
    print("="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total tasks: {len(tasks)}")
    print(f"Created: {len(created)}")
    print(f"Skipped: {len(skipped)}")
    print(f"Failed: {len(failed)}")
    print()

    if created:
        print("Created files by role:")
        galph_created = [r for r in created if r['role'] == 'galph']
        ralph_created = [r for r in created if r['role'] == 'ralph']
        print(f"  galph: {len(galph_created)}")
        print(f"  ralph: {len(ralph_created)}")

    # Save results
    results = {
        'created': created,
        'skipped': skipped,
        'failed': failed,
        'summary': {
            'total': len(tasks),
            'created': len(created),
            'skipped': len(skipped),
            'failed': len(failed)
        }
    }

    with open('summary_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print()
    print(f"Detailed results saved to summary_results.json")

    return 0 if len(failed) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
