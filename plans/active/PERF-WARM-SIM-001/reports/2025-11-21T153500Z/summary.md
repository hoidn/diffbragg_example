### Turn Summary
Captured the 2025-11-21T150000Z Stage B telemetry, logged the CUDA OOM regression as finding PERF-WARM-011, and refreshed the fix-plan ledger with the new scope.
Drafted a ready-for-implementation Do Now so stage_b_full_eval_on_cpu routes canonical panel runs to CPU while the small-detector ROI path stays on the warmed CUDA cache, and mapped the enforcing pytest commands plus ROI summary script.
Next: implement the CPU fallback, rerun both Stage B smokes, and regenerate stage_b_roi_summary.json to resume REFINE-008 analysis with non-error telemetry.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T153500Z/
