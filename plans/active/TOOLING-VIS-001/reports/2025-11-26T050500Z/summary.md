### Turn Summary
Confirmed from 2025-11-26T020500Z db_at_029 metrics that Stage A still reports log_scale_baseline=0 and scale_ratio_before≈1.9e-10 despite scale_ratio_mapping_masked=1.
Updated docs/fix_plan.md Attempts History and rewrote input.md with a ready-for-implementation Do Now that tensorizes the Stage A masked-mean baseline and replays DB-AT-028/029 under the canonical metadata env.
Reserved plans/active/TOOLING-VIS-001/reports/2025-11-26T050500Z/ for Ralph’s evidence drop and documented pitfalls/guardrails so telemetry and artifact capture stay compliant.
Next: Ralph implements the masked-mean tensor fix in dbex/nanobrag_refinement.py::_build_stage_a_params and reruns DB-AT-028/029 per the How-To Map.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-26T050500Z/ (summary.md)
