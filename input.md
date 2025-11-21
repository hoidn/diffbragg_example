# Input

- Summary: Enforce the nanobrag CLI’s sigma_readout contract by requiring a nonzero source and tagging sigma provenance through telemetry/tests.
- Mode: Parity
- Focus: PHYSICS-LOSS-001 — Implement variance-weighted loss function
- Branch: integration
- Mapped tests:
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_requires_sigma_rdout`
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata`
- Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T054520Z/

## Do Now
- Focus Item: PHYSICS-LOSS-001
- Implement: `dbex/refine_one.py::run_nanobrag_backend` — refuse to launch nanobrag refinement unless a positive `sigma_readout` source exists (CLI scalar or calibrated map), plumb the detected provenance/value into `RefinementConfig`/telemetry, and produce the actionable CLI error per spec-db-core.md:57-68 when both sources are missing.
- Implement: `dbex/refine_one.py::_write_torch_outputs` & `dbex/nanobrag_refinement.py::RefinementTelemetry` — add `sigma_readout_provenance` (string) and `sigma_readout_reference_value` (float, photon units) so Stage A/B/C telemetry and the HDF5 diagnostics record how the variance model was parameterized; update the CLI/unit tests accordingly.
- Implement: `tests/dbex/test_refine_one_cli.py` — add a regression that asserts `run_nanobrag_backend` raises with a clear message when `--sigma-rdout` is absent and no calibrated metadata is injected, and extend `test_torch_diagnostics_metadata` to verify the new telemetry/HDF5 attributes.
- Update: `docs/TESTING_GUIDE.md` — document the sigma_readout requirement for nanobrag runs (CLI/env knob + telemetry provenance) so future operators cannot skip the noise input.
- Test: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_refine_one_cli.py -k "sigma_rdout or torch_diagnostics_metadata" | tee plans/active/PHYSICS-LOSS-001/reports/2025-11-21T054520Z/pytest_cli_sigma.log`
- Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T054520Z/

## How-To Map
1. Inspect `dbex/refine_one.py::create_parser` and `run_nanobrag_backend` to determine where CLI options are parsed and `sigma_readout_array` is built. Introduce a helper (e.g., `_resolve_sigma_readout(DL, args)`) that returns both the tensor and a provenance enum; when neither CLI override nor future calibrated metadata is available, raise `ValueError("--sigma-rdout is required ...")` referencing spec-db-core.md:62-68.
2. When CLI provides the scalar, keep the broadcast path but enforce `args.sigma_rdout > 0`, log the value, and cache a float copy for telemetry. Wire the provenance/value into `RefinementConfig` so Stage A/B/C closures can expose them.
3. Extend `dbex/nanobrag_refinement.py::RefinementTelemetry` with `sigma_readout_provenance`/`sigma_readout_reference_value` (Optional[str]/Optional[float]); populate the fields for Stage A and propagate to Stage B/C snapshots so `_write_torch_outputs` can persist them.
4. Update `_write_torch_outputs` to emit the new attributes under each `torch_diagnostics/stage_*` group plus the legacy top-level Stage A mirror. Reflect the same fields in `_record_stage_telemetry` if additional JSON is written.
5. In `tests/dbex/test_refine_one_cli.py`, patch `run_nanobrag_backend` to assert the new failure path (`pytest.raises(ValueError, match="sigma_rdout")`) by ensuring mocks do not inject sigma noise. Update `test_nanobrag_backend_runs_simulator` (and other spots) to pass a valid `sigma_rdout` argument, and expand `test_torch_diagnostics_metadata` to inspect the new telemetry attrs in the HDF5 file.
6. Refresh `docs/TESTING_GUIDE.md` §2 to call out the now-required CLI sigma flag for nanobrag runs (point at the spec clause) and mention the telemetry provenance field so downstream tooling knows how to interpret chi-squared evidence.
7. Run the targeted pytest command above and drop the log into the artifacts directory; if additional tests fail, capture their logs in the same folder before iterating.

## Pitfalls To Avoid
- Do not silently zero `sigma_readout`; spec-db-core.md mandates positive noise terms and treating missing inputs as fatal.
- Keep device/dtype neutrality when broadcasting the sigma tensor; reuse the existing numpy→torch conversion paths without reintroducing CPU copies inside the closures.
- Preserve the variance-floor guard (`sigma_floor_value`) and ensure new telemetry fields never clobber the existing canonical Stage A metadata or chi-squared traces.
- Avoid inventing metadata heuristics—only accept explicit CLI overrides or future calibrated maps; anything else must raise with an actionable message.
- Keep `tests/dbex/test_refine_one_cli.py` deterministic by mocking simulator outputs rather than instantiating nanobrag_torch.
- Update every callsite that constructs `RefinementTelemetry`; missing the new fields will trigger dataclass init errors.
- When editing docs/TESTING_GUIDE.md, do not relax the canonical Stage A/B/C gates or DB-AT guard verbiage.
- The new telemetry attrs belong in both per-stage groups and the legacy Stage A mirror; forgetting either breaks existing reporting scripts.
- Preserve Environment Freeze—no pip installs or torch upgrades while running the CLI tests.

## If Blocked
- If the CLI still cannot determine sigma provenance (e.g., metadata API missing), capture the exact error/traceback, log it in `plans/active/PHYSICS-LOSS-001/reports/2025-11-21T054520Z/blocked.log`, and append a note to `docs/fix_plan.md` Attempts History describing why Phase A4 remains blocked. Include the command (`pytest ...` or CLI invocation) and the detector asset you attempted to use.

## Findings Applied (Mandatory)
- PHYSICS-LOSS-001 — All refinement paths must emit chi-squared + masked-MSE with correct variance inputs; enforcing the CLI guard keeps the variance model valid.
- PHYSICS-LOSS-002 — Sigma-floor clamps depend on truthful sigma tensors; refusing zeroed noise ensures the clamp telemetry remains meaningful.
- PHYSICS-LOSS-003 — Stage A canonical chi-squared snapshots feed Stage B/C telemetry, so provenance tagging must stay consistent across stages.
- REFINE-007 — Canonical smoke gating consumes Stage A telemetry; the new provenance field documents whether the noise came from CLI overrides or calibrated assets.
- SCALE-007 — DB-AT-024 needs diagnostic proof for chi-squared inputs; documenting sigma provenance prevents silent drift between CLI runs and acceptance tests.

## Pointers
- docs/spec-db-core.md:57 — Normative variance-weighted loss and sigma_readout requirements.
- dbex/refine_one.py:70 — CLI parser definitions for `--sigma-rdout`/`--sigma-floor`.
- dbex/refine_one.py:200 — Current sigma broadcast + telemetry plumbing that still allows zeroed tensors.
- dbex/nanobrag_refinement.py:322 — `RefinementTelemetry` fields where the new provenance/value attributes belong.
- docs/TESTING_GUIDE.md:30 — Stage smoke + CLI invocation requirements that need updating with the sigma guard.

## Next Up (optional)
1. After sigma provenance is enforced, revisit `DataLoad`/detector ingestion to surface calibrated dark-noise maps so CLI users can omit the override when metadata exists.

## Doc Sync Plan (Conditional)
- After adding the new `tests/dbex/test_refine_one_cli.py::test_nanobrag_backend_requires_sigma_rdout` node (and adjusting existing tests), run `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_refine_one_cli.py > plans/active/PHYSICS-LOSS-001/reports/2025-11-21T054520Z/collect_cli_sigma.log` once code passes, and update `docs/TESTING_GUIDE.md` + `docs/development/TEST_SUITE_INDEX.md` to describe the sigma guard regression.

## Mapped Tests Guardrail
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_refine_one_cli.py -k sigma_rdout`
