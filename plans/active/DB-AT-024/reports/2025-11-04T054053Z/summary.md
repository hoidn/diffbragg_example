# 2025-11-04T054053Z — DB-AT-024 mapping consistency planning

## Key observations
- DB-AT-020/021/022/023 selectors are marked done with active tests, leaving mapping consistency (DB-AT-024) as the remaining workflow guardrail (`docs/spec-db-conformance.md:34-52`).
- Current pipeline only exposes zero-iteration forward outputs through `dbex.refine_one.run_nanobrag_backend`, which always writes HDF5 and hides intermediate tensors—tests need a reusable helper that returns arrays directly.
- Canonical assets (`refGeom.{expt,refl}`, `scaled.mtz`, `747_mask.pkl`, golden tensors under `tests/fixtures/golden_data/simple_cubic/`) are present in-repo, enabling acceptance coverage without environment changes.
- Parity utilities (`tests/fixtures/parity_loader.py`) already compute ROI correlation/localization; plan is to reuse them to avoid metric drift for DB_AT_024.

## Normative references consulted
- `docs/spec-db-conformance.md` — workflow integration profile and DB-AT-024 thresholds.
- `docs/forward_equivalence.md` — correlation/localization math and artifact expectations.
- `docs/spec-db-tracing.md` — diagnostics + artifact policy for parity/mapping investigations.
- `docs/development/TEST_SUITE_INDEX.md` — DB_AT_024 listed as Planned selector needing activation.

## Micro probes
```
$ ls -1 tests/fixtures
golden_data
parity_loader.py

$ ls -1 tests/fixtures/golden_data/simple_cubic
bragg_diffbragg.npy
bragg_panel_0.npy
bragg_torch.npy
loss_mask_panel_0.npy
manifest.json
metadata.json
target_panel_0.npy

$ find . -maxdepth 2 -name 'refGeom.*'
./refGeom.expt
./refGeom.refl

$ ls -1 scaled.mtz
scaled.mtz

$ ls -1 747_mask.pkl
747_mask.pkl
```

## Next actions
- Finalize Phase A-C plan in `implementation.md` and wire it into `docs/fix_plan.md`.
- Capture baseline `data - background` metrics via `DataLoad` probe to set expected ROI correlation/localization.
- Draft Do Now instructing Ralph to extract zero-iteration helper and author DB_AT_024 selector with mapped pytest/collect commands.
