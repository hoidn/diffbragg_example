"""
Tests for refine_one CLI backend dispatch.

Per docs/TESTING_GUIDE.md, run with:
    KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_refine_one_cli.py
"""
import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
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

    # Mock beam and crystal
    mock_dl.beam = Mock()
    mock_dl.crystal = Mock()

    # Mock MTZ Miller array
    mock_F = Mock()
    mock_F.indices.return_value = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
    mock_F.data.return_value = np.array([100.0, 200.0, 150.0])
    mock_dl.F = mock_F

    # Setup mock bridge output
    mock_inputs = RefinementInputs(
        target=np.zeros((1, 100, 100), dtype=np.float32),
        loss_mask=np.ones((1, 100, 100), dtype=bool),
        panel_slices=[(0, (10, 20, 10, 20))],
        trusted_mask=np.ones((1, 100, 100), dtype=bool)
    )
    mock_prepare.return_value = mock_inputs

    # Mock structure factor grid (SCALE-001: unscaled)
    mock_hkl_grid = torch.zeros((3, 3, 3), dtype=torch.float32)
    mock_hkl_metadata = {
        'h_min': 0, 'h_max': 2, 'k_min': 0, 'k_max': 2, 'l_min': 0, 'l_max': 2,
        'grid_nonzero': 3
    }
    mock_build_grid.return_value = (mock_hkl_grid, mock_hkl_metadata)

    # Mock config objects
    mock_detector_config.return_value = Mock()
    mock_beam_config.return_value = Mock()
    mock_crystal_config.return_value = Mock()

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

    # Setup mock args with spot_scale_override
    args = Mock()
    args.outFile = 'test.h5'
    args.spot_scale_override = 4.0  # sqrt(4.0) = 2.0

    run_nanobrag_backend(args, mock_dl)

    # Verify structure factor grid was built (SCALE-001: unscaled)
    mock_build_grid.assert_called_once()
    call_kwargs = mock_build_grid.call_args[1]
    assert 'indices' in call_kwargs
    assert 'amplitudes' in call_kwargs

    # Verify configs were created per panel
    mock_detector_config.assert_called_once()
    mock_beam_config.assert_called_once()
    mock_crystal_config.assert_called_once()

    # Verify models were instantiated
    mock_Detector.assert_called_once()
    mock_Crystal.assert_called_once()

    # Verify HKL data was attached to crystal model
    assert mock_crystal_instance.hkl_data is mock_hkl_grid
    assert mock_crystal_instance.hkl_metadata == mock_hkl_metadata

    # Verify simulator was run
    mock_Simulator.assert_called_once()
    mock_simulator_instance.run.assert_called_once()

    # Verify output writer was called
    mock_write.assert_called_once()

    # Verify SCALE-002: sqrt(spot_scale_override) applied post-simulation
    # The Bragg array passed to _write_torch_outputs should be scaled
    bragg_array = mock_write.call_args[0][2]
    expected_scaled = 1000.0 * np.sqrt(4.0)  # 1000.0 * 2.0 = 2000.0
    assert bragg_array[0, 0, 0] == pytest.approx(expected_scaled, rel=1e-5)


def test_torch_diagnostics_metadata():
    """B1: Verify torch diagnostics HDF5 metadata."""
    import h5py
    import numpy as np
    import sys
    from dbex.nanobrag_bridge import RefinementInputs

    # Mock score_trainer.roi_check before it gets imported
    mock_roi_check_module = Mock()
    mock_checker = Mock()
    mock_checker.score.return_value = 0.85
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
                trusted_mask=np.ones((1, 100, 100), dtype=bool)
            )

            mock_dl = Mock()
            mock_dl.data = np.zeros((1, 100, 100), dtype=np.float32)
            mock_dl.background_image = np.ones((1, 100, 100), dtype=np.float32) * -1
            mock_dl.pids = np.array([0])
            mock_dl.bbox = np.array([[10, 20, 10, 20]])

            mock_args = Mock()
            mock_args.outFile = outfile

            mock_bragg = np.zeros((1, 100, 100), dtype=np.float32)
            masked_mse = 1234.5

            # Import the function to test
            from dbex.refine_one import _write_torch_outputs
            _write_torch_outputs(mock_args, mock_dl, mock_bragg, mock_inputs, masked_mse)

            # Verify diagnostics group exists and has correct metadata
            with h5py.File(outfile, 'r') as h:
                assert 'torch_diagnostics' in h, "torch_diagnostics group missing"
                diag = h['torch_diagnostics']
                assert 'masked_mse' in diag.attrs
                assert 'loss_mask_coverage' in diag.attrs
                assert 'n_rois' in diag.attrs
                assert 'target_shape' in diag.attrs
                assert 'backend' in diag.attrs

                assert diag.attrs['masked_mse'] == masked_mse
                assert diag.attrs['loss_mask_coverage'] == pytest.approx(0.25)
                assert diag.attrs['n_rois'] == 1
                assert diag.attrs['backend'] == 'nanobrag'
