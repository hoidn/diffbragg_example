# ARCH-SIM-CONSTRUCTION-001 Loop Summary — 2025-12-15T150000Z

## Cache Implementation Complete

Implemented zero-iteration Bragg stack caching to align `bragg_before` with Stage A telemetry per input.md Do Now.

### Changes Made

1. **StageAContext** (dbex/refinement/context.py:933-936, 959)
   - Added optional `bragg_zero_iter` field (np.ndarray, float32 CPU copy)
   - Carries sqrt-scaled baseline Bragg array from warm-cache baseline derivation
   - Default `None` preserves backward compatibility

2. **stage_a.py:446-454** — Cache population
   - After computing `bragg_stack_scaled = bragg_stack * sqrt_spot_scale`
   - Stash CPU float32 copy: `stage_a_ctx.bragg_zero_iter = bragg_stack_scaled.detach().cpu().numpy().astype(np.float32)`
   - Guarded with try/except so cold-mode contexts remain valid

3. **reconstruction.py:80-86** — Cache reuse fast-path
   - Detect cache hit: `param_state=="initial"` + `stage_a_ctx.bragg_zero_iter` populated
   - Return `np.array(stage_a_ctx.bragg_zero_iter, copy=True)` instead of rerunning simulators
   - Log cache hit for diagnostics: "[ARCH-SIM-CONSTRUCTION-001 CACHE HIT]"

4. **test_artifact_parity.py:363-489** — Coverage test
   - New test: `test_stage_a_cached_zero_iter_bragg_matches_initial_reconstruction`
   - Validates cache population after Stage A run
   - Asserts reconstruction helper exactly matches cached array for param_state="initial"

### Validation Results

**Baseline probe** (`stage_a_baseline_probe.json`):
- **CACHE HIT** working correctly
- `model_mean_masked` ratio = **1.000000** (exact parity!)
- Telemetry vs reconstructed bragg_before: perfect match

**DB-AT-028/029 tests** (`pytest_db_at_028_029.log`):
- Cache hit confirmed in logs (shape=(1, 1024, 1024))
- Tests still **FAIL** with same signature:
  - chi²/pixel initial = 209,715 (vs ≤1e2 spec)
  - median ROI correlation before = -0.053 (vs ≥0.2 floor)

**New coverage test**:
- Collectible via `pytest --collect-only tests/dbex/test_artifact_parity.py::test_stage_a_cached_zero_iter_bragg_matches_initial_reconstruction`

### Key Finding

Cache implementation is **working as designed** — `bragg_before` now matches Stage A telemetry exactly (ratio=1.0).

However, DB-AT-028/029 failure signature remains unchanged, suggesting:
- The underlying chi²/ROI issues are **NOT** due to `bragg_before` reconstruction parity
- Failures reflect deeper spec/harness/test expectations requiring separate investigation

### Recommendation

**Escalate to spec_change/harness investigation initiative.**

Parity is now achieved between Stage A telemetry and reconstruction, but tests remain far from acceptance criteria. This suggests the problem lies in:
- Test expectations (spec-db-conformance.md criteria may need revision)
- Test harness setup (fixture/mask/calibration differences)
- Spec alignment (physics model vs test gates mismatch)

### Artifacts

- `baseline_probe.log` — Cache hit + ratio=1.0 evidence
- `pytest_db_at_028_029.log` — Tests still fail despite cache
- `db_at_028_metrics.json` — chi²=209,715, cache_hit=true
- `db_at_029_metrics.json` — median_corr=-0.053, cache_hit=true

### Commits

- **10377521** — Cache implementation (4 files: context.py, stage_a.py, reconstruction.py, test_artifact_parity.py)
- **aee3385c** — fix_plan.md update with attempt entry

### References

- SCALE-009 (reconstruction baseline alignment)
- SCALE-008 (Stage A warm-cache authority)
- ARCH-SIM-CONSTRUCTION-001 input.md Do Now items 1-4
