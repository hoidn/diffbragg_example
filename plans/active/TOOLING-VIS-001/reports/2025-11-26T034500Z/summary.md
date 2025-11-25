### Turn Summary
Recorded the Stage A masked-mean failure and refreshed the Do Now/input so the next loop computes the log-scale baseline from the warmed simulator instead of the global scale hint.
Root-caused the null baseline to the numpy mask → torch tensor indexing inside dbex/nanobrag_refinement.py:1324-1365 and captured evidence (db_at_029 metrics) in docs/fix_plan.md + galph_memory.md.
Next: implement the tensorized masked-mean path, persist the zero-iteration means to telemetry, and rerun DB-AT-028/029 under the canonical metadata env.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-26T034500Z/ (input.md, planning notes)
