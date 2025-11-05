### Turn Summary
Reproduced the Stage A smoke failure and captured telemetry showing LBFGS exits early because `log_scale` explodes to ~8.99e+01, tripping the gradient NaN/Inf guard.
Confirmed the best snapshot restores `log_scale≈4.29` while `RefinementInputs.global_scale_hint=62.66`, aligning with the spec’s warm-start guidance and proving the simulator is otherwise healthy.
Next: warm-start `log_scale` from the calibration hint, clamp the exponent before `torch.exp`, and rerun the smoke to verify ≥5% loss drop with telemetry.status="ok".
Artifacts: plans/active/TORCH-REFINE-001/reports/2025-11-05T013525Z/ (pytest_refine_smoke_fail.log)

#### One-off analysis
```python
from pathlib import Path
from argparse import Namespace
import numpy as np
from dbex.data_load import DataLoad
from dbex.nanobrag_bridge import prepare_refinement_inputs

repo_root = Path('.')
args = Namespace(
    exptName=str(repo_root / 'refGeom.expt'),
    reflName=str(repo_root / 'refGeom.refl'),
    exptIdx=0,
    maskFile=str(repo_root / '747_mask.pkl'),
    mtzFile=str(repo_root / 'scaled.mtz'),
    mtzCol='F,SIGF'
)
data = DataLoad(args)
detector = data.Expt.detector
trusted_masks = []
for pid in range(len(detector)):
    panel = detector[pid]
    image_size = panel.get_image_size()
    mask = np.ones(image_size[::-1], dtype=bool)
    trusted_masks.append(mask)
inputs = prepare_refinement_inputs(
    data=data.data,
    background_image=data.background_image,
    trusted_mask=trusted_masks,
    bbox=data.bbox,
    pids=data.pids,
    detector=detector,
    adu_per_photon=None,
)
mask = inputs.loss_mask
per_panel = mask.reshape((mask.shape[0], -1)).sum(axis=1)
print('n_panels', mask.shape[0])
print('nonzero panels', int((per_panel > 0).sum()))
print('min coverage', int(per_panel.min()), 'max coverage', int(per_panel.max()))
print('panel sums first10', per_panel[:10])
```
Output:
```
n_panels 1
nonzero panels 1
min coverage 13158 max coverage 13158
panel sums first10 [13158]
```
