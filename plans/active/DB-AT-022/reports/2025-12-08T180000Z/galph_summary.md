# DB-AT-022 Phase A — Galph Planning Summary

**Loop**: i=151 (Galph)
**Date**: 2025-12-08T18:00:00Z
**Action**: planning
**DecisionStatus**: exploring

---

## Focus Selection

Selected DB-AT-022 Phase A (Background Sentinel Guard) from DB-AT-SUITE-CARE-001 Phase B.4 member plan coordination.

**Portfolio Status**:
- DB-AT-020: ✅ Complete (Phase C done i=147)
- DB-AT-021: ✅ Complete (Phase C done i=150)
- DB-AT-022: ⏳ Phase A starting (this loop)
- DB-AT-023: ⏳ Pending
- DB-AT-024: ⏳ Phase A complete, Phase B pending

**Tier 0 Status**: ARCH-GRADIENT-FLOW-001 blocked_pending_environment (i=141 lifecycle decision)

---

## Phase A Scope

### A1 — Asset Validation
Cross-reference i=143 Phase B.2 asset validation (refGeom.expt, refGeom.refl, scaled.mtz, 747_mask.pkl).

### A2 — Baseline Metrics Capture
Instantiate DataLoad, capture data/background shapes, ROI count, bbox sample dimensions.

### A3 — Sentinel Coverage Probe
Compute sentinel mask (`background == -1`), ROI union mask, analyze overlap/complement relationship.

**Expected Outcomes**:
- 4/4 assets VALID
- DataLoad instantiates without error
- Sentinel mask == complement of ROI union (overlap == 0)

---

## Spec References

- `docs/spec-db-workflow.md:38` — Background sentinels −1 MUST be masked consistently
- `docs/spec-db-conformance.md:63-64` — DB-AT-022 acceptance: sentinel logic correct, ROI coverage matches metadata
- `docs/simtbx_api.md:14` — background_image filled with −1 sentinel for invalid pixels

---

## ARCH Contract

**ARCH-CONTRACT-SENTINEL-001**: Background sentinel convention
- Owner: `dbex.data_load.DataLoad` + simtbx `get_roi_background_and_selection_flags`
- Contract: −1 sentinel outside ROIs; `loss_mask = (background >= 0) ∧ trusted_mask`

---

## Artifacts

`plans/active/DB-AT-022/reports/2025-12-08T180000Z/`
- `galph_summary.md` — This file
- `asset_availability.md` — A1 deliverable (Ralph)
- `baseline_metrics.md` — A2 deliverable (Ralph)
- `sentinel_probe.md` — A3 deliverable (Ralph)
- `summary.md` — Phase A completion notes (Ralph)

---

## Next Action

Ralph executes Phase A (i=151): asset cross-ref, DataLoad instantiation, sentinel coverage probe.
Expected 4 artifacts. Phase B scoping in summary.md.
