"""
Smoke calibration capture CLI.

Command-line interface for capturing smoke calibration bundles from metadata smoke
datasets. Exposes canonical CLI surface for calibration bundle generation per
docs/data_dependency_manifest.md:86-103.

Owner: dbex.tools (ARCH-PROBE-FREEZE-001)
Business Logic Owner: dbex.calibration.smoke_capture

Usage:
    libtbx.python -m dbex.tools.capture_smoke_calibration \
        --expt sp.proc/idx-0000_sigma_metadata.expt \
        --refl refGeom.refl \
        --mask 747_mask.pkl \
        --mtz scaled.mtz \
        --out-config sp.proc/calibration/config_torch_smoke.json \
        --manifest <artifacts-path>/smoke_calibration_manifest.json \
        --num-macro 3

Applied Findings:
- STAGEA-001 (Calibration provenance): Canonical CLI routes through owner module
- Diagnostic Script Policy (prompts/supervisor.md:272-309): CLI delegates to owner API
"""

import sys
import logging
from pathlib import Path
from argparse import ArgumentParser

from dbex.calibration.smoke_capture import capture_calibration_metadata


def main():
    """
    Main entry point for smoke calibration capture CLI.

    Parses command-line arguments and delegates to dbex.calibration.smoke_capture
    for business logic execution.
    """
    parser = ArgumentParser(
        description="Capture smoke calibration bundle from metadata smoke dataset",
        epilog="See docs/data_dependency_manifest.md:86-103 for bundle requirements"
    )
    parser.add_argument(
        "--expt",
        type=Path,
        required=True,
        help="Experiment file (e.g., sp.proc/idx-0000_sigma_metadata.expt)"
    )
    parser.add_argument(
        "--refl",
        type=Path,
        required=True,
        help="Reflections file (e.g., refGeom.refl)"
    )
    parser.add_argument(
        "--mtz",
        type=Path,
        required=True,
        help="Structure factors MTZ (e.g., scaled.mtz)"
    )
    parser.add_argument(
        "--mask",
        type=Path,
        required=True,
        help="Trusted mask pickle (e.g., 747_mask.pkl)"
    )
    parser.add_argument(
        "--out-config",
        type=Path,
        required=True,
        help="Output path for config_torch_smoke.json"
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Output path for manifest JSON"
    )
    parser.add_argument(
        "--refined-mtz-out",
        type=Path,
        default=None,
        help="Output path for DiffBragg-refined structure factors MTZ"
    )
    parser.add_argument(
        "--num-macro",
        type=int,
        default=3,
        help="Number of refinement macro cycles (default 3)"
    )

    args = parser.parse_args()

    # Setup logging
    logger = logging.getLogger("dbex.tools.capture_smoke_calibration")
    logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(console_handler)

    # Validate input files
    for input_file, name in [(args.expt, "experiment"), (args.refl, "reflections"),
                              (args.mtz, "MTZ"), (args.mask, "mask")]:
        if not input_file.exists():
            logger.error(f"Input {name} file not found: {input_file}")
            sys.exit(1)

    # Capture calibration via owner module
    try:
        calibration = capture_calibration_metadata(
            args.expt,
            args.refl,
            args.mtz,
            args.mask,
            args.out_config,
            args.manifest,
            refined_mtz_out_path=args.refined_mtz_out,
            num_macro=args.num_macro,
            repo_root=Path.cwd(),
            logger=logger
        )
        logger.info("Success!")
    except Exception as e:
        logger.error(f"Calibration capture failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
