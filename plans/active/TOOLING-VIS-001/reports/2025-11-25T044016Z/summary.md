### Turn Summary
Refactored stage_a_smoke_result fixture and compare_stage_a_mapping_parity.py probe to share HKL/calibration/inputs via build_mapping_stage_a_context per input.md Do Now.
Both now use the same mapping dataset (metadata sigma, nearest-neighbor HKL, refined MTZ when available) and bragg_zero_iter for parity comparison; mapping ROI CC=0.62 confirms forward stack is aligned, while Stage A before/after ROI CC=-0.04/-0.05 documents the mismatch to be debugged.
DB-AT-028/029 persist mapping metrics before assertions (mapping_forward_success=true) even on failure per STAGEA-001 finding; tests properly FAIL with chi²/pixel initial=1.08e5 exceeding 1e2 bound and ROI CC below 0.2 floor.
Next: investigate why Stage A initial geometry + perturbed crystal produces negative ROI correlations vs mapping zero-point geometry.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T044016Z/ (parity_metrics.json, db_at_028_metrics.json, db_at_029_metrics.json, pytest logs, collect-only log)
