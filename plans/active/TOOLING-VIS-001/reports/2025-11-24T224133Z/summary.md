### Turn Summary
Implemented Stage A calibration plumbing to align zero-point forward model with DB-AT-024 mapping baseline per DB-AT-027 spec.
Extended RefinementConfig with calibration_metadata fields, threaded spot_scale_override/beam flux/N_cells through _build_stage_a_context into beam/crystal configs, implemented log_scale baseline separation (±3 delta clamping when calibrated), and updated refine_one.py + stage_a_adam.py to forward calibration payload.
Next: run pytest selector for DB-AT-027, remove xfail if tolerances pass, update docs/TESTING_GUIDE.md and TEST_SUITE_INDEX.md with Active status.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-24T224133Z/ (summary.md, commit e1d8432)
