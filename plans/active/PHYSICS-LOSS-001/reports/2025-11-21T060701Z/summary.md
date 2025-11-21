### Turn Summary
Rescoped PHYSICS-LOSS-001 after confirming the sigma guard already shipped and that `_resolve_sigma_readout` never sees calibrated maps because DataLoad never exposes one.
Updated `docs/fix_plan.md`, the implementation plan, and `input.md` with Phase E deliverables plus a Do Now that adds a `--sigma-map` loader, CLI regression, helper unit tests, and doc/test-index sync.
Recorded evidence that the refGeom experiments’ `external_lookup.{gain,pedestal,mask}` slots report zero tiles, so future calibrated noise must come from explicit assets.
Next: Ralph implements the calibrated-map ingestion path and reruns the mapped CLI + helper pytest selectors before refreshing the Testing Guide entries.
Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T060701Z/ (summary.md)

#### One-off analysis — Panel metadata & external lookups
```bash
python - <<'PY'
from dxtbx.model import ExperimentList
el = ExperimentList.from_file('sp.proc/idx-0000_refined.expt')
expt = el[0]
panel = expt.detector[0]
print('Panel gain:', panel.get_gain())
print('Panel pedestal:', panel.get_pedestal())
print('Panel trusted_range:', panel.get_trusted_range())
imageset = expt.imageset
for name in ('gain', 'pedestal', 'mask'):
    lookup = getattr(imageset.external_lookup, name)
    tiles = len(lookup.data) if lookup and lookup.data is not None else 0
    print(f'external_lookup.{name} tiles:', tiles)
PY
```
Output:
```
Panel gain: 1.0
Panel pedestal: 0.0
Panel trusted_range: (0.0, 1009797.0)
external_lookup.gain tiles: 0
external_lookup.pedestal tiles: 0
external_lookup.mask tiles: 0
```
