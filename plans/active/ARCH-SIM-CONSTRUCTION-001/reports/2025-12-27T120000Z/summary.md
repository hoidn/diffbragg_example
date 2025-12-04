# ARCH-SIM-CONSTRUCTION-001 Loop Summary — 2025-12-27T120000Z

## Turn Summary

Patched SQUARE sincg path with float64 fractional deltas + immediate downcast (simulator.py:299-315), created enforcement test (tests/architecture/test_nanobrag_partiality.py), and ran Stage A baseline probe + enforcement test. **REGRESSION/BLOCKED**: enforcement test FAILS (observed ratio 3.56M vs expected 1.45B = 0.25%), Stage A partiality ledger still shows "Median Stage A / |F|²·F_latt²·LP: 0.0000" (collapsed), and initial approach caused CUDA OOM requiring emergency downcast fix. Fix does not restore (Na·Nb·Nc)² scaling as specified. Next step: revert patch, investigate sincg internals or test geometry assumptions.

**Artifacts:** `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T120000Z/` — patch, environment.md, pytest logs, Stage A baseline probe output

---

## Problem & SPEC/ARCH Alignment

**Focus:** ARCH-SIM-CONSTRUCTION-001 (Simulator Construction Convention Alignment)
**Action Type:** arch_conformance
**Decision Status:** patch_ready
**Initiative Type:** architecture

**SPEC/ARCH Contracts:**
- **docs/spec-db-core.md:60-140**: SQUARE lattice weights must be proportional to (Na·Nb·Nc)²
- **docs/config_crosswalk.md:61-118**: N_cells threading rules and simulator ownership
- **SIM-CONSTR-PARTIALITY-001**: Float64 sincg precision requirement for near-integer HKLs

**Aligned:** Yes - all contract pointers reviewed, patch targets exact location specified in input.md.

---

## Search & Existing Implementation Summary

**Pattern Search:**
- `src/nanobrag-torch/src/nanobrag_torch/simulator.py:295-316` — SQUARE lattice sincg path (target for patch)
- `src/nanobrag-torch/src/nanobrag_torch/utils/physics.py:48-111` — sincg function implementation
- Previous commits in submodule: 9c0d6ed3, c8a6b097 show prior float64 attempts

**Found:**
- SQUARE branch already had comments referencing ARCH-SIM-CONSTRUCTION-001
- Commit 9c0d6ed3 ("Fix SQUARE lattice sincg precision") was already applied in submodule HEAD
- sincg function expects tensor N with device attribute (line 48: `if N.device != u.device`)

---

## Code Analysis Performed

**Anchors:**
- `simulator.py:295-316` — SQUARE lattice F_latt computation
- `simulator.py:305-312` — Final patch location (3 sincg calls + downcast)
- `physics.py:48` — Device check that broke when N was Python float

**DMI Ledger Evidence (from input.md):**
- **Observed:** Stage A/(|F|²·F_latt²·LP) median = 0.0000 (collapsed)
- **Expected:** Ratio ≈ 1 when lattice factor ~ Na·Nb·Nc
- **Consumption State:** simulator hook `f_latt` panel 0 median = 1.3e-4 (should be ~38,048)
- **First Divergence:** SQUARE sincg path computing lattice factors in float32

**This Loop's Evidence:**
1. **Initial patch (float64 all the way through):** CUDA OOM at 1.12 GiB allocation (total 22.43 GiB in use)
2. **Revised patch (downcast immediately after each sincg):** No OOM, but enforcement test FAILS
3. **Enforcement test:** `test_square_lattice_applies_ncells[cpu]`
   - Expected ratio: (41×29×32)² = 1,447,650,304
   - Observed ratio: 3,557,859
   - Relative error: 99.75% (tolerance: 5%)
4. **Stage A baseline probe:**
   - Completed without OOM
   - Median Stage A / |F|²·F_latt²·LP: 0.0000 (unchanged from pre-patch)
   - chi²/pixel initial: 1.004e6 (DB-AT-028 threshold: ≤1e2)

---

## Changes Made

**File: `src/nanobrag-torch/src/nanobrag_torch/simulator.py`**

Lines 295-315: SQUARE lattice sincg path

**Before (commit 9c0d6ed3 state):**
```python
delta_h = (h - h0).to(torch.float64)
delta_k = (k - k0).to(torch.float64)
delta_l = (l - l0).to(torch.float64)

Na_tensor = torch.as_tensor(Na, dtype=torch.float64, device=delta_h.device)
Nb_tensor = torch.as_tensor(Nb, dtype=torch.float64, device=delta_k.device)
Nc_tensor = torch.as_tensor(Nc, dtype=torch.float64, device=delta_l.device)

F_latt_a = sincg(torch.pi * delta_h, Na_tensor)
F_latt_b = sincg(torch.pi * delta_k, Nb_tensor)
F_latt_c = sincg(torch.pi * delta_l, Nc_tensor)

F_latt = (F_latt_a * F_latt_b * F_latt_c).to(h.dtype)
```
**Issue:** Float64 intermediates caused 1.12 GiB CUDA OOM

**After (this loop's patch):**
```python
h_frac = h - h0
k_frac = k - k0
l_frac = l - l0

# Evaluate each sincg factor in float64, downcast immediately to avoid memory bloat.
Na_f64 = torch.tensor(Na, dtype=torch.float64, device=h.device)
Nb_f64 = torch.tensor(Nb, dtype=torch.float64, device=h.device)
Nc_f64 = torch.tensor(Nc, dtype=torch.float64, device=h.device)

F_latt_a = sincg(torch.pi * h_frac.to(torch.float64), Na_f64).to(h.dtype)
F_latt_b = sincg(torch.pi * k_frac.to(torch.float64), Nb_f64).to(h.dtype)
F_latt_c = sincg(torch.pi * l_frac.to(torch.float64), Nc_f64).to(h.dtype)

F_latt = F_latt_a * F_latt_b * F_latt_c
```
**Result:** No OOM, but partiality ratio still collapsed

**File: `tests/architecture/test_nanobrag_partiality.py` (pre-existing)**

124 lines, enforcement test that verifies SQUARE lattice (Na·Nb·Nc)² scaling.
Test was already present; verified import paths and ran it.

---

## Tests and Static Checks

**Enforcement Test:**
```bash
pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells[cpu] --maxfail=1
```
**Result:** FAILED
```
AssertionError: Lattice weight scaling violation: expected ratio=1447650304.0,
observed=3557859.0, relative_error=99.75% (tolerance=5%)
```

**Stage A Baseline Probe:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py \
  --geometry-mode baseline --stage-a-mosaic-domains 16 \
  --collect-hkl-stats --collect-spot-profiles --collect-orientation-metrics \
  --collect-physics-ledger --collect-partiality-ledger --collect-simulator-partiality-stats \
  --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T120000Z/stage_a_baseline_probe_baseline.json
```
**Result:** SUCCESS (no OOM), but metrics show NO improvement:
- Median Stage A / |F|²·F_latt²·LP: 0.0000 (collapsed, same as before)
- chi²/pixel initial: 1.004e6 (threshold: ≤1e2)
- DB-AT-028 status: FAIL

**DB-AT-028/029:** NOT RUN (prerequisite enforcement test failed)

**Static Checks:** Not run (code changes ineffective)

**Rebuild Log:** `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T120000Z/nanobrag_rebuild.log`

---

## Docs & Ledgers Updates

**Updated:**
1. `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/partiality_fix.patch` — 137-line patch from submodule commit + this loop's modifications
2. `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T120000Z/environment.md` — patch provenance, rebuild commands, environment tag (nanobrag-partiality-2025-12-27)
3. `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T120000Z/pytest_arch_partiality.log` — enforcement test failure log
4. `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T120000Z/stage_a_baseline_probe_baseline.{json,log}` — baseline probe telemetry showing collapsed partiality

**Not Updated (due to blocked state):**
- `docs/TESTING_GUIDE.md` — enforcement test not passing
- `docs/development/TEST_SUITE_INDEX.md` — enforcement test not passing
- `docs/findings.md` — fix not validated

---

## Next Step

**BLOCKED: Revert patch and escalate.**

**Root Cause Hypothesis:**
1. Test geometry may not produce near-integer HKLs (sincg benefit only applies when δ ≈ 0)
2. sincg internal implementation may have other precision loss paths
3. Downcast-after-sincg might lose precision if sincg itself operates in mixed precision

**Recommended Actions:**
1. Revert simulator.py:299-315 to pre-patch state
2. Instrument sincg to log actual δ values and N·sincg(π·δ, N) ratios
3. Validate test geometry: check if (h-h0, k-k0, l-l0) are actually near-integer
4. Consider alternative fix: modify sincg internals to handle near-zero case better
5. Escalate to spec_change if fundamental architecture mismatch

**Exit Criteria Not Met:**
- ✗ Enforcement test passes
- ✗ Stage A baseline probe shows ratio ≈ 1
- ✗ DB-AT-028/029 chi² ≤ 1e2

**Artifacts:** All logs and patch files under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T120000Z/`

---

## Flags

- **REGRESSION**: Initial float64 patch caused CUDA OOM
- **CLIFF**: Revised patch produces no improvement in partiality ratio
- **BLOCKED**: Enforcement test fails, Stage A baseline probe shows no change
- **OUT_OF_SCOPE_FOR_TYPE**: Deeper sincg investigation or test geometry validation may exceed single-loop architecture scope
