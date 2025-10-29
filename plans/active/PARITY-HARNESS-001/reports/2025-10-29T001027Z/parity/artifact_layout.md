# Parity Harness Artifact Layout Template

**Version:** 1.0
**Date:** 2025-10-29
**Spec Reference:** `docs/parity_harness_spec.md` §4.1

## Purpose

This template defines the normative directory structure and artifact naming conventions for DB-AT parity harness runs.

## Directory Structure

Per `docs/parity_harness_spec.md` §4.1, all parity harness runs MUST use the following structure:

```
plans/active/<initiative-id>/reports/<YYYY-MM-DDTHHMMSSZ>/
├── parity/                           # DB-AT-001 artifacts
│   ├── metrics.json                  # Standardized metrics per §4.3
│   ├── golden_trace_panel{p}_s{s}_f{f}.log  # Golden reference trace
│   ├── py_trace_panel{p}_s{s}_f{f}.log      # PyTorch trace (same pixel)
│   ├── diff_heatmap_panel{p}.png     # Visual diff (golden - py)
│   ├── overlay_panel{p}.png          # Optional: overlay visualization
│   ├── histogram_diff.png            # Optional: pixel difference histogram
│   ├── summary.md                    # Human-readable summary
│   ├── commands.txt                  # Exact reproduction commands
│   └── env.json                      # Environment snapshot
├── determinism/                      # DB-AT-002 artifacts
│   ├── metrics_same_seed.json        # Same-seed scenario metrics
│   ├── metrics_diff_seed.json        # Different-seed scenario metrics
│   ├── env.json                      # Platform fingerprint
│   ├── summary.md                    # Scenario results summary
│   ├── commands.txt                  # Reproduction commands
│   ├── diff_heatmap_diff_seed.png    # Optional: visual diff for diff-seed
│   └── histogram_same_seed.png       # Optional: same-seed difference histogram
└── pytest.log                        # Pytest execution log (shared)
```

## Example: DB-AT-001 Parity Run

**Initiative:** PARITY-HARNESS-001
**Timestamp:** 2025-10-29T001027Z
**Test:** DB-AT-001 (simple cubic parity)

**Artifact Path:**
`plans/active/PARITY-HARNESS-001/reports/2025-10-29T001027Z/parity/`

**Files Created:**
```
parity/
├── metrics.json
├── golden_trace_panel0_s1200_f1000.log
├── py_trace_panel0_s1200_f1000.log
├── diff_heatmap_panel0.png
├── summary.md
├── commands.txt
└── env.json
```

**metrics.json excerpt:**
```json
{
  "test_id": "DB-AT-001",
  "timestamp": "2025-10-29T00:10:27Z",
  "correlation": 0.9912,
  "threshold_met": true,
  "spec_threshold": 0.99
}
```

**summary.md excerpt:**
```markdown
# DB-AT-001 Parity Run Summary

**Test ID:** DB-AT-001
**Timestamp:** 2025-10-29T00:10:27Z
**Status:** PASS

## Metrics
- Correlation: 0.9912 (≥ 0.99 threshold: ✓)
- MSE: 1.23e-4
- RMSE: 1.11e-2
- Max |Δ|: 0.05
- Sum ratio: 1.0001

## First Divergence
None (all trace checkpoints match within float64 tolerance)

## Artifacts
- Golden trace: golden_trace_panel0_s1200_f1000.log
- PyTorch trace: py_trace_panel0_s1200_f1000.log
- Diff heatmap: diff_heatmap_panel0.png
```

## Example: DB-AT-002 Determinism Run

**Initiative:** PARITY-HARNESS-001
**Timestamp:** 2025-10-29T001500Z
**Test:** DB-AT-002 (determinism validation)

**Artifact Path:**
`plans/active/PARITY-HARNESS-001/reports/2025-10-29T001500Z/determinism/`

**Files Created:**
```
determinism/
├── metrics_same_seed.json
├── metrics_diff_seed.json
├── env.json
├── summary.md
└── commands.txt
```

**metrics_same_seed.json excerpt:**
```json
{
  "test_id": "DB-AT-002",
  "scenario": "same_seed",
  "timestamp": "2025-10-29T00:15:00Z",
  "bitwise_equal": true,
  "correlation": 0.99999999,
  "max_abs_diff": 1.2e-12,
  "threshold_met": true
}
```

**metrics_diff_seed.json excerpt:**
```json
{
  "test_id": "DB-AT-002",
  "scenario": "diff_seed",
  "timestamp": "2025-10-29T00:15:05Z",
  "bitwise_equal": false,
  "correlation": 0.45,
  "percent_pixels_differ": 67.8,
  "threshold_met": true
}
```

## Artifact Capture Macro

Per `docs/parity_harness_spec.md` §4.2, use this shell macro to create directories and capture environment:

```bash
# Set artifact root with auto-timestamp
export ART=plans/active/PARITY-HARNESS-001/reports/$(date -u +%FT%TZ)

# Create subdirectories
mkdir -p "$ART/parity" "$ART/determinism"

# Capture environment
echo "Python: $(python -V)" > "$ART/env.txt"
pip show torch | grep Version >> "$ART/env.txt"
lscpu | head -n1 >> "$ART/env.txt"
grep MemTotal /proc/meminfo >> "$ART/env.txt"

# Example test run (DB-AT-001)
KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests -k DB_AT_001 | tee "$ART/pytest.log"

# Metrics and traces written by test harness to $ART/parity/
```

## Required Artifacts by Test

### DB-AT-001 (Simple Cubic Parity)
**Mandatory:**
- `metrics.json` — Core metrics per §2.5
- `summary.md` — Human-readable summary

**Strongly Recommended:**
- `golden_trace_panel{p}_s{s}_f{f}.log` — Golden reference trace
- `py_trace_panel{p}_s{s}_f{f}.log` — PyTorch trace
- `diff_heatmap_panel{p}.png` — Visual diff per panel

**Optional:**
- `overlay_panel{p}.png` — Overlay visualization
- `histogram_diff.png` — Pixel difference histogram
- `commands.txt` — Reproduction commands
- `env.json` — Environment snapshot

### DB-AT-002 (Determinism)
**Mandatory:**
- `metrics_same_seed.json` — Same-seed scenario metrics
- `metrics_diff_seed.json` — Different-seed scenario metrics
- `env.json` — Platform fingerprint
- `summary.md` — Scenario results

**Strongly Recommended:**
- `commands.txt` — Reproduction commands

**Optional:**
- `diff_heatmap_diff_seed.png` — Visual diff for different-seed
- `histogram_same_seed.png` — Same-seed difference histogram

## Fix Plan Integration

Per `docs/parity_harness_spec.md` §4.4, every parity harness run MUST update `docs/fix_plan.md` Attempts History with:

**Required Lines:**
```
* <timestamp> — <action summary>
  Metrics: <key metrics summary>
  Artifacts: <path to artifact directory>
  First Divergence: <checkpoint name and delta, or "n/a">
  Next Actions: <follow-up tasks or closure>
```

**Example:**
```
* 2025-10-29T001027Z — Implemented DB-AT-001 parity harness with golden data comparison.
  Metrics: correlation=0.9912, MSE=1.23e-4, RMSE=1.11e-2, max|Δ|=0.05, threshold_met=True.
  Artifacts: plans/active/PARITY-HARNESS-001/reports/2025-10-29T001027Z/parity/.
  First Divergence: n/a.
  Next Actions: DB-AT-002 determinism harness; document correlation helper in conftest.py.
```

## Checksum Validation

Per `docs/parity_harness_spec.md` §2.2, golden datasets MUST include checksums:

**manifest.json example:**
```json
{
  "golden_data_version": "1.0",
  "generated_date": "2025-10-15",
  "files": [
    {
      "path": "golden_image_panel0.bin",
      "sha256": "a1b2c3d4e5f6...",
      "size_bytes": 49888024,
      "dtype": "float64",
      "shape": [1, 2527, 2463]
    },
    {
      "path": "golden_trace_panel0_s1200_f1000.log",
      "sha256": "f6e5d4c3b2a1...",
      "size_bytes": 4567
    }
  ]
}
```

Tests MUST validate checksums before comparison to detect data corruption.

## References

- `docs/parity_harness_spec.md` §4.1 — Artifact layout specification
- `docs/parity_harness_spec.md` §4.2 — Artifact capture macro
- `docs/parity_harness_spec.md` §4.4 — Fix plan integration requirements
- `docs/TESTING_GUIDE.md` §3 — General artifact policy
