# Loop i=112 Planning: Phase B.3-B.4 Refactor

## Turn Summary

Planned Phase B.3-B.4 refactor to eliminate duplicated sqrt(spot_scale_override) scaling logic in Stage A and reconstruction by delegating to canonical `apply_sqrt_spot_scale` API. Delegated to Ralph with mapped tests expecting cold-path enforcement test to PASS (improvement from 64.7% rel_error to <0.0001%).

Artifacts: plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T020000Z/phase_b3_b4_planning.md, input.md

---

## Context

Phase B.1-B.2 complete (loop i=111):
- Canonical API delivered: `dbex.refinement.scaling_utils.apply_sqrt_spot_scale` (11/11 unit tests PASS)
- `calibration_metadata` parameter threaded to reconstruction signature
- Warm-cache regression PASSED (Phase A.1)
- Cold-path baseline FAILED as expected (Phase A.2: 64.7% rel_error, 2.83x scale factor drift)

## Phase B.3-B.4 Scope

**Refactor Stage A** (dbex/refinement/stage_a.py:438-444):
- Replace duplicated sqrt extraction logic with `apply_sqrt_spot_scale` call
- Requires torch↔numpy conversion (canonical API is numpy-only)
- Identity refactor: preserve device/dtype, no behavior change

**Refactor Reconstruction** (dbex/refinement/reconstruction.py:213-221):
- Delete duplicated sqrt extraction logic (lines 217-221)
- Replace `* sqrt_spot_scale` multiplication sites with canonical API calls
- Apply API at final multiplication site (after scale_factor × baseline_alignment_factor)

## Mapped Tests

1. **Phase A.1** (warm-cache regression): `test_stage_a_vs_reconstruction_scale` → expect PASS
2. **Phase A.2** (cold-path validation): `test_stage_a_vs_reconstruction_scale_cold_path` → expect PASS (was 64.7% rel_error)
3. **Stage A smoke**: `test_stage_a_smoke_parity` → expect PASS (no regression)

## Expected Outcomes

- Phase A.1: PASS (no behavior change, warm-cache uses Stage A artifacts)
- Phase A.2: PASS (rel_error drop from 64.7% to <0.0001% via canonical API parity)
- Stage A smoke: PASS (identity refactor)

## Next Actions

If Phase A.2 PASSES after refactor:
- Phase B.5: Update docs (findings.md SCALE-008/009, TESTING_GUIDE.md, TEST_SUITE_INDEX.md)
- Phase B.6: Consider ARCH-CONTRACT-003 validation (Mapping → Stage A baseline override)

If Phase A.2 still FAILS:
- Phase B.5: Audit call sites, update to pass `calibration_metadata` explicitly
- Investigate remaining discrepancies in cold-path reconstruction logic

## Risks

- Torch↔numpy conversion overhead in Stage A hot path (mitigated: occurs once per run, not per LBFGS step)
- Cold-path complexity: multiple interleaved scale factors (mitigated: apply canonical API at final site only)
- Call sites not passing `calibration_metadata` yet (mitigated: falls back to `config.calibration_metadata`)

## Cross-References

- **Planning**: phase_b3_b4_planning.md
- **Phase B.1-B.2 Summary**: ../2026-01-14T000000Z/summary.md
- **Implementation Plan**: ../../implementation.md
- **galph_memory**: /home/ollie/Documents/diffbragg_example/galph_memory.md:1-8
