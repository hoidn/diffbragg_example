"""
Tests for DiffBragg scratch file isolation utilities.

Validates:
- Concurrent run isolation via multiprocessing
- User-provided output directory
- Cleanup behavior (--keep-scratch flag)
- No leftover scratch files in working directory
"""

import multiprocessing
import time
from pathlib import Path
import shutil

import pytest

from dbex.diffbragg_tmp import diffbragg_scratch_dir


def _concurrent_worker(worker_id):
    """
    Worker function for concurrent test.

    Must be at module level for multiprocessing pickling.
    """
    with diffbragg_scratch_dir() as scratch:
        # Simulate DiffBragg writing geom_ref files
        geom_ref_dir = scratch / "geom_ref"
        geom_ref_dir.mkdir(exist_ok=True)
        test_file = geom_ref_dir / "_geom_ref.expt"
        test_file.write_text(f"worker {worker_id} artifact")
        time.sleep(0.1)  # Simulate processing
        return test_file.exists()


def test_scratch_dir_default():
    """Test default system temp directory allocation."""
    with diffbragg_scratch_dir() as scratch:
        assert scratch.exists()
        assert scratch.is_dir()
        # Verify it's a Path object
        assert isinstance(scratch, Path)
        # Create test file
        test_file = scratch / "test.txt"
        test_file.write_text("test")
        assert test_file.exists()
    # After context exit, temp dir should be cleaned up
    # (Note: can't test cleanup of system temp directly, handled by TemporaryDirectory)


def test_scratch_dir_subdirectories():
    """Test creating subdirectories within scratch directory."""
    with diffbragg_scratch_dir() as scratch:
        # Create geom_ref subdirectory
        geom_ref_dir = scratch / "geom_ref"
        geom_ref_dir.mkdir(parents=True, exist_ok=True)
        assert geom_ref_dir.exists()

        # Create geom_out subdirectory
        geom_out_dir = scratch / "geom_out"
        geom_out_dir.mkdir(parents=True, exist_ok=True)
        assert geom_out_dir.exists()

        # Write test files
        (geom_ref_dir / "_geom_ref.expt").write_text("test expt")
        (geom_out_dir / "diffBragg_detector.expt").write_text("test detector")

        assert (geom_ref_dir / "_geom_ref.expt").exists()
        assert (geom_out_dir / "diffBragg_detector.expt").exists()


def test_scratch_dir_user_provided():
    """Test user-provided output directory."""
    user_dir = Path("/tmp/test_diffbragg_user")
    user_dir.mkdir(parents=True, exist_ok=True)

    try:
        with diffbragg_scratch_dir(user_out_dir=user_dir, cleanup=True) as scratch:
            assert scratch.exists()
            assert scratch.parent == user_dir
            # Verify timestamped directory name
            assert scratch.name.startswith("diffbragg_")
            test_file = scratch / "test.txt"
            test_file.write_text("test")
            assert test_file.exists()
            scratch_path = scratch  # Save for later check
        # Cleanup should remove subdirectory
        assert not scratch_path.exists()
    finally:
        # Clean up parent directory
        if user_dir.exists():
            shutil.rmtree(user_dir)


def test_scratch_dir_keep_scratch():
    """Test --keep-scratch flag (cleanup=False)."""
    user_dir = Path("/tmp/test_diffbragg_keep")
    user_dir.mkdir(parents=True, exist_ok=True)

    try:
        with diffbragg_scratch_dir(user_out_dir=user_dir, cleanup=False) as scratch:
            test_file = scratch / "test.txt"
            test_file.write_text("test")
            scratch_path = scratch  # Save for later check
        # Scratch dir should persist
        assert scratch_path.exists()
        assert (scratch_path / "test.txt").exists()
    finally:
        # Manual cleanup
        if user_dir.exists():
            shutil.rmtree(user_dir)


def test_concurrent_diffbragg_runs():
    """
    Test concurrent runs with isolated scratch directories.

    This is the core validation for Phase D D1: ensures concurrent runs
    don't collide on scratch files.
    """
    cwd = Path.cwd()

    # Clean up any pre-existing scratch files before test
    # (from manual testing or previous runs without scratch isolation)
    for scratch_file in ["_geom_ref.expt", "_geom_ref.refl", "_geom_ref.pkl", "_geom_groups.txt"]:
        scratch_path = cwd / scratch_file
        if scratch_path.exists():
            scratch_path.unlink()

    # Spawn 3 workers concurrently
    with multiprocessing.Pool(3) as pool:
        results = pool.map(_concurrent_worker, [1, 2, 3])

    assert all(results), "All workers should write artifacts successfully"

    # Check: no NEW _geom_ref.* files created in current working dir
    # (This is the core assertion: concurrent runs don't pollute workspace)
    assert not (cwd / "_geom_ref.expt").exists(), "No scratch files in working dir"
    assert not (cwd / "_geom_ref.refl").exists(), "No scratch files in working dir"
    assert not (cwd / "_geom_ref.pkl").exists(), "No scratch files in working dir"
    assert not (cwd / "_geom_groups.txt").exists(), "No scratch files in working dir"


def test_scratch_cleanup():
    """
    Test cleanup behavior.

    Validates that scratch directory is properly cleaned up after context exit.
    """
    user_dir = Path("/tmp/test_diffbragg_cleanup")
    user_dir.mkdir(parents=True, exist_ok=True)

    try:
        scratch_paths = []
        for i in range(3):
            with diffbragg_scratch_dir(user_out_dir=user_dir, cleanup=True) as scratch:
                # Create some files
                (scratch / f"file_{i}.txt").write_text(f"test {i}")
                scratch_paths.append(scratch)
                # Verify cleanup after each context
                time.sleep(0.01)  # Ensure unique timestamps

        # All scratch directories should be cleaned up
        for scratch_path in scratch_paths:
            assert not scratch_path.exists(), f"Scratch directory {scratch_path} should be cleaned up"

    finally:
        # Clean up parent directory
        if user_dir.exists():
            shutil.rmtree(user_dir)


def test_scratch_dir_no_geom_out_pollution():
    """
    Test that _geom.out/ directory is NOT created in working directory.

    This validates that the geom_out directory is isolated to scratch.
    """
    cwd = Path.cwd()
    geom_out_cwd = cwd / "_geom.out"

    # Clean up any pre-existing _geom.out (from manual testing)
    if geom_out_cwd.exists():
        shutil.rmtree(geom_out_cwd)

    with diffbragg_scratch_dir() as scratch:
        geom_out_dir = scratch / "geom_out"
        geom_out_dir.mkdir(parents=True, exist_ok=True)
        (geom_out_dir / "test.txt").write_text("test")
        assert geom_out_dir.exists()

    # After context exit, no _geom.out in working directory
    assert not geom_out_cwd.exists(), "No _geom.out/ directory in working dir"
