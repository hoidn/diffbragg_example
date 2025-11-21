### Turn Summary
Implemented CPU cache cloning so canonical Stage B runs reuse cached detectors/simulators/masks even on CPU, restoring cache_mode="warm" telemetry and reducing runtime from ~80s to ~72s.
The small-detector smoke stays on CUDA with ROI mode (~193ms), while the canonical smoke now runs on CPU with warm panel cache, proving cache reuse works across devices.
Next: Exit criteria satisfied (canonical Stage B reports cache_mode="warm" with ~10% runtime improvement); PERF-WARM-SIM-001 can remain active for future ROI recalibration or Stage C optimizations.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T160700Z/ (pytest_stage_b_small.log, telemetry_stage_b_small.json, pytest_stage_b_full.log, telemetry_stage_b_full.json, stage_b_roi_summary.json)
