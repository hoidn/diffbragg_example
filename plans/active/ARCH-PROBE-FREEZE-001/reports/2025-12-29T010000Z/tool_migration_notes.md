# Sigma Embedding Tool Migration

## Summary

Successfully migrated `plans/active/PHYSICS-LOSS-001/bin/embed_sigma_external_lookup.py` to the canonical owner module `dbex.tools.embed_sigma_external_lookup` per ARCH-PROBE-FREEZE-001 (Probe Freeze & Logging Consolidation).

## Architecture Context

- **Initiative**: ARCH-PROBE-FREEZE-001 — Probe Freeze & Logging Consolidation
- **Finding**: PHYSICS-LOSS-001, PHYSICS-LOSS-005 — sigma provenance + variance telemetry belong to owner modules
- **Policy**: diagnostic_script_policy (prompts/supervisor.md:272-309)
- **Contract**: spec-db-core.md:32-68 — sigma provenance contract

## Changes

### 1. New Canonical Owner Module

**File**: `dbex/tools/embed_sigma_external_lookup.py`

- Migrated all functionality from plan-local script
- Exposed reusable `embed_sigma_external_lookup()` function for programmatic use
- CLI entry point via `python -m dbex.tools.embed_sigma_external_lookup`
- Preserved all CLI flags and backwards compatibility

**Key Functions**:
- `main(args=None)` — CLI entry point
- `embed_sigma_external_lookup(...)` — Core embedding function, importable by tests/fixtures
- `_parse_args(args=None)` — Argument parsing with testability
- `_build_image_tiles()` — ImageDouble/flex conversion
- `_write_manifest()` — Reproducibility metadata with SHA256 hashes

### 2. Compatibility Shim

**File**: `plans/active/PHYSICS-LOSS-001/bin/embed_sigma_external_lookup.py`

Reduced to 19 lines (from 291 lines):
```python
#!/usr/bin/env python3
"""Legacy compatibility shim for sigma metadata embedding."""

from __future__ import annotations

if __name__ == "__main__":
    from dbex.tools.embed_sigma_external_lookup import main
    main()
```

### 3. Documentation Updates

**Files Updated**:
- `docs/TESTING_GUIDE.md` — Updated command examples and added legacy alias note
- `sp.proc/README.md` — Updated regeneration workflow command
- `tests/sp_proc/test_sigma_metadata_fixture.py` — Updated skip message
- `tests/conftest.py` — Updated sigma fixture error message
- `tests/dbex/test_mapping_consistency.py` — Updated metadata error message
- `tests/dbex/test_artifact_parity.py` — Updated metadata error message
- `tests/dbex/test_torch_refine_smoke.py` — Updated metadata error message

## New CLI Usage

**Canonical Command**:
```bash
python -m dbex.tools.embed_sigma_external_lookup \
  --expt refGeom.expt \
  --output sp.proc/idx-0000_sigma_metadata.expt \
  --expt-idx 0 \
  --sigma-value 3.0 \
  --report <artifact_dir>/sigma_metadata.json \
  --manifest sp.proc/sigma_metadata_manifest.json
```

**Legacy Alias** (still works):
```bash
python plans/active/PHYSICS-LOSS-001/bin/embed_sigma_external_lookup.py [args]
```

## CLI Help Output

```
usage: embed_sigma_external_lookup.py [-h] --expt EXPT --output OUTPUT
                                      [--expt-idx EXPT_IDX]
                                      (--sigma-map SIGMA_MAP | --sigma-value SIGMA_VALUE)
                                      [--report REPORT] [--manifest MANIFEST]
                                      [--lookup-key LOOKUP_KEY]

Clone a DIALS ExperimentList and inject calibrated sigma_readout tiles into
imageset.external_lookup so downstream runs can source variance metadata
without CLI overrides.

optional arguments:
  -h, --help            show this help message and exit
  --expt EXPT           Input ExperimentList (.expt) to read.
  --output OUTPUT       Destination ExperimentList path (.expt) that will
                        include the sigma tiles.
  --expt-idx EXPT_IDX   Experiment index to modify (default: 0).
  --sigma-map SIGMA_MAP
                        Path to calibrated sigma tensor (.npy/.npz/pkl)
                        aligned to detector panels.
  --sigma-value SIGMA_VALUE
                        Uniform sigma value (ADU) broadcast across all panels.
  --report REPORT       Optional JSON path for provenance output. Defaults to
                        <output>.sigma_metadata.json when omitted.
  --manifest MANIFEST   Optional manifest JSON path recording generator
                        command metadata and SHA256 hashes for the output
                        .expt, .sigma_tiles.pkl, and provenance JSON.
  --lookup-key LOOKUP_KEY
                        External lookup attribute name to populate (default:
                        pedestal). Most detectors expose pedestal/dark tiles;
                        Stage A smokes look under this key.
```

## Validation

### Test Results

**Sigma Metadata Fixture Test** (`tests/sp_proc/test_sigma_metadata_fixture.py`):
- Status: ✅ PASSED (1 passed in 1.06s)
- Validates manifest SHA256 hashes, external_lookup loading, and provenance metadata

**Stage A Metadata Smoke Test** (`test_torch_refine_smoke.py::test_stage_a_expansion`):
- Status: ⏭️ SKIPPED (missing small detector metadata fixtures)
- Note: Per input.md, "do not rewrite or regenerate `sp.proc/idx-0000_sigma_metadata.*` in-place"
- The tool is functional; fixture regeneration is out of scope for this loop

## Architectural Benefits

1. **Single Owner**: Embedding logic now lives in `dbex.tools`, not scattered across plan scripts
2. **Importable**: Tests and fixtures can import `embed_sigma_external_lookup()` function directly
3. **Discoverable**: `python -m dbex.tools.embed_sigma_external_lookup` is the standard Python module CLI pattern
4. **Documented**: Module docstring links to ARCH-PROBE-FREEZE-001 and migration reference
5. **Backwards Compatible**: Legacy plan path still works via thin shim
6. **Testable**: `_parse_args(args=None)` accepts argument list for testing

## Lines of Code Reduction

- **Before**: 291 lines in plan-local script
- **After**:
  - 385 lines in canonical owner module (includes docstrings and reusable helpers)
  - 19 lines in compatibility shim
- **Net Impact**: Consolidated shadow pipeline into production tree; plan script no longer duplicates implementation semantics

## Follow-up Items (Out of Scope)

- Regenerate small detector metadata fixtures if needed for Stage A metadata smokes
- Consider adding enforcement test under `tests/architecture/` to guard against future re-duplication of embedding logic
- Audit other plan-local scripts for similar migration opportunities (per Problems Ledger: crop_sigma_map_to_window.py, etc.)

## References

- Initiative: `plans/active/ARCH-PROBE-FREEZE-001/implementation.md`
- Findings: PHYSICS-LOSS-001, PHYSICS-LOSS-005 (`docs/findings.md`)
- Spec: `docs/spec-db-core.md:32-68` (sigma provenance contract)
- Policy: `prompts/supervisor.md:272-309` (diagnostic_script_policy)
