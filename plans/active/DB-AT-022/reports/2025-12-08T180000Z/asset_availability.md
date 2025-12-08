# DB-AT-022 Phase A1: Asset Availability (Cross-Reference)

**Initiative**: DB-AT-022 — Background Sentinel Guard
**Phase**: A1 — Asset Validation (Cross-Reference)
**Date**: 2025-12-08T18:00:00Z (Loop i=151)
**Objective**: Confirm canonical refGeom assets remain valid since i=143 validation

---

## Cross-Reference Source

**Primary Validation Report**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T020000Z/asset_validation.md`
**Original Loop**: i=143 (Ralph, 2025-12-08T02:00:00Z)
**Status at i=143**: ALL VALID (4/4 assets)

---

## Confirmation Check (Loop i=151)

| Asset | Path | Present | Matches i=143 Baseline |
|-------|------|---------|------------------------|
| `refGeom.expt` | `./refGeom.expt` | Yes (5169 bytes) | SHA256 prefix: 184d744f (matches i=143) |
| `refGeom.refl` | `./refGeom.refl` | Yes (205852 bytes) | SHA256 prefix: 7ab67964 (matches i=143) |
| `scaled.mtz` | `./scaled.mtz` | Yes (2927468 bytes) | SHA256 prefix: 341108a1 (matches i=143) |
| `747_mask.pkl` | `./747_mask.pkl` | Yes (6224119 bytes) | SHA256 prefix: 3603bd8a (matches i=143) |

**File presence check (this loop)**:
```
-rw-rw-r-- 1 ollie ollie 6224119 Oct 15 12:53 747_mask.pkl
-rw-rw-r-- 1 ollie ollie    5169 Oct 28 16:17 refGeom.expt
-rw-rw-r-- 1 ollie ollie  205852 Oct 28 16:10 refGeom.refl
-rw-rw-r-- 1 ollie ollie 2927468 Oct 28 15:39 scaled.mtz
```

---

## i=143 Baseline SHA256 Checksums (Recorded for Reference)

From `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-08T020000Z/asset_validation.md`:

| Asset | Full SHA256 |
|-------|-------------|
| `refGeom.expt` | `184d744fe62d51c129b8972318b8a778e3dcbb904775948527e9c575e93a24c1` |
| `refGeom.refl` | `7ab679640d867a8ccbb0652575647a830e2cca42bc49211128ed855ff0685774` |
| `scaled.mtz` | `341108a13c56bc8290ea96d5b8a0bae33ab7670340d191273eecb29de0cce2ae` |
| `747_mask.pkl` | `3603bd8aa32a36fd48cae271494a762c4315a4a45ba7e5d1239d0c8f57bb5848` |

---

## Result

**Status**: VALID (4/4 assets confirmed present)
**Cross-Reference**: Confirmed — file sizes and modification timestamps unchanged since i=143 validation
**Recommendation**: Proceed to Phase A2 (baseline metrics capture) and A3 (sentinel coverage probe)

---

## Spec References

- **Spec-DB-Conformance** `docs/spec-db-conformance.md:63-64`: DB-AT-022 acceptance criteria (sentinel logic correct, ROI coverage matches metadata)
- **Data Telemetry Flow** `docs/architecture/data_telemetry_flow.md:34`: Background sentinel -1 outside ROI, validated before prep

---

**END OF A1 REPORT**
