# Input for Loop i=158 (Ralph)

## Summary
Execute SPEC-SQUARE-PARTIALITY-001 Phase A: Clarify SQUARE lattice physics in docs and findings, codifying linear `Na×Nb×Nc` integrated intensity scaling per maintainer response.

## Mode
Docs

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
None — Phase A is docs-only (no code/test changes this loop).

## Artifacts
`plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T070000Z/`

## Findings Applied (Mandatory)
- **SIM-CONSTR-PARTIALITY-001**: Must update to demote `(Na×Nb×Nc)²` **integrated** scaling expectation to historical context; promote linear `Na×Nb×Nc` as enforceable requirement.
- **PROBE-FREEZE-001**: No new plan-local probes; reuse existing architecture tests in Phase B.

## Pointers
| Reference | Path | Section/Line |
|-----------|------|--------------|
| Spec | docs/spec-db-core.md | §60-140 (lattice/partiality) |
| Finding | docs/findings.md | SIM-CONSTR-PARTIALITY-001 |
| Maintainer Response | inbox/nanobrag_torch_response_2025_12_08.md | Full document |
| Implementation Plan | plans/active/SPEC-SQUARE-PARTIALITY-001/implementation.md | Phase A checklist |
| Fix Plan | docs/fix_plan.md | SPEC-SQUARE-PARTIALITY-001 row |

## ARCH Contracts (Mandatory)
| Contract ID | Doc Pointer | Owner Module/API | Failure Classification |
|-------------|-------------|------------------|------------------------|
| N/A | N/A | N/A | Phase A is docs-only; no ARCH contracts enforced this loop |

## Do Now (Hard Validity Contract)

### Focus: SPEC-SQUARE-PARTIALITY-001 Phase A — Clarify Physics

### Implement:
1. **A0 — Physics summary artifact**: Create `plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T070000Z/physics_summary.md` documenting:
   - Peak height scales as `(Na×Nb×Nc)²`
   - Integrated/summed intensity scales linearly as `Na×Nb×Nc`
   - Reference to `inbox/nanobrag_torch_response_2025_12_08.md`

2. **A1 — Update SIM-CONSTR-PARTIALITY-001**: Edit `docs/findings.md::SIM-CONSTR-PARTIALITY-001` to:
   - Demote old `(Na×Nb×Nc)²` integrated scaling expectation to historical context
   - Promote linear `Na×Nb×Nc` law as the enforceable requirement for integrated intensity
   - Add citation to maintainer response

3. **A2 — Optional spec clause** (if needed): If `docs/spec-db-core.md` contains any text implying `(Na×Nb×Nc)²` for integrated intensity, add a short "SQUARE lattice scaling behavior" paragraph clarifying peak vs integrated behavior.

4. **A3 — Create summary.md**: Document Phase A completion with artifact paths.

### Validating pytest selector(s):
- N/A (docs-only loop; tests unchanged until Phase B)

### Artifacts Path:
`plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T070000Z/`

### Initiative type consistent:
spec+tests ✓

## Touched
SPEC-SQUARE-PARTIALITY-001 Phase A (A0, A1, A2, A3)

## Forbidden This Loop
- Do NOT modify production code
- Do NOT modify test files (defer to Phase B)
- Do NOT create new plan-local probes per PROBE-FREEZE-001

## How-To Map

### Step 1: Create artifacts directory
```bash
mkdir -p plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T070000Z
```

### Step 2: Create physics_summary.md (A0)
Write to `plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T070000Z/physics_summary.md`:
```markdown
# SQUARE Lattice Scaling Physics Summary

## Key Result (from nanobrag_torch maintainer response)

Per `inbox/nanobrag_torch_response_2025_12_08.md`, the correct SQUARE lattice scaling behavior is:

1. **Peak intensity at exact Bragg condition**: ∝ `(Na×Nb×Nc)²`
   - The lattice factor F_latt peaks at integer HKL with amplitude proportional to Na×Nb×Nc
   - Peak height = |F_latt|² ∝ (Na×Nb×Nc)²

2. **Integrated/summed intensity over a reflection**: ∝ `Na×Nb×Nc` (linear)
   - When integrating over the full reflection profile (all subpixels, all angles)
   - The sinc² envelope integrates to a constant per unit cell
   - Total integrated intensity scales linearly with number of unit cells

## DBEX Expectation Mismatch (Historical)

Previous DBEX probes (ARCH-SIM-CONSTRUCTION-001 C.34-C.39) expected `(Na×Nb×Nc)²` for integrated intensity sums. This was physically incorrect. The ~11% deficit observed was consistent with linear scaling, not a sincg bug.

## Enforcement Implications

- Architecture test `tests/architecture/test_nanobrag_partiality.py` currently asserts `(Na×Nb×Nc)²` for `image.sum()` (integrated intensity) → MUST be changed to linear in Phase B
- If peak-height testing is desired, it must use exact Bragg condition sampling, not integration over the full image
```

### Step 3: Update docs/findings.md (A1)
Locate `SIM-CONSTR-PARTIALITY-001` and update to:
- Add "**Resolution (2025-12-08)**" section explaining the physics clarification
- Demote the old `(Na×Nb×Nc)²` integrated expectation as historical misunderstanding
- Cite `inbox/nanobrag_torch_response_2025_12_08.md`

### Step 4: Check docs/spec-db-core.md (A2)
Read lattice/partiality sections (§60-140). If any text implies `(Na×Nb×Nc)²` for integrated intensity, add clarifying paragraph. If text is already correct or absent, skip.

### Step 5: Create summary.md (A3)
Write Phase A completion summary with checklist status and artifact paths.

## Pitfalls To Avoid
1. **No code changes** — This is a docs-only Phase A loop
2. **No test changes** — Test modifications are Phase B
3. **Preserve existing findings structure** — Only add/update, don't delete historical context
4. **Cite maintainer response** — Must reference `inbox/nanobrag_torch_response_2025_12_08.md` in updates
5. **Don't over-specify spec** — Stick to minimal physics statement; implementation details in findings
6. **Mark implementation.md checklist items** — Update Phase A checkboxes after each task

## If Blocked
- If SIM-CONSTR-PARTIALITY-001 finding cannot be located: search for "partiality" in docs/findings.md and document discrepancy
- If spec-db-core.md has no lattice text: document as "no update needed" in summary.md
- If blocked, mark Phase A as blocked with rationale and switch focus per portfolio steering

## Doc Sync Plan (Conditional)
N/A — No tests added/renamed in Phase A.

---

**Galph Note**: Phase A is docs-only per implementation.md structure. Phase B (test updates) will follow in next loop. This establishes the physics contract before modifying enforcement tests.
