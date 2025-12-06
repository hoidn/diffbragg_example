# Input for Loop i=112

## Summary
Refactor Stage A and reconstruction to use canonical `apply_sqrt_spot_scale` API (Phase B.3-B.4), eliminating duplicated scaling logic and satisfying cold-path enforcement test.

## Mode
none (production implementation — architecture conformance refactor)

## ActionType
implementation_ready

## DecisionStatus
patch_ready

## InitiativeType
architecture

## Focus
[ARCH-IMPL-CONFORMANCE-001] — Architecture / Implementation Contract Alignment (Phase B.3-B.4: Refactor Stage A + Reconstruction to Use Canonical API)

## Branch
integration

## Mapped Tests
- `tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale` (warm-cache regression check, expect PASS)
- `tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path` (cold-path contract validation, expect PASS after refactor — was 64.7% rel_error, expect <0.0001%)
- `tests/dbex/test_stage_a_smoke_parity.py::test_stage_a_smoke_parity` (Stage A behavior regression check, expect PASS)

## Artifacts
`plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T020000Z/`

## Findings Applied (Mandatory)
- **SCALE-002** (docs/findings.md:39): DiffBragg spot_scale_override must be re-applied as sqrt factor to nanobrag_torch outputs — canonical API now encapsulates this pattern
- **SCALE-008** (docs/findings.md:42): Stage A warm-cache baseline authority and masked-intensity baseline
- **SCALE-009** (docs/findings.md:43): Reconstruction scaling provenance — Phase B.3-B.4 eliminates drift by delegating to canonical owner API
- **ARCH-FACTORY-001** (docs/findings.md:TBD): Unified simulator factory responsibilities and limits
- **ARCH-PROBE-FREEZE-001** (docs/findings.md:PROBE-FREEZE-001): No new plan-local probes; enforcement via production telemetry and architecture tests

## Pointers
- **Spec**: docs/spec-db-core.md:60-140 (calibration threading contracts)
- **Arch**: docs/architecture/calibration_scaling.md:14 (post-simulation sqrt scaling)
- **Testing**: docs/TESTING_GUIDE.md:1-100 (env vars, pytest selectors)
- **Phase B.3-B.4 Planning**: plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T020000Z/phase_b3_b4_planning.md
- **Phase B.1-B.2 Summary**: plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T000000Z/summary.md
- **Canonical API**: dbex/refinement/scaling_utils.py:35-111
- **Stage A Target**: dbex/refinement/stage_a.py:438-444
- **Reconstruction Target**: dbex/refinement/reconstruction.py:213-221

## ARCH Contracts (mandatory)

### ARCH-CONTRACT-002: Post-Run Scaling Pattern
- **Status**: API DELIVERED (Phase B.1), refactor IN PROGRESS (Phase B.3-B.4)
- **Owner module/API**: `dbex.refinement.scaling_utils.apply_sqrt_spot_scale` (delivered loop i=111)
- **Responsibility**: Apply sqrt(spot_scale_override) to raw simulator outputs
- **Failure classification**: Architecture conformance failure — duplicated scaling logic in Stage A and reconstruction cold path drifted from specification
- **Current duplicates** (to be eliminated this loop):
  - dbex/refinement/stage_a.py:438-444 (original pattern, refactor to canonical API in Phase B.3)
  - dbex/refinement/reconstruction.py:213-221 (cold path duplicate, refactor to canonical API in Phase B.4)
- **Enforcement test**: tests/architecture/test_scale_contracts.py (Phase A.1 warm-cache PASS, Phase A.2 cold-path FAIL baseline: 64.7% rel_error, expect PASS after refactor)

### ARCH-CONTRACT-001: Stage A vs Reconstruction Scaling Parity
- **Status**: PARTIALLY SATISFIED (warm-cache only via cache optimization from ARCH-SIM-CONSTRUCTION-001 Phase C.8)
- **Target**: FULL SATISFACTION after Phase B.3-B.4 refactor (cold-path parity restored)
- **Enforcement test**: tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path (expect rel_error <= 1e-6 after refactor)

## Do Now (hard validity contract)

**Focus**: [ARCH-IMPL-CONFORMANCE-001] Phase B.3-B.4

### Implement: Refactor Stage A and Reconstruction to Use Canonical `apply_sqrt_spot_scale` API

#### B.3 — Refactor Stage A (dbex/refinement/stage_a.py:438-444)

1. **Add import** (top of file, around line 28-35 with other dbex.refinement imports):
   ```python
   from dbex.refinement.scaling_utils import apply_sqrt_spot_scale
   ```

2. **Replace lines 438-444** (current duplicated logic):
   ```python
   # OLD CODE (DELETE):
   # Apply spot_scale_override per SCALE-002 (sqrt factor)
   # Extract spot_scale_override from calibration_metadata when present
   spot_scale_override = 1.0
   if config.calibration_metadata is not None:
       spot_scale_override = config.calibration_metadata.get("spot_scale_override", 1.0)
   sqrt_spot_scale = float(np.sqrt(spot_scale_override)) if spot_scale_override > 0 else 1.0
   bragg_stack_scaled = bragg_stack * sqrt_spot_scale
   ```

   **With canonical API call (NEW CODE):**
   ```python
   # Apply spot_scale_override per SCALE-002 using canonical API
   # ARCH-CONTRACT-002 owner: dbex.refinement.scaling_utils.apply_sqrt_spot_scale
   # Phase B.3 (ARCH-IMPL-CONFORMANCE-001): Eliminate duplicated scaling logic
   bragg_stack_np = bragg_stack.detach().cpu().numpy()
   bragg_stack_scaled_np = apply_sqrt_spot_scale(bragg_stack_np, config.calibration_metadata)
   bragg_stack_scaled = torch.from_numpy(bragg_stack_scaled_np).to(
       device=bragg_stack.device, dtype=bragg_stack.dtype
   )
   ```

3. **Update comment/docstring** to cite ARCH-CONTRACT-002 and Phase B.3

#### B.4 — Refactor Reconstruction (dbex/refinement/reconstruction.py:213-221)

1. **Add import** (top of file, around line 23-26 with other dbex.refinement imports):
   ```python
   from dbex.refinement.scaling_utils import apply_sqrt_spot_scale
   ```

2. **Simplify lines 213-221** (keep effective_calibration_metadata threading, delete duplicated sqrt extraction):
   ```python
   # OLD CODE (DELETE lines 217-221):
   spot_scale_override = None
   if effective_calibration_metadata is not None:
       spot_scale_override = effective_calibration_metadata.get('spot_scale_override')

   sqrt_spot_scale = float(np.sqrt(spot_scale_override)) if spot_scale_override and spot_scale_override > 0 else 1.0
   ```

   **KEEP line 216 (calibration_metadata threading from Phase B.2):**
   ```python
   # Thread calibration_metadata parameter (Phase B.2, ARCH-IMPL-CONFORMANCE-001)
   # Prioritize explicit parameter over config default
   effective_calibration_metadata = calibration_metadata or config.calibration_metadata
   ```

3. **Find all `* sqrt_spot_scale` multiplication sites** in cold-path reconstruction (around line 506) and **replace with canonical API calls**:
   ```python
   # OLD PATTERN (search for similar):
   bragg_scaled = bragg_panel * scale_factor * baseline_alignment_factor * sqrt_spot_scale

   # NEW PATTERN (apply canonical API):
   bragg_prescaled = bragg_panel * scale_factor * baseline_alignment_factor
   bragg_scaled = apply_sqrt_spot_scale(bragg_prescaled, effective_calibration_metadata)
   ```

   **Note**: Apply canonical API at the FINAL multiplication site only, preserving order of operations for scale_factor and baseline_alignment_factor.

4. **Update comment/docstring** to cite ARCH-CONTRACT-002 and Phase B.4

5. **Delete or update legacy DEBUG print statements** referencing `sqrt_spot_scale` (around line 404-406) if they no longer make sense after refactor.

#### Validation Sequence

1. **Phase A.1 warm-cache regression** (expect PASS, no behavior change):
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale | tee plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T020000Z/pytest_phase_a1_regression.log
   ```

2. **Phase A.2 cold-path contract validation** (expect PASS, improvement from 64.7% → <0.0001%):
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path | tee plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T020000Z/pytest_phase_a2_validation.log
   ```

3. **Stage A smoke regression** (expect PASS, Stage A behavior unchanged):
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_SIGMA_SOURCE=metadata \
   DBEX_SMOKE_DETECTOR_SIZE=small \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_stage_a_smoke_parity | tee plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T020000Z/pytest_stage_a_smoke.log
   ```

4. **Write summary**:
   - Capture outcomes, metrics (rel_error before/after for Phase A.2), next actions
   - Save to `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T020000Z/summary.md`

## Forbidden This Loop
- No new probes (ARCH-PROBE-FREEZE-001 enforced)
- Do not extend plan-local diagnostic scripts
- Do not modify nanobrag_torch source (Environment Freeze)
- Do not change behavior beyond delegating to canonical API (identity refactor)
- Do not update call sites to pass `calibration_metadata` explicitly yet (defer to Phase B.5 if needed)

## How-To Map

### Environment Setup
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1  # for architecture tests (gradcheck-safe)
export DBEX_SMOKE_SIGMA_SOURCE=metadata  # for Stage A smoke test
export DBEX_SMOKE_DETECTOR_SIZE=small    # for Stage A smoke test
```

### Implementation Sequence
1. Add import to `dbex/refinement/stage_a.py`: `from dbex.refinement.scaling_utils import apply_sqrt_spot_scale`
2. Replace lines 438-444 with torch↔numpy conversion + canonical API call
3. Add import to `dbex/refinement/reconstruction.py`: `from dbex.refinement.scaling_utils import apply_sqrt_spot_scale`
4. Delete lines 217-221 (duplicated sqrt_spot_scale extraction logic)
5. Replace `* sqrt_spot_scale` multiplication sites with canonical API calls
6. Update comments/docstrings to cite ARCH-CONTRACT-002, Phase B.3-B.4
7. Run Phase A.1 regression (warm-cache, expect PASS)
8. Run Phase A.2 validation (cold-path, expect PASS with rel_error <1e-6)
9. Run Stage A smoke regression (expect PASS)
10. Write summary.md with outcomes, metrics, next actions

### Artifact Destinations
- All pytest logs: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T020000Z/`
- Summary: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T020000Z/summary.md`

## Pitfalls To Avoid

1. **Type discipline**: This is `architecture` initiative (conformance refactor), not `bugfix`. Do not change semantics, only delegate to canonical owner API.

2. **Parity-first**: Phase A.2 test MUST PASS after this loop. If it still fails, investigate immediately (don't stack more changes).

3. **No stacking**: Do not add any changes beyond B.3 and B.4 scope. Call-site updates (if needed) deferred to Phase B.5.

4. **Environment Freeze**: No pip installs, no package upgrades. Only edit dbex/ and tests/.

5. **PROBE-FREEZE-001**: No new plan-local diagnostic scripts. All evidence from production telemetry or architecture enforcement tests.

6. **Enforcement test stability**: Architecture tests must run quickly (<15s) and deterministically (no random seeds, no warm-cache timing dependencies).

7. **Import discipline**: Canonical API is numpy-only; Stage A requires torch↔numpy conversion. Preserve device/dtype in reconversion.

8. **Order of operations**: In reconstruction cold path, apply canonical API AFTER scale_factor × baseline_alignment_factor to preserve existing physics order.

9. **Backward compatibility**: Do not change reconstruction call sites yet. `calibration_metadata` parameter defaults to None, falling back to `config.calibration_metadata`.

10. **Evidence→Action contract**: Loop must end with summary.md documenting:
    - Phase A.1 outcome (PASS/FAIL)
    - Phase A.2 outcome (PASS/FAIL) with rel_error before/after metrics
    - Stage A smoke outcome (PASS/FAIL)
    - Next production edit (Phase B.5 or B.6, depending on test outcomes)

11. **Dwell enforcement**: This is loop 2 for Phase B implementation (B.1-B.2 was loop 1). Phase B.5-B.6 must complete within next 1-2 loops or mark blocked.

## If Blocked

### If Phase A.2 still FAILS after refactor:
1. Mark Phase B.3-B.4 blocked in galph_memory.md
2. Document failure signature in summary.md with error metrics (actual vs expected rel_error)
3. Propose unblock options:
   - Phase B.5: Audit call sites, update to pass `calibration_metadata` explicitly
   - Investigate cold-path reconstruction logic for remaining discrepancies
   - Review Phase B.3-B.4 planning for missed refactor sites
4. Do NOT proceed to Phase B.6 until Phase A.2 PASSES

### If Phase A.1 FAILS unexpectedly:
1. Document warm-cache regression in summary.md
2. Investigate Stage A refactor for behavior change (should be identity refactor)
3. Check torch↔numpy conversion preserves device/dtype correctly
4. Revert if necessary and re-plan Phase B.3

### If Stage A smoke FAILS:
1. Stage A refactor introduced behavior change (violates identity refactor constraint)
2. Revert Stage A changes, re-plan Phase B.3 more carefully
3. Ensure canonical API call produces bit-for-bit identical results to old pattern

## Doc Sync Plan (Conditional)
Not applicable (no new tests authored in this loop; Phase A.1/A.2 tests already exist and registered).

## Cross-References
- **Phase B.3-B.4 Planning**: plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T020000Z/phase_b3_b4_planning.md
- **Phase B.1-B.2 Summary**: plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T000000Z/summary.md
- **Implementation Plan**: plans/active/ARCH-IMPL-CONFORMANCE-001/implementation.md
- **Canonical API Source**: dbex/refinement/scaling_utils.py:35-111
- **Stage A Target**: dbex/refinement/stage_a.py:438-444
- **Reconstruction Target**: dbex/refinement/reconstruction.py:213-221
- **Enforcement Tests**: tests/architecture/test_scale_contracts.py (test_stage_a_vs_reconstruction_scale, test_stage_a_vs_reconstruction_scale_cold_path)
