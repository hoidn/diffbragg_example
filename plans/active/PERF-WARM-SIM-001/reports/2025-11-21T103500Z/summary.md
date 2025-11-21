### Turn Summary
Diagnosed the 1.01× warm/cold plateau as a Stage A panel-sampling flaw—every closure renders the full detector even though <0.3% of pixels participate—and logged the ROI bottleneck plus new artifacts path in the fix-plan Attempts History.
Rewrote input.md with a ready-for-implementation Do Now directing Ralph to build ROI-aware Stage A caching (cropped Detector/Simulator pairs per panel_slices, telemetry refresh, cold-mode guard) and to re-run Stage A smokes plus the warm/cold benchmark.
Next: implement the ROI batching refactor, run both Stage A selectors (small/full) and the benchmark, and record the new speedup/telemetry for findings updates.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T103500Z/ (summary.md)
