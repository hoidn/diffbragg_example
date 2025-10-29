"""
DB-AT-001 Parity Harness Test — Minimal scaffolding for reference parity baseline.

Per docs/parity_harness_spec.md §2 and input.md:8-10:
- Tests manifest integrity and checksum validation
- Loads golden data with [panel, slow, fast] ordering enforcement
- Validates pixel pitch guards
- Provides scaffolding for future correlation/RMSE threshold tests

This is Phase A (PARITY-HARNESS-002) scaffolding. Future loops will add:
- Parity metrics computation (correlation ≥ 0.99, RMSE thresholds)
- Trace capture and first divergence workflow
- Diff heatmap generation
- Full DB-AT-001 acceptance test implementation

Findings applied:
- CONFORMANCE-001: DB_AT selector contracts and environment flag usage
- GEOMETRY-001: Pixel pitch and [panel, slow, fast] ordering enforcement
- TESTING-003: Collect-only commands and artifact logging

Environment:
    export KMP_DUPLICATE_LIB_OK=TRUE
    pytest -v tests -k DB_AT_001
"""

import pytest
import numpy as np
from pathlib import Path

# Golden data loader
from tests.fixtures.parity_loader import load_golden_data, GoldenData


@pytest.fixture(scope="module")
def golden_dir():
    """
    Path to simple cubic golden data directory.

    Per docs/parity_harness_spec.md:28-41, golden data resides under
    tests/fixtures/golden_data/simple_cubic/.
    """
    repo_root = Path(__file__).parent.parent.parent
    golden_dir = repo_root / "tests/fixtures/golden_data/simple_cubic"

    if not golden_dir.exists():
        pytest.skip(
            f"Golden data directory not found: {golden_dir}\n"
            "Run scripts/generate_simple_cubic_golden.py to create it."
        )

    return golden_dir


@pytest.fixture(scope="module")
def simple_cubic_golden(golden_dir):
    """
    Load simple cubic golden data for parity testing.

    Returns GoldenData with:
        - bragg: Predicted Bragg intensities [slow, fast] float32
        - target: Background-subtracted targets [slow, fast] float32
        - loss_mask: Loss mask [slow, fast] bool
        - metadata: Configuration metadata dict
        - manifest: Full manifest dict
        - panel_id: Panel ID (default 0)

    Per docs/parity_harness_spec.md:36-37, checksums are validated on load.
    """
    golden_data = load_golden_data(
        golden_dir=golden_dir,
        panel_id=0,
        validate_checksums=True
    )
    return golden_data


class TestManifestIntegrity:
    """
    DB-AT-001 manifest integrity validation.

    Per input.md:10 (A3 checklist), minimal test must verify:
    - Manifest file exists and is valid JSON
    - All referenced files exist
    - SHA256 checksums match
    - Tensor shapes match manifest declarations
    - [panel, slow, fast] ordering is preserved
    """

    def test_manifest_integrity(self, simple_cubic_golden):
        """
        Validate manifest integrity and checksum validation.

        Per docs/parity_harness_spec.md:36-37, harness utilities MUST validate
        checksums before comparison to detect data corruption.

        Validates:
        - Manifest loaded successfully (checksums validated in fixture)
        - All tensors have expected shapes
        - Dtypes are correct (float32 for intensities, bool for masks)
        - [slow, fast] ordering preserved
        """
        golden = simple_cubic_golden

        # Manifest was validated in load_golden_data (checksums passed)
        assert golden.manifest is not None
        assert "files" in golden.manifest
        assert "dataset_name" in golden.manifest

        # Validate tensor shapes match metadata
        expected_shape = tuple(golden.metadata["shape"]["bragg"])

        assert golden.bragg.shape == expected_shape, \
            f"Bragg shape {golden.bragg.shape} != expected {expected_shape}"
        assert golden.target.shape == expected_shape, \
            f"Target shape {golden.target.shape} != expected {expected_shape}"
        assert golden.loss_mask.shape == expected_shape, \
            f"Loss mask shape {golden.loss_mask.shape} != expected {expected_shape}"

        # Validate dtypes
        assert golden.bragg.dtype == np.float32, \
            f"Bragg dtype {golden.bragg.dtype} != float32"
        assert golden.target.dtype == np.float32, \
            f"Target dtype {golden.target.dtype} != float32"
        assert golden.loss_mask.dtype == bool, \
            f"Loss mask dtype {golden.loss_mask.dtype} != bool"

        # Validate tensor ordering is [slow, fast] (2D per-panel)
        assert golden.bragg.ndim == 2, \
            f"Bragg should be 2D [slow, fast], got {golden.bragg.ndim}D"

        # Validate pixel pitch metadata exists
        assert "detector_config" in golden.metadata
        assert "pixel_size_mm" in golden.metadata["detector_config"]

        # Log success
        print(f"\n[DB-AT-001] Manifest integrity validated")
        print(f"[DB-AT-001] Dataset: {golden.manifest['dataset_name']}")
        print(f"[DB-AT-001] Panel ID: {golden.panel_id}")
        print(f"[DB-AT-001] Bragg shape: {golden.bragg.shape}")
        print(f"[DB-AT-001] Files validated: {len(golden.manifest['files'])}")

    def test_golden_data_sanity(self, simple_cubic_golden):
        """
        Sanity checks on golden data content.

        Validates:
        - Bragg tensor is non-negative
        - Target tensor has finite values
        - Loss mask has expected coverage (>0%, <100%)
        - Tensors are not all zeros
        """
        golden = simple_cubic_golden

        # Bragg should be non-negative
        assert np.all(golden.bragg >= 0), \
            "Bragg tensor contains negative values"

        # Target should be finite
        assert np.all(np.isfinite(golden.target)), \
            "Target tensor contains non-finite values"

        # Loss mask should have reasonable coverage
        loss_mask_coverage = np.mean(golden.loss_mask)
        assert loss_mask_coverage > 0, \
            "Loss mask is all False (no pixels in loss region)"
        assert loss_mask_coverage < 1.0, \
            "Loss mask is all True (implausible coverage)"

        # Tensors should not be all zeros
        assert np.sum(np.abs(golden.bragg)) > 0, \
            "Bragg tensor is all zeros"
        assert np.sum(np.abs(golden.target)) > 0, \
            "Target tensor is all zeros"

        # Log coverage
        print(f"\n[DB-AT-001] Loss mask coverage: {loss_mask_coverage:.2%}")
        print(f"[DB-AT-001] Bragg intensity sum: {np.sum(golden.bragg):.2e}")
        print(f"[DB-AT-001] Target intensity sum: {np.sum(golden.target):.2e}")

    def test_pixel_pitch_guard(self, simple_cubic_golden):
        """
        Validate pixel pitch square constraint.

        Per docs/spec-db-core.md:43, pixel pitch SHALL be square.
        Loader should have validated this during load.

        This test documents the guard explicitly for DB-AT-001.
        """
        golden = simple_cubic_golden

        # Pixel pitch validation happened in load_golden_data
        # (validate_pixel_pitch function)
        detector_config = golden.metadata["detector_config"]
        pixel_size_mm = detector_config["pixel_size_mm"]

        # For square pixels, this value represents both fast and slow dimensions
        assert pixel_size_mm > 0, \
            f"Pixel size {pixel_size_mm} must be positive"

        # Validate detector dimensions are reasonable
        spixels = detector_config["spixels"]
        fpixels = detector_config["fpixels"]

        assert spixels > 0 and fpixels > 0, \
            f"Detector dimensions ({spixels}, {fpixels}) must be positive"

        # Validate shape matches detector dimensions
        slow_shape, fast_shape = golden.bragg.shape
        assert slow_shape == spixels, \
            f"Bragg slow dimension {slow_shape} != detector spixels {spixels}"
        assert fast_shape == fpixels, \
            f"Bragg fast dimension {fast_shape} != detector fpixels {fpixels}"

        print(f"\n[DB-AT-001] Pixel pitch: {pixel_size_mm:.6f} mm (square)")
        print(f"[DB-AT-001] Detector dimensions: {spixels} × {fpixels} px")
