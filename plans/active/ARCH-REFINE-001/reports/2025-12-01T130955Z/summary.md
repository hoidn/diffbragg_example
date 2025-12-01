### Turn Summary
Replaced direct Simulator construction with create_unified_simulator factory in Stage A/B final Bragg reconstruction cold paths per ARCH-FACTORY-001 Phase B.4.
Both Stage B and Stage C small-detector smokes passed (22.9s and 7.6s respectively) confirming factory plumbing preserves behavior.
Warm-cache retargeting and Stage closures remain on direct Simulator construction for autograd preservation.
Next: advance to next ARCH-REFINE-001 phase or consolidate remaining forward-only helpers (Phase B.5).
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T130955Z/ (pytest logs, telemetry JSONs, collection log)
