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
- [ ] A1: Extract all existing SCALE/ARCH findings touching simulator construction and scaling (SCALE-008/009, ARCH-FACTORY-001) and cross-check them against current Stage A, reconstruction, and `simulate_forward_once` implementations. **[DEFERRED to kickoff loop 2026-01-13T150000Z — findings_inventory.md, module_inventory.md already complete]**
- [ ] A2: Identify duplicated semantics and inconsistencies (e.g., double-sqrt handling, conflicting SCALE-009 text vs implementation) and document them as candidate ARCH-CONTRACT corrections. **[DEFERRED to kickoff loop 2026-01-13T150000Z — findings_inventory.md, module_inventory.md already complete]**
- [ ] A3: Propose concrete ARCH-CONTRACT definitions for at least the Stage A ↔ reconstruction scaling path and Stage A ↔ mapping baseline path, including owner API(s) and forbidden duplicates list. **[DEFERRED to kickoff loop 2026-01-13T150000Z — summary.md ARCH-CONTRACT-001/002/003 already proposed]**

### Status Note
- Phase A kickoff planning complete (2026-01-13T150000Z): findings inventory, module inventory, ARCH-CONTRACT proposals documented
- Phase A.0 nucleus test design complete (2026-01-13T200000Z): nucleus_test_design.md, phase_a1_implementation_plan.md
- **Next: Phase A.1 implementation** (loop i=109): implement nucleus test per phase_a1_implementation_plan.md
- After A.1: Decision point — skip to Phase B (canonical API implementation) or continue A.2-A.3 if additional contract refinement needed

### Dependency Analysis (Required for Refactors)
- **Touched Modules:** dbex/refinement/stage_a.py, dbex/refinement/reconstruction.py, dbex/nanobrag_bridge.py, dbex/refinement/helpers.py, tests/architecture/* (new).
- **Circular Import Risks:** Monitor imports when introducing any new shared helpers or tests; avoid moving physics into test-only modules.
- **State Migration:** Ensure any new owner API does not change persisted artifact formats or telemetry schemas without coordinated updates.

### Notes & Risks
- Existing findings (especially SCALE-009) may be partially incorrect; this initiative must correct them and clearly mark superseded text.
- Must not weaken acceptance criteria for DB-AT-027/028/029; architectural changes should be internal.

## Phase B — Canonical Owner APIs + Enforcement
### Checklist
- [ ] B1: Design and implement canonical owner API(s) for the chosen ARCH-CONTRACTs (e.g., a single helper that encodes the authoritative “Stage A-like forward + scale” contract used by both reconstruction and diagnostic paths).
- [ ] B2: Route existing duplicate implementations (reconstruction helper, bridge helper, mapping forward probes) through the owner API or clearly document any exceptions.
- [ ] B3: Add architecture enforcement tests under `tests/architecture/` that fail when:
  - Stage A and reconstruction forward paths diverge in masked mean beyond tolerance for calibrated runs, or
  - mapping forward vs Stage A forward violate the agreed baseline contract.

### Notes & Risks
- Need to respect Environment Freeze by not modifying upstream nanobrag_torch; only dbex and tests should change.
- Enforcement tests must be stable (no excessive runtime, no dependence on random seeds).

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

