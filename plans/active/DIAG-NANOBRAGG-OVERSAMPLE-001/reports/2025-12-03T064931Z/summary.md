### Turn Summary
Manual simulator trace reproduced the zero-output Stage A failure using repo fixtures and showed scattering_vec≈5.8e9 while rotated crystal vectors are ≈1e-9.
HKL fractions collapsed to ~1e-9 despite metadata spanning tens, so the lookup always returns default_F=0 and oversample/flux fixes can't help.
The trace confirms the true blocker is a crystal/cell unit mismatch (meters vs Å⁻¹), now recorded as finding DIAG-UNIT-001 and folded into the plan's new Phase D.
Next: formalize this trace as a Tier-2 script and document the analysis so we can plan the nanobrag_torch fix.
Artifacts: plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T064931Z/ (simulator_trace.log)
