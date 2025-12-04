Summary: Add a `--stage-a-mosaic-domains` knob to the baseline probe and run a 1-domain vs 16-domain sweep so we can prove whether the new RefinementConfig field changes Stage A↔reflection ratios before escalating to a nanobrag_torch patch.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T010000Z/db_at_028 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T010000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T010000Z/

Do Now (hard validity contract):
- Implement: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py::main`
  - Add `--stage-a-mosaic-domains` (int, default current config value) that threads directly into `RefinementConfig` and gets clamped to ≥1 before hitting `create_crystal_config`.
  - Record the applied domain count, Stage A/Ref median ratio, and geometry mode inside `probe_metadata` + console output so the sweep artifacts are traceable without re-running the probe.
  - After editing, run the Stage A baseline probe twice using identical inputs except for the domain count:
    * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors_small.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode baseline --stage-a-mosaic-domains 1 --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T010000Z/domain1/stage_a_baseline_probe_baseline.json`
    * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors_small.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --geometry-mode baseline --stage-a-mosaic-domains 16 --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T010000Z/domain16/stage_a_baseline_probe_baseline.json`
  - Summarize the sweep (Stage A/Ref medians from each JSON) in `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T010000Z/mosaic_domain_sweep.md` so the parity evidence is decision-carrying.
- Pytest: Run the mapped DB-AT selectors with `DBAT0XX_ARTIFACT_DIR` pointing at the new report directory so chi²/pixel and ROI correlations are captured alongside the sweep evidence.
- Artifacts: Keep all logs/JSON/pytest output under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T010000Z/` (use `domain1/`, `domain16/`, `db_at_028/`, `db_at_029/` subfolders) so the ledger and boundary plan cite a single tree.

Deterministic Parity Crisis:
- Independent Reference: `sp.proc/refGeom_small/refGeom_small.refl` reflection table — independent measurement whose median target/reference ratio is 1.02 (see `stage_a_baseline_probe_baseline.json`), so it remains the external contract for ROI-scale intensity.
- Transformation Ledger: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T010000Z/transformation_ledger.md` lists five representative ROIs where Stage A deviates 0.002×–234× from the reference while Target/Ref stays ≈1.0, proving the simulator redistributes energy before reconstruction. Example: ROI 14 HKL (0,2,-2) Stage A 407.7 ADU vs reference 1.74 ADU (233×) even though |F|² per pixel is only 39 ADU.
- Boundary Bisection Step: Execute the planned mosaic-domain sweep (domain=1 vs 16) described in `boundary_bisection.md`. If the Stage A/Ref medians remain ≈0.061 for both runs, escalate to a nanobrag_torch instrumentation patch (Environment Freeze exception path). If they diverge materially, continue investigating domain count and distribution before touching nanobrag_torch.

How-To Map:
- Use Git-aware editor (or `python -m compileall` guard) to update the probe script; avoid touching production stages this loop.
- Run the two probe commands above exactly once each, teeing stdout to `domain*/baseline_probe.log` if you need console context.
- Convert the JSON stats into `mosaic_domain_sweep.md` by copying `reflection_comparison.reflection_stats.stagea_vs_ref` medians plus HKL stats so reviewers can read the comparison quickly.
- Execute the two mapped pytest nodes with the env vars shown; include `| tee plans/.../pytest_db_at_028_029.log` if you need combined output, but the priority is storing `db_at_028/db_at_029` metrics JSONs.
- After commands complete, run `python - <<'PY' ...` or `jq` as needed to pull medians, but keep the scripted excerpts inside the sweep markdown for traceability.

Pitfalls:
- Forgetting `DBAT028_ARTIFACT_DIR`/`DBAT029_ARTIFACT_DIR` causes pytest to skip the selectors; always point them to the new report subdirs.
- `--stage-a-mosaic-domains` must clamp to ≥1; passing 0 or negatives will crash nanobrag_torch when it allocates rotation tensors.
- Use identical calibration + MTZ paths for both probe runs; changing inputs invalidates the sweep comparison.
- Do not touch `nanobrag_torch` yet—Environment Freeze requires the sweep evidence before patching vendored code.
- Keep geometry mode at `baseline` for both runs; perturbations mask the effect we are isolating.
- Remember that higher domain counts increase GPU memory; monitor usage and fail fast if CUDA OOM occurs.
- Capture all stdout/stderr under the report tree; missing logs make the ledger non-auditable.
- Ensure the probe still emits HKL stats after your edit; accidental regression there removes our safety net.
- Do not rerun DB-AT repeatedly—one post-sweep run is enough to confirm the failure signature.
- Refrain from editing production Stage A/B/C files in this loop unless the probe change forces it; scope is diagnostics only.

If Blocked:
- If the probe cannot run (CUDA OOM, missing data, CLI regression), capture the exact command + traceback in `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T010000Z/summary.md`, update `docs/fix_plan.md` Attempts History and `galph_memory.md` with the blocker, and flag whether it requires a nanobrag_torch patch or new data before scheduling another loop.
