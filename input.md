Summary: Add an HKL-amplitude ledger to the Stage A baseline probe so we can tell whether the 9.8e5 chi²/pixel crisis is born before nanobrag_torch squares |F| or inside the simulator before attempting code fixes.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors_small.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode baseline --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T210000Z/stage_a_baseline_probe_baseline.json
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors_small.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode perturbed --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T210000Z/stage_a_baseline_probe_perturbed.json
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T210000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T210000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T210000Z/pytest_db_at_028_029.log
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T210000Z/

Do Now (hard validity contract):
- Implement: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py::main`
  - Build a dict from `mapping_context.hkl_indices` → `mapping_context.hkl_amplitudes` (torch/numpy neutral) and, for every ROI matched to a reflection, look up that Miller index so we can compute `amp_sq_per_pixel = (|F|^2 / n_masked_pixels)` beside the reflection-table mean.
  - Extend the existing `reflection_comparison` block to persist the HKL index, HKL amplitude, `amp_sq_per_pixel`, and derived ratios (`amp^2` vs reflection, Stage A vs amp^2) plus percentile stats/top/bottom-N tables; emit the same information to the console summary for quick scanning.
  - Thread the HKL ledger into `probe_metadata` (resolved MTZ path/column already recorded) and fail fast if a reflection lacks an HKL match, so downstream analyses know whether the mismatch originates before or after the simulator.
  - Re-run the baseline + perturbed probes and DB-AT-028/029 commands above so the refreshed artifacts under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T210000Z/` contain the new ledger plus the usual chi²/ROI telemetry.

Deterministic Parity Crisis:
- Independent Reference: DIALS refGeom reflection table (`sp.proc/refGeom_small/refGeom_small.refl`) — provides per-ROI `intensity.sum.value` independent of nanobrag_torch and matches the observed targets (median target/ref ratio 1.0196), making it the authoritative contract for ROI-level energy.
- Transformation Ledger:

  | Field | Units / Frame / Order | Producer (file:line) | Consumer (file:line) | Observed evidence | Hypothesis |
  | --- | --- | --- | --- | --- | --- |
  | `telemetry.target_mean_masked` | ADU/pixel, Stage A loss mask order `[panel, slow, fast]` | `dbex/refinement/stage_a.py:423-431` | `tests/dbex/test_stage_a_smoke_parity.py:233-255` | `stage_a_baseline_probe_baseline.json` (2025-12-20T010000Z) → 87.1184 ADU | Target ingestion correct; global energy budget conserved. |
  | `telemetry.model_mean_masked` | same as above | `dbex/refinement/stage_a.py:456-518` | `dbex/refinement/reconstruction.py:497-572` | Same probe → 87.1184 ADU (ratio 1.0) | Baseline scaling now aligned; mismatch is not a scalar offset. |
  | ROI #0 Panel0 `[897:909,17:29]` | ADU/pixel, detector ROI mask | `compare_stage_a_baseline.py:439-704` | `tests/dbex/test_stage_a_smoke_parity.py:244-252` | Reflection mean 8.69 ADU vs Stage A 0.0199 ADU (ratio 2.28e-3) | Simulator drops nearly all energy for this HKL despite target+reference agreement. |
  | ROI #1 Panel0 `[644:656,21:33]` | same | same | Reflection 8.12 ADU vs Stage A 5.78e-4 ADU (ratio 7.1e-5) | Confirms majority of ROIs sit ≪1% of reference. |
  | ROI #2 Panel0 `[257:269,37:49]` | same | same | Reflection 83.10 ADU vs Stage A 0.244 ADU (ratio 2.94e-3) | Even strong reflections collapse, pointing upstream of Stage A baseline logic. |
  | ROI #14 Panel0 `[431:443,434:446]` | same | same | Reflection 1.74 ADU vs Stage A 407.7 ADU (ratio 2.34e2) | Minority of reflections explode, suggesting we may be feeding intensity-like magnitudes where amplitudes are expected. |
  | ROI #19 Panel0 `[787:799,694:706]` | same | same | Reflection 192.88 ADU vs Stage A 11.80 ADU (ratio 6.12e-2, near 16× deficit) | Median behavior (0.061) matches deterministic parity crisis signature. |

- Boundary Bisection Step: Augment the probe with HKL amplitude lookups so each reflection row now includes `(reflection mean, target mean, Stage A mean, |F|^2/n_pixels)`; whichever pair aligns with the reflection-table reference reveals whether HKL ingestion or simulator execution causes the crisis.

How-To Map:
- Keep using the smoke fixture + refined MTZ resolved via `get_refgeom_dataload()` so HKL indices match DB-AT fixtures; reuse the `hkl_indices` / `hkl_amplitudes` already present on `mapping_context` rather than rebuilding grids.
- Convert `mapping_context.hkl_indices` to tuples of ints once (e.g., `tuple(map(int, ...))`) so dictionary lookups stay deterministic; bail if a Miller index from the reflection table is missing to avoid silently mixing assets.
- Recompute ratios with `np.isfinite` guards and store both sums and per-pixel means so downstream analyses can decide whether to compare energy or amplitude domains.
- Use the existing `AUTHORITATIVE_CMDS_DOC` + env var boilerplate when rerunning commands to keep artifacts admissible per docs/TESTING_GUIDE.md.
- Capture the new ledger in both JSON and console output; reference it from `summary.md` so the supervisor loop has decision-carrying evidence without re-running the probe.

Pitfalls:
- The reflection table stores bounding boxes without ROI padding; ensure matching logic still tolerates the +3 pixel expansion and reports mismatches explicitly.
- HKL lookup must respect Friedel mates — use the canonical index exactly as loaded from `mapping_context` to avoid reintroducing symmetry bugs.
- Do not mutate `mapping_context.hkl_amplitudes`; clone data before casting to numpy to avoid side effects in future runs.
- Guard for `n_masked_pixels == 0` before dividing; log and skip such ROIs rather than emitting NaNs into percentile stats.
- Keep artifact paths per-command aligned with the timestamp at the top of this file; stale env vars will derail later loops.

If Blocked:
- Capture the exception (e.g., ROI/HKL mismatch, missing reflection table, tensor conversion failure) in `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T210000Z/summary.md`, update `docs/fix_plan.md` Attempts History + `galph_memory.md` with the blocking condition, and only switch initiatives after logging whether a harness/spec-change ticket is required.
