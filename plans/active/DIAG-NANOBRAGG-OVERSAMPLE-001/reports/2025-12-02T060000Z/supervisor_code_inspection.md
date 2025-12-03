# Supervisor Code Inspection — DIAG-NANOBRAGG-OVERSAMPLE-001
**Loop**: 2025-12-02T060000Z (Galph inspection per repeat-failure + instrumentation-saturation rules)
**Problem**: DB-AT-028/029 still fail with zero simulator output after flux default fix (Phase C.9)
**Trigger**: Repeat-failure guard (same acceptance criterion, same signature, 2nd consecutive loop)

---

## Code Inspection Summary

### 1. Fluence IS Used by Simulator

**File**: `src/nanobrag-torch/src/nanobrag_torch/simulator.py`

**Initialization** (line 528):
```python
# Use fluence from beam config (AT-FLU-001)
self.fluence = torch.tensor(self.beam_config.fluence, device=self.device, dtype=self.dtype)
```

**Usage** (line 1175):
```python
physical_intensity = (
    normalized_intensity
    / steps
    * self.r_e_sqr
    * self.fluence
)
```

**Conclusion**: Fluence DOES affect simulator output (contrary to Ralph's analysis that only checked `flux`).

---

### 2. BeamConfig Fluence Default is HUGE

**File**: `src/nanobrag-torch/src/nanobrag_torch/config.py`

**Default** (line 529):
```python
fluence: float = 125932015286227086360700780544.0  # Photons per square meter (default from C code)
```

**Value**: 1.26 × 10²⁹ photons/m²

---

### 3. Flux Default Change Has NO EFFECT

**File**: `src/nanobrag-torch/src/nanobrag_torch/config.py`
**Method**: `BeamConfig.__post_init__` (lines 540-555)

```python
def __post_init__(self):
    if self.flux != 0 and self.exposure > 0 and self.beamsize_mm >= 0:
        beamsize_m = self.beamsize_mm / 1000.0
        if beamsize_m > 0:
            self.fluence = self.flux * self.exposure / (beamsize_m * beamsize_m)
    elif self.exposure > 0 and self.beamsize_mm > 0 and self.fluence > 0:
        ...
```

**Analysis**:
- Condition line 545: `flux != 0 AND exposure > 0 AND beamsize_mm >= 0`
- With defaults: `flux=1.0`, `exposure=0.0`, `beamsize_mm=0.0`
- Result: `True AND **FALSE** AND True` = **FALSE**
- Therefore: fluence recomputation NEVER happens, fluence stays at default 1.26e+29

**Conclusion**: Changing flux from 0→1 has NO EFFECT because `exposure=0.0` prevents the `__post_init__` condition from triggering.

---

### 4. Factory Never Passes Calibration Args

**File**: `dbex/refinement/config_factories.py`
**Function**: `create_beam_config` (lines 234-284)

```python
def create_beam_config(beam, flux=None, beamsize_mm=None, exposure=None) -> BeamConfig:
    beam_kwargs = {
        'wavelength_A': wavelength_A,
        ...
    }

    # Only add flux/beamsize/exposure if all three are provided
    if flux is not None:
        beam_kwargs['flux'] = flux
    if beamsize_mm is not None:
        beam_kwargs['beamsize_mm'] = beamsize_mm
    if exposure is not None:
        beam_kwargs['exposure'] = exposure

    return BeamConfig(**beam_kwargs)
```

**Call site** (reconstruction.py:488):
```python
beam_config = create_beam_config(beam)  # No calibration args
```

**Result**: BeamConfig created with ALL defaults:
- flux: 1.0 (after Ralph's change)
- exposure: 0.0 (default)
- beamsize_mm: 0.0 (default)
- **fluence: 1.26e+29 (default, NOT recomputed)**

---

### 5. The Paradox

**Expected behavior**: With fluence=1.26e+29, simulator should produce HUGE output (e²⁹ scale)
**Observed behavior**: Simulator produces ZERO output
**Ralph's test output** (2025-12-02T230000Z):
```
bragg_panel[0] mean (raw sim output): 0.000000e+00
bragg_full mean (final output): 0.000000e+00
```

**Conclusion**: The zero output is NOT caused by zero fluence. Something else in the simulator pipeline is zeroing the output.

---

## Hypotheses for Zero Output (Unexplored)

From `physical_intensity = normalized_intensity / steps * r_e_sqr * fluence`:

1. **`normalized_intensity = 0`** — Structure factors or lattice factors are zero
   - Could be: HKL grid empty, F_cell all zero, lattice factor computation error

2. **`steps = ∞`** — Div by infinity yields zero
   - Unlikely but possible

3. **`self.fluence = 0` at runtime** — Something zeros it after __init__
   - Despite default 1.26e+29, maybe a setter or override path exists

4. **Simulator path not reached** — Maybe run() returns early with zeros
   - ROI mask all zero? Device/dtype mismatch causing silent failure?

---

## Missing Evidence

Ralph's diagnostic did NOT capture:
- Actual `beam_config.fluence` value passed to Simulator
- Actual `simulator.fluence` value during run()
- Values of `normalized_intensity`, `steps`, `r_e_sqr` inside the computation

**Required**: Instrument the simulator itself to dump these values, OR use maintainer debugger.

---

## Environment Freeze Violation Risk

Further debugging requires EITHER:
- **Option A**: Patch nanobrag_torch simulator.py to add print statements (violates Environment Freeze unless exception granted)
- **Option B**: Use external debugger/profiler (may not be available in CI environment)
- **Option C**: Escalate to maintainer for investigation (blocks DBEX work)

---

## Lifecycle Decision

Per `<initiative_lifecycle/>` and `<loop_discipline/>` repeat-failure rules:

> If the same acceptance criterion fails in two consecutive loops with substantially the same failure signature, you must either
> (a) reclassify the root cause and switch to/open a fix-plan item that targets the suspected implementation defect (bug), or
> (b) document [...] explicit evidence that only the gate/spec needs adjustment [...] and then follow <spec_change_flow/>.

**Status**: We have (a) investigated the suspected defect (BeamConfig flux), (b) proven it's NOT the root cause, but (c) cannot proceed further without violating Environment Freeze.

**Recommendation**: Mark DIAG-NANOBRAGG-OVERSAMPLE-001 as **stuck — blocked_environment_dependency** and escalate to maintainer OR relax DB-AT-028/029 acceptance criteria via spec_change initiative.

---

## Artifacts

- Diagnostic script: `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/bin/diagnose_zero_output.py` (T2, ready for execution)
- This inspection: `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-02T060000Z/supervisor_code_inspection.md`
- Ralph's failed attempt: `plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-02T230000Z/summary.md`

---

## Next Actions

**Blocked Path**: Cannot debug further without environment modification
**Unblock Options**:
1. **Maintainer investigation** — Request nanobrag_torch developer to debug zero-output issue
2. **Spec-change** — Relax DB-AT-028/029 gates to allow reconstruction pipeline to proceed despite zero initial output
3. **Alternative approach** — Bypass reconstruction helper entirely, use only warm-path simulators from Stage A

**Supervisor Decision**: Switch focus to unblocked initiative per portfolio steering rules.
