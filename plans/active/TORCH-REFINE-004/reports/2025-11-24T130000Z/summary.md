### Turn Summary
Authored ready-for-implementation directive for Phase 6 ASU mapping infrastructure: three helper functions (compute_hkl_asu_map, initialize_asu_modifiers, apply_asu_modifiers), RefinementConfig extensions for dynamic optimizer selection, and four unit tests validating P1/P432 space groups plus halo handling.
Ralph's Phase 6 planning (loop i=259) confirmed cctbx.miller available, designed ASU index computation with halo voxels reserved at index 0, and recommended 10K parameter gate for LBFGS vs Adam selection (P1 test fixture ~35K parameters requires Adam).
Implementation floor enforced: next loop MUST deliver production code (dwell=1 planning, max-1-docs-only-loop rule).
Next: Ralph implements helpers + unit tests, validates 4/4 tests PASS < 10s, confirms regression guard test_stage_b_shell_modifiers.
Artifacts: plans/active/TORCH-REFINE-004/reports/2025-11-24T130000Z/ (input.md, summary.md)
