# Input — Ralph Loop i=138

**Summary**: Execute ARCH-GRADIENT-FLOW-001 Phase A.1-A.2 — call graph trace and suspect module audit to identify gradient flow break root cause.

**Mode**: none (evidence collection)

**ActionType**: planning

**DecisionStatus**: exploring

**InitiativeType**: architecture

**Focus**: [ARCH-GRADIENT-FLOW-001] — Gradient Flow Restoration (DB-AT-010 Unblock)

**Branch**: integration

**Mapped tests**: none — Phase A evidence collection (no test execution required)

**Artifacts**: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T212000Z/`

---

## Findings Applied (Mandatory)

### GRADIENT-001 (Gradient test patterns)
**Reference**: `docs/findings.md::GRADIENT-001`
**Relevance**: Tests use `crystal_overrides` dict to inject differentiable parameters (correct pattern verified). Production code must preserve gradient flow.
**Code**: `tests/dbex/test_gradients.py` (test harness)
**Adherence**: Phase A audit will identify production code breaking gradient despite correct test pattern.

### RUNTIME-001 (Runtime execution guardrails)
**Reference**: `docs/findings.md::RUNTIME-001`, `docs/pytorch_runtime_checklist.md:26`
**Relevance**: DB-AT-010 requires `NANOBRAGG_DISABLE_COMPILE=1` to avoid Dynamo interference (already confirmed in Phase B.1 verification).
**Adherence**: Not directly applicable to Phase A audit (no test execution this loop).

### TESTING-003 (Acceptance test registry maintenance)
**Reference**: `docs/findings.md::TESTING-003`, `docs/development/TEST_SUITE_INDEX.md`
**Relevance**: DB-AT-010 status will update from FAILING → PASSING after fix (deferred to Phase B.4).
**Adherence**: Not applicable to Phase A (doc updates conditional on fix completion).

---

## ARCH Contracts (Mandatory)

### ARCH-CONTRACT-GRADIENT-FLOW (Implicit, to be formalized Phase B.3)
**Owner module/API**: `dbex/physics/forward.py::simulate_forward_torch` (primary entry point for differentiable forward simulation)
**Forbidden duplicates**: N/A (forward simulation is centralized)
**Classification**: **Implementation bug** — gradient flow break in production code, not architecture violation
**Evidence**: Ralph's i=136 verification shows 5/5 gradcheck tests fail with identical signature: `GradcheckError: Numerical gradient for function expected to be zero` (disconnected autograd graph).
**Hypothesis**: `.item()` coercion or `.detach()` call breaks gradient propagation from loss → refined parameters.
**Pointers**:
- `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T204336Z/db_at_010_status_verification.md` (failure signature)
- `docs/spec-db-runtime.md` §Gradient Hygiene (differentiability requirements)

### ARCH-CONTRACT-TESTING-001 (Test harness import stability)
**Owner module/API**: `tests/dbex/` (test suite structure)
**Status**: **CONFORMING** — Ralph's i=136 verification had 0 collection errors (harness stable after Phase B.3/B.4 fixes).
**Relevance**: Confirms problem is NOT in test harness (production code issue).

### ARCH-CONTRACT-FORWARD-SIMULATION (Implicit)
**Owner module/API**: `dbex/physics/forward.py::simulate_forward_torch`
**Responsibility**: Differentiable forward simulation preserving autograd graph from refined parameters → loss output.
**Classification**: **Implementation bug** — contract currently violated (gradient flow broken).
**Phase A objective**: Identify exact violation point (file:line where gradient graph disconnects).

---

## Pointers

### Evidence Artifacts (DB-AT-SUITE-CARE-001 Phase B.1, i=136)
- **Verification report**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T204336Z/db_at_010_status_verification.md`
- **Pytest log**: `plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-07T204336Z/pytest_db_at_010_verification.log`
- **Failure signature**: GradcheckError at `torch/autograd/gradcheck.py:981` (disconnected graph)
- **Loss magnitude**: ~3.66e+09 (consistent across all 5 tests, proving forward simulation executes)

### SPEC
- **docs/spec-db-conformance.md** §Gradient-Safe Profile — DB-AT-010 acceptance criteria (eps=1e-6, atol=1e-5, rtol≈0.05)
- **docs/spec-db-core.md** §Objective Function — Variance-weighted loss definition (lines 57-68)
- **docs/spec-db-runtime.md** §Gradient Hygiene — Differentiability requirements for refinement parameters

### ARCH
- **docs/architecture.md** §13 Common Pitfalls — Device/dtype neutrality, square-pixel enforcement (to be extended Phase B.4: gradient flow preservation)
- **docs/architecture/module_map.md** — Physics/geometry module ownership (forward.py, crystallography.py)
- **docs/architecture/data_telemetry_flow.md** — Forward simulation → loss computation path

### Testing Docs
- **docs/TESTING_GUIDE.md** §1.4 — DB-AT-010 selector pattern, canonical flags, gradcheck scope note (lines 175-177)
- **docs/development/TEST_SUITE_INDEX.md** — DB-AT-010 status row (currently FAILING)

### Implementation Plan
- **plans/active/ARCH-GRADIENT-FLOW-001/implementation.md** — Full Phases A/B/C structure with tasks, validation, exit criteria
- **plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T210000Z/planning_notes.md** — Context, objectives, Phase A design, risks, expected flow

---

## Do Now

### Phase A.1 — Call Graph Trace

**Objective**: Map full execution path from test → forward → loss → backward to identify module boundaries and tensor flow points.

**Steps**:

1. **Start from test entry point**:
   - File: `tests/dbex/test_gradients.py`
   - Function: `test_db_at_010_gradcheck_crystal_cell_a` (line ~230 per verification report)
   - Review test fixture setup, config assembly, parameter injection pattern

2. **Trace forward simulation path**:
   - Follow `simulate_forward_torch` call (likely in test helper or inline)
   - Map imports: `test → dbex/physics/forward.py → dbex/geometry/crystallography.py`
   - Document each function crossing with file:line references
   - Note where `crystal_overrides` dict is consumed (TorchCrystal instantiation?)

3. **Trace loss computation**:
   - Find masked MSE computation (likely `dbex/physics/loss.py::_compute_variance_weighted_loss`)
   - Document how target/model tensors flow into loss
   - Note variance/sigma handling (potential `.item()` risk in denominator)

4. **Trace backward pass**:
   - Find gradcheck invocation (likely `torch.autograd.gradcheck` at test line ~230)
   - Document gradcheck config (eps, atol, rtol per spec)

5. **Create call graph diagram**:
   ```
   test_gradients.py::test_db_at_010_gradcheck_crystal_cell_a (line X)
     → [helper or inline call]
     → dbex/physics/forward.py::simulate_forward_torch (line Y)
       → dbex/geometry/crystallography.py::TorchCrystal (line Z)
         → [crystal_overrides consumption, cell parameter hydration]
       → nanobrag_torch.Simulator (external, assume gradient-safe)
     → dbex/physics/loss.py::_compute_variance_weighted_loss (line W)
     → torch.autograd.gradcheck (line X)
   ```

6. **Write output artifact**:
   - File: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T212000Z/call_graph_trace.md`
   - Contents: Diagram + ≥5 call stack levels with file:line references + tensor flow notes

**Validation**: ≥5 module/function boundaries documented, tensor flow points identified (where `requires_grad=True` tensors pass between functions).

---

### Phase A.2 — Suspect Module Audit

**Objective**: Search high-risk gradient break patterns in 4 key production modules.

**Modules to Audit**:
1. `dbex/physics/forward.py` (primary suspect: simulate_forward_torch entry point)
2. `dbex/geometry/crystallography.py` (TorchCrystal parameter hydration)
3. `dbex/physics/loss.py` (variance-weighted loss computation)
4. `dbex/refinement/inputs.py` (RefinementInputs assembly, config hydration)

**High-Risk Patterns to Search**:
1. `.item()` — Converts tensor to Python scalar (breaks autograd)
2. `.detach()` or `.data` — Explicitly removes gradient tracking
3. `.numpy()` — Moves to NumPy (non-differentiable)
4. In-place ops on leaf tensors: `*=`, `+=`, `.copy_()` when `requires_grad=True`
5. `.cpu()` without grad retention — Device move losing gradient

**Grep Commands** (execute from repo root):
```bash
# Create artifact directory
mkdir -p plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T212000Z

# Search for .item() calls
grep -n '\.item()' dbex/physics/forward.py dbex/geometry/crystallography.py dbex/physics/loss.py dbex/refinement/inputs.py > plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T212000Z/grep_item.txt

# Search for .detach() calls
grep -n '\.detach()' dbex/physics/forward.py dbex/geometry/crystallography.py dbex/physics/loss.py dbex/refinement/inputs.py > plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T212000Z/grep_detach.txt

# Search for .numpy() calls
grep -n '\.numpy()' dbex/physics/forward.py dbex/geometry/crystallography.py dbex/physics/loss.py dbex/refinement/inputs.py > plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T212000Z/grep_numpy.txt

# Search for in-place ops
grep -n '\*=' dbex/physics/forward.py dbex/geometry/crystallography.py dbex/physics/loss.py dbex/refinement/inputs.py > plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T212000Z/grep_inplace_mul.txt
grep -n '+=' dbex/physics/forward.py dbex/geometry/crystallography.py dbex/physics/loss.py dbex/refinement/inputs.py > plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T212000Z/grep_inplace_add.txt

# Search for .cpu() calls
grep -n '\.cpu()' dbex/physics/forward.py dbex/geometry/crystallography.py dbex/physics/loss.py dbex/refinement/inputs.py > plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T212000Z/grep_cpu.txt
```

**Analysis Steps** (for each grep result):
1. Open file at reported line number
2. Read surrounding context (±5 lines)
3. Classify as **SAFE** (pattern on non-grad tensor) or **UNSAFE** (pattern on `requires_grad=True` tensor or parameter)
4. For UNSAFE matches: document exact line, surrounding code, hypothesis (e.g., "loss.py:145 uses `.item()` on variance denominator, likely breaking gradient")

**Write output artifact**:
- File: `plans/active/ARCH-GRADIENT-FLOW-001/reports/2025-12-07T212000Z/suspect_audit.md`
- Contents:
  - Summary table: `| Module | .item() | .detach() | .numpy() | inplace | .cpu() | Total Unsafe |`
  - Detailed analysis: For each UNSAFE match, document file:line, code snippet, classification, hypothesis
  - Top candidate: Single most likely root cause based on grep evidence

**Validation**: ≥4 modules audited, ≥10 grep matches analyzed (SAFE vs UNSAFE classification), top candidate identified.

---

### Deliverables (This Loop)

1. **call_graph_trace.md** — Execution path diagram with ≥5 call stack levels
2. **grep_*.txt** — 6 grep output files (item, detach, numpy, inplace_mul, inplace_add, cpu)
3. **suspect_audit.md** — Analysis of grep results with SAFE/UNSAFE classification, top candidate hypothesis
4. **summary.md** — Loop summary with Phase A.1-A.2 completion status, preliminary hypothesis, next action (Phase A.3 gradient probe OR Phase B.1 fix if evidence strong)

---

## Pitfalls To Avoid

1. **Do not execute tests this loop** — Phase A is evidence collection only (call graph + grep audit). Test execution deferred to Phase B.2 (gradcheck verification after fix).

2. **Do not implement fixes this loop** — Phase A objective is localization only. Fix implementation in Phase B.1 after hypothesis ranking (A.4).

3. **Environment freeze** — No package installs/upgrades. If grep reveals issues in nanobrag_torch (external), mark as blocked_pending_environment.

4. **Type discipline** — This is architecture (gradient flow contract enforcement), not bugfix. Classification correct because enforcement test (Phase B.3) required.

5. **Thin wrapper guardrail** — Phase A.3 gradient probe (next loop) must stay <400 LOC. Phase A.1-A.2 are grep/read only (no script creation).

6. **Parity-first not applicable** — DB-AT-010 is gradcheck (correctness), not numerical parity. No parity metrics needed.

7. **Evidence→Action contract** — This loop's output (call graph + grep audit) must enable Phase B.1 fix identification. If not, Phase A.3 gradient probe required (next loop).

8. **Do not speculate on fix** — Grep audit should classify patterns as SAFE/UNSAFE based on code context, not implement patch. Phase B.1 will handle fix.

9. **Cliff avoidance not applicable** — DB-AT-010 gradcheck failure is deterministic (not numerical instability). No cliff risk.

10. **Probe saturation not applicable yet** — This is first evidence loop. Budget: 2 probes allowed before fix required.

---

## If Blocked

### Scenario 1: Grep finds no obvious .item()/.detach() calls
**Action**: Proceed to Phase A.3 (gradient probe) next loop to isolate which module breaks gradient empirically.
**Rationale**: Gradient break may be in nanobrag_torch upstream or hidden in property getter/setter.

### Scenario 2: Grep finds >10 unsafe patterns across multiple modules
**Action**: Rank by proximity to test entry point (call graph order). Fix top-ranked candidate first (Phase B.1), re-run gradcheck, iterate if needed.
**Rationale**: Multiple gradient breaks possible; incremental fixes required.

### Scenario 3: Call graph trace reveals gradient break in nanobrag_torch (external)
**Action**: Mark ARCH-GRADIENT-FLOW-001 as blocked_pending_environment. Document in problems.md for maintainer escalation. Consider spec_change to relax gradcheck tolerances as contingency.
**Rationale**: External gradient breaks outside dbex scope; requires upstream fix or acceptance criteria adjustment.

### Scenario 4: Grep audit takes >2 hours (manual analysis bottleneck)
**Action**: Complete grep commands, defer detailed analysis to partial deliverable. Note which modules remain unaudited in summary.md. Continue Phase A.2 next loop if needed.
**Rationale**: Phase A.1-A.2 can split across 2 loops if grep results extensive.

---

## Expected Runtime

- **Call graph trace (A.1)**: ~30-45 min (file reads, import chain following, diagram authoring)
- **Grep commands (A.2)**: ~5 min (6 commands, redirect to files)
- **Grep analysis (A.2)**: ~60-90 min (10-20 matches, context reads, SAFE/UNSAFE classification)
- **Artifact writing (summary.md)**: ~15 min

**Total**: ~2-2.5 hours

---

## Success Criteria

- ✅ **call_graph_trace.md exists** with ≥5 call stack levels documented
- ✅ **6 grep output files exist** (grep_item.txt, grep_detach.txt, grep_numpy.txt, grep_inplace_mul.txt, grep_inplace_add.txt, grep_cpu.txt)
- ✅ **suspect_audit.md exists** with ≥10 matches analyzed, SAFE/UNSAFE classification, top candidate hypothesis
- ✅ **summary.md exists** with Phase A.1-A.2 completion status, preliminary hypothesis, next action recommendation

---

**Prepared by**: Galph (Loop i=137)
**For**: Ralph (Loop i=138)
**Focus**: ARCH-GRADIENT-FLOW-001 Phase A.1-A.2 — Call graph trace + suspect module audit
**Next**: Phase A.3 (gradient probe, loop i=139) OR Phase B.1 (fix, loop i=139 if A.1-A.2 evidence conclusive)
