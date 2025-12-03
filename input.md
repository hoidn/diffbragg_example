Summary: Reuse StageAArtifacts so reconstruction sees the warmed Stage A context and cached final Bragg before rerunning the DB-AT selectors.
Mode: Parity
InitiativeType: architecture
Focus: ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment
Branch: integration
Mapped tests: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/

Do Now:
- Implement: tests/dbex/test_stage_a_smoke_parity.py::stage_a_smoke_result — after `engine.run(...)`, fetch the Stage A artifact from `getattr(engine, "_artifacts", {}).get("stage_a")`, derive `stage_a_ctx` and any cached `bragg_full`, and pass that context into both `build_final_bragg_from_stage_a_telemetry` calls. Prefer the cached `bragg_full` for the "final" stack when available and keep the existing cold-path reconstruction as a fallback when artifacts are absent.
- Implement: plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py::main — mirror the artifact lookup logic so the probe hands the warmed `StageAContext` to `build_final_bragg_from_stage_a_telemetry` for both `param_state="initial"` and `"final"`, and reuse the cached `bragg_full` when Stage A is terminal. Guard the new path so legacy engines without `_artifacts` still execute via the cold factory path.
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/stage_a_baseline_probe.json
- Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/pytest_db_at_028_029.log

How-To Map:
1. Apply the StageAArtifacts wiring to both files, ensuring `stage_a_ctx` and cached `bragg_full` are pulled from `engine._artifacts.get("stage_a")` with defensive fallbacks when `_artifacts` is missing.
2. Run the baseline probe command above (the script auto-selects CUDA when available; override `--device cpu` if GPUs are unavailable) so the refreshed JSON shows matching telemetry/reconstruction masked means.
3. Execute the DB-AT selector command with the updated artifact directories so the new `baseline_stats.json`, mapping diagnostics, and pytest log land under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/`.
4. Inspect `*_baseline_stats.json` to confirm the `bragg_vs_telem_model` ratio is ~1.0 before uploading artifacts.

Pitfalls To Avoid:
- Do not resurrect the deleted `_stage_contexts` cache; the StageAArtifacts entry in `_artifacts` is the canonical source for warmed contexts.
- Keep the new code tolerant when `_artifacts` is absent (older engines) so tests still run in cold mode instead of crashing.
- Respect Environment Freeze: no package installs or nanobrag_torch edits are allowed for this loop.
- Preserve device/dtype neutrality when passing StageAContext into the helper; avoid forcing CPU copies that would break CUDA runs.
- Do not drop existing instrumentation (`baseline_stats.json`, mask coverage logs); wire the new context path alongside the logging.
- Leave Stage A physics untouched—this change only controls which simulators reconstruction uses.

If Blocked:
- If `_artifacts` is missing or lacks StageAArtifacts, leave a short note in `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/summary.md`, keep the old cold path in place, and stop rather than inventing new caches; report the absence so we can revisit engine plumbing next loop.

Findings Applied:
- SCALE-009 — Reconstruction helpers must follow the same post-run scaling convention and reuse the warmed simulator state whenever possible; pulling `stage_a_ctx` from StageAArtifacts is required to stay aligned with Stage A telemetry.
- SCALE-008 — When calibration metadata enables N_cells, the warmed StageAContext already carries the correct gating; reusing it prevents cold-path simulators from silently disabling the gate.

Pointers:
- tests/dbex/test_stage_a_smoke_parity.py:120-220 (Stage A fixture to patch)
- plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:240-380
- docs/fix_plan.md:133 (ARCH-SIM-CONSTRUCTION-001 entry + latest attempts)
- plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md: Phase C.9 checklist

Next Up (optional): Once warm-cache reconstruction matches telemetry, revisit Stage A scale telemetry vs DB-AT gates to decide whether a spec-change or additional calibration fix is needed.
