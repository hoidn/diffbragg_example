#!/usr/bin/env python
"""
Compatibility shim for smoke calibration capture.

This script has been refactored per ARCH-PROBE-FREEZE-001. All business logic now
resides in canonical owner modules:
- dbex.calibration.smoke_capture (helpers)
- dbex.tools.capture_smoke_calibration (CLI)

Use the canonical CLI instead:
    libtbx.python -m dbex.tools.capture_smoke_calibration \
        --expt sp.proc/idx-0000_sigma_metadata.expt \
        --refl refGeom.refl \
        --mask 747_mask.pkl \
        --mtz scaled.mtz \
        --out-config sp.proc/calibration/config_torch_smoke.json \
        --manifest <artifacts-path>/smoke_calibration_manifest.json \
        --num-macro 3

Owner: dbex.tools.capture_smoke_calibration
Contract: docs/data_dependency_manifest.md:86-103
Diagnostic Script Policy: prompts/supervisor.md:272-309
"""

import sys
from pathlib import Path

# Add repo root to path for imports
repo_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(repo_root))

from dbex.tools import capture_smoke_calibration


if __name__ == "__main__":
    capture_smoke_calibration.main()
