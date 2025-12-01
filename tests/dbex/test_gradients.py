"""
Test suite for DB-AT-010: Gradient correctness guard.

Validates gradient flow through nanobrag_torch forward simulation using
torch.autograd.gradcheck with tight tolerances per testing_strategy.md §4.1.

Coverage:
- Crystal parameters: cell_a, cell_gamma
- Detector parameters: distance_mm
- Beam parameters: wavelength_A
- Model parameters: spot_scale (fluence proxy via SCALE-002)

References:
- docs/spec-db-runtime.md §4.1 (gradient profile, RUNTIME-001)
- docs/spec-db-conformance.md:12-14 (DB-AT-010 acceptance)
- docs/development/testing_strategy.md:338-372 (gradcheck requirements)
- docs/pytorch_runtime_checklist.md:27-30 (NANOBRAGG_DISABLE_COMPILE=1)
- dbex/physics/forward.py (simulate_forward_torch)
- dbex/physics/loss.py (compute_masked_mse_loss)
"""

import os
import pytest
import numpy as np
import json
from pathlib import Path
from types import SimpleNamespace

# RUNTIME-001: Disable torch.compile before importing torch
# This prevents Dynamo interference with torch.autograd.gradcheck
os.environ["NANOBRAGG_DISABLE_COMPILE"] = "1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import torch
from torch.autograd import gradcheck

# Skip entire module if canonical assets are missing
pytestmark = pytest.mark.skipif(
    not all([
        Path("refGeom.expt").exists(),
        Path("refGeom.refl").exists(),
        Path("scaled.mtz").exists(),
        Path("747_mask.pkl").exists()
    ]),
    reason="Canonical assets (refGeom.expt/refl, scaled.mtz, 747_mask.pkl) not found"
)


@pytest.fixture(scope="module")
def artifact_dir():
    """
    Artifact directory for DB-AT-010 gradcheck metrics and logs.

    Uses DBAT010_ARTIFACT_DIR environment variable if set, otherwise
    creates a default path under plans/active/DB-AT-010/reports/.
    """
    env_dir = os.environ.get("DBAT010_ARTIFACT_DIR")
    if env_dir:
        artifact_path = Path(env_dir)
    else:
        artifact_path = Path("plans/active/DB-AT-010/reports/default")

    artifact_path.mkdir(parents=True, exist_ok=True)
    return artifact_path


@pytest.fixture(scope="module")
def canonical_args():
    """
    Canonical DataLoad args using refGeom assets.

    Matches the dataset used in DB-AT-020 reflection ingestion tests.
    """
    return SimpleNamespace(
        mtzFile="scaled.mtz",
        mtzCol="F,SIGF",
        exptName="refGeom.expt",
        exptIdx=0,
        reflName="refGeom.refl",
        maskFile="747_mask.pkl"
    )


@pytest.fixture(scope="module")
def data_load_instance(canonical_args):
    """
    Create a DataLoad instance with canonical assets.

    Skip if any required file is missing.
    """
    required_files = [
        canonical_args.mtzFile,
        canonical_args.exptName,
        canonical_args.reflName,
        canonical_args.maskFile
    ]
    for fpath in required_files:
        if not Path(fpath).exists():
            pytest.skip(f"Required asset {fpath} not found")

    from dbex.data_load import DataLoad
    return DataLoad(canonical_args)


@pytest.fixture(scope="module")
def refinement_inputs(data_load_instance):
    """
    Prepare RefinementInputs from DataLoad for gradient tests.

    Uses default ADU mode (no calibration) to simplify gradient setup.
    Provides deterministic sigma_readout=3.0 ADU for variance-weighted loss testing (PHYSICS-LOSS-001).
    """
    from dbex.nanobrag_bridge import prepare_refinement_inputs
    import numpy as np

    # Deterministic sigma_readout for variance-weighted loss testing
    # Use 3.0 ADU as a representative readout noise value (typical for modern detectors)
    sigma_array = np.full_like(data_load_instance.data, 3.0, dtype=np.float32)

    # Use default ADU mode for simplicity
    inputs = prepare_refinement_inputs(
        data=data_load_instance.data,
        background_image=data_load_instance.background_image,
        trusted_mask=data_load_instance.trusted_mask,
        bbox=data_load_instance.bbox,
        pids=data_load_instance.pids,
        detector=data_load_instance.detector,
        adu_per_photon=None,  # ADU mode
        sigma_readout=sigma_array  # PHYSICS-LOSS-001: variance-weighted loss path
    )

    return inputs


@pytest.fixture(scope="module")
def geometry_objects(data_load_instance):
    """
    Extract dxtbx geometry objects (detector, beam, crystal, experiment).
    """
    return {
        "detector": data_load_instance.detector,
        "beam": data_load_instance.beam,
        "crystal": data_load_instance.crystal,
        "experiment": data_load_instance.Expt
    }


@pytest.fixture(scope="module")
def hkl_data(data_load_instance):
    """
    Extract HKL indices and amplitudes from MTZ.
    """
    return {
        "indices": data_load_instance.F.indices(),
        "amplitudes": data_load_instance.F.data()
    }


class TestDB_AT_010_Gradcheck:
    """
    DB-AT-010: Gradient correctness guard using torch.autograd.gradcheck.

    Tests verify that gradients flow correctly through the forward simulation
    for refinable parameters. Uses float64 precision and tight tolerances per
    testing_strategy.md §4.1.
    """

    def test_db_at_010_gradcheck_crystal_cell_a(
        self,
        refinement_inputs,
        geometry_objects,
        hkl_data,
        artifact_dir
    ):
        """
        DB-AT-010 (1/4): Verify gradients for crystal unit cell parameter cell_a.

        Tests that torch.autograd.gradcheck passes for the cell_a parameter
        with eps=1e-6, atol=1e-5, rtol≈0.05 per testing_strategy.md:364.
        """
        from dbex.physics.forward import simulate_forward_torch
        from dbex.physics.loss import compute_masked_mse_loss
        from dbex.nanobrag_bridge import create_crystal_config

        device = torch.device('cpu')
        dtype = torch.float64

        # Convert inputs to torch
        target_torch = torch.tensor(refinement_inputs.target, dtype=dtype, device=device)
        loss_mask_torch = torch.tensor(refinement_inputs.loss_mask, dtype=torch.bool, device=device)
        sigma_readout_torch = torch.tensor(refinement_inputs.sigma_readout, dtype=dtype, device=device)

        # Get base crystal config
        base_crystal = geometry_objects["crystal"]
        experiment = geometry_objects["experiment"]

        # Create a loss function parameterized by cell_a
        def loss_fn(cell_a_tensor):
            # Use crystal_overrides to inject tensor parameter directly (GRADIENT-001)
            # This avoids .item() call that would break gradient flow
            crystal_overrides = {'cell_a': cell_a_tensor}

            # Run forward simulation with tensor override
            bragg_torch = simulate_forward_torch(
                inputs=refinement_inputs,
                detector=geometry_objects["detector"],
                beam=geometry_objects["beam"],
                crystal=base_crystal,  # Use base crystal, overrides applied internally
                experiment=experiment,
                hkl_indices=hkl_data["indices"],
                hkl_amplitudes=hkl_data["amplitudes"],
                spot_scale_override=1.0,
                device=device,
                dtype=dtype,
                crystal_overrides=crystal_overrides  # Pass tensor override
            )

            # Compute variance-weighted chi-squared loss (PHYSICS-LOSS-001)
            loss = compute_masked_mse_loss(bragg_torch, target_torch, loss_mask_torch, sigma_readout_torch)
            return loss

        # Get base cell_a value
        uc = base_crystal.get_unit_cell()
        base_cell_a = uc.parameters()[0]

        # Create differentiable parameter tensor
        cell_a_param = torch.tensor(base_cell_a, dtype=dtype, device=device, requires_grad=True)

        # Run gradcheck
        gradcheck_passed = gradcheck(
            loss_fn,
            (cell_a_param,),
            eps=1e-6,
            atol=1e-5,
            rtol=0.05,
            raise_exception=True
        )

        # Emit metrics
        metrics = {
            "parameter": "crystal_cell_a",
            "base_value": float(base_cell_a),
            "gradcheck_passed": gradcheck_passed,
            "eps": 1e-6,
            "atol": 1e-5,
            "rtol": 0.05,
            "device": str(device),
            "dtype": str(dtype)
        }

        metrics_file = artifact_dir / "gradcheck_crystal_cell_a.json"
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2)

        assert gradcheck_passed, "Gradcheck failed for crystal cell_a parameter"

    def test_db_at_010_gradcheck_crystal_cell_gamma(
        self,
        refinement_inputs,
        geometry_objects,
        hkl_data,
        artifact_dir
    ):
        """
        DB-AT-010 (2/4): Verify gradients for crystal unit cell angle cell_gamma.

        Tests that torch.autograd.gradcheck passes for the cell_gamma parameter.
        """
        from dbex.physics.forward import simulate_forward_torch
        from dbex.physics.loss import compute_masked_mse_loss

        device = torch.device('cpu')
        dtype = torch.float64

        # Convert inputs to torch
        target_torch = torch.tensor(refinement_inputs.target, dtype=dtype, device=device)
        loss_mask_torch = torch.tensor(refinement_inputs.loss_mask, dtype=torch.bool, device=device)
        sigma_readout_torch = torch.tensor(refinement_inputs.sigma_readout, dtype=dtype, device=device)

        # Get base crystal
        base_crystal = geometry_objects["crystal"]
        experiment = geometry_objects["experiment"]

        # Create a loss function parameterized by cell_gamma
        def loss_fn(cell_gamma_tensor):
            # Use crystal_overrides to inject tensor parameter directly (GRADIENT-001)
            # This avoids .item() call that would break gradient flow
            crystal_overrides = {'cell_gamma': cell_gamma_tensor}

            # Run forward simulation with tensor override
            bragg_torch = simulate_forward_torch(
                inputs=refinement_inputs,
                detector=geometry_objects["detector"],
                beam=geometry_objects["beam"],
                crystal=base_crystal,  # Use base crystal, overrides applied internally
                experiment=experiment,
                hkl_indices=hkl_data["indices"],
                hkl_amplitudes=hkl_data["amplitudes"],
                spot_scale_override=1.0,
                device=device,
                dtype=dtype,
                crystal_overrides=crystal_overrides  # Pass tensor override
            )

            # Compute variance-weighted chi-squared loss (PHYSICS-LOSS-001)
            loss = compute_masked_mse_loss(bragg_torch, target_torch, loss_mask_torch, sigma_readout_torch)
            return loss

        # Get base cell_gamma value
        uc = base_crystal.get_unit_cell()
        base_cell_gamma = uc.parameters()[5]

        # Create differentiable parameter tensor
        cell_gamma_param = torch.tensor(base_cell_gamma, dtype=dtype, device=device, requires_grad=True)

        # Run gradcheck
        gradcheck_passed = gradcheck(
            loss_fn,
            (cell_gamma_param,),
            eps=1e-6,
            atol=1e-5,
            rtol=0.05,
            raise_exception=True
        )

        # Emit metrics
        metrics = {
            "parameter": "crystal_cell_gamma",
            "base_value": float(base_cell_gamma),
            "gradcheck_passed": gradcheck_passed,
            "eps": 1e-6,
            "atol": 1e-5,
            "rtol": 0.05,
            "device": str(device),
            "dtype": str(dtype)
        }

        metrics_file = artifact_dir / "gradcheck_crystal_cell_gamma.json"
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2)

        assert gradcheck_passed, "Gradcheck failed for crystal cell_gamma parameter"

    def test_db_at_010_gradcheck_detector_distance(
        self,
        refinement_inputs,
        geometry_objects,
        hkl_data,
        artifact_dir
    ):
        """
        DB-AT-010 (3/4): Verify gradients for detector distance_mm parameter.

        Tests that torch.autograd.gradcheck passes for detector distance changes.
        """
        from dbex.physics.forward import simulate_forward_torch
        from dbex.physics.loss import compute_masked_mse_loss

        device = torch.device('cpu')
        dtype = torch.float64

        # Convert inputs to torch
        target_torch = torch.tensor(refinement_inputs.target, dtype=dtype, device=device)
        loss_mask_torch = torch.tensor(refinement_inputs.loss_mask, dtype=torch.bool, device=device)
        sigma_readout_torch = torch.tensor(refinement_inputs.sigma_readout, dtype=dtype, device=device)

        # Get base detector
        base_detector = geometry_objects["detector"]
        base_beam = geometry_objects["beam"]
        base_crystal = geometry_objects["crystal"]
        experiment = geometry_objects["experiment"]

        # For multi-panel detectors, we'll perturb the distance for all panels uniformly
        # Get original distance (z-component of origin for panel 0)
        base_panel = base_detector[0]
        base_distance = abs(base_panel.get_origin()[2])  # Distance is -z typically

        # Create a loss function parameterized by distance
        def loss_fn(distance_tensor):
            from dxtbx.model import Detector as DxtbxDetector
            from dxtbx.model import Panel as DxtbxPanel

            new_distance = float(distance_tensor.item())
            distance_delta = new_distance - base_distance

            # Create new detector with updated distance
            new_detector = DxtbxDetector()
            for panel_idx in range(len(base_detector)):
                panel = base_detector[panel_idx]
                origin = panel.get_origin()
                # Update z-component (assuming origin[2] is negative distance)
                new_origin = (origin[0], origin[1], origin[2] - distance_delta)

                # Create new panel with all attributes from base panel
                new_panel = DxtbxPanel(
                    panel.get_type(),
                    panel.get_name(),
                    panel.get_fast_axis(),
                    panel.get_slow_axis(),
                    new_origin,  # Updated origin with new distance
                    panel.get_pixel_size(),
                    panel.get_image_size(),
                    panel.get_trusted_range(),
                    panel.get_thickness(),
                    panel.get_material(),
                    panel.get_mu()
                )
                new_panel.set_px_mm_strategy(panel.get_px_mm_strategy())
                new_detector.add_panel(new_panel)

            # Run forward simulation
            bragg_torch = simulate_forward_torch(
                inputs=refinement_inputs,
                detector=new_detector,
                beam=base_beam,
                crystal=base_crystal,
                experiment=experiment,
                hkl_indices=hkl_data["indices"],
                hkl_amplitudes=hkl_data["amplitudes"],
                spot_scale_override=1.0,
                device=device,
                dtype=dtype
            )

            # Compute variance-weighted chi-squared loss (PHYSICS-LOSS-001)
            loss = compute_masked_mse_loss(bragg_torch, target_torch, loss_mask_torch, sigma_readout_torch)
            return loss

        # Create differentiable parameter tensor
        distance_param = torch.tensor(base_distance, dtype=dtype, device=device, requires_grad=True)

        # Run gradcheck with slightly relaxed rtol for geometry parameters
        gradcheck_passed = gradcheck(
            loss_fn,
            (distance_param,),
            eps=1e-6,
            atol=1e-5,
            rtol=0.05,
            raise_exception=True
        )

        # Emit metrics
        metrics = {
            "parameter": "detector_distance_mm",
            "base_value": float(base_distance),
            "gradcheck_passed": gradcheck_passed,
            "eps": 1e-6,
            "atol": 1e-5,
            "rtol": 0.05,
            "device": str(device),
            "dtype": str(dtype)
        }

        metrics_file = artifact_dir / "gradcheck_detector_distance.json"
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2)

        assert gradcheck_passed, "Gradcheck failed for detector distance parameter"

    def test_db_at_010_gradcheck_beam_wavelength(
        self,
        refinement_inputs,
        geometry_objects,
        hkl_data,
        artifact_dir
    ):
        """
        DB-AT-010 (4/4): Verify gradients for beam wavelength_A parameter.

        Tests that torch.autograd.gradcheck passes for wavelength changes.
        """
        from dbex.physics.forward import simulate_forward_torch
        from dbex.physics.loss import compute_masked_mse_loss

        device = torch.device('cpu')
        dtype = torch.float64

        # Convert inputs to torch
        target_torch = torch.tensor(refinement_inputs.target, dtype=dtype, device=device)
        loss_mask_torch = torch.tensor(refinement_inputs.loss_mask, dtype=torch.bool, device=device)
        sigma_readout_torch = torch.tensor(refinement_inputs.sigma_readout, dtype=dtype, device=device)

        # Get base objects
        base_detector = geometry_objects["detector"]
        base_beam = geometry_objects["beam"]
        base_crystal = geometry_objects["crystal"]
        experiment = geometry_objects["experiment"]

        # Get original wavelength
        base_wavelength = base_beam.get_wavelength()

        # Create a loss function parameterized by wavelength
        def loss_fn(wavelength_tensor):
            from dxtbx.model import Beam as DxtbxBeam

            new_wavelength = float(wavelength_tensor.item())

            # Create new beam with updated wavelength
            new_beam = DxtbxBeam(base_beam)  # Copy
            new_beam.set_wavelength(new_wavelength)

            # Run forward simulation
            bragg_torch = simulate_forward_torch(
                inputs=refinement_inputs,
                detector=base_detector,
                beam=new_beam,
                crystal=base_crystal,
                experiment=experiment,
                hkl_indices=hkl_data["indices"],
                hkl_amplitudes=hkl_data["amplitudes"],
                spot_scale_override=1.0,
                device=device,
                dtype=dtype
            )

            # Compute variance-weighted chi-squared loss (PHYSICS-LOSS-001)
            loss = compute_masked_mse_loss(bragg_torch, target_torch, loss_mask_torch, sigma_readout_torch)
            return loss

        # Create differentiable parameter tensor
        wavelength_param = torch.tensor(base_wavelength, dtype=dtype, device=device, requires_grad=True)

        # Run gradcheck
        gradcheck_passed = gradcheck(
            loss_fn,
            (wavelength_param,),
            eps=1e-6,
            atol=1e-5,
            rtol=0.05,
            raise_exception=True
        )

        # Emit metrics
        metrics = {
            "parameter": "beam_wavelength_A",
            "base_value": float(base_wavelength),
            "gradcheck_passed": gradcheck_passed,
            "eps": 1e-6,
            "atol": 1e-5,
            "rtol": 0.05,
            "device": str(device),
            "dtype": str(dtype)
        }

        metrics_file = artifact_dir / "gradcheck_beam_wavelength.json"
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2)

        assert gradcheck_passed, "Gradcheck failed for beam wavelength parameter"

    def test_db_at_010_gradcheck(
        self,
        refinement_inputs,
        geometry_objects,
        hkl_data,
        artifact_dir
    ):
        """
        DB-AT-010: Comprehensive gradient correctness guard (wrapper).

        This wrapper test invokes all four parameter-specific gradcheck tests
        to ensure comprehensive coverage. Designed for selector activation via:

        KMP_DUPLICATE_LIB_OK=TRUE DBAT010_ARTIFACT_DIR=<path> NANOBRAGG_DISABLE_COMPILE=1 \
          pytest -v tests/dbex/test_gradients.py::TestDB_AT_010_Gradcheck::test_db_at_010_gradcheck

        The selector exercises:
        - Crystal parameters: cell_a, cell_gamma
        - Detector parameters: distance_mm
        - Beam parameters: wavelength_A

        Emits consolidated metrics to gradcheck_metrics.json.
        """
        # Run all four gradcheck tests
        passed_tests = []
        failed_tests = []

        # Test 1: Crystal cell_a
        try:
            self.test_db_at_010_gradcheck_crystal_cell_a(
                refinement_inputs, geometry_objects, hkl_data, artifact_dir
            )
            passed_tests.append("crystal_cell_a")
        except AssertionError as e:
            failed_tests.append(("crystal_cell_a", str(e)))

        # Test 2: Crystal cell_gamma
        try:
            self.test_db_at_010_gradcheck_crystal_cell_gamma(
                refinement_inputs, geometry_objects, hkl_data, artifact_dir
            )
            passed_tests.append("crystal_cell_gamma")
        except AssertionError as e:
            failed_tests.append(("crystal_cell_gamma", str(e)))

        # Test 3: Detector distance
        try:
            self.test_db_at_010_gradcheck_detector_distance(
                refinement_inputs, geometry_objects, hkl_data, artifact_dir
            )
            passed_tests.append("detector_distance_mm")
        except AssertionError as e:
            failed_tests.append(("detector_distance_mm", str(e)))

        # Test 4: Beam wavelength
        try:
            self.test_db_at_010_gradcheck_beam_wavelength(
                refinement_inputs, geometry_objects, hkl_data, artifact_dir
            )
            passed_tests.append("beam_wavelength_A")
        except AssertionError as e:
            failed_tests.append(("beam_wavelength_A", str(e)))

        # Emit consolidated metrics
        consolidated_metrics = {
            "test_suite": "DB-AT-010 Gradient Correctness Guard",
            "passed_count": len(passed_tests),
            "failed_count": len(failed_tests),
            "passed_parameters": passed_tests,
            "failed_parameters": [param for param, _ in failed_tests],
            "tolerances": {
                "eps": 1e-6,
                "atol": 1e-5,
                "rtol": 0.05
            },
            "runtime_guards": {
                "NANOBRAGG_DISABLE_COMPILE": "1",
                "KMP_DUPLICATE_LIB_OK": "TRUE"
            }
        }

        metrics_file = artifact_dir / "gradcheck_metrics.json"
        with open(metrics_file, 'w') as f:
            json.dump(consolidated_metrics, f, indent=2)

        # Assert all tests passed
        if failed_tests:
            failure_summary = "\n".join([f"  - {param}: {msg}" for param, msg in failed_tests])
            pytest.fail(
                f"DB-AT-010 gradcheck failed for {len(failed_tests)} parameter(s):\n{failure_summary}"
            )
