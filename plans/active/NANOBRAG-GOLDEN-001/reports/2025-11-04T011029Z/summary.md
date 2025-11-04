# Loop Summary: 2025-11-04T011029Z

## Focus
NANOBRAG-GOLDEN-001 — Phase A4 detector geometry alignment for canonical DB-AT-001 tensors

## Key Observations
- Parity ROI sample (`reports/2025-11-04T011500Z/roi_triptychs/index.json`) still shows large misalignment: median_abs_offset=8 px, max_offset=15 px, indicating DIALS rotations alone did not fix torch peak drift.
- Stubbed DetectorConfig angles currently fed to `TorchDetector` reproduce fast/slow/normal vectors that disagree with dxtbx panel axes (Y/Z signs flipped), confirming our Euler conversion path is inconsistent with Torch's XYZ ordering.
- Deriving XYZ angles analytically from the column-stacked [fast, slow, normal] matrix (φ_y = −asin(R[2,0]), φ_x = atan2(R[2,1], R[2,2]), φ_z = atan2(R[1,0], R[0,0])) exactly reconstructs the dxtbx basis when reapplied via `angles_to_rotation_matrix`, so `create_detector_config` should switch to this formulation.
- Beam vector mismatch (`TorchDetector.beam_vector = [0,0,1]` vs `beam.get_unit_s0() = (0,0,-1)`) remains expected because Torch stores sample→source; no extra negation required per HKL-ORIENT-001.

## Micro probes
```bash
python plans/active/NANOBRAG-GOLDEN-001/bin/summarize_roi_offsets.py --index-json plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T011500Z/roi_triptychs/index.json
```
Output:
```
{
  "median_dy": 4.0,
  "median_dx": 4.0,
  "median_abs_offset": 8.0,
  "max_offset": 15,
  "n_samples": 18
}
```

## One-off analysis
### Offset direction scatter (T1)
```bash
python - <<'PY'
import json, statistics
from pathlib import Path
samples = json.loads(Path('plans/active/NANOBRAG-GOLDEN-001/reports/2025-11-04T011500Z/roi_triptychs/index.json').read_text())['samples']
dy = [s['diff_peak'][0] - s['torch_peak'][0] for s in samples if s['diff_peak'] and s['torch_peak']]
dx = [s['diff_peak'][1] - s['torch_peak'][1] for s in samples if s['diff_peak'] and s['torch_peak']]
print('median_dy_offset', statistics.median(dy))
print('median_dx_offset', statistics.median(dx))
print('sample_unique_offsets', sorted(set(zip(dy, dx)))[:5])
print('offset_counts', {d: dy.count(d) for d in sorted(set(dy))})
PY
```
Output:
```
median_dy_offset 3.5
median_dx_offset -2.0
sample_unique_offsets [(-4, -1), (-4, 4), (-3, -5), (-2, -5), (-2, 0)]
offset_counts {-4: 2, -3: 1, -2: 3, 3: 3, 4: 2, 5: 1, 6: 2, 7: 3, 8: 1}
```

### Torch vs dxtbx detector basis check (T1)
```bash
python - <<'PY'
from dxtbx.model.experiment_list import ExperimentListFactory
from dbex.nanobrag_bridge import create_detector_config
from nanobrag_torch.config import DetectorConfig as TorchDetectorConfig, DetectorConvention
from nanobrag_torch.models.detector import Detector as TorchDetector
import numpy as np

exp = ExperimentListFactory.from_json_file('refGeom.expt', check_format=False)[0]
panel = exp.detector[0]
beam = exp.beam
stub = create_detector_config(panel, beam)
cfg = TorchDetectorConfig(
    distance_mm=stub.distance_mm,
    pixel_size_mm=stub.pixel_size_mm,
    spixels=stub.spixels,
    fpixels=stub.fpixels,
    beam_center_s=stub.beam_center_s,
    beam_center_f=stub.beam_center_f,
    beam_center_source=stub.beam_center_source,
    detector_convention=DetectorConvention.DIALS,
    detector_rotx_deg=stub.detector_rotx_deg,
    detector_roty_deg=stub.detector_roty_deg,
    detector_rotz_deg=stub.detector_rotz_deg,
)

detector = TorchDetector(cfg, device='cpu')
fast = np.array(panel.get_fast_axis())
slow = np.array(panel.get_slow_axis())
normal = np.array(panel.get_normal())
print('torch_fast', detector.fdet_vec.numpy())
print('dxtbx_fast', fast)
print('fast_diff_norm', np.linalg.norm(detector.fdet_vec.numpy() - fast))
print('torch_slow', detector.sdet_vec.numpy())
print('dxtbx_slow', slow)
print('slow_diff_norm', np.linalg.norm(detector.sdet_vec.numpy() - slow))
print('torch_normal', detector.odet_vec.numpy())
print('dxtbx_normal', normal)
print('normal_diff_norm', np.linalg.norm(detector.odet_vec.numpy() - normal))
print('beam_vector', detector.beam_vector.numpy())
print('beam_unit_s0', beam.get_unit_s0())
PY
```
Output:
```
torch_fast [ 9.9999827e-01 -1.6894017e-03  7.8929449e-04]
dxtbx_fast (0.9999982614666334, 0.0016932224556383707, -0.000781064291071184)
fast_diff_norm 0.0037293662709881876
torch_slow [-0.00168554 -0.9999867  -0.00486554]
dxtbx_slow (0.0016894016506467187, -0.9999867300677044, -0.004866786471866984)
slow_diff_norm 0.0033749437031595714
torch_normal [ 7.9750386e-04  4.8641996e-03 -9.9998784e-01]
dxtbx_normal (-0.0007892944785418853, 0.004865458479493718, -0.9999878520902196)
normal_diff_norm 0.0015867988386511732
beam_vector [0. 0. 1.]
beam_unit_s0 (0.0, 0.0, -1.0)
```

### Analytical XYZ recovery (T1)
```bash
python - <<'PY'
import numpy as np
from dxtbx.model.experiment_list import ExperimentListFactory
from nanobrag_torch.utils.geometry import angles_to_rotation_matrix
import torch

exp = ExperimentListFactory.from_json_file('refGeom.expt', check_format=False)[0]
panel = exp.detector[0]
R = np.column_stack([
    panel.get_fast_axis(),
    panel.get_slow_axis(),
    panel.get_normal(),
])
phi_y = -np.arcsin(R[2, 0])
phi_x = np.arctan2(R[2, 1], R[2, 2])
phi_z = np.arctan2(R[1, 0], R[0, 0])
rot = angles_to_rotation_matrix(torch.tensor(phi_x), torch.tensor(phi_y), torch.tensor(phi_z)).numpy()
print('angles_deg', np.degrees([phi_x, phi_y, phi_z]))
print('reconstruction_error', np.linalg.norm(rot - R))
PY
```
Output:
```
angles_deg [-1.79721152e+02  4.47516920e-02  9.70145764e-02]
reconstruction_error 1.5775748900222573e-16
```
