### Turn Summary
Added CPU fallback diagnostic logging to Stage B helpers; all three conditions evaluate correctly (fallback=true, eval_device="cpu" for full detector).
Root cause identified: _build_final_bragg_from_stage_b_telemetry ignores use_stage_b_cpu_fallback flag and hardcodes device=cuda:0, causing OOM at final Bragg generation (line 2912), NOT in LBFGS closure.
Next: implement 7-line fix (pass fallback flag to final Bragg function + route device parameter).
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T094500Z/ (decision.md, instrumentation_summary.md, cpu_fallback_conditions.json, pytest logs)
