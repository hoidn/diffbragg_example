# A1 — Dataset Availability

## Asset Verification (2025-12-08)

```
-rw-rw-r-- 1 ollie ollie 5.1K Oct 28 16:17 refGeom.expt
-rw-rw-r-- 1 ollie ollie 202K Oct 28 16:10 refGeom.refl
-rw-rw-r-- 1 ollie ollie 2.8M Oct 28 15:39 scaled.mtz
```

**Status**: ✅ All refGeom assets present at repo root

- `refGeom.expt` — 5.1K (experiment geometry)
- `refGeom.refl` — 202K (reflection table)
- `scaled.mtz` — 2.8M (scaled intensities)

## Skip Behavior

DB-AT-020 tests will skip if `refGeom.refl` is absent (mirror smoke fixture guard per implementation.md A1). This design ensures test execution fails gracefully when canonical datasets are unavailable, matching pytest convention for data-dependent acceptance tests.

## Cross-references

- Validated per DB-AT-SUITE-CARE-001 Phase B.2 (`reports/2025-12-08T020000Z/`) — refGeom asset validation (VALID ✓)
- Workspace root: `/home/ollie/Documents/diffbragg_example_2/diffbragg_example`
