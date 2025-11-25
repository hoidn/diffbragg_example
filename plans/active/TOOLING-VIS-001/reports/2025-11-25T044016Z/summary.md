### Turn Summary
Logged the latest parity probe vs DB-AT-028/029 results and drafted a new Do Now to unify the mapping context between the probe and the smoke fixture after fixing the HKL wiring.
Captured that the CPU parity probe now reports mapping ROI CC≈0.62 while the pytest fixture on the metadata-sigma CUDA dataset still fails with chi²/pixel≈1.08e5 and ROI CC≈-0.05, indicating a dataset/device mismatch.
Updated docs/fix_plan.md attempts, refreshed input.md with ready-for-implementation steps, and recorded the loop in galph_memory.md.
Next: refactor the parity probe and stage_a_smoke_result to share build_mapping_stage_a_context, then rerun the parity probe and DB-AT-028/029 selectors.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T044016Z/ (parity_probe.log, parity_metrics.json)
