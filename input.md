# Ralph Input — TORCH-API-ALIGN-001 Phase A1 Implementation (DIALS Mapping Parity)

## Summary
Implement Phase A1 test validating DIALS mapping (beam-center swap + Euler extraction).

## Mode
none

## Focus
TORCH-API-ALIGN-001 — Phase A1: DIALS Mapping Parity Test Implementation

## Branch
integration

## Mapped Tests
- `tests/dbex/test_bridge_mapping.py::test_dials_mapping_parity` (Phase A1)
- NO regression guards (test-only change)

## Artifacts
`plans/active/TORCH-API-ALIGN-001/reports/2025-11-24T000100Z/`
- `phase_a1_decision.md`, `pytest_dials_mapping.log`, `summary.md`

## Do Now

**Context:** Phase B ✓ COMPLETE (factory -79 lines, Exit #1 satisfied). Phase B3 RESCOPED (ExperimentModel upstream bug). Next: Validate Exit Criterion #2 (DIALS mapping parity) via Phase A1 test implementation.

**Implement:** `test_dials_mapping_parity` (tests/dbex/test_bridge_mapping.py:36-61)

### Steps (9 total)

1. **Read specs:** docs/nanobrag_api.md:44-47, docs/config_crosswalk.md:29, findings GEOMETRY-001/002, plans/../phase_a1_planning.md

2. **Implement test** (~80-120 lines replacing stub):
```python
# Remove pytest.skip(), add:
import numpy as np
from dxtbx.model import Beam, Panel, Detector
from dbex.nanobrag_bridge import create_detector_config
from dbex.config import DetectorConvention

# Minimal dxtbx beam + panel (100x100 px, 0.1 mm/px)
beam = Beam(direction=(0,0,1), wavelength=1.0)
panel = Panel(
    type="SENSOR_PAD", name="panel_0",
    fast_axis=(1,0,0), slow_axis=(0,-1,0),
    origin=(-5.0, 5.0, -100.0),  # beam center (50,50)px
    pixel_size=(0.1,0.1), image_size=(100,100),
    trusted_range=(-1,1e6)
)
detector = Detector(panel)

# Build DetectorConfig via DIALS
detector_config = create_detector_config(detector, panel_id=0, convention=DetectorConvention.DIALS)

# Assert beam-center swap (fast,slow)→(s,f)
# Expected: slow=5.0mm (from fast proj), fast=5.0mm (from slow proj)
assert abs(detector_config.beam_center_mm_slow - 5.0) < 1e-6
assert abs(detector_config.beam_center_mm_fast - 5.0) < 1e-6

# Assert Euler field exists (defer exact values)
assert hasattr(detector_config, 'euler_rad') or hasattr(detector_config, 'euler_angles')

# Debug output
print(f"Beam-center (s,f): ({detector_config.beam_center_mm_slow:.6f}, {detector_config.beam_center_mm_fast:.6f})")
```

3. **Run test:**
```bash
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv -s tests/dbex/test_bridge_mapping.py::test_dials_mapping_parity 2>&1 | tee plans/active/TORCH-API-ALIGN-001/reports/2025-11-24T000100Z/pytest_dials_mapping.log
```

4. **If PASS:** Remove `@pytest.mark.xfail` decorator, re-run test clean

5. **Test registry (if PASS):**
- Run `pytest --collect-only tests/dbex/test_bridge_mapping.py`
- Add DB-API-A1 row to TESTING_GUIDE.md §2 + TEST_SUITE_INDEX.md

6. **Update plan:** Mark implementation.md:42 `[x] A1 COMPLETE 2025-11-24T000100Z`

7. **Decision.md:**
- Path A (PASS): metrics, confidence HIGH, next=Exit Criteria assessment
- Path B (FAIL): actual vs expected values, blocker analysis, return to Galph
- Path C (Error): traceback, suspected cause, return to Galph

8. **Summary.md:** Turn Summary (test outcome, next action, artifacts)

9. **Commit (if PASS):**
```
TORCH-API-ALIGN-001 Phase A1: DIALS mapping parity test COMPLETE

- Beam-center swap (fast,slow)→(s,f) ✓ PASS
- Euler field existence ✓ PASS
- xfail removed, registry synced (DB-API-A1)

Exit #2 progress: DIALS mapping validated.
Metrics: ~[X] lines test, 0 prod changes.

Findings: GEOMETRY-001/002, CONFIG-001/002.
```

## How-To Map

**Expected beam-center calc:**
- Panel origin (-5,5,-100), beam hits (0,0,-100)
- Δ=(5,-5,0), fast=(1,0,0), slow=(0,-1,0)
- fast_proj=Δ·fast=5.0, slow_proj=Δ·slow=5.0
- DIALS swap: beam_center_mm_slow=fast_proj=5.0, fast=slow_proj=5.0

**Validation:** tests/dbex/test_bridge_mapping.py::test_dials_mapping_parity

**Decision paths:**
- A (PASS): remove xfail, update registry, commit, return to Galph for Exit Criteria
- B (FAIL): blocker report (actual vs expected), return to Galph
- C (Error): error log, return to Galph

## Pitfalls

1. DIALS swap: (fast,slow)→(s,f) NOT reverse
2. Remove xfail ONLY after PASS
3. Update BOTH registry files (TESTING_GUIDE + TEST_SUITE_INDEX)
4. Euler: just check field exists, NOT specific values
5. custom_beam_vector: document ignored, NO assertion (Phase C)
6. Panel 100x100px for speed
7. Tolerance 1e-6 for mm coords

## If Blocked

**B (Assertion):** Log actual vs expected, check panel geometry, verify bridge logic, return Galph
**C (Error):** Log traceback, check imports (dxtbx, bridge, DetectorConvention), return Galph

## Findings Applied

GEOMETRY-001/002, CONFIG-001/002, PERF-WARM-001, POLICY-001

## Pointers

- docs/nanobrag_api.md:44-47, docs/config_crosswalk.md:29
- plans/active/TORCH-API-ALIGN-001/reports/2025-11-24T000100Z/phase_a1_planning.md
- implementation.md:42-45
