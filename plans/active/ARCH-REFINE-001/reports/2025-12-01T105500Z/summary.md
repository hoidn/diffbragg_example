### Turn Summary
Regenerated refGeom_small assets (29 ROIs, 1024×1024, canonical window) and captured Stage A/C telemetry proving Stage A zero-improvement blocker (0.0%, 3 LBFGS iters, loss frozen at 374M).
Stage B smoke passed cleanly; Stage C smoke blocked by Stage A assertion at test line 1146 (initial=final=3.31e+08).
Hypothesis: LBFGS convergence with small detector + cli_override sigma (uniform 3.0) or ROI sampling (4/29 @ 15%) lacks gradient signal; next step is Stage A diagnostic probes (metadata sigma, higher ROI fraction).
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T105500Z/ (refGeom_small_crop_report.json, stage_c_stage_a_probe_cli.{json,log}, pytest_stage_bc_small.log, telemetry_stage_bc_small.json)
