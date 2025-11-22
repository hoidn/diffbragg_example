### Turn Summary
Authored Phase B5 Do Now directing Ralph to fix code path discrepancy between _forward_once (script-level, chi²=1.425B) and run_nanobrag_refinement (production, chi²=1.13M).
Root cause H4a confirmed with HIGH confidence ~85% from Phase B4; B_ideal fix (commit e86fd4e) works in production but not applied in script path—likely cctbx recompute bug + missing quaternion normalization.
Next: Ralph audits _forward_once U-matrix logic (4-element comparison), patches B_ideal source + q normalization, validates with 1-step test (expect chi²_init~1.13M healthy), synthesizes Path A/B/C decision.
Artifacts: plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T183012Z/ (input.md with 10-step protocol, decision tree templates)
