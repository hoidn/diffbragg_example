### Turn Summary
Scoped Stage C helper extraction so we can move `_build_stage_c_*` + warm-cache retargeting into `dbex/refinement/stage_c_impl.py` and stop importing the monolith from Stage C.
Updated docs/fix_plan.md Attempts History plus input.md with the new Do Now (stage_c_impl implementation + Stage C smoke) and captured the required selector/env wiring under this loop’s artifacts.
Next: implement `stage_c_impl` and rerun `test_stage_c_detector_microslip` to verify telemetry, variance-floor counters, and warm-cache behavior remain intact.
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T090517Z/
