#!/usr/bin/env python3
import datetime
import json
import logging
from argparse import Namespace
from copy import deepcopy
from pathlib import Path

import numpy as np
import torch
from libtbx.phil import parse
from simtbx.command_line.hopper import phil_scope
from simtbx.diffBragg import hopper_utils, hopper_io, utils
from simtbx.modeling.forward_models import diffBragg_forward

from dbex.run_diffbragg import detector_refinement
from dbex.data_load import DataLoad
from dbex.nanobrag_bridge import (
    prepare_refinement_inputs,
    create_detector_config,
    create_beam_config,
    create_crystal_config,
)
from nanobrag_torch.config import (
    DetectorConfig as TorchDetectorConfig,
    BeamConfig as TorchBeamConfig,
    CrystalConfig as TorchCrystalConfig,
    DetectorConvention as TorchDetectorConvention,
)
from nanobrag_torch.models.detector import Detector as TorchDetector
from nanobrag_torch.models.crystal import Crystal as TorchCrystal
from nanobrag_torch.simulator import Simulator as TorchSimulator

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
    logs_dir = out_root / "logs"
    for path in (legacy_dir, torch_dir, logs_dir):
        path.mkdir(parents=True, exist_ok=True)

    args = Namespace(
        mtzFile=str(repo_root / "scaled.mtz"),
        mtzCol="F,SIGF",
        exptName=str(repo_root / "refGeom.expt"),
        exptIdx=0,
        reflName=str(repo_root / "refGeom.refl"),
        maskFile=str(repo_root / "747_mask.pkl"),
    )
    dl = DataLoad(args)

    # DiffBragg baseline (GPU devId=0 per DIFFBRAGG-001)
    logger = logging.getLogger("canonical_capture.diffbragg")
    logger.setLevel(logging.INFO)
    xtal_refine_phil = repo_root / "dbex" / "dbconfig" / "xtal_refine.phil"
    fhkl_refine_phil = repo_root / "dbex" / "dbconfig" / "fhkl_refine.phil"
    params = phil_scope.fetch(sources=[parse(Path(xtal_refine_phil).read_text())]).extract()
    params_fhkl = phil_scope.fetch(sources=[parse(Path(fhkl_refine_phil).read_text())]).extract()
    for prm in (params, params_fhkl):
        prm.simulator.structure_factors.mtz_name = args.mtzFile
        prm.simulator.structure_factors.mtz_column = args.mtzCol
        prm.roi.hotpixel_mask = args.maskFile

    Expt = deepcopy(dl.Expt)
    Famps = dl.F.data().as_numpy_array()
    Finds = dl.F.indices()
    FMap = {h: amp for h, amp in zip(Finds, Famps)}
    devId = 0
    num_macro = 5
    mdl_parm = None
    SIM_fhkl = None
    for cycle in range(num_macro):
        ref_out = hopper_utils.refine(Expt, dl.Refs, params, return_modeler=True, free_mem=True, gpu_device=devId)
        Expt, _, Modeler, SIM, x = ref_out
        mdl_parm = hopper_utils.get_param_from_x(x, Modeler, as_dict=True)
        for prm in (params, params_fhkl):
            prm.init.Nabc = mdl_parm["Na"], mdl_parm["Nb"], mdl_parm["Nc"]
            prm.init.Ndef = mdl_parm["Nd"], mdl_parm["Ne"], mdl_parm["Nf"]
            prm.init.G = mdl_parm["scale"]
        ref_out_fhkl = hopper_utils.refine(Expt, dl.Refs, params_fhkl, return_modeler=True, free_mem=True, gpu_device=devId)
        _, _, Modeler_fhkl, SIM_fhkl, x_hkl = ref_out_fhkl
        Fidx_to_asu = {i: hkl for hkl, i in SIM_fhkl.asu_map_int.items()}
        refined = np.where(SIM_fhkl.Fhkl_scales != 1)[0]
        new_amps = {}
        for i in refined:
            asu = Fidx_to_asu[i]
            if asu in FMap:
                scale = SIM_fhkl.Fhkl_scales[i]
                new_amp = np.sqrt(scale) * FMap[asu]
                new_amps[asu] = new_amp
        for i_hkl, hkl in enumerate(Finds):
            if hkl in new_amps:
                Famps[i_hkl] = new_amps[hkl]
        Fopt = dl.F.customized_copy(data=Famps)
        Fopt.as_mtz_dataset(column_root_label="F").mtz_object().write(str(repo_root / "_temp.mtz"))
        for prm in (params, params_fhkl):
            prm.simulator.structure_factors.mtz_name = str(repo_root / "_temp.mtz")
            prm.simulator.structure_factors.mtz_column = "F(+),SIGF(+),F(-),SIGF(-)"
        FMap = {h: amp for h, amp in zip(Fopt.indices(), Fopt.data())}
        params.filter_during_refinement.enable = False
        params_fhkl.filter_during_refinement.enable = False
        model_df = hopper_io.save_to_pandas(
            x_hkl,
            Modeler_fhkl,
            SIM_fhkl,
            args.exptName,
            params_fhkl,
            Expt,
            0,
            args.reflName,
            None,
            0,
            write_expt=False,
            write_pandas=False,
            exp_idx=args.exptIdx,
        )
        Expt = detector_refinement(model_df, Expt, dl.Refs, params_fhkl)

    energies = [utils.ENERGY_CONV / Expt.beam.get_wavelength()]
    fluxes = [SIM_fhkl.D.flux]
    mdl_parm = hopper_utils.get_param_from_x(x_hkl, Modeler_fhkl, as_dict=True)
    Bragg = diffBragg_forward(
        Expt.crystal,
        Expt.detector,
        Expt.beam,
        Fopt,
        energies,
        fluxes,
        oversample=SIM_fhkl.D.oversample,
        Ncells_abc=(mdl_parm["Na"], mdl_parm["Nb"], mdl_parm["Nc"]),
        Ncells_def=(mdl_parm["Nd"], mdl_parm["Ne"], mdl_parm["Nf"]),
        beamsize_mm=SIM_fhkl.D.beamsize_mm,
        device_Id=devId,
        spot_scale_override=mdl_parm["scale"],
        cuda=(devId >= 0),
        num_phi_steps=SIM_fhkl.D.phisteps,
        delta_phi=SIM_fhkl.D.phistep_deg,
        spindle_axis=SIM_fhkl.D.spindle_axis,
        no_Nabc_scale=True,
    )
    Bragg = np.asarray(Bragg, dtype=np.float32)
    np.save(legacy_dir / "bragg_diffbragg.npy", Bragg)
    diff_meta = {
        "devId": devId,
        "shape": Bragg.shape,
        "dtype": "float32",
        "max": float(Bragg.max()),
        "min": float(Bragg.min()),
        "num_macro": num_macro,
        "mdl_param": {k: float(v) if isinstance(v, (int, float, np.floating)) else list(v) for k, v in mdl_parm.items()},
        "energies": energies,
        "fluxes": [float(fluxes[0])],
        "oversample": int(SIM_fhkl.D.oversample),
        "beam_size_mm": float(SIM_fhkl.D.beamsize_mm),
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    }
    with open(legacy_dir / "config_diffbragg.json", "w") as fh:
        json.dump(diff_meta, fh, indent=2)

    # Torch capture
    device = torch.device("cuda:0")
    beam_stub = create_beam_config(dl.Expt.beam)
    crystal_stub = create_crystal_config(dl.Expt.crystal, dl.Expt)
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
        polarization_fraction=float(beam_stub.polarization_fraction),
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
        N_cells=(int(mdl_parm["Na"]), int(mdl_parm["Nb"]), int(mdl_parm["Nc"])),
        default_F=0.0,
    )
    torch_grid, hkl_meta = build_structure_factor_grid(Fopt.indices(), Fopt.data().as_numpy_array(), device=device)
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
            oversample=int(SIM_fhkl.D.oversample),
            mask_array=mask_tensor,
        )
        det_model = TorchDetector(det_cfg, device=device)
        simulator = TorchSimulator(crystal_model, det_model, beam_config=beam_cfg, device=device)
        torch_panel = simulator.run().detach().cpu().numpy().astype(np.float32)
        torch_panels.append(torch_panel)
        panel_summaries.append(
            {
                "panel_id": int(panel_id),
                "shape": torch_panel.shape,
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
            "N_cells": list(map(int, crystal_cfg.N_cells)),
            "scale_override": float(mdl_parm["scale"]),
        },
        "structure_factors": hkl_meta,
        "panel_configs": panel_results,
    }
    with open(torch_dir / "config_torch.json", "w") as fh:
        json.dump(torch_meta, fh, indent=2)
    with open(torch_dir / "panel_metrics.json", "w") as fh:
        json.dump(panel_summaries, fh, indent=2)

    # ROI metrics / summary
    loss_mask = inputs.loss_mask.astype(bool)
    metrics = compute_roi_metrics(Bragg, torch_stack, loss_mask, inputs.panel_slices)
    summary = {
        "n_panels": int(torch_stack.shape[0]),
        "loss_mask_coverage": float(np.mean(loss_mask)),
        "diffbragg_max": float(Bragg.max()),
        "torch_max": float(torch_stack.max()),
        "median_correlation": float(np.median([m["correlation"] for m in metrics])) if metrics else None,
        "median_rmse": float(np.median([m["rmse"] for m in metrics])) if metrics else None,
        "localization_success_rate": float(
            np.mean([m["peak_localized"] for m in metrics])
        ) if metrics else None,
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
    for temp_file in ("_temp.mtz",):
        temp_path = repo_root / temp_file
        if temp_path.exists():
            temp_path.unlink()
    print(f"[canonical_capture] DiffBragg baseline: {legacy_dir/'bragg_diffbragg.npy'}")
    print(f"[canonical_capture] Torch baseline: {torch_dir/'bragg_torch.npy'}")
    print(f"[canonical_capture] Metrics: {out_root/'metrics.json'}")


if __name__ == "__main__":
    main()
