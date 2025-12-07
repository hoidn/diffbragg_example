# Schema Audit — CLI Refined Structure Factor Telemetry

## Summary
Audit of `dbex/io/writer.py::_write_torch_outputs` HDF5 `/torch_diagnostics` schema to identify extension points for structure-factor telemetry fields per ARCH-CONTRACT-WRITER-001.

## Findings

### Current HDF5 Schema (dbex/io/writer.py:180-201)

**Existing attributes under `/torch_diagnostics` group**:
- `masked_mse` (float) — Masked mean squared error between target and Bragg
- `loss_mask_coverage` (float) — Fraction of pixels in loss mask
- `n_rois` (int) — Number of ROI bboxes
- `target_shape` (str) — Shape of target tensor as string
- `backend` (str) — Backend identifier ("nanobrag")
- `sigma_readout_provenance` (str, optional) — Source of sigma_readout (CLI, metadata, etc.)
- `sigma_readout_reference_value` (float, optional) — Reference value for sigma in target units
- `roi_scoring_method` (str) — ROI scoring method identifier ("nelder_mead")
- `roi_checker` (str) — ROI checker class path ("score_trainer.roi_check.roiCheck")

**Structure-factor telemetry (lines 196-200, SCALE-003)**:
- `hkl_source` (str) — Distinguishes "refined" vs "raw" MTZ provenance
- `hkl_n_reflections` (int) — Reflection count from HKL grid
- `hkl_mean_amplitude` (float) — Mean |F| amplitude for diagnostics
- `hkl_path` (str) — Absolute path to MTZ file (or empty string if default)

**Multi-stage refinement telemetry (lines 202-432)**:
- Per-stage subgroups: `/torch_diagnostics/stage_A`, `/torch_diagnostics/stage_B`, `/torch_diagnostics/stage_C`
- Each stage group contains loss traces, chi-squared metrics, optimizer config, perf counters
- Top-level legacy attrs mirror Stage A for backward compatibility (single-stage mode)

### Schema Extension Points

**Status**: **Structure-factor telemetry already implemented** (lines 196-200).

The writer function signature (line 41-54) already accepts `hkl_telemetry` parameter:
```python
def write_torch_outputs(
    args,
    data_load,
    bragg,
    inputs,
    masked_mse,
    hkl_telemetry,  # <- Required parameter
    ...
)
```

**Implementation details** (lines 196-200):
```python
# Structure-factor telemetry (SCALE-003: track refined vs raw MTZ)
diag.attrs["hkl_source"] = hkl_telemetry["hkl_source"]
diag.attrs["hkl_n_reflections"] = int(hkl_telemetry["hkl_n_reflections"])
diag.attrs["hkl_mean_amplitude"] = float(hkl_telemetry["hkl_mean_amplitude"])
diag.attrs["hkl_path"] = str(hkl_telemetry["hkl_path"])
```

**Contract**: Writer expects `hkl_telemetry` dict with 4 required keys:
- `hkl_source`: str
- `hkl_n_reflections`: int
- `hkl_mean_amplitude`: float
- `hkl_path`: str

### Backward Compatibility

**No breaking changes**:
- New attrs are additive (appended to existing `/torch_diagnostics` group)
- Existing field names/types unchanged
- Schema versioning not required (additive-only extension)

**Compatibility risks**: None identified
- Existing parsers ignore unknown attrs (h5py read patterns are attr-selective)
- Tests access telemetry via explicit attr keys (no schema iteration dependencies)

### Architecture Conformance

**ARCH-CONTRACT-WRITER-001 compliance**:
- Owner module: `dbex/io/writer.py::write_torch_outputs` ✓
- HDF5 /torch_diagnostics group schema preserved ✓
- Backward compatibility maintained (additive extension) ✓
- Consumer contracts (test_torch_diagnostics_metadata, DB-AT-024) compatible ✓

**No violations detected**.

## Next Actions

Phase B implementation scope reduced: **schema already implemented in writer** (SCALE-003 landing).

Remaining Phase B work:
1. Verify CLI plumbing populates `hkl_telemetry` dict correctly (trace `dbex/refine_one.py` → `write_torch_outputs` call site)
2. Confirm `simulate_forward_once` returns `hkl_telemetry` in diagnostics (MAP-SCALE-004 precedent)
3. Extend regression tests to assert on new attrs (backward-compatible validation)

## References

- dbex/io/writer.py:180-201 — HDF5 schema serialization (DIAGNOSTICS-001, SCALE-003)
- dbex/io/writer.py:41-54 — Function signature with `hkl_telemetry` parameter
- docs/architecture/dbex/io/writer.idl.md:55-85 — Writer diagnostics contract
- docs/findings.md SCALE-003 — Zero-iteration helper refined MTZ ingestion requirement
