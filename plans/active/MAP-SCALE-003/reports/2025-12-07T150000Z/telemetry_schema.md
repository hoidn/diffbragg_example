# Telemetry Metadata Schema — Structure Factor Provenance

## Summary
Definition of structure-factor telemetry metadata schema with 4 required fields, fallback behavior, and contract enforcement per ARCH-CONTRACT-WRITER-001 and SCALE-007.

## Schema Definition

### Required Fields

**Type**: Python dict with 4 mandatory string-keyed entries

```python
hkl_telemetry = {
    "hkl_source": str,        # "refined" | "raw" | "unknown"
    "hkl_n_reflections": int, # Reflection count from HKL grid
    "hkl_mean_amplitude": float, # Mean |F| amplitude (diagnostics)
    "hkl_path": str,          # Absolute path to MTZ file (or empty string)
}
```

### Field Specifications

#### 1. `hkl_source` (str, required)
**Purpose**: Distinguishes refined MTZ vs raw amplitudes per SCALE-007

**Allowed values**:
- `"refined"`: Structure factors loaded from DiffBragg-refined MTZ (e.g., `--refined-mtz` CLI arg)
- `"raw"`: Structure factors loaded from raw MTZ (e.g., `--mtzFile` fallback)
- `"unknown"`: Provenance indeterminate (legacy/test compatibility; should not occur in production)

**Production contract** (SCALE-007):
- When `--refined-mtz` CLI arg is provided and valid → `hkl_source = "refined"`
- When `--refined-mtz` is absent/invalid and falls back to `--mtzFile` → `hkl_source = "raw"`
- Silent fallback from refined to raw WITHOUT changing `hkl_source` violates spec-db-tracing.md §2

**Enforcement**: Phase C deliverable (MAP-SCALE-005) must add assertion:
```python
if args.refined_mtz is not None and hkl_source == "raw":
    raise ValueError("--refined-mtz provided but hkl_source='raw'; silent fallback detected")
```

---

#### 2. `hkl_n_reflections` (int, required)
**Purpose**: Record reflection count for diagnostics and debugging

**Computation**: `len(hkl_indices)` after MTZ loading

**Typical ranges**:
- Refined MTZ (DiffBragg output): ~1000-5000 reflections
- Raw MTZ (indexing output): ~5000-50000 reflections

**Validation**: Must be > 0 (zero reflections indicates loading failure)

---

#### 3. `hkl_mean_amplitude` (float, required)
**Purpose**: Mean structure factor amplitude for diagnostics

**Computation**: `float(np.mean(np.abs(hkl_amplitudes)))` after MTZ loading

**Typical ranges**:
- Refined MTZ (DiffBragg output): ~1e-6 to 1e-3 (refined Fopt)
- Raw MTZ (indexing output): ~10 to 1000 (raw amplitudes)

**Diagnostics value**:
- Order-of-magnitude check: refined amplitudes are ~94k× smaller than raw (per SCALE-003/004 findings)
- Large mean_amplitude with `hkl_source="refined"` indicates loading error

**Validation**: Must be > 0 (zero mean indicates all-zero amplitudes)

---

#### 4. `hkl_path` (str, required)
**Purpose**: Absolute path to MTZ file for provenance tracking

**Allowed values**:
- Absolute filesystem path (e.g., `/path/to/refined_structure_factors.mtz`)
- Empty string `""` when MTZ path is unavailable (legacy/test compatibility)

**Production contract**:
- When `--refined-mtz` provided → `hkl_path = os.path.abspath(args.refined_mtz)`
- When `--mtzFile` fallback → `hkl_path = os.path.abspath(args.mtzFile)`
- Empty path should not occur in production CLI runs (only in unit tests with synthetic data)

**HDF5 serialization**: Stored as string attr (empty string if unavailable)

---

## Fallback Behavior

### Scenario 1: Refined MTZ Requested but Missing/Invalid
**Trigger**: `--refined-mtz` CLI arg provided, but file does not exist or is corrupt

**Behavior**:
```python
try:
    hkl_indices, hkl_amplitudes = load_refined_mtz(args.refined_mtz)
    hkl_source = "refined"
    hkl_path = args.refined_mtz
except (FileNotFoundError, ValueError) as e:
    logger.warning(f"Refined MTZ load failed: {e}. Falling back to raw MTZ.")
    hkl_indices = dl.F.indices()
    hkl_amplitudes = dl.F.data()
    hkl_source = "raw"
    hkl_path = args.mtzFile
```

**Telemetry contract**: `hkl_source` MUST reflect actual data source (refined → raw transition is visible)

**SCALE-007 enforcement** (Phase C): If fallback is disallowed per spec, raise error instead of silent fallback

---

### Scenario 2: No Refined MTZ Provided (Raw MTZ Default)
**Trigger**: `--refined-mtz` CLI arg is `None` (not provided by user)

**Behavior**:
```python
hkl_indices = dl.F.indices()
hkl_amplitudes = dl.F.data()
hkl_source = "raw"
hkl_path = args.mtzFile
```

**Telemetry contract**: Straightforward; no fallback logic required

---

### Scenario 3: Test/Mock Context (No MTZ Path Available)
**Trigger**: Unit tests with synthetic HKL data (no actual MTZ file)

**Behavior**:
```python
hkl_indices = np.array([[1,0,0], [0,1,0], ...])  # Synthetic
hkl_amplitudes = np.array([100.0, 150.0, ...])
hkl_source = "raw"  # or "unknown" if provenance unclear
hkl_path = ""  # Empty string for tests
```

**Telemetry contract**: `hkl_path = ""` is acceptable for tests; production runs should always have a valid path

---

## HDF5 Serialization Contract

**Writer implementation** (dbex/io/writer.py:196-200):
```python
diag.attrs["hkl_source"] = hkl_telemetry["hkl_source"]
diag.attrs["hkl_n_reflections"] = int(hkl_telemetry["hkl_n_reflections"])
diag.attrs["hkl_mean_amplitude"] = float(hkl_telemetry["hkl_mean_amplitude"])
diag.attrs["hkl_path"] = str(hkl_telemetry["hkl_path"])
```

**Storage format**:
- All 4 fields stored as HDF5 attributes (not datasets)
- `hkl_source`: String attribute
- `hkl_n_reflections`: Integer attribute (h5py coerces to int64)
- `hkl_mean_amplitude`: Float attribute (h5py coerces to float64)
- `hkl_path`: String attribute

**Access pattern** (tests/analysis):
```python
import h5py
with h5py.File("output.h5", "r") as h:
    hkl_source = h["torch_diagnostics"].attrs["hkl_source"]
    n_refl = h["torch_diagnostics"].attrs["hkl_n_reflections"]
    mean_amp = h["torch_diagnostics"].attrs["hkl_mean_amplitude"]
    mtz_path = h["torch_diagnostics"].attrs["hkl_path"]
```

---

## Validation Rules

### Writer Contract Enforcement
**Location**: `dbex/io/writer.py::write_torch_outputs`

**Validations**:
1. `hkl_telemetry` parameter is non-None (required)
2. All 4 keys present in dict
3. Types match schema (str/int/float)
4. `hkl_n_reflections > 0`
5. `hkl_mean_amplitude > 0`

**Error behavior**: Raise `ValueError` with descriptive message if validation fails

---

### CLI Contract Enforcement (Phase C, MAP-SCALE-005)
**Location**: `dbex/refine_one.py::run_nanobrag_backend`

**Validations**:
1. If `--refined-mtz` provided and telemetry shows `hkl_source="raw"`, raise error (silent fallback detected)
2. If `hkl_n_reflections == 0`, abort (MTZ loading failed)
3. If `hkl_path == ""` in production CLI run, warn (unexpected missing provenance)

---

## Rationale

### Why 4 fields?
- **`hkl_source`**: Core provenance tracking per SCALE-007 (prevents silent fallback bugs)
- **`hkl_n_reflections`**: Debugging aid (low count → incomplete MTZ, high count → raw vs refined indicator)
- **`hkl_mean_amplitude`**: Order-of-magnitude sanity check (refined ~1e-6, raw ~100)
- **`hkl_path`**: Reproducibility (artifact links back to input MTZ file)

### Why not include grid metadata?
- Grid shape/bounds/coverage are implementation details (vary by HKL range, halo padding)
- Telemetry focuses on provenance + quality indicators (source, count, mean amplitude)
- Grid metadata already available in `hkl_metadata` dict from `build_structure_factor_grid`

### Why dict (not dataclass)?
- Matches existing telemetry patterns in codebase (`calibration` dict, `diagnostics` dict)
- H5py attrs serialization works directly with dicts (no conversion shim needed)
- Extensible: future fields can be added without signature changes

---

## References

- docs/spec-db-tracing.md:85-120 — Torch diagnostics artifact expectations (provenance requirements)
- docs/findings.md SCALE-007 — Silent fallback from refined to raw MTZ violates spec
- dbex/io/writer.py:196-200 — HDF5 telemetry serialization implementation
- dbex/nanobrag_bridge.py:1230+ — `simulate_forward_once` diagnostics emission
- ARCH-CONTRACT-WRITER-001 — Writer diagnostics contract (HDF5 schema stability)
