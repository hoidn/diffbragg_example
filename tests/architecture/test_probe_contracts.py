"""Architecture enforcement tests for probe script contracts.

This module enforces the diagnostic script policy per prompts/supervisor.md:272-309
and ARCH-PROBE-FREEZE-001. It validates that plan-local probe scripts remain thin
wrappers and do not re-implement production semantics (mapping, physics, refinement).

Architecture Context:
- Growth Cap: plan-local scripts under plans/active/**/bin/*.py must not exceed 400 LOC
  unless explicitly allowlisted (unavoidable legacy scripts documented by plan ID).
- Shim Delegation: New thin-wrapper scripts must contain only imports + if __name__ block
  delegating to canonical owner modules (dbex.tools.*).

References:
- prompts/supervisor.md:254-309 (scriptization_policy + diagnostic_script_policy)
- plans/active/ARCH-PROBE-FREEZE-001/implementation.md:80-150 (Phase C guardrails)
- docs/architecture/data_telemetry_flow.md:42-118 (telemetry ownership)
- docs/architecture/module_map.md:30-95 (module ownership boundaries)

Phase C.1 Deliverables:
1. test_plan_bin_growth_cap: walk plans/active/**/bin/*.py, fail when script exceeds
   400 LOC unless in GROWTH_CAP_EXCEPTIONS allowlist. Allowlist seeds with current
   offenders (13 paths as of 2025-12-31).
2. test_probe_shims_delegate_to_owner_clis: parse shim scripts (embed_sigma_external_lookup.py,
   compare_mapping_dataset_metrics.py, capture_smoke_calibration.py) and assert they
   contain only import statements + if __name__ block calling owner CLI. Fail if any
   function/class definitions creep in.

Maintenance:
- When adding entries to GROWTH_CAP_EXCEPTIONS, document with plan ID and cleanup intent.
- When refactoring a shadow pipeline, remove its allowlist entry once the script is reduced
  to thin-wrapper form or retired.
- Run this test before accepting new plan-local scripts: `pytest -vv tests/architecture/test_probe_contracts.py`
- See docs/TESTING_GUIDE.md for execution workflow and artifact policies.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Set

import pytest

# Repository root for file discovery
REPO_ROOT = Path(__file__).parent.parent.parent

# Growth cap exceptions: legacy scripts exceeding 400 LOC that are awaiting migration.
# Allowlist is explicit so new scripts cannot bypass the cap silently.
# Each entry is commented with the plan ID driving cleanup.
GROWTH_CAP_EXCEPTIONS: Set[str] = {
    # ARCH-SIM-CONSTRUCTION-001 — simulator parity instrumentation (migration deferred)
    "plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulate_forward_once_vs_reconstruction.py",
    "plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulator_outputs.py",
    "plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline_legacy.py",
    # ARCH-SIM-HKL-BOUNDS-001 — HKL projection diagnostics (migration deferred)
    "plans/active/ARCH-SIM-HKL-BOUNDS-001/bin/inspect_hkl_projection.py",
    # DIAG-NANOBRAGG-OVERSAMPLE-001 — oversample mismatch tracing (migration deferred)
    "plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/bin/trace_simulator_mismatch.py",
    # PORTFOLIO-STATUS — plan inventory reporting (migration deferred)
    "plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py",
    # TOOLING-VIS-001 — visualization tooling (migration deferred)
    "plans/active/TOOLING-VIS-001/bin/compare_mapping_forward_cpu_gpu.py",
    "plans/active/TOOLING-VIS-001/bin/compare_stage_a_mapping_parity.py",
    "plans/active/TOOLING-VIS-001/bin/generate_stage_a_refgeom_roi_triptychs_adam.py",
    "plans/active/TOOLING-VIS-001/bin/probe_mapping_roi_triptychs.py",
    "plans/active/TOOLING-VIS-001/bin/probe_scale_chain.py",
    # TORCH-REFINE-002E — crystal matrix parity diagnostics (migration deferred)
    "plans/active/TORCH-REFINE-002E/bin/compare_mapping_vs_stage_a_forward.py",
    "plans/active/TORCH-REFINE-002E/bin/probe_crystal_matrix_parity.py",
}

# Maximum LOC for plan-local scripts (excluding allowlist entries)
MAX_LOC = 400

# Shim scripts that must delegate to canonical owner modules (Phase B deliverables)
SHIM_SCRIPTS: List[Path] = [
    REPO_ROOT / "plans/active/PHYSICS-LOSS-001/bin/embed_sigma_external_lookup.py",
    REPO_ROOT / "plans/active/TOOLING-VIS-001/bin/compare_mapping_dataset_metrics.py",
    REPO_ROOT / "plans/active/TOOLING-VIS-001/bin/capture_smoke_calibration.py",
]


def _count_lines(path: Path) -> int:
    """Count non-blank, non-comment lines in a Python file.

    Args:
        path: Path to Python file.

    Returns:
        Line count (excluding blank lines and standalone comment lines).
    """
    with path.open("r", encoding="utf-8") as f:
        lines = f.readlines()

    count = 0
    for line in lines:
        stripped = line.strip()
        # Skip blank lines and lines that are purely comments
        if stripped and not stripped.startswith("#"):
            count += 1
    return count


def _find_plan_bin_scripts() -> List[Path]:
    """Find all Python scripts under plans/active/**/bin/*.py.

    Returns:
        List of Path objects sorted for determinism.
    """
    pattern = "plans/active/**/bin/*.py"
    scripts = sorted(REPO_ROOT.rglob(pattern))
    # Filter to ensure we only get .py files (rglob may match directories)
    scripts = [p for p in scripts if p.is_file() and p.suffix == ".py"]
    return scripts


def _parse_ast_and_check_shim(path: Path) -> tuple[bool, str]:
    """Parse script AST and check if it matches thin-wrapper structure.

    A valid thin wrapper contains:
    - import statements
    - optional sys.path manipulation (for legacy compatibility)
    - if __name__ == "__main__": block that calls a canonical owner CLI

    Invalid thin wrapper has:
    - function definitions (FunctionDef, AsyncFunctionDef)
    - class definitions (ClassDef)
    - top-level statements beyond imports/path manipulation/if-main

    Args:
        path: Path to Python file.

    Returns:
        (is_valid, message) tuple. is_valid=True if shim structure is valid,
        message describes any violations.
    """
    with path.open("r", encoding="utf-8") as f:
        source = f.read()

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as e:
        return False, f"Syntax error: {e}"

    violations = []
    has_if_main = False

    for node in ast.walk(tree):
        # Reject function definitions
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            violations.append(f"Function definition '{node.name}' at line {node.lineno}")
        # Reject class definitions
        elif isinstance(node, ast.ClassDef):
            violations.append(f"Class definition '{node.name}' at line {node.lineno}")
        # Check for if __name__ == "__main__": pattern
        elif isinstance(node, ast.If):
            # Check if this is the top-level if-main idiom
            if isinstance(node.test, ast.Compare):
                if (
                    isinstance(node.test.left, ast.Name)
                    and node.test.left.id == "__name__"
                    and any(
                        isinstance(comp, ast.Constant) and comp.value == "__main__"
                        for comp in node.test.comparators
                    )
                ):
                    has_if_main = True

    if violations:
        return False, "; ".join(violations)

    if not has_if_main:
        return False, "Missing 'if __name__ == \"__main__\":' block"

    return True, "Valid thin wrapper (imports + if-main delegation only)"


def test_plan_bin_growth_cap():
    """Enforce 400 LOC growth cap on plan-local probe scripts.

    Validates that scripts under plans/active/**/bin/*.py do not exceed MAX_LOC
    unless explicitly allowlisted in GROWTH_CAP_EXCEPTIONS.

    Rationale (prompts/supervisor.md:282-286):
    If a plan-local script exceeds ~400 LOC OR is extended in ≥2 loops OR contains
    re-derived semantics, further extension is forbidden. Scripts must either:
    (a) be promoted to scripts/tools/ under a harness initiative with pytest, or
    (b) stop using it and instrument inside the real production call path.

    Acceptance:
    - All scripts ≤ MAX_LOC or in GROWTH_CAP_EXCEPTIONS.
    - Allowlist is documented with plan IDs for cleanup traceability.

    Failure:
    - Script exceeds MAX_LOC and is not allowlisted.
    - Emit actionable message: file path, actual LOC, threshold, and allowlist hint.
    """
    scripts = _find_plan_bin_scripts()
    assert len(scripts) > 0, "No plan-local scripts found under plans/active/**/bin/"

    violations = []

    for script in scripts:
        # Normalize path for allowlist comparison
        rel_path = script.relative_to(REPO_ROOT).as_posix()

        # Count lines (exclude blank/comment-only)
        loc = _count_lines(script)

        # Check if exceeds threshold and not allowlisted
        if loc > MAX_LOC and rel_path not in GROWTH_CAP_EXCEPTIONS:
            violations.append(
                f"{rel_path}: {loc} LOC (exceeds {MAX_LOC} LOC threshold, not in GROWTH_CAP_EXCEPTIONS)"
            )

    if violations:
        msg = (
            f"Growth cap violations ({len(violations)} scripts exceed {MAX_LOC} LOC):\n"
            + "\n".join(f"  - {v}" for v in violations)
            + f"\n\nIf these scripts are legacy migrations in progress, add them to "
            f"GROWTH_CAP_EXCEPTIONS in {__file__} with plan ID documentation. "
            f"Otherwise, refactor to thin wrapper or promote to scripts/tools/."
        )
        pytest.fail(msg)


def test_probe_shims_delegate_to_owner_clis():
    """Enforce shim scripts delegate to canonical owner CLIs without extra logic.

    Validates that Phase B shim scripts (embed_sigma_external_lookup.py,
    compare_mapping_dataset_metrics.py, capture_smoke_calibration.py) remain minimal:
    - imports only
    - optional sys.path manipulation (legacy compatibility)
    - if __name__ == "__main__": block calling canonical owner (e.g., dbex.tools.*.main)

    Forbidden:
    - function definitions (FunctionDef, AsyncFunctionDef)
    - class definitions (ClassDef)
    - re-implementing business logic

    Rationale (prompts/supervisor.md:275-280):
    Plan-local scripts may only:
    (a) call existing dbex entrypoints/APIs,
    (b) load fixtures/data,
    (c) compute simple measurements (shape/dtype/device/sum/min/max/corr/ratios),
    (d) write artifacts.
    They may NOT implement mapping/HKL grids, ROI selection/matching, physics factors,
    refinement logic, or Stage A semantics.

    Acceptance:
    - All SHIM_SCRIPTS pass AST validation (no function/class definitions).
    - Each shim contains if __name__ == "__main__": block.

    Failure:
    - Shim contains function/class definitions.
    - Emit actionable message: file path, violation type (function/class name + line).
    """
    assert len(SHIM_SCRIPTS) > 0, "No shim scripts configured in SHIM_SCRIPTS"

    violations = []

    for script in SHIM_SCRIPTS:
        if not script.exists():
            violations.append(f"{script.relative_to(REPO_ROOT).as_posix()}: file not found")
            continue

        is_valid, msg = _parse_ast_and_check_shim(script)

        if not is_valid:
            violations.append(
                f"{script.relative_to(REPO_ROOT).as_posix()}: {msg}"
            )

    if violations:
        msg = (
            f"Shim structure violations ({len(violations)} scripts):\n"
            + "\n".join(f"  - {v}" for v in violations)
            + f"\n\nShim scripts must contain only imports + if __name__ block delegating to "
            f"canonical owner modules (dbex.tools.*). Remove function/class definitions and "
            f"migrate business logic to owner modules per ARCH-PROBE-FREEZE-001 Phase B."
        )
        pytest.fail(msg)
