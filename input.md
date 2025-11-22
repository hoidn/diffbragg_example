# Ralph Work Order — TORCH-REFINE-002E Phase A3: Mapping Forward Model Comparison

## Summary
Compare forward-model outputs between the mapping MOSFLM A* injection path and the Stage-A explicit cell+misset parameterization at zero deltas on a single panel to isolate whether the 2.6× chi-squared discrepancy originates from encoding conventions or simulator numerical differences.

## Mode
none

## Focus
TORCH-REFINE-002E — Fix Stage A Zero-Point Geometry Discontinuity

## Branch
integration

## Mapped tests
- `tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion` (regression guard)
- none — diagnostic comparison script (CPU-only analysis tool)

## Artifacts
```
plans/active/TORCH-REFINE-002E/reports/2025-11-22T100330Z/
├── forward_model_comparison.json      (Phase A3 deliverable — per-pixel/chi² comparison)
├── forward_model_comparison.log       (script execution log)
├── pytest_stage_a_regression.log      (collect + test logs for regression guard)
└── commands.txt                       (reproducible commands)
```

## Do Now

### Context

**Phase B1 confirmed:** The gradient probe shows that the explicit cell+misset parameterization at zero deltas yields χ² ≈ 2.98e6, which is **~2.6× higher** than the mapping MOSFLM A* path (χ² ≈ 1.13e6 from TOOLING-VIS-001 Phase 1 zero_point_check.json). All DoF gradients are large and non-zero (orientation_vec magnitude ≈2.88e8), proving Adam **legitimately walks away** from this starting point.

**Critical Question for Phase A3:** Does this 2.6× chi-squared gap arise from:
1. **Encoding/convention differences** in how the two paths construct the crystal A* matrix (e.g., MOSFLM injection vs cell+misset composition), OR
2. **Simulator numerical differences** (e.g., interpolation schemes, spot shape models, HKL grid coverage) that manifest when comparing Bragg stack outputs pixel-by-pixel?

Phase A3 will answer this by running **both** paths through the same nanobrag_torch simulator on a **single panel** and comparing:
- Per-pixel absolute differences in the Bragg stack
- Per-pixel relative differences (as % of mapping intensity)
- Chi-squared contribution differences
- HKL grid statistics (hits, weights, out-of-bounds counts)

If the forward models are **numerically identical** (pixel differences << 1e-6 photons, χ² identical to machine precision), the 2.6× gap is purely a **parameterization artifact** → proceed directly to **Branch G (geometry fix)**.

If the forward models **differ significantly** despite "zero deltas", there's a **simulator parity bug** between the mapping injection path and the explicit parameterization path → open a new blocker initiative to fix the simulator before attempting geometry realignment.

### Implementation Tasks

1. **Author Phase A3 comparison script**

   **File:** `plans/active/TORCH-REFINE-002E/bin/compare_mapping_vs_stage_a_forward.py`

   **Purpose:** Run both the mapping MOSFLM A* path and the Stage-A explicit cell+misset path (at zero deltas) through nanobrag_torch on a single panel, compare outputs pixel-by-pixel.

   **Requirements:**
   - Accept CLI args: `--device {cpu,cuda}`, `--panel-id {int}` (default 0), `--out-dir {path}`
   - Load canonical refGeom assets (`sp.proc/refGeom.{expt,refl}`, `sp.proc/idx-0000_refined.expt`)
   - Extract panel `--panel-id` metadata (detector config, beam, wavelength, etc.)
   - Build **two** crystal configurations:
     - **Path A (Mapping):** Use MOSFLM A* injection from mapping (`simulate_forward_once` / `build_mapping_stage_a_context` machinery)
     - **Path B (Stage-A zero):** Use GEOMETRY-003 baseline misset + zero cell/angle/orientation deltas (explicit cell+misset parameterization from `derive_robust_misset`)
   - For both paths:
     - Construct `nanobrag_torch.Crystal` with same HKL grid, beam config, spot_scale, global_scale_hint
     - Run simulator on the **same** detector ROI/panel
     - Extract Bragg stack (forward model image) as `[panel, slow, fast]` tensor
   - Compute comparisons:
     - `bragg_diff = abs(bragg_mapping - bragg_stage_a_zero)`
     - `bragg_rel_diff = bragg_diff / (bragg_mapping + 1.0)`  # avoid divide-by-zero
     - `chi_squared_mapping` using variance-weighted loss on mapping Bragg vs target
     - `chi_squared_stage_a_zero` using same loss on Stage-A zero Bragg vs target
     - HKL grid stats for both paths (num_hkl_hits, out_of_bounds_count, etc.)
   - Emit JSON summary:
     ```json
     {
       "mode": "forward_model_comparison",
       "panel_id": 0,
       "device": "cpu",
       "mapping_path": {
         "chi_squared": <float>,
         "bragg_stack_shape": [panel, slow, fast],
         "bragg_stack_sum": <float>,
         "hkl_hits": <int>,
         "hkl_out_of_bounds": <int>
       },
       "stage_a_zero_path": {
         "chi_squared": <float>,
         "bragg_stack_shape": [panel, slow, fast],
         "bragg_stack_sum": <float>,
         "hkl_hits": <int>,
         "hkl_out_of_bounds": <int>
       },
       "comparison": {
         "bragg_diff_max": <float>,
         "bragg_diff_mean": <float>,
         "bragg_diff_median": <float>,
         "bragg_rel_diff_max": <float>,
         "bragg_rel_diff_mean": <float>,
         "chi_squared_diff_abs": <float>,
         "chi_squared_diff_rel": <float>
       },
       "conclusion": "identical|differs_numerically"
     }
     ```
   - **Conclusion heuristics:**
     - If `bragg_diff_max < 1e-6` photons AND `chi_squared_diff_abs < 1e-6`: emit `"identical"`
     - Else: emit `"differs_numerically"`

2. **Execute the comparison script**

   **Command:**
   ```bash
   python plans/active/TORCH-REFINE-002E/bin/compare_mapping_vs_stage_a_forward.py \
     --device cpu \
     --panel-id 0 \
     --out-dir plans/active/TORCH-REFINE-002E/reports/2025-11-22T100330Z/
   ```

   **Expected output:** `forward_model_comparison.json` + `.log`

3. **Regression guard**

   Run the Stage A expansion smoke to ensure no regressions from Phase B1 work:

   ```bash
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   DBEX_SMOKE_DETECTOR_SIZE=small \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion \
     2>&1 | tee plans/active/TORCH-REFINE-002E/reports/2025-11-22T100330Z/pytest_stage_a_regression.log
   ```

4. **Save commands for reproducibility**

   **File:** `plans/active/TORCH-REFINE-002E/reports/2025-11-22T100330Z/commands.txt`

   Content:
   ```bash
   # Phase A3 — Mapping forward model comparison
   # Date: 2025-11-22T100330Z

   # 1. Forward model comparison
   python plans/active/TORCH-REFINE-002E/bin/compare_mapping_vs_stage_a_forward.py \
     --device cpu \
     --panel-id 0 \
     --out-dir plans/active/TORCH-REFINE-002E/reports/2025-11-22T100330Z/

   # 2. Regression guard
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   DBEX_SMOKE_DETECTOR_SIZE=small \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion
   ```

## How-To Map

### Environment Setup
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
```

### Script Implementation Guidance

**Reuse existing helpers:**
- From `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py`:
  - `build_mapping_stage_a_context()` for mapping path crystal config
  - `_stage_a_forward()` machinery (adapt to extract just Bragg stack, not full loss)
- From `dbex/nanobrag_bridge.py`:
  - `derive_robust_misset()` with GEOMETRY-003 baseline for Stage-A zero path
  - `create_crystal_config()` for explicit cell+misset encoding

**Key comparisons to emit:**
1. **Pixel-level:** `max/mean/median(abs(bragg_mapping - bragg_stage_a_zero))`
2. **Relative:** `max/mean/median(abs_diff / (bragg_mapping + 1.0))`
3. **Chi-squared:** Variance-weighted loss for both paths using same target/sigma_readout
4. **HKL grid:** Confirm both paths hit same HKL indices (if HKL coverage differs, that's a clue to the simulator parity bug)

**Decision tree based on results:**
- **Scenario 1 (Identical forward models):**
  - `bragg_diff_max < 1e-6 photons`, `chi_squared_diff_abs < 1e-6`
  - **Conclusion:** The 2.6× global chi-squared gap is NOT from the simulator—it's purely a **geometry parameterization artifact** (the Phase A strain encodes a real physics difference that manifests when switching from MOSFLM A* injection to explicit cell+misset).
  - **Next Actions:** Proceed to **Phase C Branch G** (geometry fix) — adjust baseline geometry so the explicit path reproduces mapping's effective cell.

- **Scenario 2 (Different forward models):**
  - `bragg_diff_max > 1e-4 photons` OR `chi_squared_diff_abs > 1.0`
  - **Conclusion:** There's a **simulator parity bug** between the mapping injection path and the explicit parameterization path (e.g., different HKL grid, interpolation, spot shape).
  - **Next Actions:** Open a new blocker initiative (`TORCH-SIMULATOR-PARITY-001`) to diagnose and fix the simulator before attempting geometry realignment.

### Regression Guard
```bash
# Small-detector Stage A expansion smoke
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion

# Expected: PASSED (no regressions from Phase B1)
```

## Pitfalls To Avoid

1. **Don't assume "zero deltas" = identical simulator inputs**
   - Phase B1 showed χ²_explicit ≠ χ²_mapping at zero deltas
   - Phase A3 will isolate whether that gap is from encoding OR simulator

2. **Preserve device/dtype neutrality**
   - Use same device for both paths (default: CPU)
   - All tensors must match device/dtype before comparison

3. **Use the same HKL grid / structure factors for both paths**
   - Both paths should consume identical `structure_factor_grid` from mapping
   - If Path B rebuilds HKL grid from cell, that's a clue to the encoding difference

4. **Variance-weighted chi-squared (PHYSICS-LOSS-001 contract)**
   - Use detached denominator: `(pred - obs)^2 / (pred.detach() + sigma^2)`
   - Same `sigma_readout` and `sigma_floor_value` for both paths

5. **Single-panel scope only**
   - Phase A3 is a diagnostic probe, not a full-dataset run
   - Panel 0 is sufficient to isolate encoding vs simulator differences

6. **Don't modify production code**
   - All implementation goes into `plans/active/TORCH-REFINE-002E/bin/compare_mapping_vs_stage_a_forward.py`
   - Reuse bridge helpers (`derive_robust_misset`, `create_crystal_config`) but don't change them

## If Blocked

**Blocker:** Comparison script shows large differences in forward models (`bragg_diff_max > 1e-4 photons`) despite zero deltas.

**Capture:**
1. Save `forward_model_comparison.json` with `"conclusion": "differs_numerically"`
2. Log the specific divergence (pixel locations, HKL indices, intensities)
3. Mark TORCH-REFINE-002E as `blocked` in `docs/fix_plan.md`
4. Open new initiative `TORCH-SIMULATOR-PARITY-001` with artifacts pointing to Phase A3 results
5. Record in `galph_memory.md` that geometry fix (Branch G) is deferred pending simulator parity fix

**Fallback:**
- If script fails to execute (e.g., missing dependencies, import errors), capture the traceback
- Document the blocker in Attempts History with exact error message
- Recommend environment audit or simpler reproducer before retrying

## Findings Applied (Mandatory)

**Relevant Finding IDs from `docs/findings.md`:**

- **GEOMETRY-001** (Detector mapping) — Enforces Cartesian conventions for beam/detector origins; both paths must honor these.
- **GEOMETRY-002** (Euler inversion) — Misset derivation uses cctbx Euler conventions; Phase A3 must verify both paths produce identical orientation matrices.
- **GEOMETRY-003** (B_ideal-based mapping misset) — Stage-A zero path uses `derive_robust_misset()` to align baseline orientation; Phase A3 will test whether this encoding matches mapping MOSFLM A*.
- **PHYSICS-LOSS-001** (Variance-weighted loss) — Both paths must use identical chi-squared formula with detached denominator.
- **REFINE-004** (Stage-A gate) — Not directly applicable (Phase A3 is diagnostic only), but chi-squared comparison informs whether the 0.9× improvement gate is achievable.
- **REFINE-005** (HKL halo/interpolation) — Both paths should use same HKL grid/interpolation mode; if they differ, that's evidence of simulator parity gap.

**Adherence notes:**
- GEOMETRY-003 baseline misset is used in Path B (Stage-A zero)
- PHYSICS-LOSS-001 variance-weighted loss used for chi-squared computation on both paths
- If REFINE-005 halo/interpolation settings differ between paths, log that as a potential simulator parity bug

## Pointers

**Specs:**
- `docs/spec-db-workflow.md:35-50` — Stage A mapping zero-point invariant (normative requirement that zero deltas = mapping geometry)
- `docs/spec-db-core.md:25-45` — Geometry Mapping (A* matrix conventions, reciprocal basis)
- `docs/spec-db-conformance.md:15-30` — Mapping-Aligned Stage-A Initialization (DB-AT-024 contract)

**Architecture:**
- `docs/config_crosswalk.md:80-120` — Crystal mapping section (MOSFLM A* injection vs cell+misset)

**Findings:**
- `docs/findings.md:GEOMETRY-001` — Detector mapping conventions
- `docs/findings.md:GEOMETRY-002` — Euler inversion for misset derivation
- `docs/findings.md:GEOMETRY-003` — B_ideal-based baseline misset (used in Path B)
- `docs/findings.md:PHYSICS-LOSS-001` — Variance-weighted loss formula

**Implementation plan:**
- `plans/active/TORCH-REFINE-002E/implementation.md:78-96` — Phase A checklist (A3 now unblocked)
- `plans/active/TORCH-REFINE-002E/implementation.md:126-156` — Phase C decision branches (Branch G awaits A3 results)

**Prior artifacts:**
- `plans/active/TORCH-REFINE-002E/reports/2025-11-22T094500Z/gradient_probe.json` — Phase B1 results showing χ²_explicit ≈ 2.98e6 vs χ²_mapping ≈ 1.13e6
- `plans/active/TOOLING-VIS-001/reports/stage_a_refgeom_adam_debug/20251121T234215Z/zero_point_check.json` — Phase 1 zero-point check showing mapping MOSFLM path χ² ≈ 1.13e6

## Next Up (optional)

**If Phase A3 shows identical forward models:**
- Transition to **Phase C Branch G** (geometry fix) — adjust baseline geometry in next loop

**If Phase A3 shows different forward models:**
- Open **TORCH-SIMULATOR-PARITY-001** initiative to fix simulator parity bug before attempting geometry realignment

## Doc Sync Plan (Conditional)

**Not applicable** — Phase A3 is diagnostic only; no new tests added, no pytest collection changes.

**Future sync trigger:** If Phase C Branch G creates new geometry helpers or tests, then:
1. Run `pytest --collect-only` for affected selectors
2. Archive logs under the Branch G artifacts directory
3. Update `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` after code passes
