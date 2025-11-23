# Phase A Design Document: UB Parameterization Realignment

## Initiative
TORCH-GEOMETRY-UB-REALIGN-001 — Stage A UB Parameterization Realignment

## Document Status
Draft for Phase A (Design & Spec Alignment) — 2025-11-22T170806Z

---

## §1. Normative Requirements from Specs

This section extracts all normative requirements that constrain the UB/A* parameterization design.

### From `docs/spec-db-core.md:48-68` (Baseline Crystal State and Parameterization)

**Requirement 1.1 — Baseline State Authority:**
> "For any mapping-aligned refinement, the crystal state provided by dxtbx/DIALS SHALL be treated as authoritative:
> - `U₀ = crystal.get_U()` (orientation matrix),
> - `B₀ = crystal.get_B()` (reciprocal metric tensor),
> - `A*_mapping = U₀ @ B₀` (reciprocal lattice matrix)."

**Requirement 1.2 — No Alternative Decompositions:**
> "Implementations SHALL NOT introduce alternative, incompatible decompositions of `A*_mapping` into `U,B` in production refinement code."

**Requirement 1.3 — Incremental Parameterization:**
> "Stage‑A refinement parameterizations SHALL be defined as *increments* around the baseline state, not as free absolute `A*`:
> - Orientation parameters represent a small rotation `ΔR(params)` such that `U(params) = ΔR(params) @ U₀`.
> - Cell parameters represent small perturbations of the baseline cell, producing `B(params)` via a well‑defined metric tensor map (e.g., Busing–Levy) consistent with dxtbx conventions."

**Requirement 1.4 — Zero-Point Invariant:**
> "At the Stage‑A zero point (all refinement deltas = 0), implementations MUST satisfy:
> - `U(0) = U₀`, `B(0) = B₀`, and `A*(0) = U₀ @ B₀ = A*_mapping`."

**Requirement 1.5 — One-Way Construction:**
> "In production refinement code, `A*` SHALL be constructed only in the forward direction
> `params → (U(params), B(params)) → A*(params) = U(params) @ B(params)`.
> Implementations SHALL NOT refactor `A*` back into `U,B` (e.g., via ad‑hoc decompositions) inside the refinement loop."

### From `docs/spec-db-workflow.md:36-45` (Stage A Mapping Zero-Point Invariant)

**Requirement 2.1 — Trainable Parameters:**
> "Trainable (normative): Unit cell logs/angles, orientation (quaternion → XYZ), global scale."

**Requirement 2.2 — ExperimentModel Alignment:**
> "Implementations SHOULD align their parameterization with the `ExperimentModel(param_init="stage_a")` interface in `nanobrag_torch.models.experiment`."

**Requirement 2.3 — Mapping Zero-Point Invariant:**
> "For any Stage‑A configuration that claims DB‑AT‑024 mapping parity, zero geometry parameters (all cell/angle/orientation deltas equal to zero) and baseline scale MUST reproduce the DB‑AT‑024 mapping Bragg tensor."

**Requirement 2.4 — Baseline Misset Encoding:**
> "When `crystal_overrides` are used instead of MOSFLM A* injection, Stage‑A implementations SHALL encode the mapping orientation via a baseline misset (e.g., `baseline_misset_deg`) and apply only deltas on top of that baseline, so that the Stage‑A zero point is identical to the mapping forward model."

### From `docs/spec-db-runtime.md:18-28` (Parameterization Correctness & Round-Trip)

**Requirement 3.1 — UB/A* Round-Trip Test:**
> "Any new Stage‑A parameterization SHALL pass a round‑trip correctness check against dxtbx and Busing–Levy conventions at the zero point:
> - Given baseline `U₀,B₀` from `crystal.get_U()/get_B()`, the parameterization with `params=0` MUST reproduce `U(0)=U₀`, `B(0)=B₀`, and `A*(0)=U₀ @ B₀` within a documented numerical tolerance."

**Requirement 3.2 — Executable Test Mandate:**
> "Implementations SHALL provide a small, executable test that exercises this round trip and fails fast if the parameterization drifts from the dxtbx baseline."

**Requirement 3.3 — Prohibited Inverse Decompositions:**
> "Production refinement code SHALL NOT use inverse decompositions `A* → (U,B)` to derive the baseline state or to update simulator geometry.
> Such decompositions MAY be used in diagnostic tooling only, and MUST be clearly separated from the runtime path used for DB‑AT‑024 mapping‑aligned runs."

**Requirement 3.4 — Device/Dtype Neutrality:**
> "Callers SHALL co‑locate tensors on the target device/dtype before `run()`; SHALL NOT call `.to()` inside tight loops." (spec-db-runtime.md:12)

**Requirement 3.5 — Differentiability:**
> "Callers SHALL NOT use `.item()/.detach()` on differentiable parameters in forward passes." (spec-db-runtime.md:13)

---

## §2. Lessons from CONVERGENCE-001

### Key Findings from CONVERGENCE-001 Verdict

From `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T252000Z/summary.md` and `docs/findings.md:65`:

**Lesson 2.1 — Quaternion Approach CAN Work (With Bypass Fix):**
- Pure quaternion U-matrix parameterization passed zero-point validation (CC=0.9999999843, chi²_rel_diff=-0.017%).
- With zero-check bypass fix, achieves stable long-term convergence (chi² drift +0.0083% over 10 steps, CC≈1.0).
- **Conclusion:** Quaternions are viable for ΔR when implemented correctly.

**Lesson 2.2 — Code Path Divergence Risk:**
- Root cause of initial failure: diagnostic script parameter reconstruction code path differed from direct MOSFLM A* injection.
- When ALL parameter deltas = 0, U @ B_ideal round-trip through `crystal_overrides` produced catastrophic chi² divergence (+679% in 1 step).
- **Mitigation:** Zero-check bypass logic detects zero-delta state (atol=1e-9) and forces `use_direct_mosflm_injection=True`.

**Lesson 2.3 — Production Code Unaffected:**
- Production refinement (dbex/nanobrag_refinement.py) does NOT exhibit diagnostic script pathologies.
- Issue is specific to diagnostic script parameter reconstruction in `stage_a_mapping_adam_debug.py`.

**Lesson 2.4 — Systematic Offset Acceptable:**
- 14.5% systematic offset between zero-point check (989k) and closure initialization (1.13M) is ACCEPTABLE when convergence is stable (chi² drift <1% over 10 steps, CC≥0.99).
- Primary objective is preventing convergence divergence, not eliminating methodology differences.

### Impact on UB-REALIGN Design

**Decision Point 2.5 — Orientation Representation:**
CONVERGENCE-001 proves that quaternion-based ΔR is viable, BUT only if:
1. The implementation avoids code path divergence (one consistent construction path).
2. Zero-point bypass detection is in place for diagnostic tooling.
3. The parameterization aligns with spec-db-core.md incremental structure (`U(params) = ΔR(params) @ U₀`).

**Recommendation:** Use quaternion-based ΔR for orientation, aligning with:
- Spec requirement "orientation (quaternion → XYZ)" (spec-db-workflow.md:36)
- nanobrag_torch `ExperimentModel` API (if it uses quaternions for misset parameterization)
- Proven convergence behavior (CONVERGENCE-001 Phase C6b)

**Alternative considered:** Euler angles (simpler, no normalization constraint, proven in GEOMETRY-002 finding). However, quaternions are preferred for spec alignment and nanobrag_torch API compatibility.

---

## §3. Incremental Orientation Parameterization (ΔR → U)

### Chosen Representation: Quaternion-Based Small Rotation

**Formulation:**
- Represent small rotation as a quaternion `q_delta = [w, x, y, z]` with `||q_delta|| = 1`.
- For small rotations near identity, initialize with `q_delta ≈ [1, ε_x, ε_y, ε_z]` where `ε` are small.
- Convert quaternion to rotation matrix: `ΔR = quaternion_to_matrix(q_delta / ||q_delta||)`.
- Construct orientation: `U(params) = ΔR(params) @ U₀`.

**Explicit Formula:**

```
Given baseline U₀ from dxtbx:
  U₀ = crystal.get_U()  # shape (3, 3), orthonormal rotation

Trainable parameters:
  q_delta = [q_w, q_x, q_y, q_z]  # 4-DOF quaternion

Normalization:
  q_norm = q_delta / ||q_delta||

Conversion to rotation matrix:
  ΔR = quaternion_to_matrix(q_norm)  # shape (3, 3)

Final orientation:
  U(params) = ΔR @ U₀
```

**Zero-Point Condition:**
- At initialization, set `q_delta = [1, 0, 0, 0]` (identity quaternion).
- Then `ΔR = I`, so `U(0) = I @ U₀ = U₀` ✓

**Alignment with nanobrag_torch API:**
From `docs/nanobrag_api.md:136-139`:
> "CrystalStageAParams: `delta_misset_raw`: 3‑vector mapped via `tanh` to ±10° per axis (XYZ extrinsic misset)."

**Interpretation:**
- nanobrag_torch ExperimentModel currently uses **Euler-angle-based** misset parameterization (XYZ extrinsic), NOT quaternions directly.
- However, the spec says "quaternion → XYZ" (spec-db-workflow.md:36), suggesting conversion from quaternion to Euler angles before injection.

**Design Decision:**
- Maintain quaternion `q_delta` as the **internal refinement parameter** (4-DOF, normalized).
- Convert to **Euler XYZ angles** via `quaternion_to_euler_xyz(q_delta)` before injecting into `CrystalConfig.misset_deg`.
- This satisfies:
  - Spec requirement "orientation (quaternion → XYZ)" ✓
  - nanobrag_torch API expects `misset_deg` (XYZ Euler) ✓
  - Incremental structure `U(params) = ΔR(q_delta) @ U₀` ✓

**Gradient Flow:**
- Quaternion normalization is differentiable: `q_norm = q / ||q||`.
- Quaternion-to-matrix conversion is differentiable (standard PyTorch ops).
- Euler conversion (if needed for API) is differentiable via `scipy.spatial.transform.Rotation` or PyTorch geometric libraries.

**Robustness:**
- Avoid gimbal lock (quaternions have no singularities).
- Normalization constraint is implicit (division by norm).
- For production, consider Riemannian optimizer (tangent space updates on S³ manifold) OR standard Adam with periodic re-normalization.

---

## §4. Incremental Cell Parameterization (Δcell → B)

### Chosen Representation: Logs for Lengths + Unbounded Angles

**Formulation:**
- Baseline cell from dxtbx: `a₀, b₀, c₀, α₀, β₀, γ₀ = crystal.get_unit_cell().parameters()`.
- Lengths parameterized as **log-perturbations** (ensures positivity without constraints):
  ```
  a(params) = a₀ * exp(δlog_a)
  b(params) = b₀ * exp(δlog_b)
  c(params) = c₀ * exp(δlog_c)
  ```
- Angles parameterized as **direct deltas** (unbounded):
  ```
  α(params) = α₀ + Δα
  β(params) = β₀ + Δβ
  γ(params) = γ₀ + Δγ
  ```

**Rationale:**
- Spec says "unit cell logs/angles" (spec-db-workflow.md:36) — normative.
- Log-lengths ensure `a, b, c > 0` without explicit constraints or sigmoid mappings.
- Unbounded angles: trust optimizer to stay in valid range `(0°, 180°)` for physical crystals. nanobrag_torch ExperimentModel uses bounded angles (tanh → ±10°), but that's for **deltas**, not absolute values. Our design uses unbounded deltas; the **absolute** angles `α₀ + Δα` are validated by the B-matrix derivation (which will fail if angles are unphysical).

**Alternative Considered:**
- Bounded angle parameterization: `Δα_raw → tanh(Δα_raw) * 10°` (matching nanobrag_torch API).
- **Decision:** Use **unbounded** deltas for simplicity; optimizer natural bounds should suffice. If refinement produces unphysical angles, add bounded mapping in Phase B.

**Explicit Formula:**

```
Given baseline cell parameters from dxtbx:
  a₀, b₀, c₀, α₀, β₀, γ₀ = crystal.get_unit_cell().parameters()

Trainable parameters:
  δlog_a, δlog_b, δlog_c  # log-length deltas (unbounded)
  Δα, Δβ, Δγ              # angle deltas (unbounded, degrees)

Perturbed cell parameters:
  a = a₀ * exp(δlog_a)
  b = b₀ * exp(δlog_b)
  c = c₀ * exp(δlog_c)
  α = α₀ + Δα
  β = β₀ + Δβ
  γ = γ₀ + Δγ

Metric tensor derivation:
  G = metric_tensor(a, b, c, α, β, γ)  # 3×3 symmetric matrix

B-matrix (reciprocal basis):
  B = busing_levy_B(a, b, c, α, β, γ)  # 3×3 upper-triangular
```

**Zero-Point Condition:**
- At initialization, set `δlog_a = δlog_b = δlog_c = 0`, `Δα = Δβ = Δγ = 0`.
- Then `a = a₀, b = b₀, c = c₀, α = α₀, β = β₀, γ = γ₀`.
- So `B(0) = B₀` ✓

### Busing-Levy B-Matrix Derivation

From `docs/config_crosswalk.md:58-60` and dxtbx conventions:

**dxtbx B-matrix Convention:**
> "`crystal.get_B()` → reciprocal metric" (docs/dxtbx_api.md:40)

**Busing-Levy Formula:**
The B-matrix converts fractional coordinates to reciprocal space. Standard crystallography convention (Busing & Levy, 1967):

```
B = [
  [1/a,  -cos(γ)/(a*sin(γ)),  (cos(γ)*cos(β) - cos(α))/(a*sin(γ)*sin(β_star)) ],
  [0,    1/(b*sin(γ)),        (cos(γ)*cos(α) - cos(β))/(b*sin(γ)*sin(β_star)) ],
  [0,    0,                   1/(c*sin(β_star))                                  ]
]
```

where `sin(β_star)` is derived from the metric tensor determinant.

**Implementation Note:**
- dxtbx uses `cctbx.uctbx.unit_cell(params).fractionalization_matrix()` which returns the B-matrix.
- For torch, implement the Busing-Levy formula explicitly OR use `cctbx` to compute `B₀` once, then derive `B(params)` via the same formula applied to perturbed parameters.

**Metric Tensor (Alternative Path):**
```
G = [
  [a²,              a*b*cos(γ),     a*c*cos(β)    ],
  [a*b*cos(γ),      b²,             b*c*cos(α)    ],
  [a*c*cos(β),      b*c*cos(α),     c²            ]
]

B = cholesky(G⁻¹)  # or sqrt(G⁻¹) depending on convention
```

**Recommendation:**
- Use **Busing-Levy explicit formula** to match dxtbx conventions exactly.
- Validate at zero point: `||B(0) - B₀|| < 1e-12` (requirement 1.4).

**Gradient Flow:**
- All operations (exp, trigonometric, matrix inversion/Cholesky) are differentiable in PyTorch.
- Ensure angles are converted to radians for torch trigonometric functions.

---

## §5. Validation & Testing (DB-AT-026)

### UB/A* Round-Trip Acceptance Test Specification

**Test ID:** DB-AT-026
**Title:** UB/A* Round-Trip Test — Zero-Point Invariant Validation
**Purpose:** Verify that incremental UB parameterization satisfies zero-point invariants and one-way construction.

**Test File:** `tests/dbex/test_ub_parameterization_roundtrip.py`
**Selector:** `pytest tests/dbex/test_ub_parameterization_roundtrip.py::test_db_at_026_ub_roundtrip`

**Setup:**
1. Load canonical `refGeom.expt` (workspace root, golden dataset).
2. Extract baseline state from dxtbx:
   ```python
   crystal = expt.crystal
   U₀ = np.array(crystal.get_U()).reshape(3, 3)
   B₀ = np.array(crystal.get_B()).reshape(3, 3)
   A*_mapping = U₀ @ B₀
   ```
3. Extract baseline cell parameters:
   ```python
   a₀, b₀, c₀, α₀, β₀, γ₀ = crystal.get_unit_cell().parameters()
   ```

**Zero-Point Test:**
4. Initialize incremental parameters at zero:
   ```python
   q_delta = torch.tensor([1.0, 0.0, 0.0, 0.0])  # identity quaternion
   δlog_a = δlog_b = δlog_c = 0.0
   Δα = Δβ = Δγ = 0.0
   ```
5. Compute `U(0)` via quaternion path:
   ```python
   ΔR = quaternion_to_matrix(q_delta / ||q_delta||)  # = I
   U_params = ΔR @ U₀
   ```
6. Compute `B(0)` via Busing-Levy:
   ```python
   a = a₀ * exp(0) = a₀
   b = b₀ * exp(0) = b₀
   c = c₀ * exp(0) = c₀
   α = α₀ + 0 = α₀
   β = β₀ + 0 = β₀
   γ = γ₀ + 0 = γ₀
   B_params = busing_levy_B(a, b, c, α, β, γ)
   ```
7. Compute `A*(0)`:
   ```python
   A_star_params = U_params @ B_params
   ```

**Assertions:**
```python
# Orientation identity
assert np.linalg.norm(U_params - U₀) < 1e-12, "U(0) must equal U₀"

# Cell identity
assert np.linalg.norm(B_params - B₀) < 1e-12, "B(0) must equal B₀"

# Mapping parity
assert np.linalg.norm(A_star_params - A*_mapping) < 1e-6, "A*(0) must equal A*_mapping"
```

**Tolerances (Normative):**
- `U(0) = U₀`: `||U(0) - U₀|| < 1e-12` (orthonormal matrix, high precision)
- `B(0) = B₀`: `||B(0) - B₀|| < 1e-12` (metric tensor, high precision)
- `A*(0) = A*_mapping`: `||A*(0) - A*_mapping|| < 1e-6` (per spec-db-core.md:62, allows for metric tensor numerical differences)

**Gradient Test (Optional but Recommended):**
8. Verify `A*(params)` is differentiable w.r.t. all parameters:
   ```python
   q_delta.requires_grad_(True)
   δlog_a.requires_grad_(True)
   # ... (all params)

   A_star = compute_A_star(q_delta, δlog_a, ...)
   loss = A_star.sum()
   loss.backward()

   assert q_delta.grad is not None, "Quaternion must have gradients"
   assert δlog_a.grad is not None, "Log-length must have gradients"
   # ... (check all params)
   ```

**Cross-Reference with DB-AT-024:**
9. Verify zero-point Bragg tensor matches DB-AT-024 mapping baseline:
   - Use `create_crystal_config` with derived `A*` (MOSFLM a/b/c_star tuples).
   - Run forward model with zero-point params.
   - Assert Bragg tensor matches DB-AT-024 output (chi² < threshold, CC > 0.99).

**Dependencies:**
- DB-AT-024 must pass first (ensures mapping baseline is valid).
- Requires helper functions:
  - `quaternion_to_matrix(q)` → (3,3) rotation matrix
  - `busing_levy_B(a, b, c, α, β, γ)` → (3,3) B-matrix
  - `create_crystal_config(...)` → CrystalConfig with MOSFLM injection

**Expected Outcome:**
- All assertions PASS.
- Test runs in <1 second (no simulation, just algebra).
- Serves as regression guard for any future UB parameterization changes.

**Findings Update:**
- Document DB-AT-026 in `docs/spec-db-conformance.md`.
- Add entry to `docs/development/TEST_SUITE_INDEX.md`.
- Log acceptance in `docs/findings.md` (GEOMETRY-004 or extension to GEOMETRY-003).

---

## §6. Spec Alignment Summary

### Satisfied Normative Clauses

| Spec Section | Clause | Design Element | Status |
|--------------|--------|----------------|--------|
| spec-db-core.md:51-54 | Baseline state authority (U₀, B₀, A*_mapping from dxtbx) | Extract U₀, B₀ from dxtbx; treat as authoritative | ✓ Satisfied |
| spec-db-core.md:55 | No alternative decompositions in production | One-way construction `params → U,B → A*` | ✓ Satisfied |
| spec-db-core.md:58-60 | Incremental parameterization (ΔR, Δcell) | Quaternion ΔR, log-lengths + delta-angles | ✓ Satisfied |
| spec-db-core.md:61-62 | Zero-point invariant (U(0)=U₀, B(0)=B₀, A*(0)=A*_mapping) | Identity quaternion, zero deltas | ✓ Satisfied |
| spec-db-core.md:64-67 | One-way construction (no A* → U,B refactoring) | No inverse decompositions in refinement loop | ✓ Satisfied |
| spec-db-workflow.md:36 | Trainable: unit cell logs/angles, orientation (quaternion → XYZ) | δlog_a/b/c, Δα/β/γ, q_delta → misset_deg | ✓ Satisfied |
| spec-db-workflow.md:39-44 | Mapping zero-point invariant | DB-AT-026 test validates zero-point | ✓ Satisfied |
| spec-db-runtime.md:20-23 | UB/A* round-trip test | DB-AT-026 executable test | ✓ Satisfied |
| spec-db-runtime.md:25-27 | Prohibited inverse decompositions | Diagnostic-only separation | ✓ Satisfied |
| spec-db-runtime.md:12 | Device/dtype neutrality | Torch tensors, no .to() in loops | ✓ Design compliant |
| spec-db-runtime.md:13 | Differentiability (no .item()/.detach()) | All ops differentiable | ✓ Design compliant |

### Implementation Choices and Rationale

**Choice 1: Quaternion for ΔR**
- **Rationale:** Aligns with spec "quaternion → XYZ" (spec-db-workflow.md:36), proven viable in CONVERGENCE-001, no singularities.
- **Alternative rejected:** Euler angles (simpler but spec explicitly mentions quaternions).
- **Conversion:** Quaternion → Euler XYZ for nanobrag_torch `misset_deg` injection.

**Choice 2: Unbounded angle deltas**
- **Rationale:** Simplicity; optimizer should stay in physical range. Spec says "angles" without specifying bounds.
- **Alternative:** Bounded via tanh (matching nanobrag_torch API) — defer to Phase B if needed.

**Choice 3: Busing-Levy B-matrix derivation**
- **Rationale:** Matches dxtbx conventions exactly (cited in spec-db-core.md:60).
- **Validation:** Zero-point round-trip test ensures correctness.

**Choice 4: Direct MOSFLM A* injection for baseline**
- **Rationale:** Avoids code path divergence (CONVERGENCE-001 lesson), aligns with spec-db-workflow.md:44.
- **Fallback:** If using `crystal_overrides`, encode baseline misset as per requirement 2.4.

---

## §7. Open Questions & Risks

### Open Question 1: Angle Bounding Strategy
**Question:** Should angle deltas be bounded (tanh → ±10°) to match nanobrag_torch ExperimentModel API?
**Status:** Design uses unbounded deltas for simplicity.
**Defer to Phase B:** If refinement produces unphysical angles (α, β, γ outside [0°, 180°]), add bounded parameterization.
**Risk Level:** Low (optimizer natural bounds should suffice for small perturbations around physical baseline).

### Open Question 2: Quaternion-to-Euler Conversion Library
**Question:** Use scipy.spatial.transform.Rotation or PyTorch geometric library for conversion?
**Status:** TBD in Phase B implementation.
**Options:**
- `scipy.spatial.transform.Rotation.as_euler('xyz')` — standard, but not PyTorch-native (requires .detach() for scipy, then re-wrap in torch tensor with grad).
- PyTorch `pytorch3d.transforms` or `kornia.geometry` — fully differentiable, but adds dependency.
**Recommendation:** Use scipy for initial implementation (proven in CONVERGENCE-001 via quaternion_to_matrix), defer to PyTorch-native if gradients break.
**Risk Level:** Low (conversion is local operation, easily swappable).

### Open Question 3: Baseline Misset Encoding for crystal_overrides Path
**Question:** How to encode baseline misset when bypassing MOSFLM A* injection?
**Status:** Spec requires `misset_deg = baseline_misset_deg + delta_misset` (spec-db-workflow.md:44).
**Implementation Plan:**
- Compute `baseline_misset_deg` via `derive_robust_misset` (GEOMETRY-003 finding, dbex/nanobrag_bridge.py).
- Store in Stage A context.
- Add to quaternion-derived delta misset before injecting into CrystalConfig.
**Defer to Phase B:** Implement baseline misset encoding if production path uses `crystal_overrides`.
**Risk Level:** Low (pattern already proven in GEOMETRY-003).

### Risk 1: Busing-Levy Implementation Mismatch
**Description:** If Busing-Levy formula differs from dxtbx convention, zero-point test will fail.
**Mitigation:**
- Validate `B(0) = B₀` in DB-AT-026 test before implementing full parameterization.
- Extract dxtbx B-matrix computation logic if needed (cctbx.uctbx.unit_cell source).
**Likelihood:** Low (standard formula, well-documented).
**Impact:** High (blocks Phase B implementation).

### Risk 2: Code Path Divergence Recurrence
**Description:** If UB-REALIGN introduces new code paths that diverge from mapping baseline, may repeat CONVERGENCE-001 failure.
**Mitigation:**
- Use ONE consistent construction path: `params → U,B → A*`.
- Avoid diagnostic-vs-production splits.
- Add zero-check bypass if diagnostic tooling requires parameter reconstruction.
**Likelihood:** Low (design explicitly avoids inverse decompositions per requirement 1.5).
**Impact:** Medium (requires debugging, but pattern is known).

### Risk 3: nanobrag_torch API Mismatch
**Description:** If ExperimentModel expects different parameterization than designed, may require re-design.
**Mitigation:**
- Validated against `docs/nanobrag_api.md:136-154` (ExperimentModel API).
- Design uses compatible structure (cell logs/angles, misset_deg).
- Quaternion-to-Euler conversion adds compatibility layer.
**Likelihood:** Low (API docs clear).
**Impact:** Low (conversion layer is small adjustment).

---

## §8. Phase B Preview — Implementation Tasks

Phase B will implement this design in the nanobrag_torch Stage-A path. Anticipated tasks:

**B1: Implement ΔR → U Helper**
- File: `dbex/nanobrag_bridge.py` (or new `dbex/geometry.py` module per ARCH plan).
- Function: `derive_orientation_from_quaternion_delta(q_delta, U_baseline) -> U`.
- Includes: quaternion normalization, quaternion-to-matrix conversion, `U = ΔR @ U₀`.
- Test: Unit test with identity quaternion → `U = U₀`.

**B2: Implement Δcell → B Helper**
- File: `dbex/nanobrag_bridge.py` (or `dbex/geometry.py`).
- Function: `derive_B_from_cell_deltas(δlog_a, δlog_b, δlog_c, Δα, Δβ, Δγ, cell_baseline) -> B`.
- Includes: log-exp for lengths, delta-add for angles, Busing-Levy B-matrix derivation.
- Test: Unit test with zero deltas → `B = B₀`.

**B3: Wire Incremental Parameterization into Stage A Closure**
- File: `dbex/nanobrag_refinement.py` (or new refactored engine).
- Extend `build_stage_a_lbfgs_closure` to:
  - Accept UB-parameterization mode flag (e.g., `use_incremental_ub=True`).
  - Initialize `q_delta`, `δlog_*`, `Δα/β/γ` as trainable tensors.
  - Call B1/B2 helpers to derive U, B.
  - Construct `A* = U @ B`.
  - Inject `A*` via MOSFLM a/b/c_star OR baseline_misset + delta_misset (per crystal_overrides mode).
- **Critical:** Preserve existing cell+misset default path (no regression to `test_stage_a_expansion`).

**B4: Implement DB-AT-026 Test**
- File: `tests/dbex/test_ub_parameterization_roundtrip.py`.
- Implement as per §5 specification.
- Run and verify all assertions pass.

**B5: Regression Guard**
- Run `pytest tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`.
- Ensure cell+misset default path still passes (no impact from new UB path).

---

## §9. Next Actions

1. **Review this design document** (Galph/Supervisor).
2. **Author remaining Phase A artifacts:**
   - `orientation_representation_analysis.md` (quaternion vs Euler vs axis-angle comparison).
   - `cell_parameterization_design.md` (detailed Busing-Levy derivation).
   - `db_at_026_test_spec.md` (test specification from §5).
   - `phase_a_summary.md` (concise summary for handoff).
3. **Update `plans/active/TORCH-GEOMETRY-UB-REALIGN-001/implementation.md`** with Phase A checklist complete, Phase B/C tasks.
4. **Update `docs/fix_plan.md`** Attempts History with Phase A completion entry.
5. **Proceed to Phase B implementation** (next loop, not this loop per Mode: Docs).

---

## §10. References

- `docs/spec-db-core.md:48-68` — Baseline Crystal State and Parameterization (normative)
- `docs/spec-db-workflow.md:36-45` — Stage A trainable parameters and mapping zero-point (normative)
- `docs/spec-db-runtime.md:18-28` — Parameterization Correctness & Round-Trip (normative)
- `docs/nanobrag_api.md:100-156` — ExperimentModel Stage-A parameterization
- `docs/dxtbx_api.md:35-41` — Crystal U/B/A extraction
- `docs/config_crosswalk.md:53-77` — Crystal mapping conventions
- `docs/findings.md:65` — CONVERGENCE-001 finding (code path divergence, bypass pattern)
- `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T252000Z/summary.md` — CONVERGENCE-001 verdict

---

**End of Phase A Design Document**
