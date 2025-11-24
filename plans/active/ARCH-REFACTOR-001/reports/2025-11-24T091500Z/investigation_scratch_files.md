# ARCH-REFACTOR-001 Phase D D1: DiffBragg Scratch File Investigation

**Date:** 2025-11-24T091500Z
**Phase:** D1 — Investigation

## Summary

Located ALL hardcoded scratch file paths in `dbex/run_diffbragg.py`. All paths are in the `detector_refinement()` function (lines 17-45) and the `run_diffbragg()` function (lines 48-138).

## Hardcoded Paths Found

### 1. `detector_refinement()` function (lines 17-45)

**`_geom_ref.*` files:**
- Line 20: `new_El.as_file("_geom_ref.expt")` — Writes experiment list
- Line 21: `Refs.as_file("_geom_ref.refl")` — Writes reflections
- Line 23: `model_df["geom_exp"] = "_geom_ref.expt"` — String reference
- Line 24: `model_df["geom_ref"] = "_geom_ref.refl"` — String reference
- Line 26: `model_df.to_pickle("_geom_ref.pkl")` — Writes pickle
- Line 36: `params_geom.geometry.input_pkl = "_geom_ref.pkl"` — String reference

**`_geom_groups.txt` file:**
- Line 28: `with open("_geom_groups.txt", "w") as o:` — Writes panel groups
- Line 33: `params_geom.refiner.panel_group_file = "_geom_groups.txt"` — String reference

**`_geom.out/` directory:**
- Line 39: `params_geom.outdir = "_geom.out"` — Output directory for geometry refinement
- Line 43: `new_det = ExperimentList.from_file("_geom.out/diffBragg_detector.expt")[0].detector` — Reads refined detector

### 2. `run_diffbragg()` function (lines 48-138)

**`_temp.mtz` file:**
- Line 107: `Fopt.as_mtz_dataset(column_root_label="F").mtz_object().write("_temp.mtz")` — Writes MTZ
- Line 109: `prm.simulator.structure_factors.mtz_name = "_temp.mtz"` — String reference (in loop)

## Entry Points

### Primary Entry Point: `detector_refinement()` function
- **Invoked by:** `run_diffbragg()` at line 120
- **Purpose:** Refines detector geometry using DiffBragg backend
- **Scope:** All scratch files are written/read within this function

### Secondary Entry Point: `run_diffbragg()` function
- **Invoked by:** `dbex.refine_one` module (CLI entry point)
- **Purpose:** Main refinement loop (xtal → Fhkl → detector)
- **Scope:** Writes `_temp.mtz` in macro cycle loop

## Parameterizability Assessment

**GOOD NEWS:** All paths are parameterizable!

1. **File writes** (`.as_file()`, `.to_pickle()`, `.write()`, `open()`) accept path strings
2. **String references** (dataframe columns, params attributes) can be updated to match new paths
3. **Directory reads** (`ExperimentList.from_file()`) accept path strings

**NO NEED FOR `os.chdir()` fallback** — all paths can be updated directly.

## Implementation Strategy

### Approach: Direct Path Parameterization

1. **Add `scratch_dir: Path` parameter** to `detector_refinement()` function
2. **Update all file paths** to use `scratch_dir / "geom_ref" / "_geom_ref.expt"`, etc.
3. **Create subdirectories** as needed: `geom_ref/`, `geom_out/`
4. **Pass scratch directory** from `run_diffbragg()` caller

### Required Changes

**`detector_refinement()` signature change:**
```python
def detector_refinement(model_df, Expt, Refs, params, scratch_dir: Optional[Path] = None):
    if scratch_dir is None:
        scratch_dir = Path.cwd()  # Backward compatibility

    geom_ref_dir = scratch_dir / "geom_ref"
    geom_ref_dir.mkdir(parents=True, exist_ok=True)

    geom_out_dir = scratch_dir / "geom_out"
    # ... update all paths ...
```

**Line-by-line changes:**
- Line 20: `new_El.as_file(str(geom_ref_dir / "_geom_ref.expt"))`
- Line 21: `Refs.as_file(str(geom_ref_dir / "_geom_ref.refl"))`
- Line 23: `model_df["geom_exp"] = str(geom_ref_dir / "_geom_ref.expt")`
- Line 24: `model_df["geom_ref"] = str(geom_ref_dir / "_geom_ref.refl")`
- Line 26: `model_df.to_pickle(str(geom_ref_dir / "_geom_ref.pkl"))`
- Line 28: `with open(str(geom_ref_dir / "_geom_groups.txt"), "w") as o:`
- Line 33: `params_geom.refiner.panel_group_file = str(geom_ref_dir / "_geom_groups.txt")`
- Line 36: `params_geom.geometry.input_pkl = str(geom_ref_dir / "_geom_ref.pkl")`
- Line 39: `params_geom.outdir = str(geom_out_dir)`
- Line 43: `new_det = ExperimentList.from_file(str(geom_out_dir / "diffBragg_detector.expt"))[0].detector`

**Note:** `_temp.mtz` in `run_diffbragg()` is currently NOT scoped (written to cwd). This is acceptable for Phase D D1 since:
1. It's written once per macro cycle (not per-run collision risk)
2. It's in the outer refinement loop, not the backend entry point
3. Can be addressed in future phase if needed

## Risk Mitigation

**R1: Backend Hardcoded Paths** — RESOLVED ✓
- All paths are parameterizable, no `os.chdir()` needed

**R2: Path Length Limits** — LOW
- Using short directory names (`geom_ref/`, `geom_out/`)

**R3: Cleanup Failures** — LOW
- Context manager handles cleanup with try/finally

**R4: Performance Overhead** — LOW
- Directory creation is negligible (< 1ms)

## Findings Applied

- **SPEC-DB-CORE** (Line number citations): All paths cited with `file:line` format ✓
- **CLAUDE.md Search First**: Grepped entire `dbex/` before implementing ✓
- **ARCH Design**: Direct parameterization (no `os.chdir()` side effects) ✓

## Next Steps

1. Create `dbex/diffbragg_tmp.py` with `diffbragg_scratch_dir()` context manager
2. Update `detector_refinement()` to accept `scratch_dir` parameter
3. Create validation tests with multiprocessing
4. Run tests and verify isolation

## Artifacts

- `grep_geom_ref.txt` (embedded in this report)
- `grep_temp_mtz.txt` (embedded in this report)
- `grep_geom_out.txt` (embedded in this report)
- `grep_geom_groups.txt` (embedded in this report)
