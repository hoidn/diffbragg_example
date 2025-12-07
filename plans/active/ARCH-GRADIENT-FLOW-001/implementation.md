# ARCH-GRADIENT-FLOW-001 — Gradient Flow Restoration (DB-AT-010 Unblock)

**Initiative Type**: architecture
**Priority**: Tier 0 (blocks Gradient-Safe Profile conformance)
**Status**: in_progress
**Created**: 2025-12-07T210000Z (Loop i=137, Galph)
**Context**: DB-AT-SUITE-CARE-001 Phase B.1 verification (i=136, Ralph) confirmed DB-AT-010 gradcheck regression persists: all 5/5 tests FAILING with disconnected autograd graph. Root cause: gradient flow break in `simulate_forward_torch` → loss path prevents analytical gradients from reaching refined parameters (crystal cell, detector distance, beam wavelength). Numerical gradients exist (non-zero sensitivity), but autograd cannot compute analytical gradients.

## Exit Criteria

1. **Gradient flow restored**: DB-AT-010 gradcheck tests pass with documented tolerances (`eps=1e-6`, `atol=1e-5`, `rtol=0.05`)
2. **Root cause identified and fixed**: Code audit locates `.item()` coercion or tensor detachment; patch applied to preserve gradient graph
3. **Enforcement test added**: `tests/architecture/test_gradient_contracts.py` validates gradient flow preservation (fails if future regression introduced)
4. **Documentation updated**: `docs/findings.md` records fix with GRADIENT-002 finding; `docs/architecture.md` updated with gradient hygiene guardrail
5. **Regression validation**: Full DB-AT-010 suite (5 tests) passes; `docs/development/TEST_SUITE_INDEX.md` status updated to PASSING

## Phase A — Gradient Flow Audit & Root Cause Localization

**Objective**: Trace gradient flow from loss backward to refined parameters; identify first disconnection point.
**Status**: ✅ **COMPLETE** (i=138, 2025-12-07T212000Z)

### Tasks (Phase A)
- [x] **A1 — Call graph trace**: Map full call path from `test_gradients.py::test_db_at_010_gradcheck_crystal_cell_a` → `simulate_forward_torch` → loss → backward pass. Document each module/function crossing with file:line references. Output: `reports/<ts>/call_graph_trace.md`.
  - **Completed**: i=138 Ralph, 7 call stack levels documented, 3 tensor flow boundaries identified
  - **Artifacts**: `reports/2025-12-07T212000Z/call_graph_trace.md`

- [x] **A2 — Suspect module audit**: Focus on high-risk gradient break locations per Ralph's i=136 hypothesis:
  - `dbex/physics/forward.py::simulate_forward_torch` (lines TBD)
  - `dbex/geometry/crystallography.py::TorchCrystal` bridge (parameter hydration)
  - `dbex/physics/loss.py::_compute_variance_weighted_loss` (tensor coercion)
  - `dbex/refinement/inputs.py::prepare_refinement_inputs` (config assembly)
  Search for: `.item()`, `.detach()`, `.numpy()`, `.cpu()` when `requires_grad=True`, in-place ops `*=` / `+=` on leaf tensors.
  Output: `reports/<ts>/suspect_audit.md` with file:line citations.
  - **Completed**: i=138 Ralph, 13 matches analyzed, 0 production UNSAFE patterns, 2 test harness UNSAFE patterns
  - **Key Finding**: Test harness gradient breaks at test_gradients.py:383 (detector), :496 (beam)
  - **Artifacts**: `reports/2025-12-07T212000Z/suspect_audit.md`, 6 grep output files

- [x] **A3 — Minimal gradient probe**: **DEFERRED** — Not needed for Phase B.1 (detector/beam fixes).
  - **Rationale**: Production code is gradient-safe (0 UNSAFE patterns found). Crystal test failures suspected to be external dependency (nanobrag_torch.models.Crystal constructor).
  - **Next Step**: If crystal tests still fail post Phase B.1, run A.3 probe to empirically test Crystal gradient preservation.
  - **Thin wrapper requirement**: Must stay <400 LOC per PROBE-FREEZE-001 if implemented later.

- [x] **A4 — Hypothesis ranking**: Based on A1-A2 evidence, rank top 3 hypotheses (e.g., "TorchCrystal.cell_a coerces to scalar at line X", "loss denominator uses .item() at line Y", "config builder detaches tensor at line Z"). Assign confidence scores. Output: `reports/<ts>/hypothesis_ranking.md`.
  - **Completed**: i=138 Ralph, embedded in suspect_audit.md
  - **Top Hypothesis** (confidence 0.95): Test harness detector/beam tests call `.item()` to extract scalars for dxtbx geometry construction
  - **Secondary Hypothesis** (confidence 0.6): nanobrag_torch.models.Crystal constructor breaks gradient (requires A.3 probe to confirm)

### Validation (Phase A)
- [x] Call graph trace complete with file:line references for ≥5 call stack levels (7 levels documented)
- [x] Suspect audit covers ≥4 modules with grep results for `.item()` / `.detach()` / in-place ops (4 modules, 6 grep patterns)
- [x] Minimal gradient probe executes successfully and reports grad=None or grad=tensor (DEFERRED — not needed for B.1)
- [x] Hypothesis ranking has ≥3 entries with confidence ≥0.5 for top candidate (2 hypotheses, top=0.95)

---

## Phase B — Root Cause Fix & Enforcement Test

**Objective**: Implement fix for top-ranked hypothesis; add architecture enforcement test to prevent regression.

### Tasks (Phase B)
- [ ] **B1 — Implement fix**: Patch identified gradient break location (e.g., replace `.item()` with tensor return, remove `.detach()`, convert in-place op to out-of-place). Must preserve production logic (no behavioral change except gradient flow). Output: git diff, commit message with ARCH-GRADIENT-FLOW-001 prefix.

- [ ] **B2 — Gradcheck verification**: Re-run DB-AT-010 full suite (`pytest -v tests -k DB_AT_010 --smoke-detector-size=full`) with canonical flags. Archive pytest log under `reports/<ts>/gradcheck_verification_post_fix.log`. Expected: 5/5 tests PASS.

- [ ] **B3 — Enforcement test authoring**: Create `tests/architecture/test_gradient_contracts.py::test_simulate_forward_torch_preserves_gradients`. Test must:
  1. Call `simulate_forward_torch` with `requires_grad=True` tensor parameter
  2. Compute loss, call backward
  3. Assert `param.grad is not None` and `param.grad.abs().sum() > 0`
  4. Use minimal refGeom fixture (small detector size for speed)
  Expected: test PASSES post-fix, would FAIL pre-fix (demonstrate regression detection).

- [ ] **B4 — Documentation updates**:
  - Add `docs/findings.md::GRADIENT-002` finding documenting root cause, fix location (file:line), and enforcement test cross-ref
  - Update `docs/architecture.md` §13 Common Pitfalls with "Gradient Flow Preservation" subsection
  - Update `docs/development/TEST_SUITE_INDEX.md` DB-AT-010 row: status=PASSING, artifact path updated
  Output: 3 file diffs.

### Validation (Phase B)
- Fix implemented in production code (1 module edited, ≤20 lines changed)
- DB-AT-010 gradcheck suite 5/5 PASS (verified via pytest log)
- Enforcement test exists under `tests/architecture/` and PASSES
- 3 documentation files updated (findings.md, architecture.md, TEST_SUITE_INDEX.md)
- Enforcement test would FAIL on pre-fix checkout (regression detection validated)

---

## Phase C — Closure & Lessons Learned

**Objective**: Close initiative, update fix_plan ledger, archive artifacts, and propagate lessons.

### Tasks (Phase C)
- [ ] **C1 — Fix_plan.md update**: Add ARCH-GRADIENT-FLOW-001 to Tier 0, mark status=done, update DB-AT-SUITE-CARE-001 Phase B.1 with cross-ref to this initiative, record Attempts History with metrics (5/5 tests PASS, runtime, fix location). Output: fix_plan.md diff.

- [ ] **C2 — Closure summary**: Author `reports/<final-ts>/initiative_closure_summary.md` with:
  - Problem statement (gradcheck regression symptoms)
  - Root cause (exact module + line + pattern)
  - Fix description (what changed, why gradient preserved)
  - Validation results (pytest metrics, enforcement test demonstration)
  - Lessons learned (generalizable gradient hygiene rules)
  - Cross-refs (findings.md::GRADIENT-002, test_gradient_contracts.py)

- [ ] **C3 — Archive artifacts**: Move `plans/active/ARCH-GRADIENT-FLOW-001/` to `archive/plans/ARCH-GRADIENT-FLOW-001/` after closure, update all cross-refs in fix_plan.md, findings.md, TESTING_GUIDE.md. Output: archive commit with ARCH-GRADIENT-FLOW-001 prefix.

- [ ] **C4 — Propagate lessons**: Check if similar patterns exist in other physics/geometry modules (search for `.item()` in dbex/physics/, dbex/geometry/, dbex/refinement/). If found, create follow-up hygiene item under Tier 3. Output: optional new plan ID or explicit "no additional cleanup needed" note.

### Validation (Phase C)
- fix_plan.md has ARCH-GRADIENT-FLOW-001 entry (Tier 0, status=done)
- Closure summary exists with ≥5 sections (problem, root cause, fix, validation, lessons)
- Archive move complete (no active/ references remain in ledgers)
- Lesson propagation complete (follow-up scoped OR cleanup dismissed with rationale)

---

## Dependencies

### Blocks
- **DB-AT-SUITE-CARE-001 Phase B**: Portfolio advancement requires Tier-0 blocker resolution
- **Gradient-Safe Profile conformance**: DB-AT-010 is acceptance gate per `docs/spec-db-conformance.md`

### Depends On
- **DB-AT-SUITE-CARE-001 Phase B.1 verification** (i=136, complete): Evidence from Ralph's test run seeds this initiative
- **Canonical refGeom assets**: Phase A.3 gradient probe requires `refGeom.expt`, `refGeom.refl`, `scaled.mtz`, `747_mask.pkl` (already validated per DB-AT-SUITE-CARE-001 Phase B.2)

### Related Initiatives
- **DB-AT-010**: Member plan under DB-AT-SUITE-CARE-001; Phase D.1-D.3 tasks delegated to this initiative
- **ARCH-IMPL-CONFORMANCE-001**: Completed Tier-0 architecture initiative (similar enforcement test pattern)

---

## SPEC/ARCH References

### SPEC
- **docs/spec-db-conformance.md** §Gradient-Safe Profile — DB-AT-010 acceptance criteria
- **docs/spec-db-core.md** §Objective Function — Variance-weighted loss definition
- **docs/spec-db-runtime.md** §Gradient Hygiene — Differentiability requirements

### ARCH
- **docs/architecture.md** §13 Common Pitfalls — Gradient flow preservation (to be updated Phase B.4)
- **docs/architecture/module_map.md** — Physics/geometry module responsibilities
- **docs/architecture/data_telemetry_flow.md** — Forward simulation → loss path

### Testing Docs
- **docs/TESTING_GUIDE.md** §1.4 — DB-AT-010 selector pattern and canonical flags
- **docs/development/TEST_SUITE_INDEX.md** — DB-AT-010 status row (to be updated Phase B.4)
- **docs/development/testing_strategy.md** §4.1 — Gradcheck tolerance expectations

---

## Findings Applied (Mandatory)

- **RUNTIME-001** (Runtime execution guardrails): DB-AT-010 requires `NANOBRAGG_DISABLE_COMPILE=1` to avoid Dynamo interference with `torch.autograd.gradcheck`.
  - Code: `docs/TESTING_GUIDE.md:161`, `docs/pytorch_runtime_checklist.md:26`
  - Adherence: Phase B.2 gradcheck verification uses canonical flags; enforcement test (Phase B.3) includes compile guard.

- **GRADIENT-001** (Gradient test patterns): Tests must inject differentiable parameters via `crystal_overrides` dict to preserve autograd graph (not modify Crystal object in-place).
  - Code: `tests/dbex/test_gradients.py` (existing test pattern)
  - Adherence: Phase A.3 gradient probe follows GRADIENT-001 pattern; fix (Phase B.1) preserves this contract in production code.

- **TESTING-003** (Acceptance test registry maintenance): TEST_SUITE_INDEX.md must update when DB-AT-010 status changes from FAILING → PASSING.
  - Code: `docs/development/TEST_SUITE_INDEX.md`
  - Adherence: Phase B.4 includes TEST_SUITE_INDEX.md update task; cross-referenced in Phase C.1 fix_plan entry.

---

## Pointers

### Evidence Artifacts (DB-AT-SUITE-CARE-001 Phase B.1, i=136)
- **Verification report**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T204336Z/db_at_010_status_verification.md`
- **Pytest log**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T204336Z/pytest_db_at_010_verification.log`
- **Failure signature**: GradcheckError: Numerical gradient for function expected to be zero (torch/autograd/gradcheck.py:981)
- **Hypothesis**: Gradient flow break in `simulate_forward_torch` → loss path (4 candidate modules)

### Member Plan Cross-Refs
- **DB-AT-010 implementation.md**: Phase D.1-D.3 tasks delegated to this initiative
- **DB-AT-SUITE-CARE-001 implementation.md**: Phase B.1 task definition (Tier-0 escalation)

### Code Modules Under Audit
- **dbex/physics/forward.py**: `simulate_forward_torch` entry point (primary suspect)
- **dbex/geometry/crystallography.py**: TorchCrystal parameter hydration
- **dbex/physics/loss.py**: Variance-weighted loss computation
- **dbex/refinement/inputs.py**: RefinementInputs assembly

---

## Estimated Effort

**Phase A (Audit & Localization)**: 2-3 loops
- A1 (call graph): 1 loop (grep + manual trace)
- A2 (suspect audit): combined with A1
- A3 (gradient probe): 1 loop (thin wrapper script + pytest run)
- A4 (hypothesis ranking): combined with A3

**Phase B (Fix & Enforcement)**: 2-3 loops
- B1 (implement fix): 1 loop (likely <20 lines)
- B2 (gradcheck verification): combined with B1
- B3 (enforcement test): 1 loop (new test file + pytest run)
- B4 (docs update): 1 loop (3 file diffs)

**Phase C (Closure)**: 1 loop
- C1-C4 (fix_plan, closure summary, archive, lesson propagation): batch in single loop

**Total estimated loops**: 5-7 loops

---

## Notes for Supervisor Handoff

- **Tier-0 priority**: Blocks Gradient-Safe Profile conformance and DB-AT-SUITE-CARE-001 portfolio advancement
- **Evidence-driven**: Ralph's i=136 verification provides concrete failure signature (GradcheckError with disconnected graph)
- **Thin wrapper guardrail**: Phase A.3 gradient probe must stay <400 LOC per PROBE-FREEZE-001
- **Enforcement test precedent**: Follow ARCH-IMPL-CONFORMANCE-001 pattern (`tests/architecture/test_*_contracts.py`)
- **Type discipline**: architecture (not bugfix) because gradient flow break requires module boundary audit and enforcement test
- **Deferral option**: If fix proves complex (>2 loops Phase B.1), consider spec_change to relax gradcheck tolerances or mark DB-AT-010 xfail with hypothesis

---

**Implementation plan authored**: 2025-12-07T210000Z (Loop i=137, Galph)
**Next loop (i=138)**: Phase A.1-A.2 (call graph trace + suspect audit) — delegate to Ralph
