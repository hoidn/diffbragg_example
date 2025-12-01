### Turn Summary
Diagnosed Stage C's repeat +0.067% chi² regression as a trusted-mask mismatch versus Stage A and captured the evidence plus fix plan.
Updated docs/fix_plan.md, docs/findings.md, galph_memory.md, and input.md so the next loop applies the trusted-mask gate inside Stage C's loss path and reruns the Stage C smokes with telemetry + summarizer artifacts.
Next: implement the masking fix in dbex/refinement/stage_c_impl.py and revalidate both detector sizes to prove REFINE-007 is green.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-12-01T214200Z/ (trusted_mask_analysis.md)
