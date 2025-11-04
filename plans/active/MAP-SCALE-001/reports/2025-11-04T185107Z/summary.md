# MAP-SCALE-001 Supervisor Analysis (2025-11-04T185107Z)

## Context
- Current DB_AT_024 run (2025-11-04T210000Z) still undershoots thresholds with calibrated DiffBragg metadata applied: corr≈0.019, localization≈1.1%. Diagnostics show `bragg_mean≈1.32e6` ADU while targets average 63 ADU despite refined MTZ + geometry.
- Raw simulator output (`diagnostics.bragg_raw_stats.mean≈2.3e-03`) is **2.35e4×** larger than the canonical torch baseline prior to post-sim scaling. Gate `N_cells` removal avoided a 3.2e5× blow-up but still leaves orders-of-magnitude mismatch.

## One-off analysis

### Sample clipping + crystal domain parity check
```bash
# Mirrors simulate_forward_once but enables both N_cells and beam_config sample clipping.
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
python - <<'PY'
import numpy as np
from pathlib import Path
import torch
from tests.fixtures.parity_loader import compute_parity_metrics
from dbex.data_load import DataLoad
from dbex.nanobrag_bridge import (
    prepare_refinement_inputs,
    load_calibration_metadata,
    load_refined_mtz,
    create_beam_config,
    create_crystal_config,
    create_detector_config,
    build_structure_factor_grid,
)

repo = Path('.')
fixtures = repo / 'tests' / 'fixtures' / 'golden_data' / 'simple_cubic'

dargs = type('Args', (), {
    'mtzFile': str(repo/'scaled.mtz'),
    'mtzCol': 'F,SIGF',
    'exptName': str(fixtures/'refined.expt'),
    'exptIdx': 0,
    'reflName': str(fixtures/'refined.refl'),
    'maskFile': str(repo/'747_mask.pkl'),
})()

load = DataLoad(dargs)
inputs = prepare_refinement_inputs(
    data=load.data,
    background_image=load.background_image,
    trusted_mask=load.trusted_mask,
    bbox=load.bbox,
    pids=load.pids,
    detector=load.detector,
)
indices, amps = load_refined_mtz(fixtures/'refined_structure_factors.mtz')
calib = load_calibration_metadata(fixtures/'config_torch.json')
beam_cfg = create_beam_config(load.beam, flux=calib['beam_flux'], beamsize_mm=calib['beamsize_mm'], exposure=calib['beam_exposure'])
crystal_cfg, _ = create_crystal_config(load.crystal, load.Expt, N_cells=calib['N_cells'], apply_n_cells=True)

from nanobrag_torch.models.detector import Detector as TorchDetector
from nanobrag_torch.models.crystal import Crystal as TorchCrystal
from nanobrag_torch.simulator import Simulator

device = torch.device('cpu')
hkl_grid, hkl_meta = build_structure_factor_grid(indices, amps, device=device)

bragg_raw = []
for panel_id, panel in enumerate(load.detector):
    det_cfg = create_detector_config(panel=panel, beam=load.beam, trusted_mask=inputs.trusted_mask[panel_id])
    if det_cfg.mask_array is not None and not isinstance(det_cfg.mask_array, torch.Tensor):
        det_cfg.mask_array = torch.tensor(det_cfg.mask_array, dtype=torch.float32, device=device)
    detector_model = TorchDetector(det_cfg, device=device)
    crystal_model = TorchCrystal(crystal_cfg, beam_config=beam_cfg, device=device)
    crystal_model.hkl_data = hkl_grid
    crystal_model.hkl_metadata = hkl_meta
    sim = Simulator(crystal=crystal_model, detector=detector_model, beam_config=beam_cfg, device=device)
    bragg_raw.append(sim.run().cpu().detach().numpy().astype(np.float32))

bragg_raw = np.stack(bragg_raw, axis=0)
bragg = bragg_raw * np.sqrt(calib['spot_scale_override'])
mask = inputs.loss_mask
metrics = compute_parity_metrics(bragg[0], inputs.target[0], loss_mask=mask[0])
print({
    'masked_mean': float(bragg[mask].mean()),
    'corr': float(metrics.correlation),
    'localization': float(metrics.localization),
    'sum_ratio': float(metrics.sum_ratio),
})
PY
```
Output:
```
{'masked_mean': 77.43122100830078, 'corr': 0.8112846521457935, 'localization': 1.0, 'sum_ratio': 1.2285727625133223}
```

## Findings
- Enabling **both** DiffBragg `N_cells` and beam sample clipping inside the torch bridge collapses the 2.35e4× raw-intensity gap: scaled Bragg mean falls to 77.4 ADU, matching the canonical dataset and hitting DB_AT_024 thresholds (corr≈0.81, localization=100%).
- Current production helper skips sample clipping (beam_config never reaches `Simulator`) and forces `apply_n_cells=False`, leaving raw output orders of magnitude too bright even after recent calibrations.
- Attempting to enable `N_cells` without beam sample clipping reproduces the 3.2e5× blow-up captured in SCALE-005; the guard should be lifted only in tandem with beam-config propagation.

## Recommendations
- Update `simulate_forward_once` to propagate `beam_config` into `nanobrag_torch.Simulator` and allow `create_crystal_config(..., apply_n_cells=True)` when calibration metadata includes domain counts. Maintain diagnostics for `n_cells_applied` to confirm the guard is active.
- After the plumbing change, rerun DB_AT_024; metrics should satisfy corr≥0.2 and localization≥0.90, allowing removal of the provisional failure message.
- Record the behavior change in `docs/findings.md` (SCALE-005 refinement) and sync testing docs once DB_AT_024 passes.
