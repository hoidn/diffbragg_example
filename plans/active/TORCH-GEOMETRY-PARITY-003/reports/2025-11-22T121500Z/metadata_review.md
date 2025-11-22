# Phase A2: Metadata Review — refGeom.expt Inspection

**Initiative:** TORCH-GEOMETRY-PARITY-003
**Timestamp:** 2025-11-22T121500Z
**Phase:** A2 (Metadata Review)

## Summary

Inspected `refGeom.expt` DIALS experiment JSON for calibration metadata, processing history, and environmental conditions that might explain the det(U)≠1 observation from PARITY-002 Phase C1.

## Metadata Extracted

### Detector
- **Type:** `SENSOR_PAD` (generic detector type)
- **No scan object:** This is a still image (single frame), not a rotation dataset

### Beam
- **Wavelength:** 0.9768 Å (typical for synchrotron X-ray diffraction)

### Imageset
- **Template:** Not available (N/A)
- **Processing context:** Limited metadata; no explicit MOSFLM or DIALS indexing parameters visible via high-level API

## Key Observations

### No explicit calibration/scale factors visible
The high-level dxtbx API does not expose:
- MOSFLM processing history
- Upstream refinement flags
- Isotropic scale corrections applied during indexing
- Environmental conditions (temperature, pressure)

### Consistency with dxtbx audit results
The **Phase A1 dxtbx audit** showed:
- `det(U_from_dxtbx) = 1.0000000000000007` (essentially unity, within floating-point precision)
- `det(A*) = 3.773e-05`, `det(B_ideal) = 3.773e-05` (match to ~15 significant figures)
- `A* = U @ B_ideal` identity validated to `max_abs_diff = 3.5e-18` (roundoff-level)

This proves that **dxtbx A* and unit cell are internally consistent** — there is NO 0.06% volume scaling artifact in the experiment file itself.

## Critical Discrepancy: MOSFLM A* Source

### Contradiction with PARITY-002 findings

**PARITY-002 Phase C1** reported:
- `det(U₀) = 1.000557` when deriving U from **"mapping MOSFLM A*"**
- This 0.06% offset was attributed to the A* matrix used for mapping

**PARITY-003 Phase A1** (this initiative) shows:
- `det(U_from_dxtbx) = 1.0` when deriving U from **`dxtbx crystal.get_A()`**

### Hypothesis: Mapping code uses different A* source

The **mapping MOSFLM A*** referenced in prior attempts is likely NOT the same as `dxtbx crystal.get_A()`. Possible sources:

1. **Legacy MOSFLM file:** The mapping code may load A* from a separate `.mosflm` or `.mat` file with calibrated/scaled values
2. **Intermediate processing artifact:** A* may be extracted from an intermediate DIALS/MOSFLM refinement step with different conventions
3. **Code bug in mapping extraction:** The `dbex/nanobrag_bridge.py` mapping logic may apply an unintended scale factor when converting dxtbx geometry to MOSFLM A*

### Action Required: Trace mapping A* extraction

To resolve this discrepancy, we must:
1. Identify where "mapping MOSFLM A*" is extracted in `dbex/nanobrag_bridge.py` or related modules
2. Compare the extracted A* matrix against `dxtbx crystal.get_A()` numerically
3. Determine if the 0.06% scaling is introduced during dxtbx→MOSFLM conversion or loaded from external file

## Hypothesis Status Update

Based on Phase A1 + A2 evidence:

- **H1 (dxtbx A*/cell inconsistency):** **REJECTED** — dxtbx is internally consistent (det(U)=1.0, perfect A*=U@B identity)
- **H2 (Physical volume scaling):** **Unlikely** — no environmental metadata suggesting thermal/pressure effects; dxtbx cell is self-consistent
- **H3 (Numerical precision):** **REJECTED** — cctbx B_ideal matches dxtbx `get_B()` exactly (max_diff=0.0), roundtrip is stable

### New Hypothesis: H4 (Mapping Code Artifact)

**H4: Mapping A* extraction introduces spurious scale**
- The 0.06% det offset is NOT in the refGeom.expt file itself
- It is introduced during the extraction of "MOSFLM A*" in the mapping initialization code
- Possible sources: incorrect transpose/convention, scale factor from MOSFLM file, or dxtbx→MOSFLM conversion bug

## Next Actions

### Phase A3: Numerical Precision Test (Optional)
- Given that Phase A1 already validated cctbx roundtrip (B_ideal vs dxtbx get_B() match exactly), Phase A3 is **LOW PRIORITY**
- Can defer unless Phase A4 synthesis requires additional validation

### Phase A4: Root Cause Determination (HIGH PRIORITY)
Before synthesizing the Phase A decision, we must:
1. **Locate mapping A* extraction code** in `dbex/nanobrag_bridge.py` or `dbex/data_load.py`
2. **Instrument the extraction** to log the raw A* matrix and its determinant
3. **Compare against dxtbx audit** to identify where the 0.06% scaling is introduced

If mapping code directly uses `dxtbx crystal.get_A()`, then the det(U)≠1 observation from PARITY-002 may have been a measurement/logging error, and the **problem may already be resolved** by the quaternion infrastructure changes in PARITY-002 Phase B.

## Artifacts

- `metadata_snippet.txt`: High-level experiment metadata (detector, beam, scan)
- `dxtbx_a_star_cell_audit.json`: Phase A1 audit showing det(U)=1.0 from dxtbx data

---

**Conclusion:** The det(U)≠1 anomaly is NOT in the experiment file; it must originate from the mapping code's A* extraction logic. Phase A4 synthesis requires code audit to locate the source.
