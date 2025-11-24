"""
TORCH-API-ALIGN-001 Phase A Test Stub: CUSTOM Override Exploratory (A4)

Validates optional CUSTOM DetectorConfig override path with custom_beam_vector
per docs/nanobrag_api.md (CUSTOM convention) and implementation.md:55-57.

Acceptance Criteria (from implementation.md:55-57):
- CUSTOM DetectorConfig with custom_beam_vector=normalize(-s0)
- Measure parity deltas vs DIALS on fixtures
- Record acceptance thresholds/use-cases (optional path, default OFF)

This test is xfail-guarded and optional until Phase C lands.

Findings applied:
- CONFIG-001: DetectorConvention enum
- GEOMETRY-001: Beam-center conventions
"""

import pytest


@pytest.mark.xfail(reason="TORCH-API-ALIGN-001 Phase C optional CUSTOM override not yet implemented")
def test_custom_override_exploratory():
    """
    Exploratory test for optional CUSTOM DetectorConfig override.

    Tests:
    - CUSTOM DetectorConfig construction with custom basis from panel axes
    - custom_beam_vector=normalize(-s0) explicit injection
    - Parity deltas vs DIALS on tiny fixtures
    - Acceptance threshold measurement

    Acceptance: Parity deltas recorded; acceptance thresholds/use-cases
    documented in plan reports. This is an optional path behind a flag
    (default OFF).

    Implementation note: Uses tiny fixture (<100x100 px) for fast execution.
    Phase C will implement dbex feature flag for CUSTOM override path.
    """
    pytest.skip("Phase B/C wiring pending")

    # Phase C implementation will:
    # 1. Build DIALS DetectorConfig (default path)
    # 2. Build CUSTOM DetectorConfig with custom basis from panel axes
    # 3. Set custom_beam_vector=normalize(-s0)
    # 4. Run both paths on same fixture
    # 5. Measure parity deltas (MSE, max abs diff, correlation)
    # 6. Record acceptance thresholds in plan reports
    # 7. Document use-cases where CUSTOM override is acceptable

    pass
