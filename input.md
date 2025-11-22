# Phase C5 — Code Path Equivalence Diagnostic

## Summary
Instrument and test whether `use_mapping_zero_geometry=False` with zero-valued parameters produces different A* than `use_mapping_zero_geometry=True`, causing catastrophic chi² despite correct parameter handling.

## Mode
none

## Focus
TORCH-GEOMETRY-CONVERGENCE-001 — Diagnose & Fix Quaternion U-Matrix Catastrophic Convergence Failure

## Branch
integration

## Mapped tests
- **Active:** `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (regression guard)
- **Validation:** Manual 2-step diagnostic via `stage_a_mapping_adam_debug.py`

## Artifacts
`plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T232200Z/`

## Do Now

Phase C4 audit found NO parameter staleness bugs (HIGH confidence ~95%). All parameters (log_scale, q_params, U, A*, crystal_overrides) are correctly captured and used. However, Ralph identified a new hypothesis: **code path divergence** between zero-point validation path and first closure path may produce different results even at zero parameters.

**Your task:** Implement Priority 1 diagnostic from `phase_c4_parameter_staleness_decision.md` to prove/disprove this hypothesis.

### Implementation Steps

1. **Review Phase C4 artifacts:**
   - Read `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T232000Z/phase_c4_parameter_staleness_decision.md`
   - Read `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T232000Z/phase_c4_first_closure_audit.md`
   - Understand the code path divergence hypothesis (§Evidence Summary, §Recommended Next Actions Priority 1)

2. **Instrument `_stage_a_forward` with A* checksum logging:**
   - File: `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py`
   - Target function: `_stage_a_forward` (lines ~397-464)
   - Add checksum logging at two points:

     **Point A** (after line ~410, zero-point path):
     ```python
     if use_mapping_zero_geometry:
         crystal_config, _ = create_crystal_config(...)
         # Extract A* from crystal_config for logging
         A_star_direct = np.array([
             crystal_config.mosflm_a_star,
             crystal_config.mosflm_b_star,
             crystal_config.mosflm_c_star
         ], dtype=np.float64).reshape(3, 3)
         a_star_checksum_direct = A_star_direct.sum()
         a_star_max_elem_direct = np.abs(A_star_direct).max()
     ```

     **Point B** (after line ~442, closure path):
     ```python
     else:
         # After A_star_new computation and numpy conversion
         A_star_roundtrip = A_star_new.detach().cpu().numpy()
         a_star_checksum_roundtrip = A_star_roundtrip.sum()
         a_star_max_elem_roundtrip = np.abs(A_star_roundtrip).max()

         # Compute divergence vs direct path (requires zero-point reference)
         # This will be logged in telemetry below
     ```

3. **Extend telemetry schema to include A* checksums:**
   - In `_forward_once` (line ~473), add fields to telemetry dict:
     ```python
     telemetry_data = {
         # existing fields...
         "a_star_checksum": a_star_checksum_roundtrip if not use_mapping_zero_geometry else a_star_checksum_direct,
         "a_star_max_element": a_star_max_elem_roundtrip if not use_mapping_zero_geometry else a_star_max_elem_direct,
         "code_path": "closure" if not use_mapping_zero_geometry else "zero_point",
     }
     ```

4. **Run 2-step diagnostic with dual telemetry capture:**
   - Execute `python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
       --use-u-matrix \
       --u-matrix-lr 1e-5 \
       --phases 5 \
       --dof-variants A_scale_only \
       --adam-steps 2 \
       --device cpu \
       --telemetry-dir telemetry \
       --out-dir plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T232200Z/c5_diagnostic \
       --timeout 1200`
   - Expected artifacts:
     - `c5_diagnostic/zero_point_check.json` (chi²~990k, code_path=zero_point)
     - `c5_diagnostic/telemetry/telemetry_step_000_init.json` (chi², code_path=closure, A* checksum)
     - `c5_diagnostic/telemetry/telemetry_step_000_post.json` (after first step)
     - `c5_diagnostic/telemetry/telemetry_step_001_init.json` (before second step)
     - `c5_diagnostic/block_dof_results_u_matrix.json` (if completes)

5. **Extract code path equivalence metrics:**
   - Create `c5_diagnostic/code_path_equivalence_metrics.txt` with:
     ```
     === Code Path Equivalence Metrics (Phase C5) ===

     Zero-Point Path (use_mapping_zero_geometry=True):
       chi_squared: <value from zero_point_check.json>
       correlation: <value>
       a_star_checksum: <value>
       a_star_max_element: <value>

     First Closure Path (use_mapping_zero_geometry=False, step 0 INIT):
       chi_squared: <value from telemetry_step_000_init.json>
       a_star_checksum: <value>
       a_star_max_element: <value>

     Divergence Metrics:
       delta_chi_squared: <closure_chi² - zero_point_chi²>
       delta_chi_squared_pct: <(delta / zero_point) * 100>%
       delta_a_star_checksum: <abs(closure_checksum - zero_checksum)>
       delta_a_star_max_element: <abs(closure_max - zero_max)>

     Code Path Equivalence Verdict:
       [ ] PASS — delta_chi_squared < 1% AND delta_a_star_checksum < 1e-10
       [ ] FAIL — delta_chi_squared > 10% OR delta_a_star_checksum > 1e-6
       [ ] INCONCLUSIVE — intermediate values
     ```

6. **Synthesize Phase C5 decision:**
   - Create `phase_c5_code_path_divergence_decision.md` using this template:
     ```markdown
     # Phase C5 Decision — Code Path Equivalence Diagnostic

     **Initiative:** TORCH-GEOMETRY-CONVERGENCE-001
     **Phase:** C5 (Code Path Equivalence)
     **Date:** 2025-11-22T232200Z

     ## Verdict

     **[ ] Path A — Code paths EQUIVALENT (delta_chi² < 1%, delta_A* < 1e-10)**
     **[ ] Path B — Code paths DIVERGE (delta_chi² > 10%, delta_A* > 1e-6)**
     **[ ] Path C — INCONCLUSIVE (intermediate metrics OR test failed)**

     **DIAGNOSIS:** <Fill based on metrics>

     ## Evidence Summary

     <Paste code_path_equivalence_metrics.txt>

     ## Root Cause Analysis

     <If Path B confirmed, analyze WHERE the divergence occurs:>
     - U-matrix computation from q_params?
     - B_ideal derivation?
     - A* reconstruction (U @ B_ideal)?
     - Numpy tuple conversion?
     - create_crystal_config handling of crystal_overrides?

     ## Recommended Next Actions

     ### If Path A (Equivalence CONFIRMED):
     - Reject code path divergence hypothesis
     - Escalate to Priority 2: audit `create_crystal_config` internals for subtle differences
     - Or Priority 3: test LBFGS optimizer

     ### If Path B (Divergence CONFIRMED):
     - Implement fix to make paths equivalent at zero parameters:
       - Option 1: Bypass crystal_overrides when all deltas are zero (use direct MOSFLM path)
       - Option 2: Fix numerical precision in U/B_ideal round-trip
       - Option 3: Audit `create_crystal_config` for phase-B5-style override bugs
     - Validate fix with rerun of this diagnostic

     ### If Path C (Inconclusive):
     - Review test execution logs for premature termination or telemetry corruption
     - Rerun diagnostic with extended timeout or reduced ROI count
     ```

7. **Update implementation.md checklist:**
   - Mark `C5` as `[x]` if diagnostic completes OR `[~]` if blocked
   - Add Path verdict (A/B/C) and recommended next phase
   - Update `C4` entry with cross-reference to C5 artifacts

8. **Regression guard:**
   - Run `pytest tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion -v`
   - Capture to `pytest_regression.log`
   - MUST PASS before proceeding

9. **Write summary:**
   - Create `summary.md` with Turn Summary format (3-5 sentences: what shipped, main problem, next step, artifacts pointer)

10. **Commit and push:**
    - `git add -A`
    - `git commit -m "TORCH-GEOMETRY-CONVERGENCE-001 Phase C5: Code path equivalence diagnostic (tests: test_stage_a_expansion)"`
    - `git push`


## How-To Map

### A* Checksum Extraction (Zero-Point Path)
```python
# After create_crystal_config call in use_mapping_zero_geometry=True branch
crystal_config, _ = create_crystal_config(...)
A_star_direct = np.array([
    crystal_config.mosflm_a_star,
    crystal_config.mosflm_b_star,
    crystal_config.mosflm_c_star
], dtype=np.float64).reshape(3, 3)
checksum = A_star_direct.sum()
max_elem = np.abs(A_star_direct).max()
```

### A* Checksum Extraction (Closure Path)
```python
# After A_star_new computation (line ~436)
A_star_roundtrip = A_star_new.detach().cpu().numpy()
checksum = A_star_roundtrip.sum()
max_elem = np.abs(A_star_roundtrip).max()
```

### Metrics Extraction (Python one-liner)
```bash
python -c "
import json
zp = json.load(open('c5_diagnostic/zero_point_check.json'))
t0 = json.load(open('c5_diagnostic/telemetry/telemetry_step_000_init.json'))
print(f'delta_chi²={(t0['chi_squared']-zp['chi_squared_stage_a'])/zp['chi_squared_stage_a']*100:.2f}%')
print(f'delta_A*_checksum={abs(t0.get('a_star_checksum',0)-zp.get('a_star_checksum',0)):.12e}')
"
```

## Pitfalls To Avoid

1. **Do NOT implement fixes yet** — This is a diagnostic loop. Only instrument and measure. Fix implementation happens in C6 after confirmation.

2. **Device/dtype neutrality** — All A* checksum computations must use `.detach().cpu().numpy()` and `dtype=np.float64` for consistency.

3. **Protected Assets** — Do NOT modify `dbex/nanobrag_bridge.py:create_crystal_config` in this loop. Only modify the script.

4. **Telemetry schema stability** — Add new fields (`a_star_checksum`, `code_path`) WITHOUT removing existing fields to maintain backward compatibility with Phase C3 telemetry analysis tools.

5. **Test completion** — If diagnostic times out or terminates early:
   - Check for HKL grid timeout (common blocker, ~20 min on CPU)
   - If timeout: reduce `--adam-steps` to 1 (only need step 0 init telemetry)
   - If still blocks: capture partial results and mark Path C (inconclusive)

6. **ROI scoring overhead** — Do NOT compute full ROI correlation in telemetry. Use chi² only for speed.

7. **Metrics precision** — Use at least 12 decimal places (`.12e`, `.12f`) for A* checksums to detect sub-1e-6 differences.

8. **Cross-reference accuracy** — When updating implementation.md, ensure all artifact paths point to `2025-11-22T232200Z/` (THIS loop's directory), not prior loops.

## If Blocked

**Scenario 1: Test times out during HKL grid building**
- Reduce `--adam-steps` to 1
- If still times out: reduce ROI count via `--n-rois 2` (if flag exists)
- Capture whatever telemetry was emitted before timeout
- Mark Path C (inconclusive) and document timeout in decision

**Scenario 2: Telemetry files missing `a_star_checksum` field**
- Review instrumentation code for scoping bugs (checksum vars defined inside wrong if-block)
- Check for exceptions during telemetry emission (wrap in try-except, log errors)
- If unfixable: use log output to manually extract checksums, note workaround in decision

**Scenario 3: Regression guard fails**
- Revert instrumentation changes
- Investigate what broke (likely: variable scope issue or indentation error)
- Fix, retest, then proceed

**Scenario 4: A* checksum values are identical but chi² diverges**
- Document this surprising result in decision
- Hypothesize that divergence happens AFTER crystal_config creation (in simulator)
- Recommend Priority 2 audit: `create_crystal_config` internals or nanobrag_torch forward pass

## Findings Applied

- **REFINE-001** (LBFGS scale warm-start): Not directly applicable (this is Adam diagnostic, not LBFGS)
- **PHYSICS-LOSS-002** (variance sigma-floor guard): Variance telemetry instrumentation already present from Phase C1
- **GRADIENT-001** (autograd graph preservation): A* checksum logging uses `.detach()` to avoid breaking autograd
- **CONVERGENCE-001 Phase B5** (B_ideal mismatch): Phase C4 audit checked for similar issues; none found in parameter flow
- **CONVERGENCE-001 Phase C4** (no parameter staleness): This loop tests the NEW hypothesis (code path divergence) identified by C4

## Pointers

- **Spec alignment:** `docs/spec-db-workflow.md §Stage A — Optimizer convergence`, `docs/spec-db-runtime.md §Gradient stability`
- **Test selector reference:** `docs/TESTING_GUIDE.md §2.2` (test_stage_a_expansion regression guard)
- **Architecture:** `docs/architecture/pytorch_design.md §Parameterization` (U-matrix vs cell+misset)
- **Prior phase:** `plans/active/TORCH-GEOMETRY-CONVERGENCE-001/reports/2025-11-22T232000Z/phase_c4_parameter_staleness_decision.md §Priority 1`
- **Fix plan row:** `docs/fix_plan.md:44-69` (TORCH-GEOMETRY-CONVERGENCE-001 Attempts History entry 69)

## Next Up (if you finish early)

- If Path A (equivalence confirmed): Begin Priority 2 audit of `create_crystal_config` internals
- If Path B (divergence confirmed): Draft fix options (bypass overrides, fix precision, audit config function)
- If Path C (inconclusive): Review test logs and prepare retry plan with reduced timeout scope
