### Turn Summary
Implemented Stage A warm simulator cache via StageAContext that hoists Detector model instantiation and mask tensorization out of the LBFGS closure; targeted tests (test_stage_a_expansion, test_stage_b_shell_modifiers) pass with identical telemetry.
Refactored compute_loss to reuse cached detector models and device-resident HKL grid while keeping Crystal parameter updates differentiable; no telemetry schema changes.
Next: validate full test suite passes, update fix_plan.md Attempts History, and commit the warm-cache refactor.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-05T221200Z/ (pytest_stage_a_v2.log, pytest_stage_b.log, pytest_full_suite.log)

---

### Turn Summary (Previous, 2025-11-05T135200Z)
Closed Stage B fix plan as done and synced documentation with CLI mask guard artifacts.
Audited Stage A LBFGS rebuild churn and issued a detector-cache Do Now for PERF-WARM-SIM-001.
Next: implement the Stage A panel cache and rerun Stage A/B smokes under NANOBRAGG_DISABLE_COMPILE=1.
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-05T221200Z/ (summary.md)
