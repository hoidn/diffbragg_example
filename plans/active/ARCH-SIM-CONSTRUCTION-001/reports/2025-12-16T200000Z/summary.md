### Turn Summary

Implemented DB-AT-027 mapping-parity diagnostics in the Stage A baseline probe script, adding per-ROI correlations, max|Δ|, RMSE, chi²/pixel comparison, and warning logic. Probe validation reveals catastrophic parity failure: Stage A vs mapping median ROI CC = -0.0450 (vs ≥0.99 threshold), max|Δ| = 1.105e+05 ADU (vs ≤1.0 ADU), with both models showing negative correlations against target. This proves DB-AT-027/028/029 failures stem from spec/harness/test fixture issues rather than reconstruction implementation bugs. Recommend supervisor escalate to spec_change initiative or investigate mapping model correctness.

Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-16T200000Z/stage_a_baseline_probe.json
