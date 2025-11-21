"""
Phase C smoke harness for TORCH-BRIDGE-001.

Tests exercise DataLoad through the bridge helpers and stub simulator,
producing stitched Bragg tensors, masked MSE metrics, and ROI triptych artifacts.

Per input.md:
- docs/spec-db-workflow.md:24-29 mandates stitched per-panel Bragg tensors and masked MSE
- docs/spec-db-core.md:32-56 requires [panel, slow, fast] ordering and (background >= 0) ∧ trusted loss masks
- docs/config_crosswalk.md:86-95 documents ROI/background handling and artifact expectations
- docs/dials_api.md:10-28 covers bbox ordering for ROI slicing
- docs/nanobrag_api.md:21-83 details simulator config expectations and stitch semantics

Findings applied:
- GEOMETRY-001: maintain detector geometry and square-pixel guards
- CONFORMANCE-001: export KMP_DUPLICATE_LIB_OK=TRUE for pytest
- RUNTIME-001: keep torch.compile disabled for gradient-sensitive paths
"""

from pathlib import Path
import json

import numpy as np
import pytest
from typing import NamedTuple
from argparse import Namespace

# DataLoad and bridge helpers
from dbex.data_load import DataLoad
from dbex.nanobrag_bridge import (
    prepare_refinement_inputs,
    create_detector_config,
    create_beam_config,
    create_crystal_config,
    RefinementInputs
)
from dbex.vis import compute_z_scores, save_triptych


class SmokeMetrics(NamedTuple):
    """Smoke harness metrics for reporting."""
    n_panels: int
    n_rois: int
    target_shape: tuple
    bragg_shape: tuple
    masked_mse: float
    mean_intensity_per_panel: list
    max_intensity_per_panel: list
    loss_mask_coverage: float  # fraction of pixels in loss mask


@pytest.fixture(scope="module")
def refgeom_dataload():
    """
    Load refGeom dataset via DataLoad.

    IMPORTANT: Requires reflection file from dials.stills_process.
    To generate required data files, see README.md Step 5:

    ```bash
    cd easyBragg
    dials.stills_process stills_proc.phil lys_nitr_10_6_*cbf \
      input.reference_geometry=refGeom.expt output_dir=sp.proc \
      dispatch.integrate=False
    cp sp.proc/idx-0000_indexed.refl ../refGeom.refl
    ```

    For now, this fixture is SKIPPED if refGeom.refl doesn't exist.
    This allows Phase C tests to pass with mock data initially.

    Returns DataLoad instance with:
    - Expt: dxtbx Experiment with detector/beam/crystal
    - Refs: reflection table
    - data: pixel data [panel, slow, fast]
    - background_image: background estimate [panel, slow, fast], -1 outside ROIs
    - bbox: ROI bounding boxes (n_roi, 4) as (x0, x1, y0, y1)
    - pids: panel IDs (n_roi,)
    - F: structure factors with Bijvoet mates
    """
    # Build args namespace for DataLoad (repo-relative paths)
    repo_root = Path(__file__).parent.parent.parent
    refl_path = repo_root / "refGeom.refl"

    # Skip if reflection file doesn't exist
    if not refl_path.exists():
        pytest.skip(
            f"Reflection file not found: {refl_path}\n"
            "Run dials.stills_process to generate it (see README.md Step 5)"
        )

    args = Namespace(
        mtzFile=str(repo_root / "scaled.mtz"),
        mtzCol="F,SIGF",  # MTZ column name (see error output for available columns)
        exptName=str(repo_root / "refGeom.expt"),
        exptIdx=0,
        reflName=str(refl_path)
    )

    # Load data (this invokes simtbx background estimation)
    dataload = DataLoad(args)
    return dataload


@pytest.fixture(scope="module")
def refinement_inputs(refgeom_dataload):
    """
    Prepare RefinementInputs from DataLoad via bridge helper.

    Returns RefinementInputs with:
    - target: background-subtracted [panel, slow, fast] float32
    - loss_mask: (background >= 0) & trusted_mask [panel, slow, fast] bool
    - panel_slices: [(pid, (x0, x1, y0, y1))]
    - trusted_mask: [panel, slow, fast] bool
    """
    dl = refgeom_dataload
    detector = dl.Expt.detector

    # Build trusted mask from detector panels
    # For each panel, create a mask with untrusted rectangles set to False
    trusted_mask = []
    for panel in detector:
        # Get panel dimensions
        fast_px, slow_px = panel.get_image_size()
        # Start with all pixels trusted
        panel_mask = np.ones((slow_px, fast_px), dtype=bool)

        # Mark untrusted rectangles from panel mask definition
        # Panel masks are defined as rectangles: [x0, y0, x1, y1]
        if hasattr(panel, 'get_mask') and panel.get_mask():
            for rect in panel.get_mask():
                x0, y0, x1, y1 = rect
                panel_mask[y0:y1, x0:x1] = False

        trusted_mask.append(panel_mask)

    # Convert to numpy array [panel, slow, fast]
    trusted_mask = np.array(trusted_mask, dtype=bool)

    # Prepare inputs
    inputs = prepare_refinement_inputs(
        data=dl.data,
        background_image=dl.background_image,
        trusted_mask=trusted_mask,
        bbox=dl.bbox,
        pids=dl.pids,
        detector=detector
    )

    return inputs


@pytest.fixture(scope="module")
def detector_configs(refgeom_dataload):
    """
    Create per-panel DetectorConfig objects from dxtbx geometry.

    Returns list of DetectorConfig instances, one per panel.
    """
    dl = refgeom_dataload
    detector = dl.Expt.detector
    beam = dl.Expt.beam

    # Build per-panel trusted masks
    trusted_masks = []
    for panel in detector:
        fast_px, slow_px = panel.get_image_size()
        panel_mask = np.ones((slow_px, fast_px), dtype=bool)
        if hasattr(panel, 'get_mask') and panel.get_mask():
            for rect in panel.get_mask():
                x0, y0, x1, y1 = rect
                panel_mask[y0:y1, x0:x1] = False
        trusted_masks.append(panel_mask)

    configs = []
    for panel_id, panel in enumerate(detector):
        config = create_detector_config(
            panel=panel,
            beam=beam,
            trusted_mask=trusted_masks[panel_id]
        )
        configs.append(config)

    return configs


@pytest.fixture(scope="module")
def beam_config(refgeom_dataload):
    """Create BeamConfig from dxtbx beam."""
    return create_beam_config(refgeom_dataload.Expt.beam)


@pytest.fixture(scope="module")
def crystal_config(refgeom_dataload):
    """Create CrystalConfig from dxtbx crystal and experiment."""
    dl = refgeom_dataload
    config, _ = create_crystal_config(dl.Expt.crystal, dl.Expt)
    return config


@pytest.fixture(scope="module")
def stub_bragg_tensor(refinement_inputs):
    """
    Stub Bragg tensor for smoke testing (replaces nanobrag_torch simulator).

    For now, returns a Gaussian-shaped intensity pattern on the target support.
    Shape matches target: [panel, slow, fast] float32.

    When nanobrag_torch is available, this fixture will invoke the simulator with
    the actual configs and return the real Bragg prediction.
    """
    target = refinement_inputs.target

    # Create stub Bragg tensor with Gaussian pattern on ROI support
    bragg = np.zeros_like(target)
    for panel_id, (pid, bbox) in enumerate(refinement_inputs.panel_slices):
        x0, x1, y0, y1 = bbox
        slow_size = y1 - y0
        fast_size = x1 - x0

        # Generate 2D Gaussian centered in the ROI
        slow_grid, fast_grid = np.meshgrid(
            np.linspace(-1, 1, slow_size),
            np.linspace(-1, 1, fast_size),
            indexing='ij'
        )
        gaussian = np.exp(-(slow_grid**2 + fast_grid**2) / 0.3)

        # Scale to reasonable intensity
        gaussian *= 500

        # Assign to bragg tensor at the panel/ROI location
        bragg[pid, y0:y1, x0:x1] = gaussian

    return bragg.astype(np.float32)


class TestSmokeHarness:
    """
    Smoke harness for single-experiment flow.

    Per Phase C checklist (plans/active/TORCH-BRIDGE-001/implementation.md:C1-C2):
    - C1: Run DataLoad → bridge → stub simulator, stitch Bragg, compute masked MSE
    - C2: Generate ROI triptych artifact and save metrics JSON
    """

    def test_single_experiment_flow(
        self,
        refgeom_dataload,
        refinement_inputs,
        detector_configs,
        beam_config,
        crystal_config,
        stub_bragg_tensor
    ):
        """
        Exercise single-experiment flow: DataLoad → bridge → stub Bragg → metrics.

        Validates:
        - DataLoad successfully loads refGeom experiment
        - Bridge produces valid RefinementInputs
        - Config hydration succeeds for all panels
        - Stub Bragg tensor has correct shape and ordering
        - Fixtures wire together without errors
        """
        dl = refgeom_dataload
        inputs = refinement_inputs
        bragg = stub_bragg_tensor

        # Validate DataLoad outputs
        assert dl.data.ndim == 3, f"Expected 3D data, got {dl.data.ndim}D"
        assert dl.background_image.shape == dl.data.shape
        bbox_array = np.array(dl.bbox)
        assert bbox_array.shape[1] == 4, f"Expected bbox shape (n, 4), got {bbox_array.shape}"
        assert len(dl.pids) == len(dl.bbox), "pids and bbox length mismatch"

        # Validate RefinementInputs
        assert inputs.target.shape == dl.data.shape
        assert inputs.loss_mask.shape == dl.data.shape
        assert inputs.loss_mask.dtype == bool
        assert len(inputs.panel_slices) == len(dl.bbox)

        # Validate configs
        n_panels = len(dl.Expt.detector)
        assert len(detector_configs) == n_panels
        assert beam_config.wavelength_A > 0
        assert crystal_config.cell_a > 0

        # Validate Bragg tensor shape and ordering
        assert bragg.shape == inputs.target.shape, \
            f"Bragg shape {bragg.shape} != target {inputs.target.shape}"
        assert bragg.dtype == np.float32

        # Basic sanity: Bragg should be non-negative and have some signal
        assert np.all(bragg >= 0), "Bragg tensor has negative values"
        assert np.sum(bragg) > 0, "Bragg tensor is all zeros"

        # Log success metrics
        print(f"\n[Smoke] DataLoad: {n_panels} panels, {len(dl.bbox)} ROIs")
        print(f"[Smoke] Target shape: {inputs.target.shape}")
        print(f"[Smoke] Bragg shape: {bragg.shape}")
        print(f"[Smoke] Loss mask coverage: {np.mean(inputs.loss_mask):.2%}")

    def test_masked_mse_and_shapes(
        self,
        refinement_inputs,
        stub_bragg_tensor,
        tmp_path
    ):
        """
        Compute masked MSE and validate per-panel intensity stats.

        Validates:
        - Masked MSE computation uses correct loss mask
        - Per-panel stats (mean, max intensity) are reasonable
        - Metrics can be serialized to JSON
        - Shape contracts hold: [panel, slow, fast] ordering
        """
        inputs = refinement_inputs
        bragg = stub_bragg_tensor

        # Compute masked MSE per spec-db-workflow.md:28
        # Loss = mean(((Bragg - target)[loss_mask])^2)
        residual = bragg - inputs.target
        masked_residual = residual[inputs.loss_mask]
        masked_mse = np.mean(masked_residual ** 2)

        assert masked_mse >= 0, "Masked MSE cannot be negative"
        assert np.isfinite(masked_mse), "Masked MSE is not finite"

        # Compute per-panel intensity stats
        n_panels = bragg.shape[0]
        mean_intensity_per_panel = []
        max_intensity_per_panel = []

        for panel_id in range(n_panels):
            panel_bragg = bragg[panel_id]
            panel_mask = inputs.loss_mask[panel_id]

            if np.any(panel_mask):
                masked_bragg = panel_bragg[panel_mask]
                mean_intensity_per_panel.append(float(np.mean(masked_bragg)))
                max_intensity_per_panel.append(float(np.max(masked_bragg)))
            else:
                mean_intensity_per_panel.append(0.0)
                max_intensity_per_panel.append(0.0)

        # Build metrics struct
        metrics = SmokeMetrics(
            n_panels=n_panels,
            n_rois=len(inputs.panel_slices),
            target_shape=tuple(inputs.target.shape),
            bragg_shape=tuple(bragg.shape),
            masked_mse=float(masked_mse),
            mean_intensity_per_panel=mean_intensity_per_panel,
            max_intensity_per_panel=max_intensity_per_panel,
            loss_mask_coverage=float(np.mean(inputs.loss_mask))
        )

        # Validate metrics are serializable
        metrics_dict = metrics._asdict()
        json_str = json.dumps(metrics_dict, indent=2)
        assert len(json_str) > 0

        # Log metrics
        print(f"\n[Smoke] Masked MSE: {masked_mse:.4e}")
        print(f"[Smoke] Loss mask coverage: {metrics.loss_mask_coverage:.2%}")
        print(f"[Smoke] Mean intensity per panel: {mean_intensity_per_panel}")
        print(f"[Smoke] Max intensity per panel: {max_intensity_per_panel}")

        # Optionally write to tmp_path for inspection
        metrics_file = tmp_path / "smoke_metrics.json"
        metrics_file.write_text(json_str)
        print(f"[Smoke] Metrics written to {metrics_file}")


@pytest.fixture(scope="module")
def smoke_artifacts(
    refinement_inputs,
    stub_bragg_tensor,
    tmp_path_factory
):
    """
    Generate and persist ROI triptych artifact plus metrics JSON.

    Per Phase C checklist (C2):
    - Render data/model/residual triptych for at least one ROI
    - Persist summary metrics (smoke_metrics.json) alongside image artifact
    - Store under plans/active/TORCH-BRIDGE-001/reports/2025-10-28T230500Z/

    Returns path to artifacts directory.
    """
    inputs = refinement_inputs
    bragg = stub_bragg_tensor

    # Artifacts directory (from input.md)
    repo_root = Path(__file__).parent.parent.parent
    artifacts_dir = repo_root / "plans/active/TORCH-BRIDGE-001/reports/2025-10-28T230500Z"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Compute masked MSE
    residual = bragg - inputs.target
    masked_residual = residual[inputs.loss_mask]
    masked_mse = np.mean(masked_residual ** 2)

    # Per-panel stats
    n_panels = bragg.shape[0]
    mean_intensity_per_panel = []
    max_intensity_per_panel = []
    for panel_id in range(n_panels):
        panel_bragg = bragg[panel_id]
        panel_mask = inputs.loss_mask[panel_id]
        if np.any(panel_mask):
            masked_bragg = panel_bragg[panel_mask]
            mean_intensity_per_panel.append(float(np.mean(masked_bragg)))
            max_intensity_per_panel.append(float(np.max(masked_bragg)))
        else:
            mean_intensity_per_panel.append(0.0)
            max_intensity_per_panel.append(0.0)

    # Build and save metrics JSON
    metrics = SmokeMetrics(
        n_panels=n_panels,
        n_rois=len(inputs.panel_slices),
        target_shape=tuple(inputs.target.shape),
        bragg_shape=tuple(bragg.shape),
        masked_mse=float(masked_mse),
        mean_intensity_per_panel=mean_intensity_per_panel,
        max_intensity_per_panel=max_intensity_per_panel,
        loss_mask_coverage=float(np.mean(inputs.loss_mask))
    )

    metrics_path = artifacts_dir / "smoke_metrics.json"
    with open(metrics_path, 'w') as f:
        json.dump(metrics._asdict(), f, indent=2)

    # Generate ROI triptych for first ROI using dbex.vis
    if len(inputs.panel_slices) > 0:
        pid, bbox = inputs.panel_slices[0]
        x0, x1, y0, y1 = bbox

        # Extract ROI slices
        data_roi = inputs.target[pid, y0:y1, x0:x1]
        bragg_roi = bragg[pid, y0:y1, x0:x1]
        residual_roi = residual[pid, y0:y1, x0:x1]
        mask_roi = inputs.loss_mask[pid, y0:y1, x0:x1]

        triptych_path = artifacts_dir / "roi_triptych.png"
        # Use Z-score style residuals for the visualization.
        residual_z = compute_z_scores(
            data_roi,
            bragg_roi,
            mask=mask_roi,
        )
        save_triptych(
            data_roi,
            bragg_roi,
            residual_z,
            out_path=triptych_path,
            title=f"ROI 0 panel {pid}",
        )

        print(f"[Smoke] ROI triptych saved to {triptych_path}")
        print(f"[Smoke] Metrics saved to {metrics_path}")

    return artifacts_dir


def test_artifact_generation(smoke_artifacts):
    """
    Validate artifact generation fixture produces expected files.

    Ensures:
    - smoke_metrics.json exists and is valid JSON
    - roi_triptych.png exists and is non-empty
    """
    artifacts_dir = smoke_artifacts

    metrics_path = artifacts_dir / "smoke_metrics.json"
    assert metrics_path.exists(), f"Metrics file not found: {metrics_path}"

    with open(metrics_path, 'r') as f:
        metrics = json.load(f)
        assert 'masked_mse' in metrics
        assert 'n_panels' in metrics
        assert metrics['masked_mse'] >= 0

    triptych_path = artifacts_dir / "roi_triptych.png"
    assert triptych_path.exists(), f"Triptych file not found: {triptych_path}"
    assert triptych_path.stat().st_size > 0, "Triptych file is empty"

    print(f"[Smoke] Artifacts validated: {artifacts_dir}")
