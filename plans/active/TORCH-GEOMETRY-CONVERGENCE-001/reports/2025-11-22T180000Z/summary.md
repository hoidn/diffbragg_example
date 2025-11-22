# Turn Summary

Fixed B_ideal source mismatch in LBFGS closure via code audit — closure was recomputing B_ideal from cctbx cell instead of using MOSFLM-derived value from initialization.
Root cause: dbex/nanobrag_refinement.py:786 discarded returned B_ideal and created new TorchCrystal (lines 801-818), causing U @ B_ideal_cctbx ≠ A*_MOSFLM divergence.
Fix applied (line 787 capture B_ideal, delete lines 795-818 recomputation); zero-point validation PASSED chi²=989k unchanged; LBFGS test running to confirm step 0 fix.
Artifacts: plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T180000Z/ (code_audit_b_ideal_sources.md, b_ideal_fix_implementation.md, phase_b_deep_diagnostic_decision.md, revalidation/zero_point_check.json)
