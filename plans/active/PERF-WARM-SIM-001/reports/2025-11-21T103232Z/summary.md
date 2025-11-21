### Turn Summary
Gated Stage A ROI sampling behind the warm cache (with an `allow_cold_stage_a_roi_mode` override) and exposed the roi_mode label in perf telemetry plus the benchmark CLI toggle.
Reran the Stage A smoke + telemetry and the warm/cold benchmark so perf counters now show warm roi-mode vs cold panel-mode, yielding 14.6 s vs 169.4 s (11.6×) with updated logs.
Next: extend the same ROI-only warm gating to the Stage B/C contexts once Stage A evidence remains stable.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T103232Z/ (pytest_stage_a_small.log, benchmark_summary.json)

### Turn Summary
Scoped the warm-only ROI gating increment for PERF-WARM-SIM-001, updating docs/fix_plan so we add an `allow_cold_stage_a_roi_mode` override plus benchmark/telemetry expectations for warm vs panel runs.
Rewrote input.md with a Perf-mode Do Now (Stage A ROI gate + benchmark script edits) and documented the exact pytest/benchmark commands + telemetry targets for Ralph.
Next: Ralph implements the ROI gate, runs the Stage A smoke + benchmark, and updates findings once the ≥2× speedup artifacts land.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T103232Z/ (summary.md)
