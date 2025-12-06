2026-01-14T020000Z focus=ARCH-IMPL-CONFORMANCE-001 state=implementation_ready dwell=1 action=implementation_ready artifacts=plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T020000Z/ next_action=phase_b3_b4_refactor
- Phase B.1-B.2 complete (loop i=111): canonical apply_sqrt_spot_scale API delivered (11/11 unit tests PASS), calibration_metadata parameter threaded to reconstruction signature.
- Warm-cache regression PASSED (Phase A.1), cold-path baseline FAILED as expected (Phase A.2: 64.7% rel_error).
- Phase B.3-B.4 planning complete: refactor Stage A (stage_a.py:442-443) and reconstruction (reconstruction.py:213-221) to use canonical API.
- DecisionStatus: patch_ready (API exists, refactor paths identified).
- Mapped tests: test_stage_a_vs_reconstruction_scale (warm-cache, expect PASS), test_stage_a_vs_reconstruction_scale_cold_path (cold-path, expect PASS after refactor), test_stage_a_smoke_parity (regression check).
- Next loop (i=112): Refactor both Stage A and reconstruction to delegate to apply_sqrt_spot_scale, expecting cold-path test to PASS (rel_error drop from 64.7% to <0.0001%).
Action State: implementation_ready

2026-01-14T000000Z focus=ARCH-IMPL-CONFORMANCE-001 state=implementation_ready dwell=0 action=implementation_ready artifacts=plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T000000Z/ next_action=phase_b1_b2_implementation
- Phase A complete (A.0-A.2): cold-path enforcement test confirmed 64.7% relative error (2.83x scale factor), validating duplicated sqrt(spot_scale_override) scaling logic drift.
- Root cause: calibration_metadata not threaded to reconstruction cold path (spot_scale_override=None → sqrt_spot_scale=1.0).
- Phase B.1-B.2 planning complete: phase_b_planning.md scopes canonical scaling_utils module with apply_sqrt_spot_scale function + calibration_metadata threading to reconstruction signature.
- DecisionStatus: patch_ready (canonical API design known from Phase A findings).
- Mapped tests: test_apply_sqrt_spot_scale (new unit test), test_stage_a_vs_reconstruction_scale (warm-cache regression), test_stage_a_vs_reconstruction_scale_cold_path (cold-path baseline).
- Next loop (i=111): Implement dbex/refinement/scaling_utils.py + thread calibration_metadata to reconstruction.py:203-208, expecting warm-cache PASS, cold-path FAIL (refactor deferred to B.3-B.4).
Action State: implementation_ready

2026-01-13T200000Z focus=ARCH-SIM-CONSTRUCTION-001 state=lifecycle_decision dwell=2 action=review_or_housekeeping artifacts=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T200000Z/ next_action=mark_blocked_escalate_to_environment
- Ralph's C.39 omega blocking was correct: omega hypothesis definitively rejected by evidence showing deficit exists in raw subpixel sum BEFORE omega application. F_latt at 11% of expected amplitude (vs 100%) indicates sincg lattice factor bug in nanobrag_torch itself.
- PROBE-FREEZE-001 constraint prevents further plan-local instrumentation. C.34-C.39 exhausted diagnostic capacity. Three unblock options: (A) maintainer investigation, (B) spec_change to relax DB-AT-028/029, (C) harness-grade diagnostic initiative.
- Lifecycle decision: ARCH-SIM-CONSTRUCTION-001 exceeds loop budget (C.1-C.39 = 39 loops, >6 loop hard limit) without validated first-divergence or monotonic improvement. Marking as blocked_pending_environment per non-negotiables.
- Portfolio steering: switch focus to next unblocked Tier 0 item. ARCH-IMPL-CONFORMANCE-001 (pending, architecture type) is ready to start.
Action State: lifecycle_decision_complete

2026-01-05T150000Z focus=ARCH-SIM-CONSTRUCTION-001 state=parity_localization dwell=1 action=parity_localization artifacts=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T150000Z/ next_action=collect_subpixel_coverage_metrics
- Problems ledger entry "DB-AT-028/029 scale mismatch (SCALE-009, ARCH-SIM-CONSTRUCTION-001)" serviced again this loop: we confirmed Phase C.33's centering still leaves the single-pixel probe at 0.25 % of `(Na·Nb·Nc)^2`, so the focus stays on ARCH-SIM-CONSTRUCTION-001 until the deterministic deficit is closed.
- Logged a parity-mode Do Now that keeps evidence inside the owner path: slice `_partiality_stats` down to the traced pixel inside `src/nanobrag-torch/src/nanobrag_torch/simulator.py::Simulator.run`, expose `trace_delta_{h,k,l}`, `trace_F_latt_{a,b,c}`, and `trace_F_total_squared_pre_lorentz`, extend `probe_square_lattice_scaling.py` to count how many subpixels satisfy `|Δ|<1/N` and how much `F_total²` they carry, and rerun the single-pixel probe plus `tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells` with artifacts under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T150000Z/`.
- Evidence from that run will decide whether the next implementation loop corrects the `steps` normalization or moves downstream to Lorentz/polar ordering; no new plan-local probes allowed per PROBE-FREEZE-001.
Action State: planning
