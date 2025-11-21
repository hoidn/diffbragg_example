# Input

- Summary: Allow nanobrag to consume calibrated sigma_readout maps supplied with the dataset so the variance guard no longer depends solely on CLI scalars.
- Mode: Parity
- Focus: PHYSICS-LOSS-001 — Implement variance-weighted loss function
- Branch: integration
- Mapped tests:
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_refine_one_cli.py -k "sigma_map or sigma_rdout"`
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_data_load_sigma_map.py`
- Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T060701Z/

## Do Now
- Focus Item: PHYSICS-LOSS-001
- Implement: `dbex/refine_one.py::create_parser` — add a `--sigma-map` option that accepts `.npy/.npz` stacks or pickled tuples of per-panel arrays, document units (ADU unless gain conversion requested), and plumb the path into the `DataLoad` namespace.
- Implement: `dbex/data_load.py::DataLoad.__init__` (and helper) — when `args.sigma_map` is provided, load the asset, validate it is strictly positive and shape-aligned with `data`, convert flex tuples to numpy, and expose `self.sigma_readout_map` (float32) for `_resolve_sigma_readout` to consume.
- Implement: `dbex/refine_one.py::_resolve_sigma_readout` — extend the calibrated-map branch to use `DataLoad.sigma_readout_map`, ensure ADU→photon conversion obeys `--adu-per-photon`, compute the reference median, and tag `RefinementConfig`/telemetry with `sigma_readout_provenance="calibrated_map"`.
- Implement: `tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_accepts_sigma_map` — mock a `sigma_readout_map` tensor on the DataLoad stub, assert nanobrag runs without `--sigma-rdout`, and verify `prepare_refinement_inputs` receives the calibrated tensor plus telemetry attrs stored via `_write_torch_outputs`.
- Implement: `tests/dbex/test_data_load_sigma_map.py::test_sigma_map_loader_formats` — add unit tests for the loader helper covering `.npy`, `.npz`, and pickled tuple inputs, including shape mismatch and non-positive guardrails.
- Update: `docs/TESTING_GUIDE.md` & `docs/development/TEST_SUITE_INDEX.md` — describe how to package calibrated sigma maps, note the new CLI flag + telemetry provenance, and register the new regression selectors plus their collect-only logs.
- Test: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_refine_one_cli.py -k "sigma_map or sigma_rdout" | tee plans/active/PHYSICS-LOSS-001/reports/2025-11-21T060701Z/pytest_cli_sigma_map.log`
- Test: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_data_load_sigma_map.py | tee plans/active/PHYSICS-LOSS-001/reports/2025-11-21T060701Z/pytest_data_load_sigma_map.log`
- Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T060701Z/

## How-To Map
1. Add the `--sigma-map` parser option (string path) with help text citing `docs/spec-db-core.md:32-68`, ensure it lands in the args Namespace, and pass it into `DataLoad` (e.g., `args.sigma_map`).
2. Implement `load_sigma_readout_map(path, expected_shape)` inside `dbex.data_load`: support `.npy`/`.npz` and pickled tuples/lists/flex arrays, coerce to `np.float32`, enforce positive values + matching panel count, and raise actionable `ValueError`s when validation fails; call it from `DataLoad.__init__` when `args.sigma_map` is set.
3. Update `_resolve_sigma_readout()` so calibrated maps are used whenever CLI scalar is absent: copy the numpy tensor, broadcast-check against `dataload.data`, divide by `adu_per_photon` when provided, and set `sigma_readout_provenance="calibrated_map"` plus `sigma_readout_reference_value=np.median(...)` before threading into `RefinementConfig` and `_write_torch_outputs`.
4. Extend `tests/dbex/test_refine_one_cli.py` with a new regression that patches `_write_torch_outputs`/`prepare_refinement_inputs`, injects a fake map via `mock_dl.sigma_readout_map`, asserts the CLI no longer raises, and checks telemetry attrs equal the calibrated values; update the existing guard test to keep asserting the failure path when neither source exists.
5. Author `tests/dbex/test_data_load_sigma_map.py` exercising `load_sigma_readout_map` with synthetic `.npy` and `.pkl` payloads via `tmp_path`, covering success, shape mismatch, and non-positive values; these tests run without touching refGeom assets.
6. Refresh `docs/TESTING_GUIDE.md` §1.4 (sigma guard) and `docs/development/TEST_SUITE_INDEX.md` to document the calibrated-map workflow, referenced selectors, and new collect-only logs captured under `plans/active/PHYSICS-LOSS-001/reports/2025-11-21T060701Z/`.
7. Run both mapped pytest commands above (with `AUTHORITATIVE_CMDS_DOC` exported) and archive the logs. If additional selectors fail, capture their logs beside the main artifacts before iterating.

## Pitfalls To Avoid
- Do not silently reshape or pad the sigma map; enforce exact `[panel, slow, fast]` alignment with `DataLoad.data` so Stage A/B/C receive identical weights.
- Reject zeros/negatives immediately—spec-db-core.md:32 forbids non-positive readout noise, and allowing them would reintroduce infinite variance weights.
- Preserve photon/ADU semantics: when `--adu-per-photon` is set, divide both CLI scalars and calibrated tensors consistently before forwarding to the bridge.
- Keep `_resolve_sigma_readout` thread-safe for multi-panel detectors; avoid mutating `dataload.sigma_readout_map` in-place when broadcasting casts.
- Ensure telemetry and `_write_torch_outputs` still emit `sigma_readout_provenance`/`sigma_readout_reference_value`; missing attrs will break `tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata`.
- Treat loader errors as actionable `ValueError`s referencing the offending file and expected shape; do not swallow exceptions or downgrade to warnings.
- Maintain Environment Freeze: no pip installs or dependency upgrades while exercising the new selectors.

## If Blocked
Capture the failure mode (loader exception, CLI path, or pytest failure) in `plans/active/PHYSICS-LOSS-001/reports/2025-11-21T060701Z/blocked.log`, include the command, sigma-map asset details, and traceback, then append an Attempts History note in `docs/fix_plan.md` explaining what prevented calibrated-map ingestion. Flag the focus as `blocked` with unblock criteria in `galph_memory.md` if the issue is external (e.g., missing instrument files).

## Findings Applied (Mandatory)
- PHYSICS-LOSS-001 — All refinement stages must share the same variance-weighted loss and telemetry; the calibrated-map path keeps chi-squared traces meaningful across Stage A/B/C.
- PHYSICS-LOSS-002 — Sigma-floor telemetry only makes sense when sigma tensors are truthful; ingesting calibrated maps prevents the clamp stats from hiding uninitialized noise.
- PHYSICS-LOSS-003 — Stage A’s canonical chi-squared snapshot feeds Stage B/C gates, so provenance tagging must remain consistent when the source switches from CLI scalars to calibrated maps.
- REFINE-007 — Stage B/C acceptance relies on Stage A telemetry; recording whether sigma came from a map ensures the detector-offset gates can be interpreted correctly during DB-AT reviews.
- SCALE-007 — CLI guardrails (refined MTZ + calibration metadata) demand actionable errors; the sigma-map loader must follow the same standard so operators cannot run parity selectors with silent fallbacks.

## Pointers
- docs/spec-db-core.md:32-70 — Normative variance/sigma_readout contracts and telemetry provenance requirements.
- docs/TESTING_GUIDE.md:83-86 — Sigma guard instructions and selector mapping that must be refreshed for the calibrated-map workflow.
- docs/development/TEST_SUITE_INDEX.md:13 — Registry entry for the CLI selector covering sigma guard/telemetry.
- plans/active/PHYSICS-LOSS-001/implementation.md — Phase A4/D completed, Phase E checklist defines the calibrated-map deliverables.
- docs/dxtbx_api.md:17 — Detector metadata references for future instrument-backed sigma maps.

## Next Up (optional)
1. Once the loader path is stable, teach `DataLoad` to harvest sigma maps from `Experiment.imageset.external_lookup` so operators can omit `--sigma-map` when DIALS assets already embed calibrated noise.

## Doc Sync Plan (Conditional)
- After tests pass, run `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_refine_one_cli.py -k "sigma_map or sigma_rdout" > plans/active/PHYSICS-LOSS-001/reports/2025-11-21T060701Z/collect_cli_sigma_map.log` and `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_data_load_sigma_map.py > plans/active/PHYSICS-LOSS-001/reports/2025-11-21T060701Z/collect_data_load_sigma_map.log`, then update `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` with the new selectors + artifact references.

## Mapped Tests Guardrail
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_refine_one_cli.py -k "sigma_map or sigma_rdout"` (must collect 1 test before implementation work concludes).
