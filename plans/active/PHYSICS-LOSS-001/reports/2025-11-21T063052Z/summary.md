### Turn Summary
Scoped Phase F so sigma_readout tensors can come straight from DIALS metadata, updating docs/fix_plan, the implementation plan, input.md, and findings with the external-lookup helper requirements.
Reconfirmed the current refGeom experiments expose zero `external_lookup` tiles and outlined tests/docs so Ralph can implement the helper + provenance plumbing with clear validation gates.
Next: Ralph builds the external-lookup ingestion helper, updates `_resolve_sigma_readout` provenance, refreshes docs/tests, and captures the mapped pytest logs under this report directory.
Artifacts: plans/active/PHYSICS-LOSS-001/reports/2025-11-21T063052Z/ (summary.md)

#### One-off analysis — external_lookup tiles
```bash
python - <<'PY'
from dxtbx.model import ExperimentList
el = ExperimentList.from_file('sp.proc/idx-0000_refined.expt')
expt = el[0]
imageset = expt.imageset
lookup = imageset.external_lookup
print('Has gain data:', bool(getattr(lookup.gain, 'data', None)))
print('Has pedestal data:', bool(getattr(lookup.pedestal, 'data', None)))
print('Has mask data:', bool(getattr(lookup.mask, 'data', None)))
print('Has dark data:', hasattr(lookup, 'dark') and bool(getattr(lookup.dark, 'data', None)))
print('lookup attrs:', [name for name in dir(lookup) if not name.startswith('_')])
PY
```
Output:
```
Has gain data: False
Has pedestal data: False
Has mask data: False
Has dark data: False
lookup attrs: ['dx', 'dy', 'gain', 'mask', 'pedestal']
```

#### One-off analysis — ImageDouble tile mechanics
```bash
python - <<'PY'
from dxtbx_imageset_ext import ExternalLookupItemDouble
from dxtbx_format_image_ext import ImageDouble, ImageTileDouble
from scitbx.array_family import flex
item = ExternalLookupItemDouble()
item.filename = 'sigma.h5'
img = ImageDouble()
arr = flex.double(range(6))
arr.reshape(flex.grid(2, 3))
img.append(ImageTileDouble(arr))
item.data = img
print('n_tiles', item.data.n_tiles())
tile = item.data.tile(0)
print('tile data type', type(tile.data()))
print('tile data shape', tile.data().accessor().all())
PY
```
Output:
```
n_tiles 1
tile data type <class 'scitbx_array_family_flex_ext.double'>
tile data shape (2, 3)
```
