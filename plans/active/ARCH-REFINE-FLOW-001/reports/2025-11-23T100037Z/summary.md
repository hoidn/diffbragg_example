### Turn Summary
Ralph's loop i=214 instrumentation identified root cause with high confidence: CPU fallback condition logic is perfect (all flags evaluate correctly), but _build_final_bragg_from_stage_b_telemetry ignores the device routing.
Drafted targeted 7-line fix adding use_stage_b_cpu_fallback parameter, computing final_device conditionally, and replacing 7 hardcoded device references.
Next: Ralph implements device routing fix, validates on small+full detector tests, removes instrumentation if both pass, then Phase C2.2 complete.
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T100037Z/ (input.md, galph_memory entry)
