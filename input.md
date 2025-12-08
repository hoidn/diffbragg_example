# Input for Loop i=159 (Ralph)

## Summary
Execute SPEC-SQUARE-PARTIALITY-001 Phase B: Update partiality test to expect linear `Na×Nb×Nc` integrated intensity scaling instead of `(Na×Nb×Nc)²`.

## Mode
Parity

## ActionType
implementation_ready

## DecisionStatus
patch_ready

## InitiativeType
spec+tests

## Focus
SPEC-SQUARE-PARTIALITY-001 — SQUARE Lattice Spec & Test Alignment

## Branch
integration

## Mapped tests
- `pytest -vv tests/architecture/test_nanobrag_partiality.py --maxfail=1`

## Artifacts
`plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T080000Z/`

## Findings Applied (Mandatory)
- **SIM-CONSTR-PARTIALITY-001**: Updated in Phase A — demoted `(Na×Nb×Nc)²` integrated expectation, promoted linear `Na×Nb×Nc`. Tests must now enforce linear scaling.
- **PROBE-FREEZE-001**: Do not create new plan-local probes; only update comments in existing probe script.

## Pointers
| Reference | Path | Section/Line |
|-----------|------|--------------|
| Maintainer Response | inbox/nanobrag_torch_response_2025_12_08.md | Part 2: SQUARE Lattice Partiality |
| Test File | tests/architecture/test_nanobrag_partiality.py | Line 45 (`expected_ratio`) |
| Probe Script | plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py | Comments |
| Implementation Plan | plans/active/SPEC-SQUARE-PARTIALITY-001/implementation.md | Phase B checklist |
| Fix Plan | docs/fix_plan.md | SPEC-SQUARE-PARTIALITY-001 row (line 268-285) |
| Phase A Summary | plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T070000Z/summary.md | Full document |

## ARCH Contracts (Mandatory)
| Contract ID | Doc Pointer | Owner Module/API | Failure Classification |
|-------------|-------------|------------------|------------------------|
| SIM-CONSTR-PARTIALITY-001 | docs/findings.md line 168 | tests/architecture/test_nanobrag_partiality.py | Implementation bug — test expectation incorrect per physics |

## Do Now (Hard Validity Contract)

### Focus: SPEC-SQUARE-PARTIALITY-001 Phase B — Align Tests & Probes

### Implement:

1. **B1 — Update test expectation**: Edit `tests/architecture/test_nanobrag_partiality.py`:
   - Line 45: Change `expected_ratio = (Na * Nb * Nc) ** 2` to `expected_ratio = Na * Nb * Nc`
   - Update docstring (lines 27-42) to reference **linear** scaling for integrated intensity
   - Update header comment (lines 5-9) to reflect the corrected contract
   - Reference the maintainer response and Phase A physics summary

2. **B2 — Update probe script comments** (read-only evidence, comments only):
   - Read `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py`
   - Update any comments that reference `(Na×Nb×Nc)²` for integrated intensity to clarify:
     - Peak intensity at exact Bragg: ∝ `(Na×Nb×Nc)²`
     - Integrated/summed intensity: ∝ `Na×Nb×Nc` (linear)
   - Do NOT change probe logic — comments only per PROBE-FREEZE-001

3. **B3 — Run partiality test and capture logs**:
   ```bash
   KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/architecture/test_nanobrag_partiality.py --maxfail=1 2>&1 | tee plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T080000Z/pytest_partiality.log
   ```
   - Expect: PASS after the fix (linear scaling matches actual simulator behavior)
   - Capture `pytest --collect-only` for registry sync

4. **B4 — Verify no other tests enforce old scaling**:
   ```bash
   grep -r "(Na \* Nb \* Nc) \*\* 2" tests/ --include="*.py" || echo "No other tests found"
   grep -r "Nc)\*\*2" tests/ --include="*.py" || echo "No other tests found"
   ```
   - Document any findings in summary.md

5. **B5 — Update implementation.md and create summary.md**:
   - Mark Phase B checklist items (B1-B4) as complete
   - Create `plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T080000Z/summary.md`

### Validating pytest selector(s):
- `pytest -vv tests/architecture/test_nanobrag_partiality.py --maxfail=1`

### Artifacts Path:
`plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T080000Z/`

### Initiative type consistent:
spec+tests ✓

## Touched
SPEC-SQUARE-PARTIALITY-001 Phase B (B1, B2, B3, B4, B5)

## Forbidden This Loop
- Do NOT create new plan-local probes per PROBE-FREEZE-001
- Do NOT modify probe logic — comments only for B2
- Do NOT change other physics parameters in the test
- Do NOT modify production code (only test file and probe comments)

## How-To Map

### Step 1: Read current test
```bash
cat tests/architecture/test_nanobrag_partiality.py
```

### Step 2: Edit test expectation (B1)
Edit `tests/architecture/test_nanobrag_partiality.py`:

**Line 45** — Change:
```python
expected_ratio = (Na * Nb * Nc) ** 2
```
To:
```python
expected_ratio = Na * Nb * Nc  # Linear scaling for integrated intensity
```

**Lines 5-9** — Update header:
```python
"""
Enforcement tests for nanoBragg partiality (lattice weight) contract.

ARCH-SIM-CONSTRUCTION-001: Simulator Construction Convention Alignment
SIM-CONSTR-PARTIALITY-001: SQUARE lattice integrated intensity scales linearly with Na×Nb×Nc

Per inbox/nanobrag_torch_response_2025_12_08.md:
- Peak intensity at exact Bragg: ∝ (Na×Nb×Nc)²
- Integrated/summed intensity: ∝ Na×Nb×Nc (linear)

This test enforces the contract that the SQUARE lattice shape must produce
integrated/summed intensity proportional to Na×Nb×Nc when summed over detector.
"""
```

**Lines 27-42** — Update test docstring to explain linear scaling:
```python
"""
Test that SQUARE lattice applies Na·Nb·Nc (linear) scaling for integrated intensity.

ARCH-CONTRACT: docs/findings.md::SIM-CONSTR-PARTIALITY-001 (Resolved 2025-12-08)
Owner: nanobrag_torch.simulator.compute_physics_for_position (SQUARE branch)
Contract: Integrated/summed intensity scales as Na×Nb×Nc (linear)

Physics (per inbox/nanobrag_torch_response_2025_12_08.md):
- Peak height scales as (Na×Nb×Nc)² (sinc² peak)
- Peak width scales as 1/(Na×Nb×Nc)
- Integral = peak × width ∝ Na×Nb×Nc (linear)

This test:
1. Runs the simulator with N_cells=(1,1,1) to get base intensity I₁
2. Runs with N_cells=(Na,Nb,Nc) to get scaled intensity I₂
3. Verifies that I₂/I₁ ≈ Na×Nb×Nc within 5% tolerance
"""
```

### Step 3: Update probe comments (B2)
Read the probe script, update comments only:
```bash
cat plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py
```
Add clarifying comments about peak vs integrated scaling. Do NOT change logic.

### Step 4: Run tests and capture logs (B3)
```bash
mkdir -p plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T080000Z
KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/architecture/test_nanobrag_partiality.py --maxfail=1 2>&1 | tee plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T080000Z/pytest_partiality.log
pytest --collect-only tests/architecture/test_nanobrag_partiality.py 2>&1 | tee plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T080000Z/collect_partiality.log
```

### Step 5: Verify no other tests (B4)
```bash
grep -rn "Nb \* Nc) \*\* 2" tests/ --include="*.py" 2>/dev/null || echo "No (Na*Nb*Nc)**2 patterns found"
grep -rn "Nc)\*\*2" tests/ --include="*.py" 2>/dev/null || echo "No Nc)**2 patterns found"
```

### Step 6: Update implementation.md (B5)
Mark B1-B4 as complete with timestamps.

### Step 7: Create summary.md
Write to `plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T080000Z/summary.md`

## Pitfalls To Avoid
1. **Do NOT use `(Na×Nb×Nc)²` for integrated intensity** — this is physically incorrect
2. **Keep tolerance reasonable** — linear scaling may have some deviation due to pixel sampling
3. **Preserve other test assertions** — steps_scalar, omega_applied_post_sum checks are still valid
4. **Comments only for probe script** — do not change probe logic per PROBE-FREEZE-001
5. **Reference sources** — cite maintainer response and Phase A physics summary
6. **Run tests after edits** — verify the fix works before documenting

## If Blocked
- If test still fails after fix: capture detailed error, document hypothesis (possibly tolerance issue)
- If probe script has changed semantics: document and defer to separate loop
- If blocked, mark Phase B as blocked with rationale and switch focus

## Doc Sync Plan (Conditional)
Test file updated; after Phase B passes:
- Update `docs/development/TEST_SUITE_INDEX.md` if row needs modification
- Update `docs/TESTING_GUIDE.md` §2 if selector pattern changed
- These updates should happen in Phase C (ledger closure)

---

**Galph Note**: Phase B changes the test expectation from `(Na×Nb×Nc)²` to `Na×Nb×Nc` per maintainer physics clarification. The actual simulator behavior was always correct — only the DBEX test expectation was wrong. This should result in test PASS after the fix.
