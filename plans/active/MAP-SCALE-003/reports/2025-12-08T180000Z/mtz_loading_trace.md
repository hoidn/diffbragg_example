# Refined MTZ Loading Path Trace

**Phase A2 — MAP-SCALE-003**
**Date:** 2025-12-08

---

## Call Chain Diagram

```
CLI Entry
  └─ dbex/refine_one.py:779 main()
       │
       ├─ DataLoad()                      [line 788]
       │
       └─ run_nanobrag_backend()          [line 795]
            │
            ├─ _resolve_sigma_readout()   [line 317]
            │
            ├─ prepare_refinement_inputs() [line 323]
            │
            ├─ load_calibration_metadata() [line 351] (optional)
            │
            ├─ load_refined_mtz()         [line 388] ◄── REFINED MTZ ENTRY
            │   └─ Returns (indices, amplitudes)
            │
            ├─ build_structure_factor_grid() [line 409]
            │   └─ Returns (hkl_grid, hkl_metadata, asu_map)
            │
            ├─ create_unified_simulator() [line 475] (per panel)
            │   └─ Simulator.run()        [line 487]
            │
            ├─ RefinementEngine.run()     [line 584]
            │
            ├─ score_roi_payloads()       [line 677]
            │
            └─ write_torch_outputs()      [line 691]
                 └─ hkl_telemetry emitted [line 196-200]
```

---

## Detailed Call Chain Analysis

### 1. CLI Argument Parsing

**File:** `dbex/refine_one.py:65-68`
```python
ap.add_argument("--refined-mtz", type=str, default=None,
    help="Path to DiffBragg-refined structure factor MTZ...")
```

### 2. Refined MTZ Loading (SCALE-007 Enforcement)

**File:** `dbex/refine_one.py:382-407`

```python
# Line 382-385: Initialize tracking variables
hkl_indices = None
hkl_amplitudes = None
hkl_source = "raw"  # Track telemetry: "refined" or "raw"
hkl_path = None

# Line 386-399: Try refined MTZ if provided
if args.refined_mtz is not None:
    try:
        hkl_indices, hkl_amplitudes = load_refined_mtz(args.refined_mtz, column="F")
        hkl_source = "refined"
        hkl_path = args.refined_mtz
        print(f"[nanobrag backend] Using refined structure factors from {args.refined_mtz}")
        print(f"  n_reflections={len(hkl_indices)}, mean_amplitude={hkl_amplitudes.mean():.3e}")
    except (FileNotFoundError, ValueError, ImportError) as e:
        # SCALE-007: Fail fast when --refined-mtz is provided but cannot be loaded
        raise RuntimeError(
            f"Failed to load refined structure factors from --refined-mtz '{args.refined_mtz}': {e}\n"
            f"When --refined-mtz is provided, refined structure factors MUST be consumed..."
        ) from e

# Line 401-407: Fallback to raw MTZ if refined not requested
if hkl_indices is None:
    hkl_indices = DL.F.indices()
    hkl_amplitudes = DL.F.data()
    hkl_source = "raw"
    hkl_path = args.mtzFile
```

### 3. load_refined_mtz Implementation

**File:** `dbex/nanobrag_bridge.py:1118-1223`

```python
def load_refined_mtz(mtz_path, column="F"):
    """Load refined structure factors from DiffBragg-refined MTZ file."""

    # Line 1153-1158: Path validation
    mtz_file = Path(mtz_path)
    if not mtz_file.exists():
        raise FileNotFoundError(...)

    # Line 1160-1165: Import iotbx.mtz
    from iotbx import mtz as iotbx_mtz

    # Line 1167-1174: Parse MTZ file
    mtz_obj = iotbx_mtz.object(str(mtz_file))

    # Line 1176-1201: Extract amplitude array
    miller_arrays = mtz_obj.as_miller_arrays()
    # Find array matching column label with type 'amplitude'
    f_array = None
    for ma in miller_arrays:
        label = ma.info().label_string()
        type_hints = str(ma.info().type_hints_from_file)
        if column in label and "amplitude" in type_hints:
            f_array = ma
            break

    # Line 1208-1211: Extract indices and amplitudes
    indices = np.array(f_array.indices(), dtype=np.int32)   # shape (n_refl, 3)
    amplitudes = np.array(f_array.data(), dtype=np.float32) # shape (n_refl,)

    return indices, amplitudes
```

### 4. build_structure_factor_grid

**File:** `dbex/nanobrag_bridge.py:856-1018`

```python
def build_structure_factor_grid(indices, amplitudes, device=None, halo=False):
    """Build dense 3D HKL grid and ASU mapping for nanobrag_torch."""

    # Line 904-908: Convert inputs (SCALE-001: NO scaling applied)
    hkls = np.asarray(indices, dtype=int)
    amps = np.abs(np.asarray(amplitudes, dtype=np.float32))

    # Line 916-934: Compute HKL grid bounds with optional halo
    h_min_data, h_max_data = int(hkls[:, 0].min()), int(hkls[:, 0].max())
    # ... k, l bounds ...
    halo_width = 1 if halo else 0
    h_min = h_min_data - halo_width
    # ...

    # Line 937-939: Allocate grid
    grid = torch.zeros((h_range, k_range, l_range), device=device, dtype=torch.float32)

    # Line 968-982: Populate grid with structure factor amplitudes
    for (h, k, l), amp in zip(hkls, amps):
        idx_h = int(h - h_min)
        # ...
        grid[idx_h, idx_k, idx_l] = float(amp)

    return grid, metadata, asu_map
```

---

## Proposed Telemetry Hook Points

### Current State: Telemetry Already Implemented

The structure-factor telemetry is ALREADY captured at these hook points:

| Hook Point | Location | Telemetry Captured |
|------------|----------|-------------------|
| Post `load_refined_mtz` | refine_one.py:388-392 | `hkl_source`, `hkl_path`, print to stdout |
| Pre `build_structure_factor_grid` | refine_one.py:407 | `hkl_source`, `hkl_path` set |
| Post `build_structure_factor_grid` | refine_one.py:414 | Grid stats printed |
| Telemetry Dict Construction | refine_one.py:646-651 | All fields assembled |
| Writer Emission | writer.py:196-200 | Written to HDF5 |

### Existing Telemetry in Path

At `refine_one.py:646-651`:
```python
hkl_telemetry = {
    "hkl_source": hkl_source,
    "hkl_n_reflections": len(hkl_indices),
    "hkl_mean_amplitude": float(hkl_amp_array.mean()),
    "hkl_path": hkl_path if hkl_path else ""
}
```

---

## simulate_forward_once Path (Test/Validation)

**File:** `dbex/nanobrag_bridge.py:1230-1556`

For the `simulate_forward_once()` helper (used by DB-AT-024):

```python
# Line 1535-1541: hkl_telemetry in diagnostics
diagnostics = {
    ...
    "hkl_telemetry": {
        "hkl_source": hkl_source if hkl_source is not None else None,
        "hkl_n_reflections": len(hkl_indices),
        "hkl_mean_amplitude": float(np.asarray(hkl_amplitudes).mean()),
        "hkl_path": hkl_path if hkl_path is not None else ""
    },
    ...
}
```

Called by `test_mapping_consistency.py:271-283`:
```python
bragg, diagnostics = simulate_forward_once(
    inputs=inputs,
    detector=dl.detector,
    ...
    hkl_source=hkl_source,  # "refined" or "raw"
    hkl_path=hkl_path,
    ...
)
```

---

## SCALE-003/SCALE-004 Compliance

The current implementation satisfies:

1. **SCALE-003 (Structure Factor Provenance):**
   - `hkl_source` tracks "refined" vs "raw"
   - `hkl_path` records the MTZ file used
   - Mean amplitude and reflection count captured

2. **SCALE-004 (Calibration Precedence):**
   - Refined MTZ loading attempted first when `--refined-mtz` provided
   - SCALE-007: Fail-fast if refined MTZ cannot be loaded

3. **ARCH-CONTRACT-CALIBRATION-001:**
   - `refine_one.py:376-399` enforces fail-fast behavior
   - No silent fallback to raw MTZ when refined is explicitly requested

---

## Conclusion

The refined MTZ loading path is fully traced and telemetry hook points are already implemented. No additional hook points are required for MAP-SCALE-003 Phase A.

---

## References

- `dbex/refine_one.py:65-68` — CLI flag definition
- `dbex/refine_one.py:382-407` — Refined MTZ loading logic
- `dbex/nanobrag_bridge.py:1118-1223` — `load_refined_mtz()` implementation
- `dbex/nanobrag_bridge.py:856-1018` — `build_structure_factor_grid()`
- `dbex/io/writer.py:196-200` — Telemetry emission
- Finding SCALE-003, SCALE-004, SCALE-007
