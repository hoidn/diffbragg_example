### Turn Summary
Planned ARCH-REFACTOR-001 Phase C.7 (Stage A utilities extraction) after Phase C.6 completion left Stage A impl as the final *_impl.py module (1524 lines, 11 functions).
Analyzed cross-stage dependencies (7 shared helpers used by Stage B/C/reconstruction, 3 Stage-A-private) and designed two-step extraction following Phase C.5 hkl_utils precedent: extract shared helpers to stage_a_utils.py (C.7), inline private logic into StageA class (C.8), delete impl (C.9).
Next: Ralph executes Phase C.7 extraction + import updates across 5 files (stage_a/stage_b/stage_c/reconstruction) and validates with 4 selectors (Stage A expansion, Stage B guard/shell, Stage C microslip).
Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-12-02T200000Z/ (planning_notes.md)
