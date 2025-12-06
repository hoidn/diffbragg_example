# Implementation Plan: ARCH-IMPL-CONFORMANCE-001

## Initiative
- ID: ARCH-IMPL-CONFORMANCE-001
- Title: Architecture / Implementation Contract Alignment
- Owner: Galph ↔ Ralph
- Spec Owner: docs/spec-db-core.md
- Status: pending

## Goals
- Establish explicit ARCH-CONTRACTs for critical simulator and scaling paths (Stage A, reconstruction helpers, mapping bridge).
- Eliminate duplicated, drifting semantics between ARCH docs, findings, and implementation by introducing single-owner APIs.
- Add mechanical enforcement (tests/lints) so future ARCH/impl drift is caught automatically.

## Phases Overview
- Phase A — Contract Inventory: Extract and reconcile existing SCALE/ARCH findings and architecture docs with the current code.
- Phase B — Canonical Owner APIs + Enforcement: Centralize key semantics and add architecture enforcement tests.
- Phase C — Acceptance Alignment: Apply contracts and enforcement to DB-AT-027/028/029 and related selectors.

## Exit Criteria
1. At least two high-value ARCH-CONTRACTs are defined and documented (e.g., Stage A vs reconstruction scaling contract, Stage A vs mapping baseline contract) with explicit owner APIs.
2. All identified duplicates for those contracts are either deleted, routed through the owner API, or explicitly documented as allowed exceptions.
3. Architecture enforcement tests under `tests/architecture/` (or equivalent) fail if the contracts are violated (e.g., if Stage A vs reconstruction scale diverges again by more than tolerance).
4. Test registry synchronized: `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` reflect any new/changed tests; `pytest --collect-only` logs for documented selectors are saved under `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/<timestamp>/`. Do not close the initiative if any selector marked "Active" collects 0 tests.

## Compliance Matrix (Mandatory)
- [ ] **Spec Constraint:** docs/spec-db-core.md §§20–40 — simulator construction, calibration, and scaling contracts.
- [ ] **Fix-Plan Link:** docs/fix_plan.md — Row [ARCH-IMPL-CONFORMANCE-001].
- [ ] **Finding/Policy ID:** SCALE-008, SCALE-009, ARCH-FACTORY-001, POLICY-001 (Environment Freeze).

## Spec Alignment
- **Normative Spec:** docs/spec-db-core.md
- **Key Clauses:** Stage A loss/sigma model, simulator construction and calibration threading, acceptance criteria for DB-AT-027/028/029.

## Architecture / Interfaces
- **Key Data Types / Protocols:**
  - Stage A forward context and telemetry (StageA, StageAArtifacts, StageATelemetry).
  - Reconstruction helpers (`build_final_bragg_from_stage_a_telemetry`, `build_final_bragg_from_stage_b_telemetry`).
  - Zero-iteration bridge (`simulate_forward_once`) and mapping context (`build_mapping_stage_a_context`).
- **Boundary Definitions:**
  - [Mapping] → [Stage A warm cache] → [Reconstruction helpers] for calibrated runs.
  - ARCH-CONTRACT: “Given identical calibration metadata and geometry, Stage A warm-cache forward and reconstruction helper must agree on scale and trusted-mask handling within tolerance.”

## Context Priming (read before edits)
- Primary docs/specs to re-read:
  - docs/spec-db-core.md §§20–40 (simulator + calibration contracts)
  - docs/architecture/*.md relevant to simulator factory and refinement engine
  - docs/findings.md entries SCALE-008, SCALE-009, ARCH-FACTORY-001
- Required findings/case law:
  - SCALE-008 — warm-cache authority and masked-intensity baseline for Stage A
  - SCALE-009 — reconstruction scaling provenance (to be corrected/clarified under this initiative)
  - ARCH-FACTORY-001 — unified simulator factory responsibilities and limits
- Related telemetry/attempts:
  - plans/active/ARCH-SIM-CONSTRUCTION-001/reports/*
  - plans/active/TOOLING-VIS-001/reports/*
- Data dependencies to verify:
  - DB-AT-027/028/029 fixtures and calibration metadata (config_torch.json, sigma fixtures, masks)
  - Any additional data flows recorded in docs/data_dependency_manifest.md for these selectors.

## Phase A — Contract Inventory & Reconciliation
### Checklist
- [x] A0: **Nucleus / Test-first gate:** Identify or create a minimal architecture test that exposes current Stage A vs reconstruction scaling mismatch (e.g., a small `tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale`). **[COMPLETE 2026-01-13T200000Z — nucleus_test_design.md]**
- [x] A1: **Nucleus test implementation** — Implement `test_stage_a_vs_reconstruction_scale` for warm-cache path validation. **[COMPLETE 2026-01-13T210000Z — test PASSED (unexpected), warm-cache parity confirmed via ARCH-SIM-CONSTRUCTION-001 Phase C.8 cache optimization]**
- [x] A2: **Cold-path enforcement test** — Add `test_stage_a_vs_reconstruction_scale_cold_path` to validate reconstruction cold-path contract (force `stage_a_ctx=None` to bypass cache). **[COMPLETE 2026-01-13T230000Z — test FAILED (expected), 64.7% rel_error, 2.83x scale factor drift confirmed]**
- [x] A3: Extract all existing SCALE/ARCH findings touching simulator construction and scaling (SCALE-008/009, ARCH-FACTORY-001) and cross-check them against current Stage A, reconstruction, and `simulate_forward_once` implementations. **[COMPLETE 2026-01-13T150000Z — findings_inventory.md, module_inventory.md]**
- [x] A4: Identify duplicated semantics and inconsistencies (e.g., double-sqrt handling, conflicting SCALE-009 text vs implementation) and document them as candidate ARCH-CONTRACT corrections. **[COMPLETE 2026-01-13T150000Z — findings_inventory.md identified 3 patterns]**
- [x] A5: Propose concrete ARCH-CONTRACT definitions for at least the Stage A ↔ reconstruction scaling path and Stage A ↔ mapping baseline path, including owner API(s) and forbidden duplicates list. **[COMPLETE 2026-01-13T150000Z — ARCH-CONTRACT-001/002/003 proposed in summary.md]**

### Status Note
- Phase A kickoff planning complete (2026-01-13T150000Z): findings inventory, module inventory, ARCH-CONTRACT proposals documented
- Phase A.0 nucleus test design complete (2026-01-13T200000Z): nucleus_test_design.md, phase_a1_implementation_plan.md
- Phase A.1 implementation complete (2026-01-13T210000Z): nucleus test PASSED (warm-cache parity validated via cache optimization)
- Phase A.1 analysis complete (2026-01-13T220000Z): cold-path scenario identified as unvalidated, Phase A.2 planned (phase_a1_outcome_analysis.md)
- Phase A.2 implementation complete (2026-01-13T230000Z): cold-path enforcement test FAILED (expected), 64.7% rel_error, 2.83x scale factor drift confirmed
- Phase B.1-B.2 planning complete (2026-01-14T000000Z): phase_b_planning.md scopes canonical scaling_utils module + calibration_metadata threading
- **Next: Phase B.1-B.2** (loop i=111): implement canonical API + thread calibration_metadata to reconstruction

### Dependency Analysis (Required for Refactors)
- **Touched Modules:** dbex/refinement/stage_a.py, dbex/refinement/reconstruction.py, dbex/nanobrag_bridge.py, dbex/refinement/helpers.py, tests/architecture/* (new).
- **Circular Import Risks:** Monitor imports when introducing any new shared helpers or tests; avoid moving physics into test-only modules.
- **State Migration:** Ensure any new owner API does not change persisted artifact formats or telemetry schemas without coordinated updates.

### Notes & Risks
- Existing findings (especially SCALE-009) may be partially incorrect; this initiative must correct them and clearly mark superseded text.
- Must not weaken acceptance criteria for DB-AT-027/028/029; architectural changes should be internal.

## Phase B — Canonical Owner APIs + Enforcement
### Checklist
- [ ] B1: Create `dbex/refinement/scaling_utils.py` with canonical `apply_sqrt_spot_scale` function + unit tests **[PLANNED 2026-01-14T000000Z — phase_b_planning.md]**
- [ ] B2: Thread `calibration_metadata` to reconstruction cold path (update signature, extract in cold path) **[PLANNED 2026-01-14T000000Z — phase_b_planning.md]**
- [ ] B3: Refactor Stage A to use canonical API (stage_a.py:442-443 → call `apply_sqrt_spot_scale`)
- [ ] B4: Refactor reconstruction to use canonical API (reconstruction.py:203-208 → call `apply_sqrt_spot_scale`)
- [ ] B5: Architecture enforcement tests — Phase A.1 (warm-cache) and A.2 (cold-path) both PASS **[Phase A.1/A.2 tests already exist]**
- [ ] B6: Update docs/findings.md (SCALE-008/009), docs/TESTING_GUIDE.md, docs/development/TEST_SUITE_INDEX.md

### Notes & Risks
- Need to respect Environment Freeze by not modifying upstream nanobrag_torch; only dbex and tests should change.
- Enforcement tests must be stable (no excessive runtime, no dependence on random seeds).
- Phase B.1-B.2 establishes infrastructure; Phase A.2 test will still FAIL until B.3-B.4 refactor complete.

## Phase C — Acceptance Alignment (DB-AT-027/028/029)
### Checklist
- [ ] C1: Use the ARCH-CONTRACT enforcement tests to drive any remaining changes in reconstruction helpers so that DB-AT-027/028/029 see consistent forward models (scale, masks, N_cells).
- [ ] C2: Rerun DB-AT-027/028/029 under documented commands, capture metrics and chi²/ROI correlation, and ensure they are consistent with the revised ARCH contracts.
- [ ] C3: Update docs/TESTING_GUIDE.md and docs/development/TEST_SUITE_INDEX.md with any new architecture tests and enforcement nodes, including collection logs.

### Notes & Risks
- If acceptance criteria remain unreachable even after alignment, this may trigger a follow-on `spec_change` initiative, but ARCH-IMPL-CONFORMANCE-001 stops at alignment and enforcement.

## Artifacts Index
- Reports root: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/`
- Latest run: `<YYYY-MM-DDTHHMMSSZ>/`

