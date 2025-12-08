# Input for Ralph (Loop i=170)

## Summary
Execute ARCH-GRADIENT-FLOW-001 Phase B.5: DBEX-layer gradient audit and fix to unblock DB-AT-010 gradcheck tests.

## BindingForRalph
- **ActionType:** evidence_collection (code audit to localize gradient break in DBEX layer)
- **DecisionStatus:** exploring (first Phase B.5 loop for DBEX layer)
- **InitiativeType:** architecture

## SupervisorMode
Parity (gradient flow restoration)

## Focus
ARCH-GRADIENT-FLOW-001 — Gradient Flow Restoration (DB-AT-010 Unblock) — Phase B.5

## Branch
integration

## Mapped Tests
- `pytest -vv tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck -k "crystal_cell_a" --tb=short 2>&1 | head -100`
- Evidence-only loop: run gradcheck with verbose output to capture exact failure location

## Artifacts
`plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T220000Z/`

## Findings Applied (Mandatory)
- **GRADIENT-001** (Gradient test patterns): Tests inject differentiable parameters via `crystal_overrides` dict
  - Code: `tests/dbex/test_gradients.py:379-382`, `dbex/physics/forward.py:198-226`
  - Adherence: Audit must verify tensor flow preservation through override application
- **GRADIENT-002** (nanobrag_torch gradient fix): Upstream fix applied in nanobrag_torch layer
  - Code: `nanobrag_torch/utils/tensor_utils.py::as_tensor_preserving_grad`
  - Adherence: DBEX layer must use same pattern or compatible gradient-preserving approach
- **RUNTIME-001** (Runtime execution guardrails): Gradcheck requires `NANOBRAGG_DISABLE_COMPILE=1`
  - Code: `docs/TESTING_GUIDE.md:161`
  - Adherence: All test runs must use canonical env flags

## Pointers
- Implementation plan: `plans/active/ARCH-GRADIENT-FLOW-001/implementation.md` (Phase B section)
- Prior Phase B summary: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T060000Z/summary.md`
- Code under audit:
  - `dbex/physics/forward.py::simulate_forward_torch` (lines 73-274)
  - `dbex/refinement/config_factories.py::create_crystal_config` (lines 278-450)
  - `dbex/refinement/helpers.py::create_unified_simulator` (lines 83-240)
- Test file: `tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck` (lines 159-600)

---

## ARCH Contracts (mandatory)
- **ARCH-FACTORY-001** (Simulator Factory Scope): `create_unified_simulator` is canonical factory; forward helpers may use it
  - Owner: `dbex/refinement/helpers.py`
  - Relevance: Gradient break may be in factory's config→simulator conversion
- **GRADIENT-001** (Tensor Override Pattern): `crystal_overrides`/`detector_overrides` dicts preserve gradient flow
  - Owner: `dbex/physics/forward.py::simulate_forward_torch`
  - Classification: **Implementation bug** (override values set correctly but gradient may be lost in downstream construction)

---

## Do Now

**Focus:** ARCH-GRADIENT-FLOW-001 Phase B.5 — DBEX-layer gradient audit

### Background
Phase B (i=153) successfully fixed nanobrag_torch layer gradient flow. Enforcement tests pass (5/5 in `tests/architecture/test_gradient_contracts.py`). However, DB-AT-010 gradcheck tests still fail (5/5) with "disconnected autograd graph" error.

Root cause has shifted from nanobrag_torch to DBEX layer:
- `simulate_forward_torch` → `create_unified_simulator` → Crystal/Detector construction
- The override values (`crystal_overrides`, `detector_overrides`) are applied to config objects, but gradient flow may be lost when those configs are converted to nanobrag_torch models.

### Phase B.5 Tasks

#### B.5.1 — Run diagnostic gradcheck with tensor tracking
```bash
cd /home/ollie/Documents/diffbragg_example
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1

# Run single gradcheck test with verbose output
pytest -vvv tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_crystal_cell_a --tb=long 2>&1 | tee plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T220000Z/gradcheck_verbose.log
```

Capture: Full traceback and any tensor gradient state warnings.

#### B.5.2 — Trace tensor flow through `simulate_forward_torch`
Audit the code path for gradient breaks:

1. **Entry point** (`forward.py:73-87`): `crystal_overrides` dict received with tensor values
2. **Config creation** (`forward.py:196`): `create_crystal_config(crystal, experiment)` called WITHOUT crystal_overrides
3. **Override application** (`forward.py:200-226`): Cell parameters overwritten on `crystal_config` object

**CRITICAL QUESTION**: Does `CrystalConfig` preserve tensor values when assigned? Or does it coerce to scalar/numpy?

Check `nanobrag_torch/config/crystal.py` for `CrystalConfig` class definition — verify whether field assignment preserves torch tensors.

4. **Factory call** (`forward.py:248-259`): `create_unified_simulator(...)` receives `crystal_config` with tensor values
5. **Simulator construction** (`helpers.py:83-240`): `create_unified_simulator` builds `TorchCrystal` from config

**CRITICAL QUESTION**: Does `create_unified_simulator` extract `.item()` from tensor values or use them directly?

Search for: `.item()`, `.detach()`, `float()`, `np.array()` patterns that would break gradient flow.

#### B.5.3 — Document hypothesis and localize first gradient break
Output: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T220000Z/dbex_gradient_audit.md`

Structure:
1. **Tensor flow trace**: file:line annotations showing where tensor enters, propagates, and (if found) breaks
2. **Suspect patterns**: Any `.item()`, `.detach()`, `float()`, `np.array()` conversions on override values
3. **Hypothesis**: Specific file:line:pattern causing gradient break
4. **Confidence**: 0.0-1.0 based on evidence
5. **Proposed fix**: If localized, describe patch (single-line or few-line change)

#### B.5.4 — Summary
Output: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T220000Z/summary.md`

---

## How-To Map

```bash
# Set environment
cd /home/ollie/Documents/diffbragg_example
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
export ARTIFACT_DIR=plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T220000Z

# B.5.1: Run diagnostic gradcheck
pytest -vvv tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck_crystal_cell_a --tb=long 2>&1 | tee $ARTIFACT_DIR/gradcheck_verbose.log

# B.5.2: Search for gradient-breaking patterns in DBEX code
grep -rn "\.item()" dbex/refinement/config_factories.py dbex/refinement/helpers.py dbex/physics/forward.py
grep -rn "\.detach()" dbex/refinement/config_factories.py dbex/refinement/helpers.py dbex/physics/forward.py
grep -rn "float(" dbex/refinement/config_factories.py dbex/refinement/helpers.py dbex/physics/forward.py
grep -rn "np\.array(" dbex/refinement/config_factories.py dbex/refinement/helpers.py

# Check if CrystalConfig preserves tensors (if accessible)
grep -n "class CrystalConfig" /home/ollie/Documents/nanoBragg/src/nanobrag_torch/config/*.py 2>/dev/null || echo "Check nanobrag_torch source for CrystalConfig"

# B.5.3-B.5.4: Write audit and summary to artifacts
```

---

## Pitfalls To Avoid
1. **Do not modify nanobrag_torch** — Phase B already fixed that layer; this is DBEX-only work
2. **Do not create shadow pipeline diagnostics** — Use code reading and grep, not new probe scripts
3. **Environment Freeze** — Do not install/upgrade packages
4. **Thin wrapper rule** — Any diagnostic code must stay <400 LOC per PROBE-FREEZE-001
5. **No stacking on cliff** — If audit reveals complex multi-site issue, localize and document rather than attempting fix
6. **Type discipline** — This is architecture (gradient flow audit), not bugfix; document architectural findings

## Forbidden This Loop
- No production code changes (evidence-only loop)
- No new plan-local scripts
- Do not modify nanobrag_torch source
- Do not run full DB-AT-010 suite (single test for diagnostics)

## If Blocked
If gradient break cannot be localized in DBEX layer:
1. Document what was searched and eliminated
2. Check if break is in nanobrag_torch `CrystalConfig` → `TorchCrystal` conversion
3. If external dependency: create follow-up entry in findings.md with maintainer escalation hypothesis
4. Mark this loop as evidence-only with next hypothesis for follow-up

---

## Exit Criteria Validation

| Criterion | Expected | Validation |
|-----------|----------|------------|
| B.5.1 complete | Gradcheck verbose log captured | File exists in artifacts |
| B.5.2 complete | Code audit of tensor flow | Grep results documented |
| B.5.3 complete | dbex_gradient_audit.md exists | Hypothesis + confidence documented |
| B.5.4 complete | summary.md exists | Turn summary authored |
| No production changes | git status clean | Verify no dbex/ modifications |

---

## Output Artifacts Expected

1. `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T220000Z/gradcheck_verbose.log`
2. `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T220000Z/dbex_gradient_audit.md`
3. `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-08T220000Z/summary.md`
