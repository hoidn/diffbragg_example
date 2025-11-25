Summary: Capture HKL/sigma-source provenance and compare metadata-sigma vs cli_override mapping forwards so we can explain the -0.04 ROI CC baseline before rerunning DB-AT-028/029.
Mode: Parity
Focus: TOOLING-VIS-001 — Stage A Mapping Alignment & Visual Diagnostics
Branch: integration
Mapped tests: tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity; tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T060403Z/

Do Now
- Implement: plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py::main — add sigma/HKL provenance fields (sigma_source, HKL path, HKL count, spot_scale_override, masked/unmasked scale ratios) and support writing separate JSONs/logs for metadata-sigma and cli_override contexts under `mapping_variants/<sigma_source>/` so we can diff ROI CC/scale without rerunning code.
- Implement: tests/dbex/test_stage_a_smoke_parity.py::stage_a_smoke_result — persist sigma_source, HKL path/count, spot_scale_override, and masked/unmasked scale ratios into DB-AT-028/029 metrics before assertions (no tolerance changes) to match the probe’s provenance fields.
- Validate: Run the probe twice (metadata-sigma then cli_override) with canonical env, then rerun DB-AT-028/029 with metadata-sigma:  
  `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBEX_SMOKE_SIGMA_SOURCE=metadata plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T060403Z/mapping_variants/metadata | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T060403Z/mapping_variants/metadata/probe.log`;  
  `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBEX_SMOKE_SIGMA_SOURCE=cli_override plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py --out-dir plans/active/TOOLING-VIS-001/reports/2025-11-25T060403Z/mapping_variants/cli_override | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T060403Z/mapping_variants/cli_override/probe.log`;  
  `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small DBAT028_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T060403Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/TOOLING-VIS-001/reports/2025-11-25T060403Z/db_at_029 KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T060403Z/pytest_db_at_028_029.log`;  
  `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/TOOLING-VIS-001/reports/2025-11-25T060403Z/pytest_db_at_028_029_collect.log`.
- Artifacts: plans/active/TOOLING-VIS-001/reports/2025-11-25T060403Z/{mapping_variants/metadata/,mapping_variants/cli_override/,db_at_028/,db_at_029/,pytest_db_at_028_029.log,pytest_db_at_028_029_collect.log,summary.md}

How-To Map
1) Export canonical env vars per command snippets; keep `DBEX_SMOKE_DETECTOR_SIZE=small`, `KMP_DUPLICATE_LIB_OK=TRUE`, `NANOBRAGG_DISABLE_COMPILE=1`, and swap only `DBEX_SMOKE_SIGMA_SOURCE` between metadata and cli_override for the probe runs.
2) Extend `compare_mapping_forward_cpu_gpu.py` to emit sigma_source, HKL path/count, spot_scale_override, masked/unmasked scale ratios, and parity deltas into the JSON it already writes; add CLI args or directory naming so metadata vs cli_override runs write to `mapping_variants/<sigma_source>/`.
3) Update `stage_a_smoke_result` to include sigma/HKL provenance (path, count) and spot_scale_override in the db_at_028/db_at_029 metrics; keep existing ROI CC/scale/clamp assertions unchanged.
4) Run the two probe commands (metadata then cli_override) capturing JSON + logs under the artifacts path; verify JSONs include ROI CC, scale ratios (masked/unmasked), sigma_source, HKL path/count, spot_scale_override.
5) Run pytest execution and collect-only for DB-AT-028/029 with metadata-sigma; ensure metrics JSONs persist even on failure.
6) Summarize probe deltas (metadata vs cli_override) and DB-AT-028/029 signatures in summary.md, noting whether sigma source/HKL differences explain the -0.04 ROI CC baseline.

Pitfalls To Avoid
- Do not change DB-AT-028/029 tolerances or masking; diagnostics only.
- Keep dataset/provenance fixed across runs except for sigma_source; do not swap HKL files beyond controlled logging.
- Persist metrics before assertions; avoid early exits that drop JSON/logs.
- No environment/package changes (Environment Freeze); keep torch.compile disabled.
- Avoid mixing masked and unmasked ratios in the same field; name them explicitly.

If Blocked
- Capture both probe JSON/logs and pytest logs to the artifacts path, record observed ROI CC/scale ratios for metadata vs cli_override in summary.md and docs/fix_plan.md Attempts History, and mark TOOLING-VIS-001 blocked if CUDA unavailable or sigma_source swap fails to collect data.

Findings Applied (Mandatory)
- STAGEA-001 — Reuse calibrated mapping baselines and log diagnostics before gating.
- GEOMETRY-003 / GEOMETRY-004 — Preserve HKL provenance and mapping zero-point invariants when comparing contexts.
- PHYSICS-LOSS-001 — Keep variance-weighted chi² semantics and loss_mask pixel counts.
- POLICY-001 — Environment Freeze; no new dependencies or toolchain changes.
- CONFORMANCE-001 — Archive pytest logs and collect-only output for DB-AT selectors.

Pointers
- docs/spec-db-conformance.md:280-366 (DB-AT-028/029 tolerances)
- docs/TESTING_GUIDE.md:150-190 (DB-AT env/commands, artifact expectations)
- tests/dbex/test_stage_a_smoke_parity.py:1-240 (Stage A smoke fixture + metrics/diagnostics)
- plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py (probe to extend with sigma/HKL provenance)
- docs/findings.md#L9 (STAGEA-001 calibration baseline handling)

Next Up (optional)
- If sigma_source swap isolates the ROI CC gap, plan a follow-up loop to align mapping/Stage A config to the passing source before re-running DB-AT-028/029.

Doc Sync Plan (Conditional)
- None this loop unless DB-AT-028/029 status changes; if status flips, update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md after tests pass and archive collect-only logs.

Mapped Tests Guardrail
- Ensure `pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` collects both selectors (>0); keep the collect-only log in artifacts.

Hard Gate
- Do not close the loop without metadata vs cli_override probe JSONs (with sigma/HKL provenance) and db_at_028/db_at_029 metrics plus summary.md notes on ROI CC/scale ratios; treat zero-collected selectors as a blocker.

Normative Math/Physics
- Use docs/spec-db-conformance.md §280-366 and docs/spec-db-core.md §84-90 directly for χ²/variance/ROI CC definitions; no tolerance relaxation or paraphrased equations.
