Summary: Extend the Stage A baseline probe with reflection-table cross-checks so we can tell whether DB-AT-028/029’s 9.8e5 chi²/pixel failure comes from the simulator or from ROI preparation before scheduling the next production fix.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors_small.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode baseline --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T010000Z/stage_a_baseline_probe_baseline.json
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors_small.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode perturbed --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T010000Z/stage_a_baseline_probe_perturbed.json
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T010000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T010000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T010000Z/pytest_db_at_028_029.log
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T010000Z/

Do Now:
- Implement: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py::main` — import `dials.array_family.flex`, load `refgeom_dataload.Refs`, and align each reflection with the corresponding ROI (`panel_slices`/`pids`). For every ROI compute and persist the independent DIALS intensities (`intensity.sum.value`, `background.sum.value`, pixel count) plus derived per-pixel means so we can compare Stage A/mapping/target against the reflection-table source of truth.
- Extend the ROI diagnostics and console summary to include the new reflection metrics (top/bottom entries, percentile stats, median ratios) and emit a `reflection_comparison` block in the JSON. Guard for mismatched ROI counts or NaNs so the probe fails loudly if the reflection table diverges from the ROI ordering.
- Re-run the baseline + perturbed probe commands and DB-AT-028/029 selector listed above so the new artifacts under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-20T010000Z/` capture reflection-aware evidence alongside the chi²/ROI traces.

Deterministic Parity Crisis:
- Independent Reference: DIALS reflection table intensities from `sp.proc/refGeom_small/refGeom_small.refl` (`intensity.sum.value`, `background.sum.value`) per docs/data_dependency_manifest.md — these per-ROI photon sums are independent of the nanobrag_torch simulator and let us decide whether the Stage A vs target mismatch comes from the simulator or from ROI preparation.
- Transformation Ledger:

  | Field | Units / Frame | Producer (file:line) | Consumer (file:line) | Evidence | Hypothesis |
  | --- | --- | --- | --- | --- | --- |
  | `telemetry.target_mean_masked` | ADU over Stage A loss mask | `dbex/refinement/stage_a.py:410` | `tests/dbex/test_stage_a_smoke_parity.py:233` | `stage_a_baseline_probe_baseline.json` (2025-12-19T010000Z) shows 87.1184 ADU | Target masked mean equals telemetry, so global scale is correct |
  | `telemetry.model_mean_masked` | ADU over Stage A loss mask | `dbex/refinement/stage_a.py:430` | `dbex/refinement/reconstruction.py:557` | Same JSON shows ratio 1.000000087 | Baseline alignment succeeded; mismatch is not scale |
  | `mapping_context.bragg_zero_iter` | ADU per pixel, detector frame order `[panel, slow, fast]` | `dbex/vis/mapping.py:221-303` | `dbex/refinement/stage_a.py:334` & DB-AT fixtures | `stage_a_baseline_probe_baseline.json` reports `stagea_vs_mapping_max_abs_diff=3.9e-03 ADU` | Stage A warm cache matches mapping baseline (DB-AT-027 PASS) |
  | `chi2_per_pixel_initial` | dimensionless per-masked pixel | `tests/dbex/test_stage_a_smoke_parity.py:269` | Spec gate `docs/spec-db-conformance.md:280-318` | `db_at_028/db_at_028_metrics.json` (2025-12-19T010000Z) = 2.097×10⁵ | Deterministic parity crisis signature (>10³ over spec) persists |
  | `roi_diagnostics.stagea_vs_target_cc` | Pearson CC per ROI (panel frame) | `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:429-604` | Galph parity localization + DB-AT interpretability | Probe shows median -0.0373, worst ROI Stage A mean 1.6×10³ ADU vs target 6.9 ADU | Stage A concentrates intensity into few ROIs; need reflection-table reference to see whether simulator or ROI prep drifts |

- Boundary Bisection Step: Compare each ROI’s Stage A/mapping/target means against the independent reflection-table intensities; whichever side matches the reflection data becomes the trusted producer for the next production fix (either simulator scaling or ROI prep).

How-To Map:
- Use `flex.reflection_table` APIs to pull `intensity.sum.value` / `background.sum.value`; convert to numpy arrays once and cache so ROI iteration stays deterministic.
- Assert the reflection-table row count equals `len(refinement_inputs.panel_slices)` before zipping to avoid silent misalignment; include panel/bbox IDs in any error.
- Record the resolved MTZ/Calib paths (already in `probe_metadata`) and add reflection-table provenance (`refGeom_small.refl`) in the new block for traceability.
- When computing ratios, use masked-pixel counts (`n_masked_pixels`) to turn sums into comparable means; persist both sum and per-pixel metrics so later loops can cite whichever matches the reference.
- Rerun commands exactly as listed under Mapped tests (including `AUTHORITATIVE_CMDS_DOC`) so the harness captures context and the new reflection-aware JSON/summary share the same artifacts directory as the pytest logs.

Pitfalls:
- Do not mutate `refgeom_dataload.Refs`; copy data into numpy arrays so the DataLoad cache stays immutable for other probes.
- Guard against NaNs/infinite ratios when a ROI has zero masked pixels; skip those entries instead of skewing statistics.
- Keep the new JSON additions bounded (top/bottom-N lists + percentile stats) to avoid exploding artifact size; raw per-ROI tensors still live in existing diagnostics.
- Ensure the reflection-table ordering matches ROI ordering — if counts diverge, fail fast and document it rather than guessing.
- Respect Environment Freeze: all new logic lives in the plan-side probe, not in nanobrag_torch or external dependencies.
- When rerunning pytest, tee output to the logged file even on failure so we retain exact traces for follow-up analysis.

If Blocked:
- Capture the failure signature (stack traces, mismatched counts, device unavailability) in `summary.md`, stash whatever artifacts exist, and update `docs/fix_plan.md` + `galph_memory.md` with the blocking detail before switching focus or requesting a harness/spec-change initiative.
