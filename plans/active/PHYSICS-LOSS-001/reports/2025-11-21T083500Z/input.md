# Input

- Summary: Lock down the metadata sigma fixtures with a reproducible manifest + CI gate so Phase G assets can’t drift without detection.
- Mode: none
- Focus: PHYSICS-LOSS-001 — Implement variance-weighted loss function
- Branch: integration
- Mapped tests:
  * `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/sp_proc/test_sigma_metadata_fixture.py`
- Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T083500Z/

## Do Now
- Focus Item: PHYSICS-LOSS-001
- Implement: `plans/active/PHYSICS-LOSS-001/bin/embed_sigma_external_lookup.py::main`, `sp.proc/README.md`, `sp.proc/sigma_metadata_manifest.json`, `tests/sp_proc/test_sigma_metadata_fixture.py::test_sigma_metadata_manifest_and_loading`, `docs/TESTING_GUIDE.md#1.4`, `docs/development/TEST_SUITE_INDEX.md:1` — extend the embedding script with a `--manifest` flag that records generator command + SHA256 hashes for `idx-0000_sigma_metadata.{expt,sigma_tiles.pkl}` and the provenance JSON, publish the manifest + README so Phase G operators know how to regenerate the fixtures, and add a pytest module that reads the manifest, recomputes hashes, and reloads the experiment via `_load_external_lookup_sigma_map` to assert `sigma_readout_provenance="external_lookup"`.
- Test: `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/sp_proc/test_sigma_metadata_fixture.py | tee plans/active/PHYSICS-LOSS-001/reports/2025-11-21T083500Z/pytest_sigma_metadata_fixture.log`
- Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T083500Z/

## How-To Map
1. Run `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md python plans/active/PHYSICS-LOSS-001/bin/embed_sigma_external_lookup.py --expt refGeom.expt --output sp.proc/idx-0000_sigma_metadata.expt --sigma-value 3.0 --report plans/active/PHYSICS-LOSS-001/reports/2025-11-21T083500Z/sigma_metadata.json --manifest sp.proc/sigma_metadata_manifest.json` so the new flag captures command metadata, stats, sizes, and SHA256 hashes for the `.expt`, `.sigma_tiles.pkl`, and report files.
2. Author `sp.proc/README.md` to document the metadata fixture workflow (script invocation, manifest expectations, hash validation procedure, artifact locations) and reference spec-db-core.md:32-68 plus docs/TESTING_GUIDE.md §1.4.
3. Add `tests/sp_proc/test_sigma_metadata_fixture.py` that loads `sp.proc/sigma_metadata_manifest.json`, recomputes hashes for `idx-0000_sigma_metadata.{expt,sigma_tiles.pkl}` (warn if files missing), asserts manifest timestamps/commands are present, and uses `dxtbx.model.ExperimentList` + `dbex.data_load._load_external_lookup_sigma_map` to confirm the embedded tiles materialize and report the correct provenance metadata.
4. Update `docs/TESTING_GUIDE.md` §1.4 and `docs/development/TEST_SUITE_INDEX.md` to describe the manifest/validation command, required env vars, and artifact expectations (`pytest_sigma_metadata_fixture.log`, updated manifest snapshot) so CI operators know how to gate the fixtures.
5. Run the mapped pytest command (step above) with `AUTHORITATIVE_CMDS_DOC` + `KMP_DUPLICATE_LIB_OK=TRUE`, teeing stdout/stderr into `plans/active/PHYSICS-LOSS-001/reports/2025-11-21T083500Z/pytest_sigma_metadata_fixture.log` and copying the refreshed `sp.proc/sigma_metadata_manifest.json` + `sigma_metadata.json` into the same directory for archival.

## Pitfalls To Avoid
- Don’t mutate `refGeom.expt` in-place; always write the metadata clone under `sp.proc/idx-0000_sigma_metadata.expt` per docs/spec-db-workflow.md Stage Smoke policy.
- Keep manifest hashes deterministic: no relative paths, no timestamps in the hashed payloads, and ensure files are closed before hashing per MANIFEST-001.
- Avoid embedding metadata during pytest collection; the fixtures should assume files already exist and skip with actionable messaging when missing.
- Don’t relax sigma positivity or provenance assertions—PHYSICS-LOSS-004/005 require strict enforcement even in the new test.
- Never drop `AUTHORITATIVE_CMDS_DOC` when running the new pytest selector; every CI invocation must self-document commands.
- Treat pickled `.sigma_tiles.pkl` as binary; hash and copy via `shutil.copyfile` or equivalent, not text transforms.
- Keep the new README/docs under 100 cols and cite canonical commands; do not invent ad-hoc env vars for metadata smokes.
- Respect Environment Freeze: if dxtbx import fails while hashing/loading, log the minimal error and stop instead of installing packages.
- Ensure pytest logs and manifest snapshots land in the artifacts directory before finishing so Attempts History stays auditable.
- Preserve Stage smoke skips—if metadata assets are missing locally, the validation test should fail fast with clear remediation steps, not silently regenerate them.

## If Blocked
Capture the failing command + traceback in `plans/active/PHYSICS-LOSS-001/reports/2025-11-21T083500Z/blocked.log`, note whether `sp.proc/idx-0000_sigma_metadata.{expt,sigma_tiles.pkl}` existed (`ls -l` output), and append the blocker description plus remediation ideas to `docs/fix_plan.md` Attempts History before pausing the initiative.

## Findings Applied (Mandatory)
- PHYSICS-LOSS-004 — Loader constraints enforce `[panel, slow, fast]` shapes and positivity for sigma maps; manifest/test updates must keep those guards intact.
- PHYSICS-LOSS-005 — External_lookup tiles are the authoritative metadata source; the new pytest needs to assert `sigma_readout_provenance="external_lookup"` whenever metadata mode is active.
- MANIFEST-001 — Canonical fixtures require SHA256 verification before emitting manifests; reuse the same guard when hashing the metadata experiment and tiles.

## Pointers
- docs/fix_plan.md:14 — PHYSICS-LOSS-001 ledger + Attempts History context for this focus.
- plans/active/PHYSICS-LOSS-001/implementation.md:60 — Phase G checklist outlining G4/G5 manifest + CI validation tasks.
- docs/spec-db-core.md:32 — Variance/readout noise spec requiring strictly positive `[panel, slow, fast]` tensors.
- docs/spec-db-workflow.md:24 — Stage Smoke dataset policy governing metadata fixtures.
- docs/TESTING_GUIDE.md:80 — Sigma-map workflow section to update with manifest/validation instructions.
- docs/development/TEST_SUITE_INDEX.md:1 — Registry table where the new metadata validation selector must be documented.

## Next Up (optional)
1. After the manifest/CI gate lands, finish Phase G by wiring the fixture hash check into the GitHub workflow that currently runs the Stage smokes.

## Doc Sync Plan (Conditional)
- After the new pytest module is added, run `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only tests/sp_proc/test_sigma_metadata_fixture.py > plans/active/PHYSICS-LOSS-001/reports/2025-11-21T083500Z/collect_sigma_metadata_fixture.log`, then refresh `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` with the selector details once the implementation passes.

## Mapped Tests Guardrail
- `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only tests/sp_proc/test_sigma_metadata_fixture.py > plans/active/PHYSICS-LOSS-001/reports/2025-11-21T083500Z/collect_sigma_metadata_fixture.log`
