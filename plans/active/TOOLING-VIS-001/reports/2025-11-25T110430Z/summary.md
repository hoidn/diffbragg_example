### Turn Summary
Queued the refined HKL capture/validation work so the smoke dataset can reuse the same MTZ as its calibration bundle; plan logged in fix_plan and input.
Identified the missing `sp.proc/calibration/smoke_refined_structure_factors.mtz` + gitignore gap and directed Ralph to re-run the capture script, commit the new MTZ, and rerun mapping + DB-AT selectors under `DBEX_SMOKE_HKL_PATH` so telemetry records the refined path.
Next: execute the Do Now to regenerate the asset, collect the probe/tests, and update fix_plan with the resulting metrics.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T110430Z/ (input.md, future manifest/log placeholders)
