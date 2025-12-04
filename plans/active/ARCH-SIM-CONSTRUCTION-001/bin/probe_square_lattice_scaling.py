#!/usr/bin/env python
"""
Probe script for square lattice (Na·Nb·Nc)² scaling validation.

ARCH-SIM-CONSTRUCTION-001: Simulator Construction Convention Alignment
SIM-CONSTR-PARTIALITY-001: SQUARE lattice must emit weights ∝ (Na·Nb·Nc)²

This thin wrapper instantiates nanobrag_torch.Simulator twice:
1. Base case: N_cells=(1,1,1)
2. Scaled case: N_cells=(Na,Nb,Nc)

With a 1×1 detector, single phi/mosaic, and configurable oversample.
Captures intensities, (F_cell·F_latt)², Lorentz/polarization, and observed ratio.

Usage:
    KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
    python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py \
      --output-dir plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-02T010000Z \
      --n-cells 41 29 32 \
      --oversample 13 \
      --phi-count 1 \
      --mosaic-count 1 \
      --spixels 1 \
      --fpixels 1

Outputs:
    - square_lattice_scaling.json: JSON summary with intensities, factors, ratios
    - square_lattice_scaling.md: Markdown report with commentary
    - Console log (capture via tee)
"""

import argparse
import json
from pathlib import Path

import numpy as np
import torch

# Import nanobrag_torch owner APIs
from nanobrag_torch.simulator import Simulator
from nanobrag_torch.config import BeamConfig, CrystalConfig, CrystalShape, DetectorConfig
from nanobrag_torch.models.crystal import Crystal
from nanobrag_torch.models.detector import Detector


def sincg_reference(delta: np.ndarray, N: int) -> np.ndarray:
    """
    High-precision reference evaluator for 1D lattice response sin(NπΔ)/sin(πΔ).

    Uses NumPy float64 for numerical stability and handles special cases:
    - Δ ≈ 0: returns N (L'Hôpital's rule)
    - Δ ≈ integer: returns N·(-1)^(n(N-1)) where n is the nearest integer

    Args:
        delta: Fractional Miller index offsets (float64 array)
        N: Number of unit cells (integer)

    Returns:
        np.ndarray: Lattice response values (float64)
    """
    delta = np.asarray(delta, dtype=np.float64)
    u = np.pi * delta  # Pre-multiply by π

    eps = 1e-12  # Higher precision threshold for float64

    # Special case 1: u ≈ 0
    is_near_zero = np.abs(u) < eps

    # Special case 2: u ≈ n·π (integer multiple of π)
    u_over_pi = u / np.pi
    nearest_int = np.round(u_over_pi)
    is_near_int_pi = np.abs(u_over_pi - nearest_int) < eps / np.pi

    # Compute sign factor for integer multiples: N·(-1)^(n(N-1))
    sign_exponent = nearest_int * (N - 1)
    is_odd = (np.abs(sign_exponent) % 2) >= 0.5
    sign_factor = np.where(is_odd, -1.0, 1.0)

    # Regular case: sin(N·u) / sin(u)
    sin_u = np.sin(u)
    sin_Nu = np.sin(N * u)

    # Safe division
    with np.errstate(divide='ignore', invalid='ignore'):
        ratio = sin_Nu / sin_u

    # Apply special cases
    result = np.where(
        is_near_zero,
        float(N),
        np.where(
            is_near_int_pi & ~is_near_zero,
            N * sign_factor,
            ratio
        )
    )

    # Replace any remaining NaNs/Infs with N (conservative fallback)
    result = np.where(np.isfinite(result), result, float(N))

    return result


def run_simulation(na, nb, nc, spixels, fpixels, oversample, phi_steps, mosaic_domains, device="cpu"):
    """
    Run simulator with given N_cells configuration.

    Returns tuple: (total_intensity, debug_stats_dict)
    """
    # Create detector: single pixel or small grid
    detector_config = DetectorConfig(
        distance_mm=100.0,
        pixel_size_mm=0.1,
        spixels=spixels,
        fpixels=fpixels,
        oversample=oversample,
    )

    # Create beam config
    beam_config = BeamConfig()  # defaults: wavelength_A=1.0

    # Create crystal config with SQUARE shape
    crystal_config = CrystalConfig(
        default_F=100.0,  # Constant structure factor
        N_cells=(na, nb, nc),
        shape=CrystalShape.SQUARE,
        phi_steps=phi_steps,
        mosaic_domains=mosaic_domains,
    )

    # Instantiate crystal and detector
    crystal = Crystal(crystal_config, device=device)
    detector = Detector(detector_config, device=device)

    # Create simulator with debug config for partiality stats and trace
    debug_config = {
        'collect_partiality_stats': True,
        'trace_pixel': [0, 0]
    }

    simulator = Simulator(
        crystal=crystal,
        detector=detector,
        crystal_config=crystal_config,
        beam_config=beam_config,
        device=device,
        debug_config=debug_config,
    )

    # Run simulation
    image = simulator.run()
    total_intensity = image.sum().item()

    # Extract debug stats if available
    debug_stats = {}
    # Phase C.31: Extract partiality stats for F_cell, F_latt, F_total^2, intensity_pre_polar
    payload = {}

    # Access partiality_stats directly from simulator._partiality_stats
    if hasattr(simulator, '_partiality_stats') and simulator._partiality_stats is not None:
        pstats = simulator._partiality_stats
        # Phase C.31: Extract key metrics for scaling analysis
        if 'F_cell' in pstats:
            F_cell = pstats['F_cell']
            payload['F_cell'] = float(F_cell.mean().item()) if isinstance(F_cell, torch.Tensor) else F_cell
        if 'f_latt' in pstats:
            f_latt = pstats['f_latt']
            payload['F_latt'] = float(f_latt.mean().item()) if isinstance(f_latt, torch.Tensor) else f_latt
        if 'F_total_squared_pre_lorentz' in pstats:
            F_total_sq = pstats['F_total_squared_pre_lorentz']
            payload['F_total_squared_pre_lorentz'] = float(F_total_sq.mean().item()) if isinstance(F_total_sq, torch.Tensor) else F_total_sq
        if 'intensity_pre_polar' in pstats:
            I_pre_polar = pstats['intensity_pre_polar']
            payload['intensity_pre_polar'] = float(I_pre_polar.mean().item()) if isinstance(I_pre_polar, torch.Tensor) else I_pre_polar

        # Phase C.34/C.35: Extract per-subpixel trace data from trace_* keys
        # These are sliced to the single traced pixel but retain all subpixel samples
        per_axis_data = {}
        for axis_key, h_key, h0_key, delta_key, f_latt_key in [
            ('h', 'trace_h', 'trace_h0', 'trace_delta_h', 'trace_F_latt_a'),
            ('k', 'trace_k', 'trace_k0', 'trace_delta_k', 'trace_F_latt_b'),
            ('l', 'trace_l', 'trace_l0', 'trace_delta_l', 'trace_F_latt_c')
        ]:
            # C.35: Capture full HKL tensors and rounded indices
            if h_key in pstats:
                h_vals = pstats[h_key]
                if isinstance(h_vals, torch.Tensor):
                    per_axis_data[axis_key] = h_vals.cpu().numpy().astype(np.float64)
            if h0_key in pstats:
                h0_vals = pstats[h0_key]
                if isinstance(h0_vals, torch.Tensor):
                    per_axis_data[f'{axis_key}0'] = h0_vals.cpu().numpy().astype(np.float64)
            if delta_key in pstats and f_latt_key in pstats:
                delta_vals = pstats[delta_key]
                f_latt_vals = pstats[f_latt_key]
                if isinstance(delta_vals, torch.Tensor) and isinstance(f_latt_vals, torch.Tensor):
                    per_axis_data[f'delta_{axis_key}'] = delta_vals.cpu().numpy().astype(np.float64)
                    per_axis_data[f'F_latt_{axis_key}'] = f_latt_vals.cpu().numpy().astype(np.float64)

        # C.37: Extract dual-basis HKL projection data and compute deltas vs production HKL
        if 'trace_h_dual' in pstats and 'trace_k_dual' in pstats and 'trace_l_dual' in pstats:
            h_dual = pstats['trace_h_dual']
            k_dual = pstats['trace_k_dual']
            l_dual = pstats['trace_l_dual']
            if isinstance(h_dual, torch.Tensor) and isinstance(k_dual, torch.Tensor) and isinstance(l_dual, torch.Tensor):
                h_dual_np = h_dual.cpu().numpy().astype(np.float64)
                k_dual_np = k_dual.cpu().numpy().astype(np.float64)
                l_dual_np = l_dual.cpu().numpy().astype(np.float64)
                per_axis_data['h_dual'] = h_dual_np
                per_axis_data['k_dual'] = k_dual_np
                per_axis_data['l_dual'] = l_dual_np

                # Compute deltas: production HKL - dual-basis HKL
                if 'h' in per_axis_data and 'k' in per_axis_data and 'l' in per_axis_data:
                    h_prod = per_axis_data['h']
                    k_prod = per_axis_data['k']
                    l_prod = per_axis_data['l']
                    delta_h_dual = h_prod - h_dual_np
                    delta_k_dual = k_prod - k_dual_np
                    delta_l_dual = l_prod - l_dual_np
                    per_axis_data['delta_h_dual'] = delta_h_dual
                    per_axis_data['delta_k_dual'] = delta_k_dual
                    per_axis_data['delta_l_dual'] = delta_l_dual

                    # Compute summary stats for dual-basis deltas
                    payload['dual_basis_delta_h_stats'] = {
                        'min': float(np.min(delta_h_dual)),
                        'median': float(np.median(delta_h_dual)),
                        'max': float(np.max(delta_h_dual)),
                    }
                    payload['dual_basis_delta_k_stats'] = {
                        'min': float(np.min(delta_k_dual)),
                        'median': float(np.median(delta_k_dual)),
                        'max': float(np.max(delta_k_dual)),
                    }
                    payload['dual_basis_delta_l_stats'] = {
                        'min': float(np.min(delta_l_dual)),
                        'median': float(np.median(delta_l_dual)),
                        'max': float(np.max(delta_l_dual)),
                    }

        # C.37: Extract raw scattering vector (in Å⁻¹) when available
        if 'trace_scattering_vector' in pstats:
            scatter_vec = pstats['trace_scattering_vector']
            if isinstance(scatter_vec, torch.Tensor):
                per_axis_data['scattering_vector'] = scatter_vec.cpu().numpy().astype(np.float64)

        # Also extract trace_F_total_squared_pre_lorentz for per-subpixel intensity contribution
        if 'trace_F_total_squared_pre_lorentz' in pstats:
            f_total_sq_trace = pstats['trace_F_total_squared_pre_lorentz']
            if isinstance(f_total_sq_trace, torch.Tensor):
                per_axis_data['F_total_squared_pre_lorentz'] = f_total_sq_trace.cpu().numpy().astype(np.float64)

        payload['per_axis_data'] = per_axis_data

        # C.33: Extract minimum absolute deltas to verify oversample centering
        if 'min_abs_delta_h' in pstats:
            payload['min_abs_delta_h'] = pstats['min_abs_delta_h']
        if 'min_abs_delta_k' in pstats:
            payload['min_abs_delta_k'] = pstats['min_abs_delta_k']
        if 'min_abs_delta_l' in pstats:
            payload['min_abs_delta_l'] = pstats['min_abs_delta_l']

        # C.36: Extract raw slow/fast subpixel offsets from traced pixel
        if 'trace_subpixel_offset_slow' in pstats:
            offset_slow = pstats['trace_subpixel_offset_slow']
            if isinstance(offset_slow, torch.Tensor):
                offset_slow_np = offset_slow.cpu().numpy().astype(np.float64)
                payload['subpixel_offset_slow_stats'] = {
                    'min': float(np.min(offset_slow_np)),
                    'median': float(np.median(offset_slow_np)),
                    'max': float(np.max(offset_slow_np)),
                    'straddles_zero': bool(np.min(offset_slow_np) < 0 and np.max(offset_slow_np) > 0)
                }
        if 'trace_subpixel_offset_fast' in pstats:
            offset_fast = pstats['trace_subpixel_offset_fast']
            if isinstance(offset_fast, torch.Tensor):
                offset_fast_np = offset_fast.cpu().numpy().astype(np.float64)
                payload['subpixel_offset_fast_stats'] = {
                    'min': float(np.min(offset_fast_np)),
                    'median': float(np.median(offset_fast_np)),
                    'max': float(np.max(offset_fast_np)),
                    'straddles_zero': bool(np.min(offset_fast_np) < 0 and np.max(offset_fast_np) > 0)
                }

        debug_stats['partiality_stats'] = {
            k: (v.tolist() if isinstance(v, torch.Tensor) else v)
            for k, v in pstats.items()
            if not k.startswith('trace_')
        }

    if hasattr(simulator, 'debug_stats') and simulator.debug_stats is not None:
        stats = simulator.debug_stats
        if 'trace_pixel' in stats:
            trace = stats['trace_pixel']
            debug_stats['trace_pixel'] = {
                k: (v.tolist() if isinstance(v, torch.Tensor) and v.numel() < 100 else str(v))
                for k, v in trace.items()
            }

    return total_intensity, debug_stats, payload


def main():
    parser = argparse.ArgumentParser(description="Square lattice scaling probe")
    parser.add_argument("--output-dir", type=str, required=True,
                        help="Output directory for artifacts")
    parser.add_argument("--n-cells", type=int, nargs=3, default=[41, 29, 32],
                        help="N_cells (Na Nb Nc)")
    parser.add_argument("--oversample", type=int, default=13,
                        help="Oversample factor")
    parser.add_argument("--phi-count", type=int, default=1,
                        help="Phi sample count")
    parser.add_argument("--mosaic-count", type=int, default=1,
                        help="Mosaic sample count")
    parser.add_argument("--spixels", type=int, default=1,
                        help="Slow pixels")
    parser.add_argument("--fpixels", type=int, default=1,
                        help="Fast pixels")
    parser.add_argument("--device", type=str, default="cpu",
                        help="Device (cpu/cuda)")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    na, nb, nc = args.n_cells
    expected_ratio = (na * nb * nc) ** 2

    print(f"Square lattice scaling probe")
    print(f"=" * 60)
    print(f"N_cells target: ({na}, {nb}, {nc})")
    print(f"Expected ratio: {expected_ratio:,.1f}")
    print(f"Oversample: {args.oversample}")
    print(f"Detector: {args.spixels}×{args.fpixels} pixels")
    print(f"Phi steps: {args.phi_count}, Mosaic domains: {args.mosaic_count}")
    print(f"Device: {args.device}")
    print()

    # Run base case: N_cells=(1,1,1)
    print("Running base case: N_cells=(1,1,1)")
    intensity_base, debug_base, payload_base = run_simulation(
        1, 1, 1,
        args.spixels, args.fpixels,
        args.oversample, args.phi_count, args.mosaic_count,
        args.device
    )
    print(f"  Base intensity: {intensity_base:.6e}")
    if payload_base:
        f_cell = payload_base.get('F_cell')
        f_latt = payload_base.get('F_latt')
        f_tot_sq = payload_base.get('F_total_squared_pre_lorentz')
        i_pre = payload_base.get('intensity_pre_polar')
        f_cell_str = f"{f_cell:.6e}" if f_cell is not None else 'N/A'
        f_latt_str = f"{f_latt:.6e}" if f_latt is not None else 'N/A'
        f_tot_sq_str = f"{f_tot_sq:.6e}" if f_tot_sq is not None else 'N/A'
        i_pre_str = f"{i_pre:.6e}" if i_pre is not None else 'N/A'
        print(f"  Base payload: F_cell={f_cell_str}, "
              f"F_latt={f_latt_str}, "
              f"F_total²={f_tot_sq_str}, "
              f"I_pre_polar={i_pre_str}")
    print()

    # Run scaled case: N_cells=(Na,Nb,Nc)
    print(f"Running scaled case: N_cells=({na},{nb},{nc})")
    intensity_scaled, debug_scaled, payload_scaled = run_simulation(
        na, nb, nc,
        args.spixels, args.fpixels,
        args.oversample, args.phi_count, args.mosaic_count,
        args.device
    )
    print(f"  Scaled intensity: {intensity_scaled:.6e}")
    if payload_scaled:
        f_cell = payload_scaled.get('F_cell')
        f_latt = payload_scaled.get('F_latt')
        f_tot_sq = payload_scaled.get('F_total_squared_pre_lorentz')
        i_pre = payload_scaled.get('intensity_pre_polar')
        f_cell_str = f"{f_cell:.6e}" if f_cell is not None else 'N/A'
        f_latt_str = f"{f_latt:.6e}" if f_latt is not None else 'N/A'
        f_tot_sq_str = f"{f_tot_sq:.6e}" if f_tot_sq is not None else 'N/A'
        i_pre_str = f"{i_pre:.6e}" if i_pre is not None else 'N/A'
        print(f"  Scaled payload: F_cell={f_cell_str}, "
              f"F_latt={f_latt_str}, "
              f"F_total²={f_tot_sq_str}, "
              f"I_pre_polar={i_pre_str}")
        # C.33: Display min_abs_delta stats to verify oversample centering
        if 'min_abs_delta_h' in payload_scaled or 'min_abs_delta_k' in payload_scaled or 'min_abs_delta_l' in payload_scaled:
            print(f"  Min |Δ| stats (C.33 oversample centering):")
            if 'min_abs_delta_h' in payload_scaled:
                print(f"    min_abs_delta_h: {payload_scaled['min_abs_delta_h']:.6e}")
            if 'min_abs_delta_k' in payload_scaled:
                print(f"    min_abs_delta_k: {payload_scaled['min_abs_delta_k']:.6e}")
            if 'min_abs_delta_l' in payload_scaled:
                print(f"    min_abs_delta_l: {payload_scaled['min_abs_delta_l']:.6e}")
        # C.36: Display raw slow/fast subpixel offset stats
        if 'subpixel_offset_slow_stats' in payload_scaled or 'subpixel_offset_fast_stats' in payload_scaled:
            print(f"  Subpixel offset stats (C.36 detector-plane sampling):")
            if 'subpixel_offset_slow_stats' in payload_scaled:
                stats = payload_scaled['subpixel_offset_slow_stats']
                straddle = "YES" if stats['straddles_zero'] else "NO"
                print(f"    Slow: min={stats['min']:.6f}, median={stats['median']:.6f}, max={stats['max']:.6f} | straddles_zero={straddle}")
            if 'subpixel_offset_fast_stats' in payload_scaled:
                stats = payload_scaled['subpixel_offset_fast_stats']
                straddle = "YES" if stats['straddles_zero'] else "NO"
                print(f"    Fast: min={stats['min']:.6f}, median={stats['median']:.6f}, max={stats['max']:.6f} | straddles_zero={straddle}")
        # C.35: Display HKL tensor stats for traced pixel
        if 'per_axis_data' in payload_scaled:
            per_axis = payload_scaled['per_axis_data']
            hkl_stats_present = any(k in per_axis for k in ['h', 'k', 'l', 'h0', 'k0', 'l0'])
            if hkl_stats_present:
                print(f"  Traced pixel HKL tensor stats (C.35):")
                for ax in ['h', 'k', 'l']:
                    if ax in per_axis:
                        vals = per_axis[ax]
                        print(f"    {ax}: min={np.min(vals):.6f}, median={np.median(vals):.6f}, max={np.max(vals):.6f}")
                for ax in ['h0', 'k0', 'l0']:
                    if ax in per_axis:
                        vals = per_axis[ax]
                        print(f"    {ax}: min={np.min(vals):.0f}, median={np.median(vals):.0f}, max={np.max(vals):.0f}")
        # C.37: Display dual-basis HKL projection audit
        if 'dual_basis_delta_h_stats' in payload_scaled or 'dual_basis_delta_k_stats' in payload_scaled or 'dual_basis_delta_l_stats' in payload_scaled:
            print(f"  HKL projection audit (C.37 dual-basis solve):")
            print(f"    Deltas: production_HKL - dual_basis_HKL (signed offsets)")
            if 'dual_basis_delta_h_stats' in payload_scaled:
                stats = payload_scaled['dual_basis_delta_h_stats']
                print(f"    Δh: min={stats['min']:.6e}, median={stats['median']:.6e}, max={stats['max']:.6e}")
            if 'dual_basis_delta_k_stats' in payload_scaled:
                stats = payload_scaled['dual_basis_delta_k_stats']
                print(f"    Δk: min={stats['min']:.6e}, median={stats['median']:.6e}, max={stats['max']:.6e}")
            if 'dual_basis_delta_l_stats' in payload_scaled:
                stats = payload_scaled['dual_basis_delta_l_stats']
                print(f"    Δl: min={stats['min']:.6e}, median={stats['median']:.6e}, max={stats['max']:.6e}")
    print()

    # Compute observed ratio
    observed_ratio = intensity_scaled / intensity_base if intensity_base > 0 else 0.0
    relative_error = abs(observed_ratio - expected_ratio) / expected_ratio if expected_ratio > 0 else float('inf')

    # Phase C.32: Compute reference comparison for sincg kernel validation
    reference_analysis = {}
    if payload_scaled and 'per_axis_data' in payload_scaled:
        per_axis = payload_scaled['per_axis_data']

        # Analyze each axis separately
        for axis_name, delta_key, f_latt_key, N_val in [
            ('h', 'delta_h', 'F_latt_a', na),
            ('k', 'delta_k', 'F_latt_b', nb),
            ('l', 'delta_l', 'F_latt_c', nc),
        ]:
            if delta_key in per_axis and f_latt_key in per_axis:
                delta_vals = per_axis[delta_key]
                f_latt_vals = per_axis[f_latt_key]

                # Flatten if multi-dimensional
                delta_flat = delta_vals.flatten()
                f_latt_flat = f_latt_vals.flatten()

                # Compute reference values
                f_latt_ref = sincg_reference(delta_flat, N_val)

                # Compute per-axis error statistics
                abs_error = np.abs(f_latt_flat - f_latt_ref)
                rel_error = np.abs((f_latt_flat - f_latt_ref) / (f_latt_ref + 1e-12))

                # Find worst-case sample
                worst_idx = np.argmax(abs_error)

                axis_stats = {
                    'N': N_val,
                    'num_samples': len(delta_flat),
                    'production_mean': float(np.mean(f_latt_flat)),
                    'production_median': float(np.median(f_latt_flat)),
                    'reference_mean': float(np.mean(f_latt_ref)),
                    'reference_median': float(np.median(f_latt_ref)),
                    'abs_error_max': float(np.max(abs_error)),
                    'abs_error_median': float(np.median(abs_error)),
                    'rel_error_max': float(np.max(rel_error)),
                    'rel_error_median': float(np.median(rel_error)),
                    'worst_case': {
                        'delta': float(delta_flat[worst_idx]),
                        'production': float(f_latt_flat[worst_idx]),
                        'reference': float(f_latt_ref[worst_idx]),
                        'abs_error': float(abs_error[worst_idx]),
                        'rel_error': float(rel_error[worst_idx]),
                    }
                }

                # Find a near-zero delta sample (if any)
                near_zero_mask = np.abs(delta_flat) < 0.01
                if np.any(near_zero_mask):
                    near_zero_idx = np.argmin(np.abs(delta_flat))
                    axis_stats['near_zero_sample'] = {
                        'delta': float(delta_flat[near_zero_idx]),
                        'production': float(f_latt_flat[near_zero_idx]),
                        'reference': float(f_latt_ref[near_zero_idx]),
                        'abs_error': float(abs_error[near_zero_idx]),
                        'rel_error': float(rel_error[near_zero_idx]),
                    }

                reference_analysis[f'axis_{axis_name}'] = axis_stats

        # Compute compounded F_latt using reference values
        if all(f'axis_{ax}' in reference_analysis for ax in ['h', 'k', 'l']):
            # Use median reference values for stability
            f_latt_a_ref = reference_analysis['axis_h']['reference_median']
            f_latt_b_ref = reference_analysis['axis_k']['reference_median']
            f_latt_c_ref = reference_analysis['axis_l']['reference_median']
            f_latt_product_ref = f_latt_a_ref * f_latt_b_ref * f_latt_c_ref

            # Compare to production
            f_latt_product_prod = payload_scaled.get('F_latt', 0.0)

            reference_analysis['compounded'] = {
                'f_latt_ref_median': f_latt_product_ref,
                'f_latt_production': f_latt_product_prod,
                'f_latt_expected': float(na * nb * nc),
                'ref_vs_expected_ratio': f_latt_product_ref / (na * nb * nc) if (na * nb * nc) > 0 else 0.0,
                'prod_vs_expected_ratio': f_latt_product_prod / (na * nb * nc) if (na * nb * nc) > 0 else 0.0,
                'prod_vs_ref_ratio': f_latt_product_prod / f_latt_product_ref if abs(f_latt_product_ref) > 1e-12 else 0.0,
            }

            # Estimate what intensity SHOULD be using reference F_latt
            if intensity_base > 0 and payload_base and 'F_latt' in payload_base:
                # Scale base intensity by (F_latt_ref / F_latt_base)^2
                f_latt_base = payload_base['F_latt']
                expected_intensity_ref = intensity_base * (f_latt_product_ref / f_latt_base) ** 2 if f_latt_base != 0 else 0.0
                reference_analysis['compounded']['expected_intensity_from_ref'] = expected_intensity_ref
                reference_analysis['compounded']['expected_ratio_from_ref'] = expected_intensity_ref / intensity_base if intensity_base > 0 else 0.0

    # Phase C.31: Compute derived ratios from payload
    # These help bisect where the (Na·Nb·Nc)² scaling is lost
    derived_ratios = {}
    if payload_base and payload_scaled:
        # Ratio of F_latt values (should be Na*Nb*Nc for SQUARE)
        if 'F_latt' in payload_base and 'F_latt' in payload_scaled:
            F_latt_base = payload_base['F_latt']
            F_latt_scaled = payload_scaled['F_latt']
            if F_latt_base > 0:
                derived_ratios['F_latt_ratio'] = F_latt_scaled / F_latt_base
                derived_ratios['F_latt_ratio_expected'] = na * nb * nc

        # Ratio of F_total² pre-Lorentz (should be (Na*Nb*Nc)² for SQUARE)
        if 'F_total_squared_pre_lorentz' in payload_base and 'F_total_squared_pre_lorentz' in payload_scaled:
            F_tot_sq_base = payload_base['F_total_squared_pre_lorentz']
            F_tot_sq_scaled = payload_scaled['F_total_squared_pre_lorentz']
            if F_tot_sq_base > 0:
                derived_ratios['F_total_sq_ratio'] = F_tot_sq_scaled / F_tot_sq_base
                derived_ratios['F_total_sq_ratio_expected'] = (na * nb * nc) ** 2

        # Ratio of intensity_pre_polar (should also be (Na*Nb*Nc)² if Lorentz is consistent)
        if 'intensity_pre_polar' in payload_base and 'intensity_pre_polar' in payload_scaled:
            I_pre_polar_base = payload_base['intensity_pre_polar']
            I_pre_polar_scaled = payload_scaled['intensity_pre_polar']
            if I_pre_polar_base > 0:
                derived_ratios['I_pre_polar_ratio'] = I_pre_polar_scaled / I_pre_polar_base
                derived_ratios['I_pre_polar_ratio_expected'] = (na * nb * nc) ** 2

        # Derived ratio: (I_pre_polar) / (F_cell * F_latt)²
        # This isolates the Lorentz contribution
        for label, payload in [('base', payload_base), ('scaled', payload_scaled)]:
            if 'intensity_pre_polar' in payload and 'F_cell' in payload and 'F_latt' in payload:
                I_pre = payload['intensity_pre_polar']
                F_c = payload['F_cell']
                F_l = payload['F_latt']
                denominator = (F_c * F_l) ** 2
                if denominator > 0:
                    derived_ratios[f'{label}_I_pre_polar_over_F_total_sq'] = I_pre / denominator

    # Phase C.34: Subpixel coverage analysis
    # Compute how many subpixels hit the central sincg lobe and their intensity contribution
    coverage_analysis = {}
    if payload_scaled and 'per_axis_data' in payload_scaled:
        per_axis = payload_scaled['per_axis_data']

        # Check if we have per-subpixel data (from trace_* keys)
        if 'delta_h' in per_axis and 'delta_k' in per_axis and 'delta_l' in per_axis:
            delta_h = per_axis['delta_h'].flatten()
            delta_k = per_axis['delta_k'].flatten()
            delta_l = per_axis['delta_l'].flatten()

            # Get F_total_squared_pre_lorentz per subpixel if available
            f_total_sq_per_subpixel = None
            if 'F_total_squared_pre_lorentz' in per_axis:
                f_total_sq_per_subpixel = per_axis['F_total_squared_pre_lorentz'].flatten()

            n_subpixels = len(delta_h)

            # Define central lobe thresholds: |Δ| < 1/N for each axis
            threshold_h = 1.0 / na if na > 0 else 0.0
            threshold_k = 1.0 / nb if nb > 0 else 0.0
            threshold_l = 1.0 / nc if nc > 0 else 0.0

            # Count subpixels hitting central lobe (all three axes within threshold)
            in_central_lobe = (np.abs(delta_h) < threshold_h) & (np.abs(delta_k) < threshold_k) & (np.abs(delta_l) < threshold_l)
            n_central = np.sum(in_central_lobe)

            coverage_analysis['n_subpixels'] = n_subpixels
            coverage_analysis['n_central_lobe'] = int(n_central)
            coverage_analysis['frac_central_lobe'] = n_central / n_subpixels if n_subpixels > 0 else 0.0
            coverage_analysis['threshold_h'] = threshold_h
            coverage_analysis['threshold_k'] = threshold_k
            coverage_analysis['threshold_l'] = threshold_l

            # Compute intensity contribution from central lobe samples
            if f_total_sq_per_subpixel is not None:
                total_intensity_sq = np.sum(f_total_sq_per_subpixel)
                central_intensity_sq = np.sum(f_total_sq_per_subpixel[in_central_lobe])
                coverage_analysis['total_F_total_sq'] = float(total_intensity_sq)
                coverage_analysis['central_F_total_sq'] = float(central_intensity_sq)
                coverage_analysis['frac_intensity_from_central'] = central_intensity_sq / total_intensity_sq if total_intensity_sq > 0 else 0.0

                # Implied (Na·Nb·Nc)² if central lobe dominated
                # The spec expects central lobe samples to carry (Na·Nb·Nc)² scaling
                # If only central_frac of subpixels contribute but we divide by all subpixels (oversample²),
                # the effective ratio would be central_frac * (Na·Nb·Nc)²
                implied_ratio = (central_intensity_sq / total_intensity_sq) * expected_ratio if total_intensity_sq > 0 else 0.0
                coverage_analysis['implied_ratio_from_coverage'] = implied_ratio

    print(f"Results")
    print(f"=" * 60)
    print(f"Expected ratio: {expected_ratio:,.1f}")
    print(f"Observed ratio: {observed_ratio:,.1f}")
    print(f"Relative error: {relative_error:.2%}")
    print(f"Ratio deviation: {observed_ratio / expected_ratio:.6f}x expected")
    if derived_ratios:
        print()
        print("Phase C.31 Derived Ratios:")
        for k, v in derived_ratios.items():
            print(f"  {k}: {v:.6e}")
    if reference_analysis:
        print()
        print("Phase C.32 Reference Analysis:")
        for axis in ['h', 'k', 'l']:
            key = f'axis_{axis}'
            if key in reference_analysis:
                stats = reference_analysis[key]
                print(f"  Axis {axis} (N={stats['N']}):")
                print(f"    Production median: {stats['production_median']:.6e}")
                print(f"    Reference median: {stats['reference_median']:.6e}")
                print(f"    Median abs error: {stats['abs_error_median']:.6e}")
                print(f"    Max abs error: {stats['abs_error_max']:.6e} (Δ={stats['worst_case']['delta']:.6f})")
                print(f"    Median rel error: {stats['rel_error_median']:.6%}")
                print(f"    Max rel error: {stats['rel_error_max']:.6%}")
        if 'compounded' in reference_analysis:
            comp = reference_analysis['compounded']
            print(f"  Compounded F_latt:")
            print(f"    Reference median product: {comp['f_latt_ref_median']:.6e}")
            print(f"    Production: {comp['f_latt_production']:.6e}")
            print(f"    Expected (Na·Nb·Nc): {comp['f_latt_expected']:.6e}")
            print(f"    Ref vs expected: {comp['ref_vs_expected_ratio']:.6f}x")
            print(f"    Prod vs expected: {comp['prod_vs_expected_ratio']:.6f}x")
            print(f"    Prod vs ref: {comp['prod_vs_ref_ratio']:.6f}x")
            if 'expected_ratio_from_ref' in comp:
                print(f"  Expected intensity ratio from ref F_latt: {comp['expected_ratio_from_ref']:.6e}")
    if coverage_analysis:
        print()
        print("Phase C.34 Subpixel Coverage Analysis:")
        print(f"  Total subpixels: {coverage_analysis['n_subpixels']}")
        print(f"  Subpixels in central lobe: {coverage_analysis['n_central_lobe']} ({coverage_analysis['frac_central_lobe']:.2%})")
        print(f"  Thresholds: |Δh| < {coverage_analysis['threshold_h']:.6f}, |Δk| < {coverage_analysis['threshold_k']:.6f}, |Δl| < {coverage_analysis['threshold_l']:.6f}")
        if 'frac_intensity_from_central' in coverage_analysis:
            print(f"  Intensity share from central lobe: {coverage_analysis['frac_intensity_from_central']:.2%}")
            print(f"  Implied (Na·Nb·Nc)² ratio from coverage: {coverage_analysis['implied_ratio_from_coverage']:.6e}")
    print()

    # Prepare JSON output
    results = {
        "n_cells": {"na": na, "nb": nb, "nc": nc},
        "oversample": args.oversample,
        "detector": {"spixels": args.spixels, "fpixels": args.fpixels},
        "phi_steps": args.phi_count,
        "mosaic_domains": args.mosaic_count,
        "device": args.device,
        "intensities": {
            "base": intensity_base,
            "scaled": intensity_scaled
        },
        "ratios": {
            "expected": expected_ratio,
            "observed": observed_ratio,
            "relative_error": relative_error,
            "deviation_factor": observed_ratio / expected_ratio if expected_ratio > 0 else 0.0
        },
        "payload": {
            "base": {k: v for k, v in payload_base.items() if k != 'per_axis_data'} if payload_base else {},
            "scaled": {k: v for k, v in payload_scaled.items() if k != 'per_axis_data'} if payload_scaled else {}
        },
        "derived_ratios": derived_ratios,
        "reference_analysis": reference_analysis,
        "coverage_analysis": coverage_analysis,
        "debug_stats": {
            "base": debug_base,
            "scaled": debug_scaled
        }
    }

    # Write JSON
    json_path = output_dir / "square_lattice_scaling.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Wrote JSON: {json_path}")

    # Write Markdown report
    md_path = output_dir / "square_lattice_scaling.md"
    with open(md_path, "w") as f:
        f.write("# Square Lattice Scaling Probe Results\n\n")
        f.write("## Configuration\n\n")
        f.write(f"- **N_cells**: ({na}, {nb}, {nc})\n")
        f.write(f"- **Expected ratio**: {expected_ratio:,.1f}\n")
        f.write(f"- **Oversample**: {args.oversample}\n")
        f.write(f"- **Detector**: {args.spixels}×{args.fpixels} pixels\n")
        f.write(f"- **Phi steps**: {args.phi_count}\n")
        f.write(f"- **Mosaic domains**: {args.mosaic_count}\n")
        f.write(f"- **Device**: {args.device}\n\n")

        f.write("## Intensities\n\n")
        f.write(f"- **Base** (N_cells=1,1,1): {intensity_base:.6e}\n")
        f.write(f"- **Scaled** (N_cells={na},{nb},{nc}): {intensity_scaled:.6e}\n\n")

        f.write("## Scaling Analysis\n\n")
        f.write(f"- **Expected ratio** (Na·Nb·Nc)²: {expected_ratio:,.1f}\n")
        f.write(f"- **Observed ratio**: {observed_ratio:,.1f}\n")
        f.write(f"- **Relative error**: {relative_error:.2%}\n")
        f.write(f"- **Deviation factor**: {observed_ratio / expected_ratio:.6f}x expected\n\n")

        f.write("## Phase C.31 Payload Analysis\n\n")
        if payload_base:
            f.write("### Base Case (N_cells=1,1,1)\n")
            for k, v in payload_base.items():
                if k not in ('per_axis_data', 'subpixel_offset_slow_stats', 'subpixel_offset_fast_stats', 'dual_basis_delta_h_stats', 'dual_basis_delta_k_stats', 'dual_basis_delta_l_stats'):
                    f.write(f"- **{k}**: {v:.6e}\n")
            f.write("\n")
        if payload_scaled:
            f.write(f"### Scaled Case (N_cells={na},{nb},{nc})\n")
            for k, v in payload_scaled.items():
                if k not in ('per_axis_data', 'subpixel_offset_slow_stats', 'subpixel_offset_fast_stats', 'dual_basis_delta_h_stats', 'dual_basis_delta_k_stats', 'dual_basis_delta_l_stats'):
                    f.write(f"- **{k}**: {v:.6e}\n")
            f.write("\n")
            # C.36: Add subpixel offset summary before HKL stats
            if 'subpixel_offset_slow_stats' in payload_scaled or 'subpixel_offset_fast_stats' in payload_scaled:
                f.write("### Subpixel Offset Stats (Phase C.36)\n\n")
                f.write("Raw detector-plane slow/fast subpixel offsets (fractional pixel units) for the traced pixel:\n\n")
                f.write("| Axis | Min | Median | Max | Straddles Zero |\n")
                f.write("|------|-----|--------|-----|----------------|\n")
                if 'subpixel_offset_slow_stats' in payload_scaled:
                    stats = payload_scaled['subpixel_offset_slow_stats']
                    straddle = "✓" if stats['straddles_zero'] else "✗"
                    f.write(f"| Slow | {stats['min']:.6f} | {stats['median']:.6f} | {stats['max']:.6f} | {straddle} |\n")
                if 'subpixel_offset_fast_stats' in payload_scaled:
                    stats = payload_scaled['subpixel_offset_fast_stats']
                    straddle = "✓" if stats['straddles_zero'] else "✗"
                    f.write(f"| Fast | {stats['min']:.6f} | {stats['median']:.6f} | {stats['max']:.6f} | {straddle} |\n")
                f.write("\n")
                f.write("**Interpretation**: For oversample=13, expected range is -6/13 = -0.461538 to +6/13 = +0.461538.\n")
                f.write("Both axes should straddle zero to ensure the sincg lobe center (Δ=0) is sampled.\n\n")

            # C.35: Add traced pixel HKL tensor summary
            if 'per_axis_data' in payload_scaled:
                per_axis = payload_scaled['per_axis_data']
                hkl_stats_present = any(k in per_axis for k in ['h', 'k', 'l', 'h0', 'k0', 'l0'])
                if hkl_stats_present:
                    f.write("### Traced Pixel HKL Tensor Stats (Phase C.35)\n\n")
                    f.write("Per-subpixel HKL values captured via `_partiality_stats` for the single traced pixel:\n\n")
                    f.write("| Axis | Min | Median | Max |\n")
                    f.write("|------|-----|--------|-----|\n")
                    for ax in ['h', 'k', 'l']:
                        if ax in per_axis:
                            vals = per_axis[ax]
                            f.write(f"| {ax} | {np.min(vals):.6f} | {np.median(vals):.6f} | {np.max(vals):.6f} |\n")
                    for ax in ['h0', 'k0', 'l0']:
                        if ax in per_axis:
                            vals = per_axis[ax]
                            f.write(f"| {ax} | {np.min(vals):.0f} | {np.median(vals):.0f} | {np.max(vals):.0f} |\n")
                    f.write("\n")

            # C.37: Add HKL projection audit via dual-basis solve
            if 'dual_basis_delta_h_stats' in payload_scaled or 'dual_basis_delta_k_stats' in payload_scaled or 'dual_basis_delta_l_stats' in payload_scaled:
                f.write("### HKL Projection Audit (Phase C.37)\n\n")
                f.write("Alternate HKL projection via dual-basis matrix solve (`torch.linalg.solve`) compared to production dot-product approach.\n\n")
                f.write("**Deltas**: production_HKL - dual_basis_HKL (signed offsets per subpixel)\n\n")
                f.write("| Axis | Min | Median | Max |\n")
                f.write("|------|-----|--------|-----|\n")
                if 'dual_basis_delta_h_stats' in payload_scaled:
                    stats = payload_scaled['dual_basis_delta_h_stats']
                    f.write(f"| Δh | {stats['min']:.6e} | {stats['median']:.6e} | {stats['max']:.6e} |\n")
                if 'dual_basis_delta_k_stats' in payload_scaled:
                    stats = payload_scaled['dual_basis_delta_k_stats']
                    f.write(f"| Δk | {stats['min']:.6e} | {stats['median']:.6e} | {stats['max']:.6e} |\n")
                if 'dual_basis_delta_l_stats' in payload_scaled:
                    stats = payload_scaled['dual_basis_delta_l_stats']
                    f.write(f"| Δl | {stats['min']:.6e} | {stats['median']:.6e} | {stats['max']:.6e} |\n")
                f.write("\n")
                f.write("**Interpretation**: If the dual-basis solve produces HKL values that are closer to integers ")
                f.write("than the production dot-product approach, this suggests a bug in the HKL projection logic. ")
                f.write("If both approaches yield similar offsets from integers, the issue lies upstream (detector geometry or oversample grid construction).\n\n")

        if derived_ratios:
            f.write("### Derived Ratios\n\n")
            f.write("These ratios help bisect where the (Na·Nb·Nc)² scaling is lost:\n\n")
            for k, v in derived_ratios.items():
                f.write(f"- **{k}**: {v:.6e}\n")
            f.write("\n")

        # Phase C.32: Add reference analysis to Markdown
        if reference_analysis:
            f.write("## Phase C.32 Reference Analysis\n\n")
            f.write("High-precision NumPy float64 reference evaluator for `sin(NπΔ)/sin(πΔ)` compared against production `sincg` kernel.\n\n")

            # Per-axis error table
            f.write("### Per-Axis Error Statistics\n\n")
            f.write("| Axis | N | Production Median | Reference Median | Median Abs Err | Max Abs Err | Median Rel Err | Max Rel Err |\n")
            f.write("|------|---|-------------------|------------------|----------------|-------------|----------------|-------------|\n")
            for axis in ['h', 'k', 'l']:
                key = f'axis_{axis}'
                if key in reference_analysis:
                    stats = reference_analysis[key]
                    f.write(f"| {axis} | {stats['N']} | {stats['production_median']:.6e} | {stats['reference_median']:.6e} | ")
                    f.write(f"{stats['abs_error_median']:.6e} | {stats['abs_error_max']:.6e} | ")
                    f.write(f"{stats['rel_error_median']:.4%} | {stats['rel_error_max']:.4%} |\n")
            f.write("\n")

            # Worst-case samples
            f.write("### Worst-Case Samples (Max Absolute Error)\n\n")
            f.write("| Axis | Δ | Production | Reference | Abs Error | Rel Error |\n")
            f.write("|------|---|------------|-----------|-----------|------------|\n")
            for axis in ['h', 'k', 'l']:
                key = f'axis_{axis}'
                if key in reference_analysis and 'worst_case' in reference_analysis[key]:
                    wc = reference_analysis[key]['worst_case']
                    f.write(f"| {axis} | {wc['delta']:.6f} | {wc['production']:.6e} | {wc['reference']:.6e} | ")
                    f.write(f"{wc['abs_error']:.6e} | {wc['rel_error']:.4%} |\n")
            f.write("\n")

            # Near-zero samples
            f.write("### Near-Zero Δ Samples\n\n")
            f.write("| Axis | Δ | Production | Reference | Abs Error | Rel Error |\n")
            f.write("|------|---|------------|-----------|-----------|------------|\n")
            for axis in ['h', 'k', 'l']:
                key = f'axis_{axis}'
                if key in reference_analysis and 'near_zero_sample' in reference_analysis[key]:
                    nz = reference_analysis[key]['near_zero_sample']
                    f.write(f"| {axis} | {nz['delta']:.6f} | {nz['production']:.6e} | {nz['reference']:.6e} | ")
                    f.write(f"{nz['abs_error']:.6e} | {nz['rel_error']:.4%} |\n")
            f.write("\n")

            # Compounded analysis
            if 'compounded' in reference_analysis:
                comp = reference_analysis['compounded']
                f.write("### Compounded F_latt Analysis\n\n")
                f.write(f"- **Reference median product** (F_latt_a × F_latt_b × F_latt_c): {comp['f_latt_ref_median']:.6e}\n")
                f.write(f"- **Production F_latt**: {comp['f_latt_production']:.6e}\n")
                f.write(f"- **Expected** (Na·Nb·Nc): {comp['f_latt_expected']:.6e}\n")
                f.write(f"- **Reference vs expected ratio**: {comp['ref_vs_expected_ratio']:.6f}x\n")
                f.write(f"- **Production vs expected ratio**: {comp['prod_vs_expected_ratio']:.6f}x\n")
                f.write(f"- **Production vs reference ratio**: {comp['prod_vs_ref_ratio']:.6f}x\n")
                if 'expected_ratio_from_ref' in comp:
                    f.write(f"\n**Predicted intensity ratio using reference F_latt**: {comp['expected_ratio_from_ref']:.6e}\n")
                    f.write(f"(Expected (Na·Nb·Nc)² = {expected_ratio:,.1f})\n")
                f.write("\n")

        # Phase C.34: Add coverage analysis section
        if coverage_analysis:
            f.write("## Phase C.34 Subpixel Coverage Analysis\n\n")
            f.write("This section quantifies how many subpixels hit the central sincg lobe (|Δ_{h,k,l}| < 1/N)\n")
            f.write("and what fraction of the total intensity they contribute.\n\n")
            f.write(f"- **Total subpixels sampled**: {coverage_analysis['n_subpixels']}\n")
            f.write(f"- **Subpixels in central lobe**: {coverage_analysis['n_central_lobe']} ")
            f.write(f"({coverage_analysis['frac_central_lobe']:.2%})\n")
            f.write(f"- **Central lobe thresholds**:\n")
            f.write(f"  - |Δh| < {coverage_analysis['threshold_h']:.6f}\n")
            f.write(f"  - |Δk| < {coverage_analysis['threshold_k']:.6f}\n")
            f.write(f"  - |Δl| < {coverage_analysis['threshold_l']:.6f}\n")
            if 'frac_intensity_from_central' in coverage_analysis:
                f.write(f"- **Intensity share from central lobe**: {coverage_analysis['frac_intensity_from_central']:.2%}\n")
                f.write(f"- **Implied (Na·Nb·Nc)² ratio from coverage**: {coverage_analysis['implied_ratio_from_coverage']:.6e}\n")
                f.write(f"  (Expected: {expected_ratio:,.1f})\n\n")

                # Add decision logic commentary
                if coverage_analysis['frac_central_lobe'] < 0.01:
                    f.write("**Diagnosis**: Less than 1% of subpixels reach the central lobe.\n")
                    f.write("This explains the (Na·Nb·Nc)² deficit: the oversample grid is not capturing the sincg peak.\n")
                    f.write("Next step: investigate subpixel positioning or increase oversample factor.\n\n")
                elif coverage_analysis['frac_intensity_from_central'] < 0.10:
                    f.write("**Diagnosis**: Central lobe samples contribute <10% of total intensity.\n")
                    f.write("This indicates the intensity is dominated by subpixels off the central peak.\n")
                    f.write("Next step: audit the `steps` normalization or sincg accumulation logic.\n\n")
                else:
                    f.write("**Diagnosis**: Central lobe coverage appears healthy.\n")
                    f.write("The deficit must originate elsewhere (normalization, Lorentz, or polar ordering).\n\n")

        f.write("## Commentary\n\n")
        if relative_error < 0.05:
            f.write("✅ The observed ratio is within 5% tolerance of the expected (Na·Nb·Nc)² scaling.\n")
        else:
            f.write(f"❌ **Contract violation detected**: The observed ratio deviates by {relative_error:.1%} from expected.\n\n")
            f.write(f"The SQUARE lattice contract (docs/spec-db-core.md:60-140) requires weights ∝ (Na·Nb·Nc)².\n")
            f.write(f"This {observed_ratio / expected_ratio:.6f}x shortfall suggests a bug in the lattice weight computation.\n")

    print(f"Wrote Markdown: {md_path}")
    print()
    print("Probe complete.")


if __name__ == "__main__":
    main()
