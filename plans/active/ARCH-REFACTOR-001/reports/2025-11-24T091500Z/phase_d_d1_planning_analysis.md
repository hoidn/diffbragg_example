# ARCH-REFACTOR-001 Phase D D1 Planning Analysis: DiffBragg Scratch Isolation

**Date:** 2025-11-24T091500Z
**Loop:** Galph supervisor (i=255)
**Phase:** D1 — DiffBragg Scratch Isolation (Planning)
**Decision:** Ready for implementation (single loop, ~2-3 hours estimated)

## Objective

Create utilities under `dbex/diffbragg_tmp.py` (or similar) that allocate per-run temporary directories using `tempfile.TemporaryDirectory` or user-provided `--out-dir`, ensuring `_geom_ref.*`, `_temp.mtz`, `_geom.out/` artifacts live under isolated scopes and don't collide during concurrent runs.

## Background

**Problem:** DiffBragg backend currently writes scratch files (`_geom_ref.*`, `_temp.mtz`, `_geom.out/`) to working directory, causing:
1. Artifact collisions during concurrent runs (multiprocessing, parallel jobs)
2. Leftover scratch files polluting workspace
3. Difficulty debugging when multiple runs interleave logs/artifacts

**Solution:** Allocate per-run temporary directories with deterministic structure, update backend to write artifacts under temp scope, ensure cleanup after run.

## Scope Analysis

### Current State Investigation

**Step 1:** Locate DiffBragg backend code that writes scratch files.

```bash
# Search for file write operations
grep -rn "_geom_ref" dbex/ --include="*.py"
grep -rn "_temp.mtz" dbex/ --include="*.py"
grep -rn "_geom.out" dbex/ --include="*.py"
```

**Step 2:** Identify entry points where backend is invoked (likely `dbex/run_diffbragg_backend.py` or similar).

**Step 3:** Determine if scratch file paths are hardcoded or configurable.

### Implementation Design

**Module:** `dbex/diffbragg_tmp.py` (new file)

**Interface:**
```python
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

@contextmanager
def diffbragg_scratch_dir(user_out_dir: Optional[Path] = None, cleanup: bool = True):
    """
    Allocate per-run temporary directory for DiffBragg scratch files.

    Args:
        user_out_dir: Optional user-provided output directory. If provided, creates
                      subdirectory under this path instead of system temp.
        cleanup: If True, remove temp directory after context exit (default True).
                 Set False for debugging (e.g., via --keep-scratch CLI flag).

    Yields:
        Path to scratch directory containing:
        - geom_ref/: _geom_ref.* files
        - temp/: _temp.mtz and intermediate artifacts
        - geom_out/: _geom.out/ directory

    Example:
        with diffbragg_scratch_dir() as scratch:
            geom_ref_path = scratch / "geom_ref" / "_geom_ref.expt"
            run_diffbragg_backend(geom_ref_path=geom_ref_path, ...)
    """
    if user_out_dir is not None:
        # User-provided directory: create subdirectory with timestamp
        scratch_dir = user_out_dir / f"diffbragg_scratch_{timestamp()}"
        scratch_dir.mkdir(parents=True, exist_ok=True)
        try:
            yield scratch_dir
        finally:
            if cleanup:
                shutil.rmtree(scratch_dir)
    else:
        # System temp directory (automatically cleaned up)
        with TemporaryDirectory(prefix="diffbragg_") as tmpdir:
            yield Path(tmpdir)
```

**Subdirectory Structure:**
```
scratch_root/
├── geom_ref/      # _geom_ref.* files
├── temp/          # _temp.mtz, intermediate artifacts
└── geom_out/      # _geom.out/ directory
```

### Code Changes

**1. Create `dbex/diffbragg_tmp.py`** (~80 lines)
- `diffbragg_scratch_dir()` context manager
- Subdirectory creation helpers
- Cleanup logic with fallback for debugging

**2. Update DiffBragg backend entry point** (~20 lines)
- Wrap backend invocation in `with diffbragg_scratch_dir() as scratch:`
- Pass `scratch` paths to backend functions
- Update any hardcoded `_geom_ref` → `scratch / "geom_ref" / "_geom_ref"`

**3. Add CLI flags** (~10 lines)
- `--out-dir PATH`: User-provided output directory (optional)
- `--keep-scratch`: Disable cleanup for debugging (default False)

**4. Update docs** (~30 lines)
- `README.md` or `docs/spec-db-workflow.md`: Document new CLI flags
- Example usage with `--out-dir` and `--keep-scratch`

**Total Estimated Lines:** ~140 lines (new + modified)

### Validation Strategy

**Test 1: Sequential Runs** (sanity check)
```bash
# Run backend twice sequentially, ensure no conflicts
python -m dbex.run_diffbragg_backend <args>
python -m dbex.run_diffbragg_backend <args>
# Check: no leftover _geom_ref.* in working dir
```

**Test 2: Concurrent Runs** (core validation)
```python
# tests/dbex/test_diffbragg_tmp.py
import multiprocessing
from dbex.diffbragg_tmp import diffbragg_scratch_dir

def test_concurrent_diffbragg_runs():
    """Spawn 2 backend runs simultaneously, verify artifact isolation."""
    def worker(i):
        with diffbragg_scratch_dir() as scratch:
            # Simulate backend writing _geom_ref.expt
            geom_ref = scratch / "geom_ref" / "_geom_ref.expt"
            geom_ref.parent.mkdir(exist_ok=True)
            geom_ref.write_text(f"worker {i} artifact")
            time.sleep(0.5)  # Simulate processing
            return geom_ref.exists()

    with multiprocessing.Pool(2) as pool:
        results = pool.map(worker, [1, 2])

    assert all(results), "All workers should write artifacts successfully"
    # Check: no _geom_ref.* in working dir
    assert not Path("_geom_ref.expt").exists(), "No scratch files in working dir"
```

**Test 3: User-Provided Output Directory** (optional feature)
```bash
# Run with --out-dir, check artifacts land in correct location
python -m dbex.run_diffbragg_backend --out-dir /tmp/dbex_run <args>
# Check: /tmp/dbex_run/diffbragg_scratch_<timestamp>/ exists
```

**Test 4: Keep-Scratch Flag** (debugging workflow)
```bash
# Run with --keep-scratch, check artifacts persist after run
python -m dbex.run_diffbragg_backend --keep-scratch <args>
# Check: scratch directory NOT deleted, can inspect _geom_ref.*
```

### Risk Assessment

**R1: Backend Hardcoded Paths** (MEDIUM)
- **Risk:** Backend functions may have hardcoded `_geom_ref` paths that are difficult to parameterize.
- **Mitigation:** Use `os.chdir()` to set working directory to scratch root before backend invocation (fallback).
- **Detection:** Grep for hardcoded paths during Step 1 investigation.

**R2: Path Length Limits** (LOW)
- **Risk:** Windows MAX_PATH=260 may cause issues with deep temp directories.
- **Mitigation:** Use short temp directory names (`diffbragg_` prefix, not `diffbragg_scratch_<long_timestamp>`).
- **Detection:** Test on Windows if available, or document known limitation.

**R3: Cleanup Failures** (LOW)
- **Risk:** `shutil.rmtree()` may fail if files are locked (Windows) or permissions issue (Unix).
- **Mitigation:** Log cleanup errors as warnings, don't fail run. Provide `--keep-scratch` for debugging.
- **Detection:** Test cleanup with locked files (simulate).

**R4: Performance Overhead** (LOW)
- **Risk:** Creating/deleting temp directories may add overhead to backend runs.
- **Mitigation:** Use system `/tmp` (ramdisk on many Linux systems), avoid deep nesting.
- **Detection:** Benchmark backend runtime before/after change (expect <1% overhead).

### Decision Tree (4-Path Template)

**Path A: All Tests PASS** (90% confidence)
- Concurrent runs isolated ✓
- User `--out-dir` works ✓
- `--keep-scratch` flag works ✓
- No leftover scratch files in working dir ✓
- **Action:** Mark Phase D D1 complete, commit changes, proceed to D2 planning.

**Path B: Concurrent Tests PASS, Minor Issues** (75% confidence)
- Concurrent runs isolated ✓
- User `--out-dir` or `--keep-scratch` has minor bugs (path resolution, etc.)
- **Action:** Fix minor bugs in same loop, re-test, mark complete if passing.

**Path C: Backend Hardcoded Paths Block Parameterization** (15% confidence)
- Backend has deeply hardcoded `_geom_ref` paths that cannot be easily parameterized.
- **Action:** Use `os.chdir()` fallback (change working dir to scratch root), update tests to verify this approach.

**Path D: Fundamental Design Issue** (5% confidence)
- Backend architecture fundamentally incompatible with scratch isolation (e.g., requires specific filesystem layout).
- **Action:** Document blocker in `phase_d_d1_blocker.md`, escalate to new initiative for backend refactor, mark D1 blocked.

### Estimated Effort

**Investigation:** 30 min (grep hardcoded paths, locate entry points)
**Implementation:** 90 min (create `diffbragg_tmp.py`, update backend, add CLI flags)
**Validation:** 45 min (write tests, run concurrent validation, check cleanup)
**Documentation:** 15 min (update README/spec docs with CLI flags)
**Total:** ~3 hours (single loop)

### Confidence Assessment

**HIGH confidence** (~90%) Phase D D1 will succeed in single loop:
1. **Clear Scope:** Isolated tooling change, no core refactoring
2. **Well-Defined Interface:** Context manager pattern is standard Python
3. **Validation Strategy:** Multiprocessing test directly validates isolation
4. **Low Risk:** Fallback strategies for all identified risks

## Checklist (from implementation.md:195-197)

- [ ] D1.1: **Create `dbex/diffbragg_tmp.py`** — Context manager `diffbragg_scratch_dir()` with subdirectory structure (geom_ref/, temp/, geom_out/).
- [ ] D1.2: **Update `run_diffbragg_backend`** — Wrap invocation in context manager, pass scratch paths to backend.
- [ ] D1.3: **Add CLI flags** — `--out-dir PATH` (optional user directory), `--keep-scratch` (disable cleanup).
- [ ] D1.4: **Validation tests** — `tests/dbex/test_diffbragg_tmp.py` with concurrent multiprocessing test.
- [ ] D1.5: **Update docs** — `README.md` or `docs/spec-db-workflow.md` with CLI flag examples.

## Findings Applied

- **POLICY-001** (Environment Freeze): stdlib only (`tempfile`, `pathlib`, `shutil`) ✓
- **CLAUDE.md Simplicity**: "Choose the boring solution" — standard context manager pattern ✓
- **CLAUDE.md Incremental Progress**: "Small changes that compile and pass tests" — isolated tooling change ✓
- **galph_prompt Implementation Floor**: Next loop MUST be ready_for_implementation ✓

## Next Actions (for Ralph)

**input.md Do Now Specification** (9-step protocol):
1. **Read planning analysis:** `plans/active/ARCH-REFACTOR-001/reports/2025-11-24T091500Z/phase_d_d1_planning_analysis.md`
2. **Investigation:** Locate DiffBragg backend entry points and hardcoded scratch file paths (grep `_geom_ref`, `_temp.mtz`, `_geom.out`).
3. **Implement D1.1:** Create `dbex/diffbragg_tmp.py` with `diffbragg_scratch_dir()` context manager (~80 lines).
4. **Implement D1.2:** Update backend entry point to use scratch directory (~20 lines).
5. **Implement D1.3:** Add CLI flags `--out-dir`, `--keep-scratch` to backend argparse (~10 lines).
6. **Implement D1.4:** Create `tests/dbex/test_diffbragg_tmp.py` with concurrent multiprocessing test (~60 lines).
7. **Validation:** Run test suite, check concurrent isolation, verify cleanup.
8. **Implement D1.5:** Update docs with CLI flag examples (~30 lines).
9. **Decision synthesis** → `phase_d_d1_decision.md` (Path A/B/C/D verdict).
10. **Commit:** `git commit -m "ARCH-REFACTOR-001 Phase D D1: DiffBragg scratch isolation — tests: run"` and push.

## Artifacts

- `phase_c_complexity_assessment.md` (Phase C deferral rationale)
- `phase_d_d1_planning_analysis.md` (this document)
- `input.md` (ready_for_implementation Do Now for Ralph)

## References

- Implementation Plan: `plans/active/ARCH-REFACTOR-001/implementation.md:191-209` (Phase D checklist)
- Python `tempfile` docs: https://docs.python.org/3/library/tempfile.html
- Context managers: https://docs.python.org/3/reference/datamodel.html#context-managers
