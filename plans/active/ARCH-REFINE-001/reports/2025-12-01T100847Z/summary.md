### Turn Summary
Created the Stage C telemetry probe (`plans/active/ARCH-REFINE-001/bin/capture_stage_c_stage_a_probe.py`) but the run immediately surfaced that the cropped refGeom_small assets are missing, so no new Stage A traces were captured.
Recorded the dataset gap in docs/fix_plan.md and the probe log, blocking Stage A improvement diagnosis until the small-detector bundle is regenerated per docs/data_dependency_manifest.md.
Next: restore `sp.proc/refGeom_small/{expt,refl,mask}` via the PERF-SMOKE-DETSIZE crop script, rerun the telemetry probe, then replay the Stage B/C smokes to gather Stage A traces for the zero-improvement fix.
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T100847Z/ (stage_c_stage_a_probe_cli.log)
