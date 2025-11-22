# Input for Ralph — TORCH-GEOMETRY-PARITY-002 Phase B1-B7 Implementation

## Summary
Implement quaternion-based U-matrix direct parameterization for Stage A to eliminate the 1.37e-3 symmetric strain blocking refinement convergence. Phase B delivers the core implementation (helpers, quaternion ops, config flag, closure branching, parity probe extension, gradcheck) so Phase C can validate <1e-6 parity and stable convergence.

## Mode
none

## Focus
TORCH-GEOMETRY-PARITY-002 — Direct U-Matrix Parameterization for Stage A Geometry Refinement

## Branch
integration

## Mapped Tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (regression guard, existing — must pass with default cell+misset path)
- New: `tests/dbex/test_u_matrix_gradcheck.py::test_quaternion_roundtrip` (Phase B7, gradcheck for quaternion ops)
- New: `tests/dbex/test_u_matrix_gradcheck.py::test_u_matrix_closure_gradcheck` (Phase B7, gradcheck for U-matrix LBFGS closure)

## Artifacts
`plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T105837Z/`
- `phase_a0_evidence_synthesis.md` (completed by Galph)
- `so3_parameterization_survey.md` (completed by Galph)
- `api_design_and_risks.md` (completed by Galph)
- `gradcheck_quaternion_ops.log` (Phase B2, new)
- `gradcheck_u_matrix_closure.log` (Phase B7, new)
- `pytest_stage_a_regression.log` (Phase C4 preview, regression guard)

## Do Now

Implement Phase B checklist items B1-B7 from `plans/active/TORCH-GEOMETRY-PARITY-002/implementation.md`. Deliver the quaternion-based U-matrix parameterization infrastructure without yet validating parity or convergence (Phase C scope).

### Phase B1: U-matrix helper (`derive_u_matrix_from_mosflm_a_star`)
**Target:** `dbex/nanobrag_bridge.py::derive_u_matrix_from_mosflm_a_star`

- Signature: `def derive_u_matrix_from_mosflm_a_star(a_star: np.ndarray, cell: CellParams) -> np.ndarray:`
- Extract B_ideal_reciprocal from cell using existing helper (e.g., `_build_b_ideal_from_cell_params` or equivalent)
- Compute `U = a_star @ np.linalg.inv(B_ideal_reciprocal)` — **do NOT call `proper_rotation()` or any SO(3) projection**
- Return U (3×3 numpy array, may have det(U) ≈ 1 ± ε if strain present)
- Add docstring: "Extract U-matrix from mapping MOSFLM A* without SO(3) projection (GEOMETRY-004, TORCH-GEOMETRY-PARITY-002)."

### Phase B2: Quaternion ops (roundtrip conversion + validation)
**Target:** `dbex/nanobrag_bridge.py::matrix_to_quaternion`, `::quaternion_to_matrix`

- Implement `matrix_to_quaternion(U: Union[np.ndarray, torch.Tensor]) -> torch.Tensor` using `scipy.spatial.transform.Rotation.from_matrix(U).as_quat()` (scipy convention: [x, y, z, w]), convert to torch.Tensor
- Implement `quaternion_to_matrix(q: torch.Tensor) -> torch.Tensor` using `scipy.spatial.transform.Rotation.from_quat(q.detach().cpu().numpy()).as_matrix()`, convert to torch.Tensor
- Add roundtrip validation test in `tests/dbex/test_u_matrix_gradcheck.py::test_quaternion_roundtrip`:
  - Generate random rotation matrix U_0 (use `scipy.spatial.transform.Rotation.random().as_matrix()`)
  - Convert U_0 → q → U_1
  - Assert `torch.allclose(U_1, torch.tensor(U_0), atol=1e-6)`
- Run test, capture log in `plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T105837Z/gradcheck_quaternion_ops.log`

### Phase B3: Config flag (`use_u_matrix_parameterization`)
**Target:** `dbex/nanobrag_refinement.py` (or `dbex/config.py` if central config exists)

- Add `use_u_matrix_parameterization: bool = False` field to wherever Stage A config lives (likely inline in `build_mapping_stage_a_context` or a `RefinementConfig` dataclass if one exists)
- If no central config exists, add it as a parameter to `build_mapping_stage_a_context`
- CLI plumbing (deferred to Phase C unless trivial): if there's already a `--` flag pattern for Stage A, add `--use-u-matrix` parsing and pass through

### Phase B4: U-matrix initialization in `build_mapping_stage_a_context`
**Target:** `dbex/nanobrag_refinement.py::build_mapping_stage_a_context`

- Add branching logic near the existing baseline misset derivation:
  ```python
  if use_u_matrix_parameterization:
      U_0 = derive_u_matrix_from_mosflm_a_star(mapping_a_star_np, cell_params)
      q_0 = matrix_to_quaternion(torch.tensor(U_0, dtype=torch.float64))
      q_params = q_0.clone().requires_grad_(True)
      # Store in StageAContext (extend dataclass with q_params: Optional[torch.Tensor] = None)
  else:
      # Existing cell+misset path (orientation_vec, cell_logs, angle_raws)
      ...
  ```
- Extend `StageAContext` dataclass with new field: `q_params: Optional[torch.Tensor] = None`

### Phase B5: Closure branching in `build_stage_a_lbfgs_closure`
**Target:** `dbex/nanobrag_refinement.py::build_stage_a_lbfgs_closure`

- Add U-matrix path inside the closure:
  ```python
  def closure():
      if config.use_u_matrix_parameterization:
          # U-matrix path
          q_norm = stage_a_ctx.q_params / torch.norm(stage_a_ctx.q_params)  # Enforce ‖q‖=1
          U = quaternion_to_matrix(q_norm)  # 3x3 rotation matrix
          A_star_new = U @ B_ideal_reciprocal_torch  # Compute updated A*
          # Update crystal_overrides['A_star'] with A_star_new (convert to numpy if needed)
          crystal_config_updated = ...  # existing pattern for updating crystal_overrides
      else:
          # Existing cell+misset path (orientation_vec, cell_logs, angle_raws)
          ...

      # Forward pass, loss, backward (unchanged from existing code)
      ...
      return loss
  ```
- Ensure `B_ideal_reciprocal_torch` is computed once before the closure (from cell params) and captured in the closure scope

### Phase B6: Parity probe extension
**Target:** `plans/active/TORCH-REFINE-002E/bin/probe_crystal_matrix_parity.py`

- Add `--use-u-matrix` CLI flag
- When `--use-u-matrix` is True:
  - Initialize U-matrix from MOSFLM A* using `derive_u_matrix_from_mosflm_a_star` (no SO(3) projection)
  - Convert to quaternion q₀
  - Run forward pass (convert quaternion → U → A* via `quaternion_to_matrix`)
  - Compare reconstructed A* against mapping MOSFLM A* (compute `max_abs_diff`)
  - Emit JSON with additional fields: `{"u_matrix_mode": true, "quaternion_initial": [...], "max_abs_diff": ..., "quaternion_norm": ...}`
- Keep existing cell+misset path as default (when `--use-u-matrix` is False)

### Phase B7: Gradcheck for U-matrix closure
**Target:** `tests/dbex/test_u_matrix_gradcheck.py::test_u_matrix_closure_gradcheck`

- Create minimal synthetic test case:
  - Initialize quaternion q (random or from identity)
  - Compute A* = quaternion_to_matrix(q / ‖q‖) @ B_ideal_reciprocal
  - Run a tiny forward pass (single pixel, single HKL, synthetic target)
  - Compute variance-weighted loss
  - Use `torch.autograd.gradcheck` to verify gradients w.r.t. q are correct
- Run with `NANOBRAGG_DISABLE_COMPILE=1` (per RUNTIME-001)
- Capture log in `plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T105837Z/gradcheck_u_matrix_closure.log`

### Regression Guard (Phase C Preview)
**Target:** `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`

- After implementing B1-B7, run the existing Stage A expansion smoke with **default config** (use_u_matrix_parameterization=False) to ensure no regressions in the cell+misset path
- Command: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
- Capture log in `plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T105837Z/pytest_stage_a_regression.log`
- **Must pass** (no degradation in existing cell+misset behavior)

## How-To Map

### B1: U-matrix helper
```bash
# Locate existing B_ideal helpers in nanobrag_bridge.py
rg "b_ideal|B_ideal" dbex/nanobrag_bridge.py
# Implement derive_u_matrix_from_mosflm_a_star per spec above
```

### B2: Quaternion ops + roundtrip test
```bash
# Implement matrix_to_quaternion and quaternion_to_matrix in nanobrag_bridge.py
# Create tests/dbex/test_u_matrix_gradcheck.py
# Run roundtrip test
NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_u_matrix_gradcheck.py::test_quaternion_roundtrip > plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T105837Z/gradcheck_quaternion_ops.log 2>&1
```

### B3-B5: Config flag + initialization + closure
```bash
# Edit dbex/nanobrag_refinement.py
# Add use_u_matrix_parameterization parameter to build_mapping_stage_a_context
# Extend StageAContext dataclass with q_params field
# Branch closure logic per B5 spec
```

### B6: Parity probe extension
```bash
# Edit plans/active/TORCH-REFINE-002E/bin/probe_crystal_matrix_parity.py
# Add --use-u-matrix flag
# Branch initialization and comparison logic
```

### B7: U-matrix closure gradcheck
```bash
# Add test_u_matrix_closure_gradcheck to tests/dbex/test_u_matrix_gradcheck.py
NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_u_matrix_gradcheck.py::test_u_matrix_closure_gradcheck > plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T105837Z/gradcheck_u_matrix_closure.log 2>&1
```

### Regression guard
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion > plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T105837Z/pytest_stage_a_regression.log 2>&1
```

## Pitfalls To Avoid

1. **Device/dtype neutrality:** Use `torch.float64` for quaternion initialization and conversion to match float64 precision floor (<1e-8 roundtrip error). Do NOT hardcode GPU/CPU; inherit device from existing Stage A tensors.
2. **Protected Assets:** Do NOT edit tests/dbex/test_torch_refine_smoke.py beyond running the regression guard. U-matrix mode will be tested separately in Phase C.
3. **SO(3) Projection:** Do NOT call `proper_rotation()` or any SVD-based projection in `derive_u_matrix_from_mosflm_a_star`. The whole point is to preserve the mapping MOSFLM A* strain.
4. **Quaternion convention:** scipy uses [x, y, z, w] convention. Ensure `matrix_to_quaternion` and `quaternion_to_matrix` follow the same convention (no [w, x, y, z] vs [x, y, z, w] mixups).
5. **Normalization:** Normalize quaternion **every closure call** (`q_norm = q / ‖q‖`) before converting to matrix. Do NOT assume LBFGS will keep it on the unit sphere.
6. **Backward compatibility:** Ensure default path (`use_u_matrix_parameterization=False`) is unchanged. Existing cell+misset users must see zero behavior change.
7. **Gradcheck environment:** Always run gradchecks with `NANOBRAGG_DISABLE_COMPILE=1` per RUNTIME-001 (torch.compile interferes with autograd.gradcheck).
8. **No ad-hoc scripts:** Use the existing parity probe script (`probe_crystal_matrix_parity.py`) extended with `--use-u-matrix` flag. Do NOT create new one-off probes.
9. **B_ideal consistency:** Use the same `B_ideal_reciprocal` derivation in U-matrix path as the existing cell+misset path. Do NOT introduce divergent cell→B_ideal helpers.
10. **Spec math:** Do NOT paraphrase quaternion normalization or matrix conversion math. Reference the Phase A survey (plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T105837Z/so3_parameterization_survey.md) and scipy docs for normative equations.

## If Blocked

If any step fails or is unclear:
1. Capture the exact error message and file/line where it occurred.
2. Document the blocker in `plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T105837Z/blocker.md` with:
   - What you tried (commands, code changes)
   - Exact error text
   - Hypothesis for why it failed
3. Log the block in `docs/fix_plan.md` Attempts History with artifact pointer.
4. Return control to Galph for triage.

## Findings Applied (Mandatory)

**Relevant Finding IDs from `docs/findings.md`:**
- GEOMETRY-001: Detector mapping precision requirements (not directly applicable, but context for geometry guardrails)
- GEOMETRY-002: Euler inversion pattern (analogous to quaternion roundtrip validation)
- GEOMETRY-003: Current baseline misset path (will be superseded by GEOMETRY-004 if U-matrix succeeds)
- REFINE-001: LBFGS scale warm-start pattern (replicate for quaternion initialization from mapping zero)
- RUNTIME-001: Gradcheck requires `NANOBRAGG_DISABLE_COMPILE=1` (applied in B2, B7)
- CONFORMANCE-001: `KMP_DUPLICATE_LIB_OK=TRUE` environment flag for pytest (applied in regression guard)

**Adherence notes:**
- REFINE-001 pattern followed: Initialize U-matrix from mapping MOSFLM A* (zero deltas = mapping geometry), analogous to scale warm-start.
- RUNTIME-001 enforced: All gradchecks use `NANOBRAGG_DISABLE_COMPILE=1`.
- GEOMETRY-002 analogy: Quaternion roundtrip test mirrors Euler inversion validation (ensure numerical precision <1e-6).

## Pointers

- **Normative Spec:** `docs/spec-db-workflow.md` §Stage A (orientation parameterization clause), `docs/spec-db-core.md` §Geometry Mapping
- **Escalation Source:** `plans/active/TORCH-REFINE-002E/reports/2025-11-22T120000Z/decision.json` (Phase C1 final validation, escalation rationale)
- **Phase A Evidence:** `plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T105837Z/{phase_a0_evidence_synthesis.md,so3_parameterization_survey.md,api_design_and_risks.md}`
- **Implementation Plan:** `plans/active/TORCH-GEOMETRY-PARITY-002/implementation.md:58-86` (Phase B checklist B1-B7)
- **Testing Guide:** `docs/TESTING_GUIDE.md` §1 (Stage A selectors)
- **Code Anchors:**
  - `dbex/nanobrag_bridge.py:623` (existing `recover_cell_from_a_star` helper, pattern to replicate)
  - `dbex/nanobrag_bridge.py:710` (existing `derive_robust_misset`, shows baseline misset initialization)
  - `dbex/nanobrag_refinement.py:760-940` (Stage A context + closure, cell+misset path to branch from)

## Next Up (Optional, if you finish B1-B7 early)

Do NOT proceed to Phase C validation (parity probe, Phase 5 convergence) without explicit Galph approval. Phase B scope is implementation only.

If B1-B7 complete ahead of schedule:
1. Run `pytest --collect-only` for the new U-matrix gradcheck tests, archive log under artifacts.
2. Update `implementation.md` checklist (mark B1-B7 as done).
3. Return control to Galph for Phase C planning.

## Doc Sync Plan (Conditional)

**Not applicable for Phase B** — no new selectors marked "Active" yet. Phase C will add U-matrix parity and convergence tests; doc sync deferred until then.

## Mapped Tests Guardrail

- **Existing selector:** `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` must collect >0 and pass (regression guard)
- **New selectors:** `tests/dbex/test_u_matrix_gradcheck.py::{test_quaternion_roundtrip,test_u_matrix_closure_gradcheck}` will be created in B2/B7; collect-only validation deferred to Phase C doc sync.

## Hard Gate

If `test_stage_a_expansion` fails after B1-B7 implementation (with default use_u_matrix_parameterization=False), do NOT mark Phase B as done. Revert changes causing the regression, document the conflict in blocker.md, and return to Galph.
