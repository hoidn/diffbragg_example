### Turn Summary
Recorded a Stage B/C callchain snapshot for PERF-SMOKE-DETSIZE, tracing the smoke harnesses through `run_nanobrag_refinement` into the nanobrag_torch simulator stack.
Highlighted the concrete failure modes: Stage B’s LBFGS closure mutates `chi_squared_best_b` without `nonlocal`, and Stage C telemetry never references the ±0.25 mm detector offsets so its gates always pass despite zero chi-squared improvement.
Next: implement the Stage B closure fix (add `nonlocal` + remove debug prints) and extend Stage C telemetry to capture real baseline offsets before recalibrating the smoke tolerances.
Artifacts: plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T035150Z/ (callchain/static.md, trace/tap_points.md)
