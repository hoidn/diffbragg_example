"""
CLI for DBEX single-image refinement.

Supports two backends:
- diffbragg: Legacy DiffBragg refinement (default)
- nanobrag: PyTorch-based nanobrag_torch refinement

Usage:
    python -m dbex.refine_one --backend diffbragg -e expt.json -r refl.refl -i 0 ...
    python -m dbex.refine_one --backend nanobrag -e expt.json -r refl.refl -i 0 ...
"""
from argparse import ArgumentParser
from dbex.io.writer import write_torch_outputs


def create_parser():
    """Create argument parser for refine_one CLI."""
    ap = ArgumentParser(
        description="Refine a single experiment using DiffBragg or nanobrag_torch backend."
    )

    ap.add_argument(
        '--backend',
        type=str,
        choices=['diffbragg', 'nanobrag'],
        default='diffbragg',
        help="Backend to use: 'diffbragg' (default, legacy) or 'nanobrag' (PyTorch-based)"
    )
    ap.add_argument(
        '-e','--exptName',
        type=str,
        required=True,
        help="Path to the DIALS experiment list (.json) file."
    )
    ap.add_argument(
        '-r','--reflName',
        type=str,
        required=True,
        help="Path to the DIALS reflection table (.refl) file."
    )
    ap.add_argument(
        '-i','--exptIdx',
        type=int,
        required=True,
        help="The integer index (id) of the experiment to be refined from the experiment list and reflection table."
    )
    ap.add_argument("-o", "--outFile", type=str, required=True,
                    help="Output HDF5 file path for ROI results")
    ap.add_argument("-m", "--maskFile", type=str, required=True,
                    help="Detector mask file path")
    ap.add_argument("-z", "--mtzFile", type=str, required=True,
                    help="MTZ file containing structure factors")
    ap.add_argument("-c", "--mtzCol", type=str, default="F,SIGF",
                    help="MTZ column names (default: F,SIGF)")
    ap.add_argument("--spot-scale-override", type=float, default=None,
                    help="Optional spot scale override for nanobrag backend (applies sqrt(scale) post-simulation per SCALE-002)")
    ap.add_argument("--adu-per-photon", type=float, default=None,
                    help="Calibration factor to convert ADU to photons (must be >0 if provided). "
                         "When set, targets are converted to photons; otherwise targets remain in ADU "
                         "with learnable global scale per spec-db-workflow.md:20")
    ap.add_argument("--torch-config", type=str, default=None,
                    help="Path to DiffBragg config_torch.json with calibration metadata (spot_scale_override, "
                         "beam flux/exposure/beamsize, N_cells). When provided, overrides --spot-scale-override "
                         "and enables sample clipping per SCALE-005/SCALE-006. Gracefully skipped if missing.")
    ap.add_argument("--refined-mtz", type=str, default=None,
                    help="Path to DiffBragg-refined structure factor MTZ (e.g., refined_structure_factors.mtz). "
                         "When provided, uses refined Fopt instead of raw MTZ amplitudes per SCALE-003/SCALE-004. "
                         "Falls back to --mtzFile if missing or invalid.")
    ap.add_argument(
        "--device",
        type=str,
        default="cuda:0",
        help="Torch device for nanobrag backend tensors (default: cuda:0; falls back to CPU if unavailable)."
    )
    ap.add_argument(
        "--sigma-rdout",
        type=float,
        default=None,
        help="Detector readout noise scalar (photons or ADU) used in the variance-weighted loss "
             "per spec-db-core.md:32-68. MUST be >0 unless a calibrated sigma map is injected; "
             "when omitted and no metadata exists the CLI aborts with an actionable error."
    )
    ap.add_argument(
        "--sigma-map",
        type=str,
        default=None,
        help="Path to calibrated sigma_readout tensors (.npy/.npz or pickled tuple of per-panel arrays). "
             "Values should be in ADU unless --adu-per-photon is supplied, in which case they are converted "
             "to photons alongside the targets per spec-db-core.md:32-68."
    )
    ap.add_argument(
        "--sigma-floor",
        type=float,
        default=1.0,
        help="Variance floor guard in target units (photons or ADU, default: 1.0). "
             "Prevents infinite weights when I_model → 0. Per spec-db-core.md:67, variance is clamped: "
             "V = max(I_model + sigma_rdout^2, sigma_floor^2). Shares units with --sigma-rdout. "
             "When --adu-per-photon is set, both sigma_rdout and sigma_floor are divided by gain. "
             "Telemetry reports the clamp fraction (pixels where floor engaged)."
    )
    ap.add_argument(
        "--enable-stage-b",
        action="store_true",
        default=False,
        help="Enable Stage B Fhkl shell modifiers"
    )
    ap.add_argument(
        "--enable-stage-c",
        action="store_true",
        default=False,
        help="Enable Stage C detector distance refinement"
    )
    ap.add_argument(
        "--report-dir",
        type=str,
        default=None,
        help="Optional directory to save triptych report (PNG per ROI). "
             "When specified, automatically generates triptych visualizations "
             "for all ROIs after refinement completes."
    )

    return ap


def _resolve_sigma_readout(args, dataload):
    """
    Resolve sigma_readout source and provenance per spec-db-core.md:32-68.

    Priority order:
        1. CLI scalar (--sigma-rdout)
        2. Calibrated map supplied via DataLoad.sigma_readout_map (--sigma-map)

    Returns:
        sigma_array: np.ndarray shaped like dataload.data with strictly positive values
        provenance: str describing the source ("cli_override", "calibrated_map", etc.)
        reference_value: float scalar (target units before any ADU→photon conversion)
    """
    import numpy as np

    if args.sigma_rdout is not None:
        if args.sigma_rdout <= 0:
            raise ValueError(
                f"--sigma-rdout must be > 0 (got {args.sigma_rdout}). "
                "spec-db-core.md:32-68 mandates strictly positive readout noise so "
                "variance weights remain physical."
            )
        sigma_value = float(args.sigma_rdout)
        sigma_array = np.full_like(dataload.data, sigma_value, dtype=np.float32)
        return sigma_array, "cli_override", sigma_value

    calibrated_sigma = getattr(dataload, "sigma_readout_map", None)
    sigma_map_source = getattr(dataload, "sigma_readout_map_source", None)
    if calibrated_sigma is not None:
        sigma_array = np.array(calibrated_sigma, dtype=np.float32, copy=True)
        if sigma_array.shape != dataload.data.shape:
            raise ValueError(
                f"Calibrated sigma_readout map shape {sigma_array.shape} "
                f"does not match data shape {dataload.data.shape}."
            )
        if not np.all(sigma_array > 0):
            raise ValueError(
                "Calibrated sigma_readout map must be strictly positive per spec-db-core.md:32-34."
            )
        reference_value = float(np.median(sigma_array))
        provenance = "external_lookup" if sigma_map_source == "external_lookup" else "calibrated_map"
        return sigma_array, provenance, reference_value

    raise ValueError(
        "nanobrag backend requires a positive sigma_readout source (--sigma-rdout, --sigma-map, "
        "or calibrated external_lookup metadata). Per spec-db-core.md:32-68 and "
        "spec-db-workflow.md:26-31 the CLI MUST refuse to run when detector metadata cannot "
        "supply readout noise; pass --sigma-rdout=<photons>, provide a calibrated sigma map via "
        "--sigma-map=<path>, or ensure Experiment.imageset.external_lookup embeds pedestal/dark RMS tiles."
    )


def run_diffbragg_backend(args, DL, devid=0):
    """Run legacy DiffBragg refinement backend."""
    import h5py
    import numpy as np
    from scipy.optimize import minimize
    from score_trainer import roi_check
    from dbex.run_diffbragg import run_diffbragg

    # run model refinement
    Bragg = run_diffbragg(DL, devId=devid)

    # compare model to data
    CHECKER = roi_check.roiCheck()

    # optional mimization function to optimize a per-ROI scale factor
    def func(x, CHECKER, bragg_im, bg_im, dat_im):
        bragg_scale = x[0]
        score = CHECKER.score(dat_im, bragg_scale**2*bragg_im + bg_im)
        resid = 1-score
        return resid

    data_subims = []
    bg_subims = []
    bragg_subims = []
    opt_bragg_scales = []
    opt_bg_scales = []
    opt_offsets = []
    mask_subims = []
    model_subims = []
    scores = []
    for i_sb, (pid,  (x1,x2,y1,y2)) in enumerate(zip(DL.pids, DL.bbox)):
        Y, X = np.indices((y2-y1, x2-x1))
        bg_im = DL.background_image[pid, y1:y2, x1:x2]
        assert not np.any(np.isnan(bg_im))
        x = slice(x1,x2,1)
        y = slice(y1,y2,1)
        dat_im = DL.data[pid,y, x]
        bragg_im = Bragg[pid, y, x]
        min_out = minimize(func, x0=[1], args=(CHECKER, bragg_im, bg_im, dat_im), method="Nelder-Mead")
        if min_out.success:
            opt_bragg_scale = min_out['x'][0]**2
            #opt_bg_scale = min_out['x'][1]**2
            #opt_offset = min_out['x'][2]
        else:
            opt_bragg_scale = 1
            #opt_bg_scale = 1
            #opt_offset = 0

        mod_im =bg_im + opt_bragg_scale*bragg_im
        score = CHECKER.score(dat_im, mod_im)
        print("roi=%d : score= %.1f" % (i_sb, score*100))
        model_subims.append(mod_im)
        data_subims.append( dat_im)
        bg_subims.append(bg_im)
        bragg_subims.append(bragg_im)

        opt_bragg_scales.append(opt_bragg_scale)
        #opt_bg_scales.append(opt_bg_scale)
        #opt_offsets.append(opt_offset)

        scores.append(score)

    # Compute variance per spec-db-core.md §86-90: V = max(I_model + sigma_readout^2, sigma_floor^2)
    variance_subims = []
    sigma_readout = args.sigma_rdout if args.sigma_rdout is not None else 1.0
    sigma_floor = args.sigma_floor
    # Apply ADU→photon conversion if needed (consistent with torch backend)
    if args.adu_per_photon is not None and args.adu_per_photon > 0:
        sigma_readout = sigma_readout / args.adu_per_photon
        sigma_floor = sigma_floor / args.adu_per_photon

    for i in range(len(scores)):
        variance_i = model_subims[i] + sigma_readout**2
        variance_i = np.maximum(variance_i, sigma_floor**2)
        variance_subims.append(variance_i)

    with h5py.File(args.outFile, "w") as h:
        h.create_dataset("score", data=scores)
        h.create_dataset("bragg_scale", data=opt_bragg_scales)

        for i in range(len(scores)):
            h.create_dataset("data/roi%d" % i, data=data_subims[i])
            h.create_dataset("model/roi%d" % i, data=model_subims[i])
            h.create_dataset("bragg/roi%d" % i, data=bragg_subims[i])
            h.create_dataset("bg/roi%d" % i, data=bg_subims[i])
            h.create_dataset("variance/roi%d" % i, data=variance_subims[i])

        # Add variance metadata (spec-db-core.md §86-90)
        h.create_dataset("sigma_readout", data=sigma_readout)
        h.create_dataset("sigma_floor", data=sigma_floor)

    print("Average score:", 100*np.mean(scores), "+-", 100*np.std(scores))
    print("Fraction of spots well modeled= %.1f%%" % (100*sum([s >= 0.5 for s in scores])/len(scores), ) )
    print(f"Visualize using `python -m dbex.look {args.outFile}`")

    # Generate triptych report if --report-dir is specified (Phase B.2)
    if args.report_dir:
        _generate_triptych_report(args.outFile, args.report_dir)


def run_nanobrag_backend(args, DL, devid=0):
    """Run PyTorch nanobrag_torch refinement backend with real simulator.

    Implements:
    - SCALE-001: Structure factors pass through unscaled in HKL grid
    - SCALE-002: Apply sqrt(spot_scale_override) post-simulation
    - SCALE-005: Enable N_cells sample clipping when beam_config provided
    - SCALE-006: CLI loads DiffBragg calibration metadata for zero-iteration parity
    - GEOMETRY-002: Detector configs use analytic Euler inversion
    - HKL-ORIENT-001: Use source→sample incident direction
    - ADR-02: ADU vs photon calibration policy (spec-db-workflow.md:20)
    """
    import h5py
    import numpy as np
    import torch
    from dbex.nanobrag_bridge import (
        prepare_refinement_inputs,
        create_detector_config,
        create_beam_config,
        create_crystal_config,
        build_structure_factor_grid,
        load_calibration_metadata,
        load_refined_mtz
    )

    # Import nanobrag_torch components
    try:
        from nanobrag_torch.simulator import Simulator
        from nanobrag_torch.models.detector import Detector
        from nanobrag_torch.models.crystal import Crystal
    except ImportError as e:
        raise ImportError(
            f"nanobrag_torch is required for nanobrag backend. Import error: {e}"
        )

    print(f"[nanobrag backend] Preparing refinement inputs from DataLoad...")

    # Resolve sigma_readout source before preparing inputs (spec-db-core.md:32-68)
    sigma_readout_array, sigma_provenance, sigma_reference_value = _resolve_sigma_readout(args, DL)
    print(
        "[nanobrag backend] Resolved sigma_readout source="
        f"{sigma_provenance} reference={sigma_reference_value:.6g}"
    )

    inputs = prepare_refinement_inputs(
        data=DL.data,
        background_image=DL.background_image,
        trusted_mask=DL.trusted_mask,
        bbox=DL.bbox,
        pids=DL.pids,
        detector=DL.detector,
        adu_per_photon=args.adu_per_photon,
        sigma_readout=sigma_readout_array,
        sigma_readout_provenance=sigma_provenance,
    )

    sigma_reference_target_units = sigma_reference_value
    if (
        sigma_reference_target_units is not None
        and args.adu_per_photon is not None
        and args.adu_per_photon > 0
    ):
        sigma_reference_target_units = sigma_reference_target_units / args.adu_per_photon

    print(f"[nanobrag backend] Target shape: {inputs.target.shape}")
    print(f"[nanobrag backend] Loss mask coverage: {inputs.loss_mask.mean():.4%}")
    print(f"[nanobrag backend] Number of ROIs: {len(inputs.panel_slices)}")

    # Load calibration metadata (SCALE-006: CLI must forward DiffBragg metadata)
    calibration_metadata = None
    if args.torch_config is not None:
        try:
            calibration_metadata = load_calibration_metadata(args.torch_config)
            print(f"[nanobrag backend] Loaded calibration from {args.torch_config}:")
            print(f"  spot_scale_override={calibration_metadata['spot_scale_override']:.3e}")
            print(f"  beam_flux={calibration_metadata['beam_flux']:.3e}, exposure={calibration_metadata['beam_exposure']:.3e}")
            if calibration_metadata['beamsize_mm'] is not None:
                print(f"  beamsize_mm={calibration_metadata['beamsize_mm']:.3e}")
            if calibration_metadata['N_cells'] is not None:
                print(f"  N_cells={calibration_metadata['N_cells']}")
        except (FileNotFoundError, KeyError, ValueError) as e:
            print(f"[nanobrag backend] WARNING: Could not load calibration metadata from {args.torch_config}: {e}")
            print(f"[nanobrag backend] Falling back to CLI flags and defaults")
            calibration_metadata = None

    # Load structure factors (SCALE-003/SCALE-004: prefer refined MTZ)
    print(f"[nanobrag backend] Building structure factor grid from MTZ...")
    try:
        device = torch.device(args.device)
    except (TypeError, RuntimeError, ValueError) as e:
        raise ValueError(f"Invalid --device '{args.device}': {e}") from e
    if device.type == "cuda" and not torch.cuda.is_available():
        print(f"[nanobrag backend] WARNING: CUDA device requested ({args.device}) but torch reports no CUDA runtime. Falling back to CPU.")
        device = torch.device("cpu")
    print(f"[nanobrag backend] Using device={device} for zero-iteration simulation and refinement.")

    # Try refined MTZ first if provided, FAIL if not consumed (SCALE-007)
    hkl_indices = None
    hkl_amplitudes = None
    hkl_source = "raw"  # Track telemetry: "refined" or "raw"
    hkl_path = None
    if args.refined_mtz is not None:
        try:
            hkl_indices, hkl_amplitudes = load_refined_mtz(args.refined_mtz, column="F")
            hkl_source = "refined"
            hkl_path = args.refined_mtz
            print(f"[nanobrag backend] Using refined structure factors from {args.refined_mtz}")
            print(f"  n_reflections={len(hkl_indices)}, mean_amplitude={hkl_amplitudes.mean():.3e}")
        except (FileNotFoundError, ValueError, ImportError) as e:
            # SCALE-007: Fail fast when --refined-mtz is provided but cannot be loaded
            raise RuntimeError(
                f"Failed to load refined structure factors from --refined-mtz '{args.refined_mtz}': {e}\n"
                f"When --refined-mtz is provided, refined structure factors MUST be consumed.\n"
                f"Ensure the MTZ file exists and contains valid F(+)/F(-) or F/SIGF columns."
            ) from e

    # Use raw MTZ if refined not requested
    if hkl_indices is None:
        hkl_indices = DL.F.indices()
        hkl_amplitudes = DL.F.data()
        hkl_source = "raw"
        hkl_path = args.mtzFile
        print(f"[nanobrag backend] Using raw structure factors from {args.mtzFile}")

    hkl_grid, hkl_metadata, asu_map = build_structure_factor_grid(
        indices=hkl_indices,
        amplitudes=hkl_amplitudes,
        device=device
    )
    print(f"[nanobrag backend] HKL grid shape: {hkl_grid.shape}, nonzero: {hkl_metadata['grid_nonzero']}")

    # Determine spot scale override (SCALE-002: calibration overrides CLI flag)
    if calibration_metadata is not None:
        spot_scale = calibration_metadata['spot_scale_override']
        print(f"[nanobrag backend] Using calibration spot_scale_override={spot_scale:.3e}")
    elif args.spot_scale_override is not None:
        spot_scale = args.spot_scale_override
        print(f"[nanobrag backend] Using CLI spot_scale_override={spot_scale:.3e}")
    else:
        # Default to 1.0 if not provided
        spot_scale = 1.0
        print(f"[nanobrag backend] No spot_scale_override provided, using default={spot_scale:.3e}")

    sqrt_spot_scale = np.sqrt(spot_scale)
    print(f"[nanobrag backend] Will apply sqrt(spot_scale)={sqrt_spot_scale:.3e} post-simulation per SCALE-002")

    # Run simulator per panel
    print(f"[nanobrag backend] Running nanobrag_torch Simulator on {len(DL.detector)} panels...")
    n_panels = len(DL.detector)
    panel_shape = inputs.target.shape[1:]  # (slow, fast)
    Bragg = np.zeros((n_panels, *panel_shape), dtype=np.float32)

    for panel_id in range(n_panels):
        panel = DL.detector[panel_id]

        # Create configs for this panel
        detector_config = create_detector_config(
            panel=panel,
            beam=DL.beam,
            trusted_mask=inputs.trusted_mask[panel_id]
        )

        # Create beam config with optional calibration metadata (SCALE-005/SCALE-006)
        if calibration_metadata is not None:
            beam_config = create_beam_config(
                DL.beam,
                flux=calibration_metadata['beam_flux'],
                beamsize_mm=calibration_metadata['beamsize_mm'],
                exposure=calibration_metadata['beam_exposure']
            )
        else:
            beam_config = create_beam_config(DL.beam)

        # Create crystal config with optional N_cells (SCALE-005: gate sample clipping)
        # apply_n_cells=True only when calibration provides N_cells AND beam_config has flux/exposure
        apply_n_cells = (calibration_metadata is not None and
                        calibration_metadata['N_cells'] is not None)
        if calibration_metadata is not None and calibration_metadata['N_cells'] is not None:
            crystal_config, n_cells_applied = create_crystal_config(
                DL.crystal,
                DL.Expt,
                N_cells=calibration_metadata['N_cells'],
                apply_n_cells=apply_n_cells
            )
        else:
            crystal_config, n_cells_applied = create_crystal_config(DL.crystal, DL.Expt)

        # Use unified factory (TORCH-API-ALIGN-001 Phase B2b(i))
        from dbex.refinement.helpers import create_unified_simulator

        simulator, _, sqrt_scale_value, _ = create_unified_simulator(
            detector_config=detector_config,
            crystal_config=crystal_config,
            beam_config=beam_config,
            hkl_grid=hkl_grid,
            hkl_metadata=hkl_metadata,
            mask_array=detector_config.mask_array if hasattr(detector_config, 'mask_array') else None,
            spot_scale_override=spot_scale,
            device=device,
            dtype=torch.float32,
            calibration_metadata=calibration_metadata
        )
        panel_output = simulator.run()  # Returns torch.Tensor on device

        # Move to CPU and convert to numpy
        panel_output_np = panel_output.cpu().detach().numpy().astype(np.float32)

        # Apply sqrt(spot_scale_override) post-simulation (SCALE-002)
        # Factory returns sqrt_scale_value; use that if available, else fall back to sqrt_spot_scale
        scale_factor = sqrt_scale_value if sqrt_scale_value is not None else sqrt_spot_scale
        panel_output_scaled = panel_output_np * scale_factor

        # Store in Bragg array
        Bragg[panel_id] = panel_output_scaled

    print(f"[nanobrag backend] Simulator complete. Bragg shape: {Bragg.shape}")
    print(f"[nanobrag backend] Bragg stats: min={Bragg.min():.3e}, max={Bragg.max():.3e}, mean={Bragg.mean():.3e}")

    # Compute masked MSE for torch diagnostics
    masked_diff = np.where(inputs.loss_mask, inputs.target - Bragg, 0.0)
    masked_mse = (masked_diff ** 2).sum() / inputs.loss_mask.sum()

    print(f"[nanobrag backend] Masked MSE (zero-iteration): {masked_mse:.2e}")

    # Run Stage A LBFGS refinement nucleus (TORCH-REFINE-001)
    print(f"[nanobrag backend] Running Stage A LBFGS refinement nucleus...")
    from dbex.nanobrag_refinement import run_nanobrag_refinement, RefinementConfig
    from dbex.refinement.context import build_job_context

    # Apply ADU→photon conversion to sigma_floor if adu_per_photon is set (PHYSICS-LOSS-002)
    # Per input.md pitfalls and spec-db-core.md:67, sigma_floor shares units with sigma_rdout (target units)
    sigma_floor_value = args.sigma_floor
    if args.adu_per_photon is not None and args.adu_per_photon > 0:
        sigma_floor_value = args.sigma_floor / args.adu_per_photon

    refine_config = RefinementConfig(
        device=str(device),
        dtype=torch.float32,
        sigma_floor_value=sigma_floor_value,
        sigma_readout_provenance=sigma_provenance,
        sigma_readout_reference_value=sigma_reference_target_units,
        enable_stage_b=args.enable_stage_b,
        enable_stage_c=args.enable_stage_c,
        calibration_metadata=calibration_metadata,  # Thread calibration payload (TOOLING-VIS-001 Phase D.C, DB-AT-027)
    )

    # Build JobContext (ARCH-REFINE-001 Phase B.2)
    # Encapsulates CLI args, DataLoad, calibration metadata, sigma provenance, HKL metadata/ASU map,
    # and RefinementConfig so stages receive consistent job metadata
    job_context = build_job_context(
        cli_args=args,
        dataload=DL,
        calibration_metadata=calibration_metadata,
        sigma_provenance=sigma_provenance,
        sigma_reference_value=sigma_reference_target_units,
        refinement_config=refine_config,
        hkl_metadata=hkl_metadata,
        asu_map=asu_map,
        spot_scale_override=spot_scale,
        hkl_source=hkl_source,
        hkl_path=hkl_path,
    )
    print(f"[nanobrag backend] JobContext built: sigma_provenance={job_context.sigma_provenance}, "
          f"hkl_source={job_context.hkl_source}, spot_scale={job_context.spot_scale_override:.3e}")

    try:
        Bragg_refined, refine_telemetry_dict = run_nanobrag_refinement(
            inputs=inputs,
            detector=DL.detector,
            beam=DL.beam,
            crystal=DL.crystal,
            hkl_grid=hkl_grid,
            hkl_metadata=hkl_metadata,
            config=refine_config,
            job_context=job_context
        )

        # Extract Stage A telemetry (always present); Stage B and Stage C are optional
        refine_telemetry = refine_telemetry_dict["A"]

        # Compute refined masked MSE
        masked_diff_refined = np.where(inputs.loss_mask, inputs.target - Bragg_refined, 0.0)
        masked_mse_refined = (masked_diff_refined ** 2).sum() / inputs.loss_mask.sum()

        print(f"[nanobrag backend] Stage A status: {refine_telemetry.status}")
        print(f"[nanobrag backend] Masked MSE (refined): {masked_mse_refined:.2e}")
        print(f"[nanobrag backend] Improvement: {(masked_mse - masked_mse_refined) / masked_mse * 100:.1f}%")

        # Log Stage B if enabled
        if "B" in refine_telemetry_dict:
            refine_telemetry_b = refine_telemetry_dict["B"]
            print(f"[nanobrag backend] Stage B status: {refine_telemetry_b.status}")

        # Log Stage C if enabled
        if "C" in refine_telemetry_dict:
            refine_telemetry_c = refine_telemetry_dict["C"]
            print(f"[nanobrag backend] Stage C status: {refine_telemetry_c.status}")

        # Use refined Bragg for output
        Bragg = Bragg_refined
        masked_mse = masked_mse_refined

    except Exception as e:
        print(f"[nanobrag backend] WARNING: Refinement failed: {e}")
        print(f"[nanobrag backend] Falling back to zero-iteration Bragg")
        refine_telemetry = None

    # Prepare structure-factor telemetry for diagnostics (SCALE-003)
    # Convert flex arrays to numpy if needed for mean calculation
    if hasattr(hkl_amplitudes, 'as_numpy_array'):
        hkl_amp_array = hkl_amplitudes.as_numpy_array()
    elif hasattr(hkl_amplitudes, 'mean'):
        hkl_amp_array = hkl_amplitudes
    else:
        hkl_amp_array = np.array(hkl_amplitudes)

    hkl_telemetry = {
        "hkl_source": hkl_source,
        "hkl_n_reflections": len(hkl_indices),
        "hkl_mean_amplitude": float(hkl_amp_array.mean() if hasattr(hkl_amp_array, 'mean') else np.mean(hkl_amp_array)),
        "hkl_path": hkl_path if hkl_path else ""
    }

    # Score ROIs and write HDF5 output (ARCH-REFINE-001 Phase C.2: shared writer module)
    write_torch_outputs(
        args,
        DL,
        Bragg,
        inputs,
        masked_mse,
        hkl_telemetry,
        refine_telemetry,
        sigma_readout_provenance=sigma_provenance,
        sigma_readout_reference_value=sigma_reference_target_units,
    )

    print(f"Visualize using `python -m dbex.look {args.outFile}`")

    # Generate triptych report if --report-dir is specified (Phase B.2)
    if args.report_dir:
        _generate_triptych_report(args.outFile, args.report_dir)


# Legacy compatibility alias (ARCH-REFINE-001 Phase C.2: extracted to dbex.io.writer)
_write_torch_outputs = write_torch_outputs


def _generate_triptych_report(h5_path, report_dir):
    """Generate triptych PNGs for all ROIs in HDF5 file.

    Automatically exports triptych visualizations (Data | Model | Residuals Z-Score)
    for all ROIs in the HDF5 file using dbex.vis.plot_triptych.

    Args:
        h5_path: Path to HDF5 file with ROI datasets (data/roi%d, model/roi%d, variance/roi%d)
        report_dir: Output directory for PNG files (created if doesn't exist)

    Notes:
        - Creates report_dir if it doesn't exist (parents=True, exist_ok=True)
        - Generates one PNG per ROI: roi_0000_triptych.png, roi_0001_triptych.png, etc.
        - Gracefully degrades if variance datasets are missing (prints warning, skips ROI)
        - Uses try/except per ROI to prevent one failure from blocking others
        - Prints final message with report directory location
    """
    from pathlib import Path
    from dbex.vis import plot_triptych
    import h5py

    report_path = Path(report_dir)
    report_path.mkdir(parents=True, exist_ok=True)

    with h5py.File(h5_path, 'r') as h5:
        # Determine number of ROIs by probing data/roi%d datasets
        n_rois = 0
        while f"data/roi{n_rois}" in h5:
            n_rois += 1

        if n_rois == 0:
            print("Warning: No ROIs found in HDF5 file, skipping triptych report.")
            return

        print(f"Generating triptych report for {n_rois} ROIs...")

        for roi_idx in range(n_rois):
            try:
                # Read datasets for this ROI
                data = h5[f"data/roi{roi_idx}"][:]
                model = h5[f"model/roi{roi_idx}"][:]

                # Variance is mandatory per Phase B.1 (spec-db-core.md §86-90)
                # but gracefully degrade for old HDF5 files
                variance_key = f"variance/roi{roi_idx}"
                if variance_key not in h5:
                    print(f"Warning: Variance missing for ROI {roi_idx}, skipping triptych.")
                    continue

                variance = h5[variance_key][:]

                # Generate output filename: roi_0000_triptych.png
                out_png = report_path / f"roi_{roi_idx:04d}_triptych.png"

                # Call dbex.vis.plot_triptych with filename parameter for file output
                plot_triptych(data, model, variance, filename=str(out_png))

            except Exception as e:
                # Per input.md pitfalls: wrap each ROI in try/except so one failure
                # doesn't block the rest
                print(f"Warning: Failed to generate triptych for ROI {roi_idx}: {e}")
                continue

    print(f"Triptych report saved to: {report_dir}")


def main(argv=None):
    """Main entry point for CLI."""
    from dbex.data_load import DataLoad

    parser = create_parser()
    args = parser.parse_args(argv)
    devid = 0

    print(f"[DBEX] Loading experiment data...")
    DL = DataLoad(args)

    print(f"[DBEX] Using backend: {args.backend}")

    if args.backend == 'diffbragg':
        run_diffbragg_backend(args, DL, devid)
    elif args.backend == 'nanobrag':
        run_nanobrag_backend(args, DL, devid)
    else:
        raise ValueError(f"Unknown backend: {args.backend}")


if __name__ == "__main__":
    main()
