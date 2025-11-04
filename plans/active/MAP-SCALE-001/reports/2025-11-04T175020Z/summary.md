# MAP-SCALE-001 Supervisor Analysis (2025-11-04T175020Z)

## One-off analysis

### DiffBragg vs target alignment probe
```
python - <<'PY'
import numpy as np
from pathlib import Path
from tests.fixtures.parity_loader import compute_parity_metrics

root = Path('tests/fixtures/golden_data/simple_cubic')
target = np.load(root/'target_panel_0.npy')
diffbragg = np.load(root/'bragg_diffbragg.npy')
mask = np.load(root/'loss_mask_panel_0.npy').astype(bool)
if diffbragg.ndim == 3 and diffbragg.shape[0] == 1:
    diffbragg = diffbragg[0]
metrics = compute_parity_metrics(diffbragg, target, loss_mask=mask)
print('DiffBragg vs target metrics:')
print(f'  correlation={metrics.correlation:.4f}')
print(f'  localization={metrics.localization:.2f}')
print(f'  sum_ratio={metrics.sum_ratio:.4f}')
print(f'  rmse={metrics.rmse:.4f}')
print(f'  masked_pixels={metrics.n_pixels}')
PY
```
Output:
```
DiffBragg vs target metrics:
  correlation=0.8173
  localization=1.00
  sum_ratio=1.1123
  rmse=574.3243
  masked_pixels=13086
```

### simulate_forward_once vs canonical torch probe
```
python - <<'PY'
import numpy as np
from pathlib import Path
from tests.fixtures.parity_loader import compute_parity_metrics
from dbex.data_load import DataLoad
from dbex.nanobrag_bridge import (
    prepare_refinement_inputs,
    simulate_forward_once,
    load_calibration_metadata,
    load_refined_mtz,
)
import argparse

repo = Path('.')
fixtures = repo / 'tests' / 'fixtures' / 'golden_data' / 'simple_cubic'

args = argparse.Namespace(
    mtzFile=str(repo/'scaled.mtz'),
    mtzCol='F,SIGF',
    exptName=str(fixtures/'refined.expt'),
    exptIdx=0,
    reflName=str(fixtures/'refined.refl'),
    maskFile=str(repo/'747_mask.pkl'),
)

dl = DataLoad(args)
inputs = prepare_refinement_inputs(
    data=dl.data,
    background_image=dl.background_image,
    trusted_mask=dl.trusted_mask,
    bbox=dl.bbox,
    pids=dl.pids,
    detector=dl.detector,
    adu_per_photon=None,
)
calibration = load_calibration_metadata(fixtures/'config_torch.json')
indices, amps = load_refined_mtz(fixtures/'refined_structure_factors.mtz')

bragg, diag = simulate_forward_once(
    inputs=inputs,
    detector=dl.detector,
    beam=dl.beam,
    crystal=dl.crystal,
    experiment=dl.Expt,
    hkl_indices=indices,
    hkl_amplitudes=amps,
    spot_scale_override=calibration['spot_scale_override'],
    device='cpu',
)

canonical = np.load(fixtures/'bragg_torch.npy')
if canonical.ndim == 3 and canonical.shape[0] == 1:
    canonical = canonical[0]

mask = inputs.loss_mask[0]
metrics = compute_parity_metrics(bragg[0], canonical, loss_mask=mask)
print('Torch simulate_forward_once vs canonical bragg_torch metrics:')
print(f"  corr={metrics.correlation:.6f}")
print(f"  sum_ratio={metrics.sum_ratio:.6e}")
print(f"  rmse={metrics.rmse:.3f}")
print(f"  diag_bragg_mean={diag['bragg_stats']['mean']:.6e}")
print(f"  canonical_mean={float(canonical[mask].mean()):.6e}")
print(f"  mask_pixels={metrics.n_pixels}")
PY
```
Output (warnings trimmed):
```
Torch simulate_forward_once vs canonical bragg_torch metrics:
  corr=0.062665
  sum_ratio=2.347877e+04
  rmse=6037171.920
  diag_bragg_mean=1.318974e+06
  canonical_mean=7.747556e+01
  mask_pixels=13084
```

## Takeaways
- DiffBragg refined simulation already correlates 0.817 with `data - background`; DB_AT_024 failure stems from the nanobrag bridge, not the reference dataset.
- `simulate_forward_once` output diverges sharply from the canonical `bragg_torch.npy` despite using refined structure factors, geometry, and calibration metadata; correlation stays at 0.063 with a ~2.3e4 intensity ratio.
- Canonical generator injects beam flux/exposure, beamsize, and crystal `N_cells` into nanobrag_torch configs (see `config_torch.json`), but the runtime bridge still constructs minimalist configs, so simulator physics do not match the calibrated capture.

