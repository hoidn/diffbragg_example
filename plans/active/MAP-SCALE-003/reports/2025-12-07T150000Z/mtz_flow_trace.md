# MTZ Flow Trace — Refined Structure Factor Loading Path

## Summary
Call chain trace from CLI `--refined-mtz` argument through refined MTZ loading, structure-factor grid construction, and diagnostics payload emission.

## Call Chain (file:line anchors)

### 1. CLI Argument Ingestion
**File**: `dbex/refine_one.py`

**Anchor**: Lines 65-68
```python
ap.add_argument("--refined-mtz", type=str, default=None,
    help="Path to DiffBragg-refined structure factor MTZ (e.g., refined_structure_factors.mtz). "
         "When provided, uses refined Fopt instead of raw MTZ amplitudes per SCALE-003/SCALE-004. "
         "Falls back to --mtzFile if missing or invalid.")
```

**Responsibility**: Accept optional path to refined MTZ file from user

---

### 2. Refined MTZ Loading
**File**: `dbex/nanobrag_bridge.py`

**Function**: `load_refined_mtz` (lines 1118-1230)

**Anchor**: Line 1118
```python
def load_refined_mtz(mtz_path, column="F"):
    """Load refined structure factors from DiffBragg-refined MTZ file.
    ...
    Returns:
        tuple: (indices, amplitudes) where:
            - indices: numpy array of Miller indices, shape (n_refl, 3), dtype int
            - amplitudes: numpy array of refined |F| values, shape (n_refl,), dtype float32
    """
```

**Key behavior**:
- Reads MTZ file using `iotbx.mtz` (lines 1168-1174)
- Extracts Miller arrays with column matching (lines 1178-1201)
- Returns indices + amplitudes as numpy arrays (lines 1208-1210)
- **No scaling applied** per SCALE-001 (line 1141)

**Telemetry hook opportunity**: After amplitude extraction (line 1210), before return
- Compute `hkl_n_reflections = len(indices)`
- Compute `hkl_mean_amplitude = np.mean(amplitudes)`
- Tag `hkl_source = "refined"` (constant for this function)

---

### 3. Structure Factor Grid Construction
**File**: `dbex/nanobrag_bridge.py`

**Function**: `build_structure_factor_grid` (lines 856-1116)

**Anchor**: Line 856
```python
def build_structure_factor_grid(indices, amplitudes, device=None, halo=False):
    """Build dense 3D HKL grid and ASU mapping for nanobrag_torch from MTZ reflections.
    ...
    Returns:
        tuple: (grid, metadata, asu_map) where
            - grid: torch.Tensor, shape (h_range, k_range, l_range), dtype float32
            - metadata: dict with HKL range, grid stats, coverage info, and 'has_halo' flag
            - asu_map: torch.Tensor, same shape as grid, dtype int32 with ASU indices or -1
    """
```

**Key behavior**:
- Converts indices/amplitudes to HKL grid on specified device (lines 904-940)
- **No scaling applied** per SCALE-001 (lines 907-913)
- Returns grid + metadata dict + ASU map

**Metadata returned** (lines 856-877):
- HKL range bounds (h_min, h_max, k_min, k_max, l_min, l_max)
- Grid stats (min/max/mean amplitudes)
- Coverage info
- `has_halo` flag

**Telemetry gap**: `metadata` dict does not currently include reflection count or source provenance
- These must be computed/tagged by caller (e.g., `simulate_forward_once`)

---

### 4. Zero-Iteration Helper (Diagnostics Emission)
**File**: `dbex/nanobrag_bridge.py`

**Function**: `simulate_forward_once` (lines 1230-1500+)

**Anchor**: Line 1230
```python
def simulate_forward_once(
    inputs: RefinementInputs,
    detector,
    beam,
    crystal,
    experiment,
    hkl_indices: np.ndarray,
    hkl_amplitudes: np.ndarray,
    spot_scale_override: Optional[float] = None,
    calibration: Optional[dict] = None,
    hkl_source: Optional[str] = None,  # <- Telemetry param (line 1240)
    hkl_path: Optional[str] = None,    # <- Telemetry param (line 1241)
    ...
) -> Tuple[np.ndarray, dict]:
```

**Key behavior**:
- Accepts `hkl_source` and `hkl_path` as optional telemetry parameters (lines 1240-1241)
- Calls `build_structure_factor_grid(hkl_indices, hkl_amplitudes, device)` (line 1345)
- Constructs diagnostics payload dict (lines 1290-1312)

**Diagnostics payload** (lines 1305-1309):
```python
# hkl_telemetry: Dict with structure-factor metadata:
#     - hkl_source: "refined" or "raw" (or None if not provided)
#     - hkl_n_reflections: Number of reflections
#     - hkl_mean_amplitude: Mean structure factor amplitude
#     - hkl_path: Path to MTZ file (or empty string if not provided)
```

**Telemetry construction site**: Not visible in read window, but docstring indicates telemetry dict returned in diagnostics

**Hook point**: Must construct `hkl_telemetry` dict after calling `build_structure_factor_grid` and before returning diagnostics

---

### 5. CLI Backend Integration
**File**: `dbex/refine_one.py`

**Expected call pattern** (not shown in read window, inferred from --refined-mtz arg):
```python
# Pseudo-code based on CLI arg and function signatures
if args.refined_mtz is not None:
    hkl_indices, hkl_amplitudes = load_refined_mtz(args.refined_mtz, column="F")
    hkl_source = "refined"
    hkl_path = args.refined_mtz
else:
    # Fall back to raw MTZ from --mtzFile
    hkl_indices = ...  # from dl.F or similar
    hkl_amplitudes = ...
    hkl_source = "raw"
    hkl_path = args.mtzFile

# Later: pass to simulate_forward_once or call writer directly
bragg, diagnostics = simulate_forward_once(
    ...,
    hkl_indices=hkl_indices,
    hkl_amplitudes=hkl_amplitudes,
    hkl_source=hkl_source,
    hkl_path=hkl_path,
    ...
)

# Extract hkl_telemetry from diagnostics
hkl_telemetry = diagnostics["hkl_telemetry"]

# Pass to writer
write_torch_outputs(
    ...,
    hkl_telemetry=hkl_telemetry,
    ...
)
```

---

## Telemetry Hook Points Summary

### Hook Point A: Post-Grid Construction (simulate_forward_once)
**Location**: `dbex/nanobrag_bridge.py::simulate_forward_once`, after `build_structure_factor_grid` call

**Responsibility**: Construct `hkl_telemetry` dict from function parameters + computed stats
```python
hkl_telemetry = {
    "hkl_source": hkl_source if hkl_source is not None else "unknown",
    "hkl_n_reflections": len(hkl_indices),
    "hkl_mean_amplitude": float(np.mean(np.abs(hkl_amplitudes))),
    "hkl_path": hkl_path if hkl_path is not None else "",
}
diagnostics["hkl_telemetry"] = hkl_telemetry
```

**Rationale**:
- `simulate_forward_once` has access to both user-provided tags (`hkl_source`, `hkl_path`) and raw data (`hkl_indices`, `hkl_amplitudes`)
- Avoids duplication: single computation site for all consumers (CLI, tests)

### Hook Point B: CLI Backend (dbex/refine_one.py)
**Location**: `dbex/refine_one.py::run_nanobrag_backend` (function not yet read, inferred)

**Responsibility**: Populate `hkl_source` and `hkl_path` based on `--refined-mtz` vs `--mtzFile` precedence
```python
if args.refined_mtz is not None:
    hkl_indices, hkl_amplitudes = load_refined_mtz(args.refined_mtz)
    hkl_source = "refined"
    hkl_path = args.refined_mtz
else:
    # Raw MTZ fallback
    hkl_indices = dl.F.indices()
    hkl_amplitudes = dl.F.data()
    hkl_source = "raw"
    hkl_path = args.mtzFile
```

**Rationale**: CLI is the authoritative source for refined vs raw decision

---

## Verification Plan

Phase B implementation must confirm:
1. CLI plumbing correctly populates `hkl_source` and `hkl_path` before passing to `simulate_forward_once`
2. `simulate_forward_once` constructs `hkl_telemetry` dict and includes it in diagnostics return
3. CLI backend extracts `hkl_telemetry` from diagnostics and passes to `write_torch_outputs`
4. Tests (DB-AT-024, test_torch_diagnostics_metadata) assert on telemetry attrs in HDF5 artifacts

## References

- dbex/refine_one.py:65-68 — `--refined-mtz` CLI argument definition
- dbex/nanobrag_bridge.py:1118-1230 — `load_refined_mtz` implementation
- dbex/nanobrag_bridge.py:856-1116 — `build_structure_factor_grid` implementation
- dbex/nanobrag_bridge.py:1230+ — `simulate_forward_once` signature and docstring
- dbex/io/writer.py:196-200 — HDF5 telemetry serialization
- docs/findings.md SCALE-003, SCALE-004 — Refined MTZ ingestion requirements
