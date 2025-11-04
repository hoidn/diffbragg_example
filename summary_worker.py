#!/usr/bin/env python3
"""
Worker script to generate a single summary from a log file.

Usage: summary_worker.py <log_file> <output_file> <role> <iteration>
"""

import sys
import re
from pathlib import Path
from datetime import datetime


def extract_key_sections(log_content, role, iteration):
    """Extract key information from the log file."""
    lines = log_content.split('\n')

    # Find errors, failures, decisions, and key actions
    errors = []
    actions = []
    decisions = []
    tests = []

    error_patterns = [
        r'error', r'failed', r'exception', r'traceback',
        r'FAIL', r'ERROR', r'\bFAIL\b', r'\bERROR\b'
    ]

    action_patterns = [
        r'Creating', r'Updating', r'Modifying', r'Running',
        r'Writing', r'Generating', r'Implementing', r'Fixing'
    ]

    decision_patterns = [
        r'decided', r'choosing', r'selecting', r'approach',
        r'strategy', r'will use', r'going to'
    ]

    test_patterns = [
        r'pytest', r'test', r'PASSED', r'FAILED',
        r'assertion', r'assert'
    ]

    for i, line in enumerate(lines):
        line_lower = line.lower()

        # Check for errors
        if any(re.search(pattern, line_lower) for pattern in error_patterns):
            if len(errors) < 10:  # Limit to 10 errors
                errors.append((i+1, line.strip()))

        # Check for actions
        if any(re.search(pattern, line, re.IGNORECASE) for pattern in action_patterns):
            if len(actions) < 15:
                actions.append((i+1, line.strip()))

        # Check for decisions
        if any(re.search(pattern, line_lower) for pattern in decision_patterns):
            if len(decisions) < 10:
                decisions.append((i+1, line.strip()))

        # Check for test results
        if any(re.search(pattern, line_lower) for pattern in test_patterns):
            if len(tests) < 10:
                tests.append((i+1, line.strip()))

    return {
        'errors': errors,
        'actions': actions,
        'decisions': decisions,
        'tests': tests,
        'total_lines': len(lines)
    }


def generate_summary(log_file, role, iteration):
    """Generate a markdown summary from a log file."""

    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            log_content = f.read()
    except Exception as e:
        return f"# Iteration {iteration:05d} - {role.upper()}\n\n**Error reading log file:** {e}\n"

    sections = extract_key_sections(log_content, role, iteration)

    # Build summary
    summary = f"# Iteration {iteration:05d} - {role.upper()}\n\n"
    summary += f"**Log file:** `{log_file}`\n"
    summary += f"**Total lines:** {sections['total_lines']}\n\n"

    # Summary section
    summary += "## Summary\n\n"
    if role == "galph":
        summary += f"Galph (integration/validation agent) iteration {iteration}. "
    else:
        summary += f"Ralph (test/evidence agent) iteration {iteration}. "

    summary += f"Processed {sections['total_lines']} lines of log output.\n\n"

    # Key actions
    if sections['actions']:
        summary += "## Key Actions\n\n"
        for line_num, action in sections['actions'][:10]:
            summary += f"- L{line_num}: {action[:150]}\n"
        summary += "\n"

    # Decisions
    if sections['decisions']:
        summary += "## Decisions/Rationales\n\n"
        for line_num, decision in sections['decisions'][:8]:
            summary += f"- L{line_num}: {decision[:150]}\n"
        summary += "\n"

    # Errors/Failures
    if sections['errors']:
        summary += "## Errors/Failures\n\n"
        for line_num, error in sections['errors'][:10]:
            summary += f"- L{line_num}: {error[:150]}\n"
        summary += "\n"
    else:
        summary += "## Errors/Failures\n\nNo obvious errors detected.\n\n"

    # Tests
    if sections['tests']:
        summary += "## Test Results\n\n"
        for line_num, test in sections['tests'][:8]:
            summary += f"- L{line_num}: {test[:150]}\n"
        summary += "\n"

    # Evidence/Links
    summary += "## Evidence/Links\n\n"
    summary += f"- Raw log: `{log_file}`\n"
    summary += f"- Role: {role}\n"
    summary += f"- Iteration: {iteration:05d}\n\n"

    # Next steps (extracted from end of log if possible)
    summary += "## Next Steps\n\n"
    last_lines = log_content.split('\n')[-20:]
    next_step_found = False
    for line in last_lines:
        if any(word in line.lower() for word in ['next', 'todo', 'will', 'going to', 'should']):
            summary += f"- {line.strip()[:150]}\n"
            next_step_found = True

    if not next_step_found:
        summary += "No explicit next steps found in log.\n"

    summary += "\n"

    return summary


def main():
    if len(sys.argv) != 5:
        print(f"Usage: {sys.argv[0]} <log_file> <output_file> <role> <iteration>")
        return 1

    log_file = sys.argv[1]
    output_file = sys.argv[2]
    role = sys.argv[3]
    iteration = int(sys.argv[4])

    if log_file == "None" or not Path(log_file).exists():
        print(f"Log file not found: {log_file}")
        # Create a minimal summary
        summary = f"# Iteration {iteration:05d} - {role.upper()}\n\n"
        summary += "**Status:** Log file not found or missing\n\n"
        summary += "## Summary\n\nNo log file available for this iteration.\n"
    else:
        summary = generate_summary(log_file, role, iteration)

    # Write summary
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(summary)

    print(f"Generated: {output_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
