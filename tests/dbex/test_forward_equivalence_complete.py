"""
DB-AT-001 Forward Equivalence Smoke Test - Complete Implementation

Forward-only parity comparison between DiffBragg and nanobrag_torch backends.
Per docs/forward_equivalence.md, docs/spec-db-conformance.md:23-26, and input.md.

This test uses canonical golden data from tests/fixtures/golden_data/simple_cubic/
with bragg_diffbragg.npy and bragg_torch.npy baselines for parity comparison.

Environment:
    export KMP_DUPLICATE_LIB_OK=TRUE
    pytest -v tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001

Findings applied:
- CONFORMANCE-001: DB_AT selector contracts and environment flag usage
- TESTING-003: Collect-only commands and artifact logging
- SCALE-001/SCALE-002: Canonical structure-factor scaling and √spot_scale
- PARITY-001: First divergence metadata capture
- MANIFEST-001: Checksum validation for golden data
"""

import pytest
import numpy as np
import json
from pathlib import Path

# Parity harness utilities
from tests.fixtures.parity_loader import (
    load_golden_data,
    GoldenData,
    compute_parity_metrics,
    ParityMetrics,
    write_parity_artifacts,
    find_first_divergence,
)


@pytest.fixture(scope="module")
def golden_dir():
    """
    Path to simple cubic golden data directory.

    Per docs/parity_harness_spec.md:28-41 and MANIFEST-001,
    golden data resides under tests/fixtures/golden_data/simple_cubic/.
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
        - bragg_diffbragg: DiffBragg baseline [slow, fast] float32
        - bragg_torch: nanobrag_torch baseline [slow, fast] float32
        - target: Background-subtracted targets [slow, fast] float32
        - loss_mask: Loss mask [slow, fast] bool
        - metadata: Configuration metadata dict
        - manifest: Full manifest dict
        - panel_id: Panel ID (default 0)

    Per MANIFEST-001, checksums are validated on load.
    """
    golden_data = load_golden_data(
        golden_dir=golden_dir,
        panel_id=0,
        validate_checksums=True
    )
    return golden_data


@pytest.fixture(scope="module")
def artifact_dir():
    """
    Artifact directory for FORWARD-EQUIV-002 initiative.

    Per input.md:6-7, artifacts target:
    plans/active/FORWARD-EQUIV-002/reports/2025-11-04T041500Z/forward_equiv/
    """
    repo_root = Path(__file__).parent.parent.parent
    path = repo_root / "plans/active/FORWARD-EQUIV-002/reports/2025-11-04T041500Z/forward_equiv"
    path.mkdir(parents=True, exist_ok=True)
    return path


class TestForwardEquiv:
    """
    DB-AT-001 Forward equivalence smoke test.

    Per docs/spec-db-conformance.md:23-26 and docs/forward_equivalence.md:46-52:
    - Median ROI correlation ≥ 0.2
    - ≥90% ROIs with localized peaks (central half-box check)

    This test loads canonical DiffBragg and nanobrag_torch forward passes
    from golden data and asserts DB-AT-001 thresholds without xfail.
    """

    def test_DB_AT_001_forward_equiv(self, simple_cubic_golden, artifact_dir):
        """
        DB-AT-001 forward equivalence smoke test with canonical parity data.

        Per docs/forward_equivalence.md:46-52 and CONFORMANCE-001, this test:
        - Loads canonical golden data (bragg_diffbragg, bragg_torch, target, loss_mask)
        - Computes parity metrics between DiffBragg and torch baselines
        - Emits artifacts with manifest checksum per PARITY-001
        - Enforces thresholds: correlation ≥0.2, localization ≥0.90

        Environment:
            export KMP_DUPLICATE_LIB_OK=TRUE
            pytest -v tests/dbex/test_forward_equivalence_complete.py::TestForwardEquiv::test_DB_AT_001_forward_equiv
        """
        golden = simple_cubic_golden

        # Validate canonical baselines are present
        if golden.bragg_torch is None:
            pytest.skip("Canonical torch baseline not available in golden data")
        if golden.bragg_diffbragg is None:
            pytest.skip("Canonical DiffBragg baseline not available in golden data")

        # Use canonical baselines for parity comparison
        torch_baseline = golden.bragg_torch  # nanobrag_torch forward pass
        diffbragg_baseline = golden.bragg_diffbragg  # DiffBragg forward pass

        # Compute parity metrics per docs/forward_equivalence.md:30-53
        # (DiffBragg as "target", torch as "predicted" for consistency with parity harness)
        metrics = compute_parity_metrics(
            predicted=torch_baseline,
            target=diffbragg_baseline,
            loss_mask=golden.loss_mask,
            check_localization=True
        )

        # Find first divergence per PARITY-001
        first_div = find_first_divergence(
            predicted=torch_baseline,
            target=diffbragg_baseline,
            loss_mask=golden.loss_mask,
            abs_threshold=1e-6,
            rel_threshold=1e-4
        )

        # Get manifest checksum per MANIFEST-001
        manifest_checksum = golden.manifest.get("manifest_sha256")

        # Write artifacts per docs/spec-db-tracing.md:10-24
        artifacts = write_parity_artifacts(
            artifact_dir=artifact_dir,
            metrics=metrics,
            predicted=torch_baseline,
            target=diffbragg_baseline,
            manifest_checksum=manifest_checksum,
            metadata={
                "test": "DB_AT_001_forward_equiv",
                "initiative": "FORWARD-EQUIV-002",
                "timestamp": "2025-11-04T041500Z",
                "panel_id": golden.panel_id,
            }
        )

        # Write first divergence metadata if found
        if first_div is not None:
            first_div_path = artifact_dir / "parity_harness/first_divergence.json"
            with open(first_div_path, 'w') as f:
                json.dump(first_div.to_dict(), f, indent=2)
            artifacts["first_divergence_json"] = str(first_div_path)

        # Save full tensors for debugging (per docs/forward_equivalence.md:60-74)
        (artifact_dir / "legacy").mkdir(exist_ok=True)
        (artifact_dir / "torch").mkdir(exist_ok=True)
        np.save(artifact_dir / "legacy/bragg_diffbragg.npy", diffbragg_baseline)
        np.save(artifact_dir / "torch/bragg_torch.npy", torch_baseline)
        np.save(artifact_dir / "target.npy", golden.target)
        np.save(artifact_dir / "loss_mask.npy", golden.loss_mask)

        # Print diagnostics
        print(f"\n[DB-AT-001] Artifacts: {artifact_dir}")
        print(f"[DB-AT-001] Manifest checksum: {manifest_checksum}")
        print(f"[DB-AT-001] Correlation: {metrics.correlation:.6f}")
        print(f"[DB-AT-001] RMSE: {metrics.rmse:.2f}")
        print(f"[DB-AT-001] Localization: {metrics.localization:.2f}")
        print(f"[DB-AT-001] Valid pixels: {metrics.n_pixels}")
        if first_div:
            print(f"[DB-AT-001] First divergence at {first_div.pixel_index}: "
                  f"abs_diff={first_div.abs_diff:.2e}")

        # Assert DB-AT-001 thresholds per docs/spec-db-conformance.md:23-26
        # Correlation ≥ 0.2, localization ≥ 0.90
        # Note: localization from compute_parity_metrics returns 0.0-1.0 scale
        # (1.0 = both peaks centered, 0.5 = one peak centered, 0.0 = neither)
        # Spec requires ≥90% ROIs localized; for single-panel test, use 0.9 threshold
        assert metrics.correlation >= 0.2, (
            f"DB-AT-001 correlation threshold not met: {metrics.correlation:.4f} < 0.2"
        )
        assert metrics.localization >= 0.9, (
            f"DB-AT-001 localization threshold not met: {metrics.localization:.2f} < 0.9"
        )
