### Turn Summary
Captured canonical Stage B telemetry via probe script showing Stage A stalls at χ²≈3.0e8 while Stage B drops to 1.23e8 with shell_0=2.0, proving ROI mode breaks REFINE-008.
Logged PERF-WARM-010 + fix-plan attempt so canonical runs must disable Stage A ROI mode until the strict gate is recalibrated, and rewrote input.md with the ROI-toggle Do Now plus rerun commands.
Next: Ralph turns off Stage A ROI mode for `smoke-detector-size=full`, reruns both Stage B smokes, and publishes telemetry + summary artifacts.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-21T133127Z/ (stage_b_full_probe.json, stage_b_full_probe.txt)
