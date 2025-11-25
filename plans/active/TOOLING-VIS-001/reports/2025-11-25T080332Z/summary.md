### Turn Summary
Flagged the smoke calibration capture JSON schema mismatch and documented how it prevents load_calibration_metadata from ever seeing the newly generated metadata.
Authored a ready-for-implementation Do Now so Ralph reshapes capture_smoke_calibration.py to emit the canonical DiffBragg config_torch layout, regenerates the calibration bundle, and reruns the mapping probe plus DB-AT-028/029 with DBEX_SMOKE_CALIB_PATH set.
Next: Execute the capture/probe/pytest workflow under the new artifacts directory and confirm telemetry finally reports spot_scale_override≈3.1e+17 before tackling the remaining chi²/ROI gaps.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T080332Z/
