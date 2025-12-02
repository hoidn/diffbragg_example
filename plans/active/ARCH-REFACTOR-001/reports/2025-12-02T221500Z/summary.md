### Turn Summary
Redirected 4 inline imports in test_physics_loss_current.py from facade (dbex.nanobrag_refinement) to canonical module (dbex.physics.loss); all tests passed with no behavioral changes.
Phase D.4 import cleanup complete; facade re-exports no longer used by physics loss tests.
Next: Phase D.3 Batch 2 (test_stage_a_smoke_parity.py migration) or Phase D.5 (facade deletion).
Artifacts: plans/active/ARCH-REFACTOR-001/reports/2025-12-02T221500Z/ (pytest_phase_d4.log, import_verification.txt)

---

## Implementation Notes

**File:** `tests/dbex/test_physics_loss_current.py`

**Changes:**
- Updated 4 inline imports (lines 63, 125, 160, 207)
- Old path: `dbex.nanobrag_refinement`
- New path: `dbex.physics.loss`
- Function name unchanged: `_compute_variance_weighted_loss`

**Validation:**
- All 4 tests PASSED (0.90s runtime)
- Zero remaining facade imports confirmed
- No behavioral changes (function signature/behavior unchanged since Phase A.3)

**Metrics:**
- Import paths redirected: 4/4
- Tests validated: 4/4
- Files touched: 1
- Net change: 0 lines (same import statement length)
