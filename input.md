Summary: Capture ROI-level Stage A vs target diagnostics and re-run DB-AT-028/029 so we can see whether the C.14 baseline fix resolved the chi²/ROI regressions or if specific ROIs remain out-of-tolerance.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors_small.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode baseline --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-19T010000Z/stage_a_baseline_probe_baseline.json
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors_small.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode perturbed --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-19T010000Z/stage_a_baseline_probe_perturbed.json
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-19T010000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-19T010000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-19T010000Z/pytest_db_at_028_029.log
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-19T010000Z/

Do Now:
- Implement: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py::main` — extend the probe so each run records detailed ROI diagnostics (top/bottom-N ROIs with panel+bbox IDs, percentile/median stats, masked mean deltas) for Stage A↔target in addition to the existing mapping parity data. Emit the new block in the JSON and log it in the console summary so DB-AT evidence immediately shows which ROIs drive failures.
- Run the enhanced probe twice (baseline & perturbed geometry modes) with the mapped commands above, storing JSON + logs under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-19T010000Z/`.
- Re-run the DB-AT-028/029 selector with the same fixtures/env overrides so we capture fresh chi²/ROI metrics after the C.14 fix. Archive `pytest_db_at_028_029.log`, updated `db_at_028/db_at_029` metric JSONs, and a `summary.md` that cites the new ROI diagnostics and calls out whether chi²/median CC improved.

How-To Map:
1. When updating the probe, compute ROI correlations using the existing `_roi_correlations` helper and sort them so you can emit both the percentile summary (min/p25/median/p75/max) and a small list of the worst/best ROIs (include `(panel, bbox)` so we can map back to raw images without dumping every ROI).
2. Include masked mean deltas per ROI so we can tell whether failures are due to scale or structure; storing only a handful of representative entries keeps JSON manageable.
3. Use the same env overrides for both probe invocations so geometry/HKL inputs exactly match what DB-AT uses; record the resolved MTZ/calibration paths in `probe_metadata` to satisfy SCALE-008 provenance requirements.
4. After running pytest, drop the resulting metrics and the new probe outputs into `summary.md` with a short narrative (e.g., “top 3 failing ROIs remain negative, chi² unchanged”) so the next planning loop can decide whether to pursue spec-change vs implementation work.
5. Keep `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md` on every command so harness tooling captures the run context.

Pitfalls To Avoid:
- Limit ROI dumps to a fixed small number (e.g., top/bottom 5) so JSON stays reviewable; do not serialize all ROI tensors.
- Ensure both geometry modes use the same HKL/calibration assets or clearly annotate any divergence, otherwise we cannot compare baseline vs perturbed evidence.
- Keep the probe deterministic (set device from env, avoid random ROI sampling) so future runs can diff JSON cleanly.
- Respect the Environment Freeze—instrumentation lives under `plans/active/.../bin/`, not in nanobrag_torch or external deps.
- When rerunning DB-AT-028/029, tee output into the artifact log so we have the exact pytest trace even if it fails again.

If Blocked:
- If the probe crashes because metadata is missing (e.g., loss mask not present), capture the failure signature in `summary.md`, stash whatever artifacts exist, and update docs/fix_plan.md with the missing hook rather than guessing.
- If GPU resources are unavailable, rerun everything on CPU (set `DBEX_SMOKE_DEVICE=cpu` or override `--device cpu`) and annotate the summary/log filenames with the device so we know why runtimes changed.

Findings Applied (Mandatory):
- SCALE-008 — Stage A warm-cache telemetry is authoritative; ROI diagnostics must quote telemetry-derived baselines before interpreting data.
- SCALE-009 — Reconstruction/mapping helpers must stay in lockstep with Stage A scaling; the new probe outputs demonstrate whether chi²/corr failures stem from post-scaling behavior or underlying physics.

Pointers:
- plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py: add ROI analytics where the existing mapping parity summary lives (≈lines 380-560).
- tests/dbex/test_stage_a_smoke_parity.py: DB-AT-028/029 harness producing the metrics you’ll refresh.
- plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-18T010000Z/summary.md and stage_a_baseline_probe_baseline.json: reference outputs from the C.14 loop so you can extend them consistently.
