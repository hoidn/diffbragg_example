Summary: Capture per-ROI mapping diagnostics on the metadata-sigma smoke dataset so we can see whether Stage A’s negative ROI correlations stem from geometric misregistration or structural mismatch before touching physics.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T073500Z/

Do Now
- Implement: plans/active/TOOLING-VIS-001/bin/probe_mapping_roi_triptychs.py::main — new T2 probe that loads the metadata-sigma smoke dataset (respecting DBEX_SMOKE_* env + optional --mtz-path), computes per-ROI correlation/MSE/scale stats, and writes `roi_metrics.json` plus the `N` lowest-correlation ROIs as PNG/NPZ triptychs using `dbex.vis.triptych`; include histogram data so we can inspect failure modes without editing production modules.
- Validate: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T073500Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T073500Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k \"DB_AT_028 or DB_AT_029\" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T073500Z/pytest_db_at_028_029.log`

How-To Map
1) Author the probe with the standard T2 header, argparse for `--out-dir`, `--roi-count`, `--device`, and `--mtz-path`, reuse `build_mapping_stage_a_context` + `dbex.vis.triptych.plot_triptych` to render the lowest-correlation ROIs, and emit `roi_metrics.json` (sorted list) plus `roi_histogram.json` (bin counts) under `plans/active/TOOLING-VIS-001/reports/2025-11-25T073500Z/roi_diagnostics/`.
2) Run the probe with metadata sigma:  
   `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small python plans/active/TOOLING-VIS-001/bin/probe_mapping_roi_triptychs.py --roi-count 16 --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T073500Z/roi_diagnostics | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T073500Z/roi_diagnostics/probe.log`
3) Rerun DB-AT-028/029 with metadata sigma (nearest-neighbor HKL) using the command in Do Now; export collect-only if needed when selectors change, but current scope is execution only.
4) Summarize probe + pytest signatures in `plans/active/TOOLING-VIS-001/reports/2025-11-25T073500Z/summary.md`, highlighting any geometric/structural pattern spotted in the ROI triptychs.

Pitfalls To Avoid
- No production code edits; keep work inside plans/active tooling and tests' artifact fields.
- Metadata sigma assets live under `sp.proc/idx-0000_sigma_metadata.*`; bail out early if missing rather than switching datasets.
- Keep ROI samples bounded (`--roi-count` ≤ 24) so artifacts stay small and deterministic.
- Respect sigma ladder + nearest-neighbor HKL (no interpolation/halo) to stay aligned with DB-AT-028/029 specs.
- Always persist db_at metrics before pytest assertions so failures still leave breadcrumbs.
- Torch compile stays disabled; avoid CUDA warmups that mutate the environment.
- Do not relax DB-AT tolerances even if ROI diagnostics look hopeless; we’re gathering evidence.

If Blocked
- Archive whatever the probe produced (or the exception trace) plus pytest logs in the artifacts dir, note the failure mode in summary.md and docs/fix_plan.md Attempts History, and mark the focus blocked only after capturing the error signature and ROI stats path.

Findings Applied (Mandatory)
- STAGEA-001 — Mapping-aligned calibration must be logged alongside any new diagnostics so we can root-cause Stage A divergence later.
- GEOMETRY-003 / GEOMETRY-004 — ROI probes need to reuse the existing MappingStageAContext inputs so the incremental UB zero-point invariant stays intact.
- CONVERGENCE-001 — Diagnostics must not bypass the mapping zero-point check; zero-parameter forward matches mapping geometry before we inspect ROIs.
- PHYSICS-LOSS-001 — Variance-weighted chi² and loss_mask pixel counts are the reference; ROI stats should quote masked values only.
- POLICY-001 — Environment Freeze: only use locally available deps/scripts; no installs or external data pulls.

Pointers
- docs/spec-db-conformance.md:280-366 — DB-AT-028/029 tolerances and ROI definitions.
- docs/spec-db-vis.md §2 — Triptych layout + residual definitions for the new ROI artifacts.
- docs/TESTING_GUIDE.md:130-190 — Canonical DB-AT-028/029 commands, env vars, artifact requirements.
- tests/dbex/test_stage_a_smoke_parity.py:200-360 — Stage A smoke fixture (for wiring ROI stats references).
- plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py — reference for DataLoad/env plumbing and diagnostics style.

Next Up (optional)
- If ROI triptychs reveal systematic ROI misregistration, follow up with a geometry delta probe comparing mapping ROI boxes vs raw reflections before modifying Stage A physics.

Doc Sync Plan (Conditional)
- None yet; if new ROI diagnostics promote to a selector/regression guard, run `pytest --collect-only` for the affected node and update docs/TESTING_GUIDE.md + docs/development/TEST_SUITE_INDEX.md after the code passes.

Mapped Tests Guardrail
- Ensure `pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` reports both selectors (>0). Treat zero collection as a blocker before touching diagnostics.

Hard Gate
- Do not close the loop without `roi_diagnostics/roi_metrics.json`, the PNG/NPZ samples, db_at_028/db_at_029 metrics (even if failing), and the pytest log under the artifacts path even if failures persist.

Normative Math/Physics
- Reference docs/spec-db-core.md §82-92 for variance/ROI correlation math in the probe; do not paraphrase equations or relax tolerances without spec approval.
