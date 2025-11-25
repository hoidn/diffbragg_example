Summary: Compare scaled.mtz vs refined HKL mapping forwards to pinpoint the Stage A anti-correlation, aligning probe + DB-AT-028/029 fixtures on the same HKL override.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity; tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T061925Z/

Do Now
- Implement: plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py::main — add `--mtz-path` (defaulting to scaled.mtz or DBEX_SMOKE_HKL_PATH if set) so the probe can run both scaled and refined HKL inputs, propagate the chosen path/source into DataLoad + diagnostics, and keep sigma/HKL provenance fields in the JSON/log.
- Implement: tests/dbex/test_torch_refine_smoke.py::refgeom_dataload — honor `DBEX_SMOKE_HKL_PATH` (default scaled.mtz) when constructing the DataLoad so the Stage A smoke fixture and mapping probe share the same HKL source without changing defaults for other tests; ensure the HKL path/count already emitted in db_at_028/db_at_029 metrics reflects the override.
- Validate: Run the probe twice (scaled then refined HKL) and rerun DB-AT-028/029 with metadata sigma using the refined HKL override:  
  `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_HKL_PATH=scaled.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T061925Z/mapping_scaled | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T061925Z/mapping_scaled/probe.log`;  
  `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_HKL_PATH=tests/fixtures/golden_data/simple_cubic/refined_structure_factors.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T061925Z/mapping_refined | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T061925Z/mapping_refined/probe.log`;  
  `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_HKL_PATH=tests/fixtures/golden_data/simple_cubic/refined_structure_factors.mtz DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T061925Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T061925Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T061925Z/pytest_db_at_028_029.log`;  
  `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBEX_SMOKE_HKL_PATH=tests/fixtures/golden_data/simple_cubic/refined_structure_factors.mtz KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T061925Z/pytest_db_at_028_029_collect.log`.
- Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T061925Z/{mapping_scaled/,mapping_refined/,db_at_028/,db_at_029/,pytest_db_at_028_029.log,pytest_db_at_028_029_collect.log,summary.md}

How-To Map
1) Add `--mtz-path` to the probe CLI; default to `Path(repo_root/"scaled.mtz")` when neither CLI arg nor DBEX_SMOKE_HKL_PATH is set, and resolve relative paths against repo root to avoid cwd surprises; propagate the selected path/source into DataLoad and the JSON summary.
2) Update `refgeom_dataload` to read DBEX_SMOKE_HKL_PATH (if set) and pass it to DataLoad; keep scaled.mtz as the default so other tests stay unchanged. Ensure the HKL path/count in the DB-AT metrics reflect this override (metrics already recorded in stage_a_smoke_result).
3) Run the mapping probe twice with the commands above, verifying each JSON/log captures ROI CC, scale ratios, sigma_source, hkl_path/count, spot_scale_override, and parity metrics.
4) Rerun DB-AT-028/029 with metadata sigma and the refined HKL override; capture execution + collect-only logs plus db_at_028/db_at_029 metrics JSONs (should persist even on failure).
5) Summarize scaled vs refined ROI CC/scale deltas and DB-AT-028/029 signatures in summary.md, noting whether refined HKL improves correlation.

Pitfalls To Avoid
- Do not change DB-AT-028/029 tolerances or masking; diagnostics only.
- Keep defaults intact when DBEX_SMOKE_HKL_PATH is unset to avoid disrupting other fixtures/selectors.
- Resolve HKL paths relative to repo root to avoid missing-file errors in CI.
- Ensure probe and pytest runs use the same sigma source (metadata) and detector size (small); no ad-hoc dataset swaps.
- Persist metrics before assertions so artifacts exist even on failure; keep torch.compile disabled.
- No environment or dependency changes (Environment Freeze).

If Blocked
- Save both probe JSONs/logs and pytest logs to the artifacts path, record ROI CC/scale ratios for scaled vs refined HKL in summary.md and docs/fix_plan.md Attempts History, and mark TOOLING-VIS-001 blocked if HKL override cannot be honored or selectors fail to collect.

Findings Applied (Mandatory)
- STAGEA-001 — Preserve calibrated mapping baselines and log diagnostics before gating.
- GEOMETRY-003 / GEOMETRY-004 — Maintain mapping zero-point invariants and HKL provenance.
- PHYSICS-LOSS-001 — Keep variance-weighted chi² semantics and loss_mask pixel counts.
- POLICY-001 — Environment Freeze; no new deps or toolchain changes.
- CONFORMANCE-001 — Archive pytest execution + collect-only logs for DB-AT selectors.

Pointers
- docs/spec-db-conformance.md:280-366 (DB-AT-028/029 tolerances)
- docs/TESTING_GUIDE.md:150-190 (DB-AT env/commands, artifact expectations)
- tests/dbex/test_torch_refine_smoke.py:97-133 (refgeom_dataload DataLoad construction)
- plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py (probe to extend with HKL override)
- tests/dbex/test_stage_a_smoke_parity.py:70-240 (Stage A parity fixture + metrics)

Next Up (optional)
- If refined HKL improves ROI CC, plan follow-up to choose the canonical HKL source and update DB-AT-028/029 gate status and docs accordingly.

Doc Sync Plan (Conditional)
- None unless DB-AT-028/029 status changes; if they flip, archive collect-only logs and update docs/TESTING_GUIDE.md §2 + docs/development/TEST_SUITE_INDEX.md after tests pass.

Mapped Tests Guardrail
- Ensure `pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` collects both selectors (>0); treat zero collection as a blocker.

Hard Gate
- Do not finish without both probe JSONs (scaled + refined HKL) and db_at_028/db_at_029 metrics plus summary.md notes comparing ROI CC/scale ratios; if selectors still fail, log signatures and keep focus open.

Normative Math/Physics
- Use docs/spec-db-conformance.md §280-366 for DB-AT-028/029 gates and docs/spec-db-core.md §84-90 for variance/ROI CC definitions; no tolerance relaxation or paraphrased equations.
