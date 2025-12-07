# Guard Design (A3): Refined MTZ Enforcement Architecture

## Summary

The CLI **already implements** a comprehensive guard for refined MTZ enforcement at `dbex/refine_one.py:375-393`. This document analyzes the existing design, defines failure surfaces, and assesses error message quality against user-facing standards.

## Existing Implementation

### Guard Location

**File:** `dbex/refine_one.py`
**Function:** `run_nanobrag_backend(args, DL, devid)`
**Lines:** 375-393

### Control Flow

```python
# Initialize telemetry trackers
hkl_source = "raw"  # Default assumption
hkl_path = None

if args.refined_mtz is not None:
    try:
        # Attempt to load refined MTZ
        hkl_indices, hkl_amplitudes = load_refined_mtz(args.refined_mtz, column="F")
        hkl_source = "refined"
        hkl_path = args.refined_mtz
        # Success path: log consumption
        print(f"[nanobrag backend] Using refined structure factors from {args.refined_mtz}")
    except (FileNotFoundError, ValueError, ImportError) as e:
        # FAIL-FAST: Re-raise with actionable message
        raise RuntimeError(
            f"Failed to load refined structure factors from --refined-mtz '{args.refined_mtz}': {e}\n"
            f"When --refined-mtz is provided, refined structure factors MUST be consumed.\n"
            f"Ensure the MTZ file exists and contains valid F(+)/F(-) or F/SIGF columns."
        ) from e

# Fallback: use raw MTZ only if --refined-mtz was NOT provided
if hkl_indices is None:
    hkl_indices = DL.F.indices()
    hkl_amplitudes = DL.F.data()
    hkl_source = "raw"
    hkl_path = args.mtzFile  # Tracked from -z flag
```

### Delegation to Helper

The guard delegates the actual load operation to `load_refined_mtz()` at `dbex/nanobrag_bridge.py:1118-1210`, which handles:

- **File existence check** (raises `FileNotFoundError` at line 1155)
- **Import availability** (raises `ImportError` at line 1163 if iotbx.mtz missing)
- **MTZ parsing** (raises `ValueError` at line 1171 if MTZ corrupted)
- **Column validation** (raises `ValueError` at line 1188 if specified column not found)
- **Data validation** (raises `ValueError` at line 1205 if indices/amplitudes are empty or mismatched)

## Failure Surface Taxonomy

### Surface 1: File Not Found

**Trigger:** `--refined-mtz /path/to/missing.mtz` where path does not exist

**Exception Chain:**
1. `load_refined_mtz` raises `FileNotFoundError` at `nanobrag_bridge.py:1155`
2. Caught at `refine_one.py:387`
3. Re-raised as `RuntimeError` at `refine_one.py:389-393`

**Error Message:**
```
RuntimeError: Failed to load refined structure factors from --refined-mtz '/path/to/missing.mtz':
Refined MTZ not found: /path/to/missing.mtz. Expected DiffBragg-refined structure factors for parity testing.
When --refined-mtz is provided, refined structure factors MUST be consumed.
Ensure the MTZ file exists and contains valid F(+)/F(-) or F/SIGF columns.
```

**User Action Required:** Verify file path, check for typos, confirm file exists on filesystem

**Quality Assessment:** ✅ **GOOD**
- Includes full file path for easy copy-paste verification
- Clear normative statement ("MUST be consumed")
- Actionable guidance (check existence, column format)

### Surface 2: MTZ Parse Failure

**Trigger:** `--refined-mtz /path/to/corrupted.mtz` where file exists but is invalid

**Exception Chain:**
1. `iotbx_mtz.object()` raises exception at `nanobrag_bridge.py:1169`
2. Caught and re-raised as `ValueError` at `nanobrag_bridge.py:1171-1173`
3. Caught at `refine_one.py:387`
4. Re-raised as `RuntimeError` at `refine_one.py:389-393`

**Error Message:**
```
RuntimeError: Failed to load refined structure factors from --refined-mtz '/path/to/corrupted.mtz':
Failed to parse MTZ file /path/to/corrupted.mtz. Expected valid DiffBragg-refined MTZ. Error: <parse_error>
When --refined-mtz is provided, refined structure factors MUST be consumed.
Ensure the MTZ file exists and contains valid F(+)/F(-) or F/SIGF columns.
```

**User Action Required:** Regenerate MTZ, verify file integrity, check for partial download

**Quality Assessment:** ✅ **GOOD**
- Includes underlying parse error for debugging
- Indicates expected format (DiffBragg-refined)

### Surface 3: Column Not Found

**Trigger:** `--refined-mtz /path/to/valid.mtz` but MTZ lacks expected column (e.g., "F" column missing)

**Exception Chain:**
1. Column search fails at `nanobrag_bridge.py:1188`
2. `ValueError` raised with column diagnostic
3. Caught at `refine_one.py:387`
4. Re-raised as `RuntimeError` at `refine_one.py:389-393`

**Error Message:**
```
RuntimeError: Failed to load refined structure factors from --refined-mtz '/path/to/valid.mtz':
MTZ file /path/to/valid.mtz does not contain column 'F'. Available columns: [...]
When --refined-mtz is provided, refined structure factors MUST be consumed.
Ensure the MTZ file exists and contains valid F(+)/F(-) or F/SIGF columns.
```

**User Action Required:** Verify MTZ column names, check if DiffBragg output format changed

**Quality Assessment:** ✅ **EXCELLENT**
- Lists available columns for easy diagnosis
- Matches error message guidance ("valid F(+)/F(-) or F/SIGF columns")

### Surface 4: Empty Indices/Amplitudes

**Trigger:** MTZ parses successfully but contains no data (edge case)

**Exception Chain:**
1. Data validation fails at `nanobrag_bridge.py:1205`
2. `ValueError` raised
3. Caught at `refine_one.py:387`
4. Re-raised as `RuntimeError` at `refine_one.py:389-393`

**Error Message:**
```
RuntimeError: Failed to load refined structure factors from --refined-mtz '/path/to/empty.mtz':
Refined MTZ yielded empty indices or amplitudes: n_indices=0, n_amplitudes=0
When --refined-mtz is provided, refined structure factors MUST be consumed.
Ensure the MTZ file exists and contains valid F(+)/F(-) or F/SIGF columns.
```

**User Action Required:** Regenerate MTZ, check refinement logs, verify DiffBragg completion

**Quality Assessment:** ✅ **GOOD**
- Diagnostic includes counts for debugging

### Surface 5: iotbx.mtz Import Failure

**Trigger:** `--refined-mtz` provided but cctbx/iotbx not available in environment

**Exception Chain:**
1. `import iotbx.mtz` fails at `nanobrag_bridge.py:1161`
2. `ImportError` raised at `nanobrag_bridge.py:1163-1165`
3. Caught at `refine_one.py:387`
4. Re-raised as `RuntimeError` at `refine_one.py:389-393`

**Error Message:**
```
RuntimeError: Failed to load refined structure factors from --refined-mtz '/path/to/file.mtz':
iotbx.mtz is required to read MTZ files. Import error: <import_error>
When --refined-mtz is provided, refined structure factors MUST be consumed.
Ensure the MTZ file exists and contains valid F(+)/F(-) or F/SIGF columns.
```

**User Action Required:** Verify cctbx installation, check environment activation

**Quality Assessment:** ✅ **GOOD**
- Clear dependency statement

### Surface 6: Telemetry Downgrade (PREVENTED by Design)

**Hypothetical Trigger:** Code path that allows `hkl_source="raw"` after `--refined-mtz` is provided

**Current Implementation:** ✅ **PREVENTED**
- The `hkl_source` variable is initialized to `"raw"` at line 378
- It is only set to `"refined"` at line 383 (inside the try block, after successful load)
- If the `except` block is entered (lines 387-393), a `RuntimeError` is raised **immediately**
- Execution never proceeds to simulation or telemetry writing
- Therefore, telemetry downgrade is **architecturally impossible** with the current guard design

**Quality Assessment:** ✅ **EXCELLENT**
- Fail-fast design prevents all silent-fallback scenarios
- Telemetry consistency is guaranteed by exception propagation

## Guard Positioning Analysis

### Execution Timeline

1. **Argument parsing** (`main()` at line 782)
2. **DataLoad construction** (loads raw MTZ via `-z` flag)
3. **Backend routing** (`run_nanobrag_backend()` at line 789)
4. **Sigma resolution** (`_resolve_sigma_readout()` at line 317)
5. **🛡️ REFINED MTZ GUARD 🛡️** (lines 375-393) ← **Current location**
6. **HKL grid construction** (lines 396-410)
7. **Simulation context building** (lines 412+)
8. **Zero-iteration simulation** or **Stage A refinement**
9. **Telemetry writing** (HDF5 output)

### Guard Location Assessment

**Placement:** ✅ **OPTIMAL**

- **After sigma resolution:** Ensures all required calibration inputs are validated first (per spec-db-workflow.md:46 precedent)
- **Before simulation:** Prevents wasted GPU allocation or computation on doomed runs
- **Before telemetry:** Guarantees no HDF5 artifact is written for failed runs (clean failure)
- **Within backend function:** Keeps nanobrag-specific enforcement separate from shared CLI logic

**Alternative Locations Considered:**

1. **In argument parser (argparse validation):** ❌ Too early — file existence checks should not block `--help` or CLI exploration
2. **In `load_refined_mtz` only:** ❌ Too deep — error context loss, harder to provide actionable CLI-level message
3. **After simulation:** ❌ Too late — wastes computation, allows partial artifacts

### Exception Handling Design

**Pattern:** Try-except with re-raise

**Rationale:**
- `load_refined_mtz` provides **domain-specific** error diagnostics (file, column, data validation)
- `run_nanobrag_backend` adds **CLI-context** wrapper (flag name, normative policy statement)
- `from e` preserves **exception chain** for debugging

**Quality Assessment:** ✅ **EXCELLENT**
- Layered error handling preserves all diagnostic information
- User sees both "what failed" (file/column) and "why it matters" (MUST be consumed)
- Developers get full traceback for debugging

## Error Message Template (Already Implemented)

### Current Template

```python
raise RuntimeError(
    f"Failed to load refined structure factors from --refined-mtz '{args.refined_mtz}': {e}\n"
    f"When --refined-mtz is provided, refined structure factors MUST be consumed.\n"
    f"Ensure the MTZ file exists and contains valid F(+)/F(-) or F/SIGF columns."
) from e
```

### Template Components

1. **Context:** "Failed to load refined structure factors from --refined-mtz '<path>'"
   - ✅ Identifies the operation that failed
   - ✅ Quotes the user-provided path verbatim for easy verification

2. **Diagnostic:** ": {e}"
   - ✅ Includes underlying exception message (FileNotFoundError, ValueError, etc.)
   - ✅ Preserves diagnostic detail from `load_refined_mtz`

3. **Policy Statement:** "When --refined-mtz is provided, refined structure factors MUST be consumed."
   - ✅ Normative language ("MUST") signals spec requirement
   - ✅ Explains *why* the error is fatal (not optional)

4. **Actionable Guidance:** "Ensure the MTZ file exists and contains valid F(+)/F(-) or F/SIGF columns."
   - ✅ Directs user to check file existence (Surface 1)
   - ✅ Directs user to verify column format (Surface 3)
   - ⚠️ Could be improved: "valid F(+)/F(-) or F/SIGF columns" is slightly generic; specific column name ("F") is buried in diagnostic

### Potential Enhancements (OPTIONAL for Phase B)

If Phase B proceeds to implementation (unlikely given A1/A2 findings), consider:

1. **More specific column guidance:**
   ```python
   f"Ensure the MTZ file exists and contains a '{column}' column with F(+)/F(-) or F/SIGF data."
   ```

2. **Provenance hint:**
   ```python
   f"Expected DiffBragg-refined MTZ (e.g., refined_structure_factors.mtz from Stage A/B refinement)."
   ```

3. **Fallback suggestion (CONTROVERSIAL — may encourage wrong behavior):**
   ```python
   f"To use raw structure factors, omit --refined-mtz and use -z/--mtzFile only."
   ```
   **Risk:** Could imply that raw MTZ is equivalent to refined MTZ (it is NOT per SCALE-003)

**Current Assessment:** ✅ **No changes needed**
- Existing message is clear, actionable, and spec-aligned
- Potential enhancements are marginal improvements

## Design Strengths

1. **Fail-fast enforcement:** Errors before simulation (no wasted computation)
2. **Layered diagnostics:** Domain-specific (load_refined_mtz) + CLI-context (run_nanobrag_backend)
3. **Telemetry consistency:** Impossible to produce `hkl_source="raw"` telemetry when `--refined-mtz` provided
4. **Exception chaining:** Full traceback preserved via `from e`
5. **Clear normative policy:** "MUST be consumed" aligns with spec language
6. **Actionable guidance:** Covers common failure modes (file existence, column format)

## Design Weaknesses (None Identified)

All analyzed failure surfaces are handled with appropriate error messages. No silent-fallback paths exist.

## Comparison to Other CLI Enforcement

### sigma_readout Enforcement (spec-db-workflow.md:46 precedent)

**Location:** `dbex/refine_one.py:168` (`_resolve_sigma_readout`)

**Pattern:**
```python
if sigma_readout_array is None:
    raise ValueError(
        f"nanobrag backend requires a positive sigma_readout source (...). "
        f"Per spec-db-core.md:32-68 and spec-db-workflow.md:26-31 the CLI MUST refuse to run ..."
    )
```

**Similarities to Refined MTZ Guard:**
- ✅ Fail-fast before simulation
- ✅ Clear normative language ("MUST refuse to run")
- ✅ References spec sections for justification
- ✅ Actionable guidance (provides alternative flags)

**Differences:**
- sigma_readout uses `ValueError` (single-layer)
- refined MTZ uses `RuntimeError` wrapping (two-layer for richer context)

**Consistency Assessment:** ✅ **ALIGNED**
- Both follow fail-fast-before-simulation pattern
- Both use clear normative language
- Message structure is comparable

## Recommendations for Phase B

### Option A: Minimal Scope (Recommended)

1. **Add regression test** to `tests/dbex/test_cli_enforcement.py` (new module):
   ```python
   def test_refined_mtz_missing_file_fails_fast():
       """Verify CLI fails when --refined-mtz points to nonexistent file (SCALE-007)."""
       with pytest.raises(RuntimeError, match="When --refined-mtz is provided"):
           # Invoke refine_one with --refined-mtz /nonexistent/path.mtz
   ```

2. **Update ARCH-CONTRACT-CALIBRATION-001** to reflect actual implementation:
   ```diff
   - currently falls back silently when refined MTZ load fails.
   + currently fails fast with RuntimeError when refined MTZ load fails per spec-db-workflow.md:47.
   ```

3. **Document guard design** in architecture docs (reuse this artifact)

### Option B: Close Initiative (Alternative)

If stakeholders agree:
- Existing implementation satisfies all SCALE-007 requirements
- Error message quality is production-ready
- Regression test can be added via separate test harness initiative (DB-AT-SUITE-CARE-001)

Then close MAP-SCALE-005 as "already satisfied" and document findings in `docs/findings.md`.

## Artifacts

- Guard implementation: `dbex/refine_one.py:375-393`
- Helper implementation: `dbex/nanobrag_bridge.py:1118-1210`
- Failure surface reproduction: `plans/active/MAP-SCALE-005/reports/2025-12-06T235959Z/fallback_reproduction.md`
- Normative citations: `plans/active/MAP-SCALE-005/reports/2025-12-06T235959Z/spec_citations.md`
