# ARCH-IMPL-CONFORMANCE-001 Phase A Kickoff — Contract Inventory & Reconciliation Planning

## Date: 2026-01-13T150000Z

## Context

ARCH-SIM-CONSTRUCTION-001 blocked after Phase C.39 omega hypothesis rejection. Root cause (sincg lattice factor computation bug in nanobrag_torch) requires either (a) maintainer investigation, (b) spec_change, or (c) harness-grade diagnostic initiative — all outside current plan scope.

Switching focus to ARCH-IMPL-CONFORMANCE-001 to make progress on architectural contract enforcement while ARCH-SIM-CONSTRUCTION-001 environment blocker is resolved.

## Scope: Phase A Planning

**Goal**: Inventory existing SCALE/ARCH findings, identify duplicated scaling/calibration semantics across Stage A ↔ reconstruction ↔ mapping, and propose explicit ARCH-CONTRACT definitions.

**Out of scope**: Implementation, enforcement tests, code refactoring (reserved for Phase B)

**Mode**: Docs (research and planning only)

## Phase A Deliverables (This Loop)

### 1. Findings Inventory

**Artifact**: `findings_inventory.md`

**Key findings reviewed**:
- **SCALE-008**: Stage A vs mapping baseline alignment — Stage A ignores mapping-adjusted baseline, re-derives from raw calibration
- **SCALE-009**: Reconstruction scaling parity — originally described as missing sqrt multiplication, but ARCH-SIM-CONSTRUCTION-001 revealed multi-factor issue (mask, N_cells, baseline)
- **ARCH-FACTORY-001**: Unified simulator factory scope — forward-only paths use factory, refinement closures use direct Simulator instantiation

**Contract gaps identified**:
1. No explicit ARCH-CONTRACT for factory vs direct Simulator usage
2. No canonical owner API for sqrt(spot_scale_override) scaling pattern
3. No baseline override contract for mapping → Stage A handoff

### 2. Module Inventory

**Artifact**: `module_inventory.md`

**Modules reviewed**:
- `dbex/refinement/stage_a.py` (consumer, not owner — applies sqrt scaling locally)
- `dbex/refinement/reconstruction.py` (consumer, duplicates Stage A scaling logic in cold path)
- `dbex/nanobrag_bridge.py` (candidate canonical owner for forward helpers)

**Duplicated semantics**:
1. **Pattern 1**: sqrt(spot_scale_override) multiplication (stage_a.py:442-443, reconstruction.py:~220-223)
2. **Pattern 2**: Beam calibration threading (stage_a_utils.py:267, reconstruction.py:~170)
3. **Pattern 3**: Baseline derivation (mapping.py computes, Stage A overrides)

### 3. Proposed ARCH-CONTRACTs (Phase A Output)

#### ARCH-CONTRACT-001: Simulator Factory Scope
- **Owner**: `dbex.refinement.helpers.create_unified_simulator`
- **Scope**: Forward-only simulator construction (no autograd)
- **Consumers**: `simulate_forward_once`, reconstruction cold paths, CLI forward helpers
- **Anti-pattern**: Using factory in refinement closures (breaks gradient tracking)

#### ARCH-CONTRACT-002: Post-Run Scaling Pattern
- **Owner**: NEW `dbex.refinement.scaling_utils.apply_sqrt_spot_scale`
- **Responsibility**: Apply sqrt(spot_scale_override) to raw simulator outputs
- **Current duplicates**: stage_a.py:442-443, reconstruction.py:~220-223
- **Enforcement test** (Phase B): `tests/architecture/test_scaling_contracts.py`

#### ARCH-CONTRACT-003: Mapping → Stage A Baseline Override
- **Producer**: `dbex.vis.mapping.build_mapping_stage_a_context` (provides adjusted baseline)
- **Consumer**: `dbex.refinement.stage_a` (must honor `log_scale_baseline_source` tag)
- **Current gap**: Stage A ignores mapping baseline, recomputes from raw calibration
- **Enforcement test** (Phase B): `tests/architecture/test_baseline_handoff.py`

## Phase B Planning (Next Loop)

Phase B will be **implementation_ready** with the following checklist:

### B.1 — Create Canonical Scaling Utility
- [ ] Author `dbex/refinement/scaling_utils.py` with:
  - `apply_sqrt_spot_scale(bragg, calibration_metadata)` → scaled bragg
  - `extract_beam_calibration(calibration_metadata)` → dict of beam fields
  - `should_defer_to_mapping_baseline(calibration_metadata)` → bool
- [ ] Add unit tests: `tests/dbex/test_scaling_utils.py`

### B.2 — Enhance Factory Calibration Threading
- [ ] Update `create_unified_simulator` signature: accept `calibration_metadata: dict | None`
- [ ] Extract beam_flux/exposure/beamsize internally, thread to `create_beam_config`
- [ ] Update all factory call sites to pass calibration_metadata

### B.3 — Refactor Stage A to Use Canonical API
- [ ] Replace local sqrt scaling (stage_a.py:442-443) with `scaling_utils.apply_sqrt_spot_scale`
- [ ] Add baseline handoff logic: check `log_scale_baseline_source`, defer to mapping when appropriate
- [ ] Run Stage A smokes + DB-AT-027 to validate no regression

### B.4 — Refactor Reconstruction to Use Canonical API
- [ ] Replace cold path sqrt scaling with `scaling_utils.apply_sqrt_spot_scale`
- [ ] Update factory call to pass `calibration_metadata`
- [ ] Run reconstruction parity tests

### B.5 — Enforcement Tests
- [ ] `tests/architecture/test_scaling_contracts.py::test_sqrt_scaling_parity` — Stage A vs reconstruction vs simulate_forward_once produce identical sqrt-scaled outputs
- [ ] `tests/architecture/test_factory_calibration.py::test_factory_threads_beam_calibration` — factory correctly extracts and applies beam fields
- [ ] `tests/architecture/test_baseline_handoff.py::test_stage_a_defers_to_mapping_baseline` — Stage A honors mapping-adjusted baseline

### B.6 — Documentation Updates
- [ ] Add ARCH-CONTRACTs to `docs/architecture/calibration_scaling.md` or create new `docs/architecture/scaling_contracts.idl.md`
- [ ] Update `docs/architecture/module_map.md` to clarify owner responsibilities
- [ ] Update SCALE-009 finding in `docs/findings.md` to reflect multi-factor nature (not just missing sqrt)

## Findings Drift / Inconsistencies

### SCALE-009 Partially Obsolete
Original finding (2025-12-02) described root cause as missing sqrt multiplication. ARCH-SIM-CONSTRUCTION-001 Phases C.6-C.14 (2025-12-10 through 2025-12-18) revealed:
- Trusted mask threading was missing
- N_cells gate propagation was missing
- Baseline alignment logic was missing
- Sqrt scaling alone was insufficient

**Recommendation**: Update SCALE-009 summary in `docs/findings.md` to reference multi-factor parity issue, or create new finding (SCALE-010) and mark SCALE-009 as resolved/superseded.

### ARCH-FACTORY-001 Calibration Threading Ambiguity
Finding clarifies factory scope (forward-only) but doesn't specify whether factory should:
- Accept `calibration_metadata` dict and thread it internally (proposed Phase B.2), OR
- Expect caller to extract fields and pass them explicitly

**Recommendation**: Extend ARCH-FACTORY-001 in Phase B.6 docs update to specify calibration threading contract.

## Blockers / Risks

### Risk: Phase B Scope Creep
Refactoring Stage A and reconstruction to use canonical API may surface additional edge cases (e.g., uncalibrated runs, partial calibration metadata, warm vs cold cache differences).

**Mitigation**: Limit Phase B to **routing only** — call canonical API with same inputs currently used; defer semantic changes to separate initiative.

### Risk: DB-AT-028/029 Still Failing After Phase B
ARCH-IMPL-CONFORMANCE-001 addresses architectural duplication, not the underlying sincg bug blocking ARCH-SIM-CONSTRUCTION-001.

**Mitigation**: Phase B exit criteria focus on **architectural alignment** (enforcement tests pass, duplicates removed), not DB-AT-028/029 acceptance gates. ARCH-SIM-CONSTRUCTION-001 remains responsible for DB-AT gates.

## Next Actions

1. **Supervisor review** of Phase A output (findings_inventory.md, module_inventory.md, this summary)
2. **Approval for Phase B** — confirm proposed ARCH-CONTRACTs and checklist
3. **Next Ralph loop**: implementation_ready with Phase B.1-B.6 checklist, starting with `dbex/refinement/scaling_utils.py` creation

## Artifacts

- `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T150000Z/findings_inventory.md` — SCALE-008/009 + ARCH-FACTORY-001 analysis
- `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T150000Z/module_inventory.md` — duplicated semantics + ownership proposal
- `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T150000Z/summary.md` — this document

## Cross-References

- `docs/findings.md:42` (SCALE-008)
- `docs/findings.md:43` (SCALE-009)
- `docs/findings.md:90` (ARCH-FACTORY-001)
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T150000Z/BLOCKED.md` (context for focus switch)
- `plans/active/ARCH-IMPL-CONFORMANCE-001/implementation.md` (Phase B checklist — to be updated by supervisor)

## Turn Summary (for fix_plan.md Attempts History)

Phase A kickoff planning complete after ARCH-SIM-CONSTRUCTION-001 blocked. Scoped contract inventory for SCALE-008/009 + ARCH-FACTORY-001, identified three duplicated scaling/calibration patterns (sqrt multiplication, beam threading, baseline override), proposed three ARCH-CONTRACTs with canonical owner APIs. Phase B ready for implementation_ready loop: create `scaling_utils.py`, enhance factory calibration threading, refactor Stage A/reconstruction to use canonical APIs, add enforcement tests. Artifacts: `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T150000Z/`.

---

### Turn Summary

Completed docs-only loop for ARCH-IMPL-CONFORMANCE-001 Phase A kickoff after ARCH-SIM-CONSTRUCTION-001 blocked (omega hypothesis rejected). Documented ARCH-SIM-CONSTRUCTION-001 blocking condition in fix_plan.md (status→blocked_pending_environment) + implementation.md (Phase C.39 closure note) + BLOCKED.md (three unblock options with evidence cross-refs). Completed ARCH-IMPL-CONFORMANCE-001 Phase A research: inventoried SCALE-008/009 + ARCH-FACTORY-001 findings, identified three duplicated scaling/calibration patterns (sqrt multiplication at stage_a.py:442-443 + reconstruction.py:~220-223; beam threading at stage_a_utils.py:267 + reconstruction.py:~170; baseline override mapping vs Stage A), proposed three ARCH-CONTRACTs with canonical owner APIs (scaling_utils, enhanced factory, baseline handoff). Phase B ready: create scaling utilities, refactor Stage A/reconstruction to use canonical APIs, add enforcement tests. Next: Supervisor review and approval for implementation_ready loop.

Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-13T150000Z/ (BLOCKED.md, summary.md omega correction), plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-13T150000Z/ (findings_inventory.md, module_inventory.md, summary.md Phase A kickoff)
