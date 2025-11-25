### Turn Summary
Verified the metadata smoke calibration bundle (config_torch_smoke.json + manifest) already exists and still reports spot_scale_override≈3.10e17, so DB-AT-028/029 must run under DBEX_SMOKE_CALIB_PATH before we can judge Stage A.
Documented the capture in docs/fix_plan.md and refreshed input.md with a ready-for-implementation Do Now to log calibration_path in the CPU/GPU probe and Stage A smoke fixture.
Next: Ralph reruns capture → mapping probe → DB-AT-028/029 with the new logging so we can see whether the calibration produces non-zero Bragg stacks and record the path in artifacts.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T074043Z/ (input.md, summary.md)
