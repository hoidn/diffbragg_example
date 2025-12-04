Summary: Add HKL-orientation diagnostics to the Stage A baseline probe so we can prove DB-AT-028/029 failures track |Δhkl| misalignment instead of raw intensity scalars before touching nanobrag_torch.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-23T010000Z/db_at_028 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-23T010000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-23T010000Z/

Do Now (hard validity contract):
- Implement: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py::main`
  - Introduce `--collect-orientation-metrics` (store_true) and wire it into the reflection-table ledger. When enabled, compute the diffracted-beam vector at each matched ROI center (`detector[pid].get_pixel_lab_coord`, normalize to `s1`, use `beam.get_s0`), solve `h_frac = A^{-1} q` using `crystal.get_A()`, and record fractional HKL, `Δhkl`, `|Δhkl|`, resolution (Å = 1/‖q‖), and 2θ per ROI. Store these values inside each `reflection_metrics` entry plus a new top-level block `orientation_alignment` containing percentile stats and Pearson correlation between `|Δhkl|` and the existing Stage A↔reference ratios.
  - Extend the existing Markdown writer (currently `_summarize_spot_profiles`) so it also emits an “Orientation Alignment” section summarizing median `|Δhkl|`, median resolution, and the five worst ROIs by misalignment (panel, bbox, HKL, ratios). Reuse the same summary file so reviewers can see energy and orientation evidence side by side.
  - Run the probe once in normative geometry with every diagnostic enabled and capture stdout:  
    `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors_small.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode baseline --stage-a-mosaic-domains 16 --collect-hkl-stats --collect-spot-profiles --collect-orientation-metrics --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-23T010000Z/stage_a_baseline_probe_baseline.json | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-23T010000Z/stage_a_baseline_probe_baseline.log`
  - After the run, append a short python (or jq) snippet that prints the new `orientation_alignment` medians + correlation into `spot_profile_summary.md` so the ledger cites a human-readable summary.
- Pytest: Execute the mapped DB-AT selectors above with `DBAT028_ARTIFACT_DIR` / `DBAT029_ARTIFACT_DIR` pointing at the new report tree so chi²/ROI telemetry lines up with the fresh probe output.
- Artifacts: Keep the probe JSON/log, Markdown summary, and both pytest outputs under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-23T010000Z/` (subdirs `db_at_028/`, `db_at_029/`) so docs/fix_plan and the findings ledger can cite a single directory.

Deterministic Parity Crisis:
- Independent Reference: DIALS reflection table `sp.proc/refGeom_small/refGeom_small.refl` (refGeom smoke dataset). Its `intensity.sum.value` column remains independent of Stage A/mapping and reports target/ref median ≈1.02, so it is still the contract we must satisfy before touching simulator code.
- Transformation Ledger:
  | Field | Units/frame | Producer (file:line) | Consumer (file:line) | Observed evidence | Hypothesis |
  | --- | --- | --- | --- | --- | --- |
  | ROI 0 panel 0 [897:909,17:29], HKL (-10,2,0) Stage A mean | ADU/pixel | plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:1082-1105 | plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T150000Z/spot_profile_probe.json:357-414 | Stage A=1.99e-02 vs ref=8.69 (ratio 2.3e-03) while target/ref=0.90; spot-profile shows ROI keeps only 4.8% of halo energy | Simulator peak misses ROI center because HKL alignment is off by O(10⁻²), so chi² sees almost no modeled intensity where the reference bins it. |
  | ROI 1 panel 0 [644:656,21:33], HKL (-7,5,-3) Stage A mean | ADU/pixel | plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:1082-1105 | plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T150000Z/spot_profile_probe.json:403-446 | Stage A=5.78e-04 vs ref=8.12 (ratio 7.1e-05) even though |F|²/pix ≈ 4.34; only 0.54% of Stage A energy lands inside ROI | Deterministic HKL misalignment pushes most modeled energy into the halo, collapsing ROI intensity by 4–5 orders of magnitude relative to the reference. |
  | ROI 2 panel 0 [257:269,37:49], HKL (-3,8,-9) Stage A mean | ADU/pixel | plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:1082-1105 | plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T150000Z/spot_profile_probe.json:447-520 | Stage A=0.244 vs ref=83.1 (ratio 2.9e-03) while |F|²/pix is 509; halo stores 98.9% of modeled energy | Loss mask samples the wrong pixels because the modeled spot is shifted relative to the DIALS bbox, so chi² penalizes Stage A even though total energy matches the reference grid. |
  | ROI 14 panel 0 [431:443,434:446], HKL (0,2,-2) Stage A mean | ADU/pixel | plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:1082-1105 | plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T150000Z/spot_profile_probe.json:909-954 | Stage A=407.7 vs ref=1.74 (ratio 234×) and |F|²/pix already overshoots ref 22×; ROI fraction≈0.999 so the simulator dumps everything into that bbox | HKL assignment is correct but nanobrag_torch over-concentrates the peak because it never compensates for partiality/Lorentz, creating “bright spike” outliers that dominate χ². |
  | ROI 27 panel 0 [350:362,877:889], HKL (4,-5,-1) Stage A mean | ADU/pixel | plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:1082-1105 | plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T150000Z/spot_profile_probe.json:1508-1541 | Stage A=16.8 vs ref=5.42 (ratio 3.10) while Stage A/|F|²=4.5e-04 → the simulator samples the wrong angular slice so whatever energy lands in the ROI bears no resemblance to the reference. |
- Boundary Bisection Step: The new orientation ledger must report |Δhkl| and show whether the low-intensity ROIs (ratios ≪1) coincide with large misalignment magnitudes. If |Δhkl| tracks the measured ratios, the next loop can justify either (a) retargeting simulators to the DIALS ROI centers or (b) adding a nanobrag_torch debug patch to trace per-reflection q vectors. If |Δhkl| stays ~0 while ratios still diverge, we pivot back to physics (Lorentz/partiality) instead of geometry.

How-To Map:
- After editing the probe, rerun the single baseline command above (no perturbed geometry this loop) and keep the stdout log under the new report directory.
- Use a tiny python helper (e.g., `python - <<'PY' ...`) to read `stage_a_baseline_probe_baseline.json` and append the `orientation_alignment` medians, correlation coefficient, and worst-5 misalignments into `spot_profile_summary.md` immediately so reviewers do not need to open the raw JSON.
- When checking correlation, treat NaNs carefully (`np.isfinite`); log the computed Pearson metric in the Markdown summary for traceability.
- Run the DB-AT selectors once after the probe so chi²/pixel and ROI CC logs share the same artifact root; keep the naming pattern from prior loops so diffs are easy to audit.
- File naming: keep the probe JSON (`stage_a_baseline_probe_baseline.json`), log (`...log`), and Markdown summary (`spot_profile_summary.md`) in the report root plus `db_at_028/` and `db_at_029/` subdirectories for pytest outputs/metrics.

Pitfalls:
- Forgetting to guard the new orientation math behind `--collect-orientation-metrics` will slow every probe invocation and break legacy scripts.
- Detector pixels are `[fast, slow]`; swapping order when calling `get_pixel_lab_coord` yields meaningless q vectors.
- `crystal.get_A()` returns row-major values; reshape carefully and use `np.linalg.solve(A, q)` (not `A.T`). Drop a quick unit test in the script to assert `A @ h_int` ≈ `q` for matched reflections to catch mistakes.
- Normalize `s1` with wavelength in Å so units match `beam.get_s0()`; mixing meters/Å gives 1e10-scale deltas and bogus resolution.
- Clamp halo windows to detector bounds before slicing or NumPy will wrap indices and corrupt energy totals.
- `np.corrcoef` returns NaNs if either column is constant; guard with `len(valid_pairs) > 1` and log “undefined” instead of crashing.
- Remember to include the new orientation section in the Markdown summary; a JSON-only evidence drop will force another loop.
- Keep the probe command consistent with prior env vars; changing calibration/HKL assets mid-loop invalidates trend comparisons.
- Do not run perturbed geometry this loop—DB-AT-027 parity is already proven, and extra runs violate the stop-and-read rule.
- If the probe crashes, do not rerun blindly; capture the traceback under the report tree and flag the blocker in docs/fix_plan before retrying.

If Blocked:
- If `get_pixel_lab_coord` raises (missing detector geometry, etc.), log the failing ROI/panel plus the stack trace under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-23T010000Z/summary.md`, update docs/fix_plan Attempts History and galph_memory, and pause. Do not backdoor nanobrag_torch instrumentation unless the evidence shows geometry data are inaccessible—in that case, request a dedicated Environment Freeze exception loop before editing simulator code. If pytest failures prevent artifact capture, still stash the partial logs/JSON and note the status so the ledger records the block.
