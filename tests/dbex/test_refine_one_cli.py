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


@patch('dbex.nanobrag_bridge.prepare_refinement_inputs')
@patch('dbex.refine_one._stub_bragg_tensor')
@patch('dbex.refine_one._write_torch_outputs')
def test_nanobrag_backend_calls_bridge(mock_write, mock_stub, mock_prepare):
    """A2: Verify nanobrag backend uses bridge helpers."""
    import numpy as np
    from dbex.nanobrag_bridge import RefinementInputs

    # Setup mock DataLoad
    mock_dl = Mock()
    mock_dl.data = np.zeros((1, 100, 100), dtype=np.float32)
    mock_dl.background_image = np.ones((1, 100, 100), dtype=np.float32) * -1
    mock_dl.trusted_mask = np.ones((1, 100, 100), dtype=bool)
    mock_dl.bbox = np.array([[10, 20, 10, 20]])
    mock_dl.pids = np.array([0])
    mock_dl.detector = Mock()

    # Setup mock bridge output
    mock_inputs = RefinementInputs(
        target=np.zeros((1, 100, 100), dtype=np.float32),
        loss_mask=np.ones((1, 100, 100), dtype=bool),
        panel_slices=[(0, (10, 20, 10, 20))],
        trusted_mask=np.ones((1, 100, 100), dtype=bool)
    )
    mock_prepare.return_value = mock_inputs
    mock_stub.return_value = np.zeros((1, 100, 100), dtype=np.float32)

    # Setup mock args
    args = Mock()
    args.outFile = 'test.h5'

    run_nanobrag_backend(args, mock_dl)

    # Verify bridge was called
    mock_prepare.assert_called_once()
    assert mock_prepare.call_args[1]['data'] is mock_dl.data
    assert mock_prepare.call_args[1]['background_image'] is mock_dl.background_image

    # Verify stub tensor was generated
    mock_stub.assert_called_once()

    # Verify output writer was called
    mock_write.assert_called_once()


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
