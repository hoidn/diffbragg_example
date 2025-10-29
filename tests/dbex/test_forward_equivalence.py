"""
DB-AT-001 Forward Equivalence Smoke Test

Forward-only parity comparison between DiffBragg and nanobrag_torch backends
without running refinement loops. Validates geometry/config propagation and
produces physically plausible intensities before attempting optimization.

Per docs/forward_equivalence.md:
- Acceptance: median ROI correlation ≥ 0.2, ≥ 90% localization success
- xfail when thresholds miss but diagnostics captured
- Artifacts: plans/active/FORWARD-EQUIV-001/reports/<ts>/forward_equiv/

Spec references:
- docs/spec-db-conformance.md:18-33 — DB-AT-001 acceptance profile
- docs/spec-db-core.md:20-58 — [panel, slow, fast] ordering, mask semantics
- docs/spec-db-workflow.md:24-29 — Stitched Bragg tensors, masked MSE

Findings applied:
- CONFORMANCE-001: KMP_DUPLICATE_LIB_OK=TRUE environment flag
- CONFIG-001: Bridge hydration for geometry consistency
- MASKING-001: Loss mask coverage expectations (sparse, <1% typical)
- TESTING-003: Collect-only logs and doc sync requirements

Environment:
    export KMP_DUPLICATE_LIB_OK=TRUE
    pytest -v tests/dbex/test_forward_equivalence.py -k DB_AT_001
"""

import pytest
import numpy as np
