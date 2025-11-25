### Turn Summary
Updated .gitignore for calibration bundle persistence; regenerated refined MTZ and config_torch_smoke.json via DiffBragg capture (spot_scale=3.11e17, N_cells=[36,28,26]).
Critical blocker identified: refined structure factors produce negative ROI correlation (median=-0.040 in mapping probe, -0.051 in DB-AT-029 fixture), chi²/px=2.1e5 >> 1e2 bound, indicating fundamental incompatibility between DiffBragg-refined HKL and Stage A torch forward simulator under the smoke metadata/calibration environment.
Next: escalate to Galph with evidence (mapping probe + DB-AT metrics); revisit capture workflow vs spot_scale/HKL pairing assumptions per SCALE-004 before retrying DB-AT selectors.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T110430Z/ (smoke_calibration_manifest.json, mapping_comparison.log, pytest_db_at_028_029.log, db_at_028/db_at_028_metrics.json, db_at_029/db_at_029_metrics.json)

---

### Turn Summary
Queued the refined HKL capture/validation work so the smoke dataset can reuse the same MTZ as its calibration bundle; plan logged in fix_plan and input.
Identified the missing `sp.proc/calibration/smoke_refined_structure_factors.mtz` + gitignore gap and directed Ralph to re-run the capture script, commit the new MTZ, and rerun mapping + DB-AT selectors under `DBEX_SMOKE_HKL_PATH` so telemetry records the refined path.
Next: execute the Do Now to regenerate the asset, collect the probe/tests, and update fix_plan with the resulting metrics.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T110430Z/ (input.md, future manifest/log placeholders)
