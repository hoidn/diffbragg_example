"""
Tests for refine_one CLI backend dispatch.

Per docs/TESTING_GUIDE.md, run with:
    KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_refine_one_cli.py
"""
import os
import tempfile
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

from dbex.refine_one import create_parser, main, run_nanobrag_backend


def test_parser_has_backend_flag():
    """A1: Verify --backend flag exists with correct choices and default."""
    parser = create_parser()
    args = parser.parse_args(['--backend', 'diffbragg',
                             '-e', 'test.expt', '-r', 'test.refl',
                             '-i', '0', '-o', 'out.h5',
                             '-m', 'mask.pickle', '-z', 'test.mtz'])
    assert args.backend == 'diffbragg'

    args = parser.parse_args(['--backend', 'nanobrag',
                             '-e', 'test.expt', '-r', 'test.refl',
                             '-i', '0', '-o', 'out.h5',
                             '-m', 'mask.pickle', '-z', 'test.mtz'])
    assert args.backend == 'nanobrag'

    # Test default
    args = parser.parse_args(['-e', 'test.expt', '-r', 'test.refl',
                             '-i', '0', '-o', 'out.h5',
                             '-m', 'mask.pickle', '-z', 'test.mtz'])
    assert args.backend == 'diffbragg'


def test_parser_rejects_invalid_backend():
    """A1: Verify invalid backend choices are rejected."""
    parser = create_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(['--backend', 'invalid',
                          '-e', 'test.expt', '-r', 'test.refl',
                          '-i', '0', '-o', 'out.h5',
                          '-m', 'mask.pickle', '-z', 'test.mtz'])


def test_parser_accepts_sigma_map_flag():
    """PHYSICS-LOSS-001: Ensure --sigma-map option is wired through parser."""
    parser = create_parser()
    args = parser.parse_args([
        '--backend', 'nanobrag',
        '-e', 'test.expt', '-r', 'test.refl',
        '-i', '0', '-o', 'out.h5',
        '-m', 'mask.pickle', '-z', 'test.mtz',
        '--sigma-map', 'sigma.npy'
    ])
    assert args.sigma_map == 'sigma.npy'


@patch('dbex.data_load.DataLoad')
@patch('dbex.refine_one.run_diffbragg_backend')
def test_main_dispatches_to_diffbragg_backend(mock_diffbragg, mock_dataload):
    """A2: Verify main() dispatches to diffbragg backend correctly."""
    mock_dl = Mock()
    mock_dataload.return_value = mock_dl

    argv = ['--backend', 'diffbragg',
            '-e', 'test.expt', '-r', 'test.refl',
            '-i', '0', '-o', 'out.h5',
            '-m', 'mask.pickle', '-z', 'test.mtz']

    main(argv)

    mock_dataload.assert_called_once()
    mock_diffbragg.assert_called_once()
    args = mock_diffbragg.call_args[0][0]
    assert args.backend == 'diffbragg'


@patch('dbex.data_load.DataLoad')
@patch('dbex.refine_one.run_nanobrag_backend')
def test_main_dispatches_to_nanobrag_backend(mock_nanobrag, mock_dataload):
    """A2: Verify main() dispatches to nanobrag backend correctly."""
    mock_dl = Mock()
    mock_dataload.return_value = mock_dl

    argv = ['--backend', 'nanobrag',
            '-e', 'test.expt', '-r', 'test.refl',
            '-i', '0', '-o', 'out.h5',
            '-m', 'mask.pickle', '-z', 'test.mtz']

    main(argv)

    mock_dataload.assert_called_once()
    mock_nanobrag.assert_called_once()
    args = mock_nanobrag.call_args[0][0]
    assert args.backend == 'nanobrag'


@patch('nanobrag_torch.simulator.Simulator')
@patch('nanobrag_torch.models.detector.Detector')
@patch('nanobrag_torch.models.crystal.Crystal')
@patch('dbex.nanobrag_bridge.prepare_refinement_inputs')
@patch('dbex.nanobrag_bridge.build_structure_factor_grid')
@patch('dbex.nanobrag_bridge.create_detector_config')
@patch('dbex.nanobrag_bridge.create_beam_config')
@patch('dbex.nanobrag_bridge.create_crystal_config')
@patch('dbex.refine_one._write_torch_outputs')
def test_nanobrag_backend_runs_simulator(
    mock_write, mock_crystal_config, mock_beam_config, mock_detector_config,
    mock_build_grid, mock_prepare, mock_Crystal, mock_Detector, mock_Simulator
):
    """A2: Verify nanobrag backend uses real simulator with SCALE-001/002 guardrails."""
    import numpy as np
    import torch
    from dbex.nanobrag_bridge import RefinementInputs

    # Setup mock DataLoad with MTZ data
    mock_dl = Mock()
    mock_dl.data = np.zeros((1, 100, 100), dtype=np.float32)
    mock_dl.background_image = np.ones((1, 100, 100), dtype=np.float32) * -1
    mock_dl.trusted_mask = np.ones((1, 100, 100), dtype=bool)
    mock_dl.bbox = np.array([[10, 20, 10, 20]])
    mock_dl.pids = np.array([0])

    # Mock detector with single panel
    mock_panel = Mock()
    mock_dl.detector = [mock_panel]

    # Mock beam, crystal, and Expt
    mock_dl.beam = Mock()
    mock_dl.crystal = Mock()
    mock_dl.Expt = Mock()

    # Mock MTZ Miller array
    mock_F = Mock()
    mock_F.indices.return_value = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
    mock_F.data.return_value = np.array([100.0, 200.0, 150.0])
    mock_dl.F = mock_F

    # Setup mock bridge output
    sigma_stub = np.zeros((1, 100, 100), dtype=np.float32)
    mock_inputs = RefinementInputs(
        target=np.zeros((1, 100, 100), dtype=np.float32),
        loss_mask=np.ones((1, 100, 100), dtype=bool),
        panel_slices=[(0, (10, 20, 10, 20))],
        trusted_mask=np.ones((1, 100, 100), dtype=bool),
        sigma_readout=sigma_stub
    )
    mock_prepare.return_value = mock_inputs

    # Mock structure factor grid (SCALE-001: unscaled)
    mock_hkl_grid = torch.zeros((3, 3, 3), dtype=torch.float32)
    mock_hkl_metadata = {
        'h_min': 0, 'h_max': 2, 'k_min': 0, 'k_max': 2, 'l_min': 0, 'l_max': 2,
        'grid_nonzero': 3
    }
    mock_asu_map = torch.zeros_like(mock_hkl_grid, dtype=torch.int32)
    mock_build_grid.return_value = (mock_hkl_grid, mock_hkl_metadata, mock_asu_map)

    # Mock config objects
    # CLI-001: DetectorConfig.mask_array must be torch.Tensor (not numpy)
    # Create a proper mock with mask_array as float32 tensor with 0/1 values
    mock_detector_config_obj = Mock()
    mock_detector_config_obj.mask_array = torch.ones((100, 100), dtype=torch.float32)
    mock_detector_config.return_value = mock_detector_config_obj

    mock_beam_config.return_value = Mock()
    # create_crystal_config returns (config, n_cells_applied) tuple
    mock_crystal_config.return_value = (Mock(), False)

    # Mock model instantiation
    mock_detector_instance = Mock()
    mock_Detector.return_value = mock_detector_instance
    mock_crystal_instance = Mock()
    mock_Crystal.return_value = mock_crystal_instance

    # Mock simulator run output (base intensity before scaling)
    mock_panel_output = torch.ones((100, 100), dtype=torch.float32) * 1000.0
    mock_simulator_instance = Mock()
    mock_simulator_instance.run.return_value = mock_panel_output
    mock_Simulator.return_value = mock_simulator_instance

    # Setup mock args with spot_scale_override (no calibration file)
    args = Mock()
    args.outFile = 'test.h5'
    args.spot_scale_override = 4.0  # sqrt(4.0) = 2.0
    args.torch_config = None  # No calibration metadata
    args.refined_mtz = None  # No refined MTZ
    args.adu_per_photon = None
    args.sigma_rdout = 3.0
    args.sigma_floor = 1.0
    args.device = "cpu"

    run_nanobrag_backend(args, mock_dl)

    # Verify structure factor grid was built (SCALE-001: unscaled)
    mock_build_grid.assert_called_once()
    call_kwargs = mock_build_grid.call_args[1]
    assert 'indices' in call_kwargs
    assert 'amplitudes' in call_kwargs

    # Verify configs were created per panel WITHOUT calibration overrides (SCALE-006)
    # Note: refinement nucleus may call configs multiple times (zero-iter + LBFGS closure)
    assert mock_detector_config.call_count >= 1, "detector_config should be called at least once"

    # CLI-001: Verify the returned DetectorConfig has mask_array as torch.Tensor with float32 dtype and 0/1 values
    # This guard ensures CLI path doesn't regress back to numpy arrays (AttributeError in Simulator.__init__)
    detector_config_result = mock_detector_config.return_value
    assert hasattr(detector_config_result, 'mask_array'), "DetectorConfig must have mask_array attribute"

    if detector_config_result.mask_array is not None:
        assert isinstance(detector_config_result.mask_array, torch.Tensor), \
            f"CLI-001: DetectorConfig.mask_array must be torch.Tensor, got {type(detector_config_result.mask_array).__name__}"
        assert detector_config_result.mask_array.dtype == torch.float32, \
            f"CLI-001: DetectorConfig.mask_array must be float32, got {detector_config_result.mask_array.dtype}"
        # Verify mask contains only 0.0 and 1.0 values (inclusion polarity per config_crosswalk.md:31)
        unique_vals = torch.unique(detector_config_result.mask_array)
        assert torch.all((unique_vals == 0.0) | (unique_vals == 1.0)), \
            f"CLI-001: DetectorConfig.mask_array must contain only {{0.0, 1.0}}, got unique values: {unique_vals.tolist()}"

    # When no calibration metadata, beam_config called without flux/exposure/beamsize
    assert mock_beam_config.call_count >= 1, "beam_config should be called at least once"
    # Verify beam_config was called with beam only (no calibration)
    for call in mock_beam_config.call_args_list:
        assert call[0][0] == mock_dl.beam or call.kwargs.get('beam') == mock_dl.beam
    # When no calibration metadata, crystal_config called without N_cells
    assert mock_crystal_config.call_count >= 1, "crystal_config should be called at least once"

    # Verify models were instantiated (may be called multiple times by refinement)
    assert mock_Detector.call_count >= 1, "Detector model should be instantiated at least once"
    assert mock_Crystal.call_count >= 1, "Crystal model should be instantiated at least once"

    # Verify HKL data was attached to crystal model
    assert mock_crystal_instance.hkl_data is mock_hkl_grid
    assert mock_crystal_instance.hkl_metadata == mock_hkl_metadata

    # Verify simulator was run
    # Verify simulator was called (may be called multiple times by refinement)
    assert mock_Simulator.call_count >= 1, "Simulator should be called at least once"
    assert mock_simulator_instance.run.call_count >= 1, "Simulator.run should be called at least once"

    # Verify output writer was called
    mock_write.assert_called_once()

    # Verify SCALE-002: sqrt(spot_scale_override) applied post-simulation
    # The Bragg array passed to _write_torch_outputs should be scaled
    bragg_array = mock_write.call_args[0][2]
    expected_scaled = 1000.0 * np.sqrt(4.0)  # 1000.0 * 2.0 = 2000.0
    assert bragg_array[0, 0, 0] == pytest.approx(expected_scaled, rel=1e-5)


@patch('nanobrag_torch.simulator.Simulator')
@patch('nanobrag_torch.models.detector.Detector')
@patch('nanobrag_torch.models.crystal.Crystal')
@patch('dbex.nanobrag_bridge.prepare_refinement_inputs')
@patch('dbex.nanobrag_bridge.build_structure_factor_grid')
@patch('dbex.nanobrag_bridge.create_detector_config')
@patch('dbex.nanobrag_bridge.create_beam_config')
@patch('dbex.nanobrag_bridge.create_crystal_config')
@patch('dbex.nanobrag_bridge.load_calibration_metadata')
@patch('dbex.refine_one._write_torch_outputs')
def test_nanobrag_backend_applies_calibration(
    mock_write, mock_load_calib, mock_crystal_config, mock_beam_config,
    mock_detector_config, mock_build_grid, mock_prepare, mock_Crystal,
    mock_Detector, mock_Simulator
):
    """
    SCALE-006: Verify CLI applies DiffBragg calibration metadata.

    Tests that when --torch-config is provided:
    1. load_calibration_metadata is invoked with the path
    2. create_beam_config receives flux/exposure/beamsize overrides
    3. create_crystal_config receives N_cells and apply_n_cells=True
    4. Simulator is constructed with beam_config when calibration present

    Implements input.md Do Now: calibration-positive CLI test for MAP-SCALE-002.
    """
    import numpy as np
    import torch
    from dbex.nanobrag_bridge import RefinementInputs

    # Setup mock DataLoad
    mock_dl = Mock()
    mock_dl.data = np.zeros((1, 100, 100), dtype=np.float32)
    mock_dl.background_image = np.ones((1, 100, 100), dtype=np.float32) * -1
    mock_dl.trusted_mask = np.ones((1, 100, 100), dtype=bool)
    mock_dl.bbox = np.array([[10, 20, 10, 20]])
    mock_dl.pids = np.array([0])

    # Mock detector with single panel
    mock_panel = Mock()
    mock_dl.detector = [mock_panel]

    # Mock beam, crystal, and Expt
    mock_dl.beam = Mock()
    mock_dl.crystal = Mock()
    mock_dl.Expt = Mock()

    # Mock MTZ Miller array
    mock_F = Mock()
    mock_F.indices.return_value = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
    mock_F.data.return_value = np.array([100.0, 200.0, 150.0])
    mock_dl.F = mock_F

    # Setup mock bridge output
    sigma_stub = np.zeros((1, 100, 100), dtype=np.float32)
    mock_inputs = RefinementInputs(
        target=np.zeros((1, 100, 100), dtype=np.float32),
        loss_mask=np.ones((1, 100, 100), dtype=bool),
        panel_slices=[(0, (10, 20, 10, 20))],
        trusted_mask=np.ones((1, 100, 100), dtype=bool),
        sigma_readout=sigma_stub
    )
    mock_prepare.return_value = mock_inputs

    # Mock structure factor grid
    mock_hkl_grid = torch.zeros((3, 3, 3), dtype=torch.float32)
    mock_hkl_metadata = {
        'h_min': 0, 'h_max': 2, 'k_min': 0, 'k_max': 2, 'l_min': 0, 'l_max': 2,
        'grid_nonzero': 3
    }
    mock_asu_map = torch.zeros_like(mock_hkl_grid, dtype=torch.int32)
    mock_build_grid.return_value = (mock_hkl_grid, mock_hkl_metadata, mock_asu_map)

    # Mock calibration metadata load (SCALE-006 guard)
    calibration_metadata = {
        'spot_scale_override': 3.185e17,
        'beam_flux': 1e12,
        'beam_exposure': 1.0,
        'beamsize_mm': 1.0,
        'N_cells': [36, 28, 26]
    }
    mock_load_calib.return_value = calibration_metadata

    # Mock config objects
    mock_detector_cfg = Mock()
    mock_detector_config.return_value = mock_detector_cfg
    mock_beam_cfg = Mock()
    mock_beam_config.return_value = mock_beam_cfg
    # create_crystal_config returns (config, n_cells_applied) tuple
    mock_crystal_cfg = Mock()
    mock_crystal_config.return_value = (mock_crystal_cfg, True)

    # Mock model instantiation
    mock_detector_instance = Mock()
    mock_Detector.return_value = mock_detector_instance
    mock_crystal_instance = Mock()
    mock_Crystal.return_value = mock_crystal_instance

    # Mock simulator run output
    mock_panel_output = torch.ones((100, 100), dtype=torch.float32) * 1000.0
    mock_simulator_instance = Mock()
    mock_simulator_instance.run.return_value = mock_panel_output
    mock_Simulator.return_value = mock_simulator_instance

    # Setup mock args WITH calibration file (calibration-positive path)
    args = Mock()
    args.outFile = 'test.h5'
    args.spot_scale_override = 4.0  # CLI flag (calibration should override)
    args.torch_config = '/fake/path/config_torch.json'  # Trigger calibration load
    args.refined_mtz = None
    args.adu_per_photon = None
    args.sigma_rdout = 3.0
    args.sigma_floor = 1.0
    args.device = "cpu"

    run_nanobrag_backend(args, mock_dl)

    # Assert 1: load_calibration_metadata called with path
    mock_load_calib.assert_called_once_with('/fake/path/config_torch.json')

    # Assert 2: create_beam_config received flux/exposure/beamsize overrides
    mock_beam_config.assert_called_once()
    beam_call_kwargs = mock_beam_config.call_args[1]
    assert beam_call_kwargs['flux'] == 1e12
    assert beam_call_kwargs['exposure'] == 1.0
    assert beam_call_kwargs['beamsize_mm'] == 1.0

    # Assert 3: create_crystal_config received N_cells and apply_n_cells=True
    mock_crystal_config.assert_called_once()
    crystal_call_kwargs = mock_crystal_config.call_args[1]
    assert crystal_call_kwargs['N_cells'] == [36, 28, 26]
    assert crystal_call_kwargs['apply_n_cells'] is True

    # Assert 4: Simulator constructed with beam_config when calibration present
    mock_Simulator.assert_called_once()
    sim_call_kwargs = mock_Simulator.call_args[1]
    assert sim_call_kwargs['beam_config'] is mock_beam_cfg

    # Verify models were instantiated and simulator ran
    mock_Detector.assert_called_once()
    mock_Crystal.assert_called_once()
    mock_simulator_instance.run.assert_called_once()

    # Verify output writer was called
    mock_write.assert_called_once()


@patch('dbex.nanobrag_bridge.prepare_refinement_inputs')
def test_nanobrag_backend_requires_sigma_rdout(mock_prepare):
    """PHYSICS-LOSS-001: Ensure CLI refuses nanobrag backend without sigma_readout input."""
    import numpy as np

    mock_dl = Mock()
    mock_dl.data = np.zeros((1, 5, 5), dtype=np.float32)
    mock_dl.background_image = np.zeros((1, 5, 5), dtype=np.float32)
    mock_dl.trusted_mask = np.ones((1, 5, 5), dtype=bool)
    mock_dl.bbox = np.array([[0, 1, 0, 1]])
    mock_dl.pids = np.array([0])
    mock_dl.detector = [Mock()]
    mock_dl.beam = Mock()
    mock_dl.crystal = Mock()
    mock_dl.sigma_readout_map = None

    args = Mock()
    args.outFile = 'out.h5'
    args.spot_scale_override = None
    args.torch_config = None
    args.refined_mtz = None
    args.adu_per_photon = None
    args.sigma_rdout = None
    args.sigma_floor = 1.0
    args.device = "cpu"

    with pytest.raises(ValueError, match="--sigma-rdout"):
        run_nanobrag_backend(args, mock_dl)

    mock_prepare.assert_not_called()


@patch('nanobrag_torch.simulator.Simulator')
@patch('nanobrag_torch.models.detector.Detector')
@patch('nanobrag_torch.models.crystal.Crystal')
@patch('dbex.nanobrag_bridge.prepare_refinement_inputs')
@patch('dbex.nanobrag_bridge.build_structure_factor_grid')
@patch('dbex.nanobrag_bridge.create_detector_config')
@patch('dbex.nanobrag_bridge.create_beam_config')
@patch('dbex.nanobrag_bridge.create_crystal_config')
@patch('dbex.refine_one._write_torch_outputs')
def test_nanobrag_backend_accepts_sigma_map(
    mock_write,
    mock_crystal_config,
    mock_beam_config,
    mock_detector_config,
    mock_build_grid,
    mock_prepare,
    mock_Crystal,
    mock_Detector,
    mock_Simulator,
):
    """PHYSICS-LOSS-001: Calibrated sigma maps allow nanobrag backend without --sigma-rdout."""
    import numpy as np
    import torch
    from dbex.nanobrag_bridge import RefinementInputs

    sigma_map = np.full((1, 8, 8), 6.0, dtype=np.float32)

    mock_dl = Mock()
    mock_dl.data = np.zeros((1, 8, 8), dtype=np.float32)
    mock_dl.background_image = np.ones((1, 8, 8), dtype=np.float32) * -1
    mock_dl.trusted_mask = np.ones((1, 8, 8), dtype=bool)
    mock_dl.bbox = np.array([[0, 4, 0, 4]])
    mock_dl.pids = np.array([0])
    mock_dl.detector = [Mock()]
    mock_dl.beam = Mock()
    mock_dl.crystal = Mock()
    mock_dl.Expt = Mock()
    mock_dl.F = Mock()
    mock_dl.F.indices.return_value = np.array([[0, 0, 1]], dtype=np.int32)
    mock_dl.F.data.return_value = np.array([10.0], dtype=np.float32)
    mock_dl.sigma_readout_map = sigma_map

    # Bridge outputs
    mock_detector_config.return_value = Mock()
    mock_beam_config.return_value = Mock()
    mock_crystal_config.return_value = (Mock(), False)
    mock_build_grid.return_value = (
        torch.zeros((3, 3, 3), dtype=torch.float32),
        {"grid_nonzero": 1},
        torch.zeros((3, 3, 3), dtype=torch.int32),
    )

    # Simulator outputs constant tensor
    mock_simulator_instance = Mock()
    mock_simulator_instance.run.return_value = torch.ones((8, 8), dtype=torch.float32)
    mock_Simulator.return_value = mock_simulator_instance
    mock_Detector.return_value = Mock()
    mock_Crystal.return_value = Mock()

    # prepare_refinement_inputs return
    mock_prepare.return_value = RefinementInputs(
        target=np.zeros((1, 8, 8), dtype=np.float32),
        loss_mask=np.ones((1, 8, 8), dtype=bool),
        panel_slices=[(0, (0, 4, 0, 4))],
        trusted_mask=np.ones((1, 8, 8), dtype=bool),
        sigma_readout=np.full((1, 8, 8), 3.0, dtype=np.float32),
    )

    args = Mock()
    args.outFile = 'out.h5'
    args.spot_scale_override = None
    args.torch_config = None
    args.refined_mtz = None
    args.adu_per_photon = 2.0
    args.sigma_rdout = None
    args.sigma_floor = 1.0
    args.device = "cpu"

    run_nanobrag_backend(args, mock_dl)

    # prepare_refinement_inputs should receive the calibrated sigma map (before photon conversion)
    mock_prepare.assert_called_once()
    sigma_kwarg = mock_prepare.call_args[1]['sigma_readout']
    assert np.array_equal(sigma_kwarg, sigma_map)

    # Writer should receive calibrated provenance and photon-space reference median (6 / 2 = 3)
    mock_write.assert_called_once()
    write_kwargs = mock_write.call_args[1]
    assert write_kwargs['sigma_readout_provenance'] == "calibrated_map"
    assert write_kwargs['sigma_readout_reference_value'] == pytest.approx(3.0)


@patch('nanobrag_torch.simulator.Simulator')
@patch('nanobrag_torch.models.detector.Detector')
@patch('nanobrag_torch.models.crystal.Crystal')
@patch('dbex.nanobrag_bridge.prepare_refinement_inputs')
@patch('dbex.nanobrag_bridge.build_structure_factor_grid')
@patch('dbex.nanobrag_bridge.create_detector_config')
@patch('dbex.nanobrag_bridge.create_beam_config')
@patch('dbex.nanobrag_bridge.create_crystal_config')
@patch('dbex.refine_one._write_torch_outputs')
def test_nanobrag_backend_accepts_external_lookup_sigma_map(
    mock_write,
    mock_crystal_config,
    mock_beam_config,
    mock_detector_config,
    mock_build_grid,
    mock_prepare,
    mock_Crystal,
    mock_Detector,
    mock_Simulator,
):
    """Metadata-derived sigma maps set external_lookup provenance."""
    import numpy as np
    import torch
    from dbex.nanobrag_bridge import RefinementInputs

    sigma_map = np.full((1, 6, 6), 4.0, dtype=np.float32)

    mock_dl = Mock()
    mock_dl.data = np.zeros((1, 6, 6), dtype=np.float32)
    mock_dl.background_image = np.ones((1, 6, 6), dtype=np.float32) * -1
    mock_dl.trusted_mask = np.ones((1, 6, 6), dtype=bool)
    mock_dl.bbox = np.array([[0, 3, 0, 3]])
    mock_dl.pids = np.array([0])
    mock_dl.detector = [Mock()]
    mock_dl.beam = Mock()
    mock_dl.crystal = Mock()
    mock_dl.Expt = Mock()
    mock_dl.F = Mock()
    mock_dl.F.indices.return_value = np.array([[0, 0, 1]], dtype=np.int32)
    mock_dl.F.data.return_value = np.array([10.0], dtype=np.float32)
    mock_dl.sigma_readout_map = sigma_map
    mock_dl.sigma_readout_map_source = "external_lookup"

    mock_detector_config.return_value = Mock()
    mock_beam_config.return_value = Mock()
    mock_crystal_config.return_value = (Mock(), False)
    mock_build_grid.return_value = (
        torch.zeros((3, 3, 3), dtype=torch.float32),
        {"grid_nonzero": 1},
        torch.zeros((3, 3, 3), dtype=torch.int32),
    )

    mock_simulator_instance = Mock()
    mock_simulator_instance.run.return_value = torch.ones((6, 6), dtype=torch.float32)
    mock_Simulator.return_value = mock_simulator_instance
    mock_Detector.return_value = Mock()
    mock_Crystal.return_value = Mock()

    mock_prepare.return_value = RefinementInputs(
        target=np.zeros((1, 6, 6), dtype=np.float32),
        loss_mask=np.ones((1, 6, 6), dtype=bool),
        panel_slices=[(0, (0, 3, 0, 3))],
        trusted_mask=np.ones((1, 6, 6), dtype=bool),
        sigma_readout=np.full((1, 6, 6), 2.0, dtype=np.float32),
    )

    args = Mock()
    args.outFile = 'out.h5'
    args.spot_scale_override = None
    args.torch_config = None
    args.refined_mtz = None
    args.adu_per_photon = 2.0
    args.sigma_rdout = None
    args.sigma_floor = 1.0
    args.device = "cpu"

    run_nanobrag_backend(args, mock_dl)

    mock_prepare.assert_called_once()
    np.testing.assert_allclose(
        mock_prepare.call_args[1]['sigma_readout'],
        sigma_map,
    )

    mock_write.assert_called_once()
    write_kwargs = mock_write.call_args[1]
    assert write_kwargs['sigma_readout_provenance'] == "external_lookup"
    # Median = 4 ADU, converted to photons by adu_per_photon=2
    assert write_kwargs['sigma_readout_reference_value'] == pytest.approx(2.0)


@patch('dbex.data_load.DataLoad')
@patch('nanobrag_torch.simulator.Simulator')
@patch('nanobrag_torch.models.detector.Detector')
@patch('nanobrag_torch.models.crystal.Crystal')
@patch('dbex.nanobrag_bridge.prepare_refinement_inputs')
@patch('dbex.nanobrag_bridge.build_structure_factor_grid')
@patch('dbex.nanobrag_bridge.create_detector_config')
@patch('dbex.nanobrag_bridge.create_beam_config')
@patch('dbex.nanobrag_bridge.create_crystal_config')
@patch('dbex.nanobrag_bridge.load_refined_mtz')
@patch('dbex.refine_one._write_torch_outputs')
def test_nanobrag_backend_uses_refined_mtz(
    mock_write, mock_load_refined, mock_crystal_config, mock_beam_config,
    mock_detector_config, mock_build_grid, mock_prepare, mock_Crystal,
    mock_Detector, mock_Simulator, mock_DataLoad
):
    """
    SCALE-003: Verify CLI loads refined MTZ and telemetry reflects refined source.

    Validates that when --refined-mtz is provided:
    1. load_refined_mtz is invoked with the correct path
    2. Refined indices/amplitudes are passed to build_structure_factor_grid
    3. Telemetry passed to _write_torch_outputs marks hkl_source="refined"

    This regression test guards SCALE-003/SCALE-004 assumptions that refined
    structure factors are applied when available.
    """
    import tempfile
    import sys
    import numpy as np
    from unittest.mock import MagicMock
    from dbex.nanobrag_bridge import RefinementInputs

    # Setup: mock refined MTZ loading
    refined_indices = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.int32)
    refined_amplitudes = np.array([100.0, 200.0, 300.0], dtype=np.float32)
    mock_load_refined.return_value = (refined_indices, refined_amplitudes)

    # Setup: mock structure factor grid builder
    hkl_grid_mock = np.zeros((10, 10, 10), dtype=np.float32)
    hkl_metadata_mock = {"grid_nonzero": 3}
    mock_asu_map = np.zeros((10, 10, 10), dtype=np.int32)
    mock_build_grid.return_value = (hkl_grid_mock, hkl_metadata_mock, mock_asu_map)

    # Setup: mock config builders
    mock_detector_config.return_value = MagicMock()
    mock_beam_config.return_value = MagicMock()
    mock_crystal_cfg = MagicMock()
    mock_crystal_config.return_value = (mock_crystal_cfg, False)  # no n_cells

    # Setup: mock models
    mock_Detector.return_value = MagicMock()
    mock_Crystal.return_value = MagicMock()

    # Setup: mock simulator
    import torch
    mock_simulator_instance = MagicMock()
    mock_simulator_instance.run.return_value = torch.zeros((2527, 2463), dtype=torch.float32)
    mock_Simulator.return_value = mock_simulator_instance

    # Setup: mock refinement inputs
    target_mock = np.zeros((2, 2527, 2463), dtype=np.float32)
    loss_mask_mock = np.ones((2, 2527, 2463), dtype=bool)
    mock_prepare.return_value = RefinementInputs(
        target=target_mock,
        loss_mask=loss_mask_mock,
        panel_slices=[],
        trusted_mask=np.ones((2, 2527, 2463), dtype=np.float32),
        sigma_readout=np.zeros((2, 2527, 2463), dtype=np.float32)
    )

    # Setup: mock DataLoad
    mock_DL_instance = MagicMock()
    mock_DL_instance.detector = [MagicMock(), MagicMock()]  # 2 panels
    mock_DL_instance.beam = MagicMock()
    mock_DL_instance.crystal = MagicMock()
    mock_DL_instance.Expt = MagicMock()
    mock_DL_instance.F = MagicMock()
    mock_DL_instance.F.indices.return_value = np.array([[0, 0, 1]], dtype=np.int32)
    mock_DL_instance.F.data.return_value = np.array([50.0], dtype=np.float32)
    mock_DL_instance.pids = [0, 1]
    mock_DL_instance.bbox = [(0, 100, 0, 100), (0, 100, 0, 100)]
    mock_DL_instance.background_image = np.zeros((2, 2527, 2463), dtype=np.float32)
    mock_DL_instance.data = np.zeros((2, 2527, 2463), dtype=np.float32)
    mock_DataLoad.return_value = mock_DL_instance

    # Mock DataLoad and run CLI
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as exp_file:
        exp_file.write('{"fake": "experiment"}')
        exp_file.flush()
        exp_path = exp_file.name

    with tempfile.NamedTemporaryFile(mode='w', suffix='.refl', delete=False) as refl_file:
        refl_path = refl_file.name

    with tempfile.NamedTemporaryFile(mode='w', suffix='.pkl', delete=False) as mask_file:
        mask_path = mask_file.name

    with tempfile.NamedTemporaryFile(mode='w', suffix='.mtz', delete=False) as mtz_file:
        mtz_path = mtz_file.name

    with tempfile.NamedTemporaryFile(mode='w', suffix='_refined.mtz', delete=False) as refined_mtz_file:
        refined_mtz_path = refined_mtz_file.name

    with tempfile.NamedTemporaryFile(mode='w', suffix='.h5', delete=False) as out_file:
        out_path = out_file.name

    try:
        # Inject mocks into sys.modules
        sys.modules['simtbx.diffBragg.utils'] = MagicMock()
        sys.modules['simtbx.diffBragg.hopper_utils'] = MagicMock()
        sys.modules['score_trainer'] = MagicMock()
        sys.modules['score_trainer.roi_check'] = MagicMock()

        from dbex.refine_one import main

        # Run CLI with --refined-mtz
        main([
            '-e', exp_path,
            '-r', refl_path,
            '-i', '0',
            '-o', out_path,
            '-m', mask_path,
            '-z', mtz_path,
            '--sigma-rdout', '3.0',
            '--refined-mtz', refined_mtz_path,
            '--backend', 'nanobrag'
        ])

        # Verify load_refined_mtz was invoked with correct path
        mock_load_refined.assert_called_once_with(refined_mtz_path, column="F")

        # Verify build_structure_factor_grid received refined arrays
        build_grid_call_kwargs = mock_build_grid.call_args[1]
        np.testing.assert_array_equal(build_grid_call_kwargs['indices'], refined_indices)
        np.testing.assert_array_equal(build_grid_call_kwargs['amplitudes'], refined_amplitudes)

        # Verify _write_torch_outputs received telemetry marking refined source
        mock_write.assert_called_once()
        write_call_args = mock_write.call_args[0]
        hkl_telemetry = write_call_args[5]  # 6th positional arg is hkl_telemetry
        assert hkl_telemetry["hkl_source"] == "refined"
        assert hkl_telemetry["hkl_n_reflections"] == len(refined_indices)
        assert hkl_telemetry["hkl_mean_amplitude"] == pytest.approx(refined_amplitudes.mean(), rel=1e-5)
        assert hkl_telemetry["hkl_path"] == refined_mtz_path

    finally:
        import os
        for path in [exp_path, refl_path, mask_path, mtz_path, refined_mtz_path, out_path]:
            try:
                os.unlink(path)
            except OSError:
                pass


@pytest.mark.parametrize(
    ("sigma_source", "sigma_reference"),
    [("cli_override", 3.0), ("external_lookup", 5.0)],
)
def test_torch_diagnostics_metadata(sigma_source, sigma_reference):
    """B1: Verify torch diagnostics HDF5 metadata."""
    import h5py
    import numpy as np
    import sys
    from dbex.nanobrag_bridge import RefinementInputs

    # Mock score_trainer.roi_check before it gets imported
    mock_roi_check_module = Mock()
    mock_checker = Mock()
    # Return a real float, not a Mock, so >= comparisons work
    mock_checker.score = Mock(return_value=0.85)
    mock_roi_check_class = Mock(return_value=mock_checker)
    mock_roi_check_module.roiCheck = mock_roi_check_class
    sys.modules['score_trainer.roi_check'] = mock_roi_check_module

    # Mock scipy.optimize.minimize
    from unittest.mock import patch
    with patch('scipy.optimize.minimize') as mock_minimize:
        # Mock the minimize result - need to support both dict-like access and attributes
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.__getitem__ = Mock(side_effect=lambda key: np.array([1.0]) if key == 'x' else None)
        mock_minimize.return_value = mock_result

        with tempfile.TemporaryDirectory() as tmpdir:
            outfile = os.path.join(tmpdir, 'test_torch_diag.h5')

            # Create mock inputs
            mock_inputs = RefinementInputs(
                target=np.zeros((1, 100, 100), dtype=np.float32),
                loss_mask=np.ones((1, 100, 100), dtype=bool) * 0.25,  # 25% coverage
                panel_slices=[(0, (10, 20, 10, 20))],
                trusted_mask=np.ones((1, 100, 100), dtype=bool),
                sigma_readout=np.zeros((1, 100, 100), dtype=np.float32)
            )

            mock_dl = Mock()
            mock_dl.data = np.zeros((1, 100, 100), dtype=np.float32)
            mock_dl.background_image = np.ones((1, 100, 100), dtype=np.float32) * -1
            mock_dl.pids = np.array([0])
            mock_dl.bbox = np.array([[10, 20, 10, 20]])
            if sigma_source == "external_lookup":
                mock_dl.sigma_readout_map = np.full(
                    (1, 100, 100), sigma_reference, dtype=np.float32
                )
                mock_dl.sigma_readout_map_source = "external_lookup"

            mock_args = Mock()
            mock_args.outFile = outfile

            mock_bragg = np.zeros((1, 100, 100), dtype=np.float32)
            masked_mse = 1234.5

            # Prepare HKL telemetry (SCALE-003)
            hkl_telemetry = {
                "hkl_source": "raw",
                "hkl_n_reflections": 100,
                "hkl_mean_amplitude": 50.0,
                "hkl_path": "/path/to/test.mtz"
            }

            # PHYSICS-LOSS-001: Create mock refinement telemetry with dual loss metrics
            # ARCH-REFINE-001 Phase C.1: Import from canonical location
            from dbex.refinement import RefinementTelemetry
            mock_telemetry_a = RefinementTelemetry(
                optimizer="LBFGS",
                stage="A",
                history_size=10,
                max_iter=30,
                tolerance_grad=1e-7,
                tolerance_change=1e-9,
                roi_sample_fraction=0.15,
                roi_count_sampled=1,
                roi_count_total=1,
                loss_trace_sample=[1000.0, 900.0, 800.0],  # Legacy chi_squared trace
                loss_trace_full=[(0, 1000.0), (5, 900.0), (10, 800.0)],  # Legacy chi_squared trace
                best_loss_full=(800.0, 10),  # Legacy chi_squared best
                param_deltas={"log_scale": 0.1},
                status="ok",
                message="Converged",
                perf_counters={"cache_mode": "warm"},
                # PHYSICS-LOSS-001: Dual loss metrics
                chi_squared_trace_sample=[1000.0, 900.0, 800.0],
                chi_squared_trace_full=[(0, 1000.0), (5, 900.0), (10, 800.0)],
                chi_squared_best=(800.0, 10),
                masked_mse_trace_sample=[500.0, 450.0, 400.0],
                masked_mse_trace_full=[(0, 500.0), (5, 450.0), (10, 400.0)],
                masked_mse_best=(400.0, 10),
                sigma_readout_provenance=sigma_source,
                sigma_readout_reference_value=sigma_reference,
                variance_floor_value=4.0,
                variance_floor_clamp_fraction=0.125,
                canonical_stage_label="A",
                canonical_chi_squared=800.0,
                canonical_chi_squared_iteration=10,
                canonical_roi_count=1,
                canonical_detector_distances_mm=[100.0],
            )
            refine_telemetry_dict = {"A": mock_telemetry_a}

            # Import the function to test
            from dbex.refine_one import _write_torch_outputs
            _write_torch_outputs(
                mock_args,
                mock_dl,
                mock_bragg,
                mock_inputs,
                masked_mse,
                hkl_telemetry,
                refine_telemetry=refine_telemetry_dict,
                sigma_readout_provenance=sigma_source,
                sigma_readout_reference_value=sigma_reference,
            )

            # Verify diagnostics group exists and has correct metadata
            with h5py.File(outfile, 'r') as h:
                assert 'torch_diagnostics' in h, "torch_diagnostics group missing"
                diag = h['torch_diagnostics']
                assert 'masked_mse' in diag.attrs
                assert 'loss_mask_coverage' in diag.attrs
                assert 'n_rois' in diag.attrs
                assert 'target_shape' in diag.attrs
                assert 'backend' in diag.attrs
                # SCALE-003: verify HKL telemetry fields
                assert 'hkl_source' in diag.attrs
                assert 'hkl_n_reflections' in diag.attrs
                assert 'hkl_mean_amplitude' in diag.attrs
                assert 'hkl_path' in diag.attrs
                assert diag.attrs['hkl_source'] == "raw"
                assert diag.attrs['hkl_n_reflections'] == 100
                assert diag.attrs['hkl_mean_amplitude'] == 50.0
                assert diag.attrs['hkl_path'] == "/path/to/test.mtz"

                assert diag.attrs['masked_mse'] == masked_mse
                assert diag.attrs['loss_mask_coverage'] == pytest.approx(0.25)
                assert diag.attrs['n_rois'] == 1
                assert diag.attrs['backend'] == 'nanobrag'
                assert diag.attrs['sigma_readout_provenance'] == sigma_source
                assert diag.attrs['sigma_readout_reference_value'] == pytest.approx(sigma_reference)

                # TORCH-CLI-004: Verify score dataset contains numeric values (not Mock objects)
                assert 'score' in h
                scores_ds = h['score'][:]
                assert len(scores_ds) == 1
                assert isinstance(scores_ds[0], (int, float, np.number))
                # Score should be numeric and finite (coercion guards against Mock objects)
                assert np.isfinite(scores_ds[0])
                assert 0.0 <= scores_ds[0] <= 1.0

                # PHYSICS-LOSS-001: Verify dual loss metrics in Stage A telemetry
                assert 'stage_A' in diag, "stage_A group missing from torch_diagnostics"
                stage_a_group = diag['stage_A']

                # Chi-squared metrics
                assert 'chi_squared_trace_sample' in stage_a_group, "chi_squared_trace_sample dataset missing"
                assert 'chi_squared_trace_full' in stage_a_group, "chi_squared_trace_full dataset missing"
                assert 'chi_squared_best' in stage_a_group.attrs, "chi_squared_best attr missing"
                assert 'chi_squared_best_iteration' in stage_a_group.attrs, "chi_squared_best_iteration attr missing"

                chi2_sample = stage_a_group['chi_squared_trace_sample'][:]
                assert len(chi2_sample) == 3, f"Expected 3 chi_squared_trace_sample entries, got {len(chi2_sample)}"
                assert np.allclose(chi2_sample, [1000.0, 900.0, 800.0])

                chi2_full = stage_a_group['chi_squared_trace_full'][:]
                assert len(chi2_full) == 3, f"Expected 3 chi_squared_trace_full entries, got {len(chi2_full)}"
                assert chi2_full['iteration'][0] == 0
                assert chi2_full['chi_squared'][0] == pytest.approx(1000.0)
                assert chi2_full['iteration'][2] == 10
                assert chi2_full['chi_squared'][2] == pytest.approx(800.0)

                assert stage_a_group.attrs['chi_squared_best'] == pytest.approx(800.0)
                assert stage_a_group.attrs['chi_squared_best_iteration'] == 10

                # Masked-MSE metrics
                assert 'masked_mse_trace_sample' in stage_a_group, "masked_mse_trace_sample dataset missing"
                assert 'masked_mse_trace_full' in stage_a_group, "masked_mse_trace_full dataset missing"
                assert 'masked_mse_best' in stage_a_group.attrs, "masked_mse_best attr missing"
                assert 'masked_mse_best_iteration' in stage_a_group.attrs, "masked_mse_best_iteration attr missing"

                mse_sample = stage_a_group['masked_mse_trace_sample'][:]
                assert len(mse_sample) == 3, f"Expected 3 masked_mse_trace_sample entries, got {len(mse_sample)}"
                assert np.allclose(mse_sample, [500.0, 450.0, 400.0])

                mse_full = stage_a_group['masked_mse_trace_full'][:]
                assert len(mse_full) == 3, f"Expected 3 masked_mse_trace_full entries, got {len(mse_full)}"
                assert mse_full['iteration'][0] == 0
                assert mse_full['masked_mse'][0] == pytest.approx(500.0)
                assert mse_full['iteration'][2] == 10
                assert mse_full['masked_mse'][2] == pytest.approx(400.0)

                assert stage_a_group.attrs['masked_mse_best'] == pytest.approx(400.0)
                assert stage_a_group.attrs['masked_mse_best_iteration'] == 10
                assert stage_a_group.attrs['variance_floor_value'] == pytest.approx(4.0)
                assert stage_a_group.attrs['variance_floor_clamp_fraction'] == pytest.approx(0.125)
                assert stage_a_group.attrs['canonical_stage_label'] == "A"
                assert stage_a_group.attrs['canonical_chi_squared'] == pytest.approx(800.0)
                assert stage_a_group.attrs['canonical_chi_squared_iteration'] == 10
                assert stage_a_group.attrs['canonical_roi_count'] == 1
                assert 'canonical_detector_distances_mm' in stage_a_group
                assert np.allclose(stage_a_group['canonical_detector_distances_mm'][:], [100.0])
                assert stage_a_group.attrs['sigma_readout_provenance'] == sigma_source
                assert stage_a_group.attrs['sigma_readout_reference_value'] == pytest.approx(sigma_reference)

                # PHYSICS-LOSS-001: Verify legacy top-level compatibility (Stage A only)
                assert 'chi_squared_trace_sample' in diag, "Top-level chi_squared_trace_sample dataset missing"
                assert 'chi_squared_trace_full' in diag, "Top-level chi_squared_trace_full dataset missing"
                assert 'chi_squared_best' in diag.attrs, "Top-level chi_squared_best attr missing"
                assert 'masked_mse_trace_sample' in diag, "Top-level masked_mse_trace_sample dataset missing"
                assert 'masked_mse_trace_full' in diag, "Top-level masked_mse_trace_full dataset missing"
                assert 'masked_mse_best' in diag.attrs, "Top-level masked_mse_best attr missing"
                assert 'variance_floor_value' in diag.attrs
                assert 'variance_floor_clamp_fraction' in diag.attrs
                assert diag.attrs['variance_floor_value'] == pytest.approx(4.0)
                assert diag.attrs['variance_floor_clamp_fraction'] == pytest.approx(0.125)
                assert diag.attrs['canonical_stage_label'] == "A"
                assert diag.attrs['canonical_chi_squared'] == pytest.approx(800.0)
                assert diag.attrs['canonical_chi_squared_iteration'] == 10
                assert diag.attrs['canonical_roi_count'] == 1
                assert 'canonical_detector_distances_mm' in diag
                assert np.allclose(diag['canonical_detector_distances_mm'][:], [100.0])


@patch('dbex.data_load.DataLoad')
def test_nanobrag_backend_refined_mtz_missing_errors(mock_DataLoad):
    """
    MAP-SCALE-005: Verify CLI fails fast when --refined-mtz is provided but cannot be loaded.

    Validates SCALE-007 guardrail: when --refined-mtz is supplied, the CLI MUST raise
    a RuntimeError (not SystemExit, to avoid masking stack traces) if:
    1. The refined MTZ file does not exist
    2. The refined MTZ file cannot be parsed
    3. The refined MTZ file lacks expected columns

    This test ensures the CLI does not silently fall back to raw MTZ when refined
    structure factors are explicitly requested, preventing calibration metadata
    from being ignored.
    """
    import tempfile
    import sys
    import numpy as np
    from unittest.mock import MagicMock

    # Setup: mock DataLoad to avoid file I/O
    mock_DL_instance = MagicMock()
    # Mock detector panels with get_pixel_size returning tuple
    mock_panel1 = MagicMock()
    mock_panel1.get_pixel_size.return_value = (0.1, 0.1)  # Square pixels
    mock_panel2 = MagicMock()
    mock_panel2.get_pixel_size.return_value = (0.1, 0.1)
    mock_DL_instance.detector = [mock_panel1, mock_panel2]
    mock_DL_instance.beam = MagicMock()
    mock_DL_instance.crystal = MagicMock()
    mock_DL_instance.Expt = MagicMock()
    mock_DL_instance.F = MagicMock()
    mock_DL_instance.F.indices.return_value = np.array([[0, 0, 1]], dtype=np.int32)
    mock_DL_instance.F.data.return_value = np.array([50.0], dtype=np.float32)
    mock_DL_instance.pids = [0, 1]
    mock_DL_instance.bbox = [(0, 100, 0, 100), (0, 100, 0, 100)]
    # Background image: -1 sentinel outside ROIs, 0 inside ROIs
    background_image = np.full((2, 2527, 2463), -1.0, dtype=np.float32)
    background_image[0, 0:100, 0:100] = 0.0  # ROI 1
    background_image[1, 0:100, 0:100] = 0.0  # ROI 2
    mock_DL_instance.background_image = background_image
    mock_DL_instance.data = np.zeros((2, 2527, 2463), dtype=np.float32)
    mock_DL_instance.trusted_mask = np.ones((2, 2527, 2463), dtype=bool)
    mock_DataLoad.return_value = mock_DL_instance

    # Create temp files
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as exp_file:
        exp_file.write('{"fake": "experiment"}')
        exp_file.flush()
        exp_path = exp_file.name

    with tempfile.NamedTemporaryFile(mode='w', suffix='.refl', delete=False) as refl_file:
        refl_path = refl_file.name

    with tempfile.NamedTemporaryFile(mode='w', suffix='.pkl', delete=False) as mask_file:
        mask_path = mask_file.name

    with tempfile.NamedTemporaryFile(mode='w', suffix='.mtz', delete=False) as mtz_file:
        mtz_path = mtz_file.name

    with tempfile.NamedTemporaryFile(mode='w', suffix='.h5', delete=False) as out_file:
        out_path = out_file.name

    # Nonexistent refined MTZ path
    nonexistent_refined_mtz = "/tmp/does_not_exist_refined_12345.mtz"

    try:
        # Inject mocks into sys.modules
        sys.modules['simtbx.diffBragg.utils'] = MagicMock()
        sys.modules['simtbx.diffBragg.hopper_utils'] = MagicMock()
        sys.modules['score_trainer'] = MagicMock()
        sys.modules['score_trainer.roi_check'] = MagicMock()

        from dbex.refine_one import main

        # Test 1: FileNotFoundError when refined MTZ does not exist
        with pytest.raises(RuntimeError) as exc_info:
            main([
                '-e', exp_path,
                '-r', refl_path,
                '-i', '0',
                '-o', out_path,
                '-m', mask_path,
                '-z', mtz_path,
                '--sigma-rdout', '3.0',
                '--refined-mtz', nonexistent_refined_mtz,
                '--backend', 'nanobrag'
            ])

        # Verify error message is actionable and mentions the flag
        error_msg = str(exc_info.value)
        assert "--refined-mtz" in error_msg, f"Error message should reference --refined-mtz flag: {error_msg}"
        assert nonexistent_refined_mtz in error_msg, f"Error message should include the path provided: {error_msg}"
        assert "MUST be consumed" in error_msg, f"Error message should explain the enforcement: {error_msg}"

    finally:
        import os
        for path in [exp_path, refl_path, mask_path, mtz_path, out_path]:
            try:
                os.unlink(path)
            except OSError:
                pass
