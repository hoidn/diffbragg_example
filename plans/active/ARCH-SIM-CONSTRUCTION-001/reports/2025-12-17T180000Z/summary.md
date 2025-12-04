### Turn Summary

Implemented masked-mean ratio scaling in mapping baseline (`dbex/vis/mapping.py::build_mapping_stage_a_context`), achieving DB-AT-027 parity between Stage A and mapping zero-iteration outputs (max|Δ|=3.9e-03 ADU < 1.0 ADU threshold, median ROI CC=1.0000 ≥ 0.99). Exit criterion #1 SATISFIED—mapping and Stage A baselines now produce identical outputs within numerical noise when using the same parameters. DB-AT-028/029 still fail (chi²=2.1e5, ROI corr=-0.053) as expected, with reconstruction helper not yet applying mapping baseline. Next step: update reconstruction helper to detect `log_scale_baseline_source="mapping_masked_mean_adjustment"` and use mapping baseline when present.

Artifacts: stage_a_baseline_probe_baseline.json (DB-AT-027 PASS), pytest_db_at_028_029.log, baseline_probe.log
