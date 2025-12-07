# CLI Plumbing Verification — MAP-SCALE-003 Phase B

## Summary
CLI correctly threads hkl_source and hkl_path from argument parsing through to writer serialization. All telemetry plumbing validated.

## Data Flow Anchors

### 1. HKL Source/Path Resolution (dbex/refine_one.py)

**Lines 376-401**: `run_nanobrag_backend` function resolves hkl_source and hkl_path

```python
# Line 378: Initialize hkl_source tracking variable
hkl_source = "raw"  # Track telemetry: "refined" or "raw"
hkl_path = None

# Lines 380-393: Refined MTZ path (--refined-mtz takes precedence)
if args.refined_mtz is not None:
    try:
        hkl_indices, hkl_amplitudes = load_refined_mtz(args.refined_mtz, column="F")
        hkl_source = "refined"  # Line 383
        hkl_path = args.refined_mtz  # Line 384
        # ... success logging
    except (FileNotFoundError, ValueError, ImportError) as e:
        # SCALE-007: Fail fast when --refined-mtz provided but cannot load
        raise RuntimeError(...)

# Lines 396-401: Fallback to raw MTZ if refined not requested
if hkl_indices is None:
    hkl_indices = DL.F.indices()
    hkl_amplitudes = DL.F.data()
    hkl_source = "raw"  # Line 399
    hkl_path = args.mtzFile  # Line 400
```

**Validation**: ✓ hkl_source set to "refined" when --refined-mtz provided, "raw" otherwise
**Validation**: ✓ hkl_path set to absolute path from --refined-mtz or --mtzFile

### 2. JobContext Threading (dbex/refine_one.py)

**Lines 532-544**: JobContext receives hkl_source and hkl_path

```python
job_context = build_job_context(
    cli_args=args,
    dataload=DL,
    calibration_metadata=calibration_metadata,
    sigma_provenance=sigma_provenance,
    sigma_reference_value=sigma_reference_target_units,
    refinement_config=refine_config,
    hkl_metadata=hkl_metadata,
    asu_map=asu_map,
    spot_scale_override=spot_scale,
    hkl_source=hkl_source,  # Line 542
    hkl_path=hkl_path,      # Line 543
)
```

**Validation**: ✓ CLI threads hkl_source/hkl_path to JobContext for engine consumption

### 3. HKL Telemetry Dict Construction (dbex/refine_one.py)

**Lines 640-645**: Telemetry dict built with CLI-resolved values

```python
hkl_telemetry = {
    "hkl_source": hkl_source,  # Line 641: CLI-resolved value
    "hkl_n_reflections": len(hkl_indices),  # Line 642: Computed stat
    "hkl_mean_amplitude": float(hkl_amp_array.mean() if hasattr(hkl_amp_array, 'mean') else np.mean(hkl_amp_array)),  # Line 643
    "hkl_path": hkl_path if hkl_path else ""  # Line 644: CLI-resolved path
}
```

**Validation**: ✓ Telemetry dict constructed with correct schema fields (hkl_source, hkl_n_reflections, hkl_mean_amplitude, hkl_path)
**Validation**: ✓ hkl_n_reflections and hkl_mean_amplitude computed from actual HKL data

### 4. Writer Invocation (dbex/refine_one.py)

**Lines 685-698**: write_torch_outputs receives hkl_telemetry dict

```python
write_torch_outputs(
    args,
    DL,
    Bragg,
    inputs,
    masked_mse,
    hkl_telemetry,  # Line 691: Dict passed to writer
    refine_telemetry,
    sigma_readout_provenance=sigma_provenance,
    sigma_readout_reference_value=sigma_reference_target_units,
    stage_artifacts=engine_artifacts,
    roi_payloads=roi_payloads,
    stage_results=stage_results,
)
```

**Validation**: ✓ hkl_telemetry dict passed to write_torch_outputs at line 691

## Telemetry Schema Validation

Per ARCH-CONTRACT-WRITER-001, the writer must serialize hkl_telemetry dict to /torch_diagnostics HDF5 group attrs. Phase A audit confirmed writer correctly persists all four fields:

- `hkl_source` (string: "refined" or "raw")
- `hkl_n_reflections` (int)
- `hkl_mean_amplitude` (float)
- `hkl_path` (string: absolute path)

## Conclusion

**CLI plumbing is COMPLETE and correct.** All gaps from MAP-SCALE-003 Phase A planning are resolved:

1. ✓ hkl_source correctly set based on --refined-mtz vs --mtzFile precedence (lines 378-401)
2. ✓ hkl_path correctly captures absolute MTZ path (lines 384, 400)
3. ✓ Telemetry dict construction includes all four schema fields (lines 640-645)
4. ✓ Writer receives hkl_telemetry dict (line 691)
5. ✓ Writer serialization to HDF5 attrs already implemented (Phase A audit)

**No production code changes required.** Phase B proceeds to test assertion validation.
