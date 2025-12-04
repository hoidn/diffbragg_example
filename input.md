Summary: Capture HKL-query telemetry alongside the reflection ledger so we can prove whether Stage A/simulate_forward_once are sampling the wrong lattice before touching nanobrag_torch physics.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors_small.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode baseline --collect-hkl-stats --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T230000Z/stage_a_baseline_probe_baseline.json
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors_small.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode perturbed --collect-hkl-stats --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T230000Z/stage_a_baseline_probe_perturbed.json
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T230000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T230000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T230000Z/pytest_db_at_028_029.log
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T230000Z/

Do Now (hard validity contract):
- Implement: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py::main`
  - Add an optional `--collect-hkl-stats` flag, helper to aggregate per-panel stats, and instrumentation that rebuilds a Stage A warm-cache context via `_build_stage_a_context(..., debug_config={'collect_hkl_stats': True})` so each panel simulator runs once and exposes `h_min/h_max`, `k_min/k_max`, `l_min/l_max`, and in/out-of-bounds counts.
  - Thread `debug_config={'collect_hkl_stats': True}` into `simulate_forward_once` when the flag is set and persist the resulting `per_panel_hkl_stats` + `hkl_stats` metadata next to the existing reflection ledger, ensuring both warm (Stage A) and cold (`simulate_forward_once`) paths capture hit rates for the exact dataset that feeds DB-AT-028/029.
  - Extend the JSON payload with a `hkl_query_stats` block and log concise console summaries so the supervisor loop can immediately tell whether nanobrag_torch is querying outside the populated HKL grid; preserve existing reflection/ROI ledger output verbatim.
  - Re-run the baseline + perturbed probes and the DB-AT-028/029 selector command above so `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T230000Z/` holds the refreshed reflection ledger, HKL stats, and test telemetry for the same env/config.

Deterministic Parity Crisis:
- Independent Reference: DIALS refGeom reflection table (`sp.proc/refGeom_small/refGeom_small.refl`) remains independent of nanobrag_torch and matches the observed targets (median target/reference ratio ≈ 1.02), so it is the authoritative ROI-level contract.
- Transformation Ledger:

  | Field | Units / Frame / Order | Producer (file:line) | Consumer (file:line) | Observed evidence | Hypothesis |
  | --- | --- | --- | --- | --- | --- |
  | Masked mean baseline (`telemetry.target_mean_masked`, `model_mean_masked`, `chi²/pixel`) | ADU/pixel, detector loss mask ordering | `dbex/refinement/stage_a.py:403-520` | `tests/dbex/test_stage_a_smoke_parity.py:335-515` | `stage_a_baseline_probe_baseline.json` shows `target_mean_masked = model_mean_masked = 87.118 ADU` yet `chi²/pixel(initial)=9.8e5`. | Global energy budget matches; deterministic crisis is in ROI redistribution rather than scalar calibration. |
  | ROI 0 Panel 0 `[897:909,17:29]`, HKL (−10,2,0) | ADU/pixel (ROI mask order) | `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:611-747` | `tests/dbex/test_stage_a_smoke_parity.py:398-515` | Reflection 8.69 ADU vs Stage A 0.0199 ADU; `stagea_vs_amp_sq_ratio=0.0020`. | Simulator drops ≈500× energy for this HKL even though target+reference agree, so HKL sampling/normalization is suspect. |
  | ROI 1 Panel 0 `[644:656,21:33]`, HKL (−7,5,−3) | ADU/pixel | same as above | same as above | Reflection 8.12 ADU vs Stage A 5.8×10⁻⁴ ADU (`stagea_vs_ref_ratio=7.1×10⁻⁵`). | Most reflections collapse to ≪1 % of expected intensity, so error is systemic, not random. |
  | ROI 2 Panel 0 `[257:269,37:49]`, HKL (−3,8,−9) | ADU/pixel | same | same | Reflection 83.10 ADU vs Stage A 0.244 ADU (`stagea_vs_amp_sq_ratio=4.8×10⁻⁴`). | Even bright peaks lose >99.9 % of signal ⇒ mismatch originates upstream of ROI masking. |
  | ROI 14 Panel 0 `[431:443,434:446]`, HKL (0,2,−2) | ADU/pixel | same | same | Reflection 1.74 ADU vs Stage A 407.7 ADU (`stagea_vs_ref_ratio=234`, `stagea_vs_amp_sq_ratio=10.4`). | Minority of HKLs explode, implying coordinate or normalization drift rather than a single missing scalar. |
  | ROI 21 Panel 0 `[787:799,694:706]`, HKL (−2,−6,5) | ADU/pixel | same | same | Reflection 192.88 ADU vs Stage A 11.80 ADU (`stagea_vs_ref_ratio=0.061`). | Median deficit (~16×) matches chi² signature and shows the simulator under-distributes energy almost everywhere. |

- Boundary Bisection Step: Use the new `--collect-hkl-stats` flag to record Stage A and simulate_forward_once HKL query ranges and hit rates; if either path spends most queries outside the populated HKL grid (bounds from `build_structure_factor_grid`), root cause = projection/coordinate bug; if hit rate ≈100 % yet ROI intensities diverge, escalate to nanobrag_torch physics (Lorentz/polarization/unit handling) with this telemetry in hand.

How-To Map:
- Reuse the smoke fixture’s refined MTZ + calibration so HKL indices and `N_cells` match DB-AT selectors; do not rebuild structure-factor grids from scratch.
- Convert `mapping_context.hkl_indices` to tuple keys once (`tuple(map(int, idx))`) and store floats in a Python dict; fail fast when the reflection-table Miller index is absent so asset drift is surfaced immediately.
- Instantiate the diagnostic Stage A context with `panel_slices=None` / `enable_roi_mode=False` to limit HKL stats to canonical panel simulators; ROI stats are unnecessary for this boundary.
- Capture HKL stats before running DB-AT tests so each command in the mapped list produces artifacts under the same timestamp directory.
- Keep env vars identical to prior probes (AUTHORITATIVE_CMDS_DOC, DBEX_SMOKE_*, KMP, NANOBRAGG_DISABLE_COMPILE) to satisfy testing-guide policy.

Pitfalls:
- Forgetting to guard simulator.run() with try/except will crash the probe if nanobrag_torch raises during diagnostics; log warnings and keep evidence flowing.
- HKL stats rely on debug-only hooks; ensure the new flag defaults to False so production runs remain untouched.
- Probe saturation guard: this addition reuses the existing `collect_hkl_stats` hook rather than inventing a third instrumentation path—avoid layering another probe until a production fix is attempted.
- Keep JSON additions backward-compatible (None when flag unset) so historical artifacts remain parseable.
- When matching reflections to ROIs, continue to tolerate the +3 px ROI padding; report mismatches explicitly to avoid silent skew in percentiles.

If Blocked:
- Record exceptions or missing HKL assets in `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T230000Z/summary.md`, log the condition in `docs/fix_plan.md` Attempts History and `galph_memory.md`, and only switch initiatives after deciding whether a harness/spec-change effort (e.g., nanobrag_torch patch) is required.
