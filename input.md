# Input — ARCH-SIM-CONSTRUCTION-001 Phase C.1 Implementation

## Summary
Apply `sqrt(spot_scale_override)` post-run scaling and beam calibration threading to reconstruction helpers, matching Stage A conventions.

## Mode
Parity

## InitiativeType
architecture

## Focus
[ARCH-SIM-CONSTRUCTION-001] — Simulator Construction Convention Alignment (Training vs Reconstruction)

## Branch
integration

## Mapped Tests
- tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity
- tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity

## Artifacts
plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-02T235959Z/

---

## Do Now

### Context

Ralph's Phase A.1 evidence collection (commit 9d3ca6b4, artifacts at plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-02T233717Z/) confirmed root cause: reconstruction helper `build_final_bragg_from_stage_a_telemetry()` (dbex/refinement/reconstruction.py:140-223) omits the explicit `sqrt(spot_scale_override)` post-run multiplication that Stage A applies to every simulator output (stage_a.py:442-443). This produces simulator raw outputs ~23,900× too small (≈(spot_scale)^(1/4)), causing DB-AT-028/029 failures (chi²/pixel initial ~1e5 vs ≤100 spec, ROI correlation before -0.05 vs ≥0.2 floor) even when `log_scale_baseline` extraction logic is correct (commit 6db57f45).

**Strategy:** Implement Option B (Stage A post-run scaling pattern) + Option C (beam calibration threading) per Ralph's recommendation.

### Implement

**File:** `dbex/refinement/reconstruction.py`

**1. Beam Calibration Threading (Option C — lines ~167-170):**

Before the current `beam_config` creation (line 170), extract beam calibration from `config.calibration_metadata`:

```python
# Extract beam calibration for architectural consistency with Stage A (stage_a_utils.py:267)
beam_flux = None
beam_exposure = None
beamsize_mm = None
if config.calibration_metadata is not None:
    beam_flux = config.calibration_metadata.get('beam_flux')
    beam_exposure = config.calibration_metadata.get('beam_exposure')
    beamsize_mm = config.calibration_metadata.get('beamsize_mm')

beam_config = create_beam_config(beam, flux=beam_flux, exposure=beam_exposure, beamsize_mm=beamsize_mm)
```

**2. Post-Run Scaling (Option B — lines ~167 and ~220-223):**

Before the simulator loop (around line 167), extract `spot_scale_override` and compute `sqrt_spot_scale`:

```python
# Extract spot_scale_override for post-run scaling (matches stage_a.py:442-443, SCALE-009)
spot_scale_override = None
if config.calibration_metadata is not None:
    spot_scale_override = config.calibration_metadata.get('spot_scale_override')

sqrt_spot_scale = float(np.sqrt(spot_scale_override)) if spot_scale_override and spot_scale_override > 0 else 1.0
```

Inside the simulator loop (lines ~220-223), apply `sqrt_spot_scale` to raw output before `scale_factor` multiplication:

```python
for pid, sim in zip(sampled_panel_ids, simulators):
    bragg_panel = sim.run()
    bragg_panel_scaled = bragg_panel * sqrt_spot_scale  # ← NEW: consistent with Stage A pattern (SCALE-009)
    bragg_scaled = bragg_panel_scaled * scale_factor
    bragg_full[pid] = bragg_scaled.cpu().numpy().astype(np.float32)
```

**3. Import Required:**

Add `import numpy as np` at the top of the file if not already present.

**4. Validate:**

Run DB-AT-028/029 with full detector + metadata sigma source:

```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=metadata \
DBEX_SMOKE_DETECTOR_SIZE=full \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv \
  tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity \
  tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity \
  --tb=short \
  -o log_cli=true \
  -o log_cli_level=INFO
```

Expected outcomes:
- `bragg_after_mean ≈ O(1) ≈ 0.24` (matching bragg_before_mean, not ~1e-05)
- `chi²/pixel initial ≤ 100` (currently ~1.08e5)
- `median ROI correlation before ≥ 0.2` (currently -0.05)

Capture pytest log to `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-02T235959Z/pytest_db_at_028_029.log`.

---

## How-To Map

1. **Read reconstruction.py to confirm exact line numbers:**
   ```bash
   head -n 230 dbex/refinement/reconstruction.py | tail -n 100
   ```

2. **Edit beam_config creation (lines ~167-170):**
   - Add beam calibration extraction before the existing `beam_config = create_beam_config(beam)` line
   - Update the call to thread `flux`, `exposure`, `beamsize_mm`

3. **Add spot_scale_override extraction before simulator loop (~line 167):**
   - Extract `spot_scale_override` from `config.calibration_metadata`
   - Compute `sqrt_spot_scale = sqrt(spot_scale_override)` with default `1.0` for uncalibrated case

4. **Update simulator loop post-run scaling (lines ~220-223):**
   - Replace `bragg_scaled = bragg_panel * scale_factor` pattern
   - Add intermediate step: `bragg_panel_scaled = bragg_panel * sqrt_spot_scale`
   - Then apply: `bragg_scaled = bragg_panel_scaled * scale_factor`

5. **Run tests with validation environment:**
   - Use exact env vars and selectors listed above
   - Capture pytest output to artifacts directory

6. **Extract and save metrics:**
   - Parse pytest output for `bragg_after_mean`, `chi2_per_pixel_initial`, `roi_cc_median_before`
   - Save to `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-02T235959Z/metrics_comparison.json`

---

## Pitfalls to Avoid

1. **Do not modify factory (`create_unified_simulator`) or Stage A/B/C training logic** — fix is isolated to reconstruction.py cold path only (Exit Criterion #4)

2. **Preserve backward compatibility:**
   - Handle `config.calibration_metadata is None` gracefully (uncalibrated runs default to `sqrt_spot_scale = 1.0`, beam params = None)
   - Do not break legacy tests without calibration metadata

3. **Match Stage A pattern exactly:**
   - Use `sqrt_spot_scale = float(np.sqrt(spot_scale_override))` matching stage_a.py:442
   - Apply it to **every** `sim.run()` output before `scale_factor` multiplication
   - Extract beam params from same keys as stage_a_utils.py:267 (`beam_flux`, `beam_exposure`, `beamsize_mm`)

4. **Do not confuse with warm path:**
   - This fix targets reconstruction cold path only (lines ~177-223)
   - Warm path (lines ~149-165) reuses Stage A simulators and should already have correct scaling via Stage A context
   - Do not modify warm path logic

5. **Device/dtype neutrality:**
   - `sqrt_spot_scale` is a Python float (not tensor), safe for multiplication with GPU/CPU tensors
   - No device movement required

6. **Reference Finding SCALE-009:**
   - Cross-reference docs/findings.md:42 in code comments if adding explanatory notes

---

## If Blocked

If tests still fail after implementation:

1. **Capture debug metrics:**
   - Add temporary logging to print `bragg_panel.mean()`, `sqrt_spot_scale`, `bragg_panel_scaled.mean()`, `bragg_scaled.mean()`
   - Save to `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-02T235959Z/debug_metrics.txt`

2. **Check calibration metadata presence:**
   - Verify `config.calibration_metadata` is not None and contains `spot_scale_override` key
   - If missing, the test fixture may need updating (out of scope for this Do Now; record in Attempts History)

3. **Warm vs cold path confusion:**
   - Verify test is hitting the cold path (no `stage_a_ctx` available)
   - If warm path is active, the fix may not be exercised (record this in Attempts History)

4. **Log the block in Attempts History:**
   - Note exact failure signature (chi², correlation, bragg magnitudes)
   - Include pytest log path and debug metrics
   - Tag as blocked with reason

---

## Findings Applied

**SCALE-009 (Active):** Reconstruction helpers must apply `sqrt(spot_scale_override)` post-run to match Stage A pattern; omitting causes ~23,900× magnitude discrepancy and DB-AT-028/029 failures. This Do Now implements the fix described in SCALE-009.

**SCALE-002, SCALE-004 (Active):** Post-simulation `sqrt(spot_scale_override)` application pattern; reconstruction must follow same convention as Stage A for architectural consistency.

**GEOMETRY-001 (Active):** Bridge must derive beam center and detector vectors exactly per dxtbx mapping; this fix does not touch detector config construction so GEOMETRY-001 remains orthogonal.

**No relevant findings in PHYSICS-LOSS or GRADIENT categories** for this reconstruction cold path fix.

---

## Pointers

- **Spec:** docs/spec-db-core.md §§20-40 (calibration threading contracts)
- **Spec:** docs/architecture/calibration_scaling.md (spot_scale application timing)
- **Ralph's evidence:** plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-02T233717Z/summary.md
- **Stage A reference pattern:** dbex/refinement/stage_a.py:442-443 (post-run sqrt scaling)
- **Stage A beam config pattern:** dbex/refinement/stage_a_utils.py:267 (beam calibration threading)
- **Reconstruction target:** dbex/refinement/reconstruction.py:140-223 (`build_final_bragg_from_stage_a_telemetry` cold path)
- **Tests:** tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity (line ~60), test_db_at_029_structure_parity (line ~120)
- **Plan:** plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md (Phase C.1 checklist)
- **Finding:** docs/findings.md:42 (SCALE-009)

---

## Next Up

(None — focus remains ARCH-SIM-CONSTRUCTION-001 Phase C.1 until DB-AT-028/029 pass)
