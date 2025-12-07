# Input for Ralph — Loop i=140

**Summary**: Refactor detector/beam overrides to post-creation pattern (match crystal_overrides), validate detector distance gradcheck, document beam wavelength external blocker.

**Mode**: none

**ActionType**: implementation_ready

**DecisionStatus**: patch_ready

**InitiativeType**: architecture

**Focus**: ARCH-GRADIENT-FLOW-001 — Gradient Flow Restoration (DB-AT-010 Unblock)

**Branch**: integration

**Mapped tests**:
- `tests/dbex/test_gradients.py::test_db_at_010_gradcheck_detector_distance` (primary validation, expect PASS)
- `tests/dbex/test_gradients.py::test_db_at_010_gradcheck_beam_wavelength` (secondary validation, expect FAIL external blocker)
- `pytest -v tests -k DB_AT_010 --smoke-detector-size=full` (regression check IF detector passes)

**Artifacts**: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T230000Z/`

---

## Findings Applied (Mandatory)

**RUNTIME-001** (Runtime execution guardrails):
- DB-AT-010 gradcheck requires `NANOBRAGG_DISABLE_COMPILE=1` to avoid Dynamo interference with `torch.autograd.gradcheck`
- Code: `docs/TESTING_GUIDE.md:22-28`, `docs/pytorch_runtime_checklist.md:26`
- Adherence: All validation commands include `NANOBRAGG_DISABLE_COMPILE=1` + `KMP_DUPLICATE_LIB_OK=TRUE`

**GRADIENT-001** (Gradient test patterns):
- Tests must inject differentiable parameters via tensor-valued override mechanisms preserving autograd graph
- Post-creation override pattern matches crystal_overrides precedent (working implementation)
- Code: `dbex/physics/forward.py:194-208` (crystal_overrides pattern)
- Adherence: Option C refactor implements symmetrical pattern for detector/beam configs

**ARCH-ENGINE-002** (Config factory ownership):
- Geometry config construction logic lives in `config_factories.py` with scalar extraction from dxtbx
- Override logic lives in caller scope (`simulate_forward_torch`) with tensor field assignment
- Code: `dbex/refinement/config_factories.py`
- Adherence: Revert factory parameter approach (i=139), restore factory-creates-caller-overrides separation

**TESTING-003** (Acceptance test registry maintenance):
- TEST_SUITE_INDEX.md must update when DB-AT-010 status changes
- Code: `docs/development/TEST_SUITE_INDEX.md`
- Adherence: Deferred to Phase B.4 after full gradcheck suite passes

---

## Pointers

**SPEC**:
- `docs/spec-db-conformance.md` §DB-AT-010 — Gradcheck tolerance requirements (eps=1e-6, atol=1e-5, rtol=0.05)
- `docs/spec-db-runtime.md` §Gradient Hygiene — Differentiability preservation contract

**ARCH**:
- `docs/architecture.md` §13 Common Pitfalls — Gradient flow preservation (to be updated Phase B.4)
- `docs/architecture/module_map.md` — Physics/geometry module responsibilities

**Testing Docs**:
- `docs/TESTING_GUIDE.md:106-108` — Gradient test canonical commands with compile guard
- `docs/development/TEST_SUITE_INDEX.md` — DB-AT-010 status row (currently FAILING)

**Evidence Artifacts** (Ralph i=139):
- `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T220000Z/phase_b1_analysis.md` — Option C recommendation (lines 183-195)
- `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T220000Z/pytest_detector_distance_post_fix.log` — Jacobian mismatch signature
- `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T220000Z/pytest_beam_wavelength_post_fix.log` — External blocker evidence (nanobrag_torch.simulator.py:761)

**Code Modules**:
- `dbex/physics/forward.py:85-86,113-118,184-188,231-241` — Current override implementation (i=139, to be refactored)
- `dbex/refinement/config_factories.py:234,249-250,257-260` — Wavelength override addition (i=139, to be reverted)
- `tests/dbex/test_gradients.py:379-401,467-489` — Updated test harness (i=139, minor adjustments if needed)
- `dbex/physics/forward.py:194-208` — Crystal overrides pattern (precedent for Option C)

---

## ARCH Contracts (mandatory)

### ARCH-CONTRACT: GRADIENT-001 (Gradient Test Tensor Override Pattern)

**Owner API**: `dbex/physics/forward.py::simulate_forward_torch` (crystal_overrides parameter + post-creation field assignment pattern)

**Description**: Gradient tests inject differentiable tensor parameters via override dictionaries. Configs are created with scalars from dxtbx, then overridden with tensors AFTER creation to preserve autograd graph.

**Forbidden duplicates**:
- Test-specific backdoors in config factories (e.g., tensor-typed parameters in `create_detector_config`, `create_beam_config`)
- Pre-creation tensor injection (type conversions/validations may strip gradients)
- Manual geometry construction in tests (duplicate config factory logic)

**Failure classification**: Implementation bug within architecture (i=139 used pre-creation pattern, violates GRADIENT-001 post-creation precedent)

**Remediation** (this loop):
1. **Canonical owner API**: `simulate_forward_torch` post-creation override pattern (lines 194-208 crystal precedent)
2. **Delete/route duplicates**: Revert factory parameter approach from i=139 (`wavelength_override`, `distance_mm_override` parameters removed)
3. **Enforcement test**: Deferred to Phase B.3 (requires detector test passing first)

---

### ARCH-CONTRACT: ARCH-ENGINE-002 (Config Factory Scalar Extraction Responsibility)

**Owner API**: `dbex/refinement/config_factories.py` (create_detector_config, create_beam_config, create_crystal_config)

**Description**: Config factories extract scalar geometry values from dxtbx objects and construct nanobrag_torch config dataclasses. Tensor-valued overrides are NOT in factory scope (caller responsibility).

**Forbidden duplicates**:
- Tensor parameter threading through factory signatures (violates scalar extraction contract)
- Test-specific logic branches in factories (use caller override pattern instead)

**Failure classification**: Implementation bug (i=139 added tensor parameters to factories, violates separation of concerns)

**Remediation** (this loop):
1. **Canonical owner API**: Factories create configs with scalars only (restore pre-i=139 signatures)
2. **Delete/route duplicates**: Remove wavelength_override parameter from create_beam_config (revert lines 234, 249-250, 257-260)
3. **Enforcement test**: Covered by GRADIENT-001 enforcement (same test validates both contracts)

---

## Do Now (hard validity contract)

**Focus**: ARCH-GRADIENT-FLOW-001 Phase B.1 Continuation (Option C Refactor)

### Implement: `dbex/physics/forward.py::simulate_forward_torch` + `dbex/refinement/config_factories.py`

**Exact changes**:

1. **Revert beam override factory approach** (`dbex/refinement/config_factories.py`):
   - Remove `wavelength_override` parameter from `create_beam_config` signature (line 234)
   - Remove wavelength override docstring (lines 249-250)
   - Remove conditional logic using wavelength override (lines 257-260)
   - Restore function to pre-i=139 state (scalar extraction from dxtbx Beam only)

2. **Add post-creation beam override** (`dbex/physics/forward.py`):
   - After `beam_config = create_beam_config(beam)` call (locate existing call site)
   - Insert override logic:
     ```python
     # Apply beam overrides (post-creation pattern matching crystal_overrides)
     if beam_overrides and 'wavelength_A' in beam_overrides:
         beam_config.wavelength_A = beam_overrides['wavelength_A']
     ```
   - Remove wavelength_override parameter from create_beam_config call (line 184-188 region)

3. **Add post-creation detector override** (`dbex/physics/forward.py`):
   - After `detector_configs = [create_detector_config(...) for panel in ...]` loop (locate existing call site)
   - Insert override logic:
     ```python
     # Apply detector overrides (post-creation pattern matching crystal_overrides)
     if detector_overrides and 'distance_mm' in detector_overrides:
         for panel_idx in range(len(detector_configs)):
             detector_configs[panel_idx].distance_mm = detector_overrides['distance_mm']
     ```
   - Remove distance_mm_override parameter from create_detector_config calls (line 231-241 region)

4. **Update simulate_forward_torch docstring** (`dbex/physics/forward.py`):
   - Update detector_overrides / beam_overrides parameter documentation (lines 113-118)
   - Note: "Applied AFTER config creation to preserve gradient graph"

**Validation commands**:

5. **Detector distance gradcheck** (primary validation):
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
     KMP_DUPLICATE_LIB_OK=TRUE \
     NANOBRAGG_DISABLE_COMPILE=1 \
     pytest -vv tests/dbex/test_gradients.py::test_db_at_010_gradcheck_detector_distance \
     --smoke-detector-size=full \
     | tee plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T230000Z/pytest_detector_distance_option_c.log
   ```
   Expected: **PASS** (Jacobian mismatch resolved, gradcheck tolerance satisfied)

6. **Beam wavelength gradcheck** (secondary validation):
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
     KMP_DUPLICATE_LIB_OK=TRUE \
     NANOBRAGG_DISABLE_COMPILE=1 \
     pytest -vv tests/dbex/test_gradients.py::test_db_at_010_gradcheck_beam_wavelength \
     --smoke-detector-size=full \
     | tee plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T230000Z/pytest_beam_wavelength_option_c.log
   ```
   Expected: **FAIL** (external blocker persists, nanobrag_torch.simulator.py:761)

7. **Full DB-AT-010 suite** (regression check, conditional):
   ```bash
   # ONLY run if detector test PASSES (task 5)
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
     KMP_DUPLICATE_LIB_OK=TRUE \
     NANOBRAGG_DISABLE_COMPILE=1 \
     pytest -vv tests -k DB_AT_010 --smoke-detector-size=full \
     | tee plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T230000Z/pytest_db_at_010_full_suite_option_c.log
   ```
   Expected: ≥1/5 PASS (detector), 3 crystal tests status TBD, 1 beam FAIL

**Artifacts**:

8. **Implementation summary** (`plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T230000Z/option_c_implementation_summary.md`):
   - Modules touched (file paths + line ranges)
   - LOC metrics (added/removed/net)
   - Git diff snippets for key changes
   - Pattern comparison: pre-creation (i=139) vs post-creation (i=140)

9. **Loop summary** (`plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T230000Z/summary.md`):
   - Test results (detector PASS/FAIL, beam FAIL expected)
   - Next loop decision (Phase B.1 closure OR escalation)
   - Beam blocker documentation status

**Commit**:

10. Commit with message:
    ```
    ARCH-GRADIENT-FLOW-001: Phase B.1 Option C refactor — post-creation detector/beam overrides

    Refactored detector_overrides and beam_overrides to use post-creation pattern
    matching crystal_overrides (assign tensor values AFTER config object creation).
    Reverted i=139 factory parameter approach (wavelength_override removed from
    create_beam_config signature).

    Test results: detector distance gradcheck [PASS/FAIL], beam wavelength gradcheck
    FAIL (external blocker nanobrag_torch.simulator.py:761 persists as expected).

    Artifacts: plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T230000Z/
    ```

---

## Forbidden This Loop

**Phase B.1 Continuation Scope**:
- **No new probes or diagnostic scripts** — implementation only (post-creation override refactor)
- **No factory signature expansion** — revert i=139 changes, restore scalar-only factory contract
- **No nanobrag_torch patches** — external blocker documented, not fixed (out of scope)
- **No enforcement test authoring** — deferred to Phase B.3 after detector test passes

**File Restrictions**:
- **Do not extend** `plans/active/ARCH-GRADIENT-FLOW-001/bin/` (no new probe scripts per PROBE-FREEZE-001)
- **Do not modify** `tests/architecture/` (enforcement test deferred to Phase B.3)
- **Do not modify** nanobrag_torch submodule (external dependency, blocker documented only)

---

## How-To Map

**Standard pytest execution** (detector/beam individual tests):
1. Set canonical env vars: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md`, `KMP_DUPLICATE_LIB_OK=TRUE`, `NANOBRAGG_DISABLE_COMPILE=1`
2. Run pytest with smoke detector size flag: `--smoke-detector-size=full`
3. Tee output to timestamped log under `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T230000Z/`
4. Review gradcheck error signature (if FAIL): Jacobian mismatch vs numerical gradient zero
5. Expected runtime: ~30-50s per test (gradcheck is compute-intensive)

**Full suite execution** (conditional on detector PASS):
1. Same env vars as individual tests
2. Use `-k DB_AT_010` selector to run all 5 gradcheck tests
3. Expected: ≥1 PASS (detector), ≤1 FAIL (beam external blocker), 3 crystal tests TBD
4. If crystal tests regress → revert Option C changes, escalate to blocked

**Artifact assembly**:
1. All pytest logs tee to `reports/2025-12-07T230000Z/pytest_*.log`
2. Implementation summary references git diff output + LOC metrics
3. Loop summary captures test results + next loop decision tree

**No toggle matrices** — single implementation path (post-creation override refactor)

---

## Pitfalls To Avoid

1. **Type discipline (gradient hygiene)**:
   - Do NOT use `.item()`, `.detach()`, `.numpy()` when overriding config fields
   - Ensure override dict values are tensor-typed with `requires_grad=True` (test harness responsibility)
   - Post-creation assignment must preserve gradient graph (assign tensor directly, no conversions)

2. **No stacking on cliff**:
   - i=139 showed gradient flow restored (not a cliff), Jacobian error is addressable
   - If detector test fails with NEW failure mode (not Jacobian mismatch) → stop, escalate

3. **Parity-first NOT applicable** (architecture work, not parity debugging):
   - This is gradient flow restoration, not end-to-end metric convergence
   - Success = gradcheck PASSES (analytical == numerical gradients within tolerance)

4. **Shadow-pipeline guard**:
   - Do NOT create new scripts under `plans/active/ARCH-GRADIENT-FLOW-001/bin/`
   - Beam blocker reproducer deferred to next loop IF detector passes

5. **Factory signature discipline**:
   - Revert ALL i=139 factory parameter additions (wavelength_override removal mandatory)
   - Factories must remain scalar-only (no tensor parameters per ARCH-ENGINE-002)

6. **Enforcement test timing**:
   - Do NOT author `tests/architecture/test_gradient_contracts.py` this loop
   - Enforcement test requires working implementation first (deferred to Phase B.3)

7. **Crystal test regression prevention**:
   - If full suite shows crystal tests FAIL with NEW signature → revert changes immediately
   - Crystal overrides pattern must remain unchanged (lines 194-208 reference only)

8. **External blocker acknowledgment**:
   - Beam wavelength test expected to FAIL (nanobrag_torch.simulator.py:761)
   - Do NOT attempt nanobrag_torch patch (environment freeze + external scope)
   - Document blocker persistence in summary.md, defer escalation decision to next loop

9. **Test harness modification minimization**:
   - Test harness already updated in i=139 to use override dicts
   - Only modify test_gradients.py IF config field names mismatch (unlikely)

10. **Commit hygiene**:
    - Commit message must reference Option C explicitly (distinguish from i=139 approach)
    - Test results in commit message (detector PASS/FAIL, beam FAIL expected)
    - Artifacts path mandatory for reproducibility

---

## If Blocked

**Detector test FAILS with Jacobian mismatch** (same signature as i=139):
- **Root cause hypothesis rejected**: Post-creation pattern does NOT resolve magnitude error
- **Action**: Mark ARCH-GRADIENT-FLOW-001 as `blocked_pending_environment`
- **Deliverables**:
  1. Create minimal reproducer for nanobrag_torch maintainer (detector + beam gradient breaks combined)
  2. Document both issues in `docs/findings.md::GRADIENT-003` (detector Jacobian) + `GRADIENT-004` (beam wavelength)
  3. Update `docs/fix_plan.md` ARCH-GRADIENT-FLOW-001 status: blocked_pending_environment
  4. Update galph_memory.md with escalation rationale + blocker classification

**Detector test FAILS with NEW failure mode** (not Jacobian mismatch):
- **Unexpected regression**: Option C refactor introduced new issue
- **Action**: Revert i=140 changes, re-run detector test to confirm pre-i=140 signature
- **If revert restores i=139 signature**: Document Option C failure, escalate to blocked
- **If revert shows NEW signature**: Deeper issue introduced, audit forward.py call chain

**Crystal tests regress** (new FAILs or changed signatures):
- **Architectural risk realized**: Refactor broke working crystal override pattern
- **Action**: Immediate revert of all i=140 changes
- **Escalate**: Mark blocked_pending_architecture, audit config object field assignment semantics

**Both detector AND beam PASS** (optimistic scenario):
- **Hypothesis**: nanobrag_torch.simulator.py:761 self-resolved OR BeamConfig field assignment bypasses simulator constructor
- **Action**: Continue to Phase B.2 (enforcement test authoring)
- **Validation**: Run full DB-AT-010 suite, expect 5/5 PASS

---

## Doc Sync Plan (Conditional)

**Not applicable this loop** — no new tests authored, no selector renames.

**Deferred to Phase B.3** (when enforcement test added):
- Run `pytest --collect-only tests/architecture/test_gradient_contracts.py` → capture to collect log
- Update `docs/development/TEST_SUITE_INDEX.md` with new enforcement test row
- Cross-reference in `docs/TESTING_GUIDE.md` §Architecture Enforcement Tests

---

**Input authored**: 2025-12-07T230000Z (Loop i=140, Galph)
**Dwell**: 2 (i=139 implementation + i=140 continuation)
**Next loop**: Phase B.1 closure OR escalation (depends on detector test result)
