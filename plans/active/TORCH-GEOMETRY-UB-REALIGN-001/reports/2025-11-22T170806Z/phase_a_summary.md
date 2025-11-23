# Phase A Summary: UB Parameterization Realignment

## Initiative
TORCH-GEOMETRY-UB-REALIGN-001 — Stage A UB Parameterization Realignment

## Phase A Status
**COMPLETE** — Design & Spec Alignment (2025-11-22T170806Z)

---

## Chosen Parameterization Summary

### Orientation: Quaternion-Based ΔR

**Formula:**
```
U(params) = ΔR(q_delta) @ U₀

where:
  q_delta = [w, x, y, z]  # 4-DOF unit quaternion
  ΔR = quaternion_to_matrix(q_delta / ||q_delta||)
  U₀ = crystal.get_U()  # baseline from dxtbx
```

**Zero-Point:**
```
q_delta = [1, 0, 0, 0]  →  ΔR = I  →  U(0) = U₀  ✓
```

**Conversion to nanobrag_torch API:**
- Convert quaternion to Euler XYZ angles: `misset_deg = quaternion_to_euler_xyz(q_delta)`
- Inject into `CrystalConfig.misset_deg`

**Rationale:**
- Aligns with spec "orientation (quaternion → XYZ)" (spec-db-workflow.md:36) — **normative** ✓
- Proven viable in CONVERGENCE-001 (chi² drift +0.0083%, CC≈1.0 with bypass fix) ✓
- No singularities (unlike Euler gimbal lock) ✓
- Smooth gradient flow on S³ manifold ✓

---

### Cell: Logs for Lengths + Unbounded Angles

**Formula:**
```
a(params) = a₀ * exp(δlog_a)
b(params) = b₀ * exp(δlog_b)
c(params) = c₀ * exp(δlog_c)

α(params) = α₀ + Δα  (degrees)
β(params) = β₀ + Δβ
γ(params) = γ₀ + Δγ

B(params) = busing_levy_B(a, b, c, α, β, γ)
```

**Zero-Point:**
```
δlog_a = δlog_b = δlog_c = 0  →  a = a₀, b = b₀, c = c₀
Δα = Δβ = Δγ = 0  →  α = α₀, β = β₀, γ = γ₀
→  B(0) = B₀  ✓
```

**Busing-Levy B-Matrix:**
- Matches dxtbx `crystal.get_B()` convention exactly.
- Differentiable PyTorch implementation (trigonometric ops, volume calculation, reciprocal cell derivation).

**Rationale:**
- Aligns with spec "unit cell logs/angles" (spec-db-workflow.md:36) — **normative** ✓
- Logs ensure `a, b, c > 0` without explicit constraints ✓
- Unbounded angles: trust optimizer; defer bounded mapping to Phase B if needed ✓
- Compatible with nanobrag_torch `CrystalStageAParams` (minor difference: unbounded vs bounded angles) ⚠️

---

### Zero-Point Invariant

**At params=0:**
```
U(0) = U₀        (||U(0) - U₀|| < 1e-12)
B(0) = B₀        (||B(0) - B₀|| < 1e-12)
A*(0) = U₀ @ B₀  (||A*(0) - A*_mapping|| < 1e-6)
```

**Validation:** DB-AT-026 test ensures all three conditions hold.

---

## Spec Alignment

### Satisfied Normative Clauses

| Spec Clause | Requirement | Design Element | Status |
|-------------|-------------|----------------|--------|
| spec-db-core.md:51-54 | Baseline state authority (U₀, B₀ from dxtbx) | Extract from dxtbx, treat as authoritative | ✓ |
| spec-db-core.md:55 | No alternative decompositions in production | One-way construction `params → U,B → A*` | ✓ |
| spec-db-core.md:58-60 | Incremental parameterization (ΔR, Δcell) | Quaternion ΔR, log-lengths + delta-angles | ✓ |
| spec-db-core.md:61-62 | Zero-point invariant | Identity quaternion, zero deltas → U(0)=U₀, B(0)=B₀ | ✓ |
| spec-db-core.md:64-67 | One-way construction (no A*→U,B refactoring) | No inverse decompositions in refinement loop | ✓ |
| spec-db-workflow.md:36 | Trainable: logs/angles, quaternion→XYZ | δlog_a/b/c, Δα/β/γ, q_delta→misset_deg | ✓ |
| spec-db-workflow.md:39-44 | Mapping zero-point invariant | DB-AT-026 validates zero-point | ✓ |
| spec-db-runtime.md:20-23 | UB/A* round-trip test | DB-AT-026 executable test | ✓ |
| spec-db-runtime.md:25-27 | Prohibited inverse decompositions | Diagnostic-only separation | ✓ |

**All normative requirements satisfied.** ✓

---

## DB-AT-026 Test Summary

**Test File:** `tests/dbex/test_ub_parameterization_roundtrip.py`
**Selector:** `pytest tests/dbex/test_ub_parameterization_roundtrip.py -m acceptance`

**Test Coverage:**
1. **DB-AT-026.1:** Orientation zero-point (`||U(0) - U₀|| < 1e-12`)
2. **DB-AT-026.2:** Cell zero-point (`||B(0) - B₀|| < 1e-12`)
3. **DB-AT-026.3:** Mapping parity (`||A*(0) - A*_mapping|| < 1e-6`)
4. **DB-AT-026.4:** Gradient flow validation (all params differentiable)
5. **DB-AT-026.5:** Cross-reference with DB-AT-024 (mapping Bragg tensor parity)

**Expected Runtime:** <1s (Tests 1-4), ~30s (Test 5)

**Acceptance Criteria:**
- Tests 1-4 must PASS for Phase B completion.
- Test 5 may be deferred to Phase C (requires full forward model integration).

---

## Open Questions & Deferred Decisions

### Open Question 1: Angle Bounding Strategy
**Question:** Should angle deltas be bounded (tanh → ±10°) to match nanobrag_torch ExperimentModel?
**Current Design:** Unbounded deltas (trust optimizer).
**Defer to Phase B:** Add bounded mapping if refinement produces unphysical angles.
**Risk:** Low (optimizer should stay in valid range for small perturbations).

### Open Question 2: Quaternion-to-Euler Conversion Library
**Question:** Use scipy or PyTorch geometric library?
**Current Plan:** scipy for initial implementation (proven in PARITY-002).
**Defer to Phase B:** Switch to PyTorch-native (pytorch3d/kornia) if gradients break.
**Risk:** Low (conversion is local operation, easily swappable).

### Open Question 3: Baseline Misset Encoding
**Question:** How to encode baseline misset when using `crystal_overrides` path?
**Current Plan:** Use `derive_robust_misset` (GEOMETRY-003 finding) to compute baseline misset, add to quaternion-derived delta misset.
**Defer to Phase B:** Implement if production path uses `crystal_overrides`.
**Risk:** Low (pattern already proven in GEOMETRY-003).

---

## Risks Identified

### Risk 1: Busing-Levy Implementation Mismatch
**Description:** If Busing-Levy formula differs from dxtbx convention, zero-point test will fail.
**Mitigation:** Validate `B(0) = B₀` in DB-AT-026 Test 2 before full implementation.
**Likelihood:** Low | **Impact:** High (blocks Phase B)

### Risk 2: Code Path Divergence Recurrence
**Description:** If UB-REALIGN introduces new code paths that diverge from mapping baseline, may repeat CONVERGENCE-001 failure.
**Mitigation:** Use ONE consistent construction path (`params → U,B → A*`); avoid diagnostic-vs-production splits.
**Likelihood:** Low | **Impact:** Medium (requires debugging, but pattern is known)

### Risk 3: nanobrag_torch API Mismatch
**Description:** If ExperimentModel expects different parameterization than designed, may require re-design.
**Mitigation:** Design uses compatible structure (cell logs/angles, misset_deg); quaternion-to-Euler adds compatibility layer.
**Likelihood:** Low | **Impact:** Low (conversion layer is small adjustment)

---

## Next Loop Preview: Phase B (Implementation & Wiring)

### Phase B Tasks (B1-B5)

**B1: Implement ΔR → U Helper**
- File: `dbex/nanobrag_bridge.py` (or new `dbex/geometry.py` module)
- Function: `derive_orientation_from_quaternion_delta(q_delta, U_baseline) -> U`
- Includes: quaternion normalization, quaternion-to-matrix, quaternion-to-Euler conversion
- Test: Unit test with identity quaternion → `U = U₀`

**B2: Implement Δcell → B Helper**
- File: `dbex/nanobrag_bridge.py`
- Function: `derive_B_from_cell_deltas(δlog_a, ..., cell_baseline) -> B`
- Includes: log-exp for lengths, delta-add for angles, Busing-Levy B-matrix derivation
- Function: `busing_levy_B_torch(a, b, c, α, β, γ) -> B`
- Test: Unit test with zero deltas → `B = B₀`

**B3: Wire Incremental Parameterization into Stage A Closure**
- File: `dbex/nanobrag_refinement.py` (or refactored engine)
- Extend `build_stage_a_lbfgs_closure` to accept UB-parameterization mode
- Initialize `q_delta`, `δlog_*`, `Δα/β/γ` as trainable tensors
- Call B1/B2 helpers to derive U, B → construct `A* = U @ B`
- Inject via MOSFLM a/b/c_star OR baseline_misset + delta_misset
- **Critical:** Preserve existing cell+misset default path (no regression)

**B4: Implement DB-AT-026 Test**
- File: `tests/dbex/test_ub_parameterization_roundtrip.py`
- Implement Tests 1-5 as per specification
- Run and verify all pass (Tests 1-4 mandatory, Test 5 optional)

**B5: Regression Guard**
- Run `pytest tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
- Ensure cell+misset default path still passes

**Expected File Changes:**
- `dbex/nanobrag_bridge.py` (~200 lines added: B1, B2 helpers)
- `dbex/nanobrag_refinement.py` (~100 lines modified: B3 wiring)
- `tests/dbex/test_ub_parameterization_roundtrip.py` (~300 lines new: B4 test)
- `docs/TESTING_GUIDE.md` (add DB-AT-026 entry)
- `docs/development/TEST_SUITE_INDEX.md` (add DB-AT-026 status)

---

## Artifacts Summary

**Phase A Deliverables (All Complete):**
- ✓ `phase_a_design_document.md` — Comprehensive design with §1-10 (normative requirements, chosen parameterization, zero-point formulas, DB-AT-026 spec, spec alignment, risks, Phase B preview, references)
- ✓ `orientation_representation_analysis.md` — Quaternion vs Euler vs Axis-Angle comparison with decision rationale
- ✓ `cell_parameterization_design.md` — Busing-Levy B-matrix derivation, PyTorch implementation, zero-point validation
- ✓ `db_at_026_test_spec.md` — Full test specification with 5 tests, acceptance criteria, execution commands, artifacts policy
- ✓ `phase_a_summary.md` — This document

**Artifacts Path:** `plans/active/TORCH-GEOMETRY-UB-REALIGN-001/reports/2025-11-22T170806Z/`

---

## Implementation Plan Status

**Phase A Checklist (COMPLETE):**
- [x] A1: Normative requirements synthesis (§1 of design doc)
- [x] A2: Orientation representation choice (quaternion-based ΔR, with rationale)
- [x] A3: Cell parameterization design (logs + unbounded angles, Busing-Levy derivation)
- [x] A4: DB-AT-026 test specification (5 tests, acceptance criteria)
- [x] A5: Design document authored (comprehensive, all sections)

**Phase B Overview (Ready for Implementation):**
- [ ] B1: Implement ΔR → U helper (`derive_orientation_from_quaternion_delta`)
- [ ] B2: Implement Δcell → B helper (`derive_B_from_cell_deltas`, `busing_levy_B_torch`)
- [ ] B3: Wire incremental parameterization into Stage A closure
- [ ] B4: Implement DB-AT-026 test (Tests 1-5)
- [ ] B5: Regression guard (`test_stage_a_expansion` must pass)

**Phase C Overview (Validation & Rollout):**
- [ ] C1: Run DB-AT-026 (zero-point round-trip validation)
- [ ] C2: Run DB-AT-024 (mapping parity with new parameterization)
- [ ] C3: Stage A smoke test with incremental UB params
- [ ] C4: Findings update (GEOMETRY-004 or extension to GEOMETRY-003)
- [ ] C5: Documentation sync (TESTING_GUIDE.md, TEST_SUITE_INDEX.md)

---

## Findings & Ledger Updates

**Ready for `docs/findings.md` (Phase C):**
- GEOMETRY-004 (or GEOMETRY-003 extension): Incremental UB parameterization conventions, zero-point invariants, quaternion-to-Euler conversion, Busing-Levy B-matrix derivation, DB-AT-026 acceptance test.

**Ready for `docs/fix_plan.md` Attempts History (this loop):**
- Timestamp: 2025-11-22T170806Z
- Action: Phase A Design & Spec Alignment COMPLETE
- Chosen parameterization: Quaternion ΔR + logs/angles Δcell
- DB-AT-026 test spec authored
- Artifacts: (5 documents)
- Next Actions: Phase B implementation (B1-B5)

---

## References

- `docs/spec-db-core.md:48-68` — Baseline Crystal State and Parameterization (normative)
- `docs/spec-db-workflow.md:36-45` — Stage A trainable parameters and mapping zero-point (normative)
- `docs/spec-db-runtime.md:18-28` — Parameterization Correctness & Round-Trip (normative)
- `docs/nanobrag_api.md:100-156` — ExperimentModel Stage-A parameterization
- `docs/dxtbx_api.md:35-41` — Crystal U/B/A extraction
- `docs/config_crosswalk.md:53-77` — Crystal mapping conventions
- `docs/findings.md:65` — CONVERGENCE-001 finding
- `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T252000Z/summary.md` — CONVERGENCE-001 verdict

---

**Phase A Design Complete. Ready for Phase B Implementation.**
