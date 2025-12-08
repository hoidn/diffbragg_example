# DB-AT-023 Phase A — Summary

**Initiative**: DB-AT-023 (Calibration Policy Guard — ADU vs Photons)
**Loop**: i=153 (Ralph)
**Date**: 2025-12-08T02:21:01Z
**Mode**: Parity
**ActionType**: planning
**DecisionStatus**: exploring
**InitiativeType**: harness

---

## Phase A Completion Status

| Task | Status | Artifact |
|------|--------|----------|
| A1: Asset Availability Check | COMPLETE | `asset_availability.md` |
| A2: Baseline Metrics Capture | COMPLETE | `baseline_metrics.md` |
| A3: Calibration Policy Summary | COMPLETE | `calibration_policy_summary.md` |

---

## Key Findings

### A1: Asset Availability
- All 4 canonical assets VALID (cross-referenced from i=143 validation)
- No blockers for DB-AT-023 Phase B implementation

### A2: Baseline Metrics
- 92 ROIs extracted, 13,158 pixels
- No sigma_readout_map loaded (Phase B must exercise sigma sourcing paths)
- No torch_config provided (current baseline uses implicit ADU mode)
- Background-subtracted ROI mean: 62.66 ADU

### A3: Calibration Policy
- Unit mode: ADU (no `--adu-per-photon` flag exists yet)
- Precedence ladder: torch_config → CLI → external_lookup → MTZ → defaults
- Conflict resolution: Run SHALL fail when torch_config and CLI disagree
- Required fields: `spot_scale_override`, `sigma_floor`, `sigma_readout`

---

## Phase B Scoping Notes

Phase B (Implementation & Testing) must deliver:

### B1: CLI Extension
- Add `--adu-per-photon` flag to `dbex/refine_one.py::create_parser`
- Thread value to `DataLoad` and `prepare_refinement_inputs`
- Estimated LOC: ~20-30

### B2: Photon Conversion Path
- Update `dbex/nanobrag_bridge.py::prepare_refinement_inputs`
- Convert target/sigma when `adu_per_photon > 0`
- Surface `unit_mode` and `gain` in telemetry
- Estimated LOC: ~50-80

### B3: Test Fixtures
- Create `tests/dbex/test_calibration_policy.py`
- Test cases: photon conversion, ADU path, invalid gain guardrail, precedence conflict
- Use baseline metrics for assertions (92 ROIs, ~63 ADU mean)
- Estimated LOC: ~100-150

### B4: Test Execution
- `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_calibration_policy.py -k DB_AT_023`
- `pytest --collect-only tests -k DB_AT_023`

---

## ARCH Contract Alignment

| Contract | Status | Phase B Action |
|----------|--------|----------------|
| ARCH-CONTRACT-CALIBRATION-001 | Conforms | Document in enforcement test |
| ARCH-CONTRACT-UNIT-MODE-001 | Partially exists | Implement `--adu-per-photon` |
| ARCH-CONTRACT-SIGMA-001 | Conforms | No action needed |

---

## Findings Applied

- **TESTING-003**: Registry updates will occur in Phase C after test authoring
- **RUNTIME-001**: Environment flags documented for Phase B test commands
- **DIAGNOSTICS-001**: Artifact structure follows standard pattern

---

## Next Actions

1. **Phase B.1**: Implement `--adu-per-photon` CLI flag (Ralph next loop)
2. **Phase B.2**: Update `prepare_refinement_inputs` with photon conversion
3. **Phase B.3**: Author test fixtures using baseline metrics
4. **Phase B.4**: Execute mapped pytest commands
5. **Phase C**: Registry sync after tests pass

---

### Turn Summary

Executed DB-AT-023 Phase A (Calibration Policy Guard reality check). Confirmed all 4 canonical assets VALID via i=143 cross-reference. Captured baseline metrics: 92 ROIs, no sigma_readout_map loaded, implicit ADU mode. Summarized calibration policy from spec-db-workflow.md: unit mode selection, precedence ladder, conflict guardrails. Phase B scoped for CLI extension (`--adu-per-photon`), photon conversion path, and test fixtures.

Artifacts: `plans/active/DB-AT-023/reports/2025-12-08T022101Z/` (`asset_availability.md`, `baseline_metrics.md`, `calibration_policy_summary.md`, `summary.md`)
