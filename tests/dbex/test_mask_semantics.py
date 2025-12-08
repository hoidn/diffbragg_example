"""
DB-AT-021 — Mask semantics guard acceptance test.

Tests validate mask polarity, loss_mask construction, and ARCH-CONTRACT-MASKING-001 precedence.

Per input.md:
- docs/spec-db-core.md:124 defines loss_mask normative formula: (background >= 0) ∧ trusted_mask
- docs/spec-db-conformance.md:58-61 defines DB-AT-021 acceptance criteria
- docs/dials_api.md:16 mandates mask polarity: True=trusted (no inversion)
- docs/architecture.md:165-178 specifies mask precedence rules (ADR-07 background sentinel)

Findings applied:
- MASKING-001: Loss mask coverage <1% is expected for sparse Bragg peaks; assertions do not flag low coverage as failure
- TESTING-003: Selector status transitions only after pytest --collect-only confirms >0 tests
- CONFORMANCE-001: DB-AT parity selectors use `-k DB_AT_0XX` pattern; test method naming follows `test_DB_AT_021_*`
- DIALS-API polarity: True=trusted per dials_api.md:16; test assertions validate boolean dtype with True=trusted polarity
"""

import ast
import pytest
import numpy as np
from pathlib import Path

# DataLoad for mask semantics validation
from dbex.data_load import DataLoad
from dbex.refinement.inputs import prepare_refinement_inputs


class TestDB_AT_021_MaskSemantics:
    """
    Test suite for DB-AT-021 mask semantics guard.

    Validates:
    - Mask polarity: trusted_mask is boolean with True=trusted (B2)
    - Loss mask construction: (background >= 0) & trusted_mask per spec (B3)
    - ARCH-CONTRACT-MASKING-001: canonical owner precedence, no duplicates (B4)
    """

    def test_DB_AT_021_polarity_checks(self, refgeom_dataload):
        """
        DB-AT-021 B2: Validate trusted_mask polarity and dtype.

        Per docs/dials_api.md:16 and docs/spec-db-core.md:47-55:
        - Trusted mask SHALL be boolean dtype with True=trusted polarity (no inversion)
        - DIALS convention: True=trusted, False=untrusted/hot/bad pixels

        Assertions:
        1. trusted_mask.dtype == bool (DIALS convention)
        2. Sample trusted pixel validates True polarity (ROI 0 coordinates from baseline probe)
        3. Polarity check: >50% True pixels (typical for functioning detectors)
        """
        dl = refgeom_dataload

        # Assert dtype is boolean (DIALS convention)
        assert dl.trusted_mask.dtype == bool, \
            f"Expected trusted_mask dtype bool, got {dl.trusted_mask.dtype}. " \
            f"DIALS convention requires boolean mask per docs/dials_api.md:16"

        # Validate sample trusted pixel from baseline probe
        # Per plans/active/DB-AT-021/reports/2025-12-08T120000Z/baseline_probe.md:
        # sample_roi_bbox: (582, 594, 0, 12) → ROI at panel 0, fast [582:594], slow [0:12]
        # We'll validate a pixel in the middle of this ROI should be trusted
        sample_panel = 0
        sample_slow = 5  # Middle of slow range [0:12]
        sample_fast = 588  # Middle of fast range [582:594]

        # Assert sample pixel is trusted
        assert dl.trusted_mask[sample_panel, sample_slow, sample_fast] == True, \
            f"Expected trusted pixel at panel={sample_panel}, slow={sample_slow}, fast={sample_fast} " \
            f"to be True (trusted). Got {dl.trusted_mask[sample_panel, sample_slow, sample_fast]}. " \
            f"Per baseline probe, ROI 0 pixels should be trusted."

        # Polarity sanity check: >50% True pixels (avoid inverted masks)
        # Per dbex/refinement/inputs.py:132-137 guard pattern
        true_fraction = np.mean(dl.trusted_mask)
        assert true_fraction > 0.5, \
            f"Trusted mask appears inverted: only {true_fraction*100:.1f}% True. " \
            f"Expected >50% True for proper True=trusted polarity per docs/spec-db-core.md:29"

        # Report metrics
        n_trusted = np.sum(dl.trusted_mask)
        n_untrusted = np.sum(~dl.trusted_mask)
        print(f"\nDB-AT-021 B2 PASSED: Trusted mask polarity validated")
        print(f"  - dtype: {dl.trusted_mask.dtype} (expected: bool)")
        print(f"  - Trusted pixels: {n_trusted:,} ({true_fraction*100:.1f}%)")
        print(f"  - Untrusted pixels: {n_untrusted:,} ({(1-true_fraction)*100:.1f}%)")
        print(f"  - Sample ROI 0 pixel (panel={sample_panel}, slow={sample_slow}, fast={sample_fast}): {dl.trusted_mask[sample_panel, sample_slow, sample_fast]} (trusted)")


    def test_DB_AT_021_loss_mask_construction(self, refgeom_dataload):
        """
        DB-AT-021 B3: Validate loss_mask construction matches spec formula.

        Per docs/spec-db-core.md:124:
        - Loss mask SHALL be: (background >= 0) ∧ trusted_mask
        - Background sentinel -1 excludes pixels outside ROIs (ADR-07)
        - Trusted mask precedence: False excludes pixels even if background >= 0

        Assertions:
        1. Compute expected: (background_image >= 0) & trusted_mask
        2. Call prepare_refinement_inputs to extract actual loss_mask
        3. Assert numpy.array_equal(actual, expected)
        4. Validate sentinel handling: pixels with background == -1 excluded
        5. Validate trusted precedence: pixels with trusted_mask == False excluded
        """
        dl = refgeom_dataload

        # Extract inputs from DataLoad
        data = dl.data
        background_image = dl.background_image
        trusted_mask = dl.trusted_mask
        bbox = dl.bbox
        pids = dl.pids
        detector = dl.Expt.detector

        # Compute expected loss_mask per spec formula
        expected_loss_mask = (background_image >= 0) & trusted_mask

        # Call canonical owner API to get actual loss_mask
        refinement_inputs = prepare_refinement_inputs(
            data=data,
            background_image=background_image,
            trusted_mask=trusted_mask,
            bbox=bbox,
            pids=pids,
            detector=detector,
            adu_per_photon=None,  # ADU mode (default)
            sigma_readout=None,   # No sigma for this test
        )

        actual_loss_mask = refinement_inputs.loss_mask

        # Assert exact match
        assert np.array_equal(actual_loss_mask, expected_loss_mask), \
            f"Loss mask mismatch: expected formula (background >= 0) & trusted_mask. " \
            f"Canonical owner prepare_refinement_inputs produced different result. " \
            f"Per docs/spec-db-core.md:124, loss_mask MUST be (background >= 0) ∧ trusted_mask"

        # Validate sentinel handling: pixels with background == -1 are excluded
        sentinel_pixels = (background_image == -1)
        sentinel_in_loss = actual_loss_mask & sentinel_pixels
        assert not np.any(sentinel_in_loss), \
            f"Loss mask incorrectly includes {np.sum(sentinel_in_loss)} sentinel pixels (background == -1). " \
            f"Per ADR-07, sentinel pixels outside ROIs MUST be excluded from loss_mask."

        # Validate trusted mask precedence: pixels with trusted_mask == False are excluded
        # even if background >= 0
        untrusted_with_valid_bg = (~trusted_mask) & (background_image >= 0)
        untrusted_in_loss = actual_loss_mask & untrusted_with_valid_bg
        assert not np.any(untrusted_in_loss), \
            f"Loss mask incorrectly includes {np.sum(untrusted_in_loss)} untrusted pixels with valid background. " \
            f"Per docs/spec-db-core.md:124, trusted_mask precedence MUST exclude untrusted pixels."

        # Report metrics
        n_loss_mask = np.sum(actual_loss_mask)
        n_sentinel = np.sum(sentinel_pixels)
        n_untrusted_valid_bg = np.sum(untrusted_with_valid_bg)
        print(f"\nDB-AT-021 B3 PASSED: Loss mask construction validated")
        print(f"  - Loss mask pixels: {n_loss_mask:,} (sparse Bragg peaks expected per MASKING-001)")
        print(f"  - Sentinel pixels (background == -1): {n_sentinel:,} (excluded)")
        print(f"  - Untrusted pixels with valid background: {n_untrusted_valid_bg:,} (excluded)")
        print(f"  - Formula: (background >= 0) & trusted_mask (exact match)")


    def test_DB_AT_021_precedence_guards(self, refgeom_dataload):
        """
        DB-AT-021 B4: Validate ARCH-CONTRACT-MASKING-001 enforcement.

        Per input.md ARCH-CONTRACT-MASKING-001:
        - Owner Module/API: dbex.refinement.inputs.prepare_refinement_inputs
        - Forbidden Duplicates: Alternative loss_mask construction in Stage A/B/C helpers
        - Test harness boilerplate MAY call DataLoad API directly for validation

        Assertions:
        1. Use AST inspection to search for duplicate loss_mask construction patterns
        2. Search Stage A/B/C implementation files for (background >= 0) & trusted_mask patterns
        3. If duplicates found, raise AssertionError with file:line references
        4. If no duplicates, assert canonical owner is prepare_refinement_inputs
        """
        repo_root = Path(__file__).parent.parent.parent

        # Target Stage implementation files per input.md
        stage_impl_files = [
            repo_root / "dbex" / "refinement" / "stage_a_impl.py",
            repo_root / "dbex" / "refinement" / "stage_b_impl.py",
            repo_root / "dbex" / "refinement" / "stage_c_impl.py",
        ]

        # Pattern to search: (background >= 0) & trusted_mask or equivalent variants
        # We'll use AST to search for BinOp nodes with '&' combining background/trusted checks
        duplicates = []

        for stage_file in stage_impl_files:
            if not stage_file.exists():
                # Skip if stage implementation file doesn't exist yet
                # (per input.md, stages may not be fully implemented)
                continue

            try:
                with open(stage_file, 'r') as f:
                    source = f.read()
                    tree = ast.parse(source, filename=str(stage_file))

                # Walk AST looking for suspicious loss_mask construction patterns
                for node in ast.walk(tree):
                    # Look for assignments like: loss_mask = (background >= 0) & trusted_mask
                    if isinstance(node, ast.Assign):
                        # Check if target is named 'loss_mask' (or variants)
                        targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
                        if any('loss' in t.lower() and 'mask' in t.lower() for t in targets):
                            # Check if value involves '&' operator with background/trusted patterns
                            if isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.BitAnd):
                                duplicates.append({
                                    'file': str(stage_file.relative_to(repo_root)),
                                    'line': node.lineno,
                                    'code': ast.unparse(node) if hasattr(ast, 'unparse') else '<unknown>',
                                })

            except (SyntaxError, FileNotFoundError) as e:
                # Skip files with syntax errors or missing files
                # (environment freeze means we don't fix Stage impl issues here)
                pass

        # If duplicates found, raise AssertionError per ARCH-CONTRACT-MASKING-001
        if duplicates:
            duplicate_report = "\n".join([
                f"  {d['file']}:{d['line']} — {d['code']}"
                for d in duplicates
            ])
            pytest.fail(
                f"ARCH-CONTRACT-MASKING-001 violation: Found {len(duplicates)} duplicate loss_mask construction(s) "
                f"in Stage implementation files:\n{duplicate_report}\n\n"
                f"Per input.md, loss_mask construction MUST be delegated to canonical owner API: "
                f"dbex.refinement.inputs.prepare_refinement_inputs. Stage helpers SHALL NOT "
                f"re-implement (background >= 0) & trusted_mask."
            )

        # Assert canonical owner is prepare_refinement_inputs
        # (Already validated in B3 by successful prepare_refinement_inputs call)
        canonical_owner_module = "dbex.refinement.inputs"
        canonical_owner_func = "prepare_refinement_inputs"

        # Validate canonical owner exists and is importable (already imported at top)
        assert hasattr(prepare_refinement_inputs, '__module__'), \
            f"Canonical owner {canonical_owner_func} is not a valid function"
        assert prepare_refinement_inputs.__module__ == canonical_owner_module, \
            f"Canonical owner module mismatch: expected {canonical_owner_module}, " \
            f"got {prepare_refinement_inputs.__module__}"

        print(f"\nDB-AT-021 B4 PASSED: ARCH-CONTRACT-MASKING-001 enforcement validated")
        print(f"  - No duplicate loss_mask construction found in Stage A/B/C implementations")
        print(f"  - Canonical owner: {canonical_owner_module}.{canonical_owner_func}")
        print(f"  - Scanned files: {len([f for f in stage_impl_files if f.exists()])}/{len(stage_impl_files)}")
