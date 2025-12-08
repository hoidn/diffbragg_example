# Input for Ralph (Loop i=164)

## Summary
Execute RUNTIME-VEC-001 Phase A (Evidence & Scope Definition) — confirm nanobrag_torch CLI accessibility, inventory source-weight tests, define artifact policy.

## BindingForRalph
- **ActionType:** evidence_collection
- **DecisionStatus:** exploring
- **InitiativeType:** perf

## SupervisorMode
none (evidence collection, no specific mode lens)

## Focus
RUNTIME-VEC-001 — Runtime Vectorization Checklist Enforcement (Phase A)

## Branch
integration

## Mapped Tests
- `pytest --collect-only tests/dbex/test_runtime_vectorization.py 2>&1 || echo "Test file may not exist yet"` — check if test file exists
- No production test execution required for Phase A (evidence collection)

## Artifacts
`plans/active/RUNTIME-VEC-001/reports/2025-12-08T140000Z/`

## Findings Applied (Mandatory)
- **RUNTIME-001** — Runtime guard for source equal-weighting (relevant policy for this initiative)
- **PROBE-FREEZE-001** — No new plan-local scripts; evidence collection via existing APIs and inspection

## Pointers
- Plan: `plans/active/RUNTIME-VEC-001/implementation.md` — Phase A checklist
- Fix-plan row: `docs/fix_plan.md` Tier 1 line 465 — [RUNTIME-VEC-001]
- Spec refs: `docs/architecture/pytorch_design.md` §1.1.5 (source weighting), `docs/pytorch_runtime_checklist.md` item #4 (source equal-weight)
- Finding: `docs/findings.md` — RUNTIME-001 (source weight runtime guard)

## ARCH Contracts (mandatory)
1. **ARCH-CONTRACT-RUNTIME-001**: Source equal-weighting
   - Owner: `nanobrag_torch` simulator runtime (source weight normalization)
   - Classification: implementation work (test porting)

---

## Do Now

**Focus:** RUNTIME-VEC-001 Phase A (Evidence & Scope Definition)

### Execute Phase A tasks from `plans/active/RUNTIME-VEC-001/implementation.md`:

#### A1: Confirm nanobrag_torch CLI accessibility and capture spec references
1. **Test nanobrag_torch import:**
   ```bash
   cd /home/ollie/Documents/diffbragg_example
   python -c "import nanobrag_torch; print(f'nanobrag_torch version: {getattr(nanobrag_torch, \"__version__\", \"unknown\")}')" 2>&1
   ```
2. **Check for CLI entry points (if any):**
   ```bash
   python -c "from nanobrag_torch import Simulator; print('Simulator import OK')" 2>&1
   ```
3. **Capture spec references:**
   - Read `docs/architecture/pytorch_design.md` §1.1.5 for source weighting design
   - Read `docs/pytorch_runtime_checklist.md` item #4 for source equal-weight rule
   - Document relevant excerpts in `plans/active/RUNTIME-VEC-001/reports/2025-12-08T140000Z/a1_spec_refs.md`

#### A2: Inventory TestSourceWeights test cases
1. **Locate existing source-weight tests:**
   ```bash
   # Check if nanoBragg tests exist in the workspace
   find /home/ollie/Documents/nanoBragg -name "*source*weight*" -o -name "test_cli_scaling*" 2>/dev/null | head -20
   ```
2. **Inventory test cases from the editable nanobrag_torch source:**
   - Look in `/home/ollie/Documents/nanoBragg/tests/` for `test_cli_scaling.py` or similar
   - Document which assertions map to DBEX needs (equal weighting, divergence parity)
   - Note required fixtures/artifacts
3. **Write inventory to:**
   `plans/active/RUNTIME-VEC-001/reports/2025-12-08T140000Z/a2_test_inventory.md`

#### A3: Define artifact policy and planned pytest selectors
1. **Artifact policy:**
   - Define where test metrics should be written on failure (e.g., `$RUNTIME_VEC_ARTIFACT_DIR`)
   - Define JSON schema for metrics output (optional but recommended)
2. **Planned pytest selectors:**
   - Proposed test file: `tests/dbex/test_runtime_vectorization.py`
   - Proposed test class: `TestRuntimeVectorization`
   - Proposed test names: `test_source_weights_ignored_per_spec`, `test_source_weights_divergence_parity` (if applicable)
3. **Environment flags:**
   - Document any required env vars (e.g., `KMP_DUPLICATE_LIB_OK=TRUE`, device selection)
4. **Write artifact policy to:**
   `plans/active/RUNTIME-VEC-001/reports/2025-12-08T140000Z/a3_artifact_policy.md`

#### A4: Create summary.md
- Write `plans/active/RUNTIME-VEC-001/reports/2025-12-08T140000Z/summary.md` documenting:
  - Phase A completion status (A1/A2/A3 checked)
  - Key findings (nanobrag_torch accessibility, test inventory count, artifact policy decisions)
  - Scoped Phase B tasks based on inventory

#### A5: Update implementation.md
- Mark Phase A tasks (A1, A2, A3) as complete in `plans/active/RUNTIME-VEC-001/implementation.md`

---

## How-To Map

```bash
# Set environment
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
cd /home/ollie/Documents/diffbragg_example

# A1: Test nanobrag_torch accessibility
python -c "import nanobrag_torch; print('OK')"

# A2: Find existing source-weight tests
find /home/ollie/Documents/nanoBragg -type f -name "*.py" -exec grep -l "source.*weight\|SourceWeight" {} \; 2>/dev/null

# Create artifacts directory (if needed)
mkdir -p plans/active/RUNTIME-VEC-001/reports/2025-12-08T140000Z

# A3: Check for existing test file
ls -la tests/dbex/test_runtime_vectorization.py 2>&1 || echo "File does not exist yet (expected)"
```

## Pitfalls To Avoid
1. **Do not create new probe scripts** — PROBE-FREEZE-001 applies; use existing test utilities and APIs
2. **Do not implement tests yet** — Phase A is evidence collection only; Phase B handles implementation
3. **Do not modify production code** — This is a harness/perf initiative; production changes require separate initiative
4. **Check nanoBragg source tree** — The editable install is at `/home/ollie/Documents/nanoBragg`, not the vendored `src/nanobrag-torch`
5. **Document deferral if test suite is minimal** — If nanoBragg has limited source-weight tests, document this and scope Phase B accordingly

## Forbidden This Loop
- No new plan-local scripts (per PROBE-FREEZE-001)
- No production code changes
- No test implementation (Phase B)

## If Blocked
If nanobrag_torch is not importable or source-weight tests don't exist:
- Record the blocker in summary.md
- Document what infrastructure would be needed
- Consider whether initiative should be deferred or rescoped
- Mark RUNTIME-VEC-001 as `blocked_missing_upstream_tests` if no TestSourceWeights found

---

## Exit Criteria Preview (for Phase A)

| Task | Expected Outcome |
|------|------------------|
| A1 | nanobrag_torch imports successfully; spec refs documented |
| A2 | Inventory of source-weight tests (count + mapping to DBEX) |
| A3 | Artifact policy + pytest selectors documented |
| summary.md | Created with Phase A findings |
