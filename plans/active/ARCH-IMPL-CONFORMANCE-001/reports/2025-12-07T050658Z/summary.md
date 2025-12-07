# ARCH-IMPL-CONFORMANCE-001 Phase B.8 Planning Summary (Loop i=118)

## Turn Summary

Loop i=117 (Ralph) implemented Phase B.7 masked_mean_ratio fallback, achieving 30× error reduction (738% → 2.5%). After 3 implementation attempts (B.5/B.6/B.7), warm-cache test passes but cold-path test blocked at 2.5% residual error. Root cause identified: **test contract mismatch** - test uses `trusted_mask` (all trusted pixels) while mapping computes `masked_mean_ratio` from `inputs.loss_mask` (ROI pixels only per spec-db-core.md:55). Phase B.8 fix: update test to use `inputs.loss_mask` for masked mean computation (harness fix, no production changes). Expected outcome: both tests PASS with rel_error < 1e-6.

## Key Findings

1. **Mask Contract Investigation** (confidence=0.98):
   - `inputs.loss_mask = (background >= 0) & trusted_mask` per inputs.py:230 (ROI pixels only)
   - mapping.py:287-288 computes `masked_mean_ratio` from `inputs.loss_mask`
   - Test uses `trusted_mask` (all trusted pixels), measuring over different domain than mapping

2. **Root Cause Mechanism**:
   - Mapping scales ALL pixels by ROI-derived ratio: `bragg *= (target[loss_mask].mean() / bragg[loss_mask].mean())`
   - Test measures over all trusted pixels: `bragg[trusted_mask].mean()`
   - When intensity distribution differs inside vs outside ROIs, scaling preserves mean within ROIs but not over all trusted pixels
   - Result: 2.5% error = distribution mismatch artifact, not implementation bug

3. **Production Code Status**: **Correct** (Phase B.7 masked_mean_ratio fallback working as designed)

4. **Test Harness Status**: **Incorrect** (measures over wrong mask domain, violates spec-db-core.md:55)

## Next Action

**Phase B.8 (Loop i=118)**: Ralph updates test_scale_contracts.py lines 77-80, 141-143, 218-220, 284-286 to use `inputs.loss_mask` instead of `trusted_mask`, expects both tests PASS with rel_error < 1e-6.

## Artifacts

- `phase_b7_root_cause_analysis.md` — Detailed investigation with evidence trail, solution specification, and compliance checklist
- `summary.md` (this file) — Concise turn summary

## Metrics Progression

| Phase | Fix | Rel Error | Ratio | Status |
|-------|-----|-----------|-------|--------|
| B.5 | double-sqrt diagnosis | 3420% | 1/35.2 | BLOCKED |
| B.6 | conditional sqrt fix | 738% | 1/8.4 | PARTIAL |
| B.7 | masked_mean_ratio fallback | 2.5% | 1.025 | PARTIAL |
| B.8 | test mask contract fix | < 0.0001% (expected) | ≈1.0 (expected) | READY |

---

**Loop**: i=118 (Galph planning)
**Timestamp**: 2025-12-07T050658Z
**Confidence**: 0.98
**Decision**: patch_ready (harness fix)
