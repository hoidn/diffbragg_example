# TORCH-GEOMETRY-UB-REALIGN-001 Phase A — Design & Spec Alignment

## Summary
Design a concrete Stage-A UB/A* incremental parameterization that treats dxtbx crystal state (`U₀, B₀`) as authoritative, parameterizes orientation and cell as small perturbations (`ΔR`, `Δcell`), and satisfies the normative zero-point invariant and one-way construction requirements from spec-db-core.md and spec-db-workflow.md.

## Mode
**Docs** (Planning-only; no production code changes this loop)

## Focus
**TORCH-GEOMETRY-UB-REALIGN-001 — Stage A UB Parameterization Realignment**

## Branch
`integration`

## Mapped Tests
**None** — evidence-only / planning loop (no pytest selectors for design work)

## Artifacts
`plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-22T170806Z/`
- `phase_a_design_document.md` (comprehensive parameterization design with spec alignment)
- `db_at_026_test_spec.md` (UB/A* round-trip acceptance test specification)
- `orientation_representation_analysis.md` (comparison of Euler, axis-angle, quaternion approaches for ΔR)
- `cell_parameterization_design.md` (logs for lengths, bounded angles, metric tensor derivation)

---

## Do Now (Phase A Planning Tasks)

### 1. Read Normative Spec Sections (First Priority)
**Goal:** Extract every normative requirement for incremental UB/A* parameterization

**a) Read spec-db-core.md:48-68** (Baseline Crystal State and Parameterization):
```bash
# Extract key requirements:
# - Baseline state definition (U₀, B₀, A*_mapping)
# - Incremental parameterization contract (ΔR → U(params), Δcell → B(params))
# - Zero-point invariant (params=0 → U=U₀, B=B₀, A*=A*_mapping)
# - One-way construction (params → U,B → A*; no A* decomposition in refinement loop)
```

**b) Read spec-db-workflow.md:36-40** (Stage A mapping zero-point invariant):
```bash
# Extract:
# - Trainable parameters: unit cell logs/angles, orientation (quaternion → XYZ), global scale
# - Mapping zero-point requirement: zero deltas + baseline scale MUST reproduce DB-AT-024 mapping Bragg tensor
# - Alignment with ExperimentModel(param_init="stage_a") interface
```

**c) Read spec-db-runtime.md** (Parameterization Correctness & Round-Trip section if exists):
```bash
# Extract:
# - Device/dtype neutrality requirements
# - Autograd graph preservation for UB parameters
# - Constraints on tensor operations (detach placement, clone usage)
```

**Output:** Numbered list of ALL normative requirements in `phase_a_design_document.md` §1 (Normative Requirements from Specs)

### 2. Synthesize CONVERGENCE-001 Verdict Impact
**Goal:** Document lessons from CONVERGENCE-001 that constrain the UB-REALIGN design

**Read artifacts:**
- `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T252000Z/summary.md`
- `docs/findings.md` row 65 (CONVERGENCE-001)
- `plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T170806Z/closure_review.md`

**Extract lessons:**
1. Quaternion approach CAN work (with bypass fix), but exposed fragility in diagnostic scripts
2. Code path divergence risk when U/B_ideal round-trip through `crystal_overrides` differs from direct MOSFLM A* injection
3. Zero-check bypass pattern documented: detect when all params=0 and force direct injection
4. Production code (dbex/nanobrag_refinement.py) does NOT exhibit diagnostic script pathologies

**Decision Point:** Should UB-REALIGN-001 use quaternions for ΔR, or choose a different representation?
- **Option A:** Quaternion-based ΔR (align with nanobrag_torch ExperimentModel if it uses quaternions)
- **Option B:** Euler angle-based ΔR (simpler, no normalization constraint)
- **Option C:** Axis-angle representation (compact, well-defined for small rotations)

**Output:** Document CONVERGENCE-001 lessons in `phase_a_design_document.md` §2 (Lessons from CONVERGENCE-001) and initial orientation representation recommendation with rationale

### 3. Design Incremental Orientation Parameterization (ΔR → U)
**Goal:** Choose and specify ΔR representation with explicit formula `U(params) = ΔR(params) @ U₀`

**Analysis required:**
- **Quaternion approach:**
  - Parameterize small rotation quaternion `q_delta = [w, x, y, z]` with `w ≈ 1` for small rotations
  - Constraint: `||q_delta|| = 1` (normalization)
  - `ΔR = quaternion_to_matrix(q_delta / ||q_delta||)`
  - Pros: Aligns with spec-db-workflow.md "quaternion → XYZ"; potentially aligns with nanobrag_torch API
  - Cons: CONVERGENCE-001 exposed diagnostic script fragility; requires careful normalization handling

- **Euler angle approach:**
  - Parameterize three rotation angles `(δφ_x, δφ_y, δφ_z)` in radians
  - `ΔR = R_z(δφ_z) @ R_y(δφ_y) @ R_x(δφ_x)` (or ZYX convention matching dxtbx)
  - Pros: Simple, no constraints, well-tested in GEOMETRY-002 finding
  - Cons: Potential gimbal lock for large rotations (mitigated by "small rotation" assumption)

- **Axis-angle approach:**
  - Parameterize rotation axis `n = [n_x, n_y, n_z]` and angle `θ`
  - `ΔR = rodrigues_formula(n, θ)` or `axis_angle_to_matrix(θ * n)`
  - Pros: Compact (3 DOF instead of 4), well-defined for small rotations
  - Cons: Less common in crystallography APIs; may not align with nanobrag_torch

**Decision criteria:**
1. Alignment with spec-db-workflow.md normative "quaternion → XYZ" clause
2. Compatibility with nanobrag_torch `ExperimentModel` API (check docs/nanobrag_api.md)
3. Robustness (avoid CONVERGENCE-001-style code path divergence)
4. Simplicity of implementation and gradient flow

**Tasks:**
a) Read `docs/nanobrag_api.md` to check if ExperimentModel specifies orientation parameterization
b) Compare three approaches in `orientation_representation_analysis.md` with pros/cons/spec-alignment
c) Make recommendation based on criteria above
d) Write explicit formula for chosen `ΔR(params)` in `phase_a_design_document.md` §3

### 4. Design Incremental Cell Parameterization (Δcell → B)
**Goal:** Specify cell perturbation parameters and derivation of `B(params)` via metric tensor

**Spec requirement (spec-db-core.md:60):**
> Cell parameters represent small perturbations of the baseline cell, producing `B(params)` via a well-defined metric tensor map (e.g., Busing–Levy) consistent with dxtbx conventions.

**Parameterization options:**
- **Logs for lengths:** `δlog_a, δlog_b, δlog_c` → `a(params) = a₀ * exp(δlog_a)`, etc.
  - Ensures a, b, c > 0 without explicit constraints
  - Spec-db-workflow.md says "unit cell logs/angles" (normative)

- **Angles:** `δα, δβ, δγ` (in degrees or radians?)
  - Spec-db-workflow.md says "angles" (but doesn't specify bounded vs unbounded)
  - Need to ensure α, β, γ ∈ (0°, 180°) for physical crystals
  - **Decision:** Use bounded parameterization (e.g., sigmoid mapping) or trust optimizer to stay in valid range?

**Metric tensor derivation:**
- `G = metric_tensor(a, b, c, α, β, γ)` (symmetric 3×3 matrix)
- `B = sqrt(G⁻¹)` or `B = cholesky(G⁻¹)` (Busing-Levy reciprocal basis)
- **Critical:** Must match dxtbx `crystal.get_B()` convention at baseline (`δparams = 0`)

**Tasks:**
a) Document dxtbx B-matrix convention (read `docs/dxtbx_api.md`, `docs/config_crosswalk.md`)
b) Write explicit formulas for `a(params), b(params), c(params), α(params), β(params), γ(params)` in `cell_parameterization_design.md`
c) Specify metric tensor formula and B-matrix derivation (cite Busing-Levy paper or dxtbx source if needed)
d) Verify zero-point condition: when all `δ` params = 0, `B(0) = B₀` exactly
e) Document in `phase_a_design_document.md` §4 (Cell Parameterization)

### 5. Define DB-AT-026 (UB/A* Round-Trip Test) Specification
**Goal:** Write acceptance test spec that validates zero-point invariant and one-way construction

**Test requirements:**
1. **Setup:** Load canonical `refGeom.expt`, extract `U₀ = crystal.get_U()`, `B₀ = crystal.get_B()`, `A*_mapping = U₀ @ B₀`
2. **Zero-point test:** Set all refinement params to zero (`δlog_a=0, δlog_b=0, ..., q_delta=[1,0,0,0]` or `δφ=0`)
3. **Compute:** `U(0) = ΔR(0) @ U₀`, `B(0) = metric_tensor_to_B(a₀, b₀, c₀, α₀, β₀, γ₀)`, `A*(0) = U(0) @ B(0)`
4. **Assert:**
   - `||U(0) - U₀|| < 1e-12` (orientation identity)
   - `||B(0) - B₀|| < 1e-12` (cell identity)
   - `||A*(0) - A*_mapping|| < 1e-6` (mapping parity, per spec-db-core.md:62)
5. **Gradient test (optional):** Verify `A*(params)` is differentiable w.r.t. all params (no detached tensors)

**Additional checks:**
- Test that `create_crystal_config` accepts the derived `A*` (mosflm_a/b/c_star tuples) without errors
- Test that zero-point Bragg tensor matches DB-AT-024 mapping baseline (cross-reference existing test)

**Tasks:**
a) Write full test specification in `db_at_026_test_spec.md` with setup, assertions, and expected tolerances
b) Document test file location (`tests/dbex/test_ub_parameterization_roundtrip.py` or similar)
c) Note dependencies: DB-AT-024 must pass first (ensure mapping baseline is valid)
d) Reference in `phase_a_design_document.md` §5 (Validation & Testing)

### 6. Update Implementation Plan with Phase A Outcomes
**Goal:** Populate `plans/active/TORCH-GEOMETRY-UB-REALIGN-001/implementation.md` with design decisions

**Tasks:**
a) Read existing `plans/active/TORCH-GEOMETRY-UB-REALIGN-001/implementation.md` (currently a stub)
b) Add Phase A checklist with completion status:
   - [x] A1: Normative requirements synthesis
   - [x] A2: Orientation representation choice (Quaternion/Euler/Axis-angle)
   - [x] A3: Cell parameterization design (logs + angles)
   - [x] A4: DB-AT-026 test specification
   - [x] A5: Design document authored
c) Draft Phase B overview (Implementation & Wiring):
   - B1: Implement ΔR → U helper in `dbex/nanobrag_bridge.py`
   - B2: Implement Δcell → B helper (metric tensor + Busing-Levy derivation)
   - B3: Wire incremental parameterization into Stage A closure (replace or extend current cell+misset path)
   - B4: Implement DB-AT-026 test
   - B5: Regression guard (test_stage_a_expansion must pass)
d) Draft Phase C overview (Validation & Rollout):
   - C1: Run DB-AT-026 (zero-point round-trip)
   - C2: Run DB-AT-024 (mapping parity with new parameterization)
   - C3: Stage A smoke test with incremental UB params
   - C4: Findings update (GEOMETRY-004 or extension to GEOMETRY-003)
   - C5: Documentation sync (TESTING_GUIDE.md, TEST_SUITE_INDEX.md)

### 7. Write Phase A Summary
**Goal:** Create comprehensive summary for next loop handoff

**Required sections:**
- **Chosen Parameterization Summary:**
  - Orientation: [Quaternion/Euler/Axis-angle] for ΔR with formula
  - Cell: Logs for lengths + [bounded/unbounded] angles with metric tensor derivation
  - Zero-point invariant: Explicit conditions at params=0
- **Spec Alignment:**
  - List of satisfied normative clauses from spec-db-core.md and spec-db-workflow.md
  - Any deviations or implementation choices (with rationale)
- **DB-AT-026 Test Summary:**
  - Test file, selector, acceptance criteria
- **Open Questions / Risks:**
  - e.g., "Need to verify nanobrag_torch ExperimentModel API alignment" if docs unclear
  - e.g., "Angle bounding strategy TBD (sigmoid vs trust optimizer)"
- **Next Loop Preview:**
  - Phase B1-B5 tasks ready for implementation
  - Expected file changes (dbex/nanobrag_bridge.py, tests/dbex/test_ub_parameterization_roundtrip.py)

**Output:** `plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-22T170806Z/phase_a_summary.md`

### 8. Update Fix Plan Ledger
**Goal:** Add Phase A Attempts History entry to `docs/fix_plan.md`

**Entry template:**
```
* 2025-11-22T170806Z (Galph, planning) — **Phase A Design & Spec Alignment COMPLETE.** Synthesized normative requirements from spec-db-core.md §Baseline Crystal State (incremental UB/A* parameterization, zero-point invariant, one-way construction) and spec-db-workflow.md §Stage A (trainable cell logs/angles + orientation, mapping zero-point requirement). Analyzed CONVERGENCE-001 lessons (quaternion approach viable with bypass fix; code path divergence risk documented). Designed incremental orientation parameterization ([CHOSEN: Quaternion/Euler/Axis-angle]) with explicit formula `U(params) = ΔR(params) @ U₀` and incremental cell parameterization (logs for lengths + [bounded/unbounded] angles) with Busing-Levy metric tensor derivation `B(params)`. Authored DB-AT-026 (UB/A* round-trip test) specification with zero-point assertions (`||U(0)-U₀||<1e-12`, `||B(0)-B₀||<1e-12`, `||A*(0)-A*_mapping||<1e-6`). Updated implementation.md with Phase A checklist complete and Phase B/C overview. **Artifacts:** plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-22T170806Z/{phase_a_design_document.md, db_at_026_test_spec.md, orientation_representation_analysis.md, cell_parameterization_design.md, phase_a_summary.md}. **Next Actions:** Phase B implementation (B1: ΔR helper, B2: Δcell helper, B3: Stage A closure wiring, B4: DB-AT-026 test, B5: regression guard).
```

**Tasks:**
a) Locate the correct insertion point in `docs/fix_plan.md` (after UB-REALIGN-001 "Attempts History:" line)
b) Insert the entry with actual chosen parameterization details (replace `[CHOSEN: ...]` with actual decision)
c) Verify entry follows ledger conventions (timestamp, action type, metrics, artifacts, next actions)

---

## How-To Map

### Environment Setup
```bash
# No special environment needed for docs-only loop
# All work is reading specs and authoring markdown documents
```

### Spec Reading Commands
```bash
# Read normative sections
cat docs/spec-db-core.md | sed -n '48,68p'  # Baseline Crystal State
cat docs/spec-db-workflow.md | sed -n '36,40p'  # Stage A trainable params
cat docs/spec-db-runtime.md | grep -A 20 "Parameterization Correctness"  # If exists

# Read CONVERGENCE-001 verdict
cat plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T252000Z/summary.md
cat docs/findings.md | sed -n '65p'  # CONVERGENCE-001 row
```

### Document Creation Workflow
```bash
# Create design documents under artifacts directory
mkdir -p plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-22T170806Z
cd plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-22T170806Z

# Write each document in sequence (Tasks 1-7)
# phase_a_design_document.md (main design with all sections)
# db_at_026_test_spec.md (test specification)
# orientation_representation_analysis.md (ΔR approach comparison)
# cell_parameterization_design.md (Δcell formulas)
# phase_a_summary.md (loop summary)
```

### Implementation Plan Update
```bash
# Update the plan file
vim plans/active/TORCH-GEOMETRY-UB-REALIGN-001/implementation.md
# Populate Phase A checklist, draft Phase B/C overviews
```

### Fix Plan Ledger Update
```bash
# Insert Attempts History entry
vim docs/fix_plan.md
# Find "### [TORCH-GEOMETRY-UB-REALIGN-001]" section
# Add entry under "Attempts History:" line
```

---

## Pitfalls To Avoid

1. **Do NOT implement production code this loop** — Mode: Docs means planning/design only; all code stays in design documents
2. **Do NOT guess spec requirements** — Read the normative sections verbatim; quote exact clauses when documenting alignment
3. **Do NOT choose parameterization without analysis** — Document pros/cons of all options (quaternion, Euler, axis-angle) before recommendation
4. **Do NOT forget zero-point validation** — Every design formula must be verified to satisfy `U(0)=U₀`, `B(0)=B₀`, `A*(0)=A*_mapping`
5. **Do NOT ignore CONVERGENCE-001 lessons** — Code path divergence risk is real; design must avoid fragile round-trip conversions
6. **Do NOT skip metric tensor derivation** — B-matrix must match dxtbx conventions exactly; cite Busing-Levy or dxtbx source
7. **Do NOT write DB-AT-026 test code yet** — Only specification this loop; test implementation happens in Phase B4
8. **Do NOT forget device/dtype neutrality** — All formulas must work on CPU/GPU, float32/float64 (per spec-db-runtime.md)
9. **Do NOT assume nanobrag_torch API alignment** — Check docs/nanobrag_api.md; document any mismatches or unknowns
10. **Do NOT leave open questions unresolved** — If uncertain (e.g., angle bounding strategy), document options and defer decision to Phase B with explicit note

---

## If Blocked

**Scenario 1: Normative spec unclear or contradictory**
- Document the ambiguity in `phase_a_design_document.md` §Open Questions
- Propose two alternatives with pros/cons
- Recommend one based on best engineering judgment
- Flag for Galph review next loop

**Scenario 2: Cannot determine nanobrag_torch API alignment**
- Check `docs/nanobrag_api.md` for ExperimentModel orientation parameterization
- If missing, document "TBD — verify nanobrag_torch API in Phase B" and proceed with spec-compliant design
- Worst case: design may need minor adjustments in Phase B to align with actual API

**Scenario 3: Busing-Levy metric tensor derivation unfamiliar**
- Search codebase for existing B-matrix derivations (`grep -r "metric_tensor" dbex/`)
- Check dxtbx source if available (`grep -r "get_B" simtbx_project/`)
- Use standard crystallography formula: `G_ij = a_i · a_j` (dot product of real-space basis vectors)
- Document formula with citation if needed

**Scenario 4: Uncertainty about quaternion vs Euler choice**
- Default to **Euler angles** if spec-db-workflow.md "quaternion → XYZ" is ambiguous
- Rationale: GEOMETRY-002 finding documents Euler inversion as proven approach; CONVERGENCE-001 showed quaternion fragility in diagnostics
- Document both options fully; recommend Euler with clear justification

---

## Findings Applied (Mandatory)

**Applied from docs/findings.md:**

1. **GEOMETRY-001** (detector mapping) — NOT directly applicable (focus is crystal parameterization, not detector geometry)
2. **GEOMETRY-002** (Euler inversion) — **APPLICABLE** — If choosing Euler angles for ΔR, use analytic inversion formula from detector matrix recovery (proven approach per finding)
3. **GEOMETRY-003** (B_ideal-based mapping misset) — **APPLICABLE** — Baseline misset derivation lessons may inform ΔR zero-point alignment; ensure `U(0) @ B₀` reproduces mapping A* exactly
4. **DXTBX-001** (crystal API) — **APPLICABLE** — `crystal.get_A()` returns 9-element tuple (row-major); `U₀ = np.array(crystal.get_U()).reshape(3,3)`, `B₀ = np.array(crystal.get_B()).reshape(3,3)`
5. **REFINE-001** (LBFGS scale warm-start) — NOT directly applicable (focus is parameterization design, not optimizer tuning)
6. **GRADIENT-001** (autograd graph preservation) — **APPLICABLE** — Ensure `U(params)` and `B(params)` derivations do NOT call `.item()`, `.numpy()`, or `.detach()` inappropriately; all tensors must preserve gradients
7. **CONVERGENCE-001** (zero-check bypass pattern) — **HIGHLY APPLICABLE** — Code path divergence risk when U/B round-trip differs from direct MOSFLM injection; design must ensure production refinement uses ONE path consistently (no diagnostic vs production split)

**Additional findings reviewed but not directly applicable:** PHYSICS-LOSS series (loss function, not parameterization), PERF-WARM series (performance, not design), CLI series (interface, not math).

---

## Pointers

**Normative Specs:**
- `docs/spec-db-core.md:48-68` — Baseline Crystal State and Parameterization (authoritative)
- `docs/spec-db-workflow.md:36-40` — Stage A trainable parameters and mapping zero-point invariant
- `docs/spec-db-runtime.md` — Device/dtype neutrality (search for "Parameterization" section)
- `docs/spec-db-conformance.md` — DB-AT-024 mapping parity baseline (cross-reference for DB-AT-026)

**CONVERGENCE-001 Artifacts:**
- `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T252000Z/summary.md` — Final verdict
- `docs/findings.md:65` — CONVERGENCE-001 finding (bypass pattern, systematic offset handling)

**PARITY-003 Closure:**
- `plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T170806Z/closure_review.md` — Archival rationale

**API Documentation:**
- `docs/dxtbx_api.md` — Crystal U/B matrix extraction
- `docs/nanobrag_api.md` — ExperimentModel interface (check for param_init="stage_a")
- `docs/config_crosswalk.md` — dxtbx → nanobrag_torch mapping conventions

**Implementation Plan:**
- `plans/active/TORCH-GEOMETRY-UB-REALIGN-001/implementation.md` — Update with Phase A outcomes

**Fix Plan Ledger:**
- `docs/fix_plan.md:63-80` — TORCH-GEOMETRY-UB-REALIGN-001 section (insert Attempts History entry)

**Findings Ledger:**
- `docs/findings.md:6,7,8,10,52,65` — Rows for GEOMETRY-001/002/003, DXTBX-001, GRADIENT-001, CONVERGENCE-001

---

## Next Up (Optional)

If Phase A completes early and all design documents are authored:
1. **Proofread design documents** — Check for internal consistency (formulas match across docs)
2. **Cross-reference specs** — Verify every normative requirement from specs is addressed in design
3. **Draft Phase B task breakdown** — Expand Phase B overview in implementation.md with file-by-file changes
4. **Sketch test structure** — Outline DB-AT-026 test file structure (setup, fixtures, assertions) without writing code

Do NOT proceed to Phase B implementation (production code) this loop per Mode: Docs constraint.

---

## Doc Sync Plan
**Not applicable** — No tests added/renamed this loop (planning-only)

---

**END OF INPUT.MD**
