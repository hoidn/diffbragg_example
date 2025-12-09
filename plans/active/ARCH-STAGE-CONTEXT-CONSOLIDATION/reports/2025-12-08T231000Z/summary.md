### Turn Summary
Added `StageAInputContext` dataclass to `dbex/refinement/context.py:1033` per Phase B.1 — consolidates 11 input params for `_build_stage_a_params`.
Import verified; context module tests passed (6/6). Stage A smoke failed with pre-existing HKL hit-rate=0% issue (unrelated to this change).
Next: Phase B.2 — add `StageBInputContext` dataclass.
Artifacts: plans/active/ARCH-STAGE-CONTEXT-CONSOLIDATION/reports/2025-12-08T231000Z/ (import_check.log, pytest_context.log, pytest_stage_a_smoke.log)

## Metrics
- Import: OK
- Context tests: 6/6 PASSED
- Stage A smoke: FAILED (pre-existing HKL grid issue, model_mean=0.0, hit_rate=0%)

## Files Changed
- `dbex/refinement/context.py`: +39 lines (StageAInputContext dataclass)
- `docs/fix_plan.md`: Updated status to Phase B.1 complete
