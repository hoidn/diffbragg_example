# MAP-SCALE-001 — Zero-iteration mapping scale alignment

## Purpose
Resolve the scale mismatch between `simulate_forward_once` outputs and background-subtracted targets so that DB_AT_024 can assert its correlation and localization thresholds without provisional XFAIL.

## References
- `docs/spec-db-workflow.md` §4 — calibration policy & global scale initialization
- `docs/architecture.md` §4.3 — torch staging (global scale expectations)
- Findings: SCALE-001, SCALE-002, CONFORMANCE-001, TESTING-003
- Artifacts: `plans/active/DB-AT-024/reports/2025-11-04T070000Z/mapping_metrics.json`

## Exit Criteria (from fix_plan)
1. Diagnose the scale mismatch and capture per-ROI intensity ratios.
2. Validate a scaling strategy (analysis-only) that reaches corr≥0.2, localization≥0.90.
3. Produce a ready-for-implementation Do Now with mapped pytest selector and artifact plan.

## Phase Breakdown

- **Phase A — Evidence & Diagnostics**
  - [x] A1: Snapshot baseline metrics (correlation, localization, bragg/target means) into `reports/<ts>/baseline_metrics.json`.
  - [x] A2: Compute per-ROI scale ratios (target_mean / bragg_mean) and histogram to confirm systematic under-scaling.
  - [x] A3: Document findings + spec cross-links in `reports/<ts>/summary.md`.

- **Phase B — Strategy Prototyping (analysis-mode)**
  - [x] B1: Evaluate candidate scaling rules (e.g., apply `global_scale_hint`, ratio-of-means, shared `spot_scale_override`) via analysis script that multiplies `simulate_forward_once` outputs without modifying production code.
  - [x] B2: Record resulting metrics (corr, localization) for each rule; store in `reports/<ts>/strategy_comparison.json`.
  - [x] B3: Select preferred strategy aligned with SCALE-001/002 (no structure-factor rescale; strictly post-sim scaling).
    - Outcome: Adopt DiffBragg-refined `Fopt` amplitudes plus √spot_scale post-sim scaling (per SCALE-001/002/003) as the viable remediation path.

- **Phase C — Implementation Prep**
  - [x] C1: Draft Do Now with concrete production edits (`dbex/nanobrag_bridge.py::simulate_forward_once`, optional CLI plumbing) and mapped pytest selector `tests/dbex/test_mapping_consistency.py::TestDB_AT_024_Mapping::test_db_at_024_mapping_smoke`.
  - [x] C2: Outline artifact capture + documentation sync (TESTING_GUIDE.md, TEST_SUITE_INDEX.md) for Ralph.
  - [x] C3: Update `docs/findings.md` if new guardrails emerge (e.g., scale initialization best practice).

## Risks / Open Questions
- Ensure scaling fix does not regress photon-mode (adu_per_photon) paths.
- Spot scale override might require sourcing from MTZ or CLI; need to spec retrieval if fixed ratio is insufficient.
- Must avoid violating Environment Freeze; all prototyping stays in analysis artifacts.
