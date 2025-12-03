# Input for Ralph (ARCH-SIM-CONSTRUCTION-001 Phase C.3 Diagnostic Probe)

## Summary
Create diagnostic probe to compare raw simulator outputs between `simulate_forward_once()` and reconstruction helper paths to isolate the 23,400× discrepancy source in DB-AT-028/029.

## Mode
none (evidence collection only)

## InitiativeType
architecture

## Focus
[ARCH-SIM-CONSTRUCTION-001] — Simulator Construction Convention Alignment (Training vs Reconstruction)

## Branch
integration

## Mapped tests
```bash
# No tests run this loop — evidence-only probe
# Validation will occur after root cause is confirmed
```

## Artifacts
`plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T220000Z/`

---

## Do Now

### Objective
Isolate the root cause of the 23,400× discrepancy between `bragg_before` (0.239 ADU) and `bragg_after` (1.025e-05 ADU) in DB-AT-028/029 by comparing RAW simulator outputs (before any post-run scaling) from both paths.

### Evidence So Far

**From metrics (loop i=451 debug)**:
- `bragg_before_mean = 0.239` ADU (from `simulate_forward_once()`)
- `bragg_after_mean = 1.025e-05` ADU (from reconstruction helper)
- `spot_scale_override = 3.105e17`, `sqrt(spot_scale) = 5.57e8`
- `log_scale_baseline = 20.138 = log(sqrt(spot_scale))`
- `log_scale_baseline_source = "spot_scale_override_sqrt"` (Priority 2 path, NOT Priority 1)

**From reconstruction debug (loop i=451)**:
- Raw simulator output (first panel): `1.839e-14` ADU
- After scale_factor multiplication: `1.024e-05` ADU (matches bragg_after)

**Hypothesis**:
If `simulate_forward_once()` uses the SAME raw output (1.839e-14) and multiplies by sqrt(spot_scale), it should produce 1.024e-05 ADU, NOT 0.239 ADU.

The 23,400× ratio suggests `simulate_forward_once()` simulators produce raw outputs that are ~23,400× LARGER than reconstruction simulators (~4.29e-10 vs 1.839e-14).

**Possible causes**:
1. Different HKL grids (more/fewer reflections)
2. Different detector configurations (panel count, footprint, oversampling)
3. Different beam calibration (flux, exposure, beamsize)
4. Different simulator internal scaling that we're not aware of

### Task

Create a diagnostic probe script: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulate_forward_once_vs_reconstruction.py`

**Requirements**:

1. **Load the exact DB-AT-028 test configuration**:
   - Use the same detector, beam, crystal, HKL grid, calibration as the failing test
   - Extract from `stage_a_smoke_result` fixture or replicate its setup

2. **Path A: simulate_forward_once()**:
   - Call `simulate_forward_once()` with the test config
   - Capture the `bragg` output (which has sqrt(spot_scale) applied per SCALE-002)
   - **ALSO capture the RAW simulator output BEFORE sqrt scaling**
     (You'll need to instrument `nanobrag_bridge.py:simulate_forward_once()` temporarily to print/return `panel_output_np` before line 1435)

3. **Path B: Reconstruction helper**:
   - Build a simulator using the SAME config via `create_unified_simulator()` (cold path)
   - Run the simulator and capture RAW output
   - Apply `sqrt(spot_scale)` manually
   - Apply `scale_factor = exp(log_scale_baseline + delta)` as reconstruction does

4. **Comparison**:
   - Compare raw simulator outputs (before any scaling) between Path A and Path B
   - Compare final scaled outputs
   - Compute ratios and determine which stage introduces the discrepancy

5. **Output**:
   - `simulation_comparison.json` with:
     - `path_a_raw_mean`, `path_a_raw_max` (simulate_forward_once raw, before sqrt)
     - `path_a_scaled_mean`, `path_a_scaled_max` (simulate_forward_once final, after sqrt)
     - `path_b_raw_mean`, `path_b_raw_max` (reconstruction simulator raw)
     - `path_b_scaled_mean`, `path_b_scaled_max` (reconstruction after sqrt)
     - `path_b_scalefactor_mean`, `path_b_scalefactor_max` (reconstruction after scale_factor)
     - `raw_ratio` (path_a_raw / path_b_raw)
     - `scaled_ratio` (path_a_scaled / path_b_scaled)
     - `spot_scale_override`, `sqrt_spot_scale`, `log_scale_baseline`
     - `verdict`: string indicating where discrepancy occurs

   - `summary.md` with:
     - Interpretation of the ratio
     - Identification of which path/step introduces the 23,400× factor
     - Recommended fix

### Implementation Steps

1. **Create the probe script**:
   ```bash
   touch plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulate_forward_once_vs_reconstruction.py
   chmod +x plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulate_forward_once_vs_reconstruction.py
   ```

2. **Temporarily instrument simulate_forward_once()** (if needed):
   - Add a print statement or return value to capture `panel_output_np` before sqrt scaling (line ~1433)
   - Document this as temporary diagnostic instrumentation

3. **Run the probe**:
   ```bash
   cd /home/ollie/Documents/diffbragg_example
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_SIGMA_SOURCE=metadata \
   DBEX_SMOKE_DETECTOR_SIZE=full \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulate_forward_once_vs_reconstruction.py \
     > plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T220000Z/probe_run.log 2>&1
   ```

4. **Capture artifacts**:
   - Copy output JSON and summary to the report directory
   - Revert any temporary instrumentation to `nanobrag_bridge.py`

---

## How-To Map

**Probe script location**: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulate_forward_once_vs_reconstruction.py`

**Test configuration source**: Replicate the `stage_a_smoke_result` fixture setup from `tests/dbex/test_stage_a_smoke_parity.py:73-170`

**Key comparisons**:
- Raw simulator outputs (before sqrt): Should these match?
- Final outputs (after sqrt and scale_factor): Should reconstruction match simulate_forward_once?

**Expected outcome**:
- If raw outputs differ → simulator construction/config mismatch
- If raw outputs match but scaled differ → scaling logic mismatch
- If both match → test harness or assertion issue

---

## Pitfalls To Avoid

1. **Do NOT modify production code this loop** — evidence collection only
2. **Ensure exact config parity** — use the SAME detector, beam, crystal, HKL grid, calibration between both paths
3. **Capture raw outputs BEFORE any scaling** — the goal is to isolate where the 23,400× factor enters
4. **Document temporary instrumentation** — if you add prints to `nanobrag_bridge.py`, note them in the summary and revert after
5. **Device neutrality** — use CPU to match the test's device selection
6. **Respect Environment Freeze** — do not install packages; treat missing imports as blockers

---

## If Blocked

If the probe reveals that the raw simulator outputs differ due to config mismatch:
- Document which config parameters differ (HKL grid size, beam flux, detector panels, etc.)
- Update `input.md` for next loop with the specific fix needed

If the probe confirms raw outputs match but scaling logic differs:
- Document the exact scaling formula mismatch
- Prepare a corrective Do Now for the reconstruction helper

If the probe shows everything matches:
- Escalate to test harness investigation (DB-AT-028 assertion logic, reference data source)

---

## Findings Applied

- **SCALE-002** (docs/findings.md): sqrt(spot_scale_override) is applied post-simulation in `simulate_forward_once()`; verify reconstruction helper follows the same pattern
- **SCALE-008** (docs/findings.md): log_scale_baseline priority paths (Priority 1 vs Priority 2); test uses Priority 2 (`log_scale_baseline = log(sqrt(spot_scale))`)
- **STAGEA-001** (docs/findings.md): Stage A baseline derivation includes sqrt(spot_scale) multiplication before computing ratio; ensure reconstruction logic is aligned

---

## Pointers

**Spec/Arch references**:
- `docs/spec-db-conformance.md:280-318` — DB-AT-028 acceptance criteria
- `docs/findings.md` — SCALE-002, SCALE-008, STAGEA-001
- `dbex/nanobrag_bridge.py:1433-1438` — simulate_forward_once() sqrt scaling (SCALE-002)
- `dbex/refinement/stage_a.py:1186-1303` — Stage A loss scaling logic
- `dbex/refinement/reconstruction.py:165-262` — Reconstruction helper scaling logic
- `tests/dbex/test_stage_a_smoke_parity.py:176-189` — Test computes bragg_before/after

**Key equations**:
- Priority 2 baseline: `log_scale_baseline = log(sqrt(spot_scale_override))` (stage_a.py:170)
- Stage A loss: `bragg_scaled = raw × exp(log_scale_baseline + delta)` (stage_a.py:1303)
- Reconstruction: `bragg_scaled = raw × exp(log_scale_baseline + delta)` (reconstruction.py:252)
- simulate_forward_once: `bragg = panel_output_np × sqrt_scale_value` (nanobrag_bridge.py:1435)

---

## Next Up (Optional)

None — this is a blocking evidence probe. Galph will analyze results in the next loop before planning corrective action.

---

## Doc Sync Plan

Not applicable — no tests added/renamed this loop.
