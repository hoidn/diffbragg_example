### Turn Summary
Diagnosed metadata smoke fixtures still reporting calibration_path=null because tests/conftest.py only exposes args.config_path, so mapping helpers drop the captured config.
Added check_mapping_fixture_calibration.py plus new input.md/fix_plan updates directing Ralph to thread calibration_config_path through refGeom and rerun DB-AT-028/029 under the canonical metadata env.
Next: implement the fixture patch, run the selectors, and use the checker to prove calibration_path and spot_scale_override match the smoke assets before tackling the physics gap.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T140000Z/
