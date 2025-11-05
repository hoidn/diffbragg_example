### Turn Summary
Delivered HKL hit-rate probe analyzing REFINE-004 perturbation coverage; discovered 100% in-bounds rate but all indices fractional (max 0.5), contradicting REFINE-005 grid-bounds hypothesis.
The 0% hit rate from prior attempts likely stems from nanobrag_torch integer index lookup rejecting fractional coordinates, not bounds violations; tricubic interpolation semantics need verification.
Next: investigate whether nanobrag_torch HKL interpolation accepts fractional indices or requires rounding; if rounding viable, perturbation may work without grid rebuild.
Artifacts: plans/active/TORCH-REFINE-002D/reports/2025-11-05T044720Z/ (hkl_probe.json, collect_stage_a.log, pytest_stage_a.log)
