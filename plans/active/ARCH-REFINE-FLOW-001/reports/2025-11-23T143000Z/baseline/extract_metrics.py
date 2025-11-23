#!/usr/bin/env python3
import json
import re

def extract_test_metrics(log_path):
    with open(log_path, 'r') as f:
        content = f.read()
    
    # Extract test result
    if re.search(r'1 passed', content):
        status = 'PASS'
    elif re.search(r'1 failed', content):
        status = 'FAIL'
    elif re.search(r'1 skipped', content):
        status = 'SKIP'
    else:
        status = 'UNKNOWN'
    
    # Extract runtime
    runtime_match = re.search(r'(\d+\.\d+)s\s*=+$', content, re.MULTILINE)
    runtime = float(runtime_match.group(1)) if runtime_match else None
    
    # Extract exit code
    exit_code_match = re.search(r'Exit code: (\d+)', content)
    exit_code = int(exit_code_match.group(1)) if exit_code_match else None
    
    return {
        'status': status,
        'runtime_seconds': runtime,
        'exit_code': exit_code
    }

# Extract small detector metrics
small_metrics = extract_test_metrics('pytest_stage_c_small_final.log')
small_metrics['test'] = 'stage_c_small'
small_metrics['detector_size'] = 'small'

# Extract full detector metrics
full_metrics = extract_test_metrics('pytest_stage_c_full.log')
full_metrics['test'] = 'stage_c_full'
full_metrics['detector_size'] = 'full'

# Write metrics
with open('metrics_stage_c_small.json', 'w') as f:
    json.dump(small_metrics, f, indent=2)

with open('metrics_stage_c_full.json', 'w') as f:
    json.dump(full_metrics, f, indent=2)

print("Metrics extracted successfully")
