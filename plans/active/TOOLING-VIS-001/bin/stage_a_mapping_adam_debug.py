#!/usr/bin/env python3
"""
TOOLING-VIS-001 — Stage A Mapping Adam Debug Driver (CLI Shim).

Thin argparse shim over dbex.tools.stage_a_adam module.
Extracted during ARCH-REFACTOR-001 Phase D D2.2.

Implements the instrumentation described in
`plans/active/TOOLING-VIS-001/stage_a_mapping_adam_debug_plan.md` and the
Phase D zero-point realignment work in
`plans/active/TOOLING-VIS-001/stage_a_mapping_alignment_plan.md`:

- Phase 0: Environment lockdown + deterministic debug run directory.
- Phase 1: Forward-model equality probe between:
    * Mapping Bragg stack (`bragg_zero_iter` from `simulate_forward_once`)
    * Stage-A "no-op" simulator using the same HKL grid + calibration.
- Phase 2: Loss-definition alignment between mapping diagnostics and the
    Stage-A variance-weighted chi-squared loss.
- Phase 3: Zero-point alignment probe in which the Stage-A Adam core
    reproduces `bragg_zero_iter` at zero parameters (geometry/scale).
- Phase 4: Single-step Adam experiment on full Stage A parameters
    (scale + unit cell + orientation) to inspect the first optimizer step.
- Phase 5: Block-wise DoF sweeps (scale-only, scale+cell, scale+orientation,
    full) gated on a passing zero-point check.

Artifacts are written under:

    plans/active/TOOLING-VIS-001/reports/stage_a_refgeom_adam_debug/<timestamp>/

with JSON files:
    - forward_model_probe.json
    - loss_alignment.json
    - zero_point_check.json
    - single_step_adam.json
    - block_dof_results.json
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Add project root to Python path (necessary for bin scripts)
REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dbex.tools.stage_a_adam import (
    StageADebugConfig,
    build_dataload,
    create_debug_run_dir,
    run_blockwise_dof_experiments,
    run_forward_model_probe,
    run_gradient_probe,
    run_loss_alignment_probe,
    run_single_step_adam,
    run_zero_point_check,
    setup_environment,
    write_commands_txt,
)
from dbex.vis import build_mapping_stage_a_context


def parse_args() -> StageADebugConfig:
    """Parse CLI arguments into StageADebugConfig dataclass."""
    parser = argparse.ArgumentParser(
        description="Stage A mapping Adam debug driver (TOOLING-VIS-001)."
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="phases",
        choices=["phases", "gradient_probe"],
        help=(
            "Execution mode: 'phases' runs selected debug phases (legacy behavior); "
            "'gradient_probe' evaluates chi-squared and per-DoF gradients at the "
            "mapping zero point (TORCH-REFINE-002E Phase B1)."
        ),
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="Torch device for simulation (default: cpu).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20251121,
        help="Random seed for debug run (default: 20251121).",
    )
    parser.add_argument(
        "--adam-steps",
        type=int,
        default=10,
        help="Number of Adam steps for Phase 5 block-wise experiments (default: 10).",
    )
    parser.add_argument(
        "--adam-lr",
        type=float,
        default=1e-4,
        help="Learning rate for Phase 4 Adam experiment (default: 1e-4).",
    )
    parser.add_argument(
        "--u-matrix-lr",
        type=float,
        default=1e-5,
        help=(
            "Learning rate for Adam optimizer when --use-u-matrix is enabled "
            "(default: 1e-5, per CONVERGENCE-001 Phase C1 root cause). "
            "Only applies when --use-u-matrix is True and --use-lbfgs is False."
        ),
    )
    parser.add_argument(
        "--phases",
        type=str,
        default="1,2,4",
        help=(
            "Comma-separated list of phases to run "
            "(subset of 1,2,3,4,5; 3=zero-point alignment probe)."
        ),
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default=None,
        help=(
            "Override output directory (absolute path or relative to repo root). "
            "If not provided, a timestamped directory is created under "
            "plans/active/TOOLING-VIS-001/reports/stage_a_refgeom_adam_debug/<timestamp>/ "
            "for phases mode, or under the initiative-specific reports directory for "
            "gradient_probe mode."
        ),
    )
    parser.add_argument(
        "--dof-variants",
        type=str,
        default=None,
        help=(
            "Comma-separated list of DoF variants to run in Phase 5 "
            "(subset of A_scale_only,B_scale_plus_cell,C_scale_plus_orientation,D_full). "
            "If not provided, all variants are run."
        ),
    )
    parser.add_argument(
        "--use-u-matrix",
        action="store_true",
        help=(
            "Enable quaternion U-matrix parameterization for Stage A orientation "
            "(TORCH-GEOMETRY-PARITY-002). When enabled, refines orientation via 4-DOF "
            "quaternion → rotation matrix → A* instead of cell+misset decomposition."
        ),
    )
    parser.add_argument(
        "--use-lbfgs",
        action="store_true",
        help=(
            "Use LBFGS optimizer instead of Adam for U-matrix path "
            "(TORCH-GEOMETRY-CONVERGENCE-001 Test B1). LBFGS eliminates momentum accumulation, "
            "uses line search for stability. Only applies when --use-u-matrix is enabled."
        ),
    )
    parser.add_argument(
        "--optimizer-steps",
        type=int,
        default=10,
        help="Number of optimizer steps (Adam or LBFGS). Default: 10.",
    )
    parser.add_argument(
        "--telemetry-dir",
        type=str,
        default=None,
        help=(
            "Directory for per-step telemetry JSON files (TORCH-GEOMETRY-CONVERGENCE-001 Phase A1). "
            "When set, enables instrumentation of quaternion U-matrix closure to emit parameter, "
            "gradient, loss, and variance metrics for convergence diagnosis. Relative paths are "
            "resolved relative to --out-dir if provided, otherwise relative to the current directory."
        ),
    )

    args = parser.parse_args()

    # Parse phases list
    phases_list = [int(p.strip()) for p in args.phases.split(",") if p.strip()]

    # Parse dof_variants list
    dof_variants_list = None
    if args.dof_variants is not None:
        dof_variants_list = [v.strip() for v in args.dof_variants.split(",") if v.strip()]

    # Parse out_dir path
    out_dir = Path(args.out_dir) if args.out_dir is not None else None

    # Parse telemetry_dir path
    telemetry_dir = Path(args.telemetry_dir) if args.telemetry_dir is not None else None

    # Repo root (for dataload)
    repo_root = Path(__file__).resolve().parents[4]

    # Base output dir (for timestamped dirs)
    base_output_dir = repo_root / "plans" / "active" / "TOOLING-VIS-001" / "reports" / "stage_a_refgeom_adam_debug"

    return StageADebugConfig(
        repo_root=repo_root,
        device=args.device,
        seed=args.seed,
        mode=args.mode,
        phases=phases_list,
        adam_steps=args.adam_steps,
        adam_lr=args.adam_lr,
        u_matrix_lr=args.u_matrix_lr,
        out_dir=out_dir,
        dof_variants=dof_variants_list,
        use_u_matrix=args.use_u_matrix,
        use_lbfgs=args.use_lbfgs,
        optimizer_steps=args.optimizer_steps,
        telemetry_dir=telemetry_dir,
        base_output_dir=base_output_dir,
    )


def main(argv: List[str] | None = None) -> None:
    """Entry point - delegate to module functions."""
    config = parse_args()

    seed = setup_environment(config.seed, config.device)

    # Handle custom out_dir or create default timestamped directory
    if config.out_dir is not None:
        out_root = config.out_dir
        if not out_root.is_absolute():
            out_root = config.repo_root / out_root
        out_root.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    else:
        timestamp, out_root = create_debug_run_dir(config.base_output_dir)

    write_commands_txt(out_root, seed, sys.argv if argv is None else argv)

    dataload = build_dataload(config.repo_root)
    context = build_mapping_stage_a_context(dataload, device="cpu")

    if config.mode == "gradient_probe":
        # TORCH-REFINE-002E Phase B1: Gradient probe mode
        run_gradient_probe(
            dataload,
            context,
            device_str=config.device,
            out_dir=out_root,
        )
        print(
            f"[stage_a_mapping_adam_debug] Gradient probe completed "
            f"→ artifacts under {out_root}"
        )
    else:
        # Legacy phases mode
        phases_set = set(config.phases)

        zero_point_result: Dict[str, object] | None = None
        if 3 in phases_set or 4 in phases_set or 5 in phases_set:
            zero_point_result = run_zero_point_check(
                dataload,
                context,
                device_str=config.device,
                out_dir=out_root,
            )
            zero_ok = bool(zero_point_result.get("zero_point_ok", False))
            if not zero_ok:
                print(
                    "[stage_a_mapping_adam_debug] Zero-point check FAILED "
                    "(see zero_point_check.json); geometry phases will be skipped."
                )
                # If zero-point is not aligned, do not run geometry experiments.
                phases_set.discard(4)
                phases_set.discard(5)

        if 1 in phases_set:
            run_forward_model_probe(
                dataload,
                context,
                device_str=config.device,
                out_dir=out_root,
            )

        if 2 in phases_set:
            run_loss_alignment_probe(
                context,
                device_str=config.device,
                out_dir=out_root,
            )

        if 4 in phases_set:
            # Use U-matrix LR if U-matrix mode is enabled (CONVERGENCE-001 Phase C2)
            phase4_lr = config.u_matrix_lr if config.use_u_matrix else config.adam_lr
            run_single_step_adam(
                dataload,
                context,
                device_str=config.device,
                lr=phase4_lr,
                out_dir=out_root,
            )

        if 5 in phases_set:
            # Resolve telemetry_dir relative to out_root if it's a relative path
            telemetry_dir_resolved = None
            if config.telemetry_dir is not None:
                telemetry_p = config.telemetry_dir
                if not telemetry_p.is_absolute():
                    telemetry_dir_resolved = str(out_root / telemetry_p)
                else:
                    telemetry_dir_resolved = str(config.telemetry_dir)

            # Use U-matrix LR if U-matrix mode is enabled (CONVERGENCE-001 Phase C2)
            phase5_lr = config.u_matrix_lr if config.use_u_matrix else config.adam_lr
            run_blockwise_dof_experiments(
                dataload,
                context,
                device_str=config.device,
                n_steps=max(config.optimizer_steps, 0),
                lr=phase5_lr,
                out_dir=out_root,
                dof_variants=config.dof_variants,
                use_u_matrix=config.use_u_matrix,
                use_lbfgs=config.use_lbfgs,
                telemetry_output_dir=telemetry_dir_resolved,
            )

        # This script is debug-only; no exceptions here are converted to non-zero
        # exit codes beyond Python's defaults.
        print(
            f"[stage_a_mapping_adam_debug] Completed phases {sorted(phases_set)} "
            f"→ artifacts under {out_root} (timestamp={timestamp})"
        )


if __name__ == "__main__":
    main()
