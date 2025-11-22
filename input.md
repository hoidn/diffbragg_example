# Supervisor Input — 2025-11-22T120500Z

## Summary
Rerun Phase C2/C3 convergence test with B_ideal_reciprocal shape bugfix applied (quaternion U-matrix sensitivity test).

## Mode
none

## Focus
TORCH-GEOMETRY-PARITY-002 — Direct U-Matrix Parameterization for Stage A Geometry Refinement

## Branch
integration

## Mapped Tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (regression guard — cell+misset default path unchanged)
- Phase 5 convergence metrics from `stage_a_mapping_adam_debug.py` (not a pytest selector, CLI-driven validation)

## Artifacts
```
plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T120500Z/
  block_dof_results_u_matrix.json
  phase_c2_c3_decision.json
  stage_a_debug_u_matrix.log
  pytest_stage_a_regression.log
  commands.txt
  summary.md
  phase_c2_shape_bug_diagnosis.md (already created by supervisor)
```

## Do Now

**Context:** Supervisor diagnosed and fixed the B_ideal_reciprocal shape bug blocking Phase C2/C3. Ralph's 2025-11-22T114945Z zero-point check PASSED (CC=0.9999999843, chi²_rel_diff=-0.017%), confirming U-matrix parameterization logic is correct at zero deltas. The Phase 5 convergence test crashed with `RuntimeError: size mismatch` because `cctbx_cell(...).fractionalization_matrix()` returns a flat (9,) array, not (3,3). Supervisor fixed this by adding `.reshape(3,3)` at line 325 of `stage_a_mapping_adam_debug.py`. Now ready to rerun the full Phase C2/C3 convergence test.

**Hypothesis (unchanged):** Quaternion U-matrix may still succeed because it directly parameterizes the 9-DOF orientation (4-param quaternion → 3×3 rotation) without the cell+misset decomposition that created the 1.37e-3 symmetric strain gradient artifact. Even though quaternion parity is ~4e-05 (same as cell+misset), the gradient flow may be cleaner and enable convergence at the mapping zero point.

**Decision Tree (CRITICAL, unchanged from 2025-11-22T114945Z input.md):**
- **If A_scale_only shows:** median ROI CC ≥ 0.99 AND χ² drift ≤ 0.5% after 10 Adam steps → **ACCEPT** quaternion as viable; proceed to findings update GEOMETRY-004
- **If A_scale_only degrades:** CC < 0.99 OR χ² drift > 0.5% → **ESCALATE** to TORCH-GEOMETRY-PARITY-003 (investigate `det(U)≠1` root cause via dxtbx A*/cell audit OR evaluate hybrid cell+U+scale factorization)
- **If D_full degrades:** (secondary check) — log in decision.json but quaternion viability hinges on A_scale_only only per exit criterion #2

**Phase C2/C3 Convergence Test (bundled):**

1. **Verify bugfix landed:** Check line 325 of `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py` reads `.reshape(3, 3).T` (supervisor already applied this fix).

2. **Execute Phase 5 convergence test** with quaternion U-matrix mode:
   ```bash
   KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
   python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
     --use-u-matrix \
     --phases 5 \
     --dof-variants A_scale_only,D_full \
     --adam-steps 10 \
     --device cpu \
     --out-dir plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T120500Z/
   ```

   **Expected outputs:**
   - `block_dof_results_u_matrix.json` with per-variant metrics (chi_squared_initial, chi_squared_final, median_roi_correlation_initial, median_roi_correlation_final, improvement_pct)
   - `stage_a_debug_u_matrix.log` (console output)

   **Time budget:** 20 minutes (1200 seconds); if timeout, capture partial results and document in decision.json with `decision="escalate_to_geometry_parity_003"` + rationale citing the timeout

3. **Synthesize decision.json:**
   ```json
   {
     "decision": "accept_quaternion" | "escalate_to_geometry_parity_003",
     "rationale": "<1-2 sentences explaining which decision tree branch triggered>",
     "a_scale_only": {
       "chi_squared_initial": <float>,
       "chi_squared_final": <float>,
       "chi_squared_drift_pct": <float>,
       "median_roi_correlation_initial": <float>,
       "median_roi_correlation_final": <float>,
       "verdict": "pass" | "fail",
       "exit_criterion": "CC ≥ 0.99 and χ² drift ≤ 0.5%"
     },
     "d_full": {
       "chi_squared_initial": <float>,
       "chi_squared_final": <float>,
       "improvement_pct": <float>,
       "median_roi_correlation_final": <float>,
       "verdict": "monotonic_improvement" | "degrade",
       "exit_criterion": "monotonic χ² improvement, no large CC collapses"
     },
     "parity_context": {
       "quaternion_parity_max_abs_diff": 4.0221959352493286e-05,
       "det_u_zero": 1.0005572899796854,
       "so3_projection_loss": "0.06% volume scaling lost during quaternion conversion"
     },
     "zero_point_validation": {
       "corr_median_vs_mapping": 0.9999999843,
       "chi2_rel_diff": -0.00016771711901888685,
       "max_abs_diff_photons": 85.13671875,
       "status": "passed"
     }
   }
   ```
   Write to `plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T120500Z/phase_c2_c3_decision.json`

4. **Regression guard:**
   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   DBEX_SMOKE_DETECTOR_SIZE=small \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion > plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T120500Z/pytest_stage_a_regression.log 2>&1
   ```

   **Expected:** Exit code 0 (test PASSED)
   **On failure:** Do NOT proceed to findings update; document regression details and mark TORCH-GEOMETRY-PARITY-002 as blocked

5. **Conditional findings update (only if decision="accept_quaternion"):**
   - Add GEOMETRY-004 to `docs/findings.md`:
     ```markdown
     | GEOMETRY-004 | 2025-11-22 | geometry, crystal, u-matrix, so3 | Quaternion U-matrix parameterization for Stage A enables direct 4-DOF orientation refinement (quaternion → rotation matrix → A*) without cell+misset decomposition. Achieves same A* parity as cell+misset (~4e-05) due to SO(3) projection discarding the 0.06% volume scaling embedded in mapping MOSFLM A* (`det(U₀)=1.000557`). Raw U-matrix (no SO(3) constraint) achieves perfect parity (3.5e-18) but is not a valid rotation. Quaternion normalization (`q_norm = q / ||q||`) enforces unit sphere constraint; SO(3) manifold is maintained via scipy.spatial.transform.Rotation conversion. Convergence tests (Phase C2/C3) show A_scale_only χ² drift [FILL: actual drift %] and CC_final=[FILL: actual CC], confirming quaternion is viable for Stage A refinement despite parity gap. Zero-point validation: CC=0.9999999843, chi²_rel_diff=-0.017%. | dbex/nanobrag_bridge.py:matrix_to_quaternion, dbex/nanobrag_refinement.py:use_u_matrix_parameterization, plans/active/TORCH-GEOMETRY-PARITY-002/reports/ | Active |
     ```
   - Cross-reference TORCH-GEOMETRY-PARITY-002 and cite phase_c2_c3_decision.json metrics
   - Fill [FILL: ...] placeholders with actual values from decision.json
   - Only execute this step if `decision.json::decision == "accept_quaternion"`; otherwise skip and leave findings update for GEOMETRY-PARITY-003

6. **Record artifacts and commands:**
   - Emit `commands.txt` listing all bash commands executed this loop (Phase 5 run, regression guard)
   - Update `summary.md` (Turn Summary template: prepend to existing summary.md if it exists)

## How-To Map

### 1. Phase 5 U-matrix convergence test (with bugfix)
**Command:**
```bash
cd /home/ollie/Documents/diffbragg_example
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
  --use-u-matrix \
  --phases 5 \
  --dof-variants A_scale_only,D_full \
  --adam-steps 10 \
  --device cpu \
  --out-dir plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T120500Z/
```
**Timeout:** 1200 seconds (20 minutes)
**Expected success:** Exit code 0, `block_dof_results_u_matrix.json` written
**On timeout/error:** Capture partial logs and document in decision.json with `decision="escalate_to_geometry_parity_003"` + rationale citing the timeout

### 2. Decision synthesis
**Read:** `plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T120500Z/block_dof_results_u_matrix.json`
**Extract:**
- `A_scale_only.chi_squared_initial`, `.chi_squared_final`, `.median_roi_correlation_final`
- `D_full.chi_squared_initial`, `.chi_squared_final`, `.median_roi_correlation_final`
**Compute:**
- `chi_squared_drift_pct = 100 * (chi_squared_final - chi_squared_initial) / chi_squared_initial` for A_scale_only
- `improvement_pct = 100 * (chi_squared_initial - chi_squared_final) / chi_squared_initial` for D_full
**Decision logic:**
```python
a_scale_verdict = "pass" if (median_roi_correlation_final >= 0.99 and abs(chi_squared_drift_pct) <= 0.5) else "fail"
decision = "accept_quaternion" if a_scale_verdict == "pass" else "escalate_to_geometry_parity_003"
```
**Write:** `phase_c2_c3_decision.json` per template above (include zero_point_validation section from 2025-11-22T114945Z/zero_point_check.json)

### 3. Regression guard
**Command:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion > plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T120500Z/pytest_stage_a_regression.log 2>&1
```
**Expected:** Exit code 0 (test PASSED)
**On failure:** Do NOT proceed to findings update; document regression details in summary.md and mark TORCH-GEOMETRY-PARITY-002 as blocked

### 4. Conditional findings update
**Guard:** Only execute if `phase_c2_c3_decision.json::decision == "accept_quaternion"`
**File:** `docs/findings.md`
**Action:** Append GEOMETRY-004 row to the findings table (after GEOMETRY-003), filling `[FILL: ...]` placeholders with actual `A_scale_only.chi_squared_drift_pct` and `median_roi_correlation_final` from decision.json
**Cross-refs:** Link to TORCH-GEOMETRY-PARITY-002, phase_c2_c3_decision.json, implementation.md

## Pitfalls To Avoid

1. **Do NOT skip the regression guard:** Even though U-matrix is opt-in via `use_u_matrix_parameterization=False` default, verify `test_stage_a_expansion` still passes to ensure the bugfix didn't break the cell+misset path

2. **Do NOT update findings if decision="escalate":** GEOMETRY-004 should only be added if quaternion proves viable; otherwise defer to GEOMETRY-PARITY-003 for GL(3)/hybrid alternatives

3. **Phase 5 timeout handling:** If `stage_a_mapping_adam_debug.py` times out (>20 min) or crashes, capture the partial `block_dof_results_u_matrix.json` (may be incomplete) and synthesize decision.json with `decision="escalate_to_geometry_parity_003"` + rationale citing the timeout/error. Do NOT wait indefinitely.

4. **A_scale_only is the primary gate:** Exit criterion #2 (implementation.md:23-24) specifies A_scale_only must maintain CC ≥ 0.99 + stable χ²; D_full is a secondary check. If A_scale_only passes but D_full degrades, still accept quaternion and note the D_full limitation in findings.

5. **Decision tree is HARD:** Do not editorialize or soften the verdict — if A_scale_only CC < 0.99 OR χ² drift > 0.5%, the decision MUST be `escalate_to_geometry_parity_003` per implementation.md:110-112 abort trigger

6. **ROI correlation threshold:** Use median ROI correlation (not global), same metric as TORCH-REFINE-002E Phase 5 validation; `block_dof_results.json` structure from TOOLING-VIS-001 should already emit this

7. **Device neutrality:** Run on CPU (`--device cpu`) to avoid CUDA OOM (same as TORCH-REFINE-002E canonical runs); quaternion ops are device-neutral per RUNTIME-001

8. **Bugfix verification:** Before running Phase 5, verify line 325 of `stage_a_mapping_adam_debug.py` shows `.reshape(3, 3).T` — if not, the bugfix was not applied and Phase 5 will crash with the same shape mismatch error

9. **Protected Assets:** Do not edit `docs/spec-db-*.md`, `docs/TESTING_GUIDE.md`, or `tests/dbex/test_torch_refine_smoke.py` unless the regression guard fails and you need to fix a bug. The findings update is the only doc change permitted for the accept_quaternion path.

10. **Environment Freeze:** Do not propose/execute package installs; scipy.spatial.transform.Rotation is already available (used in Phase C1). If an import fails, treat as blocker and record in decision.json.

11. **Zero-point validation context:** Include the zero_point_validation section in decision.json (from 2025-11-22T114945Z/zero_point_check.json) to show Ralph's partial success validated the U-matrix logic at zero deltas before the convergence test.

## If Blocked

**Timeout/Error during Phase 5:**
- Capture partial logs (`stage_a_debug_u_matrix.log`, incomplete `block_dof_results_u_matrix.json`)
- Synthesize decision.json with `decision="escalate_to_geometry_parity_003"`, rationale: "Phase 5 timeout/error — quaternion convergence test incomplete, escalating to deeper dxtbx A* investigation"
- Document in summary.md and return; supervisor will open GEOMETRY-PARITY-003

**Regression guard fails:**
- Inspect `pytest_stage_a_regression.log` for the failure signature
- If it's a bugfix regression (e.g., broke cell+misset path), fix it and re-run
- If it's a fundamental incompatibility, document in decision.json and escalate

**Decision synthesis unclear:**
- If `block_dof_results_u_matrix.json` is missing expected fields (e.g., no `median_roi_correlation_final`), check log for Phase 5 execution errors
- Default to `decision="escalate_to_geometry_parity_003"` and document the missing metrics

## Findings Applied (Mandatory)

**Relevant Finding IDs from `docs/findings.md`:**
- **GEOMETRY-003** (B_ideal-based mapping misset) — Adherence: U-matrix path bypasses this; regression guard ensures GEOMETRY-003 cell+misset default unchanged
- **GRADIENT-001** (crystal_overrides dict) — Adherence: U-matrix closure updates `crystal_overrides['A_star']` directly per implementation.md:84-87
- **RUNTIME-001** (NANOBRAGG_DISABLE_COMPILE for gradcheck) — Adherence: Phase 5 runs with `NANOBRAGG_DISABLE_COMPILE=1` to avoid Dynamo interference
- **REFINE-001** (LBFGS scale warm-start) — Adherence: quaternion initialization follows same pattern (extract U₀, convert to q₀, initialize trainable params)
- **DXTBX-001** (crystal.get_A() tuple→array) — Adherence: U-matrix derivation uses `derive_u_matrix_from_mosflm_a_star` which already handles the tuple→array reshape per Phase B1 implementation

**New Finding (conditional):**
- **GEOMETRY-004** (U-matrix quaternion parameterization) — To be added to `docs/findings.md` ONLY if `decision="accept_quaternion"`; otherwise deferred to GEOMETRY-PARITY-003

**Bugfix Applied (2025-11-22T120500Z):**
- **B_ideal_reciprocal shape fix** — `cctbx_cell(...).fractionalization_matrix()` returns flat (9,) not (3,3); added `.reshape(3,3)` before transpose in `stage_a_mapping_adam_debug.py:325` to fix matmul shape mismatch. Documented in `phase_c2_shape_bug_diagnosis.md`.

## Pointers

### Primary Specs
- `docs/spec-db-workflow.md:44` — Stage A orientation parameterization clause (normative for U-matrix)
- `docs/spec-db-core.md:40-46` — Geometry Mapping contract (crystal orientation must reproduce MOSFLM A* at zero)

### Architecture/Plans
- `plans/active/TORCH-GEOMETRY-PARITY-002/implementation.md:21-28` — Exit criteria (parity + convergence gates)
- `plans/active/TORCH-GEOMETRY-PARITY-002/implementation.md:110-112` — Abort/escalation trigger (Phase C parity failure → GEOMETRY-PARITY-003)
- `plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T113409Z/phase_c1_parity_failure_diagnosis.md:58-74` — Alternative Path 3 rationale
- `plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T120500Z/phase_c2_shape_bug_diagnosis.md` — B_ideal_reciprocal shape bug diagnosis + fix

### Code Anchors
- `dbex/nanobrag_bridge.py:derive_u_matrix_from_mosflm_a_star` — U-matrix extraction (Phase B1)
- `dbex/nanobrag_bridge.py:matrix_to_quaternion` — SO(3) projection via scipy (Phase B2)
- `dbex/nanobrag_refinement.py:use_u_matrix_parameterization` — Config flag (Phase B3)
- `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py:--use-u-matrix` — CLI flag for quaternion mode (Phase C1)
- `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py:325` — B_ideal_reciprocal bugfix location

### Testing
- `docs/TESTING_GUIDE.md:§2` — Authoritative Stage A smoke selector + env flags
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` — Regression guard for cell+misset default

### Prior Evidence
- `plans/active/TORCH-REFINE-002E/reports/2025-11-22T120000Z/decision.json` — Escalation trigger (cell+misset all DoFs degrade)
- `plans/active/TORCH-REFINE-002E/reports/2025-11-22T090505Z/crystal_matrix_parity.json` — Phase A0 strain decomposition (log_u_symmetric_norm=1.37e-3)
- `plans/active/TORCH-REFINE-002E/reports/2025-11-22T094500Z/gradient_probe.json` — Phase B1 massive gradients (orientation_vec ≈2.88e8)
- `plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T113409Z/crystal_matrix_parity.json` — Phase C1 raw U perfect parity + det(U)≠1 discovery
- `plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T114945Z/zero_point_check.json` — Phase C2 zero-point validation PASSED (CC=0.9999999843, chi²_rel_diff=-0.017%)

## Next Up (optional)

**If decision="accept_quaternion":**
1. Phase C4: Update test registry (`docs/TESTING_GUIDE.md` §2, `docs/development/TEST_SUITE_INDEX.md`) if any new selectors were added
2. Phase C7: Mark TORCH-REFINE-002E as `done` (alternative path: strain identified + quaternion U-matrix provides viable workaround)
3. Close TORCH-GEOMETRY-PARITY-002 as `done`

**If decision="escalate_to_geometry_parity_003":**
1. Supervisor opens TORCH-GEOMETRY-PARITY-003 with focus on:
   - Investigating `det(U₀)=1.000557` root cause (dxtbx A*/cell inconsistency? physical volume scaling?)
   - Evaluating hybrid cell+U+scale factorization (Alternative Path 2)
   - GL(3) full 9-DOF parameterization risk analysis (Alternative Path 1)
2. TORCH-GEOMETRY-PARITY-002 marked as `blocked` pending GEOMETRY-PARITY-003 resolution

## Doc Sync Plan (Conditional)

**Only if decision="accept_quaternion" AND any new selectors were authored:**
1. Run `pytest --collect-only -k "stage_a" > plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T120500Z/collect_stage_a_tests.log 2>&1`
2. Update `docs/TESTING_GUIDE.md` §2 with any new U-matrix selectors (e.g., `test_stage_a_u_matrix_convergence` if added)
3. Update `docs/development/TEST_SUITE_INDEX.md` registry

**For this loop:** No new pytest selectors expected (Phase C2/C3 uses CLI `stage_a_mapping_adam_debug.py`, not pytest); doc sync likely skipped unless Ralph authors a new test

## Mapped Tests Guardrail

**Primary selector:** `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
**Collect-only verification:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
```
**Expected:** 1 item collected (Active selector, confirmed in TESTING_GUIDE.md:§2)

**Secondary validation:** Phase 5 CLI metrics from `block_dof_results_u_matrix.json` (not a pytest selector)

**Hard Gate:** If `test_stage_a_expansion` collects 0 or fails during regression guard, BLOCK before findings update and escalate per If Blocked section

---

**CRITICAL REMINDER:** This is a **convergence sensitivity test**, not a parity validation. We already know quaternion parity is ~4e-05 (same as cell+misset). The question is whether quaternion **improves refinement behavior** by eliminating the symmetric strain gradient artifact. Follow the decision tree strictly — if A_scale_only fails, escalate immediately; do not try to "fix" quaternion or soften the verdict.

**Bugfix Status:** Supervisor diagnosed and fixed the B_ideal_reciprocal shape bug (cctbx returns flat (9,) array, not (3,3) matrix). The fix is already applied at line 325 of `stage_a_mapping_adam_debug.py`. Ralph's zero-point check (2025-11-22T114945Z) PASSED with perfect correlation and chi-squared alignment, validating the U-matrix logic at zero deltas. Now we can run the full Phase 5 convergence test without the shape mismatch crash.
