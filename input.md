Summary: Make the Stage A smoke fixture (and mapping probes) default to the refined smoke MTZ whenever the calibration bundle exists and capture telemetry proving the new HKL path is used.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity; tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T203500Z/

Do Now:
- Implement: tests/dbex/test_torch_refine_smoke.py::refgeom_dataload — when `sp.proc/calibration/config_torch_smoke.json` (or DBEX_SMOKE_CALIB_PATH) resolves and `DBEX_SMOKE_HKL_PATH` is unset, default `hkl_source_path` to `sp.proc/calibration/smoke_refined_structure_factors.mtz`, persist the resolved path/source on the fixture so mapping contexts inherit it, and keep the explicit override/relative-path behavior unchanged.
- Implement: dbex/vis/mapping.py::build_mapping_stage_a_context — mirror the nested `diagnostics["hkl_telemetry"]` entries onto top-level `hkl_source`/`hkl_path` keys (without mutating the telemetry payload) so Stage A smoke diagnostics and DB-AT selectors read the actual HKL asset even when callers still reference the old keys; update any TOOLING probes that cached their own HKL resolver (e.g., `plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py::build_dataload_for_case`) to reuse the same fallback so CLI runs match the fixture.
- Validate: `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` with the canonical metadata env so both selectors archive telemetry showing the refined HKL path (assertions expected to fail but logs must capture the new provenance).

How-To Map:
1. `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md REPORT=plans/active/TOOLING-VIS-001/reports/2025-11-25T203500Z DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_SIGMA_MAP_PATH=sp.proc/refGeom_small/idx-0000_sigma_metadata_small.sigma_tiles.pkl DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke.json KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1` and `mkdir -p "$REPORT"/mapping_dataset_metrics "$REPORT"/db_at_028 "$REPORT"/db_at_029`.
2. Update `tests/dbex/test_torch_refine_smoke.py::refgeom_dataload` so the default HKL resolver is: (a) honor `DBEX_SMOKE_HKL_PATH` when set, (b) else if `sp.proc/calibration/smoke_refined_structure_factors.mtz` exists and a calibration config resolved, use that refined file, (c) otherwise fall back to `scaled.mtz`. Persist the resolved path on `args.hkl_source_path` and add a `resolved_hkl_source` string to the diagnostics payload if it does not exist yet.
3. Update `dbex/vis/mapping.py::build_mapping_stage_a_context` (and any helper your change touches) to copy `hkl_source/hkl_path` from `hkl_telemetry` into the top-level `diagnostics` dict before returning the context. Confirm `MappingStageAContext.diagnostics` now surfaces the accurate HKL metadata without relying on test-only logic.
4. Mirror the new resolver inside tooling scripts that hand-roll DataLoad args (at minimum `plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py::build_dataload_for_case` and `plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py::main`) so probes see the same refined default as the pytest fixture.
5. With the canonical metadata env (`DBEX_SMOKE_HKL_PATH` intentionally *unset* so the new default takes effect), run `python plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py --cases metadata_raw metadata_calibrated --emit-roi-artifacts --roi-count 16 --default-sigma 3.0 --device cuda:0 --out-dir "$REPORT"/mapping_dataset_metrics | tee "$REPORT"/mapping_dataset_metrics/probe.log` and confirm `mapping_dataset_metrics.json` records `hkl_source="refined"` plus the refined path for both cases.
6. `export DBAT028_ARTIFACT_DIR="$REPORT"/db_at_028 DBAT029_ARTIFACT_DIR="$REPORT"/db_at_029` then `pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee "$REPORT"/pytest_db_at_028_029_collect.log` to prove the selectors still collect.
7. `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee "$REPORT"/pytest_db_at_028_029.log`; let the assertions fail but verify the emitted `mapping_context_fixture.json` files now list `hkl_source="refined"` and `hkl_path` pointing at `sp.proc/calibration/smoke_refined_structure_factors.mtz`.

Pitfalls To Avoid:
- Keep `DBEX_SMOKE_HKL_PATH` overrides authoritative; do not ignore it when present.
- Do not bake absolute paths into the fixture—resolve relative paths via repo root so CI and local runs behave identically.
- Avoid mutating the contents of `hkl_telemetry`; add mirrored keys instead so downstream consumers that already reference the nested dict keep working.
- Ensure tooling scripts and pytest fixtures share the same resolver to prevent the “probe uses refined, test uses raw” split we just diagnosed.
- Preserve lazy imports and torch device neutrality inside the mapping helper; no CUDA-only shortcuts.
- Capture probe/pytest logs even when tests fail; artifacts are mandatory evidence for this initiative.
- Leave environment freeze intact—no pip installs or package upgrades to chase missing deps.
- Refrain from updating unrelated fixtures/tests; limit the change to HKL selection + diagnostics so review stays focused.
- Keep ROI artifact counts modest (16 worst ROIs) to avoid bloating the report directory.
- If CUDA is unavailable, note the device switch in summary.md but still run the probe/test suite on CPU.

If Blocked:
- If the refined MTZ path is missing or unreadable, record the error stack in `$REPORT/mapping_dataset_metrics/probe.log`, mention it in summary.md, and update docs/fix_plan Attempts History with the missing-asset blocker before stopping.
- If pytest cannot collect DB-AT-028/029 after the fixture change, archive the collect log, triage briefly (≤15 min), and if unresolved mark TOOLING-VIS-001 blocked with the exact error signature in fix_plan + summary.

Findings Applied (Mandatory):
- STAGEA-001 — Mapping/Stage A helpers must share calibration + HKL provenance; switching the default HKL source keeps the Stage A engine aligned with mapping diagnostics.
- SCALE-004 — Refined structure factors must travel with the calibration metadata; updating the fixture + probes enforces that pairing.
- SCALE-005 — Sigma/scale provenance must remain auditable; the probe and pytest artifacts still log sigma source + spot_scale even as HKL defaults change.

Pointers:
- docs/data_dependency_manifest.md:17-95 — mapping/helper dependency contract (HKL/calibration defaults, overrides, telemetry expectations).
- docs/fix_plan.md:340-360 — latest TOOLING-VIS-001 attempts noting HKL default drift and sigma-source probe evidence.
- docs/findings.md:9-42 — STAGEA-001 and SCALE-001–SCALE-006 guardrails on calibration/HKL usage.
- plans/active/TOOLING-VIS-001/implementation.md:1-160 — initiative goals, Phase D context, and acceptance gates for DB-AT-027/028/029.
- tests/dbex/test_stage_a_smoke_parity.py:70-190 — Stage A smoke fixture + diagnostics that consume the HKL metadata you’re changing.

Next Up (optional):
- If refined HKL + calibration still yield negative ROI CC, plan a follow-up loop to compare refined-vs-scaled HKL amplitudes (e.g., extend `probe_scale_chain.py`) before touching Stage A physics.
