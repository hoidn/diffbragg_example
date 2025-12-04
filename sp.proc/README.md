# Sigma Metadata Fixtures

This directory stores the canonical sigma-readout assets used by Stage smoke tests
and DB-AT mapping selectors. The fixtures follow the normative variance and
metadata contracts in `docs/spec-db-core.md:32-68` (strict positivity and
`[panel, slow, fast]` ordering) plus the Stage Smoke dataset policy in
`docs/spec-db-workflow.md:24-45`.

## Assets

- `idx-0000_sigma_metadata.expt` — Clone of `refGeom.expt` with calibrated sigma
  tiles embedded in `imageset.external_lookup`.
- `idx-0000_sigma_metadata.sigma_tiles.pkl` — Pickled flex payload written next
  to the experiment for reproducible loading via dxtbx.
- `sigma_metadata_manifest.json` — Manifest produced by the embedding script
  (below) that captures the generator command, hash digests, and stats so CI can
  detect drift.
- `idx-0000_sigma_metadata.sigma_tiles.npy` — Convenience NumPy stack matching
  the pickle payload.

## Regenerating the fixtures

Run the embedding helper from the repository root so both the provenance report
and manifest capture a stable command line:

```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
python -m dbex.tools.embed_sigma_external_lookup \
  --expt refGeom.expt \
  --output sp.proc/idx-0000_sigma_metadata.expt \
  --expt-idx 0 \
  --sigma-value 3.0 \
  --report plans/active/PHYSICS-LOSS-001/reports/<timestamp>/sigma_metadata.json \
  --manifest sp.proc/sigma_metadata_manifest.json
```

The `--manifest` flag emits SHA256 hashes for the `.expt`, pickle tiles, and
JSON report plus the authoritative command. Stage smokes ingest the
`sp.proc/sigma_metadata_manifest.json` snapshot to prove the tiles still match
the refGeom detector layout.

## Validation

`tests/sp_proc/test_sigma_metadata_fixture.py` recomputes the manifest hashes,
loads `idx-0000_sigma_metadata.expt`, and calls
`dbex.data_load._load_external_lookup_sigma_map` to ensure the bridge would tag
`sigma_readout_provenance="external_lookup"` per PHYSICS-LOSS-005. The sigma
manifest and report are also copied into each loop’s
`plans/active/PHYSICS-LOSS-001/reports/<timestamp>/` directory so CI auditors
have the full metadata trail.
