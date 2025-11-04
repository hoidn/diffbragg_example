# DB-AT-021 Planning Snapshot
- Confirmed `747_mask.pkl` contains a single trusted-mask panel matching refGeom dimensions `(2527, 2463)` with True polarity (≈91.53% trusted coverage) to anchor acceptance-test expectations.
- Noted DataLoad currently lacks `trusted_mask` hydration despite `refine_one` consuming `DL.trusted_mask`, implying the upcoming implementation must wire mask loading + polarity guards alongside DB-AT-021 tests.
- Identified docs/spec references to drive assertions: `docs/spec-db-core.md:29-55`, `docs/spec-db-conformance.md:32-37`, `docs/dials_api.md:12-24`, and Testing Guide rows for DB_AT_021 (planned) requiring activation.

## One-off analysis — mask provenance probe (T1)
```python
from pathlib import Path
import pickle
from dials.array_family import flex
import numpy as np

mask_path = Path("747_mask.pkl")
mask = pickle.load(mask_path.open("rb"))

if isinstance(mask, flex.bool):
    panels = [mask]
elif isinstance(mask, tuple):
    panels = [m for m in mask]
else:
    raise TypeError(type(mask))

shapes = []
true_fractions = []
for panel_mask in panels:
    arr = panel_mask.as_numpy_array()
    shapes.append(arr.shape)
    true_fractions.append(float(arr.mean()))

print(f"panels={len(panels)}")
print(f"unique_shapes={sorted(set(shapes))}")
print(f"true_fraction=({true_fractions[0]:.6f})")
print(f"sample_false_pixels={np.count_nonzero(1-arr)}")
```

```
panels=1
unique_shapes=[(2527, 2463)]
true_fraction=(0.915327)
sample_false_pixels=527005
```
