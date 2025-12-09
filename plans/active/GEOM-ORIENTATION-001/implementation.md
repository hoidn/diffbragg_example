# Implementation Plan: GEOM-ORIENTATION-001

## Initiative
- ID: GEOM-ORIENTATION-001
- Title: Crystal Orientation & Beam Direction Alignment
- Owner: Galph ↔ Ralph
- Spec Owner: docs/spec-db-core.md §§Baseline Crystal State, Geometry Mapping
- Status: pending
- Type: architecture / bugfix
- Priority: Highest (Tier 0)
- Tier: 0 (unblocks Stage A/B/C smoke tests)
- Created: 2025-12-09T200000Z
- Depends on: ARCH-REFACTOR-001 (completed)
- Blocks: ARCH-SIM-CONSTRUCTION-001, DB-AT-028/029

---

## Problem Statement

Root cause investigation identified **two distinct bugs** causing 0% HKL hit rate in Stage A/B/C smoke tests:

| Bug | Description | Impact | Status |
|-----|-------------|--------|--------|
| **Bug 1** | Cell+misset path loses absolute crystal orientation (~140°), applying only delta (~1.5°) | Wrong HKL indices queried; crystal vectors differ by ~54 Å | **OPEN** |
| **Bug 2** | Beam direction sign mismatch: nanobrag defaults to `[0,0,1]` but DIALS convention is `[0,0,-1]` | Scattering vectors computed with wrong incident direction | **PARTIALLY FIXED** (vendored only) |

### Evidence Summary

**Bug 1 — Cell+Misset Orientation Loss:**
- `compute_baseline_misset_deg(perturbed, baseline)` returns only ~1.5° delta
- Absolute rotation from default Busing-Levy to indexed crystal is ~140°
- Incremental UB path: max diff 3.47e-18 (correct)
- Cell+misset path: max diff 0.0671 (completely wrong)
- Crystal `a` vector: expected `[-14.47, -13.02, -20.02]` Å, actual `[24.48, 10.19, 8.76]` Å

**Bug 2 — Beam Direction Sign:**
- dxtbx `beam.get_s0()` returns `(0, 0, -1/λ)` → unit `(0, 0, -1)` (source→sample)
- nanobrag_torch DIALS convention defaults to `[0, 0, 1]` (opposite sign)
- Patch applied to vendored `src/nanobrag-torch` in ARCH-SIM-HKL-BOUNDS-001
- Authoritative runtime at `/home/ollie/Documents/nanoBragg` status: **UNVERIFIED**

---

## Goals

1. **Restore correct crystal orientation** so Stage A constructs crystals matching dxtbx A* within 1e-12 tolerance
2. **Verify beam direction alignment** between authoritative nanoBragg source and DIALS convention
3. **Re-enable Stage A/B/C smoke tests** with ≥99% HKL hit rate
4. **Update specs** to codify orientation path requirements and beam direction conventions
5. **Document decision** on cell+misset path: deprecation vs fix

## Non-Goals

- Modifying Stage B/C refinement logic (geometry only)
- Changing HKL interpolation policies (covered by SPEC-INTERP-TRICUBIC-001)
- Fixing intensity scaling issues (covered by ARCH-SIM-CONSTRUCTION-001)

---

## Phases Overview

- **Phase A — Verification & Evidence:** Verify authoritative nanoBragg state; create reproducers proving orientation loss
- **Phase B — Spec & Architecture Updates:** Update normative specs with orientation requirements and beam conventions
- **Phase C — Implementation:** Fix or deprecate cell+misset path; verify beam direction parity
- **Phase D — Validation & Documentation:** Re-run DB-AT selectors; update findings ledger

---

## Exit Criteria

1. [ ] HKL hit rate ≥99% on canonical refGeom smoke fixtures (small and full detector)
2. [ ] DB-AT-028: chi²/pixel ≤1e2 (currently ~2.1e5)
3. [ ] DB-AT-029: median ROI correlation ≥0.2 (currently ~-0.05)
4. [ ] Crystal orientation: `max|A*_torch - A*_dxtbx| ≤ 1e-12 Å⁻¹` at Stage A zero point
5. [ ] Beam direction: `incident_beam_direction = -s0/‖s0‖` matches dxtbx convention
6. [ ] All affected specs updated with normative language
7. [ ] `docs/findings.md` entry GEOM-ORIENT-001 documenting root cause and fix
8. [ ] Test registry synchronized: `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` reflect any new/changed tests

---

## Compliance Matrix (Mandatory)

- [ ] **Spec Constraint:** `docs/spec-db-core.md §§62-85 — Baseline Crystal State and Parameterization`
- [ ] **Spec Constraint:** `docs/spec-db-core.md §§51-60 — Geometry Mapping`
- [ ] **Spec Constraint:** `docs/spec-db-workflow.md §26 — Incident direction note`
- [ ] **Fix-Plan Link:** `docs/fix_plan.md — Row [ARCH-SIM-HKL-BOUNDS-001]` (beam direction predecessor)
- [ ] **Fix-Plan Link:** `docs/fix_plan.md — Row [ARCH-SIM-CONSTRUCTION-001]` (downstream dependency)
- [ ] **Finding/Policy ID:** `DIAG-OVERSAMPLE-001` (HKL stats evidence)
- [ ] **Environment Freeze:** Any edits to `/home/ollie/Documents/nanoBragg` require patch file, rebuild commands, findings entry per CLAUDE.md

---

## Spec Alignment

- **Normative Spec:** `docs/spec-db-core.md`
- **Key Clauses:**
  - §62-70: Baseline state SHALL treat dxtbx crystal A* as authoritative
  - §71-79: Incremental parameterization around baseline, not free absolute A*
  - §80-85: One-way construction of A* from params → (U, B) → A*
  - §51-60: Geometry mapping from dxtbx → simulator

---

## Architecture / Interfaces

- **Key Data Types:**
  - `dxtbx.model.Crystal` → `A* = crystal.get_A()` (3×3 reciprocal matrix)
  - `CrystalConfig` → `mosflm_a/b/c_star` (MOSFLM A* injection) OR `cell_params + misset_deg`
  - `compute_baseline_misset_deg()` → returns XYZ Euler angles (degrees)
  - `derive_robust_misset()` → returns absolute misset from B_ideal to A*

- **Boundary Definitions:**
  ```
  [dxtbx Crystal] → [nanobrag_bridge.py] → [CrystalConfig] → [nanobrag_torch Crystal] → [Simulator]
                         ↓
              compute_baseline_misset_deg()
                         ↓
              (delta only — BUG 1)
  ```

- **Sequence Sketch (Current — Buggy):**
  ```
  1. Stage A loads dxtbx crystal with A*_indexed
  2. compute_baseline_misset_deg(perturbed, baseline) → delta ~1.5°
  3. CrystalConfig constructed with cell_params + delta misset
  4. nanobrag Crystal uses Busing-Levy B + delta rotation
  5. Result: A*_torch ≠ A*_indexed (missing ~140° absolute rotation)
  ```

- **Sequence Sketch (Fixed — Incremental UB):**
  ```
  1. Stage A loads dxtbx crystal with A*_indexed
  2. CrystalConfig constructed with mosflm_a/b/c_star = columns of A*_indexed
  3. nanobrag Crystal directly uses injected A*
  4. Result: A*_torch = A*_indexed (within fp tolerance)
  ```

---

## Context Priming (read before edits)

- **Primary docs/specs:**
  - `docs/spec-db-core.md` §§51-85 (geometry mapping, crystal state)
  - `docs/spec-db-workflow.md` §26 (incident direction note)
  - `docs/nanobrag_api.md` §§59-67 (CrystalConfig orientation)
  - `docs/config_crosswalk.md` (beam/crystal mapping)

- **Required findings/case law:**
  - `DIAG-OVERSAMPLE-001`: HKL stats evidence showing 0% hit rate
  - `ARCH-SIM-HKL-BOUNDS-001`: Prior beam direction fix (vendored)
  - `TORCH-GEOMETRY-SYNC-001`: Related geometry alignment work

- **Related telemetry/attempts:**
  - `plans/active/ARCH-SIM-HKL-BOUNDS-001/reports/2025-12-03T154217Z/` (beam direction patch)
  - `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/` (ongoing intensity work)

- **Data dependencies:**
  - Canonical refGeom smoke fixtures (`refGeom.expt`, `refGeom.refl`, `scaled.mtz`)
  - Per `docs/data_dependency_manifest.md`

---

## Phase A — Verification & Evidence

### Objective
Verify the current state of both bugs and create reproducible evidence for decision-making.

### Checklist

- [ ] A0: **Nucleus / Test-first gate:** Author `plans/active/GEOM-ORIENTATION-001/bin/verify_orientation_paths.py` that:
  1. Loads canonical refGeom smoke dataset
  2. Constructs CrystalConfig via incremental UB path (MOSFLM A* injection)
  3. Constructs CrystalConfig via cell+misset path
  4. Compares resulting A* matrices against dxtbx `crystal.get_A()`
  5. Emits JSON metrics: max|ΔA*|, per-axis offsets, orientation angle delta

- [ ] A1: **Authoritative nanoBragg beam direction check:** Inspect `/home/ollie/Documents/nanoBragg/src/nanobrag_torch/models/detector.py` and `/home/ollie/Documents/nanoBragg/src/nanobrag_torch/simulator.py` to determine if ARCH-SIM-HKL-BOUNDS-001 patch is present in the runtime source. Record findings in `plans/active/GEOM-ORIENTATION-001/reports/<timestamp>/beam_direction_status.md`.

- [ ] A2: **HKL hit rate verification:** Extend the nucleus probe to run a single-panel simulation with both orientation paths and capture HKL stats (in-bounds fraction, queried ranges). Store results in `hkl_stats_by_path.json`.

- [ ] A3: **Decision gate:** Based on A0-A2 evidence, document recommendation:
  - Option A: Deprecate cell+misset path, mandate incremental UB for all production runs
  - Option B: Fix cell+misset to apply absolute misset (more invasive)
  - Option C: Hybrid — fix cell+misset but prefer incremental UB

  Record decision in `plans/active/GEOM-ORIENTATION-001/reports/<timestamp>/decision_rationale.md`.

### Dependency Analysis

- **Touched Modules:** `dbex/nanobrag_bridge.py`, `dbex/refinement/stage_a.py`, `dbex/refinement/config_factories.py`
- **Circular Import Risks:** None identified — all imports are unidirectional toward nanobrag_torch
- **State Migration:** If deprecating cell+misset, existing telemetry with `param_deltas['misset_deg']` must remain readable but not drive new simulations

### Notes & Risks

- **Risk A1:** Authoritative nanoBragg may lack the beam direction fix, requiring external blocker request per CLAUDE.md
- **Mitigation:** If missing, file request to `~/Documents/nanoBragg/inbox/` and document blocker in this plan

---

## Phase B — Spec & Architecture Updates

### Objective
Update normative specs to codify orientation path requirements before implementation.

### Checklist

- [ ] B1: **Update `docs/spec-db-core.md` §§62-85 (Baseline Crystal State):**
  - Add explicit requirement: "Cell+misset path MUST preserve absolute orientation relative to the laboratory frame, not just delta from baseline"
  - Add note: "MOSFLM A* injection (incremental UB) is the canonical path for mapping-aligned refinement"
  - Add conformance gate: "Implementations using cell+misset MUST validate A*_constructed matches A*_dxtbx within DB-AT-026 tolerances"

- [ ] B2: **Update `docs/spec-db-core.md` §§51-60 (Geometry Mapping):**
  - Add explicit beam direction requirement: "Incident beam direction SHALL be computed as `-s0/‖s0‖` from dxtbx beam"
  - Add note: "DIALS convention default `[0,0,1]` in DetectorConfig applies ONLY when custom_beam_vector is not set; production mappings MUST verify sign parity"

- [ ] B3: **Add ADR to `docs/architecture.md`:**
  ```
  ADR-08: Crystal Orientation Path Selection
  - Context: Cell+misset path loses absolute orientation; incremental UB preserves it
  - Decision: MOSFLM A* injection is mandatory for mapping-aligned refinement
  - Consequences: Cell+misset path is deprecated for production; may be used for diagnostics with explicit warning
  ```

- [ ] B4: **Update `docs/nanobrag_api.md` §CrystalConfig:**
  - Add warning box: "When using cell+misset (no MOSFLM A* injection), absolute crystal orientation is NOT preserved"
  - Document: "For production refinement, always set `mosflm_a/b/c_star` from `crystal.get_A()` columns"

- [ ] B5: **Update `docs/config_crosswalk.md`:**
  - Crystal section: Add explicit mapping from dxtbx A* to CrystalConfig MOSFLM fields
  - Beam section: Add explicit `-s0/‖s0‖` conversion with example code

- [ ] B6: **Update `docs/dxtbx_api.md` §Crystal/Beam:**
  - Add section on A* matrix extraction: `A_star = np.array(crystal.get_A()).reshape(3, 3)`
  - Clarify column ordering: `a* = A_star[:, 0]`, `b* = A_star[:, 1]`, `c* = A_star[:, 2]`
  - Add explicit s0 sign note: "s0 points source→sample; for simulator use `-s0/‖s0‖`"

- [ ] B7: **Update `docs/spec-db-workflow.md` §Stage A Canonical Initialization:**
  - Add explicit requirement: "Stage A SHALL use MOSFLM A* injection for crystal construction"
  - Add note: "Cell+misset path is deprecated; runs using it MUST be tagged in telemetry"

- [ ] B8: **Update `docs/spec-db-conformance.md` DB-AT-026:**
  - Add orientation path requirement to acceptance criteria
  - Add: "Zero-point orientation MUST match dxtbx A* within stated tolerances for BOTH paths if cell+misset is used"

- [ ] B9: **Update `docs/STAGE_A_REFINEMENT.md`:**
  - Add "Crystal Orientation" section explaining the two paths
  - Add warning about cell+misset orientation loss
  - Add recommended usage pattern with MOSFLM A* injection

- [ ] B10: **Create `docs/architecture/dbex/crystal_orientation.idl.md`:**
  - Document the IDL contract for crystal orientation paths
  - Include type signatures for `compute_baseline_misset_deg`, `derive_robust_misset`
  - Document invariants: `A*_torch = U(params) @ B(params)` at zero point

### Notes & Risks

- **Risk B1:** Spec changes may conflict with existing ARCH-SIM-CONSTRUCTION-001 assumptions
- **Mitigation:** Coordinate with that initiative; spec changes are prerequisites, not blockers

---

## Phase C — Implementation

### Objective
Implement the chosen fix from Phase A decision gate.

### Checklist (Option A — Deprecate cell+misset)

- [ ] C1: **Add deprecation guard to `dbex/refinement/stage_a.py`:**
  - When `use_incremental_ub=False` and production mode detected, emit warning:
    ```
    warnings.warn(
        "Cell+misset path is deprecated and may produce incorrect crystal orientation. "
        "Set use_incremental_ub=True for production refinement.",
        DeprecationWarning
    )
    ```
  - Add telemetry field `orientation_path: "incremental_ub" | "cell_misset_deprecated"`

- [ ] C2: **Update `_build_stage_a_context()` to prefer incremental UB:**
  - Check if `use_incremental_ub` is explicitly set; if not, default to `True`
  - When building CrystalConfig, always extract MOSFLM A* columns from dxtbx crystal:
    ```python
    A_star = np.array(crystal.get_A()).reshape(3, 3)
    crystal_config = create_crystal_config(
        crystal,
        mosflm_a_star=tuple(A_star[:, 0]),
        mosflm_b_star=tuple(A_star[:, 1]),
        mosflm_c_star=tuple(A_star[:, 2]),
        ...
    )
    ```

- [ ] C3: **Update `simulate_forward_once()` to use incremental UB:**
  - Ensure mapping path also uses MOSFLM A* injection
  - Add assertion: `assert max|A*_torch - A*_dxtbx| < 1e-12` at construction time

- [ ] C4: **Verify beam direction in authoritative nanoBragg:**
  - If ARCH-SIM-HKL-BOUNDS-001 patch is missing:
    - Create `~/Documents/nanoBragg/inbox/geom_orientation_001_beam_direction_request.md`
    - Document blocker in this plan
    - Set status to `blocked_pending_external`
  - If patch is present:
    - Document parity verification in reports
    - Proceed to Phase D

- [ ] C5: **Add architecture enforcement test:**
  - Create `tests/architecture/test_crystal_orientation_parity.py`:
    ```python
    def test_stage_a_crystal_matches_dxtbx():
        """DB-AT-GEOM-001: Stage A crystal A* matches dxtbx within tolerance."""
        # Load canonical fixture
        # Build Stage A context
        # Compare A* matrices
        assert max_diff < 1e-12
    ```

### Checklist (Option B — Fix cell+misset) [Alternative]

- [ ] C1-alt: **Modify `compute_baseline_misset_deg()` to return absolute misset:**
  - When `baseline_crystal == crystal` (self-comparison), return absolute misset from B_ideal
  - Update docstring to clarify behavior change

- [ ] C2-alt: **Thread absolute misset through Stage A:**
  - Update `_build_stage_a_context()` to pass full misset, not delta

### Notes & Risks

- **Risk C1:** Option A may break existing workflows that rely on cell+misset behavior
- **Mitigation:** Deprecation warning gives transition period; telemetry tags allow identification of affected runs

- **Risk C4:** External blocker on nanoBragg may delay completion
- **Mitigation:** Document clearly; Phase D validation can proceed on vendored source as interim measure

---

## Phase D — Validation & Documentation

### Objective
Validate fixes via DB-AT selectors and document in findings ledger.

### Checklist

- [ ] D1: **Run orientation verification probe:**
  ```bash
  AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
  KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
  python plans/active/GEOM-ORIENTATION-001/bin/verify_orientation_paths.py \
    --output plans/active/GEOM-ORIENTATION-001/reports/<timestamp>/orientation_verification.json
  ```
  - Assert `max|ΔA*| < 1e-12` for incremental UB path
  - Assert HKL hit rate ≥99%

- [ ] D2: **Run DB-AT-028/029 selectors:**
  ```bash
  AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
  DBAT028_ARTIFACT_DIR=plans/active/GEOM-ORIENTATION-001/reports/<timestamp>/db_at_028 \
  DBAT029_ARTIFACT_DIR=plans/active/GEOM-ORIENTATION-001/reports/<timestamp>/db_at_029 \
  DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small \
  KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
  pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" \
    | tee plans/active/GEOM-ORIENTATION-001/reports/<timestamp>/pytest_db_at.log
  ```
  - Assert chi²/pixel ≤1e2 (DB-AT-028)
  - Assert median ROI correlation ≥0.2 (DB-AT-029)

- [ ] D3: **Update `docs/findings.md`:**
  Add entry GEOM-ORIENT-001:
  ```markdown
  | GEOM-ORIENT-001 | 2025-12-09 | crystal, orientation, geometry, beam | Cell+misset path loses absolute crystal orientation (~140°) by returning only delta misset (~1.5°); incremental UB path via MOSFLM A* injection preserves full orientation. Beam direction in DIALS convention must be `-s0/‖s0‖`. Fix: mandate incremental UB for production refinement. | dbex/nanobrag_bridge.py:767-906, dbex/refinement/stage_a.py:1267-1279 | Active |
  ```

- [ ] D4: **Update `docs/fix_plan.md`:**
  - Add row `[GEOM-ORIENTATION-001]` in Portfolio Overview
  - Add full entry in Detailed Status section with:
    - Status, priority, tier, depends-on, blocks
    - Working plan link
    - Attempts history with timestamps
  - Update `[ARCH-SIM-CONSTRUCTION-001]` dependencies to note orientation fix complete

- [ ] D5: **Update test registry:**
  - `docs/TESTING_GUIDE.md` §2: Add `test_crystal_orientation_parity` selector with:
    - Description of what it tests
    - Environment variables required
    - Expected outcomes
  - `docs/development/TEST_SUITE_INDEX.md`: Add entry for new architecture test with:
    - File path, test name, marker, description
    - Dependencies on fixtures/data
  - Capture `pytest --collect-only` log in reports

- [ ] D6: **Update `docs/galph_memory.md` (if applicable):**
  - Clear GEOM-ORIENTATION-001 from active focus
  - Update portfolio status

- [ ] D7: **Verify all Phase B documentation is complete:**
  - Re-read each updated doc (B1-B10)
  - Ensure cross-references between docs are consistent
  - Verify no dangling references to deprecated cell+misset behavior

- [ ] D8: **Close initiative:**
  - Verify all exit criteria met
  - Update initiative status to `done`
  - Archive reports under `plans/archive/GEOM-ORIENTATION-001/`

### Notes & Risks

- **Risk D2:** DB-AT failures may persist due to ARCH-SIM-CONSTRUCTION-001 intensity issues
- **Mitigation:** Document which failures are orientation-related vs intensity-related; orientation fix is prerequisite for intensity fix

---

## Abort / Escalation Triggers

1. **Authoritative nanoBragg requires external patch:** File request to `~/Documents/nanoBragg/inbox/`, set status to `blocked_pending_external`, document expected response timeline
2. **Spec changes require broader consensus:** Open spec_change initiative per supervisor workflow
3. **DB-AT failures persist after orientation fix:** Delegate remaining failures to ARCH-SIM-CONSTRUCTION-001 and close orientation-specific work

---

## Artifacts Index

- Reports root: `plans/active/GEOM-ORIENTATION-001/reports/`
- Bin scripts: `plans/active/GEOM-ORIENTATION-001/bin/`
- Patches (if any): `plans/active/GEOM-ORIENTATION-001/patches/`
- Latest run: `<YYYY-MM-DDTHHMMSSZ>/`

---

## Related Initiatives

| Initiative | Relationship |
|------------|--------------|
| ARCH-SIM-HKL-BOUNDS-001 | Predecessor — beam direction fix (vendored) |
| ARCH-SIM-CONSTRUCTION-001 | Downstream — depends on correct orientation for intensity parity |
| TORCH-GEOMETRY-SYNC-001 | Related — geometry alignment patterns |
| TORCH-GEOMETRY-UB-REALIGN-001 | Related — UB matrix alignment |
| DB-AT-028/029 | Validation — acceptance tests for Stage A parity |
