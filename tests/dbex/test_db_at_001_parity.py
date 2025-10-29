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
from tests.fixtures.parity_loader import (
    load_golden_data,
    GoldenData,
    compute_parity_metrics,
    ParityMetrics,
    write_parity_artifacts,
    find_first_divergence,
    FirstDivergence,
)


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


class TestParityMetrics:
    """
    Unit tests for compute_parity_metrics() helper.

    Per input.md:8 (B1 checklist), these tests cover:
    - Correlation, RMSE, MSE, max|Δ| computation
    - Sum ratio handling (normal, zero denominator, zero numerator)
    - Localization metric (central half-box check)
    - Mask application (exclusion of masked pixels)
    - Edge cases (empty arrays, single pixel, perfect match)

    Tests use synthetic data to validate metric computation independently
    of golden dataset availability.
    """

    def test_perfect_match(self):
        """
        Test metrics when predicted == target (perfect parity).

        Expected:
        - correlation = 1.0
        - rmse = 0.0
        - mse = 0.0
        - max_abs_diff = 0.0
        - sum_ratio = 1.0
        - localization = 1.0 (both peaks at same location)
        """
        shape = (64, 64)
        # Create a simple peak pattern
        target = np.zeros(shape, dtype=np.float32)
        target[32, 32] = 100.0  # Peak at center
        target[30:35, 30:35] = 10.0

        predicted = target.copy()

        metrics = compute_parity_metrics(predicted, target)

        assert metrics.correlation == pytest.approx(1.0, abs=1e-6), \
            f"Perfect match should have correlation=1.0, got {metrics.correlation}"
        assert metrics.rmse == pytest.approx(0.0, abs=1e-6), \
            f"Perfect match should have rmse=0.0, got {metrics.rmse}"
        assert metrics.mse == pytest.approx(0.0, abs=1e-6), \
            f"Perfect match should have mse=0.0, got {metrics.mse}"
        assert metrics.max_abs_diff == pytest.approx(0.0, abs=1e-6), \
            f"Perfect match should have max_abs_diff=0.0, got {metrics.max_abs_diff}"
        assert metrics.sum_ratio == pytest.approx(1.0, abs=1e-6), \
            f"Perfect match should have sum_ratio=1.0, got {metrics.sum_ratio}"
        assert metrics.localization == pytest.approx(1.0, abs=1e-6), \
            f"Perfect match should have localization=1.0, got {metrics.localization}"
        assert metrics.n_pixels == 64 * 64

        print(f"\n[parity_metrics] Perfect match test passed")
        print(f"[parity_metrics] All metrics at expected values")

    def test_correlation_computation(self):
        """
        Test correlation computation with known patterns.

        Uses linear relationships to verify Pearson correlation:
        - predicted = 2 * target → correlation = 1.0
        - predicted = -target → correlation = -1.0
        - predicted = target + constant → correlation = 1.0
        """
        shape = (64, 64)
        np.random.seed(42)
        target = np.random.randn(*shape).astype(np.float32)

        # Test 1: Linear scaling (correlation = 1.0)
        predicted_scaled = 2.0 * target
        metrics_scaled = compute_parity_metrics(predicted_scaled, target)
        assert metrics_scaled.correlation == pytest.approx(1.0, abs=1e-6), \
            f"Linear scaling should preserve correlation=1.0, got {metrics_scaled.correlation}"

        # Test 2: Negation (correlation = -1.0)
        predicted_negated = -target
        metrics_negated = compute_parity_metrics(predicted_negated, target)
        assert metrics_negated.correlation == pytest.approx(-1.0, abs=1e-6), \
            f"Negation should give correlation=-1.0, got {metrics_negated.correlation}"

        # Test 3: Constant offset (correlation = 1.0)
        predicted_offset = target + 10.0
        metrics_offset = compute_parity_metrics(predicted_offset, target)
        assert metrics_offset.correlation == pytest.approx(1.0, abs=1e-6), \
            f"Constant offset should preserve correlation=1.0, got {metrics_offset.correlation}"

        print(f"\n[parity_metrics] Correlation computation test passed")
        print(f"[parity_metrics] Scaled: {metrics_scaled.correlation:.6f}")
        print(f"[parity_metrics] Negated: {metrics_negated.correlation:.6f}")
        print(f"[parity_metrics] Offset: {metrics_offset.correlation:.6f}")

    def test_error_metrics(self):
        """
        Test RMSE, MSE, and max|Δ| computation.

        Uses synthetic data with known differences:
        - Uniform difference → RMSE = |diff|, max|Δ| = |diff|
        - Single spike difference → max|Δ| captures spike
        """
        shape = (32, 32)
        target = np.ones(shape, dtype=np.float32) * 50.0

        # Test 1: Uniform difference
        predicted_uniform = target + 10.0  # All pixels +10
        metrics_uniform = compute_parity_metrics(predicted_uniform, target)

        expected_mse = 10.0 ** 2
        expected_rmse = 10.0
        expected_max = 10.0

        assert metrics_uniform.mse == pytest.approx(expected_mse, abs=1e-3), \
            f"Uniform +10 should give MSE=100, got {metrics_uniform.mse}"
        assert metrics_uniform.rmse == pytest.approx(expected_rmse, abs=1e-3), \
            f"Uniform +10 should give RMSE=10, got {metrics_uniform.rmse}"
        assert metrics_uniform.max_abs_diff == pytest.approx(expected_max, abs=1e-3), \
            f"Uniform +10 should give max|Δ|=10, got {metrics_uniform.max_abs_diff}"

        # Test 2: Single spike difference
        predicted_spike = target.copy()
        predicted_spike[16, 16] = 150.0  # +100 at center
        metrics_spike = compute_parity_metrics(predicted_spike, target)

        assert metrics_spike.max_abs_diff == pytest.approx(100.0, abs=1e-3), \
            f"Spike difference should give max|Δ|=100, got {metrics_spike.max_abs_diff}"

        print(f"\n[parity_metrics] Error metrics test passed")
        print(f"[parity_metrics] Uniform: MSE={metrics_uniform.mse:.2f}, RMSE={metrics_uniform.rmse:.2f}")
        print(f"[parity_metrics] Spike: max|Δ|={metrics_spike.max_abs_diff:.2f}")

    def test_sum_ratio(self):
        """
        Test sum ratio computation in various scenarios.

        Covers:
        - Normal case: sum_ratio = sum(predicted) / sum(target)
        - Zero target sum: sum_ratio = nan or inf
        - Zero predicted sum with non-zero target: sum_ratio = 0.0
        """
        shape = (32, 32)
        target = np.ones(shape, dtype=np.float32) * 10.0

        # Test 1: Normal case (predicted = 2x target)
        predicted_scaled = target * 2.0
        metrics_scaled = compute_parity_metrics(predicted_scaled, target)
        assert metrics_scaled.sum_ratio == pytest.approx(2.0, abs=1e-6), \
            f"2x scaling should give sum_ratio=2.0, got {metrics_scaled.sum_ratio}"

        # Test 2: Zero predicted sum with non-zero target
        predicted_zero = np.zeros(shape, dtype=np.float32)
        metrics_zero_pred = compute_parity_metrics(predicted_zero, target)
        assert metrics_zero_pred.sum_ratio == pytest.approx(0.0, abs=1e-6), \
            f"Zero predicted should give sum_ratio=0.0, got {metrics_zero_pred.sum_ratio}"

        # Test 3: Zero target sum (should return nan or inf)
        target_zero = np.zeros(shape, dtype=np.float32)
        predicted_nonzero = np.ones(shape, dtype=np.float32)
        metrics_zero_targ = compute_parity_metrics(predicted_nonzero, target_zero)
        assert np.isinf(metrics_zero_targ.sum_ratio), \
            f"Zero target with nonzero pred should give inf, got {metrics_zero_targ.sum_ratio}"

        # Test 4: Both zero (should return nan)
        metrics_both_zero = compute_parity_metrics(target_zero, target_zero)
        assert np.isnan(metrics_both_zero.sum_ratio), \
            f"Both zero should give nan, got {metrics_both_zero.sum_ratio}"

        print(f"\n[parity_metrics] Sum ratio test passed")
        print(f"[parity_metrics] Scaled: {metrics_scaled.sum_ratio:.2f}")
        print(f"[parity_metrics] Zero pred: {metrics_zero_pred.sum_ratio:.2f}")

    def test_localization_metric(self):
        """
        Test peak localization metric (central half-box check).

        Per docs/forward_equivalence.md:48-49, localization checks if
        brightest pixel is within central half-box.

        Scenarios:
        - Both peaks centered → localization = 1.0
        - One peak centered, one off-center → localization = 0.5
        - Both peaks off-center → localization = 0.0
        """
        shape = (64, 64)

        # Test 1: Both peaks centered
        target_centered = np.zeros(shape, dtype=np.float32)
        target_centered[32, 32] = 100.0

        predicted_centered = np.zeros(shape, dtype=np.float32)
        predicted_centered[32, 32] = 100.0

        metrics_both = compute_parity_metrics(predicted_centered, target_centered)
        assert metrics_both.localization == pytest.approx(1.0, abs=1e-6), \
            f"Both centered should give localization=1.0, got {metrics_both.localization}"

        # Test 2: One peak centered, one off-center
        predicted_offcenter = np.zeros(shape, dtype=np.float32)
        predicted_offcenter[10, 10] = 100.0  # Far from center

        metrics_one = compute_parity_metrics(predicted_offcenter, target_centered)
        assert metrics_one.localization == pytest.approx(0.5, abs=1e-6), \
            f"One centered should give localization=0.5, got {metrics_one.localization}"

        # Test 3: Both peaks off-center
        target_offcenter = np.zeros(shape, dtype=np.float32)
        target_offcenter[10, 10] = 100.0

        metrics_neither = compute_parity_metrics(predicted_offcenter, target_offcenter)
        assert metrics_neither.localization == pytest.approx(0.0, abs=1e-6), \
            f"Neither centered should give localization=0.0, got {metrics_neither.localization}"

        print(f"\n[parity_metrics] Localization test passed")
        print(f"[parity_metrics] Both: {metrics_both.localization:.2f}")
        print(f"[parity_metrics] One: {metrics_one.localization:.2f}")
        print(f"[parity_metrics] Neither: {metrics_neither.localization:.2f}")

    def test_mask_application(self):
        """
        Test loss mask application (exclude masked pixels).

        Per docs/spec-db-workflow.md:24-29, loss mask coverage is typically
        <1% for Bragg peaks. Masked pixels should be excluded from metrics.

        Validates:
        - Masked pixels excluded from correlation/RMSE/MSE
        - n_pixels and n_masked counts correct
        - Metrics computed only on unmasked region
        """
        shape = (32, 32)
        # Use varying data in unmasked region (not constant)
        np.random.seed(123)
        target = np.random.rand(*shape).astype(np.float32) * 100.0
        predicted = target.copy()

        # Create mask that excludes edges
        loss_mask = np.ones(shape, dtype=bool)
        loss_mask[:8, :] = False  # Mask top 8 rows
        loss_mask[-8:, :] = False  # Mask bottom 8 rows

        # Introduce difference in masked region (should be ignored)
        predicted[:8, :] = 999.0
        predicted[-8:, :] = 999.0

        metrics = compute_parity_metrics(predicted, target, loss_mask=loss_mask)

        # Should have perfect correlation in unmasked region
        assert metrics.correlation == pytest.approx(1.0, abs=1e-6), \
            f"Masked difference should not affect correlation, got {metrics.correlation}"
        assert metrics.rmse == pytest.approx(0.0, abs=1e-6), \
            f"Masked difference should not affect RMSE, got {metrics.rmse}"

        # Validate pixel counts
        expected_unmasked = 32 * 16  # Middle 16 rows
        expected_masked = 32 * 16  # Top 8 + bottom 8 rows

        assert metrics.n_pixels == expected_unmasked, \
            f"n_pixels should be {expected_unmasked}, got {metrics.n_pixels}"
        assert metrics.n_masked == expected_masked, \
            f"n_masked should be {expected_masked}, got {metrics.n_masked}"

        print(f"\n[parity_metrics] Mask application test passed")
        print(f"[parity_metrics] n_pixels: {metrics.n_pixels}")
        print(f"[parity_metrics] n_masked: {metrics.n_masked}")

    def test_edge_cases(self):
        """
        Test edge cases for parity metrics.

        Covers:
        - Empty array (all pixels masked) → NaN metrics
        - Single pixel → NaN correlation, valid error metrics
        - Shape mismatch → ValueError
        """
        # Test 1: Empty array (all masked)
        shape = (16, 16)
        target = np.ones(shape, dtype=np.float32)
        predicted = np.ones(shape, dtype=np.float32)
        loss_mask = np.zeros(shape, dtype=bool)  # All masked

        metrics_empty = compute_parity_metrics(predicted, target, loss_mask=loss_mask)

        assert np.isnan(metrics_empty.correlation), \
            f"Empty array should give NaN correlation, got {metrics_empty.correlation}"
        assert np.isnan(metrics_empty.rmse), \
            f"Empty array should give NaN RMSE, got {metrics_empty.rmse}"
        assert metrics_empty.n_pixels == 0

        # Test 2: Single pixel (correlation should be NaN)
        target_single = np.array([[42.0]], dtype=np.float32)
        predicted_single = np.array([[43.0]], dtype=np.float32)

        metrics_single = compute_parity_metrics(predicted_single, target_single)

        assert np.isnan(metrics_single.correlation), \
            f"Single pixel should give NaN correlation, got {metrics_single.correlation}"
        assert metrics_single.rmse == pytest.approx(1.0, abs=1e-6), \
            f"Single pixel RMSE should be |diff|, got {metrics_single.rmse}"
        assert metrics_single.n_pixels == 1

        # Test 3: Shape mismatch (should raise)
        target_wrong = np.ones((16, 16), dtype=np.float32)
        predicted_wrong = np.ones((16, 32), dtype=np.float32)

        with pytest.raises(ValueError, match="Shape mismatch"):
            compute_parity_metrics(predicted_wrong, target_wrong)

        print(f"\n[parity_metrics] Edge cases test passed")
        print(f"[parity_metrics] Empty array n_pixels: {metrics_empty.n_pixels}")
        print(f"[parity_metrics] Single pixel n_pixels: {metrics_single.n_pixels}")

    def test_to_dict_serialization(self):
        """
        Test ParityMetrics.to_dict() for JSON serialization.

        Validates:
        - All fields present in dict
        - Numeric types are JSON-serializable (float/int)
        - NaN values preserved
        """
        shape = (32, 32)
        target = np.ones(shape, dtype=np.float32) * 10.0
        predicted = target * 2.0

        metrics = compute_parity_metrics(predicted, target)
        metrics_dict = metrics.to_dict()

        # Validate all keys present
        expected_keys = {
            "correlation", "rmse", "mse", "max_abs_diff",
            "sum_ratio", "localization", "n_pixels", "n_masked"
        }
        assert set(metrics_dict.keys()) == expected_keys, \
            f"Missing keys: {expected_keys - set(metrics_dict.keys())}"

        # Validate types are JSON-serializable
        import json
        json_str = json.dumps(metrics_dict)  # Should not raise
        assert len(json_str) > 0

        print(f"\n[parity_metrics] Serialization test passed")
        print(f"[parity_metrics] JSON length: {len(json_str)} bytes")


class TestArtifactEmission:
    """
    Unit tests for write_parity_artifacts() artifact writer.

    Per input.md:9 (B2 checklist), these tests cover:
    - Metrics JSON emission with manifest checksum
    - CSV stub generation
    - Overlay stub creation
    - NPY tensor persistence
    - Artifact directory structure
    """

    def test_artifact_emission(self, tmp_path):
        """
        Test artifact writer creates expected files.

        Validates:
        - parity_harness/ subdirectory created
        - metrics.json written with correct structure
        - metrics.csv written with headers
        - overlay stub and NPY files created when tensors provided
        - Manifest checksum included in metrics JSON
        """
        # Create synthetic metrics
        shape = (32, 32)
        target = np.ones(shape, dtype=np.float32) * 10.0
        predicted = target * 2.0

        metrics = compute_parity_metrics(predicted, target)

        # Write artifacts
        artifact_dir = tmp_path / "test_artifacts"
        artifacts = write_parity_artifacts(
            artifact_dir=artifact_dir,
            metrics=metrics,
            predicted=predicted,
            target=target,
            manifest_checksum="abc123",
            metadata={"test": "value"}
        )

        # Validate artifact paths
        assert "metrics_json" in artifacts
        assert "metrics_csv" in artifacts
        assert "overlay_stub" in artifacts
        assert "predicted_npy" in artifacts
        assert "target_npy" in artifacts

        # Validate files exist
        parity_dir = artifact_dir / "parity_harness"
        assert parity_dir.exists()
        assert (parity_dir / "metrics.json").exists()
        assert (parity_dir / "metrics.csv").exists()
        assert (parity_dir / "diff_overlay_stub.txt").exists()
        assert (parity_dir / "predicted.npy").exists()
        assert (parity_dir / "target.npy").exists()

        # Validate metrics JSON structure
        import json
        with open(parity_dir / "metrics.json", 'r') as f:
            metrics_data = json.load(f)

        assert "correlation" in metrics_data
        assert "manifest_checksum" in metrics_data
        assert metrics_data["manifest_checksum"] == "abc123"
        assert "metadata" in metrics_data
        assert metrics_data["metadata"]["test"] == "value"

        # Validate CSV has header
        with open(parity_dir / "metrics.csv", 'r') as f:
            csv_lines = f.readlines()
        assert len(csv_lines) > 1
        assert "metric,value" in csv_lines[0]

        # Validate NPY files can be loaded
        pred_loaded = np.load(parity_dir / "predicted.npy")
        targ_loaded = np.load(parity_dir / "target.npy")
        assert pred_loaded.shape == shape
        assert targ_loaded.shape == shape

        print(f"\n[artifact_emission] All files created successfully")
        print(f"[artifact_emission] Artifact dir: {artifact_dir}")
        print(f"[artifact_emission] Files: {len(artifacts)} artifacts")

    def test_artifact_emission_minimal(self, tmp_path):
        """
        Test artifact writer with minimal inputs (no tensors).

        Validates:
        - Metrics JSON and CSV created even without tensors
        - No overlay or NPY files created
        - Directory structure still valid
        """
        # Create synthetic metrics
        shape = (16, 16)
        target = np.ones(shape, dtype=np.float32) * 5.0
        predicted = target.copy()

        metrics = compute_parity_metrics(predicted, target)

        # Write artifacts without tensors
        artifact_dir = tmp_path / "test_minimal"
        artifacts = write_parity_artifacts(
            artifact_dir=artifact_dir,
            metrics=metrics,
        )

        # Validate minimal artifact paths
        assert "metrics_json" in artifacts
        assert "metrics_csv" in artifacts
        assert "overlay_stub" not in artifacts
        assert "predicted_npy" not in artifacts

        # Validate files exist
        parity_dir = artifact_dir / "parity_harness"
        assert parity_dir.exists()
        assert (parity_dir / "metrics.json").exists()
        assert (parity_dir / "metrics.csv").exists()
        assert not (parity_dir / "diff_overlay_stub.txt").exists()

        print(f"\n[artifact_emission] Minimal mode successful")
        print(f"[artifact_emission] Files: {len(artifacts)} artifacts")


class TestDB_AT_001_Parity:
    """
    DB-AT-001 parity harness integration test (Phase B3).

    Per input.md:10 (B3 checklist) and docs/spec-db-conformance.md:23-26,
    this test:
    - Loads golden data with deterministic RNG seeding
    - Computes parity metrics (correlation, RMSE, localization)
    - Emits artifacts under designated reports directory
    - Conditionally xfails when thresholds not met (stub simulator scenario)

    Future work (Phase C):
    - Replace stub tensors with real DiffBragg/torch forward passes
    - Enforce thresholds: correlation ≥0.2, localization ≥90%
    - Capture first divergence metrics for parity debugging
    """

    def test_db_at_001_parity_smoke(self, simple_cubic_golden):
        """
        DB-AT-001 parity smoke test with metrics computation.

        Per docs/forward_equivalence.md:46-52, this test:
        - Loads golden data (bragg, target, loss_mask)
        - Computes parity metrics
        - Emits artifacts with manifest checksum
        - xfails if thresholds not met (expected with synthetic data)

        Thresholds (future enforcement when real simulator lands):
        - Median ROI correlation ≥ 0.2
        - ≥90% ROIs with localized peaks

        Environment:
            export KMP_DUPLICATE_LIB_OK=TRUE
            pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001
        """
        golden = simple_cubic_golden

        # Set deterministic RNG seed for reproducibility
        np.random.seed(42)

        # For Phase B, we use golden data directly as "predicted" vs "target"
        # (In Phase C, predicted will come from torch forward pass)
        # For now, introduce synthetic mismatch to test metrics
        predicted = golden.bragg.copy()
        # Add noise to simulate imperfect parity
        noise = np.random.randn(*predicted.shape).astype(np.float32) * 5.0
        predicted = predicted + noise

        # Compute parity metrics
        metrics = compute_parity_metrics(
            predicted=predicted,
            target=golden.target,
            loss_mask=golden.loss_mask,
            check_localization=True
        )

        # Get manifest checksum from golden data
        manifest_files = golden.manifest.get("files", {})
        manifest_checksum = None
        if "manifest" in manifest_files:
            manifest_checksum = manifest_files["manifest"]["sha256"]

        # Find first divergence (per docs/spec-db-tracing.md:15-19)
        first_div = find_first_divergence(
            predicted=predicted,
            target=golden.target,
            loss_mask=golden.loss_mask,
            abs_threshold=1e-6,
            rel_threshold=1e-4,
        )

        # Write artifacts
        repo_root = Path(__file__).parent.parent.parent
        artifact_dir = repo_root / "plans/active/PARITY-HARNESS-002/reports/2025-10-29T020937Z"

        artifacts = write_parity_artifacts(
            artifact_dir=artifact_dir,
            metrics=metrics,
            predicted=predicted,
            target=golden.target,
            manifest_checksum=manifest_checksum,
            metadata=golden.metadata
        )

        # Write first divergence metadata to separate JSON file
        # Per input.md:22-27, emit first_divergence.json for parity debugging
        if first_div is not None:
            import json
            parity_dir = artifact_dir / "parity_harness"
            first_div_path = parity_dir / "first_divergence.json"
            with open(first_div_path, 'w') as f:
                json.dump(first_div.to_dict(), f, indent=2)
            artifacts["first_divergence_json"] = str(first_div_path)

        # Log metrics
        print(f"\n[DB-AT-001] Parity metrics computed")
        print(f"[DB-AT-001] Correlation: {metrics.correlation:.4f}")
        print(f"[DB-AT-001] RMSE: {metrics.rmse:.2e}")
        print(f"[DB-AT-001] Max|Δ|: {metrics.max_abs_diff:.2e}")
        print(f"[DB-AT-001] Sum ratio: {metrics.sum_ratio:.4f}")
        print(f"[DB-AT-001] Localization: {metrics.localization:.2f}")
        print(f"[DB-AT-001] n_pixels: {metrics.n_pixels}")

        # Log first divergence
        if first_div is not None:
            print(f"[DB-AT-001] First divergence: pixel {first_div.pixel_index}, "
                  f"abs_diff={first_div.abs_diff:.2e}, "
                  f"rel_diff={first_div.rel_diff:.2e}, "
                  f"scanned={first_div.n_pixels_scanned}")
        else:
            print(f"[DB-AT-001] No divergence found (perfect parity)")

        print(f"[DB-AT-001] Artifacts: {len(artifacts)} files")

        # Conditional xfail for Phase B (synthetic data)
        # Per docs/forward_equivalence.md:46-52 and input.md:30,
        # xfail when thresholds not met but diagnostics captured
        correlation_threshold = 0.2
        localization_threshold = 0.9

        if metrics.correlation < correlation_threshold or metrics.localization < localization_threshold:
            pytest.xfail(
                f"Parity thresholds not met (expected with synthetic data):\n"
                f"  correlation={metrics.correlation:.4f} (threshold ≥{correlation_threshold})\n"
                f"  localization={metrics.localization:.2f} (threshold ≥{localization_threshold})\n"
                f"Artifacts captured under: {artifact_dir}/parity_harness/\n"
                f"Phase C will replace synthetic data with real forward passes."
            )

        # If thresholds met (unlikely with synthetic noise), test passes
        assert metrics.correlation >= correlation_threshold, \
            f"Correlation {metrics.correlation:.4f} < {correlation_threshold}"
        assert metrics.localization >= localization_threshold, \
            f"Localization {metrics.localization:.2f} < {localization_threshold}"
