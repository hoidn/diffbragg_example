#!/usr/bin/env python
"""
Generate canonical golden data for DB-AT-001 parity harness.

Per docs/spec-db-core.md:20-54, docs/spec-db-conformance.md:23-26,
and docs/nanobrag_api.md:22-44:
- Captures paired DiffBragg + nanobrag_torch baselines via refinement pipeline
- Uses refGeom experiment as geometry basis
- Honors [panel, slow, fast] tensor ordering and square-pixel guards
- Stores tensors as .npy files with manifest.json + SHA256 checksums + provenance

Output structure:
    <canonical-out>/
    ├── legacy/
    │   ├── bragg_diffbragg.npy      # DiffBragg baseline [panel, slow, fast]
    │   └── config_diffbragg.json    # DiffBragg metadata
    ├── torch/
    │   ├── bragg_torch.npy          # nanobrag_torch baseline [panel, slow, fast]
    │   ├── target_panel_0.npy       # Background-subtracted targets [slow, fast]
    │   ├── loss_mask_panel_0.npy    # Loss mask [slow, fast] bool
    │   ├── config_torch.json        # Torch config metadata
    │   └── panel_metrics.json       # Per-panel peak stats
    ├── logs/
    │   └── canonical_capture.log    # Capture process log
    ├── metrics.json                 # Parity metrics summary
    └── roi_metrics.csv              # Per-ROI correlation/RMSE
"""

import sys
import json
import hashlib
import logging
import datetime
import numpy as np
import torch
from pathlib import Path
from argparse import ArgumentParser, Namespace
from copy import deepcopy

# Add repo root to path for imports
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from libtbx.phil import parse
from simtbx.command_line.hopper import phil_scope
from simtbx.diffBragg import hopper_utils, hopper_io, utils
from simtbx.modeling.forward_models import diffBragg_forward
from scitbx.array_family import flex

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


def compute_sha256(file_path):
    """Compute SHA256 checksum for a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def to_native(obj):
    """Recursively convert numpy/torch types to native Python types for JSON serialization."""
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, (np.ndarray, torch.Tensor)):
        return [to_native(x) for x in obj.tolist()]
    elif isinstance(obj, dict):
        return {key: to_native(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [to_native(item) for item in obj]
    else:
        return obj


def build_structure_factor_grid(indices, amplitudes, device, scale_override=None):
    """Build dense 3D HKL grid for nanobrag_torch from cctbx reflections.

    Args:
        indices: Miller indices (h, k, l)
        amplitudes: Structure factor amplitudes |F|
        device: torch device
        scale_override: DiffBragg spot_scale_override to apply to structure factors.
                       Since intensity ∝ |F|², scale F by sqrt(scale_override) to
                       match DiffBragg intensity scaling (per docs/config_crosswalk.md:71)
    """
    hkls = np.asarray(indices, dtype=int)
    amps = np.abs(np.asarray(amplitudes, dtype=np.float32))

    # CRITICAL FIX: Apply scale to structure factors
    # DiffBragg multiplies final intensity by spot_scale_override
    # nanobrag_torch has no scale parameter, so we scale F by sqrt(scale)
    # since intensity ∝ |F|² → scale on F² equals spot_scale_override
    logger = logging.getLogger("canonical_capture")
    if scale_override is not None and scale_override > 0:
        scale_factor = np.sqrt(float(scale_override))
        logger.info(f"BEFORE scaling: amps min={amps.min():.3e}, max={amps.max():.3e}, mean={amps.mean():.3e}")
        amps = amps * scale_factor
        logger.info(f"Scaling structure factors by sqrt(scale_override)={scale_factor:.3e}")
        logger.info(f"AFTER scaling: amps min={amps.min():.3e}, max={amps.max():.3e}, mean={amps.mean():.3e}")
    h_min, h_max = hkls[:, 0].min(), hkls[:, 0].max()
    k_min, k_max = hkls[:, 1].min(), hkls[:, 1].max()
    l_min, l_max = hkls[:, 2].min(), hkls[:, 2].max()
    h_range = h_max - h_min + 1
    k_range = k_max - k_min + 1
    l_range = l_max - l_min + 1
    grid = torch.zeros((h_range, k_range, l_range), device=device, dtype=torch.float32)

    # Track HKL statistics for instrumentation
    n_total = len(hkls)
    n_inrange = 0

    for (h, k, l), amp in zip(hkls, amps):
        idx_h = h - h_min
        idx_k = k - k_min
        idx_l = l - l_min

        if 0 <= idx_h < h_range and 0 <= idx_k < k_range and 0 <= idx_l < l_range:
            grid[idx_h, idx_k, idx_l] = float(amp)
            n_inrange += 1

    grid_nonzero_count = int((grid != 0).sum().item())
    grid_min = float(grid.min().item())
    grid_max = float(grid.max().item())
    grid_mean = float(grid.mean().item())

    logger.info(f"Structure factor grid stats: min={grid_min:.3e}, max={grid_max:.3e}, mean={grid_mean:.3e}, nonzero={grid_nonzero_count}")

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
        "n_reflections": int(n_total),
        "n_in_range": int(n_inrange),
        "in_range_fraction": float(n_inrange / n_total) if n_total > 0 else 0.0,
        "grid_nonzero": grid_nonzero_count,
        "grid_min": grid_min,
        "grid_max": grid_max,
        "grid_mean": grid_mean,
    }
    return grid, metadata


def compute_roi_metrics(db_stack, torch_stack, loss_mask, panel_slices, sample_frac=0.2):
    """Compute per-ROI parity metrics (correlation, RMSE, localization) for debugging."""
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


def generate_simple_cubic_golden(
    output_dir: Path,
    hkl_debug_path: Path = None,
    emit_manifest: bool = False,
    fixtures_dir: Path = None
):
    """
    Generate canonical golden dataset using DiffBragg refinement + nanobrag_torch.

    Per NANOBRAG-GOLDEN-001, this captures both legacy (DiffBragg) and torch
    baselines from the same refined experiment, emitting paired full-panel
    [panel, slow, fast] tensors plus provenance metadata.

    Args:
        output_dir: Path to output directory (e.g., plans/active/.../reports/.../golden_dataset/)
        hkl_debug_path: Optional path for HKL debugging JSON (default: output_dir/torch_hkl_debug.json)
        emit_manifest: If True, generate manifest.json with SHA256 checksums (default False)
        fixtures_dir: If provided, copy canonical tensors to fixtures directory (default None)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    legacy_dir = output_dir / "legacy"
    torch_dir = output_dir / "torch"
    logs_dir = output_dir / "logs"
    for path in (legacy_dir, torch_dir, logs_dir):
        path.mkdir(parents=True, exist_ok=True)

    if hkl_debug_path is None:
        hkl_debug_path = output_dir.parent / "torch_hkl_debug.json"

    # Setup logging
    logger = logging.getLogger("canonical_capture")
    logger.setLevel(logging.INFO)
    log_handler = logging.FileHandler(logs_dir / "canonical_capture.log")
    log_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(log_handler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(console_handler)

    logger.info("=== Canonical Golden Dataset Generation ===")

    # Load refGeom experiment
    logger.info("Loading refGeom experiment...")
    args = Namespace(
        mtzFile=str(repo_root / "scaled.mtz"),
        mtzCol="F,SIGF",
        exptName=str(repo_root / "refGeom.expt"),
        exptIdx=0,
        reflName=str(repo_root / "refGeom.refl"),
        maskFile=str(repo_root / "747_mask.pkl"),
    )

    try:
        dl = DataLoad(args)
        logger.info(f"Loaded {len(dl.Refs)} reflections from {args.reflName}")
    except Exception as e:
        logger.error(f"Failed to load DataLoad: {e}")
        logger.error("Ensure refGeom.refl exists (see docs/forward_equivalence.md)")
        sys.exit(1)

    # === DiffBragg Refinement and Baseline Capture ===
    logger.info("Starting DiffBragg refinement (GPU devId=0 per DIFFBRAGG-001)...")
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
        logger.info(f"Refinement macro cycle {cycle+1}/{num_macro}...")
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

        # Convert Famps back to flex.double for customized_copy
        Famps_flex = flex.double(Famps)
        Fopt = dl.F.customized_copy(data=Famps_flex)
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

    logger.info("Refinement converged. Generating DiffBragg baseline...")
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
    logger.info(f"DiffBragg baseline saved: max={Bragg.max():.2f}, shape={Bragg.shape}")

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
        json.dump(to_native(diff_meta), fh, indent=2)

    # === Torch Baseline Capture ===
    logger.info("Building nanobrag_torch configs...")
    device = torch.device("cuda:0")

    beam_stub = create_beam_config(Expt.beam)
    crystal_stub = create_crystal_config(Expt.crystal, Expt)

    # Build trusted masks
    trusted_masks = []
    for panel in Expt.detector:
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
        detector=Expt.detector,
    )

    # FIX: Add flux, beamsize_mm, exposure to BeamConfig
    beam_cfg = TorchBeamConfig(
        wavelength_A=float(beam_stub.wavelength_A),
        polarization_factor=float(beam_stub.polarization_factor),
        nopolar=bool(beam_stub.nopolar),
        polarization_axis=tuple(np.asarray(beam_stub.polarization_axis, dtype=np.float32)),
        dmin=float(beam_stub.dmin),
        flux=float(SIM_fhkl.D.flux),  # CRITICAL: Use DiffBragg flux
        beamsize_mm=float(SIM_fhkl.D.beamsize_mm),  # CRITICAL: Use DiffBragg beamsize
        exposure=1.0,  # Fixed exposure for stills
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

    logger.info("Building structure factor grid...")
    torch_grid, hkl_meta = build_structure_factor_grid(
        Fopt.indices(),
        Fopt.data().as_numpy_array(),
        device=device,
        scale_override=mdl_parm["scale"]  # CRITICAL: Apply DiffBragg scale to match intensity
    )
    logger.info(f"HKL grid: {hkl_meta['n_in_range']}/{hkl_meta['n_reflections']} reflections in range ({hkl_meta['in_range_fraction']*100:.1f}%)")
    logger.info(f"HKL grid nonzero: {hkl_meta['grid_nonzero']}")

    # Write HKL debug JSON
    with open(hkl_debug_path, "w") as fh:
        json.dump(to_native(hkl_meta), fh, indent=2)

    crystal_model = TorchCrystal(crystal_cfg, beam_config=beam_cfg, device=device)
    crystal_model.hkl_data = torch_grid
    crystal_model.hkl_metadata = hkl_meta

    logger.info("Running nanobrag_torch simulator per panel...")
    panel_results = []
    torch_panels = []
    panel_summaries = []

    for panel_id, panel in enumerate(Expt.detector):
        det_stub = create_detector_config(panel, Expt.beam, inputs.trusted_mask[panel_id])
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

        # CRITICAL: Log raw simulator output before any conversions
        raw_torch_output = simulator.run()
        logger.info(f"Panel {panel_id} RAW torch output: device={raw_torch_output.device}, dtype={raw_torch_output.dtype}, "
                   f"shape={raw_torch_output.shape}, min={raw_torch_output.min().item():.6e}, "
                   f"max={raw_torch_output.max().item():.6e}, mean={raw_torch_output.mean().item():.6e}, "
                   f"nonzero={int((raw_torch_output != 0).sum().item())}")

        torch_panel = raw_torch_output.detach().cpu().numpy().astype(np.float32)
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
        logger.info(f"Panel {panel_id}: torch_max={torch_panel.max():.2f}, shape={torch_panel.shape}")

        panel_meta = {
            "panel_id": int(panel_id),
            "distance_mm": float(det_cfg.distance_mm),
            "beam_center_s": float(det_cfg.beam_center_s) if det_cfg.beam_center_s is not None else None,
            "beam_center_f": float(det_cfg.beam_center_f) if det_cfg.beam_center_f is not None else None,
            "pixel_size_mm": float(det_cfg.pixel_size_mm),
        }
        panel_results.append(panel_meta)

        np.save(torch_dir / f"target_panel_{panel_id}.npy", inputs.target[panel_id].astype(np.float32))
        # CRITICAL: Save loss mask as bool (np.bool_) per CONFIG-001 finding
        np.save(torch_dir / f"loss_mask_panel_{panel_id}.npy", inputs.loss_mask[panel_id].astype(bool))

    torch_stack = np.stack(torch_panels, axis=0)
    np.save(torch_dir / "bragg_torch.npy", torch_stack)
    logger.info(f"Torch baseline saved: max={torch_stack.max():.2f}, shape={torch_stack.shape}")

    torch_meta = {
        "device": str(device),
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "beam": {
            "wavelength_A": float(beam_cfg.wavelength_A),
            "polarization_factor": float(beam_cfg.polarization_factor),
            "nopolar": bool(beam_cfg.nopolar),
            "polarization_axis": [float(x) for x in beam_cfg.polarization_axis],
            "flux": float(beam_cfg.flux),
            "beamsize_mm": float(beam_cfg.beamsize_mm),
            "exposure": float(beam_cfg.exposure),
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
            "mosflm_a_star": [float(x) for x in crystal_cfg.mosflm_a_star],
            "mosflm_b_star": [float(x) for x in crystal_cfg.mosflm_b_star],
            "mosflm_c_star": [float(x) for x in crystal_cfg.mosflm_c_star],
            "misset_deg": [float(x) for x in crystal_cfg.misset_deg],
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
        json.dump(to_native(torch_meta), fh, indent=2)
    with open(torch_dir / "panel_metrics.json", "w") as fh:
        json.dump(to_native(panel_summaries), fh, indent=2)

    # === ROI Metrics & Summary ===
    logger.info("Computing parity metrics...")
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
    with open(output_dir / "metrics.json", "w") as fh:
        json.dump(to_native(summary), fh, indent=2)
    with open(output_dir / "roi_metrics.csv", "w") as fh:
        fh.write("roi_idx,panel_id,correlation,rmse,mse,max_abs_diff,peak_localized\n")
        for record in metrics:
            fh.write(
                f"{record['roi_idx']},{record['panel_id']},{record['correlation']:.6f},"
                f"{record['rmse']:.6f},{record['mse']:.6f},{record['max_abs_diff']:.6f},{record['peak_localized']}\n"
            )

    # Clean up temp files
    for temp_file in ("_temp.mtz",):
        temp_path = repo_root / temp_file
        if temp_path.exists():
            temp_path.unlink()

    # === Manifest emission (if requested) ===
    if emit_manifest:
        logger.info("Generating manifest.json with SHA256 checksums...")

        # Capture actual CLI command from sys.argv
        import subprocess
        generator_command = " ".join(sys.argv)

        # Get actual git revision
        try:
            git_rev = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_root,
                text=True
            ).strip()
        except Exception as e:
            logger.warning(f"Could not get git revision: {e}")
            git_rev = "unknown"

        manifest_data = {
            "dataset_name": "simple_cubic_canonical",
            "generation_timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "generator_command": generator_command,
            "git_revision": git_rev,
            "structure_factor_source": "scaled.mtz",
            "experiment_source": "refGeom.expt",
            "files": {}
        }

        # Compute checksums for all tensor files
        tensor_files = [
            ("bragg_diffbragg", legacy_dir / "bragg_diffbragg.npy"),
            ("bragg_torch", torch_dir / "bragg_torch.npy"),
        ]

        # Add per-panel files
        for panel_id in range(len(Expt.detector)):
            tensor_files.append((f"target_panel_{panel_id}", torch_dir / f"target_panel_{panel_id}.npy"))
            tensor_files.append((f"loss_mask_panel_{panel_id}", torch_dir / f"loss_mask_panel_{panel_id}.npy"))

        for key, file_path in tensor_files:
            if file_path.exists():
                sha256 = compute_sha256(file_path)
                manifest_data["files"][key] = {
                    "filename": file_path.name,
                    "sha256": sha256,
                    "size_bytes": int(file_path.stat().st_size),
                }
                logger.info(f"  {file_path.name}: {sha256[:16]}...")

        manifest_path = output_dir / "manifest.json"
        with open(manifest_path, "w") as fh:
            json.dump(to_native(manifest_data), fh, indent=2)
        logger.info(f"Manifest written to {manifest_path}")

        # Compute manifest self-checksum and update it
        manifest_sha256 = compute_sha256(manifest_path)
        manifest_data["manifest_sha256"] = manifest_sha256

        # Rewrite manifest with self-checksum included
        with open(manifest_path, "w") as fh:
            json.dump(to_native(manifest_data), fh, indent=2)
        logger.info(f"  manifest.json: {manifest_sha256[:16]}... (self-checksum)")

    # === Fixture copy (if requested) ===
    if fixtures_dir is not None:
        logger.info(f"Copying canonical tensors to fixtures directory: {fixtures_dir}")
        fixtures_dir = Path(fixtures_dir)
        fixtures_dir.mkdir(parents=True, exist_ok=True)

        # Copy tensors
        import shutil
        files_to_copy = [
            (legacy_dir / "bragg_diffbragg.npy", fixtures_dir / "bragg_diffbragg.npy"),
            (torch_dir / "bragg_torch.npy", fixtures_dir / "bragg_torch.npy"),
        ]

        for panel_id in range(len(Expt.detector)):
            files_to_copy.append((
                torch_dir / f"target_panel_{panel_id}.npy",
                fixtures_dir / f"target_panel_{panel_id}.npy"
            ))
            files_to_copy.append((
                torch_dir / f"loss_mask_panel_{panel_id}.npy",
                fixtures_dir / f"loss_mask_panel_{panel_id}.npy"
            ))

        for src, dst in files_to_copy:
            if src.exists():
                shutil.copy2(src, dst)
                logger.info(f"  Copied {src.name} -> {dst}")

        # Copy manifest if it was generated
        if emit_manifest:
            manifest_src = output_dir / "manifest.json"
            manifest_dst = fixtures_dir / "manifest.json"
            shutil.copy2(manifest_src, manifest_dst)
            logger.info(f"  Copied manifest.json -> {manifest_dst}")

        # Generate metadata.json for fixtures
        metadata = {
            "dataset_name": "simple_cubic_canonical",
            "generation_timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "shape": {
                "bragg": list(torch_stack.shape[1:]),  # [slow, fast] per-panel
                "n_panels": int(torch_stack.shape[0]),
            },
            "detector_config": {
                "pixel_size_mm": float(det_cfg.pixel_size_mm),
                "spixels": int(det_cfg.spixels),
                "fpixels": int(det_cfg.fpixels),
            },
            "provenance": {
                "generator": "scripts/generate_simple_cubic_golden.py",
                "experiment": "refGeom.expt",
                "structure_factors": "scaled.mtz",
                "branch": "integration",
            }
        }

        metadata_path = fixtures_dir / "metadata.json"
        with open(metadata_path, "w") as fh:
            json.dump(to_native(metadata), fh, indent=2)
        logger.info(f"  Wrote metadata.json -> {metadata_path}")

    logger.info("=== Canonical Capture Complete ===")
    logger.info(f"DiffBragg baseline: {legacy_dir/'bragg_diffbragg.npy'} (max={Bragg.max():.2f})")
    logger.info(f"Torch baseline: {torch_dir/'bragg_torch.npy'} (max={torch_stack.max():.2f})")
    logger.info(f"Metrics: {output_dir/'metrics.json'}")
    if summary["median_correlation"] is not None:
        logger.info(f"Median correlation: {summary['median_correlation']:.4f}")
        logger.info(f"Localization success: {summary['localization_success_rate']*100:.1f}%")

    return output_dir


if __name__ == "__main__":
    parser = ArgumentParser(description="Generate canonical golden dataset for DB-AT-001 parity harness")
    parser.add_argument(
        "--canonical-out",
        type=Path,
        default=repo_root / "tests" / "fixtures" / "golden_data" / "simple_cubic",
        help="Output directory for canonical dataset",
    )
    parser.add_argument(
        "--hkldebug",
        type=Path,
        default=None,
        help="Path for HKL debug JSON (default: <canonical-out>/../torch_hkl_debug.json)",
    )
    parser.add_argument(
        "--emit-manifest",
        action="store_true",
        help="Generate manifest.json with SHA256 checksums after capture",
    )
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=None,
        help="Copy tensors to fixtures directory and update manifest",
    )

    args_cli = parser.parse_args()

    output_dir = generate_simple_cubic_golden(
        args_cli.canonical_out,
        args_cli.hkldebug,
        emit_manifest=args_cli.emit_manifest,
        fixtures_dir=args_cli.fixtures
    )

    print(f"\nCanonical dataset written to: {output_dir}")
    print("Next steps:")
    print(f"  1. Inspect metrics: jq '.torch_max' {output_dir}/torch/panel_metrics.json")
    print(f"  2. Check HKL stats: jq '.in_range_fraction' {output_dir.parent}/torch_hkl_debug.json")
    print(f"  3. Run parity tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001")

    if args_cli.emit_manifest:
        print(f"\nManifest emitted to: {output_dir}/manifest.json")
    if args_cli.fixtures:
        print(f"Fixtures copied to: {args_cli.fixtures}")
