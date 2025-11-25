### Turn Summary
Cataloged the fallout from removing the golden fallback: mapping probe outputs are now all-zero because no smoke calibration asset exists, so DB-AT-028/029 still carry the same failure signature.
Updated docs/fix_plan.md and input.md so Ralph’s next loop captures a metadata-specific calibration (new capture script + manifest) and wires `refgeom_dataload` to use it by default.
Next: implement the capture script, persist `sp.proc/calibration/config_torch_smoke.json`, and rerun the mapping probe plus DB-AT-028/029 under the new `DBEX_SMOKE_CALIB_PATH`.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T083500Z/
