# Input for Loop i=111

## Summary
Implement canonical scaling utilities (Phase B.1) and thread calibration_metadata to reconstruction cold path (Phase B.2) to establish infrastructure for ARCH-CONTRACT-002 enforcement.

## Mode
none (production implementation)

## ActionType
implementation_ready

## DecisionStatus
patch_ready

## InitiativeType
architecture

## Focus
[ARCH-IMPL-CONFORMANCE-001] — Architecture / Implementation Contract Alignment (Phase B.1-B.2: Canonical API + Calibration Threading)

## Branch
integration

## Mapped Tests
- `tests/dbex/refinement/test_scaling_utils.py::test_apply_sqrt_spot_scale` (new unit test, expect PASS)
- `tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale` (warm-cache regression check, expect PASS)
- `tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path` (cold-path baseline persistence, expect FAIL until B.3-B.4 refactor)

## Artifacts
`plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T000000Z/`

## Findings Applied (Mandatory)
- **SCALE-002** (docs/findings.md:39): DiffBragg spot_scale_override must be re-applied as sqrt factor to nanobrag_torch outputs
- **SCALE-008** (docs/findings.md:42): Stage A warm-cache baseline authority and masked-intensity baseline
- **SCALE-009** (docs/findings.md:43): Reconstruction scaling provenance (multi-factor parity issue)
- **ARCH-FACTORY-001** (docs/findings.md:TBD): Unified simulator factory responsibilities and limits

## Pointers
- **Spec**: docs/spec-db-core.md:60-140 (calibration threading contracts)
- **Arch**: docs/architecture/calibration_scaling.md:14 (post-simulation sqrt scaling)
- **Testing**: docs/TESTING_GUIDE.md:1-100 (env vars, pytest selectors)
- **Phase B Planning**: plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T000000Z/phase_b_planning.md
- **Phase A.2 Summary**: plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T230000Z/summary.md

## ARCH Contracts (mandatory)

### ARCH-CONTRACT-001: Stage A vs Reconstruction Scaling Parity
- **Status**: PARTIALLY SATISFIED (warm-cache only, Phase A.1 validated)
- **Owner module/API**: NEW `dbex.refinement.scaling_utils.apply_sqrt_spot_scale` (Phase B.1)
- **Failure classification**: Architecture conformance failure — duplicated scaling logic in reconstruction cold path (lines 203-208) drifted from Stage A pattern (lines 442-443)
- **Current duplicates**:
  - dbex/refinement/stage_a.py:442-443 (original pattern)
  - dbex/refinement/reconstruction.py:203-208 (cold path duplicate)
- **Enforcement test**: tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path (FAIL baseline: 64.7% rel_error)

### ARCH-CONTRACT-002: Post-Run Scaling Pattern
- **Owner module/API**: NEW `dbex.refinement.scaling_utils.apply_sqrt_spot_scale` (Phase B.1 deliverable)
- **Responsibility**: Apply sqrt(spot_scale_override) to raw simulator outputs
- **Consumers** (Phase B.3-B.4 will refactor):
  - dbex/refinement/stage_a.py:442-443
  - dbex/refinement/reconstruction.py:203-208
  - dbex/vis/mapping.py (simulate_forward_once path)
- **Enforcement test**: tests/architecture/test_scale_contracts.py (Phase A.1/A.2 tests)

### ARCH-CONTRACT-003: Mapping → Stage A Baseline Override
- **Status**: NOT VALIDATED (out of scope for Phase B.1-B.2)
- **Deferred to**: Phase B.6 or follow-on initiative

## Do Now (hard validity contract)

**Focus**: [ARCH-IMPL-CONFORMANCE-001] Phase B.1-B.2

### Implement: `dbex/refinement/scaling_utils.py::apply_sqrt_spot_scale`

1. **Create canonical scaling utility module** (Phase B.1):
   - Author `dbex/refinement/scaling_utils.py` (~80 lines)
   - Function signature:
     ```python
     def apply_sqrt_spot_scale(
         bragg: np.ndarray,
         calibration_metadata: dict | None,
     ) -> np.ndarray:
     ```
   - Extract `spot_scale_override` from `calibration_metadata.get('spot_scale_override')`
   - Return `bragg * sqrt(spot_scale_override)` if override > 0 else `bragg` unchanged
   - Handle None metadata gracefully (scale = 1.0)
   - Docstring must cite ARCH-CONTRACT-002, SCALE-002/008/009
   - No torch dependencies (numpy-only)

2. **Create unit test** (Phase B.1):
   - Author `tests/dbex/refinement/test_scaling_utils.py::test_apply_sqrt_spot_scale`
   - Test cases:
     - No metadata (None) → scale = 1.0
     - No spot_scale_override key → scale = 1.0
     - spot_scale_override = 0 → scale = 1.0
     - spot_scale_override = 3.2e17 → scale ≈ 5.66e8
     - Shape preservation (panel mode vs single-panel)

3. **Thread calibration_metadata to reconstruction** (Phase B.2):
   - Update `dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry` signature:
     - Add parameter: `calibration_metadata: dict | None = None`
   - Update cold-path sqrt_spot_scale extraction (lines 203-208):
     ```python
     effective_calibration_metadata = calibration_metadata or config.calibration_metadata
     spot_scale_override = None
     if effective_calibration_metadata is not None:
         spot_scale_override = effective_calibration_metadata.get('spot_scale_override')
     sqrt_spot_scale = float(np.sqrt(spot_scale_override)) if spot_scale_override and spot_scale_override > 0 else 1.0
     ```
   - Add docstring update citing ARCH-CONTRACT-002 and Phase B.1 canonical API
   - DO NOT update call sites yet (backward compatibility via default None)

4. **Run validation tests**:
   ```bash
   # Unit test (expect PASS)
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   KMP_DUPLICATE_LIB_OK=TRUE \
   pytest -vv tests/dbex/refinement/test_scaling_utils.py::test_apply_sqrt_spot_scale

   # Warm-cache regression (expect PASS)
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale

   # Cold-path baseline persistence (expect FAIL, refactor not yet applied)
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path
   ```

5. **Write artifacts**:
   - `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T000000Z/pytest_phase_b1_unit.log`
   - `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T000000Z/pytest_phase_a1_regression.log`
   - `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T000000Z/pytest_phase_a2_baseline.log`
   - `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T000000Z/summary.md`

## Forbidden This Loop
- No new probes (ARCH-PROBE-FREEZE-001)
- Do not extend plan-local diagnostic scripts
- Do not refactor Stage A (stage_a.py:442-443) — defer to Phase B.3
- Do not refactor reconstruction consumers — defer to Phase B.4
- Do not update call sites to pass calibration_metadata — defer to Phase B.3-B.4

## How-To Map

### Environment Setup
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1  # for architecture tests (gradcheck-safe)
```

### Implementation Sequence
1. Create `dbex/refinement/scaling_utils.py` with `apply_sqrt_spot_scale` function
2. Create `tests/dbex/refinement/test_scaling_utils.py` with unit tests
3. Run unit test: `pytest -vv tests/dbex/refinement/test_scaling_utils.py::test_apply_sqrt_spot_scale | tee plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T000000Z/pytest_phase_b1_unit.log`
4. Update `dbex/refinement/reconstruction.py` signature + cold-path extraction (lines 64, 203-208)
5. Run warm-cache regression: `pytest -vv tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale | tee plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T000000Z/pytest_phase_a1_regression.log`
6. Run cold-path baseline: `pytest -vv tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path | tee plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T000000Z/pytest_phase_a2_baseline.log`
7. Write summary.md with loop outcome, metrics, next actions

### Artifact Destinations
- All pytest logs: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T000000Z/`
- Summary: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T000000Z/summary.md`

## Pitfalls To Avoid

1. **Type discipline**: This is `architecture` initiative, not `bugfix`. Do not change semantics, only centralize owner API.

2. **Parity-first**: Phase A.2 test will still FAIL after this loop (expected). Phase B.3-B.4 refactor required to pass.

3. **No stacking**: Do not stack additional changes on reconstruction.py beyond signature + cold-path extraction. Call-site updates deferred to B.3-B.4.

4. **Environment Freeze**: No pip installs, no package upgrades. Only edit dbex/ and tests/.

5. **PROBE-FREEZE-001**: No new plan-local diagnostic scripts. All evidence must come from production telemetry or architecture enforcement tests.

6. **Enforcement test stability**: Architecture tests must run quickly (<10s) and deterministically (no random seeds, no warm-cache timing dependencies).

7. **Import discipline**: `scaling_utils.py` must be numpy-only (no torch imports) to avoid circular dependencies. Unit test may import torch fixtures but helper itself is torch-free.

8. **Backward compatibility**: Default `calibration_metadata=None` in reconstruction signature ensures existing call sites continue to work. Phase B.3-B.4 will update them explicitly.

9. **Evidence→Action contract**: Loop must end with summary.md documenting:
   - Unit test outcome (PASS/FAIL)
   - Warm-cache regression outcome (PASS/FAIL)
   - Cold-path baseline outcome (FAIL expected)
   - Next production edit (Phase B.3: refactor stage_a.py:442-443)

10. **Dwell enforcement**: This is loop 1 for Phase B implementation. Phase B.3-B.4 must complete within next 2 loops or mark blocked.

## If Blocked

If unit test FAILS or warm-cache regression FAILS:
1. Mark Phase B.1-B.2 blocked in galph_memory.md
2. Document blocker in summary.md with error signature
3. Propose unblock options (fix canonical API, defer to spec_change, etc.)
4. Do NOT proceed to Phase B.3-B.4 until Phase B.1-B.2 exit criteria satisfied

If cold-path test PASSES unexpectedly:
1. Document surprise in summary.md
2. Investigate why calibration_metadata threading alone fixed parity
3. Adjust Phase B.3-B.4 scope if canonical API refactor no longer needed

## Doc Sync Plan (Conditional)
Not applicable (no new tests authored in this loop; Phase A.1/A.2 tests already exist).
