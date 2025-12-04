### Turn Summary (Galph — 2025-12-29T010000Z)

Stage A baseline telemetry + DB-AT wiring landed last loop, so the remaining blocker on the Problems Ledger item “Freeze plan-local probe scripts…” is the set of other shadow pipelines cataloged in `probe_inventory.md`. The highest-risk holdout is `plans/active/PHYSICS-LOSS-001/bin/embed_sigma_external_lookup.py` (≈250 LOC) because every metadata-backed smoke/DB-AT selector still depends on this plan-local script to clone experiments and inject sigma tiles.

**Focus decision**
- Continue ARCH-PROBE-FREEZE-001, Phase B — target the sigma embedding script next so metadata fixtures/telemetry move under owner control.
- Promote the helper into `dbex/tools/embed_sigma_external_lookup.py` (new CLI + helpers for ExperimentList cloning, sigma map loading, and manifest/report emission). The plan-local script will shrink to a 2-line shim that calls the owner tool.
- Update docs/tests that reference the old path (Testing Guide §1.4, `sp.proc/README.md`, skip hints in `tests/conftest.py`, `tests/dbex/test_mapping_consistency.py`, `tests/dbex/test_artifact_parity.py`, `tests/dbex/test_torch_refine_smoke.py`, etc.) so operators invoke the production CLI (`python -m dbex.tools.embed_sigma_external_lookup`).

**Validation expectations**
- Re-run `pytest -vv tests/sp_proc/test_sigma_metadata_fixture.py` to prove the fixture governance harness still loads the regenerated experiments + manifest.
- Re-run the Stage A metadata smoke selector (small detector acceptable) with `DBEX_SMOKE_SIGMA_SOURCE=metadata` to prove Stage A still reports `sigma_readout_provenance="external_lookup"` after the tool migration.

Artifacts for the upcoming implementation loop will live under this directory alongside updated plan/docs snippets once Ralph lands the code.
