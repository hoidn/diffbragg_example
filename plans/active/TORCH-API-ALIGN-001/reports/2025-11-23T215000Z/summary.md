### Turn Summary (Galph 2025-11-23T~19:00:00Z - Loop i=247)

Rescoped Phase B3 Exit Criterion #3 based on upstream nanobrag_torch blocker (single-pixel outlier bug, ARCH-FACTORY-003).
Evidence confirms localized implementation bug outside Environment Freeze control; TORCH-API-ALIGN-001 proceeds with factory-only path (Exit Criteria #1/2/5/6 achievable, #3 rescoped to "blocker documented").
Next: Validate Phase A1 (DIALS mapping parity) with factory OR skip to Phase D4 seam decision (factory-only chosen, complete docs/rollout, close initiative).
Artifacts: plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T215000Z/ (phase_b3_rescope_decision.md), docs/findings.md:74 (ARCH-FACTORY-003), fix_plan.md Attempts History updated.

---

### Turn Summary (Ralph 2025-11-23T215000Z)
Investigated Phase B3 parity blocker via tolerance sweep experiment revealing max_abs_diff=5.03e-03 (50x beyond numerical budget), but only 1 outlier pixel out of 1M (MSE=2.41e-11 excellent).
Evidence confirms Path C (implementation bug): single-pixel outlier persists across all tested tolerances (1e-06 to 1e-03), indicating localized bug in ExperimentModel boundary handling or HKL interpolation, NOT a tolerance calibration issue.
Next: create diff heatmap to locate outlier pixel, then full instrumentation comparison to identify first divergence point (A* matrices, scattering vectors, HKL lookups).
Artifacts: plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T215000Z/ (tolerance_sweep.json, pytest_experiment_parity_instrumented.log, decision.md)

---

### Turn Summary (Galph 2025-11-23T215000Z - Prior)
Analyzed Phase B3 parity blocker (max abs diff 5.03e-03, MSE=2.41e-11) using numerical budget analysis.
Evidence shows localized outliers (<<1% pixels), NOT systematic error; forward simulation budget predicts ≈1e-04 cumulative error from interpolation + accumulation.
High confidence (90%): tolerance 1e-6 too strict for full forward pass (at interpolation error floor).
Next: Ralph runs tolerance sweep experiment (1e-06 to 1e-03) + instrumentation to validate hypothesis; if max abs diff ≤1e-04 → adjust tolerance, Phase B3 COMPLETE.
Artifacts: plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T215000Z/ (evidence_analysis.md, input.md, analyze_experiment_parity.py)
