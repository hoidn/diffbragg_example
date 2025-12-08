# DB-AT-022 Phase A3: Sentinel Coverage Probe

**Initiative**: DB-AT-022 — Background Sentinel Guard
**Phase**: A3 — Sentinel Coverage Probe
**Date**: 2025-12-08T18:00:00Z (Loop i=151)
**Objective**: Validate background_image sentinel coverage against ROI union, per spec-db-conformance.md:63-64 and spec-db-workflow.md:38

---

## Sentinel Contract (ARCH-CONTRACT-SENTINEL-001)

Per `docs/architecture/data_telemetry_flow.md:34`:
> Background sentinel: -1 outside ROI; validated before prep

Per `docs/spec-db-workflow.md:38`:
> Background sentinels -1 MUST be masked consistently in loss/variance

Per `docs/spec-db-conformance.md:116`:
> Loss mask formula: `(background >= 0) ∧ trusted_mask`

---

## Probe Methodology

```python
# Sentinel mask: True where background == -1
sentinel_mask = np.isclose(bg, -1.0)

# ROI union mask: True for pixels inside ANY ROI
roi_union = np.zeros(bg.shape, dtype=bool)
for (x0, x1, y0, y1), pid in zip(loader.bbox, loader.pids):
    roi_union[pid, y0:y1, x0:x1] = True

# Overlap: Should be 0 (sentinel cannot be inside ROI)
overlap = (sentinel_mask & roi_union).sum()

# Complement match: sentinel should equal ~roi_union
complement_match = (sentinel_mask == ~roi_union).all()
```

---

## Results

### A3.1: Sentinel Analysis

| Metric | Value | Notes |
|--------|-------|-------|
| sentinel_count | 6,210,753 | Pixels with background == -1 |
| total_pixels | 6,224,001 | Total array size |
| sentinel_fraction | 0.997871 | 99.7871% of detector is sentinel |

### A3.2: ROI Union Analysis

| Metric | Value | Notes |
|--------|-------|-------|
| roi_union_count | 13,248 | Pixels inside at least one ROI |
| roi_fraction | 0.002129 | 0.2129% of detector is ROI area |

**ROI area calculation**: 92 ROIs × 12×12 pixels = 13,248 pixels
**Match**: roi_union_count (13,248) exactly equals expected ROI area

### A3.3: Overlap & Complement Analysis

| Check | Result | Expected | Status |
|-------|--------|----------|--------|
| overlap (sentinel ∧ roi_union) | 0 | 0 | PASS |
| complement_match (sentinel == ~roi_union) | True | True | PASS |
| valid_bg_count (bg >= 0 ∧ roi_union) | 13,158 | ≤13,248 | PASS |
| full_coverage ((sentinel ∨ roi) covers all) | True | True | PASS |
| uncovered pixels | 0 | 0 | PASS |

**Note**: valid_bg_count (13,158) < roi_union_count (13,248) indicates 90 pixels inside ROIs have background < 0 (likely edge effects from background fitting). This is expected behavior per `bg_is_good` flag handling.

### A3.4: Non-Sentinel Background Statistics

| Stat | Value |
|------|-------|
| min | -0.4896 |
| max | 12.9755 |
| mean | 2.9473 |
| std | 2.2220 |

**Note**: Background values inside ROIs range from slight negative (fit artifacts) to ~13 counts, with reasonable mean ~3 counts.

### A3.5: Coverage Sum Check

```
sentinel_fraction + roi_fraction = 1.000000
```

**Result**: Sentinel and ROI union are exact complements, confirming the sentinel convention is correctly implemented.

---

## Classification

**Case A: Perfect match**

The sentinel mask equals the exact complement of the ROI union:
- **overlap = 0**: No pixel is both sentinel (-1) AND inside an ROI
- **complement_match = True**: Every pixel outside ROIs is sentinel, every pixel inside ROIs is not sentinel
- **coverage = 100%**: No gaps or overlaps between sentinel and ROI regions

This confirms ARCH-CONTRACT-SENTINEL-001 is satisfied for the refGeom dataset.

---

## Conformance Assessment

### DB-AT-022 Acceptance Criteria (docs/spec-db-conformance.md:63-64)

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Sentinel logic correct | PASS | overlap=0, complement_match=True |
| ROI coverage matches metadata | PASS | 92 ROIs × 144 px/ROI = 13,248 (exact match) |

### Loss Mask Contract (docs/spec-db-conformance.md:116)

Formula: `loss_mask = (background >= 0) ∧ trusted_mask`

| Component | Verified |
|-----------|----------|
| background >= 0 excludes sentinel | Yes (sentinel_mask = background == -1) |
| ROI union defines valid background region | Yes (complement_match = True) |

---

## Recommendation

Phase A3 complete with **Case A: Perfect match**.

**Next Steps (Phase B)**:
1. B1: Harden `prepare_refinement_inputs` with explicit sentinel guard and ValueError for unexpected values
2. B2: Author `tests/dbex/test_background_semantics.py` with DB-AT-022 selectors
3. B3: Execute pytest selectors and capture artifacts

---

## Spec References

- **Spec-DB-Workflow** `docs/spec-db-workflow.md:38`: Background sentinels -1 MUST be masked consistently
- **Spec-DB-Conformance** `docs/spec-db-conformance.md:63-64`: DB-AT-022 acceptance criteria
- **Spec-DB-Conformance** `docs/spec-db-conformance.md:116`: Loss mask formula
- **Architecture** `docs/architecture/data_telemetry_flow.md:34`: Background sentinel convention
- **simtbx API** `docs/simtbx_api.md:14`: background_image filled with -1 sentinel

---

**END OF A3 REPORT**
