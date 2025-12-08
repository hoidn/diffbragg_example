# Input for Loop i=161 (Ralph)

## Summary
Investigate SPEC-SQUARE-PARTIALITY-001 DMI by running partiality test with larger detector (100×100 px) to verify finite-detector hypothesis.

## Mode
Parity

## ActionType
debug

## DecisionStatus
exploring (testing finite-detector hypothesis)

## InitiativeType
spec+tests

## Focus
SPEC-SQUARE-PARTIALITY-001 — SQUARE Lattice Spec & Test Alignment (Phase B.6 — DMI Investigation)

## Branch
integration

## Mapped tests
- `pytest -vv tests/architecture/test_nanobrag_partiality.py --maxfail=1` (with modified detector size)

## Artifacts
`plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T100000Z/`

## Findings Applied (Mandatory)
- **SIM-CONSTR-PARTIALITY-001**: Linear scaling expectation from maintainer; DMI suggests finite-detector effects
- **PROBE-FREEZE-001**: This investigation modifies existing test file parameters, does NOT create new probes

## Pointers
| Reference | Path | Section/Line |
|-----------|------|--------------|
| Phase B DMI Summary | plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T080000Z/summary.md | Full document |
| Loop i=160 Analysis | plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T090000Z/summary.md | DMI Analysis section |
| Maintainer Response | inbox/nanobrag_torch_response_2025_12_08.md | Part 2: SQUARE Lattice Partiality |
| Test File | tests/architecture/test_nanobrag_partiality.py | Lines 58-64 (detector config) |
| Implementation Plan | plans/active/SPEC-SQUARE-PARTIALITY-001/implementation.md | Phase B |

## ARCH Contracts (Mandatory)
| Contract ID | Doc Pointer | Owner Module/API | Failure Classification |
|-------------|-------------|------------------|------------------------|
| SIM-CONSTR-PARTIALITY-001 | docs/findings.md | tests/architecture/test_nanobrag_partiality.py | Investigation — DMI between expectation and observation |

## DMI Section (Mandatory)

### Independent Reference
Maintainer response (`inbox/nanobrag_torch_response_2025_12_08.md`) claims linear `Na×Nb×Nc` integrated intensity scaling. This is based on infinite-area integration (full reciprocal-space solid angle).

### Transformation Ledger
| Field/Tensor | Expected | Producer | Hydration | Consumer | Observed | Hypothesis |
|--------------|----------|----------|-----------|----------|----------|------------|
| intensity_base | >0 | sim_base.run() | detector pixels | test assertion | ~35.0 | OK |
| intensity_scaled | ~38,048× base | sim_scaled.run() | detector pixels | test assertion | ~1,187,854× base | 31× over linear |
| N_cells_effect | Na×Nb×Nc | CrystalConfig | Crystal | sincg lattice factor | Na×Nb×Nc×Nc | One axis squared |
| detector_coverage | full integration | DetectorConfig | Detector | pixel sum | partial? | Need larger detector |
| peak_width_a | 1/Na | sincg formula | physics | pixel sampling | ? | Not measured |
| peak_width_c | 1/Nc | sincg formula | physics | pixel sampling | ? | Not measured |

### Source Trace Anchors
- **Producer**: `sim.run()` → `simulator.py:_compute_physics_for_position` (SQUARE branch)
- **Hydration**: `CrystalConfig.N_cells` → `Crystal._compute_lattice_factor()`
- **Consumer**: `test_square_lattice_applies_ncells` assertion at line 169

### Consumption-State Measurements
- Current detector: 10×10 px × 0.1 mm = 1.0 mm² area
- Proposed detector: 100×100 px × 0.1 mm = 10.0 mm² area (100× coverage)

### Boundary Bisection Step
- Current boundary: detector geometry (10×10 px)
- Next boundary: larger detector (100×100 px)
- Metric: ratio change from ~31× to ~1× would confirm hypothesis

### Probe Budget
Probe count: 1 (this loop)

## Do Now (Hard Validity Contract)

### Focus: SPEC-SQUARE-PARTIALITY-001 Phase B.6 — DMI Investigation

### Implement:

1. **B6.1 — Create test variant with larger detector**:
   Edit `tests/architecture/test_nanobrag_partiality.py`:
   - Add a second test function `test_square_lattice_larger_detector` OR
   - Modify existing test parameters temporarily for investigation
   - Change `spixels=10, fpixels=10` to `spixels=100, fpixels=100`
   - Keep all other parameters the same (Na=41, Nb=29, Nc=32, oversample=13)

2. **B6.2 — Run investigation and capture output**:
   ```bash
   mkdir -p plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T100000Z
   KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/architecture/test_nanobrag_partiality.py --maxfail=1 2>&1 | tee plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T100000Z/pytest_larger_detector.log
   ```

3. **B6.3 — Analyze results**:
   - If scaling becomes ~linear (within 5%): **Hypothesis CONFIRMED** — finite detector was the issue
   - If scaling still shows ~31× linear: **Hypothesis REJECTED** — deeper physics issue

4. **B6.4 — Document findings**:
   Create `plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T100000Z/investigation_results.md`:
   - Test configuration changes
   - Observed ratio with larger detector
   - Comparison to 10×10 results
   - Conclusion and next step recommendation

5. **B6.5 — Revert test if needed OR finalize**:
   - If hypothesis CONFIRMED: keep larger detector config (or parameterize test for both sizes)
   - If hypothesis REJECTED: revert to 10×10, escalate to maintainers

6. **B6.6 — Update implementation.md**:
   Add Phase B.6 section documenting investigation results

### Validating pytest selector(s):
- `pytest -vv tests/architecture/test_nanobrag_partiality.py --maxfail=1`

### Artifacts Path:
`plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T100000Z/`

### Initiative type consistent:
spec+tests ✓ (investigation modifies test parameters, not production code)

## Touched
SPEC-SQUARE-PARTIALITY-001 Phase B.6 (B6.1, B6.2, B6.3, B6.4, B6.5, B6.6)

## Forbidden This Loop
- Do NOT create new plan-local probes per PROBE-FREEZE-001
- Do NOT modify production code
- Do NOT modify the probe script logic
- If hypothesis is REJECTED, do NOT keep the modified test — revert it

## How-To Map

### Step 1: Backup original test
```bash
cp tests/architecture/test_nanobrag_partiality.py tests/architecture/test_nanobrag_partiality.py.bak
```

### Step 2: Modify detector size (B6.1)
Edit `tests/architecture/test_nanobrag_partiality.py` lines 58-64:

**Current:**
```python
detector_config = DetectorConfig(
    distance_mm=100.0,
    pixel_size_mm=0.1,
    spixels=10,
    fpixels=10,
    oversample=test_oversample,
)
```

**Change to:**
```python
detector_config = DetectorConfig(
    distance_mm=100.0,
    pixel_size_mm=0.1,
    spixels=100,  # 10× larger
    fpixels=100,  # 10× larger
    oversample=test_oversample,
)
```

### Step 3: Run test (B6.2)
```bash
mkdir -p plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T100000Z
KMP_DUPLICATE_LIB_OK=TRUE pytest -vv tests/architecture/test_nanobrag_partiality.py --maxfail=1 2>&1 | tee plans/active/SPEC-SQUARE-PARTIALITY-001/reports/2025-12-08T100000Z/pytest_larger_detector.log
```

### Step 4: Analyze (B6.3)
Check the log for observed ratio:
- If `relative_error < 5%` → **SUCCESS** (linear scaling confirmed with larger detector)
- If `relative_error > 100%` → **FAILURE** (hypothesis rejected)

### Step 5: Document (B6.4)
Write investigation_results.md with findings

### Step 6: Decide next action (B6.5)
Based on results:
- **If CONFIRMED**: Consider parameterizing test to run both detector sizes (edge case coverage)
- **If REJECTED**: Restore backup, escalate with detailed evidence

## Pitfalls To Avoid
1. **Do NOT reduce oversample** — keep oversample=13 to isolate detector size variable
2. **Do NOT change N_cells** — keep (41,29,32) to compare apples-to-apples
3. **Memory considerations** — 100×100 × oversample=13² = 1.69M subpixels per simulation; may need more time
4. **Backup original** — always restore if hypothesis rejected
5. **Record exact ratio** — we need numeric comparison to 10×10 case

## If Blocked
- If test runs out of memory: try 50×50 detector as intermediate step
- If test takes too long: reduce oversample to 7 temporarily for investigation (note in results)
- If pytest crashes: capture traceback, document, and escalate

---

**Galph Note**: This is a targeted investigation to test the finite-detector hypothesis. The DMI showed `Na×Nb×Nc×Nc` scaling (31× linear) on a 10×10 detector. With a 100×100 detector (100× more area), we expect to see scaling approach the linear `Na×Nb×Nc` claimed by the maintainer. If this succeeds, we can either use a larger detector in the test or document the finite-detector limitation. If it fails, we need to escalate with specific evidence.
