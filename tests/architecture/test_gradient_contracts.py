"""
Gradient Contract Enforcement Tests

ARCH-GRADIENT-FLOW-001: Verifies that gradient flow is preserved through
key pathways in the nanobrag_torch simulation library.

Cross-references:
- DBEX-GRADIENT-001: inbox/from_nanobragg.md (upstream fix design)
- docs/findings.md::GRADIENT-002
- src/nanobrag-torch/src/nanobrag_torch/utils/tensor_utils.py

These tests enforce the architectural constraint that simulation parameters
provided as differentiable tensors maintain their gradient graph through
to the output.
"""

import pytest
import torch


class TestGradientContracts:
    """Enforcement tests for gradient flow preservation in nanobrag_torch."""

    @pytest.mark.architecture
    def test_as_tensor_preserving_grad_preserves_tensor_grad(self):
        """
        GRAD-CONTRACT-001: as_tensor_preserving_grad preserves requires_grad for tensors.

        The utility must use .to() for tensor inputs to maintain gradient graph.
        """
        from nanobrag_torch.utils.tensor_utils import as_tensor_preserving_grad

        device = torch.device('cpu')
        dtype = torch.float64

        # Tensor with requires_grad=True
        x = torch.tensor(1.5, requires_grad=True)
        result = as_tensor_preserving_grad(x, device=device, dtype=dtype)

        assert result.requires_grad, (
            "as_tensor_preserving_grad must preserve requires_grad=True for tensor inputs"
        )

        # Verify gradient actually flows
        y = result * 2.0
        y.backward()
        assert x.grad is not None, "Gradient should flow back to original tensor"
        assert x.grad.item() == pytest.approx(2.0)

    @pytest.mark.architecture
    def test_as_tensor_preserving_grad_scalar_no_grad(self):
        """
        GRAD-CONTRACT-002: as_tensor_preserving_grad creates new tensor for scalars.

        Scalar inputs have no gradient; the result should be a tensor without grad.
        """
        from nanobrag_torch.utils.tensor_utils import as_tensor_preserving_grad

        device = torch.device('cpu')
        dtype = torch.float64

        result = as_tensor_preserving_grad(1.5, device=device, dtype=dtype)

        assert isinstance(result, torch.Tensor)
        assert result.item() == pytest.approx(1.5)
        assert not result.requires_grad

    @pytest.mark.architecture
    def test_detector_distance_property_gradient_flow(self):
        """
        GRAD-CONTRACT-003: Detector.distance property preserves gradient from config.

        When config.distance_mm is a tensor with requires_grad=True, the Detector.distance
        property must return a tensor that maintains the gradient graph.

        This is the "post-creation override pattern" from DBEX-GRADIENT-001.
        """
        from nanobrag_torch.models.detector import Detector
        from nanobrag_torch.config import DetectorConfig

        # Create config with scalar value
        config = DetectorConfig(
            distance_mm=100.0,
            pixel_size_mm=0.1,
            spixels=10,
            fpixels=10
        )

        # Create detector
        detector = Detector(config, device=torch.device('cpu'), dtype=torch.float64)

        # Post-creation override: inject differentiable distance
        distance_param = torch.tensor(100.0, requires_grad=True)
        detector.config.distance_mm = distance_param

        # Access property - should maintain gradient
        distance = detector.distance

        # distance is in meters (mm / 1000)
        expected = distance_param / 1000.0

        # Verify gradient flow
        loss = distance.sum()  # trivial loss
        loss.backward()

        assert distance_param.grad is not None, (
            "Gradient should flow from Detector.distance back to config.distance_mm tensor"
        )

    @pytest.mark.architecture
    def test_simulator_wavelength_gradient_flow(self):
        """
        GRAD-CONTRACT-004: Simulator.wavelength preserves gradient from beam_config.

        When beam_config.wavelength_A is a tensor with requires_grad=True, the
        Simulator must store wavelength in a way that preserves gradient flow.
        """
        from nanobrag_torch.simulator import Simulator
        from nanobrag_torch.config import BeamConfig, DetectorConfig, CrystalConfig
        from nanobrag_torch.models.crystal import Crystal
        from nanobrag_torch.models.detector import Detector

        device = torch.device('cpu')
        dtype = torch.float64

        # Create configs with tensor wavelength
        wavelength_param = torch.tensor(1.0, requires_grad=True, dtype=dtype)
        beam_config = BeamConfig(wavelength_A=wavelength_param)
        crystal_config = CrystalConfig()
        detector_config = DetectorConfig(
            distance_mm=100.0,
            pixel_size_mm=0.1,
            spixels=10,
            fpixels=10
        )

        # Create models
        crystal = Crystal(crystal_config, device=device, dtype=dtype)
        detector = Detector(detector_config, device=device, dtype=dtype)

        # Create simulator - this should preserve wavelength gradient
        simulator = Simulator(
            crystal=crystal,
            detector=detector,
            beam_config=beam_config,
            device=device,
            dtype=dtype
        )

        # The internal wavelength tensor should maintain gradient connection
        assert simulator.wavelength.requires_grad, (
            "Simulator.wavelength must have requires_grad=True when beam_config.wavelength_A is a tensor"
        )

        # Verify gradient actually flows
        loss = simulator.wavelength * 2.0
        loss.backward()

        assert wavelength_param.grad is not None, (
            "Gradient should flow from Simulator.wavelength back to beam_config.wavelength_A"
        )

    @pytest.mark.architecture
    def test_simulator_fluence_gradient_flow(self):
        """
        GRAD-CONTRACT-005: Simulator.fluence preserves gradient from beam_config.

        When beam_config.fluence is a tensor with requires_grad=True, the
        Simulator must store fluence in a way that preserves gradient flow.
        """
        from nanobrag_torch.simulator import Simulator
        from nanobrag_torch.config import BeamConfig, DetectorConfig, CrystalConfig
        from nanobrag_torch.models.crystal import Crystal
        from nanobrag_torch.models.detector import Detector

        device = torch.device('cpu')
        dtype = torch.float64

        # Create configs with tensor fluence
        # Note: Use a large value since BeamConfig.__post_init__ may modify it
        fluence_param = torch.tensor(1.0e28, requires_grad=True, dtype=dtype)
        beam_config = BeamConfig(
            wavelength_A=1.0,
            flux=0.0,  # Disable flux-based fluence calculation
            fluence=fluence_param
        )
        crystal_config = CrystalConfig()
        detector_config = DetectorConfig(
            distance_mm=100.0,
            pixel_size_mm=0.1,
            spixels=10,
            fpixels=10
        )

        # Create models
        crystal = Crystal(crystal_config, device=device, dtype=dtype)
        detector = Detector(detector_config, device=device, dtype=dtype)

        # Create simulator - this should preserve fluence gradient
        simulator = Simulator(
            crystal=crystal,
            detector=detector,
            beam_config=beam_config,
            device=device,
            dtype=dtype
        )

        # The internal fluence tensor should maintain gradient connection
        assert simulator.fluence.requires_grad, (
            "Simulator.fluence must have requires_grad=True when beam_config.fluence is a tensor"
        )

        # Verify gradient actually flows
        loss = simulator.fluence / 1e28
        loss.backward()

        assert fluence_param.grad is not None, (
            "Gradient should flow from Simulator.fluence back to beam_config.fluence"
        )
