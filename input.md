Summary: Capture apples-to-apples scale-chain metrics (raw vs calibrated vs refined HKL) so we know exactly where the metadata smoke mapping collapses before asking Ralph to touch Stage A physics.
Mode: none
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity; tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T170500Z/
Do Now:
- Implement: plans/active/TOOLING-VIS-001/bin/probe_scale_chain.py::main — add a T2 CLI (argparse `--cases`, `--out-dir`) that loads the metadata smoke dataload once and runs `build_mapping_stage_a_context`/`simulate_forward_once` for three permutations: (a) scaled.mtz with calibration disabled, (b) scaled.mtz plus config_torch_smoke.json calibration, (c) smoke_refined_structure_factors.mtz plus calibration. Emit a JSON summarizing ROI CC, masked/unmasked scale ratios, target/bragg mean ratios (raw+scaled), `spot_scale_override`, `sqrt_spot_scale`, `global_scale_hint`, HKL telemetry, and a diff block highlighting how each permutation diverges.
- Validate: `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` with the canonical metadata env (and a preceding `--collect-only` run) so the new telemetry lines up with the failing selectors.
How-To Map:
1. `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md REPORT=plans/active/TOOLING-VIS-001/reports/2025-11-25T170500Z DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_SIGMA_MAP_PATH=sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke.json DBEX_SMOKE_HKL_PATH=scaled.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1`.
2. `mkdir -p "$REPORT"/{scale_chain_probe,mapping_cpu_gpu_metadata,db_at_028,db_at_029}` and tee every command output into those subdirs.
3. Author `plans/active/TOOLING-VIS-001/bin/probe_scale_chain.py` with a `--cases scaled_raw,scaled_calibrated,refined_calibrated` (default order) and `--out-dir` flag; reuse `compare_mapping_forward_cpu_gpu.py` helpers for ROI correlations + scale ratios. Each case should tweak HKL/calibration inputs internally instead of mutating global env so runs stay identical apart from the intended knobs.
4. `python plans/active/TOOLING-VIS-001/bin/probe_scale_chain.py --cases scaled_raw,scaled_calibrated,refined_calibrated --out-dir "$REPORT"/scale_chain_probe --device cuda:0` (inherit env from step 1). Save stdout to `scale_chain_probe/probe.log`; the script should write a JSON (e.g., `scale_chain_metrics.json`) summarizing per-case metrics + diffs.
5. Re-run the existing parity probe for comparison: `python plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py --default-sigma 3.0 --out-dir "$REPORT"/mapping_cpu_gpu_metadata` and tee to `mapping_cpu_gpu_metadata/probe.log` so the new script’s numbers can be cross-checked against the established telemetry.
6. Export the DB-AT artifact env: `export DBAT028_ARTIFACT_DIR="$REPORT"/db_at_028 DBAT029_ARTIFACT_DIR="$REPORT"/db_at_029`.
7. Guardrail: `pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee "$REPORT"/pytest_db_at_028_029_collect.log` (fail the loop early if collection drops to 0).
8. `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee "$REPORT"/pytest_db_at_028_029.log` with the env from step 1/6 so logs, metrics, and mapping_context fixtures land under the new report tree even if the selectors continue to fail.
9. Summarize probe + pytest findings (spot_scale deltas, ROI CC deltas, failure signatures) in `$REPORT/summary.md` and update docs/fix_plan.md Attempts History referencing this timestamped directory.
Pitfalls To Avoid:
- Keep the probe script plan-local (under `plans/active/TOOLING-VIS-001/bin/`) and document args/results in `summary.md`; no production modules should import it.
- Do not mutate the calibration/config JSONs; the probe should treat calibration inputs as read-only and vary only the combinations we care about.
- Use the cropped metadata sigma tiles (`sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl`) so DB-AT-028/029 continue to run on the small-detector fixture; full-detector tiles will trip the strict shape guards.
- When running the refined case, point the probe at `sp.proc/calibration/smoke_refined_structure_factors.mtz`; forgetting to override HKL will silently duplicate the scaled.mtz run.
- Archive mapping_context_fixture.json, db_at_028_metrics.json, db_at_029_metrics.json even on failure per CONFORMANCE-001.
- Leave CUDA/CPU env identical between probe and pytest runs; switching devices mid-loop will make the scale-chain evidence incomparable.
If Blocked:
- If the new probe crashes (e.g., missing import or unexpected telemetry key), keep the traceback in `$REPORT/scale_chain_probe/probe_err.log`, note the failure in docs/fix_plan.md and galph_memory.md, and stop without modifying production code.
- If either DB-AT selector raises (not just fails assertions), capture the raw pytest log + partial metrics, mark the focus blocked in docs/fix_plan.md with the exact stack trace, and reach out before rerunning.
- If GPU resources are unavailable, fall back to `device=cpu` for the probe but record the device switch explicitly in summary.md and docs/fix_plan.md; do not mix CPU probe data with CUDA pytest artifacts without that note.
Findings Applied (Mandatory):
- STAGEA-001 — Share calibration/HKL provenance between mapping and Stage A when capturing diagnostics so evidence matches the intended zero point.
- SCALE-004 — Refined structure factors must be paired with the same calibration metadata; the probe needs to show how that pairing affects spot_scale vs ROI CC.
- POLICY-001 — Environment is frozen; rely on repo-provided scripts/deps only and store all outputs under the timestamped report directory.
- CONFORMANCE-001 — DB-AT selectors must emit full artifact sets (metrics JSONs, mapping fixtures, pytest logs) even when they fail.
- TESTING-003 — Keep explicit collect-only + execution logs for the mapped selectors so we can prove coverage didn’t silently drop.
Pointers:
- docs/data_dependency_manifest.md:80 (refined MTZ + calibration asset contract and default overrides for smoke fixtures).
- docs/TESTING_GUIDE.md:136 (DB-AT-028/029 canonical env/tolerances and artifact expectations).
- dbex/vis/mapping.py:95 (build_mapping_stage_a_context plumbing of HKL + calibration fields the probe should reuse).
- plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py:90 (existing ROI correlation/scale-ratio telemetry pattern to mirror in the new probe).
- plans/active/TOOLING-VIS-001/implementation.md:200 (Phase D diagnostic goals + context for why we’re collecting these metrics).
Next Up (optional):
- If the scale-chain probe shows a single stage applying sqrt(spot_scale) twice, prepare a focused Do Now to patch `simulate_forward_once`/Stage A telemetry to remove the duplicate application before rerunning DB-AT-028/029.
