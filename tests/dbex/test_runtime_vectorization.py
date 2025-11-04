"""
Runtime Vectorization Tests (RUNTIME-VEC-001)

Tests for runtime vectorization requirements and source weighting behavior.
Per spec-db-runtime.md and docs/pytorch_runtime_checklist.md §4:
- Source weights are parsed but IGNORED (equal weighting)
- CLI -lambda is authoritative for all sources
- Correlation ≥0.999 and |sum_ratio−1| ≤5e-3 between weighted and equal-weight runs
"""

import os
import sys
import subprocess
import tempfile
import struct
import json
import pytest
import numpy as np
from pathlib import Path


class TestRuntimeVectorization:
    """Test suite for runtime vectorization requirements."""

    def test_source_weights_ignored_per_spec(self):
        """
        Test that source weights are parsed but ignored per equal-weight spec.

        Validates RUNTIME-VEC-001 exit criterion 1:
        - Run CLI with sourcefile containing varied weights
        - Run CLI with sourcefile containing equal weights
        - Compare outputs: correlation ≥0.999, |sum_ratio−1| ≤5e-3

        References:
        - docs/pytorch_runtime_checklist.md:33 (equal weighting rule)
        - docs/architecture/pytorch_design.md:90 (thresholds)
        - RUNTIME-001, SCALE-001, SCALE-002 findings
        """
        # Get artifact directory from environment
        artifact_dir = os.environ.get('RUNTIME_VEC_ARTIFACT_DIR')
        if artifact_dir is None:
            pytest.skip("RUNTIME_VEC_ARTIFACT_DIR not set; required for artifact routing")

        artifact_path = Path(artifact_dir)
        artifact_path.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create sourcefile with varied weights (should be ignored)
            sourcefile_weighted = tmpdir_path / "sources_weighted.txt"
            sourcefile_weighted.write_text("""# Sources with varied weights (should be ignored)
# X    Y    Z    weight  wavelength
0.0   0.0   10.0   1.0     6.2e-10
0.1   0.0   10.0   2.5     6.2e-10
-0.1  0.0   10.0   0.3     6.2e-10
""")

            # Create sourcefile with equal weights
            sourcefile_equal = tmpdir_path / "sources_equal.txt"
            sourcefile_equal.write_text("""# Sources with equal weights
# X    Y    Z    weight  wavelength
0.0   0.0   10.0   1.0     6.2e-10
0.1   0.0   10.0   1.0     6.2e-10
-0.1  0.0   10.0   1.0     6.2e-10
""")

            # Output files
            output_weighted = tmpdir_path / "weighted.bin"
            output_equal = tmpdir_path / "equal.bin"

            # Common CLI parameters (minimal detector, fast run per input.md:34)
            common_args = [
                sys.executable, '-m', 'nanobrag_torch',
                '-default_F', '100',
                '-cell', '100', '100', '100', '90', '90', '90',
                '-lambda', '6.2',  # Authoritative wavelength per spec
                '-detpixels', '128',  # Small detector for speed (input.md:34)
                '-distance', '100',
                '-oversample', '1',  # Minimal oversample
            ]

            # Environment: KMP_DUPLICATE_LIB_OK + disable compile per RUNTIME-001
            env = os.environ.copy()
            env['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
            env['NANOBRAGG_DISABLE_COMPILE'] = '1'

            # Run weighted case
            cmd_weighted = common_args + [
                '-sourcefile', str(sourcefile_weighted),
                '-floatfile', str(output_weighted)
            ]

            result_weighted = subprocess.run(
                cmd_weighted,
                capture_output=True,
                text=True,
                env=env
            )

            if result_weighted.returncode != 0:
                # Environment freeze block: record and fail
                blocker_log = artifact_path / "blocker_log.txt"
                blocker_log.write_text(
                    f"Weighted run failed:\nCommand: {' '.join(cmd_weighted)}\n"
                    f"Stdout: {result_weighted.stdout}\n"
                    f"Stderr: {result_weighted.stderr}\n"
                )
                pytest.fail(f"Weighted CLI run failed (see {blocker_log}): {result_weighted.stderr}")

            # Run equal-weight case
            cmd_equal = common_args + [
                '-sourcefile', str(sourcefile_equal),
                '-floatfile', str(output_equal)
            ]

            result_equal = subprocess.run(
                cmd_equal,
                capture_output=True,
                text=True,
                env=env
            )

            if result_equal.returncode != 0:
                blocker_log = artifact_path / "blocker_log.txt"
                blocker_log.write_text(
                    f"Equal-weight run failed:\nCommand: {' '.join(cmd_equal)}\n"
                    f"Stdout: {result_equal.stdout}\n"
                    f"Stderr: {result_equal.stderr}\n"
                )
                pytest.fail(f"Equal CLI run failed (see {blocker_log}): {result_equal.stderr}")

            # Read output images
            with open(output_weighted, 'rb') as f:
                data_weighted = f.read()
            with open(output_equal, 'rb') as f:
                data_equal = f.read()

            # Parse binary floatfiles (32-bit floats, row-major)
            n_pixels = 128 * 128
            assert len(data_weighted) == n_pixels * 4, "Weighted output size mismatch"
            assert len(data_equal) == n_pixels * 4, "Equal output size mismatch"

            floats_weighted = struct.unpack('f' * n_pixels, data_weighted)
            floats_equal = struct.unpack('f' * n_pixels, data_equal)

            img_weighted = np.array(floats_weighted).reshape(128, 128)
            img_equal = np.array(floats_equal).reshape(128, 128)

            # Compute metrics (per docs/architecture/pytorch_design.md:90)
            correlation = np.corrcoef(img_weighted.flatten(), img_equal.flatten())[0, 1]
            sum_weighted = img_weighted.sum()
            sum_equal = img_equal.sum()
            sum_ratio = sum_weighted / sum_equal if sum_equal > 0 else 0.0
            sum_ratio_delta = abs(sum_ratio - 1.0)

            # Capture metrics JSON on failure or always for reproducibility
            metrics = {
                "correlation": float(correlation),
                "sum_weighted": float(sum_weighted),
                "sum_equal": float(sum_equal),
                "sum_ratio": float(sum_ratio),
                "sum_ratio_delta": float(sum_ratio_delta),
                "threshold_correlation": 0.999,
                "threshold_sum_ratio_delta": 5e-3,
                "pass": bool(correlation >= 0.999 and sum_ratio_delta <= 5e-3)
            }

            metrics_file = artifact_path / "mapping_metrics.json"
            with open(metrics_file, 'w') as f:
                json.dump(metrics, f, indent=2)

            # Assert thresholds (per docs/architecture/pytorch_design.md:90)
            assert correlation >= 0.999, (
                f"Correlation {correlation:.6f} < 0.999; weighted sources not ignored "
                f"(metrics: {metrics_file})"
            )
            assert sum_ratio_delta <= 5e-3, (
                f"|sum_ratio−1| = {sum_ratio_delta:.6f} > 5e-3; sum mismatch "
                f"(metrics: {metrics_file})"
            )

            # On success, write a summary
            summary_file = artifact_path / "source_weight_test_summary.txt"
            summary_file.write_text(
                f"RUNTIME-VEC-001: Source Weight Equal-Weight Validation\n"
                f"Correlation: {correlation:.6f} (≥0.999 ✓)\n"
                f"Sum ratio: {sum_ratio:.6f} (|Δ| = {sum_ratio_delta:.6f} ≤5e-3 ✓)\n"
                f"Weighted sum: {sum_weighted:.3e}\n"
                f"Equal sum: {sum_equal:.3e}\n"
                f"Metrics: {metrics_file}\n"
            )
