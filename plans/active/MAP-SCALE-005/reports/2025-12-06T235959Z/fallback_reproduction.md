# Reality Check (A1): CLI Refined MTZ Fallback Behavior

## Summary

Reproduced CLI behavior when `--refined-mtz` flag is provided with both missing and valid file paths. The current implementation **already fails fast** when a provided `--refined-mtz` path does not exist, which aligns with the desired spec behavior. This discovery indicates that Phase B may not require significant implementation changes — the enforcement is already present.

## Experiment Setup

### Command (Missing Refined MTZ)
```bash
python -m dbex.refine_one --backend nanobrag \
  -e tests/fixtures/golden_data/simple_cubic/refined.expt \
  -r tests/fixtures/golden_data/simple_cubic/refined.refl \
  -i 0 -o /tmp/test_fallback.h5 \
  -m 747_mask.pkl \
  -z tests/fixtures/golden_data/simple_cubic/refined_structure_factors.mtz \
  -c "F(+),SIGF(+),F(-),SIGF(-)" \
  --refined-mtz /nonexistent/path.mtz \
  --torch-config tests/fixtures/golden_data/simple_cubic/config_torch.json \
  --sigma-rdout 3.0 --sigma-floor 1.0
```

### Observed Behavior

**Exit Status:** Non-zero (RuntimeError raised)

**Error Message:**
```
RuntimeError: Failed to load refined structure factors from --refined-mtz '/nonexistent/path.mtz':
Refined MTZ not found: /nonexistent/path.mtz. Expected DiffBragg-refined structure factors for parity testing.
When --refined-mtz is provided, refined structure factors MUST be consumed.
Ensure the MTZ file exists and contains valid F(+)/F(-) or F/SIGF columns.
```

**Failure Location:** `dbex/refine_one.py:382-389` (run_nanobrag_backend)

**Stack Trace:**
- `load_refined_mtz()` raises `FileNotFoundError` at `dbex/nanobrag_bridge.py:1155`
- Caught and re-raised as `RuntimeError` with actionable message at `dbex/refine_one.py:389`

### Baseline Comparison (No --refined-mtz Flag)

**Command:**
```bash
python -m dbex.refine_one --backend nanobrag \
  -e tests/fixtures/golden_data/simple_cubic/refined.expt \
  -r tests/fixtures/golden_data/simple_cubic/refined.refl \
  -i 0 -o /tmp/test_no_refined.h5 \
  -m 747_mask.pkl \
  -z tests/fixtures/golden_data/simple_cubic/refined_structure_factors.mtz \
  -c "F(+),SIGF(+),F(-),SIGF(-)" \
  --torch-config tests/fixtures/golden_data/simple_cubic/config_torch.json \
  --sigma-rdout 3.0 --sigma-floor 1.0
```

**Exit Status:** Success (zero-iteration simulation completed despite OOM warning)

**Console Output Excerpt:**
```
[nanobrag backend] Using raw structure factors from tests/fixtures/golden_data/simple_cubic/refined_structure_factors.mtz
...
[nanobrag backend] JobContext built: sigma_provenance=cli_override, hkl_source=raw, spot_scale=3.185e+17
```

**HDF5 Telemetry (`/torch_diagnostics`):**
```
hkl_source: raw
hkl_path: tests/fixtures/golden_data/simple_cubic/refined_structure_factors.mtz
```

## Key Findings

### 1. Enforcement Already Implemented (CRITICAL)

The CLI **already enforces** the fail-fast policy when `--refined-mtz` is provided but cannot be consumed:

- **Code Path:** `dbex/refine_one.py:382` wraps `load_refined_mtz()` in a try-except block
- **Behavior:** `FileNotFoundError` from `load_refined_mtz` is caught and re-raised as `RuntimeError` with clear user-facing message
- **Compliance:** The error message explicitly states: "When --refined-mtz is provided, refined structure factors MUST be consumed."

### 2. Silent Fallback Does Not Occur

Contrary to the initial task description (which anticipated silent fallback), the implementation does NOT silently fall back to raw MTZ when `--refined-mtz` load fails. Instead:

- The run terminates immediately with a clear error
- No HDF5 output is written for the failed case
- The error message directs users to verify file existence and column format

### 3. Telemetry Downgrade Condition

When `--refined-mtz` is **NOT provided**, the CLI correctly:

- Uses the `-z/--mtzFile` path (raw MTZ)
- Records `hkl_source="raw"` in telemetry
- Emits clear console log: `"Using raw structure factors from <path>"`

### 4. ARCH-CONTRACT Alignment

**ARCH-CONTRACT-CALIBRATION-001** states:
> CLI backend SHALL populate hkl_source based on --refined-mtz vs --mtzFile precedence; currently falls back silently when refined MTZ load fails.

This contract description is **outdated**. The current implementation at `dbex/refine_one.py:382-389` does NOT fall back silently — it raises an exception.

## Implications for Phase B

### Scope Reduction

The original initiative assumed silent fallback was occurring and needed to be replaced with fail-fast enforcement. This assumption is **incorrect**. The enforcement is already implemented.

### Remaining Work (If Any)

Phase B should focus on:

1. **Validation Coverage:** Add regression test to ensure `--refined-mtz /nonexistent/path.mtz` continues to fail fast
2. **Documentation Sync:** Update ARCH-CONTRACT-CALIBRATION-001 to reflect actual implementation (fail-fast, not silent fallback)
3. **Telemetry Enforcement Test Extension:** Extend SCALE-007 enforcement from test harness to CLI layer (may already be satisfied by existing error path)
4. **Error Message Quality Audit:** Verify the current error message meets user-facing quality standards (currently quite good)

### Alternative: Initiative Closure

If the spec already defines fail-fast as normative and the implementation complies, this initiative could be **closed as already satisfied**, pending:

- Confirmation that SCALE-007 intent is met by the existing error path
- Regression test addition to prevent future silent-fallback regressions
- Documentation updates to correct outdated ARCH-CONTRACT description

## Artifacts

- **Missing MTZ stdout:** `plans/active/MAP-SCALE-005/reports/2025-12-06T235959Z/cli_fallback_stdout.log`
- **No refined MTZ stdout:** `plans/active/MAP-SCALE-005/reports/2025-12-06T235959Z/cli_no_refined_mtz_stdout.log`
- **HDF5 baseline:** `/tmp/test_no_refined.h5` (temporary, telemetry inspected via h5py)

## Next Steps

Proceed to A2 (Spec Citations) to confirm whether the current fail-fast implementation satisfies normative requirements, or whether additional telemetry enforcement is required per SCALE-007.
