#!/usr/bin/env python3
"""Compatibility shim for mapping dataset metrics comparison.

DEPRECATED: This script is now a thin wrapper around the canonical owner module.

The logic for mapping dataset metrics comparison has been promoted to:
    dbex.tools.mapping_dataset_metrics

This shim exists for backward compatibility with existing automation and documentation.
New invocations should use:
    python -m dbex.tools.mapping_dataset_metrics [args]

Usage (via shim):
    DBEX_SMOKE_SIGMA_SOURCE=metadata \\
    DBEX_SMOKE_DETECTOR_SIZE=small \\
    KMP_DUPLICATE_LIB_OK=TRUE \\
    NANOBRAGG_DISABLE_COMPILE=1 \\
    python plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py \\
        --out-dir plans/active/TOOLING-VIS-001/reports/<timestamp>/mapping_dataset_metrics \\
        --cases metadata_raw metadata_calibrated

Data dependencies (per docs/data_dependency_manifest.md):
    - Reuses build_mapping_stage_a_context with controlled HKL/calibration overrides.
    - DBEX_SMOKE_* env vars configure the baseline fixture (sigma source, detector size).
    - Each case specification provides its own HKL path and calibration config path.
    - No ad-hoc forward code; all mapping contexts flow through the same canonical helper.

Migration notes (ARCH-PROBE-FREEZE-001):
    - Calibration variant helpers: dbex.calibration.config_variants
    - Dataset path resolution: dbex.calibration.config_variants.{resolve_dataset_paths, resolve_hkl_path, resolve_smoke_calibration_path}
    - Case definition, metrics computation, and CLI: dbex.tools.mapping_dataset_metrics
    - Importable runner: dbex.tools.mapping_dataset_metrics.run_mapping_dataset_metrics
"""

if __name__ == "__main__":
    # Delegate to canonical owner module
    from dbex.tools import mapping_dataset_metrics as tool
    tool.main()
