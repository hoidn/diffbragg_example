#!/usr/bin/env python3
"""
Verify that Stage A mapping_context fixtures record the smoke calibration path
and non-unit spot_scale_override values (initiative: TOOLING-VIS-001, owner: galph)

Inputs:
    --artifacts: plans/active/TOOLING-VIS-001/reports/<timestamp>/
    --expected-calib: repo-relative or absolute path to config_torch_smoke.json
    --selectors: optional list of db_at_* directories to inspect (default: db_at_028 db_at_029)

Data deps: mapping_context_fixture.json emitted by DB-AT-028/029 fixtures
Outputs: stdout (pass/fail summary) and non-zero exit code on validation failure
Repro: python plans/active/TOOLING-VIS-001/bin/check_mapping_fixture_calibration.py --artifacts ... --expected-calib ...
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List


def load_fixture(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as exc:  # pragma: no cover - small utility
        raise RuntimeError(f"Invalid JSON payload in {path}: {exc}") from exc


def validate_fixture(
    fixture_path: Path,
    expected_calib: Path,
    selector: str,
) -> List[str]:
    errors: List[str] = []
    data = load_fixture(fixture_path)

    calib_path = data.get("calibration_path")
    if not calib_path:
        errors.append(f"{selector}: calibration_path missing or null in {fixture_path}")
    else:
        resolved_calib = Path(calib_path).resolve()
        if resolved_calib != expected_calib:
            errors.append(
                f"{selector}: calibration_path {resolved_calib} != expected {expected_calib}"
            )

    spot_scale = data.get("spot_scale_override")
    try:
        spot_scale_value = float(spot_scale)
    except (TypeError, ValueError):
        spot_scale_value = None
    if spot_scale_value is None or spot_scale_value <= 1.0:
        errors.append(
            f"{selector}: spot_scale_override={spot_scale} (expected large calibrated value > 1.0)"
        )

    sigma_prov = data.get("sigma_provenance") or data.get("sigma_source")
    if sigma_prov and "metadata" not in str(sigma_prov).lower():
        errors.append(
            f"{selector}: sigma provenance '{sigma_prov}' does not reflect metadata tiles"
        )

    return errors


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Check mapping_context fixtures for calibration wiring"
    )
    ap.add_argument(
        "--artifacts",
        required=True,
        type=Path,
        help="plans/active/TOOLING-VIS-001/reports/<timestamp>/ directory",
    )
    ap.add_argument(
        "--expected-calib",
        required=True,
        type=Path,
        help="Path to config_torch_smoke.json that should appear in diagnostics",
    )
    ap.add_argument(
        "--selectors",
        nargs="+",
        default=["db_at_028", "db_at_029"],
        help="List of db_at_* artifact directories to inspect",
    )
    args = ap.parse_args()

    artifacts_root = args.artifacts
    expected_calib = args.expected_calib.resolve()
    if not artifacts_root.exists():
        print(f"ERROR: artifacts directory not found: {artifacts_root}", file=sys.stderr)
        sys.exit(1)
    if not expected_calib.exists():
        print(f"ERROR: expected calibration file not found: {expected_calib}", file=sys.stderr)
        sys.exit(1)

    failures: List[str] = []
    for selector in args.selectors:
        fixture_path = artifacts_root / selector / "mapping_context_fixture.json"
        if not fixture_path.exists():
            failures.append(f"{selector}: missing fixture file {fixture_path}")
            continue
        failures.extend(validate_fixture(fixture_path, expected_calib, selector))

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}")
        sys.exit(1)

    print(
        "Calibration path + spot_scale_override validated for "
        f"{', '.join(args.selectors)} against {expected_calib}"
    )


if __name__ == "__main__":
    main()
