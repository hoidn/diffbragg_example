### Turn Summary
Pinned down why the Stage B CPU fallback still reports `cache_mode="cold"` (dbex/nanobrag_refinement.py:1588-1604 + stage_b_roi_summary.json:32-44) and wrote the new fix-plan attempt/input.md so Ralph clones StageAContext onto CPU and keeps canonical runs warm.
Captured the telemetry/runtime evidence plus logged finding PERF-WARM-012 and the 2025-11-21T160700Z plan update so the engineer can focus purely on the cache plumbing + smoke/test reruns.
Next: Ralph implements the CPU Stage A cache clone in run_nanobrag_refinement, refreshes the Stage B smoke asserts, reruns both selectors, and regenerates summarize_stage_b_roi.py artifacts under plans/active/PERF-WARM-SIM-001/reports/2025-11-21T160700Z/.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T160700Z/ (input.md, summary.md)
