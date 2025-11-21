# Input

- Summary: Embed a reusable refGeom metadata fixture and update the Stage A smoke so it proves `external_lookup` sigma tiles drive the chi-squared telemetry without relying on CLI overrides.
- Mode: Parity
- Focus: PHYSICS-LOSS-001 — Implement variance-weighted loss function
- Branch: integration
- Mapped tests:
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion`
- Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T065454Z/

## Do Now
- Focus Item: PHYSICS-LOSS-001
- Implement: `plans/active/PHYSICS-LOSS-001/bin/embed_sigma_external_lookup.py::main` (new script) plus `tests/conftest.py::smoke_dataset_paths`/`tests/dbex/test_torch_refine_smoke.py::{refinement_inputs,test_stage_a_expansion}` — add a CLI that copies `refGeom.expt` with synthetic `ExternalLookupItemDouble` tiles (from `--sigma-map` or `--sigma-value`), add a `--smoke-sigma-source` option/env knob so smoke fixtures can select between CLI overrides and metadata, and update the Stage A test to route metadata-backed inputs + assert telemetry shows `sigma_readout_provenance="external_lookup"` and the canonical chi-squared snapshot.
- Test: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion | tee plans/active/PHYSICS-LOSS-001/reports/2025-11-21T065454Z/pytest_stage_a_metadata.log`
- Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T065454Z/

## How-To Map
1. Create `plans/active/PHYSICS-LOSS-001/bin/embed_sigma_external_lookup.py` with argparse accepting `--expt`, `--output`, `--expt-idx`, and either `--sigma-map` (npz/npy/pkl via `dbex.data_load.load_sigma_readout_map`) or `--sigma-value` (uniform float). Use `dxtbx.model.ExperimentList.from_file` to clone the requested experiment, build an `ExternalLookupItemDouble` full of per-panel numpy tiles (float32, strictly positive), attach it under `imageset.external_lookup.pedestal`, and write the modified ExperimentList to `--output`. Emit a JSON sidecar in the same directory capturing provenance (source path, constant value) for audit.
2. Run the script before tests so the metadata fixture exists, e.g.:
   ```bash
   python plans/active/PHYSICS-LOSS-001/bin/embed_sigma_external_lookup.py \
     --expt refGeom.expt --output sp.proc/idx-0000_sigma_metadata.expt \
     --expt-idx 0 --sigma-value 3.0 \
     --report plans/active/PHYSICS-LOSS-001/reports/2025-11-21T065454Z/sigma_metadata.json
   ```
   (Add `--sigma-map sp.proc/sigma_map.npy` later if a calibrated tensor exists.)
3. Extend `tests/conftest.py`: add `--smoke-sigma-source` / `DBEX_SMOKE_SIGMA_SOURCE` (choices `cli_override` | `metadata`), include the chosen source in a new fixture, and when `metadata` is requested, rewrite `smoke_dataset_paths.expt_path` to `sp.proc/idx-0000_sigma_metadata.expt` (skip with a helpful message if the file is missing). Document that Stage smokes on metadata require the embedding script to be run first.
4. Update `tests/dbex/test_torch_refine_smoke.py`:
   - Thread the new `smoke_sigma_source` fixture into `refinement_inputs` so it either reuses the existing constant sigma tensor (`cli_override`) or pulls `sigma_readout_array = np.asarray(refgeom_dataload.sigma_readout_map)` when metadata is active.
   - In `test_stage_a_expansion`, branch on the sigma source: omit any CLI overrides when metadata is in use, assert `telemetry.sigma_readout_provenance == "external_lookup"`, log the canonical chi-squared snapshot into the telemetry helper, and keep existing gates for the CLI path untouched.
   - Guard Stage B/C fixtures to continue using the CLI overrides until we explicitly support metadata there (document via TODO comment).
5. Refresh `docs/TESTING_GUIDE.md` §1.4 and `docs/development/TEST_SUITE_INDEX.md` with the metadata-fixture workflow: how to run the embedding script, env/pytest knobs (`DBEX_SMOKE_SIGMA_SOURCE`, `--smoke-sigma-source`), and which artifacts (`pytest_stage_a_metadata.log`, telemetry JSON) belong under this report.
6. Execute the mapped Stage A selector with `DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full` so it exercises the metadata-backed dataset, then attach the log + telemetry JSON (if captured via `DBEX_SMOKE_TELEMETRY_PATH`) to this loop’s artifact folder.

## Pitfalls To Avoid
- Metadata tiles must stay `[panel, slow, fast]` with positive finite floats; never silently reshape or clamp bad data—raise with actionable errors matching spec-db-core.md.
- Keep precedence intact: CLI scalars/maps still win; only fall back to metadata when neither override is supplied.
- Do not mutate the original `refGeom.expt`; always write to a new file under `sp.proc/` so reproducibility reports can cite the exact asset.
- Ensure the Stage A smoke only drops the `--sigma-rdout` override when `smoke_sigma_source=metadata`; other paths still require deterministic scalars to keep acceptance gates stable.
- Telemetry assertions must check both provenance and reference medians to avoid masking regressions where metadata accidentally reverts to zeros.
- Preserve `enable_stage_a_warm_cache` and other perf knobs—metadata plumbing should not reintroduce per-panel model churn.

## If Blocked
If the script cannot find the requested experiment or `ExternalLookupItemDouble` APIs fail, capture the exact command/stdout/stderr in `plans/active/PHYSICS-LOSS-001/reports/2025-11-21T065454Z/blocked.log`, note whether the dataset exists under `sp.proc/`, and record the blocker + required asset (e.g., sigma map path) in `docs/fix_plan.md` Attempts History before pausing the initiative.

## Findings Applied (Mandatory)
- PHYSICS-LOSS-001 — Weighted-loss telemetry depends on truthful sigma provenance; Stage A smokes must now cover the metadata path.
- PHYSICS-LOSS-002 — Sigma-floor guards assume accurate variance, so metadata fixtures must enforce positive finite tiles before refinement.
- PHYSICS-LOSS-003 — Stage A chi-squared snapshots feed Stage B/C gates; metadata provenance needs to flow into those canonical metrics unchanged.
- PHYSICS-LOSS-004 — Loader validations (shape/positivity) still apply when building synthetic metadata; reuse the existing helper semantics.
- PHYSICS-LOSS-005 — DIALS `external_lookup` is the normative sigma source; this loop delivers the fixture + tests required to exercise it.
- REFINE-007 — Stage smokes remain the acceptance harness for detector offsets; telemetry captured from metadata runs must continue to satisfy the same detector reduction gates.

## Pointers
- docs/fix_plan.md:15 — PHYSICS-LOSS-001 entry with updated Attempts History and Phase G scope.
- plans/active/PHYSICS-LOSS-001/implementation.md:1 — Phase checklist (A–G) covering sigma provenance and the new metadata fixture requirements.
- docs/TESTING_GUIDE.md:80 — Sigma guard workflow + selector policy that needs updating for metadata fixtures.
- docs/development/TEST_SUITE_INDEX.md:12 — Registry rows for Stage smokes/CLI sigma selectors that must mention the new knob.
- tests/dbex/test_torch_refine_smoke.py:210 — `refinement_inputs` fixture currently hard-codes sigma tensors; needs parameterization.

## Next Up (optional)
1. Once Stage A metadata coverage is stable, extend the same sigma-source knob to Stage B/C smokes and DB-AT selectors so parity runs can validate external_lookup assets end-to-end.

## Mapped Tests Guardrail
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=metadata DBEX_SMOKE_DETECTOR_SIZE=full pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion > plans/active/PHYSICS-LOSS-001/reports/2025-11-21T065454Z/collect_stage_a_metadata.log`
