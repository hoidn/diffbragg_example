### Turn Summary
Documented that Stage A smoke diagnostics still resolve HKL to scaled.mtz even when calibration assets exist, so the failure signature stems from resolver drift not sigma routing.
Updated docs/fix_plan.md and docs/data_dependency_manifest.md to capture the drift and authored a ready-for-implementation Do Now that forces the refined MTZ default plus exposes accurate HKL telemetry.
Next: Ralph updates the fixtures/probes per the Do Now and reruns the mapping dataset probe plus DB-AT-028/029 to record refined-path telemetry even if the gates still fail.
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T203500Z/ (input.md)
