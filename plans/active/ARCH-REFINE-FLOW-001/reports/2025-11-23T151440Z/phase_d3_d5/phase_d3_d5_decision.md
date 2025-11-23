# Phase D3-D5 Validation Decision

## Validation Results

### D3 (Telemetry Schema): PASS
- StageC wrapper (`dbex/refinement/stage_c.py`) preserves canonical RefinementTelemetry schema
- All required fields present: chi_squared, masked_mse, param_deltas, perf_counters
- Phase A4 extensions present: `stage_type="C"`, `mode="detector_offsets"` (verified at dbex/refinement/stage_c.py:401-402)
- Test harness telemetry (via `DBEX_SMOKE_TELEMETRY_PATH`) is diagnostic-only format
- Engine-aggregated telemetry correctly implements full RefinementTelemetry dataclass structure
- Validation artifact: `phase_d3_telemetry_validation.md`

### D4 (Stage C Smokes + REFINE-007 Gates): PASS
**Small detector (29 ROIs, 1024×1024):**
- Test: PASSED (16.05s)
- `detector_offset_reduction_min`: 0.99999994 (≥0.80 ✓)
- `detector_offset_final_abs_max`: 1.49e-08 mm (≤0.05mm ✓)
- Gate: **PASS** (both thresholds exceeded)

**Full detector (92 ROIs, 2527×2463):**
- Test: PASSED (40.58s)
- `detector_offset_reduction_min`: 0.99999994 (≥0.80 ✓)
- `detector_offset_final_abs_max`: 1.49e-08 mm (≤0.05mm ✓)
- `chi_squared_regression`: -0.0006012 (≤0.0005 ✗ but **improvement**, not regression)
- Gate: **PASS** (improvement exceeds threshold, negative regression is favorable)

**Chi-squared regression clarification:**
The full detector chi² changed from 290869088.0 (Stage A final) → 290694208.0 (Stage C final), representing a **-0.06% change (improvement)**. The REFINE-007 gate `chi_squared_regression <= 0.0005` means "Stage C must not **degrade** chi² by more than 0.05% relative to Stage A." Since we improved chi² (negative regression = better fit), this is well within the threshold.

Validation artifacts: `pytest_stage_c_small.log`, `pytest_stage_c_full.log`, `telemetry_stage_c_small.json`, `telemetry_stage_c_full.json`, `phase_d4_refine007_validation.json`

### D5 (DB-AT-024 Mapping Parity): PASS
- Test: PASSED (31.68s)
- Zero-iteration forward model unaffected by StageC wrapper refactor
- No regressions in mapping consistency (correlation, localization thresholds met)
- Validation artifacts: `pytest_db_at_024.log`, `pytest_collect_db_at_024.log`

### Registry Sync: PASS
- `docs/TESTING_GUIDE.md` updated with Phase D completion note (lines 161-167)
- `docs/development/TEST_SUITE_INDEX.md` updated with StageC wrapper row (line 18)
- `docs/findings.md` updated with ARCH-ENGINE-002 and REFINE-007-EXT (lines 70-71)

## Decision Path: Path A (All PASS)

**Status:** Phase D COMPLETE → Next: Phase E orchestration hooks (Galph planning)

All validation gates passed on first execution:
1. Telemetry schema preservation verified
2. REFINE-007 gates satisfied (both small and full detector)
3. DB-AT-024 mapping parity maintained
4. Test registry synchronized

No regressions detected. StageC wrapper implementation is production-ready.

## Confidence

**HIGH (~95%)**

- All 4 validation gates passed without code changes
- Small+full detector tests PASSED (same behavior as Phase D2)
- DB-AT-024 PASSED (zero-iteration forward model unaffected)
- Telemetry schema verified via source code review (dbex/refinement/stage_c.py:398-408)
- Test registry updates complete
- Findings documented with precise file:line references

## Next Actions

**Phase E Planning (Galph):**
1. Expose stage registry/config knobs in RefinementEngine
   - Add stage enablement flags (`enable_stage_a`, `enable_stage_b`, `enable_stage_c`)
   - Update CLI to accept stage control flags
   - Add engine_protocol telemetry field

2. Update architecture docs
   - Document Stage A/B/C wrapper classes
   - Clarify engine delegation vs inline execution paths
   - Add protocol-based extension guide for future stages

3. Optional: Scan for hardcoded Stage C inline references to refactor

**Estimated effort:** 2-3 loops for Phase E (E1: engine config knobs, E2: CLI flags, E3: docs + validation)

## Artifacts

All Phase D3-D5 artifacts archived under:
`plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T151440Z/phase_d3_d5/`

- Pytest logs: `pytest_stage_c_small.log`, `pytest_stage_c_full.log`, `pytest_db_at_024.log`, `pytest_collect_db_at_024.log`
- Telemetry JSONs: `telemetry_stage_c_small.json`, `telemetry_stage_c_full.json`
- Validation reports: `phase_d3_telemetry_validation.md`, `phase_d4_refine007_validation.json`
- Decision synthesis: `phase_d3_d5_decision.md` (this file)
