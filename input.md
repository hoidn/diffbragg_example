Summary: Add mapping-parity diagnostics to the Stage A baseline probe so we can prove whether the cached zero-iteration Bragg stack matches the DB-AT-024 mapping reference before re-running DB-AT-028/029.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors_small.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --device cuda:0 --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-16T200000Z/stage_a_baseline_probe.json
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-16T200000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-16T200000Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-16T200000Z/pytest_db_at_028_029.log
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-16T200000Z/

Do Now:
- Implement: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py` — reuse `mapping_context.bragg_zero_iter` to compute Stage A vs mapping parity metrics (masked/unmasked means, per-ROI Pearson CC, RMSE, max|Δ|, chi²/pixel vs target). Emit a new `mapping_comparison` JSON section and console summary so DB-AT-027 compliance can be audited.
- Implement: add provenance fields (resolved HKL/calibration paths) and warn when Stage A vs mapping ROI correlations fall below 0.99 or max|Δ| exceeds 1 ADU. Persist the ROI percentile stats to `mapping_comparison.json` for later analysis.
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors_small.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --device cuda:0 --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-16T200000Z/stage_a_baseline_probe.json`.
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-16T200000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-16T200000Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-16T200000Z/pytest_db_at_028_029.log`.

How-To Map:
1. Inside `compare_stage_a_baseline.py`, keep the existing Stage A telemetry comparison, but cache `mapping_context.bragg_zero_iter` so you can compute Stage A vs mapping residuals before any loss computation.
2. Add helper utilities to slice ROIs (reuse `refinement_inputs.panel_slices`) and compute per-ROI correlations between Stage A vs mapping vs target; summarize median/percentiles in the JSON payload.
3. Extend the CLI output and JSON schema with a `mapping_comparison` block containing max|Δ|, RMSE, masked mean ratios, ROI CC statistics, and chi²/pixel for both Stage A and mapping relative to the target.
4. When the script runs, ensure it honours `DBEX_SMOKE_CALIB_PATH`/`DBEX_SMOKE_HKL_PATH` so both Stage A and mapping use the refined small-detector assets listed in `docs/data_dependency_manifest.md`.
5. After regenerating the probe JSON, rerun DB-AT-028/029 with the new artifact directory so the same evidence bundle captures both the parity diagnostics and the end-to-end acceptance failure.

Pitfalls To Avoid:
- Do not mutate the cached Stage A tensor in place when computing Stage A vs mapping diffs—always operate on detached copies to keep the cache reusable.
- ROI correlations should ignore masked-out pixels; reuse the loss mask so Stage A vs mapping comparisons match the acceptance path.
- When mapping and Stage A already match within numerical noise, ensure the script still emits the comparison block (do not short-circuit to avoid “missing evidence”).
- Keep console output concise—deploy warnings only when thresholds are violated so future runs remain scannable.
- Use the new artifact path for all outputs so docs/fix_plan.md and plan history can reference a single timestamp.

If Blocked:
- If `build_mapping_stage_a_context` fails (missing refined MTZ, calibration, etc.), capture the stack trace, note the missing dependency in `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-16T200000Z/summary.md`, and fall back to the existing probe behavior so we retain partial evidence.
- If ROI correlation computations exceed memory/time limits, log the failure, persist whatever stats you captured, and flag the block in docs/fix_plan.md so Galph can rescope (do NOT silently drop the comparison block).

Findings Applied (Mandatory):
- SCALE-008 — Stage A warm-cache artifacts must remain authoritative, so our parity probe needs to prove cached zero-iteration tensors match the mapping simulator.
- SCALE-009 — Reconstruction parity depends on replaying Stage A’s calibrated intensity, and these diagnostics confirm whether both paths stay aligned before chasing DB-AT thresholds.

Pointers:
- plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py (extend probe with mapping metrics)
- dbex/vis/mapping.py (MappingStageAContext semantics)
- plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-16T010000Z/db_at_028/db_at_028_metrics.json (current failure signature: chi²/pixel 2.097e5, ROI CC -0.053)
- docs/spec-db-conformance.md (§§319–366 DB-AT-028/029, DB-AT-027 parity requirements)
- docs/data_dependency_manifest.md (Stage A smoke HKL/calibration provenance)
