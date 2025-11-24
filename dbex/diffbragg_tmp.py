"""
Temporary directory utilities for DiffBragg scratch file isolation.

This module provides a context manager for allocating per-run temporary
directories, preventing concurrent run collisions and workspace pollution.
"""

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

    DiffBragg backend writes scratch files (_geom_ref.*, _temp.mtz, _geom.out/)
    during detector refinement. This context manager isolates these files in
    temporary directories to prevent:
    1. Artifact collisions during concurrent runs
    2. Leftover scratch files polluting workspace
    3. Difficulty debugging when multiple runs interleave artifacts

    Args:
        user_out_dir: Optional user-provided output directory. If provided,
                      creates timestamped subdirectory under this path instead
                      of system temp.
        cleanup: If True, remove temp directory after context exit (default True).
                 Set False for debugging (e.g., via --keep-scratch CLI flag).

    Yields:
        Path to scratch directory root. Caller should create subdirectories
        as needed:
        - geom_ref/: _geom_ref.* files (expt, refl, pkl, groups.txt)
        - geom_out/: _geom.out/ directory (refined detector artifacts)
        - temp/: _temp.mtz and other intermediate artifacts (future)

    Example:
        with diffbragg_scratch_dir() as scratch:
            geom_ref_dir = scratch / "geom_ref"
            geom_ref_dir.mkdir(parents=True, exist_ok=True)
            # Use geom_ref_dir for _geom_ref.expt, etc.
            # Files automatically cleaned up after context exit

    Example with user directory:
        with diffbragg_scratch_dir(user_out_dir=Path("/tmp/debug")) as scratch:
            # scratch = /tmp/debug/diffbragg_20251124T091500Z/
            # Files persist if cleanup=False

    Raises:
        OSError: If user_out_dir creation fails (permissions, disk full, etc.)

    Notes:
        - Cleanup failures are logged as warnings, not errors
        - System temp uses stdlib TemporaryDirectory (auto-cleanup)
        - User-provided directories use timestamped subdirectories
        - Cross-platform compatible (Path objects, not string concatenation)
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
                    # Log warning but don't fail run
                    # (User may have open file handles, permissions issues, etc.)
                    print(f"Warning: cleanup failed for {scratch_dir}: {e}")
    else:
        # System temp directory (automatically cleaned up by stdlib)
        with TemporaryDirectory(prefix="diffbragg_") as tmpdir:
            yield Path(tmpdir)
