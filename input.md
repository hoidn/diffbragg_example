Summary: Parameterize the Stage A baseline probe with a zero-perturbation geometry mode so mapping-parity diagnostics stop flagging expected differences from the smoke perturbation and rerun the evidence bundle for DB-AT-028/029.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors_small.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode baseline --device cuda:0 --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-17T010000Z/stage_a_baseline_probe_baseline.json
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-17T010000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-17T010000Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-17T010000Z/pytest_db_at_028_029.log
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-17T010000Z/

Do Now:
- Implement: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py::main` — add a `--geometry-mode {perturbed,baseline}` flag (default `perturbed`) that skips `create_perturbed_geometry` and uses the mapping baseline crystal/detector/beam when `baseline` is selected. Record the chosen mode in `probe_metadata` so evidence consumers know which geometry was used.
- Implement: thread the geometry mode through the console summary/JSON payload (e.g., `"geometry_mode": "baseline"`) and guard the mapping-parity warnings so they only fire when the mode is `baseline`. When the mode is `perturbed`, still emit the comparison block but tag it as non-normative so we can distinguish deliberate perturbations from true DB-AT-027 violations.
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors_small.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode baseline --device cuda:0 --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-17T010000Z/stage_a_baseline_probe_baseline.json` (expect Stage A vs mapping metrics to drop to numerical-noise levels when geometry is unperturbed).
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-17T010000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-17T010000Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-17T010000Z/pytest_db_at_028_029.log` (collect the failure signature with the updated parity evidence).

How-To Map:
1. Extend the argparse definition with `--geometry-mode` (choices `perturbed`/`baseline`) and plumb the setting into the geometry preparation section before calling `build_refinement_context`.
2. When `geometry_mode == "baseline"`, pass `baseline_crystal`, `baseline_detector`, and `baseline_beam` directly to the refinement context; otherwise keep using the existing `create_perturbed_geometry` path for the Stage A smoke scenario.
3. Attach the geometry mode and resolved HKL/calibration paths to the JSON metadata so downstream reports can cite exactly which configuration was probed. Update the console summary to print a clear header (e.g., "[Stage A Baseline Probe] Geometry mode: baseline").
4. Re-run the probe with `--geometry-mode baseline` and stash the JSON + stdout logs under the new report directory so we can prove Stage A vs mapping parity with zero deltas.
5. After regenerating evidence, rerun DB-AT-028/029 with artifact dirs rooted at the same timestamp to keep the chi²/ROI metrics aligned with the corrected probe data.

Pitfalls To Avoid:
- Do not mutate the `RefinementConfig` when switching geometry modes—only swap the detector/beam/crystal objects you pass into `build_refinement_context`.
- Keep the default `perturbed` behavior intact so Stage A smoke tests still exercise the intended perturbation when desired.
- When geometry mode is `baseline`, ensure the cached Stage A tensors are detached copies so reusing mapping artifacts does not trample the warm cache state.
- Always honour `DBEX_SMOKE_CALIB_PATH`/`DBEX_SMOKE_HKL_PATH` so the mapping and Stage A paths stay on the same refined assets.
- Capture stdout via `tee` when running pytest so the artifact directory contains both the logs and metrics JSON for later analysis.

If Blocked:
- If the baseline geometry mode still reports large Stage A vs mapping deltas, capture the JSON + console logs, mark the block in docs/fix_plan.md, and pause before attempting additional fixes so Galph can reassess whether Stage A zero-point code diverged.
- If CUDA is unavailable, rerun the probe and tests on CPU with `--device cpu`, record the variance in the artifacts, and note the device change in the report so we can compare apples-to-apples later.

Findings Applied (Mandatory):
- SCALE-008 — Warm-cache artifacts are considered authoritative; ensuring the probe can run with zero perturbation verifies we are comparing the same baseline geometry before interpreting chi² metrics.
- SCALE-009 — Reconstruction relies on Stage A telemetry for calibrated intensity, so correcting the probe avoids false positives when evaluating the simulator construction path.

Pointers:
- plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:35-220 (geometry prep + telemetry capture to update)
- docs/spec-db-conformance.md:319-389 (DB-AT-027/028/029 parity gates driving this evidence collection)
- plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-16T200000Z/stage_a_baseline_probe.json (shows the false positive caused by perturbed geometry)
- docs/data_dependency_manifest.md:88-133 (canonical Stage A smoke assets referenced in the probe)
