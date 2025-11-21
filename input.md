# Input

- Summary: Teach DataLoad to harvest calibrated sigma_readout tensors directly from DIALS `external_lookup` metadata so the nanobrag variance guard works without forcing `--sigma-map`.
- Mode: Parity
- Focus: PHYSICS-LOSS-001 — Implement variance-weighted loss function
- Branch: integration
- Mapped tests:
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_data_load_sigma_map.py -k "sigma_map or external_lookup"`
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_refine_one_cli.py -k "sigma_map or sigma_rdout"`
- Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T063052Z/

## Do Now
- Focus Item: PHYSICS-LOSS-001
- Implement: `dbex/data_load.py::_load_external_lookup_sigma_map` (new helper) — scan `Experiment.imageset.external_lookup` for `ExternalLookupItemDouble` payloads (pedestal/dark RMS), reshape tiles to `[panel, slow, fast]`, enforce strict positivity/shape, and return a float32 tensor plus provenance metadata.
- Implement: `dbex/data_load.py::DataLoad.__init__` — record whether `sigma_readout_map` came from CLI (`--sigma-map`) or metadata, and when no CLI asset is provided, call the helper to populate the tensor from `external_lookup`.
- Implement: `dbex/refine_one.py::_resolve_sigma_readout` — branch on `dataload.sigma_readout_map_source` so metadata-driven tensors set `sigma_readout_provenance="external_lookup"` (after any ADU→photon conversion) while CLI map usage stays `calibrated_map`; keep reference medians for telemetry/HDF5.
- Implement: `tests/dbex/test_data_load_sigma_map.py::{test_external_lookup_sigma_map_ingestion,test_external_lookup_shape_or_value_errors}` — instantiate synthetic `ExternalLookupItemDouble` stacks to prove the helper accepts valid metadata, raises on mismatched tiles/non-positive values, and prefers CLI assets when both are supplied.
- Implement: `tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_accepts_external_lookup_sigma_map` — mirror the existing sigma-map test but set `mock_dl.sigma_readout_map_source="external_lookup"` and assert `_write_torch_outputs` records the new provenance plus photon-space median.
- Update: `docs/TESTING_GUIDE.md` & `docs/development/TEST_SUITE_INDEX.md` — describe the metadata harvest workflow, selector commands/log paths (`2025-11-21T063052Z`), and clarify precedence order (CLI scalar > CLI map > metadata).
- Test: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_data_load_sigma_map.py -k "sigma_map or external_lookup" | tee plans/active/PHYSICS-LOSS-001/reports/2025-11-21T063052Z/pytest_data_load_sigma_map.log`
- Test: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_refine_one_cli.py -k "sigma_map or sigma_rdout" | tee plans/active/PHYSICS-LOSS-001/reports/2025-11-21T063052Z/pytest_cli_sigma_map.log`
- Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T063052Z/

## How-To Map
1. Implement `_load_external_lookup_sigma_map(imageset, expected_shape)` in `dbex.data_load`: accept `ExternalLookupItemDouble` tiles, convert their `flex.double` payloads to numpy, enforce `[panel, slow, fast]` shape + finite positive values, and raise actionable `ValueError`s when metadata is malformed.
2. Extend `DataLoad.__init__` so `self.sigma_readout_map` caches CLI assets first; otherwise call the helper using `self.Expt.imageset`. Track the source string (e.g., `"cli_map"` vs `"external_lookup"`) for `_resolve_sigma_readout`.
3. Update `_resolve_sigma_readout()` to branch on the stored source: CLI scalar (`cli_override`) remains highest priority, CLI map keeps `calibrated_map`, and metadata maps set `external_lookup`. Ensure the reference median is computed after any ADU→photon conversion and flows through `_write_torch_outputs`.
4. Expand `tests/dbex/test_data_load_sigma_map.py` with fixtures that build `ExternalLookupItemDouble` instances via `ImageDouble`/`ImageTileDouble`, covering success and error scenarios. Include a regression that proves metadata is ignored when a CLI map is supplied.
5. Add the new CLI test to `tests/dbex/test_refine_one_cli.py`, reusing the existing mocks but setting `mock_dl.sigma_readout_map_source="external_lookup"` and asserting telemetry strings/values.
6. Refresh `docs/TESTING_GUIDE.md` §1.4 and `docs/development/TEST_SUITE_INDEX.md` entries so operators know the precedence rules, metadata requirements, and artifact paths for the updated selectors.
7. Run the mapped pytest commands above (with `AUTHORITATIVE_CMDS_DOC` exported) and archive full logs plus any failures under this loop’s artifacts before handing back results.

## Pitfalls To Avoid
- Do not mutate `ExternalLookupItemDouble.data` tiles in place—copy into numpy arrays so dxtbx metadata stays untouched.
- Reject zero/negative or non-finite metadata immediately; spec-db-core.md §Variance forbids these and silent clamps would hide bad assets.
- Ensure `n_tiles` equals the detector panel count and each tile shape matches `(slow, fast)`; do not broadcast or pad metadata.
- Preserve precedence: CLI scalar > CLI map > metadata. Metadata must not override explicit user choices.
- Keep provenance strings stable; tests and telemetry consumers expect `"cli_override"`, `"calibrated_map"`, or `"external_lookup"`.
- Maintain device/dtype neutrality when constructing numpy tensors (float32) and avoid adding torch dependencies to the loader.
- Environment Freeze stays in effect—no pip installs when adding helper tests.

## If Blocked
Capture the failing command, stack, and metadata source in `plans/active/PHYSICS-LOSS-001/reports/2025-11-21T063052Z/blocked.log`, update `docs/fix_plan.md` Attempts History with the blocker + return criteria, and set `galph_memory.md` to `state=blocked` if calibration assets are truly absent or unreadable.

## Findings Applied (Mandatory)
- PHYSICS-LOSS-001 — Weighted loss/telemetry must share the same sigma provenance across Stage A/B/C; metadata ingestion keeps gates meaningful.
- PHYSICS-LOSS-002 — Sigma-floor clamps assume truthful readout noise; metadata tiles must be validated before reaching the variance denominator.
- PHYSICS-LOSS-003 — Stage A chi-squared snapshots back Stage B/C gates, so provenance tagging cannot regress when source switches to metadata.
- PHYSICS-LOSS-004 — Loader guardrails (shape/positivity) still apply to metadata-derived tensors; reuse the same validation semantics.
- PHYSICS-LOSS-005 — DIALS `external_lookup` tiles are the normative source once available; `DataLoad` must harvest them and expose provenance.
- REFINE-007 — Stage B/C detector-offset gates consume Stage A telemetry; clearly exposing metadata provenance keeps acceptance reviews audit-able.

## Pointers
- docs/spec-db-core.md:32-74 — Normative variance contracts and telemetry provenance requirements.
- docs/simtbx_api.md:20-36 — Context for per-pixel pedestal RMS ingestion used in DiffBragg (mirrors the metadata we are harvesting).
- docs/TESTING_GUIDE.md:80-90 — Sigma guard workflow and selector policy that need updating.
- docs/development/TEST_SUITE_INDEX.md:12-20 — Registry rows covering the sigma CLI + loader suites.
- plans/active/PHYSICS-LOSS-001/implementation.md — Phase F checklist defining the metadata-harvest deliverables.

## Next Up (optional)
1. After metadata ingestion lands, plumb external-lookups into manifest tooling so refGeom assets can ship calibrated sigma tiles without manual CLI flags.

## Mapped Tests Guardrail
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_data_load_sigma_map.py -k "sigma_map or external_lookup" > plans/active/PHYSICS-LOSS-001/reports/2025-11-21T063052Z/collect_data_load_sigma_map.log`
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_refine_one_cli.py -k "sigma_map or sigma_rdout" > plans/active/PHYSICS-LOSS-001/reports/2025-11-21T063052Z/collect_cli_sigma_map.log`
