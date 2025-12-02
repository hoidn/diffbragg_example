### Turn Summary
Planned ARCH-REFACTOR-001 Phase C.9 (final stage_a_impl.py deletion): relocate two remaining dataclasses (StageAROIEntry, StageAContext) to context.py, update 5 import sites including bugfix for physics.loss import in stage_a.py, verify zero remaining imports, then delete stage_a_impl.py (~1524 lines).
All prior phases complete: C.7 extracted cross-stage helpers to stage_a_utils.py (2025-12-02T200000Z), C.8 inlined Stage-A-private methods into StageA class (2025-12-04T215000Z with 4/4 tests passing).
Next: Ralph implements dataclass relocation + import updates, validates with 6 selectors (Stage A expansion/telemetry, Stage B guard/shell, Stage C smoke, reconstruction integration).
Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-12-02T235959Z/ (planning_notes.md, input.md ready for Ralph)
