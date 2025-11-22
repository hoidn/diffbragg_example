# TORCH-GEOMETRY-PARITY-002 Phase C Validation

## Summary
Extend parity probe with U-matrix mode, validate <1e-6 A* parity at zero deltas, and validate Phase 5 convergence (scale-only + full-DoF variants).

## Mode
none

## Focus
TORCH-GEOMETRY-PARITY-002 — Direct U-Matrix Parameterization for Stage A Geometry Refinement

## Branch
integration

## Mapped Tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (regression guard)
- `tests/dbex/test_u_matrix_gradcheck.py::test_quaternion_roundtrip` (quaternion ops validation)

## Artifacts
`plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T113409Z/`

## Do Now (Phase C1-C3: Parity + Convergence Validation)

**Context:** Phase B implementation (B1-B5) complete in commits 2793ba9 + b353b77 (scoping bugfix). All helpers, config flags, initialization logic, and closure branching for U-matrix parameterization are in place. Quaternion roundtrip test passes (<1e-6 error). Regression guard (test_stage_a_expansion) passes with default cell+misset path (use_u_matrix_parameterization=False).

**Goal:** Validate that the U-matrix parameterization achieves <1e-6 A* parity and restores convergent refinement behavior (Exit Criteria #1-#2).

**Scope (bundled Phase C items C1-C3):**

### Implement: C1 — Parity Validation (B6 deferred from Phase B)

**Target:** `plans/active/TORCH-REFINE-002E/bin/probe_crystal_matrix_parity.py::run_probe`

Extend `probe_crystal_matrix_parity.py` with `--use-u-matrix` flag to validate U-matrix path achieves <1e-6 A* parity:

1. Add `--use-u-matrix` boolean flag to argparse (default=False)
2. Update `run_probe(device: str, use_u_matrix: bool = False)` signature
3. When `use_u_matrix=True`:
   - Import helpers from `dbex.nanobrag_bridge`: `derive_u_matrix_from_mosflm_a_star`, `matrix_to_quaternion`, `quaternion_to_matrix`
   - Extract MOSFLM A* from dataload crystal
   - Call `derive_u_matrix_from_mosflm_a_star(a_star, cell)` to get U₀ (3×3 numpy array)
   - Convert U₀ to quaternion q₀ via `matrix_to_quaternion` (returns torch.Tensor[4])
   - Normalize q₀: `q_norm = q₀ / torch.norm(q₀)` (enforce unit norm constraint)
   - Convert back to rotation matrix: `U = quaternion_to_matrix(q_norm)` (torch.Tensor[3,3])
   - Compute A*_pathB = U @ B_ideal_reciprocal (use same B_ideal from Path A)
   - Compare A*_pathA (mapping MOSFLM) vs A*_pathB (U-matrix at zero deltas)
   - Compute diagnostics: `max_abs_diff`, `quaternion_delta_norm = torch.norm(q_norm - q₀).item()`, eigenvalues, singular values, log_u symmetric/antisymmetric
   - Emit results to JSON under `path_B_u_matrix` key (alongside existing variants)
4. Pass `use_u_matrix=args.use_u_matrix` to `run_probe()`
5. Update output JSON schema to include `path_B_u_matrix: PathBVariantSummary` alongside existing `path_B_unitcell`, `path_B_recovered`, `path_B_mapping_aligned`

**Execution:**
```bash
python plans/active/TORCH-REFINE-002E/bin/probe_crystal_matrix_parity.py \
  --use-u-matrix \
  --device cpu \
  --out-dir plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T113409Z/ \
  > plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T113409Z/probe_u_matrix.log 2>&1
```

**Exit Criterion #1 validation:** Verify `path_B_u_matrix.max_abs_diff < 1e-6` (U-matrix path reproduces mapping MOSFLM A* exactly at zero deltas, eliminating the 1.37e-3 symmetric strain artifact from GEOMETRY-003 cell+misset path)

### Implement: C2/C3 — Phase 5 Convergence Validation

**Target:** `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py::main`

Extend `stage_a_mapping_adam_debug.py` with `--use-u-matrix` flag to run Phase 5 validation with U-matrix parameterization:

1. Add `--use-u-matrix` boolean flag to argparse (default=False)
2. In Stage A setup section (where `RefinementConfig` or similar config is built):
   - Set `config.use_u_matrix_parameterization = args.use_u_matrix`
   - Ensure this config is passed to `run_nanobrag_refinement` so the LBFGS closure uses U-matrix path (already implemented in Phase B5)
3. Phase 5 execution will automatically use the U-matrix initialization and closure branching

**Execution (C2 — Scale-Only):**
```bash
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --phases 5 \
  --device cpu \
  --adam-steps 10 \
  --dof-variants A_scale_only \
  --use-u-matrix \
  --out-dir plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T113409Z/ \
  > plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T113409Z/phase5_scale_only.log 2>&1
```

**Exit Criterion #2a validation:** Verify median ROI CC ≥ 0.99 and χ² stable (final / initial ≤ 1.005, i.e., ≤0.5% drift) after 10 Adam steps

**Execution (C3 — Full-DoF):**
```bash
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --phases 5 \
  --device cpu \
  --adam-steps 10 \
  --dof-variants D_full \
  --use-u-matrix \
  --out-dir plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T113409Z/ \
  > plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T113409Z/phase5_full_dof.log 2>&1
```

**Exit Criterion #2b validation:** Verify monotonic χ² improvement (final < initial) without large CC collapses (CC stays ≥ 0.99)

### Validating Pytest Selector

After C1-C3 pass, re-run regression guard to verify no regressions in default cell+misset path:

```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
  > plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T113409Z/pytest_stage_a_regression_c.log 2>&1
```

**Expected:** `PASSED` (backward compatibility preserved)

### Decision Tree (Blocking Conditions)

**If C1 fails (`max_abs_diff ≥ 1e-6`):**
1. Capture exact parity metrics in `plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T113409Z/phase_c1_parity_failure_diagnosis.md`
2. Diagnose: numerical precision? B_ideal mismatch? quaternion conversion roundtrip error? Check scipy quaternion precision
3. **BLOCK** before proceeding to C2/C3
4. Escalation path: TORCH-GEOMETRY-PARITY-003 (numerical precision limits) if root cause is fundamental

**If C2/C3 fail (CC < 0.99 or χ² degrades):**
1. Capture χ² and CC trajectories from `block_dof_results_u_matrix.json`
2. Check gradient anomalies (zero, NaN, exploding)
3. Emit `phase_c_convergence_failure_diagnosis.md` with metrics and comparison to TORCH-REFINE-002E cell+misset baseline
4. **BLOCK** and escalate to TORCH-REFINE-003 (optimizer/LR sensitivity) per implementation.md abort trigger

**Expected Artifacts (success path):**
```
plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T113409Z/
├── crystal_matrix_parity_u_matrix.json   (C1: max_abs_diff < 1e-6)
├── block_dof_results_u_matrix.json       (C2/C3: convergence metrics)
├── probe_u_matrix.log                    (C1 execution log)
├── phase5_scale_only.log                 (C2 execution log)
├── phase5_full_dof.log                   (C3 execution log)
├── pytest_stage_a_regression_c.log       (C4 regression guard)
├── commands.txt                          (exact CLI commands)
└── summary.md                            (Turn Summary)
```

## How-To Map

### Step 1: Extend probe_crystal_matrix_parity.py with U-matrix path

**File:** `plans/active/TORCH-REFINE-002E/bin/probe_crystal_matrix_parity.py`

1. Add argparse flag (around line 566):
   ```python
   parser.add_argument(
       "--use-u-matrix",
       action="store_true",
       help="Use U-matrix parameterization instead of cell+misset decomposition",
   )
   ```

2. Update `run_probe` signature (around line 105):
   ```python
   def run_probe(device: str = "cpu", use_u_matrix: bool = False) -> dict:
   ```

3. Inside `run_probe`, after building Path A (mapping MOSFLM A*), add U-matrix Path B variant:
   ```python
   if use_u_matrix:
       from dbex.nanobrag_bridge import (
           derive_u_matrix_from_mosflm_a_star,
           matrix_to_quaternion,
           quaternion_to_matrix,
       )

       # Extract MOSFLM A* from dataload crystal (same as Path A)
       a_star_pathA = ... # (already extracted in existing code)

       # Derive U₀ from MOSFLM A* without SO(3) projection
       U0_np = derive_u_matrix_from_mosflm_a_star(a_star_pathA, cell_params)

       # Convert to quaternion and normalize
       q0 = matrix_to_quaternion(torch.from_numpy(U0_np).float())
       q_norm = q0 / torch.norm(q0)

       # Convert back to rotation matrix
       U = quaternion_to_matrix(q_norm)

       # Compute A* = U @ B_ideal (same B_ideal as Path A)
       a_star_pathB_u = (U @ B_ideal_reciprocal_torch).detach().cpu().numpy()

       # Compute parity metrics (reuse existing _compute_parity_summary helper)
       variant_u_matrix = _compute_parity_summary(a_star_pathA, a_star_pathB_u)

       # Add to payload
       payload["path_B_u_matrix"] = asdict(variant_u_matrix)
   ```

4. Update `main()` to pass flag (around line 575):
   ```python
   args = parser.parse_args(argv)
   payload = run_probe(device=args.device, use_u_matrix=args.use_u_matrix)
   ```

5. Update console output (around line 615) to include U-matrix variant:
   ```python
   if args.use_u_matrix:
       path_b_u = payload.get("path_B_u_matrix", {})
       print(f"  PathB_u_matrix:       log_u_symmetric_norm={path_b_u.get('log_u_symmetric_norm', 0):.3e}, "
             f"max_abs_diff={path_b_u.get('max_abs_diff', 0):.3e}")
   ```

### Step 2: Extend stage_a_mapping_adam_debug.py with --use-u-matrix flag

**File:** `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py`

1. Add argparse flag (locate existing parser, around line ~50-100):
   ```python
   parser.add_argument(
       "--use-u-matrix",
       action="store_true",
       help="Use U-matrix parameterization for Stage A (TORCH-GEOMETRY-PARITY-002)",
   )
   ```

2. In Stage A setup section (where config is built, around line ~200-300):
   ```python
   # Assuming RefinementConfig is defined inline or imported
   config.use_u_matrix_parameterization = args.use_u_matrix
   ```

3. Ensure `config` with `use_u_matrix_parameterization` is passed to `run_nanobrag_refinement` (the LBFGS closure will automatically use U-matrix path per Phase B5 implementation)

4. Output artifacts will automatically include U-matrix telemetry under existing `block_dof_results.json` schema (rename to `block_dof_results_u_matrix.json` if needed for clarity)

### Step 3: Execute and validate

1. Run C1 parity probe (U-matrix mode)
2. Check `crystal_matrix_parity_u_matrix.json` for `max_abs_diff < 1e-6`
3. If C1 passes, run C2 (scale-only Phase 5)
4. Check `block_dof_results_u_matrix.json` for CC ≥ 0.99, χ² stable
5. If C2 passes, run C3 (full-DoF Phase 5)
6. Check for monotonic χ² improvement
7. Run regression guard (test_stage_a_expansion)
8. Archive all logs and JSONs under `plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T113409Z/`

## Pitfalls To Avoid

1. **Device/dtype neutrality:** All torch operations must support both CPU and CUDA, float32 and float64. Use `device=torch.device(device_str)` and `.to(device)` consistently.

2. **Protected Assets (no edits):**
   - `tests/fixtures/golden_data/` (read-only reference data)
   - `simtbx_project/` (upstream vendored source)
   - `nanobrag_torch/` (frozen external library)

3. **Quaternion normalization:** Normalize quaternion EVERY time before converting to rotation matrix. Do NOT assume LBFGS or Adam preserves unit norm. Use `q_norm = q / torch.norm(q)`.

4. **B_ideal consistency:** U-matrix path must use the SAME B_ideal_reciprocal as the mapping path. Extract B_ideal from the SAME cell params used by nanobrag_torch's default crystal config (NOT from dxtbx unit cell unless explicitly aligned per GEOMETRY-003).

5. **Parity probe extension:** The existing `run_probe()` has 3 Path-B variants (unitcell, recovered, mapping_aligned). Add U-matrix as a FOURTH variant (`path_B_u_matrix`), not replacing existing variants. Preserve backward compatibility.

6. **Phase 5 convergence metrics:** "Stable χ²" means ≤0.5% drift (final / initial ≤ 1.005), NOT absolute zero change. "Monotonic improvement" means final < initial, allowing per-step fluctuations.

7. **JSON artifact schema:** Preserve existing JSON keys (`summary`, `path_B_unitcell`, etc.) and ADD new keys (`path_B_u_matrix`, `block_dof_results_u_matrix`) to avoid breaking downstream analysis.

8. **Gradients:** If Phase 5 convergence fails with zero/NaN gradients, capture full gradcheck diagnostics. Do NOT proceed to mark `done` without confirming gradients flow correctly through quaternion normalization and SO(3) manifold.

9. **Environment Freeze:** Do NOT install or upgrade packages. If scipy import fails, record blocker in `docs/fix_plan.md` and escalate. The environment is pre-provisioned; missing imports are blockers.

10. **Normative Spec Math:** Do NOT paraphrase quaternion normalization or A* = U @ B_ideal equations. Reference implementation.md and GEOMETRY-003 for exact formulas.

## If Blocked

**C1 parity failure (max_abs_diff ≥ 1e-6):**
1. Capture exact `max_abs_diff`, `quaternion_delta_norm`, `log_u_symmetric_norm` in `phase_c1_parity_failure_diagnosis.md`
2. Diagnose: numerical precision (check scipy quaternion uses float64)? B_ideal mismatch? quaternion roundtrip error (run test_quaternion_roundtrip on the specific A* matrix)?
3. **BLOCK** C2/C3 until parity < 1e-6 or escalation path documented
4. Escalate to TORCH-GEOMETRY-PARITY-003 if root cause is scipy quaternion precision limits

**C2/C3 convergence failure (CC < 0.99 or χ² degrades):**
1. Capture χ² and CC trajectories from `block_dof_results_u_matrix.json`
2. Check gradients: zero? NaN? Exploding? Run `torch.autograd.gradcheck` on U-matrix closure
3. Emit `phase_c_convergence_failure_diagnosis.md` with metrics and comparison to TORCH-REFINE-002E cell+misset baseline
4. Escalate to TORCH-REFINE-003 (optimizer/LR sensitivity) per implementation.md abort trigger

**Missing imports (scipy.spatial.transform.Rotation, etc.):**
1. Record exact import error in `docs/fix_plan.md` Attempts History
2. Mark TORCH-GEOMETRY-PARITY-002 as `blocked` with blocker="missing_dependency: scipy.spatial.transform"
3. Do NOT attempt pip install; escalate for environment maintenance

## Findings Applied

**Mandatory adherence:**
- **GEOMETRY-001** (detector mapping): Not directly applicable (crystal U-matrix, not detector), but respect exact dxtbx alignment pattern.
- **GEOMETRY-002** (Euler inversion): Not applicable (U-matrix bypasses Euler angles, uses quaternion).
- **GEOMETRY-003** (B_ideal-based mapping misset): **Critical reference.** U-matrix path must extract B_ideal using SAME logic as `derive_robust_misset` helper (from cell params, NOT dxtbx U-matrix). Goal: eliminate 1.37e-3 symmetric strain from cell+misset decomposition while preserving B_ideal alignment.
- **REFINE-001** (LBFGS scale warm-start): Apply same warm-start pattern to quaternion initialization. Start `q_params` at `q₀` derived from mapping MOSFLM A*, NOT at identity rotation. This ensures U-matrix path starts at mapping zero point (Exit Criterion #2).

**No other findings directly applicable.**

## Pointers

### Specs
- `docs/spec-db-workflow.md:39` — Stage A mapping zero-point invariant
- `docs/spec-db-core.md` §Geometry Mapping — A* = U @ B_ideal relationship

### Architecture
- `docs/architecture.md` — Stage A parameterization overview
- `docs/architecture/pytorch_design.md` — Tensor flow and gradients
- `plans/active/TORCH-GEOMETRY-PARITY-002/implementation.md:114-187` — Full Phase A/B/C checklist

### Findings
- `docs/findings.md` rows GEOMETRY-001:5, GEOMETRY-002:6, GEOMETRY-003:7, REFINE-001:28

### Fix-Plan
- `docs/fix_plan.md` row TORCH-GEOMETRY-PARITY-002 (current initiative)
- `docs/fix_plan.md` row TORCH-REFINE-002E (escalation source)

### Testing
- `docs/TESTING_GUIDE.md` §2 — Smoke test selectors
- `docs/development/TEST_SUITE_INDEX.md` — Test registry

### Telemetry (Evidence Chain)
- `plans/active/TORCH-REFINE-002E/reports/2025-11-22T090505Z/crystal_matrix_parity.json` — Phase A0: log_u_symmetric=1.37e-3
- `plans/active/TORCH-REFINE-002E/reports/2025-11-22T100330Z/forward_model_comparison.json` — Phase A3: 24.5% χ² gap
- `plans/active/TORCH-REFINE-002E/reports/2025-11-22T120000Z/decision.json` — Phase C1 escalation (all DoF degrade)
- `plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T112058Z/` — Phase B bugfix

## Next Up

**If C1-C3 pass and regression guard passes:**
- Phase C5 (Galph): Add GEOMETRY-004 to `docs/findings.md` documenting U-matrix parameterization, quaternion normalization, SO(3) manifold handling, parity results
- Phase C6 (conditional): Update test registry if new selectors added
- Phase C7 (Galph): Mark TORCH-REFINE-002E as `done` (alternative path: strain identified + convergence restored), mark TORCH-GEOMETRY-PARITY-002 as `done`

**If C1 fails:**
- Diagnose and escalate to TORCH-GEOMETRY-PARITY-003 (numerical precision limits)

**If C2/C3 fail:**
- Escalate to TORCH-REFINE-003 (optimizer/LR sensitivity analysis)

## Doc Sync Plan

**Conditional (only if new test selectors added):**

After C1-C4 pass:
1. Run `pytest --collect-only tests/dbex/ > plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T113409Z/collect_tests.log 2>&1`
2. Update `docs/TESTING_GUIDE.md` §2 if new selectors exist
3. Update `docs/development/TEST_SUITE_INDEX.md`

**Note:** If only extending existing scripts with flags (no new test files), Doc Sync is NOT required. Defer to Phase C6 assessment.
