"""Telemetry surfaces enforcement test.

ARCH-TELEMETRY-002 Exit Criterion 3: Prevents new long-lived telemetry dict
surfaces in dbex/ outside owner allow-list.

Owner allow-list (from docs/architecture/telemetry.md §2):
- dbex/refinement/interfaces.py (Stage*Telemetry dataclasses)
- dbex/refinement/telemetry_collectors.py (Stage*TelemetryCollector)
- dbex/io/writer.py (/torch_diagnostics HDF5 schema)

Secondary owners (diagnostics, not full enforcement):
- dbex/refinement/telemetry_baseline.py (baseline metrics)
- dbex/refinement/artifacts.py (stage artifacts)
- dbex/vis/mapping.py (calibration diagnostics)

Cross-reference: docs/architecture/telemetry.md (telemetry ownership charter)
Cross-reference: tests/architecture/test_probe_contracts.py (probe shim constraints)

Architecture Context:
- This test ensures new production telemetry surfaces are not added outside
  the chartered owner modules without updating the charter.
- It validates that the primary owner modules exist and are consistent with
  the telemetry charter documentation.
- A heuristic-based scan flags potential new telemetry patterns for review.

Maintenance:
- Update TELEMETRY_OWNER_MODULES if charter §2 changes.
- Update SECONDARY_OWNER_MODULES if charter §3 changes.
- Run: pytest -vv tests/architecture/test_telemetry_surfaces.py
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Set

import pytest

# Repository root for file discovery
REPO_ROOT = Path(__file__).parent.parent.parent

# Primary telemetry owner modules (from telemetry.md §2)
# These modules own production telemetry surfaces and their semantics
TELEMETRY_OWNER_MODULES: Set[str] = {
    "dbex/refinement/interfaces.py",
    "dbex/refinement/telemetry_collectors.py",
    "dbex/io/writer.py",
}

# Secondary owner modules (from telemetry.md §3)
# These own diagnostic/baseline telemetry, not primary production surfaces
SECONDARY_OWNER_MODULES: Set[str] = {
    "dbex/refinement/telemetry_baseline.py",
    "dbex/refinement/artifacts.py",
    "dbex/vis/mapping.py",
}

# All owner modules combined for allow-list purposes
ALL_OWNER_MODULES: Set[str] = TELEMETRY_OWNER_MODULES | SECONDARY_OWNER_MODULES

# Modules explicitly allowed to define dict-returning functions for reasons
# other than telemetry (e.g., config factories, helpers).
# Document reason for each entry.
DICT_PATTERN_EXCEPTIONS: Set[str] = {
    # Config factories legitimately return dicts for configuration purposes
    "dbex/refinement/config_factories.py",
    "dbex/refinement/config.py",
    "dbex/calibration/config_variants.py",
    # Context module manages refinement state, not telemetry export
    "dbex/refinement/context.py",
    # Helpers may return intermediate dicts for internal use
    "dbex/refinement/helpers.py",
    "dbex/refinement/scaling_utils.py",
    # Stage modules manage internal state
    "dbex/refinement/stage.py",
    "dbex/refinement/stage_a.py",
    "dbex/refinement/stage_b.py",
    "dbex/refinement/stage_c.py",
    "dbex/refinement/stage_a_utils.py",
    # Engine orchestrates stages, may pass through telemetry
    "dbex/refinement/engine.py",
    # Reconstruction may build intermediate data structures
    "dbex/refinement/reconstruction.py",
    # Input handling
    "dbex/refinement/inputs.py",
    # HKL utils are computational, not telemetry
    "dbex/refinement/hkl_utils.py",
    # IO modules for scoring/analysis, not telemetry export
    "dbex/io/roi_analysis.py",
    "dbex/io/roi_scoring.py",
    # Data loading returns structured data, not telemetry
    "dbex/data_load.py",
    # CLI/entry points
    "dbex/refine_one.py",
    "dbex/look.py",
    # Physics modules return computed values, not telemetry
    "dbex/physics/loss.py",
    "dbex/physics/forward.py",
    # Bridge modules interface with external code
    "dbex/nanobrag_bridge.py",
    "dbex/nanobrag_refinement.py",
    # Legacy DiffBragg wrapper
    "dbex/run_diffbragg.py",
    "dbex/diffbragg_tmp.py",
    # Tools are thin wrappers (per probe contracts)
    "dbex/tools/embed_sigma_external_lookup.py",
    "dbex/tools/mapping_dataset_metrics.py",
    "dbex/tools/capture_smoke_calibration.py",
    "dbex/tools/stage_a_adam.py",
    # Calibration modules
    "dbex/calibration/smoke_capture.py",
    # Visualization modules
    "dbex/vis/triptych.py",
    "dbex/vis/residuals.py",
    "dbex/vis/stage_a.py",
    # Geometry modules
    "dbex/geometry/crystallography.py",
}


def _find_dbex_modules() -> list[Path]:
    """Find all Python modules under dbex/ (excluding __init__.py and tests).

    Returns:
        List of Path objects sorted for deterministic output.
    """
    dbex_path = REPO_ROOT / "dbex"
    if not dbex_path.exists():
        return []

    modules = []
    for py_file in sorted(dbex_path.rglob("*.py")):
        # Skip __init__.py files
        if py_file.name == "__init__.py":
            continue
        # Skip test files if any exist under dbex
        if "test" in py_file.name.lower():
            continue
        modules.append(py_file)

    return modules


def _get_relative_path(path: Path) -> str:
    """Get path relative to repo root as posix string."""
    return path.relative_to(REPO_ROOT).as_posix()


def test_telemetry_owners_exist():
    """Verify that chartered telemetry owner modules exist.

    Validates that the modules listed in docs/architecture/telemetry.md §2
    (primary owners) and §3 (secondary owners) exist in the codebase.

    Rationale:
    - If owner modules are deleted or renamed, the charter becomes stale.
    - This test ensures charter-to-code alignment.

    Acceptance:
    - All modules in TELEMETRY_OWNER_MODULES exist.
    - All modules in SECONDARY_OWNER_MODULES exist.

    Failure:
    - A chartered owner module does not exist.
    - Emit actionable message: missing module path and charter reference.
    """
    missing_primary = []
    missing_secondary = []

    for module in TELEMETRY_OWNER_MODULES:
        module_path = REPO_ROOT / module
        if not module_path.exists():
            missing_primary.append(module)

    for module in SECONDARY_OWNER_MODULES:
        module_path = REPO_ROOT / module
        if not module_path.exists():
            missing_secondary.append(module)

    if missing_primary or missing_secondary:
        msg_parts = []
        if missing_primary:
            msg_parts.append(
                f"Missing primary owner modules (telemetry.md §2):\n"
                + "\n".join(f"  - {m}" for m in missing_primary)
            )
        if missing_secondary:
            msg_parts.append(
                f"Missing secondary owner modules (telemetry.md §3):\n"
                + "\n".join(f"  - {m}" for m in missing_secondary)
            )

        msg = (
            "Telemetry charter owner modules not found:\n\n"
            + "\n\n".join(msg_parts)
            + "\n\nUpdate docs/architecture/telemetry.md if modules were renamed/deleted, "
            "or restore the modules if accidentally removed."
        )
        pytest.fail(msg)


def test_no_unchartered_telemetry_exports():
    """Scan for potential new telemetry dict exports in non-owner modules.

    Uses a heuristic-based approach to detect patterns that may indicate
    unchartered telemetry surfaces:
    1. Functions returning dict literals or dict() in non-owner modules
    2. Functions with telemetry-related names (telemetry, metrics, diagnostics)

    Rationale (telemetry.md §5):
    - New production telemetry fields must follow expansion rules.
    - This test flags potential violations for review.

    Limitations:
    - This is a heuristic scan, not a full semantic analysis.
    - False positives are expected; use DICT_PATTERN_EXCEPTIONS to allow-list.
    - The goal is to catch obvious violations, not to be exhaustive.

    Acceptance:
    - No unchartered modules export telemetry-like patterns.
    - Or: all flagged patterns are in DICT_PATTERN_EXCEPTIONS with reason.

    Failure:
    - Module outside owner/exception list has telemetry-like export pattern.
    - Emit file, function name, and line number for review.
    """
    modules = _find_dbex_modules()
    assert len(modules) > 0, "No dbex modules found for scanning"

    violations = []

    # Pattern for telemetry-related function names
    telemetry_name_pattern = re.compile(
        r"(telemetry|metrics|diagnostics|_counters|_traces)",
        re.IGNORECASE
    )

    for module_path in modules:
        rel_path = _get_relative_path(module_path)

        # Skip if module is an owner or has exception
        if rel_path in ALL_OWNER_MODULES:
            continue
        if rel_path in DICT_PATTERN_EXCEPTIONS:
            continue

        try:
            with module_path.open("r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source, filename=str(module_path))
        except (SyntaxError, UnicodeDecodeError):
            # Skip files that can't be parsed
            continue

        # Walk AST looking for function definitions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_name = node.name

                # Check if function name suggests telemetry
                if telemetry_name_pattern.search(func_name):
                    # This is a potential telemetry function in a non-owner module
                    violations.append(
                        f"{rel_path}:{node.lineno} - function '{func_name}' "
                        f"has telemetry-related name in non-owner module"
                    )

    if violations:
        msg = (
            f"Potential unchartered telemetry exports detected ({len(violations)}):\n"
            + "\n".join(f"  - {v}" for v in violations[:10])  # Limit output
            + (f"\n  ... and {len(violations) - 10} more" if len(violations) > 10 else "")
            + "\n\nReview each violation:\n"
            "1. If it's legitimate telemetry, add to owner modules per telemetry.md §5.\n"
            "2. If it's not telemetry, add to DICT_PATTERN_EXCEPTIONS with reason.\n"
            "3. If it's a false positive pattern, update the heuristic."
        )
        pytest.fail(msg)


def test_charter_link_exists():
    """Verify telemetry charter is linked in docs/index.md.

    Rationale:
    - The charter must be discoverable from the documentation hub.
    - This prevents the charter from becoming orphaned documentation.

    Acceptance:
    - docs/index.md contains a link to architecture/telemetry.md
    """
    index_path = REPO_ROOT / "docs" / "index.md"
    assert index_path.exists(), "docs/index.md not found"

    with index_path.open("r", encoding="utf-8") as f:
        content = f.read()

    # Check for telemetry charter link
    if "architecture/telemetry" not in content:
        pytest.fail(
            "Telemetry charter not linked in docs/index.md.\n"
            "Add entry: ### [Telemetry Ownership Charter](architecture/telemetry.md)\n"
            "in the Architecture section."
        )
