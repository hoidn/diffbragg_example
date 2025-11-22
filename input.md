# Ralph Work Order — TORCH-REFINE-002E Phase B1: Local Gradient Probe

## Summary
Extend `stage_a_mapping_adam_debug.py` with a gradient-probe mode that evaluates χ² and per-DoF gradients at the mapping zero point to determine whether the Adam degradation is due to non-zero gradients or optimizer tuning issues.

## Mode
none

## Focus
TORCH-REFINE-002E — Fix Stage A Zero-Point Geometry Discontinuity

## Branch
integration

## Mapped tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (regression guard)
- none — diagnostic probe script (CPU-only analysis tool)

## Artifacts
```
plans/active/TORCH-REFINE-002E/reports/2025-11-22T094500Z/
├── phase_a_review.md               (already present — Phase A synthesis)
├── gradient_probe.json             (Phase B1 deliverable)
├── gradient_probe.log              (script execution log)
├── pytest_stage_a_regression.log   (collect + test logs)
└── commands.txt                    (reproducible commands)
```

## Do Now

### Context
Phase A (A0, A2) definitively characterized the A* parity gap:
- **Confirmed H1:** The 4e-5 A* difference is dominated by **symmetric strain** (log_u_symmetric_norm ≈ 1.4e-3), not pure rotation
- **Rejected H2:** Baseline cell mismatch is NOT the cause—both B_ideal variants show identical strain

However, TOOLING-VIS-001 Phase 5 shows that **all Adam DoF combinations degrade χ² and CC** from the mapping zero point:
- **A_scale_only:** χ² 1.13M → 3.52M (+210%), CC 1.0 → 0.846
- **D_full:** χ² 1.13M → 2.70M (+138%), CC 1.0 → 0.881

**Critical question:** Is the gradient truly zero at the mapping zero point, or is Adam legitimately walking away from a non-optimal configuration?

Phase B1 will answer this by computing ∂χ²/∂θ for all DoFs at the zero-parameter point and identifying which (if any) have non-negligible magnitude/sign.

### Implementation Tasks

1. **Extend `stage_a_mapping_adam_debug.py` with gradient probe mode**

   File: `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py`

   Add a new `--mode gradient_probe` option that:
   - Initializes Stage-A parameters at the mapping zero point (same setup as Phase 1/2)
   - Sets `requires_grad=True` for the DoF subset: `{log_scale, cell_logs, angle_raws, orientation_vec}`
   - Performs a **single forward pass** through the Stage-A LBFGS closure
   - Computes χ² using `_compute_variance_weighted_loss` (with detached denominator per PHYSICS-LOSS-001)
   - Calls `chi_squared.backward()` to populate gradients
   - Extracts and logs:
     - `chi_squared_value` (scalar float)
     - `grad_log_scale` (scalar, shape [])
     - `grad_cell_logs` (3-element array, [a_log, b_log, c_log])
     - `grad_angle_raws` (3-element array, [alpha, beta, gamma])
     - `grad_orientation_vec` (3-element array, normalized tangent space)
   - For each gradient, report:
     - Magnitude (`torch.norm()` or element-wise abs max)
     - Sign (positive/negative/mixed for multi-element grads)
   - Optionally, repeat the forward pass with a **trusted ROI subset** (e.g., top 20 ROIs by mapping CC ≥ 0.95) to isolate whether outlier ROIs dominate the global gradient

   **Output format:**
   ```json
   {
     "mode": "gradient_probe",
     "zero_point": {
       "chi_squared": <float>,
       "dof_gradients": {
         "log_scale": {
           "value": <float>,
           "magnitude": <float>
         },
         "cell_logs": {
           "value": [<float>, <float>, <float>],
           "magnitude": <float>,
           "element_wise_max_abs": <float>
         },
         "angle_raws": { ... },
         "orientation_vec": { ... }
       }
     },
     "trusted_roi_subset": {
       "roi_count": <int>,
       "selection_criterion": "mapping_cc >= 0.95",
       "chi_squared": <float>,
       "dof_gradients": { ... }
     }
   }
   ```

2. **Execute the gradient probe on canonical refGeom (CPU)**

   ```bash
   python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
     --mode gradient_probe \
     --device cpu \
     --out-dir plans/active/TORCH-REFINE-002E/reports/2025-11-22T094500Z/ \
     > plans/active/TORCH-REFINE-002E/reports/2025-11-22T094500Z/gradient_probe.log 2>&1
   ```

   Verify that:
   - `gradient_probe.json` contains both global and trusted-ROI gradient evaluations
   - Log includes the mapping zero-point χ² value (should match TOOLING-VIS-001 Phase 1 `before` value ≈ 1.13M)
   - Script exits cleanly (no NaN/Inf gradients due to variance floor issues)

3. **Regression check: Stage-A expansion smoke**

   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   DBEX_SMOKE_DETECTOR_SIZE=small \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest --collect-only \
     tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
     > plans/active/TORCH-REFINE-002E/reports/2025-11-22T094500Z/collect_stage_a.log 2>&1

   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   DBEX_SMOKE_DETECTOR_SIZE=small \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv \
     tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
     > plans/active/TORCH-REFINE-002E/reports/2025-11-22T094500Z/pytest_stage_a_regression.log 2>&1
   ```

   Capture both logs to ensure no geometry-related regressions from Phase A2 helpers.

4. **Document commands in `commands.txt`**

   ```bash
   cat > plans/active/TORCH-REFINE-002E/reports/2025-11-22T094500Z/commands.txt <<'EOF'
   # Phase B1 gradient probe execution
   python plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py \
     --mode gradient_probe \
     --device cpu \
     --out-dir plans/active/TORCH-REFINE-002E/reports/2025-11-22T094500Z/

   # Stage-A regression check
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   DBEX_SMOKE_DETECTOR_SIZE=small \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
   EOF
   ```

## How-To Map

### Gradient Probe Implementation Details

**Key design decisions:**

1. **Variance-weighted loss consistency:**
   - Use the **same** `_compute_variance_weighted_loss` helper as Stage-A LBFGS closures
   - Ensure `sigma_readout` and `sigma_floor` match the values used in TOOLING-VIS-001 Phase 5
   - Detach the denominator per PHYSICS-LOSS-001 (chi_squared = sum(diff^2 / variance.detach()))

2. **DoF parameterization:**
   - `log_scale`: scalar, shape []
   - `cell_logs`: [log(a), log(b), log(c)], shape [3]
   - `angle_raws`: [alpha, beta, gamma] in radians, shape [3]
   - `orientation_vec`: normalized tangent-space representation, shape [3]
   - Initialize all at **zero deltas** (mapping zero point)

3. **Trusted ROI subset selection:**
   - Filter ROIs by mapping CC ≥ 0.95 (or top N=20 ROIs if fewer than 20 exceed threshold)
   - Rebuild the loss using **only** the trusted ROI pixel masks
   - Report both global and trusted gradients to isolate outlier effects

4. **Numerical stability:**
   - If any gradient contains NaN/Inf, log the intermediate tensor shapes and values
   - Check that `sigma_floor` clamp is active (variance_floor_clamp_fraction > 0 per PHYSICS-LOSS-002)

### Environment & Execution

**Required environment:**
```bash
KMP_DUPLICATE_LIB_OK=TRUE
NANOBRAGG_DISABLE_COMPILE=1
```

**Device:** `--device cpu` (gradient probe is CPU-only for now; avoids CUDA OOM on canonical refGeom)

**Expected runtime:** ~30-60 seconds (single forward pass + backward pass)

## Pitfalls To Avoid

1. **Do NOT modify production Stage-A refinement code** — gradient probe is a diagnostic-only mode in the debug driver script
2. **Preserve Phase 5 Adam parameter setup** — use the same `global_scale_hint`, baseline misset, and sigma values so results are comparable
3. **Environment freeze** — do not install new packages; use existing `torch`, `cctbx`, `nanobrag_torch`
4. **Detach variance denominator** — per PHYSICS-LOSS-001, `chi_squared = sum(diff^2 / variance.detach())` to avoid biasing gradients
5. **Device/dtype neutrality** — all tensors on CPU, torch.float32 (or float64 if script already uses it)
6. **No ad-hoc print debugging** — log structured JSON and let the probe script write clean artifacts
7. **Check for zero-division** — if trusted ROI subset is empty, skip that section and log a warning
8. **Respect findings:**
   - **GEOMETRY-003:** Baseline misset derived per `derive_robust_misset` (already in place from Phase A2)
   - **PHYSICS-LOSS-001:** Variance-weighted loss with detached denominator
   - **PHYSICS-LOSS-002:** Sigma floor clamp active and logged

## If Blocked

- If `stage_a_mapping_adam_debug.py` doesn't have a clear `--mode` flag structure, add one (similar to `--phases` argument)
- If gradient computation fails with NaN/Inf, first check that `sigma_floor` is non-zero and clamp stats are logged
- If trusted ROI subset logic is unclear, use a simple `mapping_cc_per_roi >= 0.95` filter and log how many ROIs pass
- Record the blocking error signature in `plans/active/TORCH-REFINE-002E/reports/2025-11-22T094500Z/blocked.txt` and mark the attempt in `docs/fix_plan.md` Attempts History

## Findings Applied

- **GEOMETRY-003:** Baseline misset alignment (TORCH-REFINE-002E A0/A2 already implemented `derive_robust_misset`)
- **PHYSICS-LOSS-001:** Variance-weighted chi-squared loss with detached denominator
- **PHYSICS-LOSS-002:** Sigma floor clamp (default ≥1 photon) and telemetry
- **REFINE-004/005:** Stage-A HKL halo/interpolation (not directly relevant to this probe, but maintained for consistency)

## Pointers

- **Spec:** `docs/spec-db-workflow.md` §Stage A (mapping zero-point invariant expectation)
- **Spec:** `docs/spec-db-core.md` §Variance Model (chi-squared definition)
- **Implementation plan:** `plans/active/TORCH-REFINE-002E/implementation.md` (Phase B checklist B1)
- **Phase A review:** `plans/active/TORCH-REFINE-002E/reports/2025-11-22T094500Z/phase_a_review.md`
- **Adam debug driver:** `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py`
- **Bridge helpers:** `dbex/nanobrag_bridge.py` (`derive_robust_misset`, `compute_baseline_misset_deg`)
- **Loss helper:** `dbex/nanobrag_refinement.py` (`_compute_variance_weighted_loss`)

## Next Up (optional)

If Phase B1 gradients are near-zero (e.g., all magnitudes < 1e-6), next action is **Phase B2** (scale analytical optimum check) or **Phase B3** (LR sensitivity sweep).

If gradients are non-negligible and positive for scale, next action is **Phase B2** to derive the closed-form optimal scale α* and see if `log_scale=0` is already near the minimum.

## Doc Sync Plan

Not applicable — this is a diagnostic probe; no test registry or selector changes.

## Normative Math/Physics

**Chi-squared definition:** See `docs/spec-db-core.md` §Variance Model:
```
χ² = Σ_pixels [(pred - obs)² / (pred + sigma_readout²)]
```
where `pred` is detached in the denominator per PHYSICS-LOSS-001.

**Gradient interpretation:**
- If ∂χ²/∂θ = 0 at the mapping zero point, Adam should not move (within numerical tolerance)
- If ∂χ²/∂θ > 0 for some DoF, increasing θ increases loss → Adam walks in the negative direction, which may still degrade fit if the Hessian is ill-conditioned
- If ∂χ²/∂(log_scale) < 0, decreasing scale improves fit → current `log_scale=0` may not be optimal

Refer to the normative spec sections rather than paraphrasing equations in this work order.
