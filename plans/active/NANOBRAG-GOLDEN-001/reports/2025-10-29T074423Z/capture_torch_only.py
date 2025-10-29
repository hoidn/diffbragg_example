#!/usr/bin/env python3
"""Run nanobrag_torch forward simulator using refined parameters from DiffBragg."""
import datetime
import json
from argparse import Namespace
from pathlib import Path
import h5py
import numpy as np
import torch
from nanobrag_torch.config import (
    DetectorConfig as TorchDetectorConfig,
    BeamConfig as TorchBeamConfig,
    CrystalConfig as TorchCrystalConfig,
    DetectorConvention as TorchDetectorConvention,
)
from nanobrag_torch.models.detector import Detector as TorchDetector
from nanobrag_torch.models.crystal import Crystal as TorchCrystal
from nanobrag_torch.simulator import Simulator as TorchSimulator
from dbex.data_load import DataLoad
from dbex.nanobrag_bridge import (
    prepare_refinement_inputs,
    create_detector_config,
    create_beam_config,
    create_crystal_config,
)

torch.set_grad_enabled(False)


def repo_root_from_report(report_dir: Path) -> Path:
    for parent in report_dir.parents:
        if (parent / "scaled.mtz").exists():
            return parent
    raise RuntimeError("Unable to locate repo root from report directory.")


def build_structure_factor_grid(indices, amplitudes, device):
    hkls = np.asarray(indices, dtype=int)
    amps = np.abs(np.asarray(amplitudes, dtype=np.float32))
    h_min, h_max = hkls[:, 0].min(), hkls[:, 0].max()
    k_min, k_max = hkls[:, 1].min(), hkls[:, 1].max()
    l_min, l_max = hkls[:, 2].min(), hkls[:, 2].max()
    h_range = h_max - h_min + 1
    k_range = k_max - k_min + 1
    l_range = l_max - l_min + 1
    grid = torch.zeros((h_range, k_range, l_range), device=device, dtype=torch.float32)
    for (h, k, l), amp in zip(hkls, amps):
        grid[h - h_min, k - k_min, l - l_min] = amp
    metadata = {
        "h_min": int(h_min),
        "h_max": int(h_max),
        "k_min": int(k_min),
        "k_max": int(k_max),
        "l_min": int(l_min),
        "l_max": int(l_max),
        "h_range": int(h_range),
        "k_range": int(k_range),
        "l_range": int(l_range),
    }
    return grid, metadata


def compute_roi_metrics(db_stack, torch_stack, loss_mask, panel_slices, sample_frac=0.2):
    rng = np.random.RandomState(42)
    records = []
    for roi_idx, (pid, bbox) in enumerate(panel_slices):
        x0, x1, y0, y1 = bbox
        db_roi = db_stack[pid, y0:y1, x0:x1]
        torch_roi = torch_stack[pid, y0:y1, x0:x1]
        mask_roi = loss_mask[pid, y0:y1, x0:x1]
        if not np.any(mask_roi):
            continue
        db_flat = db_roi[mask_roi]
        torch_flat = torch_roi[mask_roi]
        if db_flat.size < 2 or torch_flat.size < 2:
            continue
        corr = float(np.corrcoef(db_flat, torch_flat)[0, 1])
        mse = float(np.mean((db_flat - torch_flat) ** 2))
        rmse = float(np.sqrt(mse))
        max_diff = float(np.max(np.abs(db_flat - torch_flat)))
        slow_size, fast_size = db_roi.shape
        center_h = slow_size // 2
        center_w = fast_size // 2
        db_peak = np.unravel_index(np.argmax(db_roi), db_roi.shape)
        torch_peak = np.unravel_index(np.argmax(torch_roi), torch_roi.shape)
        db_loc = abs(db_peak[0] - center_h) < center_h // 2 and abs(db_peak[1] - center_w) < center_w // 2
        torch_loc = abs(torch_peak[0] - center_h) < center_h // 2 and abs(torch_peak[1] - center_w) < center_w // 2
        records.append(
            {
                "roi_idx": int(roi_idx),
                "panel_id": int(pid),
                "correlation": corr,
                "rmse": rmse,
                "mse": mse,
                "max_abs_diff": max_diff,
                "peak_localized": bool(db_loc and torch_loc),
            }
        )
    rng.shuffle(records)
    sample_count = max(1, int(len(records) * sample_frac))
    return records[:sample_count]


def main():
    report_dir = Path(__file__).resolve().parent
    repo_root = repo_root_from_report(report_dir)
    out_root = report_dir / "golden_dataset"
    legacy_dir = out_root / "legacy"
    torch_dir = out_root / "torch"

    # Check that DiffBragg baseline exists
    db_baseline = legacy_dir / "bragg_diffbragg.npy"
    if not db_baseline.exists():
        raise RuntimeError(f"DiffBragg baseline not found: {db_baseline}")

    # Load DiffBragg baseline
    Bragg = np.load(db_baseline)
    print(f"[torch_capture] Loaded DiffBragg baseline: {Bragg.shape}")

    # Load data
    args = Namespace(
        mtzFile=str(repo_root / "scaled.mtz"),
        mtzCol="F,SIGF",
        exptName=str(repo_root / "refGeom.expt"),
        exptIdx=0,
        reflName=str(repo_root / "refGeom.refl"),
        maskFile=str(repo_root / "747_mask.pkl"),
    )
    dl = DataLoad(args)

    # Read refined parameters from DiffBragg HDF5
    h5_path = legacy_dir / "dbex_diffbragg_gpu.h5"
    with h5py.File(h5_path, "r") as f:
        # Extract refined Ncells if available
        if "/refined_params" in f:
            Na = float(f["/refined_params"].attrs.get("Na", 20))
            Nb = float(f["/refined_params"].attrs.get("Nb", 20))
            Nc = float(f["/refined_params"].attrs.get("Nc", 20))
            scale = float(f["/refined_params"].attrs.get("scale", 1.0))
        else:
            # Fallback defaults
            Na, Nb, Nc = 20, 20, 20
            scale = 1.0

    print(f"[torch_capture] Using N_cells=({Na}, {Nb}, {Nc}), scale={scale}")

    # Torch capture
    device = torch.device("cuda:0")
    beam_stub = create_beam_config(dl.Expt.beam)
    crystal_stub = create_crystal_config(dl.Expt.crystal, dl.Expt)

    # Build trusted masks
    trusted_masks = []
    for panel in dl.Expt.detector:
        fast_px, slow_px = panel.get_image_size()
        mask = np.ones((slow_px, fast_px), dtype=bool)
        if hasattr(panel, "get_mask") and panel.get_mask():
            for rect in panel.get_mask():
                x0, y0, x1, y1 = rect
                mask[y0:y1, x0:x1] = False
        trusted_masks.append(mask)
    trusted_masks = np.asarray(trusted_masks, dtype=bool)

    inputs = prepare_refinement_inputs(
        data=dl.data,
        background_image=dl.background_image,
        trusted_mask=trusted_masks,
        bbox=dl.bbox,
        pids=dl.pids,
        detector=dl.Expt.detector,
    )

    beam_cfg = TorchBeamConfig(
        wavelength_A=float(beam_stub.wavelength_A),
        polarization_factor=float(beam_stub.polarization_factor),
        nopolar=bool(beam_stub.nopolar),
        polarization_axis=tuple(np.asarray(beam_stub.polarization_axis, dtype=np.float32)),
        dmin=float(beam_stub.dmin),
    )

    crystal_cfg = TorchCrystalConfig(
        cell_a=float(crystal_stub.cell_a),
        cell_b=float(crystal_stub.cell_b),
        cell_c=float(crystal_stub.cell_c),
        cell_alpha=float(crystal_stub.cell_alpha),
        cell_beta=float(crystal_stub.cell_beta),
        cell_gamma=float(crystal_stub.cell_gamma),
        mosflm_a_star=np.asarray(crystal_stub.mosflm_a_star, dtype=np.float32),
        mosflm_b_star=np.asarray(crystal_stub.mosflm_b_star, dtype=np.float32),
        mosflm_c_star=np.asarray(crystal_stub.mosflm_c_star, dtype=np.float32),
        misset_deg=np.asarray(crystal_stub.misset_deg, dtype=np.float32),
        phi_steps=int(crystal_stub.phi_steps),
        osc_range_deg=float(crystal_stub.osc_range_deg),
        mosaic_domains=int(getattr(crystal_stub, "mosaic_domains", 1)),
        mosaic_spread_deg=float(getattr(crystal_stub, "mosaic_spread_deg", 0.0)),
        N_cells=(int(Na), int(Nb), int(Nc)),
        default_F=0.0,
    )

    torch_grid, hkl_meta = build_structure_factor_grid(dl.F.indices(), dl.F.data().as_numpy_array(), device=device)
    crystal_model = TorchCrystal(crystal_cfg, beam_config=beam_cfg, device=device)
    crystal_model.hkl_data = torch_grid
    crystal_model.hkl_metadata = hkl_meta

    panel_results = []
    torch_panels = []
    panel_summaries = []

    for panel_id, panel in enumerate(dl.Expt.detector):
        det_stub = create_detector_config(panel, dl.Expt.beam, inputs.trusted_mask[panel_id])
        mask_tensor = torch.tensor(inputs.trusted_mask[panel_id].astype(np.float32), device=device)

        det_cfg = TorchDetectorConfig(
            distance_mm=float(det_stub.distance_mm),
            pixel_size_mm=float(det_stub.pixel_size_mm),
            spixels=int(det_stub.spixels),
            fpixels=int(det_stub.fpixels),
            beam_center_s=float(det_stub.beam_center_s),
            beam_center_f=float(det_stub.beam_center_f),
            beam_center_source="explicit",
            detector_convention=TorchDetectorConvention.CUSTOM,
            custom_fdet_vector=tuple(np.asarray(det_stub.custom_fdet_vector, dtype=np.float32)),
            custom_sdet_vector=tuple(np.asarray(det_stub.custom_sdet_vector, dtype=np.float32)),
            custom_odet_vector=tuple(np.asarray(det_stub.custom_odet_vector, dtype=np.float32)),
            custom_beam_vector=tuple(np.asarray(det_stub.custom_beam_vector, dtype=np.float32)),
            oversample=1,
            mask_array=mask_tensor,
        )

        det_model = TorchDetector(det_cfg, device=device)
        simulator = TorchSimulator(crystal_model, det_model, beam_config=beam_cfg, device=device)
        torch_panel = simulator.run().detach().cpu().numpy().astype(np.float32)
        torch_panels.append(torch_panel)

        panel_summaries.append(
            {
                "panel_id": int(panel_id),
                "shape": list(torch_panel.shape),
                "torch_max": float(torch_panel.max()),
                "torch_sum": float(torch_panel.sum()),
                "loss_mask_coverage": float(np.mean(inputs.loss_mask[panel_id])),
            }
        )

        panel_meta = {
            "panel_id": int(panel_id),
            "distance_mm": float(det_cfg.distance_mm),
            "beam_center_s": float(det_cfg.beam_center_s) if det_cfg.beam_center_s is not None else None,
            "beam_center_f": float(det_cfg.beam_center_f) if det_cfg.beam_center_f is not None else None,
            "pixel_size_mm": float(det_cfg.pixel_size_mm),
        }
        panel_results.append(panel_meta)

        np.save(torch_dir / f"target_panel_{panel_id}.npy", inputs.target[panel_id].astype(np.float32))
        np.save(torch_dir / f"loss_mask_panel_{panel_id}.npy", inputs.loss_mask[panel_id].astype(np.uint8))

    torch_stack = np.stack(torch_panels, axis=0)
    np.save(torch_dir / "bragg_torch.npy", torch_stack)

    torch_meta = {
        "device": str(device),
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "beam": {
            "wavelength_A": float(beam_cfg.wavelength_A),
            "polarization_factor": float(beam_cfg.polarization_factor),
            "nopolar": bool(beam_cfg.nopolar),
            "polarization_axis": list(np.asarray(beam_cfg.polarization_axis, dtype=np.float32)),
            "polarization_fraction": float(beam_cfg.polarization_fraction),
        },
        "crystal": {
            "cell": {
                "a": float(crystal_cfg.cell_a),
                "b": float(crystal_cfg.cell_b),
                "c": float(crystal_cfg.cell_c),
                "alpha": float(crystal_cfg.cell_alpha),
                "beta": float(crystal_cfg.cell_beta),
                "gamma": float(crystal_cfg.cell_gamma),
            },
            "mosflm_a_star": list(np.asarray(crystal_cfg.mosflm_a_star, dtype=np.float32)),
            "mosflm_b_star": list(np.asarray(crystal_cfg.mosflm_b_star, dtype=np.float32)),
            "mosflm_c_star": list(np.asarray(crystal_cfg.mosflm_c_star, dtype=np.float32)),
            "misset_deg": list(np.asarray(crystal_cfg.misset_deg, dtype=np.float32)),
            "phi_steps": int(crystal_cfg.phi_steps),
            "osc_range_deg": float(crystal_cfg.osc_range_deg),
            "mosaic_domains": int(crystal_cfg.mosaic_domains),
            "mosaic_spread_deg": float(crystal_cfg.mosaic_spread_deg),
            "N_cells": [int(Na), int(Nb), int(Nc)],
            "scale_override": float(scale),
        },
        "structure_factors": hkl_meta,
        "panel_configs": panel_results,
    }

    with open(torch_dir / "config_torch.json", "w") as fh:
        json.dump(torch_meta, fh, indent=2)
    with open(torch_dir / "panel_metrics.json", "w") as fh:
        json.dump(panel_summaries, fh, indent=2)

    # ROI metrics
    loss_mask = inputs.loss_mask.astype(bool)
    metrics = compute_roi_metrics(Bragg, torch_stack, loss_mask, inputs.panel_slices)
    summary = {
        "n_panels": int(torch_stack.shape[0]),
        "loss_mask_coverage": float(np.mean(loss_mask)),
        "diffbragg_max": float(Bragg.max()),
        "torch_max": float(torch_stack.max()),
        "median_correlation": float(np.median([m["correlation"] for m in metrics])) if metrics else None,
        "median_rmse": float(np.median([m["rmse"] for m in metrics])) if metrics else None,
        "localization_success_rate": float(np.mean([m["peak_localized"] for m in metrics])) if metrics else None,
        "metrics_sample": len(metrics),
    }

    with open(out_root / "metrics.json", "w") as fh:
        json.dump(summary, fh, indent=2)
    with open(out_root / "roi_metrics.csv", "w") as fh:
        fh.write("roi_idx,panel_id,correlation,rmse,mse,max_abs_diff,peak_localized\n")
        for record in metrics:
            fh.write(
                f"{record['roi_idx']},{record['panel_id']},{record['correlation']:.6f},"
                f"{record['rmse']:.6f},{record['mse']:.6f},{record['max_abs_diff']:.6f},{record['peak_localized']}\n"
            )

    print(f"[torch_capture] Torch baseline: {torch_dir/'bragg_torch.npy'}")
    print(f"[torch_capture] Metrics: {out_root/'metrics.json'}")
    print(f"[torch_capture] Median correlation: {summary['median_correlation']}")


if __name__ == "__main__":
    main()
