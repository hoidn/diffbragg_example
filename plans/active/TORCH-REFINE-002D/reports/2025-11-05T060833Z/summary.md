### Turn Summary
Investigated Stage A perturbation by replaying refinement with nearest-neighbor HKL sampling to measure gate headroom.
HKL telemetry stayed 97.84% in-bounds but LBFGS improvement stalled at 0.22% and orientation deltas remained 0.0 because base misset is dropped when overrides are present.
Next: wire baseline misset into misset_deg_override and disable interpolation in the Stage A path so the deterministic perturbation can meet ≥5%.
Artifacts: plans/active/TORCH-REFINE-002D/reports/2025-11-05T060833Z/ (stage_a_probe.log)

#### One-off analysis
```bash
python - <<'PY'
import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['NANOBRAGG_DISABLE_COMPILE'] = '1'

from pathlib import Path
from argparse import Namespace
import numpy as np
import torch

from dbex.data_load import DataLoad
from dbex.nanobrag_bridge import prepare_refinement_inputs, build_structure_factor_grid
from dbex.nanobrag_refinement import run_nanobrag_refinement, RefinementConfig
from tests.dbex.test_torch_refine_smoke import create_perturbed_geometry
import nanobrag_torch.models.crystal as crystal_module

repo_root = Path('.').resolve()

args = Namespace(
    exptName=str(repo_root / 'refGeom.expt'),
    reflName=str(repo_root / 'refGeom.refl'),
    exptIdx=0,
    maskFile=str(repo_root / '747_mask.pkl'),
    mtzFile=str(repo_root / 'scaled.mtz'),
    mtzCol='F,SIGF'
)

if not Path(args.reflName).exists():
    raise SystemExit('refGeom assets missing')

DL = DataLoad(args)

trusted_masks = []
for pid in range(len(DL.Expt.detector)):
    panel = DL.Expt.detector[pid]
    image_size = panel.get_image_size()
    mask = np.ones(image_size[::-1], dtype=bool)
    trusted_masks.append(mask)

inputs = prepare_refinement_inputs(
    data=DL.data,
    background_image=DL.background_image,
    trusted_mask=trusted_masks,
    bbox=DL.bbox,
    pids=DL.pids,
    detector=DL.Expt.detector,
    adu_per_photon=None
)

hkl_grid, hkl_metadata = build_structure_factor_grid(
    indices=DL.F.indices(),
    amplitudes=DL.F.data(),
    device=torch.device('cpu')
)

perturbed_crystal, perturbed_detector, perturbed_beam = create_perturbed_geometry(
    DL.Expt.crystal, DL.Expt.detector, DL.Expt.beam
)

orig_init = crystal_module.Crystal.__init__

def patched_init(self, *args, **kwargs):
    orig_init(self, *args, **kwargs)
    self.interpolate = False

crystal_module.Crystal.__init__ = patched_init

config = RefinementConfig(
    device='cpu',
    dtype=torch.float32,
    history_size=10,
    max_iter=30,
    roi_sample_fraction=0.15,
    full_validation_interval=5,
    min_loss_improvement=0.05
)

try:
    bragg, telemetry = run_nanobrag_refinement(
        inputs=inputs,
        detector=perturbed_detector,
        beam=perturbed_beam,
        crystal=perturbed_crystal,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config
    )
finally:
    crystal_module.Crystal.__init__ = orig_init

initial_loss = telemetry.loss_trace_full[0][1]
final_loss = telemetry.loss_trace_full[-1][1]
improvement = (initial_loss - final_loss) / initial_loss
print('status', telemetry.status)
print('improvement', improvement)
print('orientation delta norm', telemetry.param_deltas['orientation_vec']['norm'])
print('misset_xyz_deg', telemetry.param_deltas['misset_xyz_deg']['final'])
PY
```

#### Outputs
```
status early_stop
improvement 0.0022166201111774027
orientation delta norm 0.0
misset_xyz_deg [0.0, 0.0, 0.0]
```

#### One-off analysis (baseline misset injection probe)
```bash
python - <<'PY'
import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['NANOBRAGG_DISABLE_COMPILE'] = '1'

from pathlib import Path
from argparse import Namespace
import numpy as np
import torch
from scitbx import matrix

from dbex.data_load import DataLoad
from dbex.nanobrag_bridge import prepare_refinement_inputs, build_structure_factor_grid
from dbex.nanobrag_refinement import run_nanobrag_refinement, RefinementConfig
import dbex.nanobrag_refinement as refine_mod
from tests.dbex.test_torch_refine_smoke import create_perturbed_geometry
import nanobrag_torch.models.crystal as crystal_module

repo_root = Path('.').resolve()

args = Namespace(
    exptName=str(repo_root / 'refGeom.expt'),
    reflName=str(repo_root / 'refGeom.refl'),
    exptIdx=0,
    maskFile=str(repo_root / '747_mask.pkl'),
    mtzFile=str(repo_root / 'scaled.mtz'),
    mtzCol='F,SIGF'
)

DL = DataLoad(args)
orig_crystal = DL.Expt.crystal
perturbed_crystal, perturbed_detector, perturbed_beam = create_perturbed_geometry(
    orig_crystal, DL.Expt.detector, DL.Expt.beam
)

U_orig = matrix.sqr(orig_crystal.get_U())
U_perturbed = matrix.sqr(perturbed_crystal.get_U())
U_delta = U_perturbed * U_orig.inverse()
quat = U_delta.r3_rotation_matrix_as_unit_quaternion()
base_misset_np = np.array(refine_mod.quaternion_to_xyz_euler(torch.tensor(quat, dtype=torch.float64))).astype(np.float32)

trusted_masks = []
for pid in range(len(DL.Expt.detector)):
    panel = DL.Expt.detector[pid]
    image_size = panel.get_image_size()
    mask = np.ones(image_size[::-1], dtype=bool)
    trusted_masks.append(mask)

inputs = prepare_refinement_inputs(
    data=DL.data,
    background_image=DL.background_image,
    trusted_mask=trusted_masks,
    bbox=DL.bbox,
    pids=DL.pids,
    detector=DL.Expt.detector,
    adu_per_photon=None
)

hkl_grid, hkl_metadata = build_structure_factor_grid(
    indices=DL.F.indices(),
    amplitudes=DL.F.data(),
    device=torch.device('cpu')
)

orig_init = crystal_module.Crystal.__init__
orig_quat_to_euler = refine_mod.quaternion_to_xyz_euler

def patched_init(self, *args, **kwargs):
    orig_init(self, *args, **kwargs)
    self.interpolate = False

base_misset_tensor = torch.tensor(base_misset_np, dtype=torch.float32)

def patched_quat_to_xyz(q: torch.Tensor) -> torch.Tensor:
    return orig_quat_to_euler(q) + base_misset_tensor.to(q.device, q.dtype)

crystal_module.Crystal.__init__ = patched_init
refine_mod.quaternion_to_xyz_euler = patched_quat_to_xyz

config = RefinementConfig(
    device='cpu',
    dtype=torch.float32,
    history_size=10,
    max_iter=30,
    roi_sample_fraction=0.15,
    full_validation_interval=5,
    min_loss_improvement=0.05
)

try:
    bragg, telemetry = run_nanobrag_refinement(
        inputs=inputs,
        detector=perturbed_detector,
        beam=perturbed_beam,
        crystal=perturbed_crystal,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config
    )
finally:
    crystal_module.Crystal.__init__ = orig_init
    refine_mod.quaternion_to_xyz_euler = orig_quat_to_euler

initial_loss = telemetry.loss_trace_full[0][1]
final_loss = telemetry.loss_trace_full[-1][1]
improvement = (initial_loss - final_loss) / initial_loss
print('status', telemetry.status)
print('improvement', improvement)
print('orientation delta norm', telemetry.param_deltas['orientation_vec']['norm'])
print('misset_xyz_deg', telemetry.param_deltas['misset_xyz_deg']['final'])
PY
```

#### Outputs
```
status early_stop
improvement 0.0020644160293241585
orientation delta norm 5.055732117398293e-07
misset_xyz_deg [2.2710346456733532e-06, 1.7051686427294044e-06, 1.499998927116394]
```

#### One-off analysis (perturbation amplitude sweep)
```bash
python - <<'PY'
import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['NANOBRAGG_DISABLE_COMPILE'] = '1'

from pathlib import Path
from argparse import Namespace
import numpy as np
import torch
from scitbx import matrix

from dbex.data_load import DataLoad
from dbex.nanobrag_bridge import prepare_refinement_inputs, build_structure_factor_grid
from dbex.nanobrag_refinement import run_nanobrag_refinement, RefinementConfig
import dbex.nanobrag_refinement as refine_mod
import nanobrag_torch.models.crystal as crystal_module

repo_root = Path('.').resolve()

args = Namespace(
    exptName=str(repo_root / 'refGeom.expt'),
    reflName=str(repo_root / 'refGeom.refl'),
    exptIdx=0,
    maskFile=str(repo_root / '747_mask.pkl'),
    mtzFile=str(repo_root / 'scaled.mtz'),
    mtzCol='F,SIGF'
)

DL = DataLoad(args)
orig_crystal = DL.Expt.crystal

from dxtbx.model import Crystal
from cctbx import uctbx
from scitbx import matrix as smatrix
import math

def create_stronger_perturbation(crystal):
    base_cell = crystal.get_unit_cell().parameters()
    perturbed_crystal = Crystal(
        real_space_a=crystal.get_real_space_vectors()[0],
        real_space_b=crystal.get_real_space_vectors()[1],
        real_space_c=crystal.get_real_space_vectors()[2],
        space_group=crystal.get_space_group()
    )

    perturbed_uc = uctbx.unit_cell((
        base_cell[0] * 1.05,
        base_cell[1] * 1.03,
        base_cell[2] * 1.03,
        base_cell[3],
        base_cell[4],
        base_cell[5]
    ))
    perturbed_crystal.set_unit_cell(perturbed_uc)

    misset_z_deg = 4.0
    misset_y_deg = 2.5
    rz = smatrix.sqr([
        math.cos(math.radians(misset_z_deg)), -math.sin(math.radians(misset_z_deg)), 0,
        math.sin(math.radians(misset_z_deg)),  math.cos(math.radians(misset_z_deg)), 0,
        0, 0, 1
    ])
    ry = smatrix.sqr([
        math.cos(math.radians(misset_y_deg)), 0, math.sin(math.radians(misset_y_deg)),
        0, 1, 0,
        -math.sin(math.radians(misset_y_deg)), 0, math.cos(math.radians(misset_y_deg))
    ])
    rotation = rz * ry
    U = smatrix.sqr(crystal.get_U())
    perturbed_crystal.set_U(rotation * U)
    return perturbed_crystal

perturbed_crystal = create_stronger_perturbation(orig_crystal)
perturbed_detector = DL.Expt.detector
perturbed_beam = DL.Expt.beam

U_orig = matrix.sqr(orig_crystal.get_U())
U_perturbed = matrix.sqr(perturbed_crystal.get_U())
U_delta = U_perturbed * U_orig.inverse()
quat = U_delta.r3_rotation_matrix_as_unit_quaternion()
base_misset_np = np.array(refine_mod.quaternion_to_xyz_euler(torch.tensor(quat, dtype=torch.float64))).astype(np.float32)

trusted_masks = []
for pid in range(len(DL.Expt.detector)):
    panel = DL.Expt.detector[pid]
    image_size = panel.get_image_size()
    mask = np.ones(image_size[::-1], dtype=bool)
    trusted_masks.append(mask)

inputs = prepare_refinement_inputs(
    data=DL.data,
    background_image=DL.background_image,
    trusted_mask=trusted_masks,
    bbox=DL.bbox,
    pids=DL.pids,
    detector=DL.Expt.detector,
    adu_per_photon=None
)

hkl_grid, hkl_metadata = build_structure_factor_grid(
    indices=DL.F.indices(),
    amplitudes=DL.F.data(),
    device=torch.device('cpu')
)

orig_init = crystal_module.Crystal.__init__
orig_quat_to_euler = refine_mod.quaternion_to_xyz_euler

def patched_init(self, *args, **kwargs):
    orig_init(self, *args, **kwargs)
    self.interpolate = False

base_misset_tensor = torch.tensor(base_misset_np, dtype=torch.float32)

def patched_quat_to_xyz(q: torch.Tensor) -> torch.Tensor:
    return orig_quat_to_euler(q) + base_misset_tensor.to(q.device, q.dtype)

crystal_module.Crystal.__init__ = patched_init
refine_mod.quaternion_to_xyz_euler = patched_quat_to_xyz

config = RefinementConfig(
    device='cpu',
    dtype=torch.float32,
    history_size=10,
    max_iter=30,
    roi_sample_fraction=0.15,
    full_validation_interval=5,
    min_loss_improvement=0.05
)

try:
    bragg, telemetry = run_nanobrag_refinement(
        inputs=inputs,
        detector=perturbed_detector,
        beam=perturbed_beam,
        crystal=perturbed_crystal,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        config=config
    )
finally:
    crystal_module.Crystal.__init__ = orig_init
    refine_mod.quaternion_to_xyz_euler = orig_quat_to_euler

initial_loss = telemetry.loss_trace_full[0][1]
final_loss = telemetry.loss_trace_full[-1][1]
improvement = (initial_loss - final_loss) / initial_loss
print('status', telemetry.status)
print('improvement', improvement)
print('orientation delta norm', telemetry.param_deltas['orientation_vec']['norm'])
print('misset_xyz_deg', telemetry.param_deltas['misset_xyz_deg']['final'])
PY
```

#### Outputs
```
status early_stop
improvement 0.0029230032499370433
orientation delta norm 6.267243861657334e-07
misset_xyz_deg [1.1971510502917226e-06, 2.4999964237213135, 4.000000476837158]
```
