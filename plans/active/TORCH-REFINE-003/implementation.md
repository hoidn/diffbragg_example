# TORCH-REFINE-003 — Stage C Detector Microslip

## Purpose
Enable the Stage C refinement stage for the nanobrag torch backend by introducing per-panel detector translations along the panel normal. The goal is to recover deterministic detector distance miscalibrations (microslip) using LBFGS with the same closure/telemetry contract as Stage A, achieving ≥0.002% masked-MSE loss reduction (calibrated to refGeom ceiling) within ≤30 steps and capturing per-panel parameter deltas for diagnostics.

## References
- docs/spec-db-workflow.md:20-56 — Stage staging contract (Stage C detector translations + LBFGS requirement, mapping-aligned Stage A zero point)
- plans/nanobrag_integration_plan.md:157-206 — Stage C strategy, optimizer expectations, telemetry notes
- docs/config_crosswalk.md:24-69 — Detector distance/axes mapping, beam centre semantics
- docs/findings.md:REFINE-001, REFINE-006 — Scale warm-start/telemetry guardrails and calibrated improvement gates carried forward
- tests/dbex/test_nanobrag_bridge_configs.py — Detector config roundtrip, odet_vec invariants

## Exit Criteria (mirror fix_plan)
1. Introduce differentiable per-panel detector distance offsets (translation along normal) optimized via LBFGS; record per-panel `param_deltas`.
2. Deterministic Stage C smoke (refGeom with synthetic panel offsets) achieves ≥0.002% masked-MSE improvement within ≤30 LBFGS iterations while maintaining non-increasing full-loss validations, starting from the mapping-aligned Stage A zero point defined by DB-AT-024 / `simulate_forward_once`.
3. Targeted pytest selector for Stage C collects/passes; artifacts (collect-only + selector logs + JSON metrics) archived; docs/findings/fix_plan updated.

## Phase Breakdown
- Phase 0 — Baseline Reality Check
  - [ ] P0.1: Quantify masked-MSE impact of deterministic detector distance offsets (e.g., +0.25 mm along odet_vec) to confirm ≥0.002% headroom.
  - [ ] P0.2: Document chosen offset magnitude and affected panels in reports to seed Stage C smoke expectations.
- Phase 1 — Stage C Parameterization & Config Plumbing
  - [ ] P1.1: Extend `RefinementConfig` with Stage C toggles (enable flag, max distance delta, LBFGS hyperparameters mirroring Stage A).
  - [ ] P1.2: Add per-panel detector distance parameters (`distance_offset_raw`) initialized to zero; map via `tanh` to bounded mm offsets (e.g., ±0.5 mm) to guard stability.
  - [ ] P1.3: Allow `create_detector_config` (or downstream hook) to accept tensor overrides for `distance_mm` so gradients propagate during Stage C.
- Phase 2 — LBFGS Integration & Geometry Update
  - [ ] P2.1: Introduce Stage C refinement loop inside `run_nanobrag_refinement` (post Stage A) that optimizes distance offsets while reusing ROI sampling + closure semantics.
  - [ ] P2.2: Rebuild detectors inside the closure with distance overrides applied along panel normals; ensure scale/crystal parameters are frozen (no grad) during Stage C.
  - [ ] P2.3: Guard against invalid distances (e.g., clamp to >0) and capture rollback/early-stop conditions consistent with Stage A tolerances.
- Phase 3 — Telemetry & Output
  - [ ] P3.1: Emit Stage C telemetry with stage label "C", LBFGS metadata, loss traces, and per-panel distance deltas (initial/final/delta arrays, max abs delta, improvement%).
  - [ ] P3.2: Update Stage A telemetry consumers to handle multi-stage output (e.g., map of stages `{ "A": ..., "C": ... }`) without breaking existing tests.
  - [ ] P3.3: Persist final Bragg tensor after Stage C adjustments; include improvement metrics comparing Stage A vs Stage C final loss.
- Phase 4 — Validation & Ledger Updates
  - [ ] P4.1: Author `test_stage_c_detector_microslip` covering deterministic detector offsets, enabling Stage C, asserting ≥0.002% improvement and telemetry completeness.
  - [ ] P4.2: Ensure Stage A smoke remains stable (0.2% gate) when Stage C perturbations are disabled; run collect-only + targeted selectors, archive logs/metrics.
  - [ ] P4.3: Update docs/ledgers (docs/fix_plan.md, docs/findings.md if new guardrails emerge, docs/TESTING_GUIDE.md / TEST_SUITE_INDEX on new selector).

## Mapped Tests (planned)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` — regression guard (0.2% gate, Stage A telemetry)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip` — new Stage C acceptance (≥0.002% improvement, per-panel deltas)
- Optional sanity: `pytest -v tests/dbex/test_nanobrag_bridge_configs.py::TestDetectorConfigRoundtrip::test_detector_model_roundtrip`

## Artifacts
- `plans/active/TORCH-REFINE-003/reports/<YYYY-MM-DDTHHMMSSZ>/`
  - `summary.md`
  - `stage_c_offset_probe.json`
  - `collect_stage_a.log`, `collect_stage_c.log`
  - `pytest_stage_a.log`, `pytest_stage_c.log`
  - `telemetry_stage_c.json`

## How-To (initial)
- `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md`
- `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
- `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip`
- `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip --maxfail=1`

## Status Update (2025-12-08)
**Blocked on:** Stage A gate restoration
- Depends on TORCH-REFINE-002D (xfail removal) and TORCH-REFINE-002E (gradient flow)
- Will unblock once 002D restores ≥0.2% improvement gate

## Next Up (after completion)
- TORCH-REFINE-004 — Stage B Fhkl modifiers once Stage C telemetry is stable.
- Calibration follow-up to widen Stage C to small panel rotations if detector translation proves insufficient.
