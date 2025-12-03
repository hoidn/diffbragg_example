# [DIAG-NANOBRAGG-OVERSAMPLE-001] nanobrag_torch Oversample Parameter Investigation

## Metadata
- **ID**: DIAG-NANOBRAGG-OVERSAMPLE-001
- **Title**: Investigate why nanobrag_torch `oversample` parameter not honored
- **Owner**: Galph ↔ Ralph
- **Status**: in_progress
- **Type**: diagnostics
- **Tier**: 0 (unblocks ARCH-SIM-CONSTRUCTION-001)
- **Created**: 2025-12-02T194500Z
- **Depends on**: None
- **Blocks**: ARCH-SIM-CONSTRUCTION-001 (reconstruction magnitude discrepancy)

## Problem Statement

ARCH-SIM-CONSTRUCTION-001 stuck after 4 implementation loops due to suspected environment issue: explicit `DetectorConfig(oversample=3)` setting does not prevent auto-selection code path in `nanobrag_torch.Simulator.run()`. Test logs show "auto-selected 3-fold oversampling" printed 209 times despite explicit parameter, causing ~23,317× magnitude discrepancy in reconstruction helpers (bragg_after=1.025e-05 vs expected ~0.24, chi²=1.084e+05 vs ≤1e2 spec).

**Suspected causes:**
1. `DetectorConfig.oversample` field not preserved by dataclass
2. Explicit `oversample=-1` passed to `simulator.run()` somewhere, overriding config
3. Auto-selection logic bug in simulator.py

Environment freeze blocks investigation without using exception clause for targeted bugfixes to locally available source.

## Spec Alignment

**Normative references:**
- docs/spec-db-core.md §§20-40 (detector configuration, oversampling semantics)
- docs/spec-db-workflow.md §§53-61 (reconstruction helpers correctness requirements)
- ARCH-SIM-CONSTRUCTION-001 exit criteria: "Reconstruction simulator raw output magnitude matches Stage A simulator raw output (within 1% for same parameters)"

**Acceptance tests:**
- DB-AT-028: `chi²/pixel initial ≤ 1e2`
- DB-AT-029: `median ROI correlation before ≥ 0.2`

## Goals

1. **Confirm root cause** of oversample parameter handling issue in nanobrag_torch
2. **Document diagnostic process** per Environment Freeze exception requirements
3. **Provide evidence** to support targeted fix or maintainer escalation

## Non-Goals

- Fixing the issue (Phase 2, conditional on Phase 1 findings)
- Changing acceptance criteria or specs
- Modifying DBEX production code (issue is in nanobrag_torch)

## Exit Criteria

1. Debug instrumentation added to `nanobrag_torch/simulator.py` to log oversample parameter flow
2. Patch file saved to `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/patches/nanobrag_debug_instrumentation.patch`
3. nanobrag_torch rebuilt successfully with debug instrumentation
4. DB-AT-028 rerun with debug output captured in artifacts
5. Root cause identified from debug logs (Case A, B, or C per problems_ledger_service.md)
6. Findings documented in `docs/findings.md` with DIAG-NANOBRAGG-OVERSAMPLE-001 tag
7. Environment state tagged (e.g., "nanobragg-debug-oversample-2025-12-03")

## Phases

### Phase A: Debug Instrumentation

**Objective**: Add minimal debug prints to confirm oversample parameter handling without changing logic

**Tasks:**
- [ ] A.1: Add debug prints to `src/nanobrag-torch/src/nanobrag_torch/simulator.py:769-780`:
  ```python
  def run(self, oversample=None, ...):
      print(f"[DIAG-OVERSAMPLE] simulator.run() called with oversample={oversample}")
      print(f"[DIAG-OVERSAMPLE] self.detector.config.oversample={self.detector.config.oversample}")
      if oversample is None:
          oversample = self.detector.config.oversample
          print(f"[DIAG-OVERSAMPLE] oversample after config read: {oversample}")
      if oversample == -1:
          # auto-selection logic
          print(f"[DIAG-OVERSAMPLE] Entering auto-selection branch")
  ```
- [ ] A.2: Save patch file to `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/patches/nanobrag_debug_instrumentation.patch`
- [ ] A.3: Document rebuild process in artifacts
- [ ] A.4: Rebuild nanobrag_torch
- [ ] A.5: Rerun DB-AT-028 with `-s` flag to capture debug output
- [ ] A.6: Analyze debug logs to identify case (A/B/C)
- [ ] A.7: Document findings in `docs/findings.md`

**Validation:**
- Debug logs show full oversample parameter flow from DetectorConfig construction through simulator.run()
- Root cause case identified (A/B/C)

**Artifacts:**
- `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/patches/nanobrag_debug_instrumentation.patch`
- `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T043000Z/nanobragg_build.log`
- `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T043000Z/pytest_db_at_028_debug.log`
- `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T043000Z/root_cause_analysis.md`
- Update to `docs/findings.md` (new finding: DIAG-OVERSAMPLE-001)

### Phase B: Targeted Fix (Conditional)

**Objective**: Apply minimal fix based on Phase A diagnosis

**Conditional execution:**
- Only proceed if Phase A confirms fixable bug (Case A or C)
- If Case B (caller issue), return to ARCH-SIM-CONSTRUCTION-001 to fix caller
- If unfixable without upstream changes, escalate to maintainers

**Tasks (TBD based on Phase A findings):**
- Case A: Add oversample field to DetectorConfig dataclass
- Case C: Fix auto-selection logic bug

**Validation:**
- DB-AT-028/029 PASS with fixed nanobrag_torch
- ARCH-SIM-CONSTRUCTION-001 unblocked

**Phase B Status**: Implemented but INSUFFICIENT (deep copy prevents intra-instance mutation but doesn't address upstream config creation)

### Phase C: Config Lifecycle Fix (Root Cause Correction)

**Objective**: Fix upstream DetectorConfig creation in DBEX to thread `oversample` through warm simulator context

**Root Cause (Corrected from Phase A):**
- Phase A incorrectly identified the problem as "single DetectorConfig being mutated"
- Phase B debug evidence shows: 2/292 configs have oversample=3, 290/292 have oversample=-1
- Actual problem: Multiple different DetectorConfig instances created with different oversample values
- Issue location: `dbex/refinement/stage_a_utils.py` calls `create_detector_config()` without passing `oversample` parameter

**Affected code locations:**
1. `stage_a_utils.py::_build_stage_a_context` line ~286-290 (panel-mode simulators)
2. `stage_a_utils.py::_build_stage_a_context` line ~326-331 (ROI-mode simulators)
3. `stage_a_utils.py::_compute_panel_loss` line ~480-484 (cold-path panel simulators, diagnostic branch)
4. `stage_a_utils.py::_compute_panel_loss` line ~572-576 (cold-path panel simulators, fast-path branch)

**Fix Strategy:**
1. Add `oversample: int = 3` field to `RefinementConfig` (dbex/refinement/config.py)
2. Thread `config.oversample` through `_build_stage_a_context` → `create_detector_config` calls (4 locations)
3. Thread `config.oversample` through `_compute_panel_loss` cold-path → `create_detector_config` calls (2 locations)

**Tasks:**
- [ ] C.1: Add `oversample` field to RefinementConfig dataclass with default value 3
- [ ] C.2: Update `_build_stage_a_context` signature to accept `config: RefinementConfig` parameter
- [ ] C.3: Pass `oversample=config.oversample` to `create_detector_config` at 4 call sites in `_build_stage_a_context`
- [ ] C.4: Thread `config.oversample` through `_compute_panel_loss` cold-path (2 call sites)
- [ ] C.5: Update all callers of `_build_stage_a_context` to pass `config` parameter
- [ ] C.6: Rerun DB-AT-028/029 with debug instrumentation to confirm 292/292 configs have oversample=3
- [ ] C.7: Remove debug instrumentation from nanobrag_torch, rerun clean validation
- [ ] C.8: Update docs/findings.md with corrected root cause analysis

**Validation:**
- Debug logs show 292/292 DetectorConfig instances have oversample=3 (not 2/292)
- Zero "Entering auto-selection branch" messages in debug logs
- DB-AT-028 PASS: chi²/pixel initial ≤ 1e2 (currently fails: 1.091e+05)
- DB-AT-029 PASS: median ROI correlation before ≥ 0.2 (currently fails: -0.037)

**Artifacts:**
- `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-0XT0XXXXXZ/phase_c_planning.md`
- `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-0XT0XXXXXZ/pytest_db_at_028_debug.log` (290→292 oversample=3 instances)
- `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-0XT0XXXXXZ/pytest_db_at_028_029_clean.log` (both PASS)

### Phase D: Crystal scale + HKL mismatch investigation (New)

**Objective**: Confirm whether the nanobrag_torch crystal/cell tensors use inconsistent units that suppress structure factors (diagnose simulator raw output remaining ~10^4× too small after Phase C.8).

**Context**:
- Phase C.8 clean validation still produced zero-intensity Bragg stacks even after oversample threading and beam flux fix attempt.
- Manual reproduction with `refGeom.expt`/`scaled.mtz` shows simulator warnings (“out of range for three point interpolation”) and `hkl_frac ≈ 3e-09` despite scattering vectors `~5.8e9` and real-space vectors `~1e-9`. This suggests real vectors are stored in meters while scattering vectors are `1/Å`, causing dot products ≈0.

**Tasks:**
- [ ] D.1: Author Tier-2 diagnostic script (`plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/bin/trace_simulator_mismatch.py`) that:
  - Loads `refGeom.expt`, `scaled.mtz`, `747_mask.pkl`.
  - Builds Detector/Crystal configs exactly like Stage A (`oversample=3`, `enable_hkl_interpolation=False`).
  - Runs a single-panel `Simulator` with `debug_config={'trace_pixel': [0,0], 'printout': True}` to capture scattering vector, rotated real/reciprocal vectors, and HKL fractions.
  - Writes JSON summary + raw trace log under `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/<timestamp>/`.
- [ ] D.2: Analyze trace outputs to quantify the unit mismatch (e.g., compare `rot_a` magnitude vs unit cell, check if `hkl_frac` stays within metadata bounds, confirm whether `scattering_vec` is 1/m or 1/Å).
- [ ] D.3: Document findings in `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/<timestamp>/crystal_unit_analysis.md`, including hypotheses for where conversion should occur (`Crystal.compute_cell_tensors` vs `compute_physics_for_position`).
- [ ] D.4: Update `docs/findings.md` with new DIAG entry (“Crystal unit mismatch collapses HKL lookup to default_F”), referencing trace artifacts.
- [ ] D.5: Revise Phase C exit criteria / implementation plan based on confirmed locus (e.g., add Phase E fix tasks targeting `nanobrag_torch.models.Crystal` or `compute_physics_for_position`).

**Validation:**
- Trace log shows non-zero `hkl_frac` aligning with grid bounds once units are corrected (or clearly demonstrates mismatch prior to fix).
- Diagnostic script reproduces zero output deterministically using repository fixtures (no missing external data).

**Artifacts:**
- `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/bin/trace_simulator_mismatch.py`
- `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/<timestamp>/simulator_trace.log`
- `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/<timestamp>/crystal_unit_analysis.md`

### Phase E: HKL coverage instrumentation & findings correction

**Objective**: Verify how often Stage A queries HKL values outside the structure-factor grid, correct the DIAG-UNIT misdiagnosis, and gather quantitative evidence (min/max h,k,l, in-bounds hit rate) to explain the zero-output Bragg stacks.

**Background**:
- Phase D trace outputs mixed SI and crystallographic units inside the CLI trace hook, leading to the (now retracted) DIAG-UNIT-001 finding.
- The production `_compute_physics_for_position` path already works in SI units end-to-end; we still do not know why `Crystal.get_structure_factor` is returning zeros everywhere.
- Need reproducible instrumentation that records the actual h,k,l arrays seen by the simulator and counts how many requests fall outside the HKL grid so we can decide whether the issue is missing structure factors vs. some other scaling bug.

**Tasks:**
- [ ] E.1 Add optional HKL stats collection to `nanobrag_torch` (e.g., extend `debug_config` or add a context manager) that records:
  - min/max of the fractional h,k,l values computed inside `_compute_physics_for_position`
  - counts of in-bounds vs out-of-bounds lookups (before default_F fallback)
  - total number of structure-factor queries and how many returned exactly zero
- [ ] E.2 Surface those stats through the existing trace path (`trace_simulator_mismatch.py`) so the script can emit a JSON summary (`hkl_stats.json`) alongside the raw trace log.
- [ ] E.3 Update `docs/findings.md` (DIAG-UNIT-001) to mark the unit-mismatch claim as **Retracted**, cite the new instrumentation, and describe the remaining unknown (HKL coverage vs. structure-factor magnitude).
- [ ] E.4 Run the smoke fixture (small detector) with HKL stats enabled; save outputs under a new timestamped report directory and highlight whether min/max h,k,l fall outside `hkl_metadata` ranges.
- [ ] E.5 Repeat for the full-detector smoke run if time permits so we know whether the issue is confined to cropped fixtures.

**Validation:**
- HKL stats JSON shows non-zero in-bounds counts (or conclusively shows every query is out-of-bounds).
- Trace script emits new artifact (`hkl_stats.json`) referenced from findings and fix_plan Attempts History.
- DIAG-UNIT-001 entry in `docs/findings.md` updated with retraction note and link to HKL stats evidence.

**Artifacts:**
- `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/bin/trace_simulator_mismatch.py` (updated to consume HKL stats)
- `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/<timestamp>/hkl_stats.json`
- Updated `docs/findings.md` (DIAG-UNIT-001 retraction + HKL stats summary)

### Phase F: HKL coverage comparison (Stage A vs. mapping forward helper)

**Objective**: Determine whether the 100% out-of-bounds HKL queries originate from Stage A’s simulator construction or from the upstream structure-factor grid by collecting comparable HKL statistics from both Stage A warm-cache simulators and the canonical `simulate_forward_once()` helper.

**Tasks:**
- [x] F.1: Extend `dbex/refinement/stage_a_utils.py::_build_stage_a_context` to accept an optional `debug_config` dict (default None) and thread it through to all Simulator instantiations (panel-mode and ROI-mode caches). Docstring notes this parameter is for diagnostics only; production Stage A runs leave it as None. (2025-12-09T153000Z)
- [x] F.2: Author `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/bin/compare_hkl_stats.py` that:
  - Loads the smoke fixture via `DataLoad`/`build_mapping_stage_a_context`
  - Builds HKL grid from mapping context indices/amplitudes via `build_structure_factor_grid`
  - Builds Stage A warm-cache simulators (`_build_stage_a_context`) with `debug_config={'collect_hkl_stats': True}` and runs each simulator once to harvest `simulator.hkl_stats`
  - Runs `simulate_forward_once(debug_config={'collect_hkl_stats': True})`
  - Emits `hkl_stats_comparison.json` summarizing grid metadata vs. observed HKL ranges for both paths plus a prose `summary.md` with side-by-side comparison and interpretation. (2025-12-09T153000Z)
- [x] F.3: Run the comparison script with small detector (`NANOBRAGG_DISABLE_COMPILE=1 python bin/compare_hkl_stats.py --detector-size small --out-dir reports/2025-12-09T153000Z/`) and update `docs/findings.md` DIAG-OVERSAMPLE-001 entry with Phase F evidence showing both paths miss the HKL grid identically (0/9.4M in-bounds, observed h∈[28,47] vs grid h∈[-24,24]). Confirmed this is NOT a Stage-A-specific config issue; recommend ARCH-SIM-HKL-BOUNDS-001 to investigate HKL grid construction or reciprocal-space transform alignment. (2025-12-09T153000Z)

**Validation:**
- Stage A smoke test (`test_stage_a_expansion`) runs without errors introduced by `debug_config` parameter (test was already failing due to HKL grid issue; new parameter remains inert when None).

**Artifacts:**
- `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-09T153000Z/hkl_stats_comparison.json`
- `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-09T153000Z/summary.md` documenting that both Stage A and `simulate_forward_once` have identical 0% in-bounds coverage
- `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-09T153000Z/compare_hkl_stats.log`
- Updated `docs/findings.md` entry (DIAG-OVERSAMPLE-001 with Phase F timestamp and artifact references)
- Updated `dbex/refinement/stage_a_utils.py:196,335,369` (debug_config parameter and threading)

## Abort/Escalation Triggers

**Abort conditions:**
- nanobrag_torch build fails with unknown dependencies → escalate to user
- Debug logs don't reveal root cause → request maintainer investigation
- Fix requires extensive nanobrag_torch changes (>50 lines) → escalate to user

**Escalation path:**
- Create problems.md entry with "[ESCALATE TO USER]" tag
- Document investigation findings and blocker
- Recommend maintainer engagement or environment upgrade

## Environment Freeze Exception Compliance

Per CLAUDE.md Environment Freeze exception clause:

✓ **Scope**: Patches to locally available source (`src/nanobrag-torch/`)
✓ **Requirement 1**: Save patch file → `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/patches/*.patch`
✓ **Requirement 2**: Document rebuild commands → captured in artifacts/build.log
✓ **Requirement 3**: Test fix resolves blocking issue → DB-AT-028/029 validation
✓ **Requirement 4**: Update docs/findings.md → DIAG-OVERSAMPLE-001 finding
✓ **Requirement 5**: Tag environment state → "nanobragg-debug-oversample-2025-12-03"

**Rationale**: ARCH-SIM-CONSTRUCTION-001 is Tier 0 blocker affecting reconstruction correctness (critical path). Investigation requires source-level debugging not achievable via configuration/API changes.

## Dependencies

**Upstream:**
- None (can proceed immediately)

**Downstream (blocks these until complete):**
- ARCH-SIM-CONSTRUCTION-001 (reconstruction magnitude discrepancy)
- ARCH-REFACTOR-001 Phase D.3 (reconstruction baseline logic, blocked by ARCH-SIM-CONSTRUCTION-001)

## Risk Assessment

**Low risk**:
- Phase A is read-only diagnostic (only adds prints, no logic changes)
- Patch file provides rollback path
- nanobrag_torch is local source, not production dependency

**Medium risk**:
- Build system complexity unknown (may require complex dependencies)
- Rebuild may expose other latent issues

**Mitigation**:
- Incremental approach (diagnose before fixing)
- Document all steps for reproducibility
- Tag environment state before/after changes

## Success Metrics

- Root cause identified from debug logs
- Zero test regressions (all existing tests continue to PASS/SKIP as before)
- ARCH-SIM-CONSTRUCTION-001 unblocked (if fix applied in Phase B)
- Documentation complete per Environment Freeze exception requirements
