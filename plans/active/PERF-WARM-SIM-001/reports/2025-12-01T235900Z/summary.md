### Turn Summary
Implemented Simulator rebuild logic in `_retarget_stage_a_detectors` to apply Stage C distance deltas; small detector (panel-mode) now passes all gates with 99.999% offset reduction and stable chi², but full detector (ROI-mode) fails with byte-identical signature to prior loop (offset increases to 0.46532mm, chi² degrades 2.25%) despite code changes, triggering repeat-failure guard.
Blocked on ROI-mode execution path issue — implementation works perfectly for panel-mode but has zero effect on ROI-mode, suggesting architectural issue with ROI simulator caching or lifecycle not addressed by current approach.
Next: Supervisor must investigate ROI-mode vs panel-mode divergence, trace ROI entry simulator lifecycle, and consider callchain analysis to identify where stale simulators persist in ROI paths.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T235900Z/ (telemetry_stage_c_small/full.json, pytest_stage_c_small/full.log, blocked.md)
