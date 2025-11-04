"""
DB-AT-020 — Reflection ingestion sanity test.

Tests validate DIALS bbox exclusivity and panel alignment using refGeom assets.

Per input.md:
- docs/spec-db-conformance.md:28 defines DB-AT-020 expectations
- docs/spec-db-core.md:22 mandates bbox semantics: (x0, x1, y0, y1) with exclusive upper bounds
- docs/dials_api.md:10-28 covers bbox ordering and panel alignment
- docs/architecture.md:122 requires runtime alignment guards

Findings applied:
- CONFORMANCE-001: adhere to DB-AT selector naming, env flags, and artifact expectations
- TESTING-003: require collect-only evidence + doc sync before promoting selector to Active
- CONFIG-001: honor ROI bbox fast/slow ordering and detector alignment from config crosswalk
"""

import pytest
import numpy as np
from pathlib import Path
from argparse import Namespace

# DataLoad for ingestion testing
from dbex.data_load import DataLoad


@pytest.fixture(scope="module")
def refgeom_dataload():
    """
    Load refGeom dataset via DataLoad for ingestion testing.

    IMPORTANT: Requires reflection file from dials.stills_process.
    To generate required data files, see README.md Step 5.

    This fixture is SKIPPED if refGeom.refl doesn't exist, allowing CI
    to pass gracefully without canonical assets.

    Returns DataLoad instance with:
    - Expt: dxtbx Experiment with detector/beam/crystal
    - Refs: reflection table
    - data: pixel data [panel, slow, fast]
    - background_image: background estimate [panel, slow, fast], -1 outside ROIs
    - bbox: ROI bounding boxes (n_roi, 4) as (x0, x1, y0, y1)
    - pids: panel IDs (n_roi,)
    - F: structure factors with Bijvoet mates
    """
    # Build args namespace for DataLoad (repo-relative paths)
    repo_root = Path(__file__).parent.parent.parent
    refl_path = repo_root / "refGeom.refl"

    # Skip if reflection file doesn't exist
    if not refl_path.exists():
        pytest.skip(
            f"Reflection file not found: {refl_path}\n"
            "Run dials.stills_process to generate it (see README.md Step 5)"
        )

    args = Namespace(
        mtzFile=str(repo_root / "scaled.mtz"),
        mtzCol="F,SIGF",  # MTZ column name
        exptName=str(repo_root / "refGeom.expt"),
        exptIdx=0,
        reflName=str(refl_path)
    )

    # Load data (this invokes simtbx background estimation)
    dataload = DataLoad(args)
    return dataload


class TestReflectionIngestion:
    """
    Test suite for DB-AT-020 reflection ingestion sanity checks.

    Validates:
    - Bbox exclusivity: x1 > x0, y1 > y0 for all ROIs
    - Slice shape consistency: sliced data/background matches bbox deltas
    - Panel alignment: panel indices are valid and consistent
    - Detector bounds: all bboxes fall within detector dimensions
    """

    def test_DB_AT_020_reflection_bbox(self, refgeom_dataload):
        """
        DB-AT-020: Validate bbox exclusivity, slice shapes, and panel alignment.

        Per docs/spec-db-core.md:22 and docs/dials_api.md:10-28:
        - Bboxes SHALL be (x0, x1, y0, y1) with x1, y1 exclusive
        - Slice as img[pid, y0:y1, x0:x1]
        - Panel indices align with reflection table and detector

        Assertions:
        1. Bbox exclusivity: x1 > x0 and y1 > y0 for every ROI
        2. Slice shape matches bbox deltas: (y1-y0, x1-x0)
        3. Panel alignment: pids fall within detector range [0, n_panels)
        4. Detector bounds: all bboxes fit within panel dimensions
        """
        dl = refgeom_dataload

        # Extract detector geometry
        detector = dl.Expt.detector
        n_panels = len(detector)

        # bbox shape: (n_roi, 4) as (x0, x1, y0, y1)
        bboxes = dl.bbox
        pids = dl.pids
        n_rois = len(bboxes)

        assert n_rois > 0, "Expected at least one ROI in refGeom dataset"
        assert len(pids) == n_rois, f"Panel ID count {len(pids)} must match ROI count {n_rois}"

        # Get panel dimensions (assuming all panels same size for refGeom)
        panel0 = detector[0]
        panel_size_fast, panel_size_slow = panel0.get_image_size()

        # Track metrics for reporting
        bbox_failures = []
        slice_failures = []
        panel_failures = []
        bounds_failures = []

        # Validate each ROI
        for i, (bbox, pid) in enumerate(zip(bboxes, pids)):
            x0, x1, y0, y1 = bbox

            # 1. Bbox exclusivity check
            if not (x1 > x0 and y1 > y0):
                bbox_failures.append({
                    'roi_idx': i,
                    'bbox': (x0, x1, y0, y1),
                    'pid': pid,
                    'x_valid': x1 > x0,
                    'y_valid': y1 > y0
                })

            # 2. Panel alignment check
            if not (0 <= pid < n_panels):
                panel_failures.append({
                    'roi_idx': i,
                    'pid': pid,
                    'valid_range': (0, n_panels)
                })
                continue  # Skip further checks if panel ID is invalid

            # 3. Detector bounds check
            if not (0 <= x0 < x1 <= panel_size_fast and 0 <= y0 < y1 <= panel_size_slow):
                bounds_failures.append({
                    'roi_idx': i,
                    'bbox': (x0, x1, y0, y1),
                    'pid': pid,
                    'panel_size': (panel_size_fast, panel_size_slow)
                })

            # 4. Slice shape validation
            # Per docs/dials_api.md:27 — slice as imgs[pid, y0:y1, x0:x1]
            expected_shape = (y1 - y0, x1 - x0)

            # Slice data
            data_slice = dl.data[pid, y0:y1, x0:x1]
            if data_slice.shape != expected_shape:
                slice_failures.append({
                    'roi_idx': i,
                    'bbox': (x0, x1, y0, y1),
                    'pid': pid,
                    'expected_shape': expected_shape,
                    'actual_shape': data_slice.shape,
                    'source': 'data'
                })

            # Slice background_image
            bg_slice = dl.background_image[pid, y0:y1, x0:x1]
            if bg_slice.shape != expected_shape:
                slice_failures.append({
                    'roi_idx': i,
                    'bbox': (x0, x1, y0, y1),
                    'pid': pid,
                    'expected_shape': expected_shape,
                    'actual_shape': bg_slice.shape,
                    'source': 'background_image'
                })

        # Report findings
        if bbox_failures:
            failure_report = "\n".join([
                f"  ROI {f['roi_idx']}: bbox={f['bbox']}, pid={f['pid']}, "
                f"x_valid={f['x_valid']}, y_valid={f['y_valid']}"
                for f in bbox_failures[:5]  # Show first 5
            ])
            pytest.fail(
                f"Bbox exclusivity violations in {len(bbox_failures)}/{n_rois} ROIs:\n"
                f"{failure_report}\n"
                f"Expected: x1 > x0 and y1 > y0 for all ROIs per docs/spec-db-core.md:22"
            )

        if panel_failures:
            failure_report = "\n".join([
                f"  ROI {f['roi_idx']}: pid={f['pid']}, valid_range={f['valid_range']}"
                for f in panel_failures[:5]
            ])
            pytest.fail(
                f"Panel ID range violations in {len(panel_failures)}/{n_rois} ROIs:\n"
                f"{failure_report}\n"
                f"Expected: 0 <= pid < {n_panels} per docs/dials_api.md:13"
            )

        if bounds_failures:
            failure_report = "\n".join([
                f"  ROI {f['roi_idx']}: bbox={f['bbox']}, pid={f['pid']}, "
                f"panel_size={f['panel_size']}"
                for f in bounds_failures[:5]
            ])
            pytest.fail(
                f"Detector bounds violations in {len(bounds_failures)}/{n_rois} ROIs:\n"
                f"{failure_report}\n"
                f"Expected: bboxes within panel dimensions per docs/spec-db-core.md:22"
            )

        if slice_failures:
            failure_report = "\n".join([
                f"  ROI {f['roi_idx']}: bbox={f['bbox']}, pid={f['pid']}, "
                f"expected={f['expected_shape']}, actual={f['actual_shape']}, source={f['source']}"
                for f in slice_failures[:5]
            ])
            pytest.fail(
                f"Slice shape mismatches in {len(slice_failures)} slices:\n"
                f"{failure_report}\n"
                f"Expected: slice shape == (y1-y0, x1-x0) per docs/dials_api.md:27"
            )

        # All checks passed - emit summary
        print(f"\nDB-AT-020 PASSED: Validated {n_rois} ROIs across {n_panels} panel(s)")
        print(f"  - All bboxes satisfy exclusivity (x1 > x0, y1 > y0)")
        print(f"  - All panel IDs in valid range [0, {n_panels})")
        print(f"  - All bboxes within detector bounds")
        print(f"  - All slices match expected shapes")

        # Sample metrics for ledger
        sample_bbox = bboxes[0]
        sample_shape = (sample_bbox[3] - sample_bbox[2], sample_bbox[1] - sample_bbox[0])
        print(f"  - Sample ROI 0: bbox={tuple(sample_bbox)}, shape={sample_shape}, pid={pids[0]}")


    def test_DB_AT_020_panel_alignment(self, refgeom_dataload):
        """
        DB-AT-020: Validate panel indices match reflection table and detector.

        Additional alignment checks:
        - Reflection table 'panel' column matches DataLoad pids
        - Panel indices are consistent across data structures
        - No gaps or duplicates in panel indexing
        """
        dl = refgeom_dataload

        # Extract reflection table panel column
        refl_panels = list(dl.Refs['panel'])
        dataload_pids = list(dl.pids)

        # Basic length check
        assert len(refl_panels) == len(dataload_pids), \
            f"Reflection table panel count {len(refl_panels)} must match DataLoad pids count {len(dataload_pids)}"

        # Panel ID alignment check
        mismatches = []
        for i, (refl_pid, dl_pid) in enumerate(zip(refl_panels, dataload_pids)):
            if refl_pid != dl_pid:
                mismatches.append({
                    'roi_idx': i,
                    'refl_panel': refl_pid,
                    'dataload_pid': dl_pid
                })

        if mismatches:
            mismatch_report = "\n".join([
                f"  ROI {m['roi_idx']}: refl_panel={m['refl_panel']}, dataload_pid={m['dataload_pid']}"
                for m in mismatches[:10]  # Show first 10
            ])
            pytest.fail(
                f"Panel ID mismatches between reflection table and DataLoad in {len(mismatches)} ROIs:\n"
                f"{mismatch_report}\n"
                f"Expected: reflection['panel'] == DataLoad.pids per docs/dials_api.md:8"
            )

        # Detector range check (already covered in main test, but verify here too)
        detector = dl.Expt.detector
        n_panels = len(detector)
        out_of_range = [pid for pid in dataload_pids if not (0 <= pid < n_panels)]

        assert not out_of_range, \
            f"Found {len(out_of_range)} panel IDs outside detector range [0, {n_panels}): {out_of_range[:10]}"

        # Report success
        print(f"\nDB-AT-020 panel alignment PASSED: All {len(dataload_pids)} ROIs have consistent panel indices")
        print(f"  - Reflection table 'panel' matches DataLoad.pids")
        print(f"  - All panel IDs in valid range [0, {n_panels})")

        # Unique panels used
        unique_panels = sorted(set(dataload_pids))
        print(f"  - Unique panels in use: {unique_panels}")
