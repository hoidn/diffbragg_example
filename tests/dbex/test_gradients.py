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
    from dbex.refinement.inputs import prepare_refinement_inputs
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
        from dbex.refinement.config_factories import create_crystal_config

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
            # Use detector_overrides to preserve gradient flow (GRADIENT-001)
            # This avoids .item() call that would detach the tensor from autograd graph
            detector_overrides = {'distance_mm': distance_tensor}

            # Run forward simulation with distance override
            bragg_torch = simulate_forward_torch(
                inputs=refinement_inputs,
                detector=base_detector,
                beam=base_beam,
                crystal=base_crystal,
                experiment=experiment,
                hkl_indices=hkl_data["indices"],
                hkl_amplitudes=hkl_data["amplitudes"],
                spot_scale_override=1.0,
                device=device,
                dtype=dtype,
                detector_overrides=detector_overrides
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
            # Use beam_overrides to preserve gradient flow (GRADIENT-001)
            # This avoids .item() call that would detach the tensor from autograd graph
            beam_overrides = {'wavelength_A': wavelength_tensor}

            # Run forward simulation with wavelength override
            bragg_torch = simulate_forward_torch(
                inputs=refinement_inputs,
                detector=base_detector,
                beam=base_beam,
                crystal=base_crystal,
                experiment=experiment,
                hkl_indices=hkl_data["indices"],
                hkl_amplitudes=hkl_data["amplitudes"],
                spot_scale_override=1.0,
                device=device,
                dtype=dtype,
                beam_overrides=beam_overrides
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


# B.8.1: Minimal reproduction test bypassing DBEX factories
def test_minimal_nanobrag_gradcheck():
    """
    Minimal reproduction of nanobrag_torch cell parameter gradcheck.

    Bypasses all DBEX factories to isolate the integration layer.
    This test should PASS if the issue is in DBEX config_factories/helpers.

    Phase B.8.1 (ARCH-GRADIENT-FLOW-001):
    - Uses parameters matching upstream test: fluence=1e28, eps=1e-6, atol=1e-5, rtol=0.05
    - Directly constructs nanobrag_torch objects without DBEX factories
    - If PASS: Confirms issue is in DBEX integration layer
    - If FAIL: Issue is in nanobrag_torch (unexpected per upstream response)

    References:
    - inbox/nanobrag_torch_cell_gradient_response_2025_12_08.md (upstream verification)
    - docs/findings.md GRADIENT-001 (tensor-valued overrides pattern)
    """
    import torch
    from torch.autograd import gradcheck
    from nanobrag_torch.config import CrystalConfig, DetectorConfig, BeamConfig
    from nanobrag_torch.models.crystal import Crystal
    from nanobrag_torch.models.detector import Detector
    from nanobrag_torch.simulator import Simulator

    device = torch.device("cpu")
    dtype = torch.float64

    # Differentiable cell parameter (matches upstream test pattern)
    cell_a = torch.tensor(100.0, dtype=dtype, requires_grad=True, device=device)

    def loss_fn(cell_a_param):
        crystal_config = CrystalConfig(
            cell_a=cell_a_param,
            cell_b=100.0,
            cell_c=100.0,
            cell_alpha=90.0,
            cell_beta=90.0,
            cell_gamma=90.0,
            N_cells=(5, 5, 5),
            default_F=100.0,
        )

        detector_config = DetectorConfig(
            distance_mm=100.0,
            pixel_size_mm=0.1,
            spixels=64,
            fpixels=64,
        )

        beam_config = BeamConfig(
            wavelength_A=1.0,
            fluence=1e28,
        )

        crystal = Crystal(config=crystal_config, device=device, dtype=dtype)
        detector = Detector(config=detector_config, device=device, dtype=dtype)

        simulator = Simulator(
            crystal=crystal,
            detector=detector,
            beam_config=beam_config,
            device=device,
            dtype=dtype,
        )

        result = simulator.run()
        return result.sum()

    # Run gradcheck with upstream tolerances
    passed = gradcheck(loss_fn, (cell_a,), eps=1e-6, atol=1e-5, rtol=0.05)
    assert passed, "Minimal nanobrag_torch gradcheck failed - issue is NOT in DBEX integration"


def test_gradient_magnitude_diagnostic():
    """
    B.8.2 Diagnostic: Compare gradient magnitudes between minimal and DBEX paths.

    This test captures:
    1. Analytical gradient magnitude (from autograd)
    2. Numerical gradient magnitude (from finite differences)
    3. Their ratio to quantify the mismatch

    Helps identify if the issue is in config_factories, HKL grid, or elsewhere.

    Phase B.8.2 (ARCH-GRADIENT-FLOW-001):
    - Mimics DBEX path but with simplified detector to isolate magnitude source
    - Does NOT use gradcheck (which raises on failure), just computes gradients
    """
    import torch
    from nanobrag_torch.config import CrystalConfig, DetectorConfig, BeamConfig
    from nanobrag_torch.models.crystal import Crystal
    from nanobrag_torch.models.detector import Detector
    from nanobrag_torch.simulator import Simulator

    device = torch.device("cpu")
    dtype = torch.float64

    results = {}

    # Test 1: Minimal path (known to work)
    cell_a_minimal = torch.tensor(100.0, dtype=dtype, requires_grad=True, device=device)

    def minimal_loss(cell_a_param):
        config = CrystalConfig(
            cell_a=cell_a_param, cell_b=100.0, cell_c=100.0,
            cell_alpha=90.0, cell_beta=90.0, cell_gamma=90.0,
            N_cells=(5, 5, 5), default_F=100.0,
        )
        crystal = Crystal(config=config, device=device, dtype=dtype)
        detector = Detector(DetectorConfig(distance_mm=100.0, pixel_size_mm=0.1, spixels=64, fpixels=64))
        sim = Simulator(crystal=crystal, detector=detector,
                       beam_config=BeamConfig(wavelength_A=1.0, fluence=1e28),
                       device=device, dtype=dtype)
        return sim.run().sum()

    # Compute analytical gradient
    loss_minimal = minimal_loss(cell_a_minimal)
    loss_minimal.backward()
    grad_analytical_minimal = cell_a_minimal.grad.clone()

    # Compute numerical gradient
    eps = 1e-6
    cell_a_plus = torch.tensor(100.0 + eps, dtype=dtype, device=device)
    cell_a_minus = torch.tensor(100.0 - eps, dtype=dtype, device=device)
    loss_plus = minimal_loss(cell_a_plus)
    loss_minus = minimal_loss(cell_a_minus)
    grad_numerical_minimal = (loss_plus - loss_minus) / (2 * eps)

    ratio_minimal = (grad_analytical_minimal / grad_numerical_minimal).item()
    results['minimal'] = {
        'analytical': grad_analytical_minimal.item(),
        'numerical': grad_numerical_minimal.item(),
        'ratio': ratio_minimal
    }

    # Test 2: DBEX-like path with MOSFLM A* = None
    # (simulates what happens when crystal_overrides triggers None A*)
    cell_a_dbex = torch.tensor(100.0, dtype=dtype, requires_grad=True, device=device)

    def dbex_like_loss(cell_a_param):
        # Create config with tensor cell_a but mosflm_* set to None (like DBEX does)
        config = CrystalConfig(
            cell_a=cell_a_param, cell_b=100.0, cell_c=100.0,
            cell_alpha=90.0, cell_beta=90.0, cell_gamma=90.0,
            N_cells=(5, 5, 5), default_F=100.0,
            mosflm_a_star=None, mosflm_b_star=None, mosflm_c_star=None,  # Explicit None
        )
        crystal = Crystal(config=config, device=device, dtype=dtype)
        detector = Detector(DetectorConfig(distance_mm=100.0, pixel_size_mm=0.1, spixels=64, fpixels=64))
        sim = Simulator(crystal=crystal, detector=detector,
                       beam_config=BeamConfig(wavelength_A=1.0, fluence=1e28),
                       device=device, dtype=dtype)
        return sim.run().sum()

    # Compute analytical gradient
    loss_dbex = dbex_like_loss(cell_a_dbex)
    loss_dbex.backward()
    grad_analytical_dbex = cell_a_dbex.grad.clone()

    # Compute numerical gradient
    cell_a_plus = torch.tensor(100.0 + eps, dtype=dtype, device=device)
    cell_a_minus = torch.tensor(100.0 - eps, dtype=dtype, device=device)
    loss_plus = dbex_like_loss(cell_a_plus)
    loss_minus = dbex_like_loss(cell_a_minus)
    grad_numerical_dbex = (loss_plus - loss_minus) / (2 * eps)

    ratio_dbex = (grad_analytical_dbex / grad_numerical_dbex).item()
    results['dbex_like'] = {
        'analytical': grad_analytical_dbex.item(),
        'numerical': grad_numerical_dbex.item(),
        'ratio': ratio_dbex
    }

    # Test 3: With beam_config passed to Crystal (like DBEX helpers.py:198)
    cell_a_beam = torch.tensor(100.0, dtype=dtype, requires_grad=True, device=device)

    def beam_crystal_loss(cell_a_param):
        config = CrystalConfig(
            cell_a=cell_a_param, cell_b=100.0, cell_c=100.0,
            cell_alpha=90.0, cell_beta=90.0, cell_gamma=90.0,
            N_cells=(5, 5, 5), default_F=100.0,
        )
        beam_config = BeamConfig(wavelength_A=1.0, fluence=1e28)
        # Pass beam_config to Crystal constructor (like DBEX does)
        crystal = Crystal(config=config, beam_config=beam_config, device=device, dtype=dtype)
        detector = Detector(DetectorConfig(distance_mm=100.0, pixel_size_mm=0.1, spixels=64, fpixels=64))
        sim = Simulator(crystal=crystal, detector=detector,
                       beam_config=beam_config,
                       device=device, dtype=dtype)
        return sim.run().sum()

    # Compute analytical gradient
    loss_beam = beam_crystal_loss(cell_a_beam)
    loss_beam.backward()
    grad_analytical_beam = cell_a_beam.grad.clone()

    # Compute numerical gradient
    loss_plus = beam_crystal_loss(torch.tensor(100.0 + eps, dtype=dtype, device=device))
    loss_minus = beam_crystal_loss(torch.tensor(100.0 - eps, dtype=dtype, device=device))
    grad_numerical_beam = (loss_plus - loss_minus) / (2 * eps)

    ratio_beam = (grad_analytical_beam / grad_numerical_beam).item()
    results['with_beam_config'] = {
        'analytical': grad_analytical_beam.item(),
        'numerical': grad_numerical_beam.item(),
        'ratio': ratio_beam
    }

    # Print diagnostics
    print("\n=== Gradient Magnitude Diagnostic ===")
    for name, data in results.items():
        print(f"\n{name}:")
        print(f"  Analytical: {data['analytical']:.6e}")
        print(f"  Numerical:  {data['numerical']:.6e}")
        print(f"  Ratio (ana/num): {data['ratio']:.2f}x")

    # Assert all ratios are close to 1.0 (within 5% tolerance = rtol=0.05)
    for name, data in results.items():
        assert 0.95 <= abs(data['ratio']) <= 1.05, f"{name}: ratio {data['ratio']:.2f}x not within 5%"


def test_dbex_hkl_grid_gradient():
    """
    B.8.3 Diagnostic: Test gradient flow through DBEX's build_structure_factor_grid.

    Tests if using DBEX's HKL grid construction introduces gradient issues.
    """
    import torch
    import numpy as np
    from torch.autograd import gradcheck
    from nanobrag_torch.config import CrystalConfig, DetectorConfig, BeamConfig
    from nanobrag_torch.models.crystal import Crystal
    from nanobrag_torch.models.detector import Detector
    from nanobrag_torch.simulator import Simulator
    from dbex.nanobrag_bridge import build_structure_factor_grid

    device = torch.device("cpu")
    dtype = torch.float64

    # Create synthetic HKL data
    hkl_indices = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 1, 0], [1, 0, 1], [0, 1, 1]], dtype=np.int32)
    hkl_amplitudes = np.array([100.0, 100.0, 100.0, 100.0, 100.0, 100.0], dtype=np.float64)

    # Build HKL grid using DBEX bridge
    hkl_grid, hkl_metadata, asu_map = build_structure_factor_grid(
        indices=hkl_indices,
        amplitudes=hkl_amplitudes,
        device=device,
        halo=True
    )

    # Differentiable cell parameter
    cell_a = torch.tensor(100.0, dtype=dtype, requires_grad=True, device=device)

    def loss_fn(cell_a_param):
        config = CrystalConfig(
            cell_a=cell_a_param, cell_b=100.0, cell_c=100.0,
            cell_alpha=90.0, cell_beta=90.0, cell_gamma=90.0,
            N_cells=(5, 5, 5),
        )
        crystal = Crystal(config=config, device=device, dtype=dtype)

        # Attach HKL data from DBEX grid builder
        crystal.hkl_data = hkl_grid.to(dtype=dtype)
        crystal.hkl_metadata = hkl_metadata

        detector = Detector(DetectorConfig(distance_mm=100.0, pixel_size_mm=0.1, spixels=64, fpixels=64))
        sim = Simulator(crystal=crystal, detector=detector,
                       beam_config=BeamConfig(wavelength_A=1.0, fluence=1e28),
                       device=device, dtype=dtype)
        return sim.run().sum()

    # Run gradcheck
    passed = gradcheck(loss_fn, (cell_a,), eps=1e-6, atol=1e-5, rtol=0.05)
    assert passed, "DBEX HKL grid path gradcheck failed"


def test_dbex_full_factory_gradient():
    """
    B.8.4 Diagnostic: Test gradient flow through full DBEX config_factories path.

    Uses create_crystal_config with crystal_overrides to match exact DBEX usage.
    """
    import torch
    import numpy as np
    from torch.autograd import gradcheck
    from nanobrag_torch.config import BeamConfig, DetectorConfig
    from nanobrag_torch.models.crystal import Crystal
    from nanobrag_torch.models.detector import Detector
    from nanobrag_torch.simulator import Simulator
    from dbex.nanobrag_bridge import build_structure_factor_grid
    from dbex.refinement.config_factories import create_crystal_config

    device = torch.device("cpu")
    dtype = torch.float64

    # Mock a simple dxtbx Crystal
    from dxtbx.model import Crystal as DxtbxCrystal
    from dxtbx.model import Experiment

    # Create a simple cubic crystal
    dxtbx_crystal = DxtbxCrystal(
        real_space_a=(100, 0, 0),
        real_space_b=(0, 100, 0),
        real_space_c=(0, 0, 100),
        space_group_symbol="P 1"
    )

    # Create minimal experiment (no scan/gonio for stills)
    experiment = Experiment(crystal=dxtbx_crystal)

    # Synthetic HKL
    hkl_indices = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.int32)
    hkl_amplitudes = np.array([100.0, 100.0, 100.0], dtype=np.float64)

    hkl_grid, hkl_metadata, _ = build_structure_factor_grid(
        indices=hkl_indices,
        amplitudes=hkl_amplitudes,
        device=device,
        halo=True
    )

    cell_a = torch.tensor(100.0, dtype=dtype, requires_grad=True, device=device)

    def loss_fn(cell_a_param):
        # Use DBEX factory with crystal_overrides (exact DBEX pattern)
        crystal_overrides = {'cell_a': cell_a_param}
        crystal_config, _ = create_crystal_config(
            dxtbx_crystal, experiment, crystal_overrides=crystal_overrides
        )

        crystal = Crystal(config=crystal_config, device=device, dtype=dtype)
        crystal.hkl_data = hkl_grid.to(dtype=dtype)
        crystal.hkl_metadata = hkl_metadata

        detector = Detector(DetectorConfig(distance_mm=100.0, pixel_size_mm=0.1, spixels=64, fpixels=64))
        sim = Simulator(crystal=crystal, detector=detector,
                       beam_config=BeamConfig(wavelength_A=1.0, fluence=1e28),
                       device=device, dtype=dtype)
        return sim.run().sum()

    # Run gradcheck
    passed = gradcheck(loss_fn, (cell_a,), eps=1e-6, atol=1e-5, rtol=0.05)
    assert passed, "DBEX full factory path gradcheck failed"


def test_simulate_forward_torch_gradient():
    """
    B.8.5 Diagnostic: Test gradient flow through simulate_forward_torch.

    Uses synthetic dxtbx objects to test the full forward path.
    """
    import torch
    import numpy as np
    from torch.autograd import gradcheck
    from types import SimpleNamespace
    from dxtbx.model import Crystal as DxtbxCrystal
    from dxtbx.model import Beam as DxtbxBeam
    from dxtbx.model import Detector as DxtbxDetector
    from dxtbx.model import Panel, Experiment

    from dbex.physics.forward import simulate_forward_torch
    from dbex.physics.loss import compute_masked_mse_loss

    device = torch.device("cpu")
    dtype = torch.float64

    # Create synthetic dxtbx crystal
    dxtbx_crystal = DxtbxCrystal(
        real_space_a=(100, 0, 0),
        real_space_b=(0, 100, 0),
        real_space_c=(0, 0, 100),
        space_group_symbol="P 1"
    )

    # Create synthetic dxtbx beam
    dxtbx_beam = DxtbxBeam(direction=(0, 0, 1), wavelength=1.0)

    # Create synthetic single-panel detector (origin z should be negative for forward-facing detector)
    dxtbx_detector = DxtbxDetector()
    panel = dxtbx_detector.add_panel()
    # dxtbx convention: origin is corner of panel, z is negative for panel facing source
    # Beam comes from -z direction, so detector at +z from sample doesn't work
    # For a detector at distance d, origin z = -d (panel normal faces -z)
    panel.set_frame(
        fast_axis=(1, 0, 0),
        slow_axis=(0, -1, 0),  # Standard dxtbx: slow axis often points -y
        origin=(-3.2, 3.2, -100)  # Panel corner, 100mm in front of sample
    )
    panel.set_pixel_size((0.1, 0.1))  # 0.1mm pixels
    panel.set_image_size((64, 64))  # 64x64 panel

    experiment = Experiment(crystal=dxtbx_crystal, beam=dxtbx_beam, detector=dxtbx_detector)

    # Synthetic HKL
    hkl_indices = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.int32)
    hkl_amplitudes = np.array([100.0, 100.0, 100.0], dtype=np.float64)

    # Create mock RefinementInputs
    panel_shape = (64, 64)
    target = np.zeros((1, *panel_shape), dtype=np.float32)
    loss_mask = np.ones((1, *panel_shape), dtype=bool)
    trusted_mask = np.ones((1, *panel_shape), dtype=bool)
    sigma_readout = np.full((1, *panel_shape), 3.0, dtype=np.float32)

    inputs = SimpleNamespace(
        target=target,
        loss_mask=loss_mask,
        trusted_mask=trusted_mask,
        sigma_readout=sigma_readout,
        panel_slices=None,
        global_scale_hint=1.0
    )

    target_torch = torch.tensor(target, dtype=dtype, device=device)
    loss_mask_torch = torch.tensor(loss_mask, dtype=torch.bool, device=device)
    sigma_torch = torch.tensor(sigma_readout, dtype=dtype, device=device)

    cell_a = torch.tensor(100.0, dtype=dtype, requires_grad=True, device=device)

    def loss_fn(cell_a_param):
        crystal_overrides = {'cell_a': cell_a_param}

        bragg_torch = simulate_forward_torch(
            inputs=inputs,
            detector=dxtbx_detector,
            beam=dxtbx_beam,
            crystal=dxtbx_crystal,
            experiment=experiment,
            hkl_indices=hkl_indices,
            hkl_amplitudes=hkl_amplitudes,
            spot_scale_override=1.0,
            device=device,
            dtype=dtype,
            crystal_overrides=crystal_overrides
        )

        loss = compute_masked_mse_loss(bragg_torch, target_torch, loss_mask_torch, sigma_torch)
        return loss

    # Run gradcheck
    passed = gradcheck(loss_fn, (cell_a,), eps=1e-6, atol=1e-5, rtol=0.05)
    assert passed, "simulate_forward_torch gradcheck failed"
