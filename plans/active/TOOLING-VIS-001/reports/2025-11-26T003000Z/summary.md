### Turn Summary
Flagged Stage A double-scaling: mapping now has the correct masked scale but Stage A still multiplies by the auto-adjusted spot_scale, yielding scale_ratio_before≈2.0e4 despite roi_cc_median_mapping≈0.047.
Updated docs/fix_plan.md, docs/findings.md, input.md, and galph_memory.md with the new log-scale override plan plus the reserved artifacts path for the next implementation loop.
Next: implement the mapping-aware log-scale baseline override in dbex/nanobrag_refinement + stage_a_smoke_result and rerun DB-AT-028/029 under the metadata env to prove Stage A matches the mapping stack.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-26T003000Z/ (summary.md placeholder)
