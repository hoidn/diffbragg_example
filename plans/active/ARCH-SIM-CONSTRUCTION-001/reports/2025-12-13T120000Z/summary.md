### Turn Summary
Diagnosed that DB-AT-028/029 still fail because the tests read `simulate_forward_once` before Stage A applies its telemetry baseline, so chi²/ROI gates never see the fixed scale.
Updated docs/fix_plan.md and the implementation plan to add a Phase C.8 bullet for replaying Stage A telemetry in the smoke fixture, and authored input.md directing Ralph to extend `build_final_bragg_from_stage_a_telemetry` plus update the test harness and rerun the selectors.
Next: Ralph implements the telemetry replay + fixture change, then captures DB-AT-028/029 artifacts under the reserved 2025-12-13T120000Z report directory.
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T120000Z/
