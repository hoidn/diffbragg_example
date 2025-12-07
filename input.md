# Loop i=117 — ARCH-IMPL-CONFORMANCE-001 Phase B.7 Implementation

## Summary
Fix residual 8.4× scale mismatch in reconstruction cold path by applying masked_mean_ratio from calibration_metadata when telemetry lacks model_mean_masked.

## Mode
none

## ActionType
implementation_ready

## DecisionStatus
patch_ready

## InitiativeType
architecture

## Focus
ARCH-IMPL-CONFORMANCE-001 — Architecture / Implementation Contract Alignment (Phase B.7: masked_mean_ratio fallback)

## Branch
integration

## Mapped Tests
- `tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale` (warm-cache regression, expect PASS)
- `tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path` (cold-path enforcement, expect PASS after fix, currently 738% rel_error)

## Artifacts
`plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T140000Z/`

## Findings Applied (Mandatory)
- **SCALE-008** (warm-cache authority, masked-intensity baseline for Stage A) — adhered: warm-cache test already passes per Phase A.1
- **SCALE-009** (reconstruction scaling provenance) — **correction in progress**: Phase B.6 fixed double-sqrt (35× → 8.4×), Phase B.7 fixes masked_mean_ratio omission (8.4× → ~1.0)
- **ARCH-FACTORY-001** (unified simulator factory responsibilities) — adhered: reconstruction cold path uses create_unified_simulator per factory contract
- **PROBE-FREEZE-001** (probe freeze & logging consolidation) — adhered: no new plan-local probes, implementation changes production code only

## Pointers
- **Spec**: `docs/spec-db-core.md` §§20-40 (simulator construction, calibration threading)
- **Architecture**: `docs/architecture/calibration_scaling.md` (masked_mean_ratio provenance, baseline_alignment_factor semantics)
- **Implementation**:
  - `dbex/vis/mapping.py:297-312` (masked_mean_ratio computation and storage in calibration dict)
  - `dbex/refinement/reconstruction.py:418-471` (baseline_alignment_factor computation, currently telemetry-only)
  - `dbex/refinement/reconstruction.py:511` (scale application site)
- **Test**: `tests/architecture/test_scale_contracts.py:165-290` (cold-path enforcement test, minimal telemetry fixture)
- **Evidence**: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T120000Z/blocked_analysis.md` (Ralph's Phase B.6 analysis)

## ARCH Contracts (Mandatory)

### ARCH-CONTRACT-001: Stage A vs Reconstruction Scaling Alignment
- **Owner module**: `dbex.refinement.scaling_utils` (canonical `apply_sqrt_spot_scale` function)
- **Owner API**: `apply_sqrt_spot_scale(bragg_np, calibration_metadata)` — applies sqrt(spot_scale_override) when present
- **Contract**: Given identical geometry, calibration_metadata, and param_state="initial", Stage A warm-cache forward and reconstruction cold path must agree on scale and trusted-mask handling within 1e-6 relative tolerance.
- **Failure classification**: **Implementation bug** (architectural contract is correct, reconstruction cold path missing masked_mean_ratio application from calibration_metadata)
- **Enforcement**: `tests/architecture/test_scale_contracts.py` (Phase A.1 warm-cache, Phase A.2 cold-path)
- **Current status**: Phase A.1 PASS (warm-cache parity via cache optimization), Phase A.2 FAIL (738% rel_error, 8.4× ratio after Phase B.6 partial fix)

### ARCH-CONTRACT-002: Calibration Metadata Threading & Scaling Pattern
- **Owner module**: `dbex.vis.mapping` (builds MappingStageAContext with masked_mean_ratio adjustment)
- **Owner API**: `build_mapping_stage_a_context(dataload, ...)` — produces bragg_zero_iter with masked_mean_ratio applied (mapping.py:297-300)
- **Contract**: masked_mean_ratio from mapping phase must be persisted in calibration_metadata and applied by all downstream consumers (Stage A warm-cache, reconstruction cold path) to maintain target-to-bragg alignment.
- **Failure classification**: **Implementation bug** (contract defined correctly in mapping.py:312, but reconstruction cold path doesn't consume it as fallback when telemetry lacks model_mean_masked)
- **Remediation**: Add masked_mean_ratio fallback extraction from calibration_metadata at reconstruction.py:454-467 (before baseline_alignment_factor computation)

## Do Now (hard validity contract)

### Context
Loop i=116 (Ralph) implemented Phase B.6 conditional sqrt scaling fix, achieving 4.17× improvement (ratio 1/35 → 1/8.4) but cold-path test still fails with 738% relative error.

**Root cause analysis** (Galph i=117):
1. Ralph's fix correctly eliminated double-sqrt scaling (Phase B.5 → B.6)
2. Residual 8.4× mismatch is due to **missing masked_mean_ratio adjustment** from mapping phase
3. `build_mapping_stage_a_context` applies `masked_mean_ratio = target_mean_masked / bragg_mean_masked` at mapping.py:297-300
4. This ratio is stored in `calibration_metadata["masked_mean_ratio"]` at mapping.py:312
5. Stage A warm-cache path uses cached `bragg_zero_iter` which already has this ratio baked in
6. Reconstruction cold path computes `baseline_alignment_factor` from telemetry at reconstruction.py:454-467, BUT test provides minimal telemetry without `model_mean_masked`
7. When `telemetry_model_mean_masked` is None, `baseline_alignment_factor` defaults to 1.0, skipping the adjustment
8. **Expected outcome**: reconstruction should fall back to `calibration_metadata["masked_mean_ratio"]` when telemetry lacks complete scaling provenance

**Evidence**:
- Phase B.6 test log (pytest_phase_b6_fix.log:37-40): `masked_mean_stage_a=0.999`, `masked_mean_reconstruction_cold=8.377`, `rel_error=7.38`, `ratio=0.119`
- Mapping code (mapping.py:297-312): computes and stores `masked_mean_ratio` in calibration dict
- Reconstruction code (reconstruction.py:454-467): only checks `telemetry_a.model_mean_masked`, doesn't fall back to calibration_metadata
- Test fixture (test_scale_contracts.py:226-239): creates minimal telemetry with zero_deltas only, no `model_mean_masked` field

### Implementation Steps

**Implement**: `dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry`

**Change**: Add masked_mean_ratio fallback extraction from calibration_metadata in baseline_alignment_factor computation logic (lines 454-467)

**Before** (lines 448-467):
```python
# Step 3: Extract telemetry model_mean_masked
telemetry_model_mean = None
if telemetry_a is not None:
    if hasattr(telemetry_a, 'model_mean_masked'):
        telemetry_model_mean = float(telemetry_a.model_mean_masked) if telemetry_a.model_mean_masked is not None else None

# Step 4: Compute baseline_alignment_factor when both are finite/positive
if (telemetry_model_mean is not None and telemetry_model_mean > 0 and
    cold_masked_mean > 0 and np.isfinite(telemetry_model_mean) and np.isfinite(cold_masked_mean)):
    baseline_alignment_factor = telemetry_model_mean / cold_masked_mean
    print(f"[ARCH-SIM-CONSTRUCTION-001 Phase C.14] Cold-path baseline alignment:")
    print(f"  telemetry_model_mean_masked: {telemetry_model_mean:.6e}")
    print(f"  cold_masked_mean (before alignment): {cold_masked_mean:.6e}")
    print(f"  baseline_alignment_factor: {baseline_alignment_factor:.6f}")
else:
    # Emit warning if alignment cannot be computed
    print(f"[ARCH-SIM-CONSTRUCTION-001 Phase C.14 WARNING] Cannot compute baseline alignment:")
    print(f"  telemetry_model_mean_masked: {telemetry_model_mean}")
    print(f"  cold_masked_mean: {cold_masked_mean if inputs.loss_mask is not None else 'N/A (no loss_mask)'}")
    baseline_alignment_factor = 1.0
```

**After** (lines 448-480, expanded):
```python
# Step 3: Extract telemetry model_mean_masked
telemetry_model_mean = None
if telemetry_a is not None:
    if hasattr(telemetry_a, 'model_mean_masked'):
        telemetry_model_mean = float(telemetry_a.model_mean_masked) if telemetry_a.model_mean_masked is not None else None

# Step 4: Compute baseline_alignment_factor when both are finite/positive
if (telemetry_model_mean is not None and telemetry_model_mean > 0 and
    cold_masked_mean > 0 and np.isfinite(telemetry_model_mean) and np.isfinite(cold_masked_mean)):
    baseline_alignment_factor = telemetry_model_mean / cold_masked_mean
    alignment_source = "telemetry_model_mean_masked"
    print(f"[ARCH-SIM-CONSTRUCTION-001 Phase C.14] Cold-path baseline alignment:")
    print(f"  telemetry_model_mean_masked: {telemetry_model_mean:.6e}")
    print(f"  cold_masked_mean (before alignment): {cold_masked_mean:.6e}")
    print(f"  baseline_alignment_factor: {baseline_alignment_factor:.6f}")
    print(f"  source: {alignment_source}")
elif effective_calibration_metadata is not None and "masked_mean_ratio" in effective_calibration_metadata:
    # ARCH-CONTRACT-002 Phase B.7: Use masked_mean_ratio from mapping phase as fallback
    # When telemetry doesn't provide model_mean_masked (e.g., minimal test fixtures),
    # fall back to masked_mean_ratio from build_mapping_stage_a_context (mapping.py:297-312).
    # This ensures reconstruction cold path aligns with mapping's target-to-bragg adjustment.
    masked_mean_ratio = effective_calibration_metadata.get("masked_mean_ratio")
    if masked_mean_ratio is not None and masked_mean_ratio > 0 and np.isfinite(masked_mean_ratio):
        baseline_alignment_factor = masked_mean_ratio
        alignment_source = "calibration_masked_mean_ratio"
        print(f"[ARCH-CONTRACT-002 Phase B.7] Cold-path baseline alignment from calibration:")
        print(f"  masked_mean_ratio (from mapping): {masked_mean_ratio:.6e}")
        print(f"  baseline_alignment_factor: {baseline_alignment_factor:.6f}")
        print(f"  source: {alignment_source}")
    else:
        # Emit warning if alignment cannot be computed
        print(f"[ARCH-SIM-CONSTRUCTION-001 Phase C.14 WARNING] Cannot compute baseline alignment:")
        print(f"  telemetry_model_mean_masked: {telemetry_model_mean}")
        print(f"  cold_masked_mean: {cold_masked_mean if inputs.loss_mask is not None else 'N/A (no loss_mask)'}")
        print(f"  calibration masked_mean_ratio: {effective_calibration_metadata.get('masked_mean_ratio')}")
        baseline_alignment_factor = 1.0
        alignment_source = "default_fallback"
else:
    # Emit warning if alignment cannot be computed
    print(f"[ARCH-SIM-CONSTRUCTION-001 Phase C.14 WARNING] Cannot compute baseline alignment:")
    print(f"  telemetry_model_mean_masked: {telemetry_model_mean}")
    print(f"  cold_masked_mean: {cold_masked_mean if inputs.loss_mask is not None else 'N/A (no loss_mask)'}")
    baseline_alignment_factor = 1.0
    alignment_source = "default_fallback"
```

### Validating Pytest Nodes
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale \
            tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path \
    > plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T140000Z/pytest_phase_b7_fix.log 2>&1
```

### Expected Outcomes
1. Phase A.1 (warm-cache) test: PASS with rel_error=0.0 (no code changes, early return unchanged)
2. Phase A.2 (cold-path) test: PASS with rel_error < 1e-6 and ratio ≈ 1.0
3. Log evidence: `alignment_source = "calibration_masked_mean_ratio"` for cold path
4. Improvement metrics: rel_error from 738% (Phase B.6) to <0.0001% (Phase B.7)

### Commit Artifacts
Write `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T140000Z/summary.md` with:
- Context: Phase B.6 partial fix (35× → 8.4× improvement)
- Root cause: missing masked_mean_ratio from mapping phase
- Implementation: fallback extraction from calibration_metadata
- Test results: Phase A.1 PASS, Phase A.2 PASS (expected)
- Metrics progression: B.5 (3520%) → B.6 (738%) → B.7 (<0.0001%)
- Next: Phase B.8 (update docs/findings.md SCALE-009)

## Forbidden This Loop
- no new probes
- do not extend plan-local diagnostic scripts
- do not modify `tests/architecture/test_scale_contracts.py` (test fixture is correct, reconstruction code needs fixing)
- do not change warm-cache path (reconstruction.py:83-86) — early return is working correctly
- do not modify `apply_sqrt_spot_scale` API (already correct from Phase B.1-B.4)
- do not add additional scaling beyond masked_mean_ratio fallback

## How-To Map

### Environment Setup
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
```

### Test Execution
```bash
pytest -vv tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale \
            tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path \
    > plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T140000Z/pytest_phase_b7_fix.log 2>&1
```

### Success Criteria
1. Phase A.1 (warm-cache) test PASS with rel_error=0.0
2. Phase A.2 (cold-path) test PASS with rel_error < 1e-6
3. Log shows `alignment_source = "calibration_masked_mean_ratio"` for cold path
4. No regression in warm-cache behavior (early return unchanged)

### Artifact Destinations
- Test logs: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T140000Z/pytest_phase_b7_fix.log`
- Summary: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T140000Z/summary.md`

## Pitfalls To Avoid
1. **Type discipline**: This is architecture conformance remediation, not bugfix or spec_change — maintain initiative type
2. **No stacking**: Do not add additional scaling logic beyond masked_mean_ratio fallback
3. **Parity-first**: Validate warm-cache regression (Phase A.1) before celebrating cold-path fix
4. **Shadow-pipeline guard**: No new diagnostic scripts, instrument inside real reconstruction.py if needed (but current logging is sufficient)
5. **Probe saturation**: Phase B.6 already added conditional sqrt logging, do not add more diagnostics beyond alignment_source tracking
6. **Evidence→Action**: This loop MUST produce both tests PASSING or document specific blocking issue (no more planning loops allowed)
7. **ARCH conformance requirement**: Update docs/findings.md SCALE-009 after tests pass to document masked_mean_ratio fallback pattern
8. **Enforcement test**: Both Phase A.1 and A.2 must PASS to satisfy ARCH-CONTRACT-001 enforcement requirement

## If Blocked
1. If Phase A.2 still fails with different ratio/error, capture exact metrics (masked_mean_stage_a, masked_mean_reconstruction_cold, masked_mean_ratio from calibration, baseline_alignment_factor computed)
2. Check if `effective_calibration_metadata` is None or missing "masked_mean_ratio" key — add defensive logging
3. If calibration_metadata doesn't contain masked_mean_ratio, investigate whether test fixture properly loads refGeom_small's torch_config.json calibration
4. Do NOT open new architecture initiative — mark ARCH-IMPL-CONFORMANCE-001 Phase B.7 blocked and escalate to Galph with evidence
5. Possible root cause if still blocked: test fixture uses different HKL data or geometry than what build_mapping_stage_a_context used, breaking the "identical inputs" assumption

## Doc Sync Plan
**Not required this loop** — tests already exist, no new selectors added. Phase B.8 (next loop) will update:
- `docs/findings.md` (SCALE-009 correction with masked_mean_ratio fallback pattern)
- `docs/TESTING_GUIDE.md` §2 (note enforcement tests for ARCH-CONTRACT-001/002)
- `docs/development/TEST_SUITE_INDEX.md` (mark test_scale_contracts Phase A.1/A.2 as Active/PASS)

No `pytest --collect-only` runs needed this loop since tests already registered.
