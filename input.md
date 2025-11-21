# Input

- Summary: Capture `refGeom_small` assets and rewire the Stage A/B/C smoke fixtures so they default to the cropped detector while documenting how parity suites keep the full dataset.
- Mode: Perf
- Focus: PERF-SMOKE-DETSIZE — Introduce small-detector fixture for smoke tests
- Branch: integration
- Mapped tests:
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py -k 'test_stage_a_expansion or test_stage_b_shell_modifiers or test_stage_c_detector_microslip' --smoke-detector-size=small`
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=full`
- Artifacts: plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T023537Z/

## Do Now
- Focus Item: PERF-SMOKE-DETSIZE
- Implement: `plans/active/PERF-SMOKE-DETSIZE/bin/crop_refgeom_to_small.py::main` (generate the cropped dataset + README/checksums), `tests/dbex/test_torch_refine_smoke.py::{pytest_addoption,refgeom_dataload,test_stage_a_expansion,test_stage_b_shell_modifiers,test_stage_c_detector_microslip}` (dataset selector + gate recalibration, telemetry expectations), and `docs/{spec-db-workflow.md,TESTING_GUIDE.md}` (document the smoke/parity workflow split and CLI knobs).
- Test: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py -k 'test_stage_a_expansion or test_stage_b_shell_modifiers or test_stage_c_detector_microslip' --smoke-detector-size=small | tee plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T023537Z/pytest_stage_smokes_small.log`
- Artifacts: plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T023537Z/

## How-To Map
1. Run `python plans/active/PERF-SMOKE-DETSIZE/bin/crop_refgeom_to_small.py --expt refGeom.expt --refl refGeom.refl --cbf lys_nitr_10_6_0001.cbf --mask 747_mask.pkl --fast-start 751 --slow-start 719 --width 1024 --height 1024 --output-root sp.proc/refGeom_small --report plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T023537Z/refGeom_small_report.json` to emit `refGeom_small.{expt,refl}` plus `lys_nitr_10_6_0001_small.cbf` and `refGeom_small_mask.pkl`; record ROI count + bbox ranges inside the JSON.
2. Capture checksums + README: `sha256sum sp.proc/refGeom_small/*.{cbf,expt,refl,pkl} > plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T023537Z/refGeom_small.sha256` and draft `sp.proc/refGeom_small/README.md` (include command, offsets, ROI counts, and artifact links).
3. Update `tests/dbex/test_torch_refine_smoke.py` fixtures to honor `--smoke-detector-size` (plus `DBEX_SMOKE_DETECTOR_SIZE` env override) and recalibrate Stage A/B/C assertion thresholds using telemetry captured from the small dataset; log perf counters + runtime deltas in `plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T023537Z/telemetry_small.json`.
4. Validate the small default path: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py -k 'test_stage_a_expansion or test_stage_b_shell_modifiers or test_stage_c_detector_microslip' --smoke-detector-size=small | tee plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T023537Z/pytest_stage_smokes_small.log`.
5. Sanity-check the full-detector fallback (document runtime delta for the README): `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=full | tee plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T023537Z/pytest_stage_a_full.log`.
6. Update `docs/spec-db-workflow.md` (§Stage smokes) and `docs/TESTING_GUIDE.md` (§2 Smoke selectors + §3 workflows) to describe the new `--smoke-detector-size`/`DBEX_SMOKE_DETECTOR_SIZE` controls, the expectation that smoke tests default to `refGeom_small`, and that DB-AT selectors assert the full detector dimensions; mirror the selector metadata in `docs/development/TEST_SUITE_INDEX.md`.

## Pitfalls To Avoid
- Do not rerun Stage smokes on the full detector unless explicitly passing `--smoke-detector-size=full`; defaulting to full violates the manual override.
- Keep CONFIG-001 invariants when cropping: adjust panel origin by the removed pixel offsets so detector/world coordinates stay consistent.
- Maintain ROI metadata integrity (bbox, xyzobs/xyzcal px, shoebox slices); dropping or half-updating these columns will corrupt `DataLoad`.
- Trusted mask polarity must remain True=include; when cropping the mask pickle, assert `np.mean(mask) > 0.5`.
- DB-AT selectors must keep using `refGeom.expt/.refl`; add guards that fail if someone tries to point parity tests at the small assets.
- Record runtime/VRAM improvements in the report; manual override requires quantitative evidence before heavy smoke loops resume.
- Do not install extra packages or rely on CUDA profiling tools; environment is frozen.
- Ensure new pytest option names are documented and added via `pytest_addoption` (no implicit env-only toggles).

## If Blocked
- If the crop script cannot write the CBF/EXPT/REFL because of DIALS/IOTBX APIs, capture the stack trace + command in `plans/active/PERF-SMOKE-DETSIZE/reports/2025-11-21T023537Z/crop_failure.log`, mark PERF-SMOKE-DETSIZE as blocked in `docs/fix_plan.md`, and stop.
- If small dataset runs still exceed VRAM/time budgets, attach telemetry + `nvidia-smi` snapshots to the artifacts, log the failure in `docs/fix_plan.md`, and await guidance before touching Stage smokes again.

## Findings Applied (Mandatory)
- CONFIG-001 — Preserve detector coordinate transforms and mask polarity when deriving `refGeom_small`; document the conversion in the README.
- PERF-WARM-001 — Reuse existing perf counters/telemetry fields when comparing small vs full detector runs so we can show speedup deltas in `/torch_diagnostics`.
- MASKING-001 — Low loss-mask coverage is expected; don’t over-filter ROIs while cropping or reinterpret low coverage as a failure.

## Pointers
- docs/spec-db-workflow.md:1 — Normative Stage smoke pipeline requirements and ROI semantics that the cropped dataset must continue to satisfy.
- docs/TESTING_GUIDE.md:1 — Canonical selector/env-flag definitions; update §2 with the new `--smoke-detector-size` workflow.
- docs/development/TEST_SUITE_INDEX.md:1 — Smoke/test registry entry that must mention the small-detector default and new pytest option.
- tests/dbex/test_torch_refine_smoke.py:1 — Existing fixtures/gates to parameterize and recalibrate.
- plans/active/PERF-SMOKE-DETSIZE/implementation.md:1 — Phase breakdown and checklist items to keep in sync with this work.

## Next Up (optional)
1. Once the small fixture lands, revisit PHYSICS-LOSS-001 Stage A/B/C smoke runs to finish the variance-weighted helper work.

## Mapped Tests Guardrail
- Run `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_torch_refine_smoke.py -k test_stage_a_expansion --smoke-detector-size=small` after wiring the pytest option; if it collects 0 tests, fix the fixture registration before running full smokes.
- Keep the `--smoke-detector-size=full` selector in `Mapped tests` as a sanity check; do not drop it without documenting why parity coverage is still intact.
