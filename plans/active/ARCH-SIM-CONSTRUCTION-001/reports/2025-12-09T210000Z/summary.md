# ARCH-SIM-CONSTRUCTION-001 Intensity + Calibration Metrics Summary

## Per-Path Results

### Stage A Warm-Cache Path

- **Raw output mean:** `1.713925e-09`
- **Scaled output mean:** `9.550518e-01`
- **sqrt(spot_scale):** `5.572305e+08`
- **log_scale_baseline:** `20.138490`
- **beam_flux:** `1000000000000.0`
- **beam_exposure:** `1.0`
- **beamsize_mm:** `1.0`

### Reconstruction Cold-Path

- **Raw output mean:** `2.023952e-09`
- **Scaled output mean:** `1.127808e+00`
- **scale_factor (exp(log_scale_baseline)):** `5.572305e+08`
- **sqrt(spot_scale):** `5.572305e+08`
- **log_scale_baseline:** `20.138490`
- **beam_flux:** `1000000000000.0`
- **beam_exposure:** `1.0`
- **beamsize_mm:** `1.0`

### simulate_forward_once Mapping Path

- **Raw output mean:** `1.713925e-09`
- **Scaled output mean:** `9.550518e-01`
- **sqrt(spot_scale):** `5.572305e+08`
- **beam_flux:** `1000000000000.0`
- **beam_exposure:** `1.0`
- **beamsize_mm:** `1.0`

## Cross-Path Ratios

### Raw Output Ratios (before post-run scaling)

- **Stage A / Reconstruction:** `8.468210e-01`
- **Stage A / Mapping:** `1.000000e+00`
- **Reconstruction / Mapping:** `1.180887e+00`

### Scaled Output Ratios (after post-run scaling)

- **Stage A / Reconstruction:** `8.468214e-01`
- **Stage A / Mapping:** `1.000000e+00`
- **Reconstruction / Mapping:** `1.180887e+00`

## Interpretation

**Verdict: Reconstruction path DIVERGES from Stage A + Mapping**

Stage A and simulate_forward_once produce matching raw outputs, but reconstruction cold-path produces different magnitude. This indicates a simulator construction difference in create_unified_simulator factory when called from reconstruction helpers.

**Recommended next steps:**
1. Audit reconstruction.py:187-217 config construction (beam_config, crystal_config, detector_config)
2. Compare calibration metadata threading (beam_flux, beam_exposure, beamsize_mm, N_cells)
3. Verify spot_scale_override is passed correctly to create_unified_simulator
4. Check for oversample mismatch (should be 3 for all paths)
