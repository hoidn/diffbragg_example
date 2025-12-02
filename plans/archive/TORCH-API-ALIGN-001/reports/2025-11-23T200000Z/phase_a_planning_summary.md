# TORCH-API-ALIGN-001 Phase A Planning Summary

## Loop Context
- **Loop:** i=241 (supervisor planning)
- **Timestamp:** 2025-11-23T200000Z
- **Actor:** Galph (supervisor)
- **Mode:** Docs (planning-only, first loop for this focus)
- **State:** planning (dwell=0)

## Focus Selection Rationale

### Execution Roadmap Analysis
**Tier 1 Status (Core Physics & Stability):** ✓ COMPLETE
- All Tier 1 items done/archived/blocked on completed dependencies

**Tier 2 Status (Architectural Maturity):**
- ARCH-REFINE-FLOW-001: ✓ DONE (2025-11-23T172000Z, Phases A-E complete)
- **TORCH-API-ALIGN-001: Pending** ← **HIGHEST PRIORITY**

Per Agent Rule: "Do not start a Tier N+1 item if a Tier N item is unblocked."

TORCH-API-ALIGN-001 is the **only remaining Tier 2 item** and is unblocked. It must be started before any Tier 3 items (TORCH-REFINE-004, ARCH-REFACTOR-001, PERF-WARM-SIM-001).

### Dependencies Impacting Other Initiatives

1. **PERF-WARM-SIM-001 (Tier 3):** Status changed from `in_progress` → `blocked` (depends on TORCH-API-ALIGN-001 completion per fix_plan.md:38,171)
   - Rationale: PERF-WARM-SIM-001 Phase D routing fixes (commit 5be669c) uncovered chi-squared mismatch requiring deeper investigation
   - Decision: Block PERF-WARM-SIM-001 on API/wiring unification (TORCH-API-ALIGN-001) to avoid multiple competing wiring paths during warm-cache implementation

2. **ARCH-REFACTOR-001 (Tier 3):** Exit criterion #9 (commit 6fd8a44) explicitly depends on TORCH-API-ALIGN-001 Phase D.4 "single simulator seam" decision
   - Phase C6 checklist blocked until TORCH-API-ALIGN-001 chooses mid-term seam (factory via ExperimentModel or vice versa)

3. **TORCH-REFINE-004 (Tier 3):** Stage B per-reflection mode deferred until ARCH-REFINE-FLOW-001 complete (✓), but also benefits from unified wiring

### WIP Cap Compliance
- **Current in_progress initiatives:** 1 (TOOLING-VIS-001 Tier 3)
- **WIP cap:** ≤2
- **Compliance:** ✓ Can start TORCH-API-ALIGN-001

### Dwell Enforcement
- **Last activity on TORCH-API-ALIGN-001:** None (new initiative)
- **Dwell count:** 0
- **State:** planning
- **Implementation floor:** Next loop (i=242) MUST be ready_for_implementation per max-1-docs-only-loop rule

## Initiative Overview

### Goals (from implementation.md)
1. **Replace duplicate Simulator wiring** with single adapter path
2. **Adopt ExperimentModel** for parity-first forward modeling
3. **Standardize on DIALS mapping** (beam-center swap + panel-axis rotations) without changing nanobrag_torch
4. **Optional CUSTOM override** behind flag for teams requiring explicit −s0

### Phases
- **Phase A:** Tests First (xfail/skip-guarded) ← **CURRENT FOCUS**
- Phase B: Wiring (unify duplicate wiring)
- Phase C: Optional CUSTOM Override (dbex-only, flagged)
- Phase D: Rollout & Parity (flip adapter ON, decide seam)

### Exit Criteria
1. Unified simulator factory validates shape/dtype/device
2. DIALS mapping parity tests PASS on fixtures
3. ExperimentModel parity tests PASS (param_init="frozen")
4. Optional CUSTOM-override path behind flag with parity evidence
5. Existing smoke/perf selectors green; new tests force warm-cache OFF + NANOBRAGG_DISABLE_COMPILE=1
6. Test registry updated with new selectors

## Phase A Scope Analysis

### Checklist Tasks (from implementation.md:41-58)
- **A1:** DIALS mapping behavior test (`test_dials_mapping_parity`)
  - Construct dxtbx beam/panel → DetectorConfig via `create_detector_config` (DIALS)
  - Assert beam-center swap (fast, slow)→(s, f)
  - Assert Euler extraction from panel axes
  - Document `custom_beam_vector` ignored under DIALS
  - Selector: `tests/dbex/test_bridge_mapping.py::test_dials_mapping_parity`

- **A2:** Unified simulator factory test (`test_panel_and_stitched_shapes`)
  - Test matrix: one-panel/multi-panel, with/without spot_scale_override, with calibration metadata, CPU/CUDA
  - Mark xfail/skip until B1/B2 land
  - Selector: `tests/dbex/test_sim_factory.py::test_panel_and_stitched_shapes`

- **A3:** ExperimentModel parity tests (`test_parity_small_fixture`)
  - Compare `ExperimentModel(..., param_init="frozen")` vs legacy Simulator wiring
  - Include ROI cropping parity
  - Force `config.enable_stage_a_warm_cache=False` + `NANOBRAGG_DISABLE_COMPILE=1`
  - Mark xfail/skip until B3 lands
  - Selector: `tests/dbex/test_experiment_parity.py::test_parity_small_fixture`

- **A4 (Optional):** CUSTOM override exploratory test (`test_custom_override_exploratory`)
  - Feature-flagged path for CUSTOM Detector with panel axes + `custom_beam_vector=normalize(−s0)`
  - Measure parity deltas, record acceptance thresholds
  - Selector: `tests/dbex/test_bridge_custom_override.py::test_custom_override_exploratory`

### Relevant Findings (from docs/findings.md)
- **GEOMETRY-001:** Bridge derives beam center/detector vectors per dxtbx, rejects non-square pixels
- **GEOMETRY-002:** Torch bridge recovers DIALS XYZ via analytic inversion
- **CONFIG-001:** Config hydration requires beam-center swap, mask polarity preservation, normalization
- **CONFIG-002:** DetectorConfig.detector_convention must use enum (DetectorConvention.DIALS), not string
- **SCALE-004:** Calibration metadata (spot_scale_override, beam flux) via load_calibration_metadata()
- **PERF-WARM-001:** Stage A warm simulator cache pattern established
- **ARCH-ENGINE-002:** Stage wrapper pattern with lazy imports + telemetry packaging

### Spec/Arch References
- **Normative:** docs/nanobrag_api.md (Simulator, DetectorConfig, ExperimentModel, DIALS convention)
- **Supporting:** docs/spec-db-workflow.md §5 (per-panel simulation), docs/spec-db-core.md (variance contract)
- **Config:** docs/config_crosswalk.md (beam-center swap, mask polarity)

## Phase A Implementation Strategy

### Test Authoring Pattern (TDD, supervisor-scoped)
Per galph_prompt `<modes>` TDD: Author minimal failing tests that encode acceptance criteria before wiring lands.

**Approach:**
1. Write test stubs with xfail/skip markers (until Phase B wiring complete)
2. Tests validate contracts (DIALS mapping, factory shape/dtype, ExperimentModel parity)
3. Tests force warm-cache OFF (`enable_stage_a_warm_cache=False`) + `NANOBRAGG_DISABLE_COMPILE=1` fixture
4. Tests use tiny fixtures for fast execution (<10s per test)
5. Collect-only validation after authoring to confirm selectors discoverable

### File Structure
```
tests/dbex/
  test_bridge_mapping.py         # A1: DIALS mapping parity
  test_sim_factory.py             # A2: Unified factory
  test_experiment_parity.py       # A3: ExperimentModel parity
  test_bridge_custom_override.py  # A4: CUSTOM override (optional)
```

### Fixtures Required
- **tiny_detector_fixture:** Single panel, 100x100 pixels, square pitch (reuse from DB-AT-024 or SMOKE small)
- **multi_panel_fixture:** 2-3 panels, small dimensions (e.g., 50x50 each) for stitching tests
- **warm_cache_off_fixture:** Pytest fixture setting `enable_stage_a_warm_cache=False` + `NANOBRAGG_DISABLE_COMPILE=1` env var
- **dxtbx_beam_panel_fixture:** Minimal dxtbx beam + panel for DIALS mapping test

### Validation Approach
- **xfail/skip markers:** All 4 tests initially marked xfail (expected to fail until Phase B wiring)
- **Collect-only check:** After test authoring, run `pytest --collect-only tests/dbex/test_bridge_mapping.py tests/dbex/test_sim_factory.py tests/dbex/test_experiment_parity.py tests/dbex/test_bridge_custom_override.py` to verify 4+ tests collected
- **No execution:** Tests do NOT run in Phase A (Mode: Docs planning + stub authoring only)

## Risks & Mitigations

### Risk 1: xfail Tests Never Pass
- **Likelihood:** LOW
- **Impact:** HIGH (blocks roadmap)
- **Mitigation:** Phase A tests encode clear acceptance criteria tied to spec clauses; Phase B wiring directly targets test contracts

### Risk 2: DIALS Mapping Drift from dxtbx
- **Likelihood:** MEDIUM
- **Impact:** MEDIUM (mapping parity regression)
- **Mitigation:** Test A1 validates beam-center swap + Euler extraction against dxtbx reference; GEOMETRY-001/002 findings document analytic inversion

### Risk 3: ExperimentModel API Changes
- **Likelihood:** LOW
- **Impact:** MEDIUM (adapter breaks)
- **Mitigation:** Test A3 validates param_init="frozen" parity; rollback flag in Phase D for emergency

### Risk 4: CUSTOM Override Acceptance Thresholds Unclear
- **Likelihood:** MEDIUM
- **Impact:** LOW (optional feature)
- **Mitigation:** Test A4 is exploratory; thresholds documented in plan reports, not normative gates

## Artifacts Path
`plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T200000Z/`
- `phase_a_planning_summary.md` (this file)
- `test_checklist_a1_a4.md` (detailed test specs with acceptance criteria)
- `fixtures_spec.md` (fixture requirements for Phase A tests)
- `findings_applied.md` (GEOMETRY-001/002, CONFIG-001/002, SCALE-004, PERF-WARM-001 adherence)

## Next Actions (Loop i=242 - Ralph)

Per implementation floor rule (max 1 docs-only loop), next loop MUST be ready_for_implementation with:
1. **Implement:** Stub tests A1-A4 (xfail markers, minimal assertions, fixtures)
2. **Validate:** `pytest --collect-only` confirms 4+ tests discoverable
3. **Update:** docs/TESTING_GUIDE.md §2 with Phase A test entries (xfail status, selectors, acceptance criteria)
4. **Archive:** Collection logs to artifacts directory
5. **Commit:** Phase A test stubs + registry update

**Decision Tree:**
- **Path A (all tests collected):** Phase A test stubs complete → Galph plans Phase B wiring
- **Path B (collection FAIL):** Debug import/fixture errors → fix → retry collection
- **Path C (acceptance criteria ambiguous):** Clarify with Galph → update test specs → re-stub
- **Path D (fixture availability):** If tiny fixtures missing, defer A2/A3 pending fixture creation

## Findings Applied
- **GEOMETRY-001:** DIALS mapping contract (beam-center + detector vectors per dxtbx)
- **GEOMETRY-002:** Euler angle recovery via analytic inversion
- **CONFIG-001:** Beam-center swap (fast, slow)→(s, f), mask polarity, normalization
- **CONFIG-002:** DetectorConvention enum (not string)
- **SCALE-004:** Calibration metadata via load_calibration_metadata()
- **PERF-WARM-001:** Warm-cache OFF pattern for deterministic tests
- **ARCH-ENGINE-002:** Lazy imports + telemetry packaging pattern (applies to Phase B wiring)
- **POLICY-001:** Environment Freeze (no engine patches, dbex-only changes)

## Roadmap Impact

### Immediate Unblocking (after TORCH-API-ALIGN-001 complete)
1. **PERF-WARM-SIM-001:** Unblocked → warm-cache can leverage unified simulator factory
2. **ARCH-REFACTOR-001 Phase C6:** Unblocked → single simulator seam decision enables consolidation

### Mid-Term Benefits
- Single test/maintenance burden for simulator wiring (vs 3+ duplicate paths)
- ExperimentModel parity path enables future PTychodus/DIALS-integration
- CUSTOM override flag documented for specialized workflows

### Long-Term Architecture
- Phase D.4 decision (factory via ExperimentModel or vice versa) sets mid-term seam
- ARCH-REFACTOR-001 can delegate to chosen seam without ad-hoc wiring

## Estimated Effort
- **Phase A (this + next loop):** Planning (this loop) + test stub authoring (next loop) = 2 loops (~2-3 hours total)
- **Phase B (wiring):** 2-3 loops (~4-6 hours: factory implementation, duplicate replacement, ExperimentModel adapter)
- **Phase C (CUSTOM override):** 1 loop (~1-2 hours: feature flag + exploratory parity)
- **Phase D (rollout):** 1-2 loops (~2-4 hours: flip default, parity matrix, registry sync, seam decision)
- **Total Initiative:** ~6-9 loops, ~10-15 hours

## Dwell & State Tracking
- **Focus:** TORCH-API-ALIGN-001 — Adopt ExperimentModel, Unify Simulator Wiring, DIALS Mapping (Phase A: Tests First)
- **State:** planning
- **Dwell:** 0 (first loop for this focus)
- **Artifacts:** plans/active/TORCH-API-ALIGN-001/reports/2025-11-23T200000Z/
- **Next Action:** ready_for_implementation (test stub authoring, A1-A4)

**FSM State:** `planning` → (next loop) → `ready_for_implementation`
