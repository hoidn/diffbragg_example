# ARCH-REFACTOR-001 Phase D D1: DiffBragg Scratch Isolation

## Summary
Create utilities for per-run temporary directories isolating DiffBragg scratch files (`_geom_ref.*`, `_temp.mtz`, `_geom.out/`), preventing concurrent run collisions and workspace pollution.

## Mode
none (tooling refactor + validation)

## Focus
ARCH-REFACTOR-001 — Refinement Engine Modularization & Physics Separation (Phase D D1: DiffBragg Scratch Isolation)

## Branch
integration

## Mapped Tests
- `tests/dbex/test_diffbragg_tmp.py::test_concurrent_diffbragg_runs` (NEW: Validates concurrent run isolation via multiprocessing)
- `tests/dbex/test_diffbragg_tmp.py::test_scratch_cleanup` (NEW: Validates cleanup behavior)
- No existing smoke tests available (DiffBragg backend is utility, not main refine path)

## Artifacts
`plans/active/ARCH-REFACTOR-001/reports/2025-11-24T091500Z/`
- `phase_d_d1_planning_analysis.md` (planning document, already exists)
- `investigation_scratch_files.md` (grep results, entry points, hardcoded paths)
- `dbex/diffbragg_tmp.py` (NEW: context manager ~80 lines)
- `tests/dbex/test_diffbragg_tmp.py` (NEW: validation tests ~100 lines)
- `pytest_diffbragg_tmp.log` (test run log)
- `phase_d_d1_decision.md` (Path A/B/C/D verdict)
- `summary.md` (Turn Summary block)

## Do Now

Ralph, execute ARCH-REFACTOR-001 Phase D D1 implementation (DiffBragg scratch isolation):

**Context:** Phases 0/A/B complete (test discipline, physics extraction, telemetry modernization). Phase C deferred (12-16 loop Engine Migration). Phase D D1 addresses DX pain point: DiffBragg backend writes scratch files (`_geom_ref.expt`, `_geom_ref.refl`, `_geom_ref.pkl`, `_geom_groups.txt`, `_geom.out/` directory, `_temp.mtz`) to working directory per TODO comment at dbex/run_diffbragg.py:15, causing collisions during concurrent runs.

**Objective:** Isolate scratch files in per-run temporary directories with context manager pattern (stdlib `tempfile`), ensuring cleanup and supporting user-provided output directory for debugging.

### Implementation Steps (10-Step Protocol)

1. **Read planning analysis:** `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T091500Z/phase_d_d1_planning_analysis.md`

2. **Investigation** → `investigation_scratch_files.md`:
   - **Step 2a:** Locate ALL hardcoded scratch file paths:
     ```bash
     grep -n "_geom_ref" dbex/run_diffbragg.py
     grep -n "_temp.mtz" dbex/
     grep -n "_geom.out" dbex/run_diffbragg.py
     grep -n "_geom_groups.txt" dbex/run_diffbragg.py
     ```
   - **Step 2b:** Document findings: Which function writes each file? Are paths hardcoded or parameterizable?
   - **Step 2c:** Identify entry points: How is `run_diffbragg.py` invoked? (CLI, library import, etc.)

3. **Implement D1.1:** Create `dbex/diffbragg_tmp.py` (~80 lines):
   ```python
   from contextlib import contextmanager
   from pathlib import Path
   from tempfile import TemporaryDirectory
   from typing import Optional
   import shutil
   import time

   @contextmanager
   def diffbragg_scratch_dir(user_out_dir: Optional[Path] = None, cleanup: bool = True):
       """
       Allocate per-run temporary directory for DiffBragg scratch files.

       Args:
           user_out_dir: Optional user-provided output directory. If provided,
                         creates subdirectory under this path instead of system temp.
           cleanup: If True, remove temp directory after context exit (default True).
                    Set False for debugging (e.g., via --keep-scratch CLI flag).

       Yields:
           Path to scratch directory with subdirectories:
           - geom_ref/: _geom_ref.* files
           - temp/: _temp.mtz and intermediate artifacts
           - geom_out/: _geom.out/ directory

       Example:
           with diffbragg_scratch_dir() as scratch:
               geom_ref_dir = scratch / "geom_ref"
               geom_ref_dir.mkdir(exist_ok=True)
               # Use geom_ref_dir for _geom_ref.expt, etc.
       """
       if user_out_dir is not None:
           # User-provided directory: create timestamped subdirectory
           timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
           scratch_dir = user_out_dir / f"diffbragg_{timestamp}"
           scratch_dir.mkdir(parents=True, exist_ok=True)
           try:
               yield scratch_dir
           finally:
               if cleanup:
                   try:
                       shutil.rmtree(scratch_dir)
                   except Exception as e:
                       # Log warning but don't fail
                       print(f"Warning: cleanup failed for {scratch_dir}: {e}")
       else:
           # System temp directory (automatically cleaned up)
           with TemporaryDirectory(prefix="diffbragg_") as tmpdir:
               yield Path(tmpdir)
   ```

4. **Implement D1.2:** Update `dbex/run_diffbragg.py` `detector_refinement()` function:
   - **Option A (if parameterizable):** Add `scratch_dir: Path` parameter, replace hardcoded paths with `scratch_dir / "geom_ref" / "_geom_ref.expt"`, etc.
   - **Option B (if not parameterizable):** Use `os.chdir()` to change working directory to scratch root before calling backend functions, then `os.chdir()` back after.
   - **Key Changes (~20 lines):**
     - Line 20: `new_El.as_file(scratch_dir / "geom_ref" / "_geom_ref.expt")`
     - Line 21: `Refs.as_file(scratch_dir / "geom_ref" / "_geom_ref.refl")`
     - Line 26: `model_df.to_pickle(scratch_dir / "geom_ref" / "_geom_ref.pkl")`
     - Line 28: `open(scratch_dir / "geom_ref" / "_geom_groups.txt", "w")`
     - Line 36: `params_geom.geometry.input_pkl = str(scratch_dir / "geom_ref" / "_geom_ref.pkl")`
     - Line 39: `params_geom.outdir = str(scratch_dir / "geom_out")`
     - Line 43: `ExperimentList.from_file(scratch_dir / "geom_out" / "diffBragg_detector.expt")`

5. **Implement D1.3:** Add CLI flags (if `run_diffbragg.py` has CLI entry point):
   - Add `--out-dir PATH` argument (optional user directory)
   - Add `--keep-scratch` flag (disable cleanup for debugging)
   - Wrap invocation in `with diffbragg_scratch_dir(args.out_dir, cleanup=not args.keep_scratch) as scratch:`

6. **Implement D1.4:** Create `tests/dbex/test_diffbragg_tmp.py` (~100 lines):
   ```python
   import multiprocessing
   import time
   from pathlib import Path
   from dbex.diffbragg_tmp import diffbragg_scratch_dir

   def test_scratch_dir_default():
       """Test default system temp directory allocation."""
       with diffbragg_scratch_dir() as scratch:
           assert scratch.exists()
           assert scratch.is_dir()
           # Create test file
           test_file = scratch / "test.txt"
           test_file.write_text("test")
           assert test_file.exists()
       # After context exit, temp dir should be cleaned up
       # (Note: can't test cleanup of system temp directly)

   def test_scratch_dir_user_provided():
       """Test user-provided output directory."""
       user_dir = Path("/tmp/test_diffbragg_user")
       user_dir.mkdir(parents=True, exist_ok=True)
       with diffbragg_scratch_dir(user_out_dir=user_dir, cleanup=True) as scratch:
           assert scratch.exists()
           assert scratch.parent == user_dir
           test_file = scratch / "test.txt"
           test_file.write_text("test")
       # Cleanup should remove subdirectory
       assert not scratch.exists()
       user_dir.rmdir()  # Clean up parent

   def test_scratch_dir_keep_scratch():
       """Test --keep-scratch flag (cleanup=False)."""
       user_dir = Path("/tmp/test_diffbragg_keep")
       user_dir.mkdir(parents=True, exist_ok=True)
       with diffbragg_scratch_dir(user_out_dir=user_dir, cleanup=False) as scratch:
           test_file = scratch / "test.txt"
           test_file.write_text("test")
       # Scratch dir should persist
       assert scratch.exists()
       assert (scratch / "test.txt").exists()
       # Manual cleanup
       import shutil
       shutil.rmtree(user_dir)

   def test_concurrent_diffbragg_runs():
       """Test concurrent runs with isolated scratch directories."""
       def worker(worker_id):
           with diffbragg_scratch_dir() as scratch:
               # Simulate DiffBragg writing geom_ref files
               geom_ref_dir = scratch / "geom_ref"
               geom_ref_dir.mkdir(exist_ok=True)
               test_file = geom_ref_dir / "_geom_ref.expt"
               test_file.write_text(f"worker {worker_id} artifact")
               time.sleep(0.1)  # Simulate processing
               return test_file.exists()

       with multiprocessing.Pool(3) as pool:
           results = pool.map(worker, [1, 2, 3])

       assert all(results), "All workers should write artifacts successfully"
       # Check: no _geom_ref.expt in current working dir
       assert not Path("_geom_ref.expt").exists(), "No scratch files in working dir"
   ```

7. **Validation:** Run test suite:
   ```bash
   pytest tests/dbex/test_diffbragg_tmp.py -xvs --tb=short 2>&1 | tee plans/active/ARCH-REFACTOR-001/reports/2025-11-24T091500Z/pytest_diffbragg_tmp.log
   ```

8. **Decision synthesis** → `phase_d_d1_decision.md` (Path A/B/C/D verdict):
   - **Path A:** All tests PASS (concurrent isolation ✓, user `--out-dir` ✓, `--keep-scratch` ✓, no leftover files ✓) → Phase D D1 COMPLETE
   - **Path B:** Tests PASS, minor bugs (path resolution, etc.) → Fix in same loop, re-test
   - **Path C:** Backend hardcoded paths require `os.chdir()` fallback → Document approach, re-test
   - **Path D:** Fundamental design issue → Document blocker, escalate

9. **Implement D1.5:** Update docs (~30 lines):
   - Update `README.md` or `docs/spec-db-workflow.md` with CLI flags:
     ```markdown
     ## DiffBragg Backend Usage

     DiffBragg scratch files (`_geom_ref.*`, `_temp.mtz`, `_geom.out/`) are automatically isolated in temporary directories.

     **CLI Flags:**
     - `--out-dir PATH`: Write scratch files to user-provided directory (default: system temp)
     - `--keep-scratch`: Preserve scratch files after run for debugging (default: auto-cleanup)

     **Example:**
     ```bash
     python -m dbex.run_diffbragg --out-dir /tmp/dbex_debug --keep-scratch <args>
     ```
     ```
     ```

10. **Commit:** `git add -A && git commit -m "ARCH-REFACTOR-001 Phase D D1: DiffBragg scratch isolation — tests: run" && git push`

## How-To Map

### Investigation Commands
```bash
# Locate hardcoded scratch file paths
grep -n "_geom_ref" dbex/run_diffbragg.py > plans/active/ARCH-REFACTOR-001/reports/2025-11-24T091500Z/grep_geom_ref.txt
grep -rn "_temp.mtz" dbex/ --include="*.py" > plans/active/ARCH-REFACTOR-001/reports/2025-11-24T091500Z/grep_temp_mtz.txt
grep -n "_geom.out" dbex/run_diffbragg.py >> plans/active/ARCH-REFACTOR-001/reports/2025-11-24T091500Z/grep_geom_out.txt
grep -n "_geom_groups.txt" dbex/run_diffbragg.py >> plans/active/ARCH-REFACTOR-001/reports/2025-11-24T091500Z/grep_geom_groups.txt
```

### Test Commands
```bash
# Run DiffBragg temp directory tests
pytest tests/dbex/test_diffbragg_tmp.py -xvs --tb=short 2>&1 | tee plans/active/ARCH-REFACTOR-001/reports/2025-11-24T091500Z/pytest_diffbragg_tmp.log
```

### Code Locations
- **DiffBragg Backend:** dbex/run_diffbragg.py (detector_refinement function, lines 17-45)
- **Hardcoded Paths:** Lines 20, 21, 26, 28, 36, 39, 43
- **NEW Module:** dbex/diffbragg_tmp.py (context manager)
- **NEW Tests:** tests/dbex/test_diffbragg_tmp.py (isolation validation)

## Pitfalls To Avoid

1. **DO NOT** modify DiffBragg backend logic (only scratch file paths)
2. **DO NOT** add external dependencies (stdlib only: `tempfile`, `pathlib`, `shutil`, `multiprocessing`)
3. **DO NOT** use `--no-verify` to bypass commit hooks
4. **DO** handle cleanup failures gracefully (log warnings, don't fail run)
5. **DO** test concurrent runs with multiprocessing (core validation)
6. **DO** preserve backward compatibility (if no CLI args provided, use system temp + auto-cleanup)
7. **DO** use Path objects for cross-platform compatibility (not string concatenation)
8. **DO** document `os.chdir()` approach if paths are not parameterizable

## Findings Applied (Mandatory)

- **POLICY-001** (Environment Freeze): stdlib only (`tempfile`, `pathlib`, `shutil`) ✓
- **CLAUDE.md Simplicity**: "Choose the boring solution" — context manager pattern is standard Python ✓
- **CLAUDE.md Incremental Progress**: "Small changes that compile and pass tests" — isolated tooling change ✓
- **galph_prompt Implementation Floor**: Next loop is ready_for_implementation ✓

## Pointers

- Planning: plans/active/ARCH-REFACTOR-001/reports/2025-11-24T091500Z/phase_d_d1_planning_analysis.md
- Implementation Plan: plans/active/ARCH-REFACTOR-001/implementation.md:191-209 (Phase D checklist)
- Fix Plan: docs/fix_plan.md ARCH-REFACTOR-001 entry (line 118)
- DiffBragg Backend: dbex/run_diffbragg.py:15 (TODO comment confirming scratch file issue)

## Next Up (optional)

If Phase D D1 finishes early:
- Phase D D2: Stage A debug tooling modularization (extract utilities from `plans/active/TOOLING-VIS-001/bin/stage_a_mapping_adam_debug.py`)
- Phase D D3: Summary-generation CLI cleanup (convert to argparse-driven CLIs)
