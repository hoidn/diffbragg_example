#!/usr/bin/env python3
"""
Debug bragg_full reconstruction from Stage A telemetry (initiative: ARCH-REFACTOR-001, owner: galph)

Inputs: Test selector (test_db_at_028_loss_scale_sanity or test_db_at_029_structure_parity)
Data deps: Test fixture data from smoke_small configuration
Outputs: Diagnostic artifacts under plans/active/ARCH-REFACTOR-001/reports/<timestamp>/debug_bragg/
Repro: python plans/active/ARCH-REFACTOR-001/bin/debug_bragg_reconstruction.py --test test_db_at_028
"""

import argparse
import json
import numpy as np
import torch
import sys
from pathlib import Path

# Add dbex to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", required=True, choices=["test_db_at_028", "test_db_at_029"], help="Test selector to debug")
    ap.add_argument("--output-dir", default="plans/active/ARCH-REFACTOR-001/reports/debug_bragg", help="Output directory for artifacts")
    args = ap.parse_args()

    from dbex.refinement.stage_a import StageA
    from dbex.refinement.engine import RefinementEngine
    from dbex.refinement.config import RefinementConfig
    from dbex.refinement.context import build_refinement_context
    from dbex.refinement.reconstruction import build_final_bragg_from_stage_a_telemetry
    from dbex.refinement.inputs import RefinementInputs
    from tests.dbex.fixtures.refgeom import fixture_refgeom_experiment
    from tests.dbex.fixtures.mapping_context import fixture_mapping_context_stage_a_smoke
    import os

    # Set environment
    os.environ["DBEX_SMOKE_SIGMA_SOURCE"] = "cli_override"
    os.environ["DBEX_SMOKE_DETECTOR_SIZE"] = "small"
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    os.environ["NANOBRAGG_DISABLE_COMPILE"] = "1"

    print(f"[DEBUG] Running test: {args.test}")
    print(f"[DEBUG] Output directory: {args.output_dir}")

    # Load fixtures
    print("[DEBUG] Loading fixtures...")
    refgeom_data = fixture_refgeom_experiment()
    mapping_context = fixture_mapping_context_stage_a_smoke(
        refgeom_experiment=refgeom_data,
        smoke_detector_size="small",
        smoke_sigma_source="cli_override"
    )

    # Extract components
    perturbed_detector = mapping_context.perturbed_geom["detector"]
    perturbed_beam = mapping_context.perturbed_geom["beam"]
    perturbed_crystal = mapping_context.perturbed_geom["crystal"]
    baseline_detector = mapping_context.baseline_geom["detector"]
    baseline_crystal = mapping_context.baseline_geom["crystal"]
    refinement_inputs = mapping_context.inputs
    hkl_grid = mapping_context.hkl_grid
    hkl_metadata = mapping_context.hkl_metadata

    # Build config
    print("[DEBUG] Building RefinementConfig...")
    config = RefinementConfig(
        device="cuda",
        dtype="float32",
        enable_stage_a_warm_cache=True,
        enable_stage_b=False,
        enable_stage_c=False,
        calibration_metadata=mapping_context.calibration,
        sigma_readout_provenance="cli_override",
        apply_calibration_n_cells=True,
    )

    # Build refinement context
    print("[DEBUG] Building RefinementContext...")
    refinement_context = build_refinement_context(
        refinement_inputs=refinement_inputs,
        detector=perturbed_detector,
        beam=perturbed_beam,
        crystal=perturbed_crystal,
        hkl_grid=hkl_grid,
        hkl_metadata=hkl_metadata,
        baseline_crystal=baseline_crystal,
        baseline_detector=baseline_detector,
    )

    # Run Stage A
    print("[DEBUG] Running Stage A refinement...")
    stages = [StageA()]
    engine = RefinementEngine(stages, config=config)
    telemetry_dict = engine.run({"context": refinement_context})

    # Extract telemetry and artifacts
    telemetry_a = telemetry_dict["A"]
    bragg_full_from_engine = engine._artifacts["stage_a"].bragg_full

    print(f"[DEBUG] bragg_full from engine artifact: shape={bragg_full_from_engine.shape if bragg_full_from_engine is not None else 'None'}")
    if bragg_full_from_engine is not None:
        print(f"[DEBUG]   mean={np.mean(bragg_full_from_engine):.6e}, std={np.std(bragg_full_from_engine):.6e}, max={np.max(bragg_full_from_engine):.6e}")

    # Now manually call build_final_bragg_from_stage_a_telemetry to trace through it
    print("[DEBUG] Manually calling build_final_bragg_from_stage_a_telemetry...")
    device = torch.device(config.device)
    dtype = getattr(torch, config.dtype)
    stage_a_ctx = engine._artifacts["stage_a"].stage_a_ctx

    # Check if param_deltas exists
    if hasattr(telemetry_a, 'param_deltas'):
        param_deltas = telemetry_a.param_deltas
        print(f"[DEBUG] param_deltas keys: {list(param_deltas.keys())}")

        # Extract log_scale
        if 'log_scale' in param_deltas:
            log_scale_entry = param_deltas['log_scale']
            print(f"[DEBUG] log_scale entry: {log_scale_entry}")
            log_scale_final = log_scale_entry.get('final', 0.0)
            print(f"[DEBUG] log_scale_final: {log_scale_final}")

        # Extract cell params
        for key in ['log_cell_a_delta', 'log_cell_b_delta', 'log_cell_c_delta', 'angle_alpha_raw', 'angle_beta_raw', 'angle_gamma_raw', 'misset_xyz_deg']:
            if key in param_deltas:
                entry = param_deltas[key]
                print(f"[DEBUG] {key}: {entry}")
    else:
        print("[ERROR] telemetry_a has no param_deltas attribute!")

    # Call the reconstruction function with detailed tracing
    try:
        bragg_full_manual = build_final_bragg_from_stage_a_telemetry(
            telemetry_a=telemetry_a,
            detector=perturbed_detector,
            beam=perturbed_beam,
            crystal=perturbed_crystal,
            inputs=refinement_inputs,
            hkl_grid=hkl_grid,
            hkl_metadata=hkl_metadata,
            config=config,
            device=device,
            dtype=dtype,
            stage_a_ctx=stage_a_ctx,
            baseline_crystal=baseline_crystal,
        )
        print(f"[DEBUG] bragg_full from manual call: shape={bragg_full_manual.shape}")
        print(f"[DEBUG]   mean={np.mean(bragg_full_manual):.6e}, std={np.std(bragg_full_manual):.6e}, max={np.max(bragg_full_manual):.6e}")

        # Check if they match
        if bragg_full_from_engine is not None:
            diff = np.abs(bragg_full_from_engine - bragg_full_manual)
            print(f"[DEBUG] Difference between engine and manual: mean={np.mean(diff):.6e}, max={np.max(diff):.6e}")
    except Exception as e:
        print(f"[ERROR] build_final_bragg_from_stage_a_telemetry failed: {e}")
        import traceback
        traceback.print_exc()

    # Save diagnostic output
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    diagnostics = {
        "test": args.test,
        "bragg_full_from_engine": {
            "shape": str(bragg_full_from_engine.shape) if bragg_full_from_engine is not None else None,
            "mean": float(np.mean(bragg_full_from_engine)) if bragg_full_from_engine is not None else None,
            "std": float(np.std(bragg_full_from_engine)) if bragg_full_from_engine is not None else None,
            "max": float(np.max(bragg_full_from_engine)) if bragg_full_from_engine is not None else None,
        },
        "param_deltas": {k: v for k, v in param_deltas.items()} if hasattr(telemetry_a, 'param_deltas') else None,
    }

    with open(output_dir / f"{args.test}_diagnostics.json", "w") as f:
        json.dump(diagnostics, f, indent=2)

    print(f"[DEBUG] Diagnostics saved to {output_dir / f'{args.test}_diagnostics.json'}")

if __name__ == "__main__":
    main()
