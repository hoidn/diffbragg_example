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
        "--use-engine-delegation",
        action="store_true",
        default=False,
        help="Use RefinementEngine with Stage wrapper classes instead of inline helpers"
    )
    ap.add_argument(
        "--enable-stage-b",
        action="store_true",
        default=False,
        help="Enable Stage B Fhkl shell modifiers (requires --use-engine-delegation)"
    )
    ap.add_argument(
        "--enable-stage-c",
        action="store_true",
        default=False,
        help="Enable Stage C detector distance refinement (requires --use-engine-delegation)"
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

    with h5py.File(args.outFile, "w") as h:
        h.create_dataset("score", data=scores)
        h.create_dataset("bragg_scale", data=opt_bragg_scales)

        for i in range(len(scores)):
            h.create_dataset("data/roi%d" % i, data=data_subims[i])
            h.create_dataset("model/roi%d" % i, data=model_subims[i])
            h.create_dataset("bragg/roi%d" % i, data=bragg_subims[i])
            h.create_dataset("bg/roi%d" % i, data=bg_subims[i])

    print("Average score:", 100*np.mean(scores), "+-", 100*np.std(scores))
    print("Fraction of spots well modeled= %.1f%%" % (100*sum([s >= 0.5 for s in scores])/len(scores), ) )
    print(f"Visualize using `python -m dbex.look {args.outFile}`")


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
    )

    try:
        Bragg_refined, refine_telemetry_dict = run_nanobrag_refinement(
            inputs=inputs,
            detector=DL.detector,
            beam=DL.beam,
            crystal=DL.crystal,
            hkl_grid=hkl_grid,
            hkl_metadata=hkl_metadata,
            config=refine_config,
            use_engine_delegation=args.use_engine_delegation
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

    # Score ROIs and write HDF5 output
    _write_torch_outputs(
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


def _write_torch_outputs(
    args,
    DL,
    Bragg,
    inputs,
    masked_mse,
    hkl_telemetry,
    refine_telemetry=None,
    sigma_readout_provenance=None,
    sigma_readout_reference_value=None,
):
    """Write torch backend outputs to HDF5 with diagnostics.

    Args:
        args: Argument namespace from CLI parser
        DL: DataLoad object with experiment/reflection/detector data
        Bragg: Simulated Bragg intensities array
        inputs: RefinementInputs namedtuple with target/loss_mask/panel_slices/trusted_mask
        masked_mse: Masked mean squared error between target and Bragg
        hkl_telemetry: Dictionary with structure-factor metadata:
            - hkl_source: "refined" or "raw"
            - hkl_n_reflections: Number of reflections
            - hkl_mean_amplitude: Mean structure factor amplitude
            - hkl_path: Path to MTZ file used
        refine_telemetry: Optional Dict[str, RefinementTelemetry] from run_nanobrag_refinement
                         (multi-stage: {"A": telemetry_a, "B": telemetry_b, "C": telemetry_c})
                         or single RefinementTelemetry (legacy, mapped to {"A": telemetry})
        sigma_readout_provenance: Optional string describing sigma source (CLI, calibrated map, etc.)
        sigma_readout_reference_value: Optional float (target units) for telemetry/diagnostics
    """
    import h5py
    import numpy as np
    from scipy.optimize import minimize
    from score_trainer import roi_check

    CHECKER = roi_check.roiCheck()

    def func(x, CHECKER, bragg_im, bg_im, dat_im):
        bragg_scale = x[0]
        score = CHECKER.score(dat_im, bragg_scale**2*bragg_im + bg_im)
        resid = 1-score
        return resid

    data_subims = []
    bg_subims = []
    bragg_subims = []
    opt_bragg_scales = []
    model_subims = []
    scores = []

    for i_sb, (pid, (x1, x2, y1, y2)) in enumerate(zip(DL.pids, DL.bbox)):
        bg_im = DL.background_image[pid, y1:y2, x1:x2]
        assert not np.any(np.isnan(bg_im))
        x = slice(x1, x2, 1)
        y = slice(y1, y2, 1)
        dat_im = DL.data[pid, y, x]
        bragg_im = Bragg[pid, y, x]

        min_out = minimize(func, x0=[1], args=(CHECKER, bragg_im, bg_im, dat_im), method="Nelder-Mead")
        if min_out.success:
            opt_bragg_scale = min_out['x'][0]**2
        else:
            opt_bragg_scale = 1

        mod_im = bg_im + opt_bragg_scale*bragg_im
        score = CHECKER.score(dat_im, mod_im)
        # TORCH-CLI-004: Coerce score to float to guard against mocks/non-scalars
        score_float = float(score)
        print("roi=%d : score= %.1f" % (i_sb, score_float*100))

        model_subims.append(mod_im)
        data_subims.append(dat_im)
        bg_subims.append(bg_im)
        bragg_subims.append(bragg_im)
        opt_bragg_scales.append(opt_bragg_scale)
        scores.append(score_float)

    with h5py.File(args.outFile, "w") as h:
        h.create_dataset("score", data=scores)
        h.create_dataset("bragg_scale", data=opt_bragg_scales)

        for i in range(len(scores)):
            h.create_dataset("data/roi%d" % i, data=data_subims[i])
            h.create_dataset("model/roi%d" % i, data=model_subims[i])
            h.create_dataset("bragg/roi%d" % i, data=bragg_subims[i])
            h.create_dataset("bg/roi%d" % i, data=bg_subims[i])

        # Add torch diagnostics group (DIAGNOSTICS-001, SCALE-003)
        diag = h.create_group("torch_diagnostics")
        diag.attrs["masked_mse"] = float(masked_mse)
        diag.attrs["loss_mask_coverage"] = float(inputs.loss_mask.mean())
        diag.attrs["n_rois"] = len(inputs.panel_slices)
        diag.attrs["target_shape"] = str(inputs.target.shape)
        diag.attrs["backend"] = "nanobrag"
        if sigma_readout_provenance is not None:
            diag.attrs["sigma_readout_provenance"] = sigma_readout_provenance
        if sigma_readout_reference_value is not None:
            diag.attrs["sigma_readout_reference_value"] = float(sigma_readout_reference_value)

        # Structure-factor telemetry (SCALE-003: track refined vs raw MTZ)
        diag.attrs["hkl_source"] = hkl_telemetry["hkl_source"]
        diag.attrs["hkl_n_reflections"] = int(hkl_telemetry["hkl_n_reflections"])
        diag.attrs["hkl_mean_amplitude"] = float(hkl_telemetry["hkl_mean_amplitude"])
        diag.attrs["hkl_path"] = str(hkl_telemetry["hkl_path"])

        # Refinement telemetry (TORCH-REFINE-001, TORCH-REFINE-003: multi-stage support)
        # ARCH-REFACTOR-001 Phase B: Dynamic HDF5 serialization from dataclass
        if refine_telemetry is not None:
            import json

            def _coerce_scalar(value):
                """Coerce numpy/torch types to Python scalars for HDF5 attrs."""
                import torch
                if isinstance(value, (np.integer, np.floating)):
                    return value.item()
                elif isinstance(value, torch.Tensor):
                    return value.item() if value.numel() == 1 else float(value)
                return value

            # Normalize to dict format (support legacy single RefinementTelemetry)
            if not isinstance(refine_telemetry, dict):
                # Legacy: single RefinementTelemetry → {"A": telemetry}
                telemetry_dict = {"A": refine_telemetry}
            else:
                telemetry_dict = refine_telemetry

            # Persist per-stage telemetry as separate HDF5 groups
            # Stage A always present; Stage B/C optional when enable_stage_b/enable_stage_c=True
            for stage_label, stage_telem in telemetry_dict.items():
                stage_group = diag.create_group(f"stage_{stage_label}")

                # Dynamic iteration over telemetry fields via to_dict()
                telem_dict = stage_telem.to_dict()

                # Special handling for legacy field names (preserve backward compatibility)
                # Map dataclass field names to HDF5 attr/dataset names
                field_name_map = {
                    "optimizer": "refine_optimizer",
                    "stage": "refine_stage",
                    "history_size": "refine_history_size",
                    "max_iter": "refine_max_iter",
                    "tolerance_grad": "refine_tolerance_grad",
                    "tolerance_change": "refine_tolerance_change",
                    "roi_sample_fraction": "refine_roi_sample_fraction",
                    "roi_count_sampled": "refine_roi_count_sampled",
                    "roi_count_total": "refine_roi_count_total",
                    "status": "refine_status",
                    "message": "refine_message",
                    "param_deltas": "refine_param_deltas",
                }

                # Process each field dynamically
                for key, value in telem_dict.items():
                    if value is None:
                        continue  # Skip None values

                    # Apply field name mapping for backward compatibility
                    hdf5_key = field_name_map.get(key, key)

                    # Handle nested structures
                    if key == "loss_trace_sample" and isinstance(value, list) and len(value) > 0:
                        stage_group.create_dataset("refine_loss_trace_sample", data=value)
                    elif key == "loss_trace_full" and isinstance(value, list) and len(value) > 0:
                        # Store as structured array: [(iteration, loss), ...]
                        loss_trace_full_arr = np.array(value, dtype=[('iteration', 'i4'), ('loss', 'f8')])
                        stage_group.create_dataset("refine_loss_trace_full", data=loss_trace_full_arr)
                    elif key == "best_loss_full" and isinstance(value, tuple):
                        stage_group.attrs["refine_best_loss_full"] = _coerce_scalar(value[0])
                        stage_group.attrs["refine_best_loss_iteration"] = _coerce_scalar(value[1])
                    elif key == "chi_squared_trace_sample" and isinstance(value, list) and len(value) > 0:
                        stage_group.create_dataset("chi_squared_trace_sample", data=value)
                    elif key == "chi_squared_trace_full" and isinstance(value, list) and len(value) > 0:
                        chi2_trace_full_arr = np.array(value, dtype=[('iteration', 'i4'), ('chi_squared', 'f8')])
                        stage_group.create_dataset("chi_squared_trace_full", data=chi2_trace_full_arr)
                    elif key == "chi_squared_best" and isinstance(value, tuple):
                        stage_group.attrs["chi_squared_best"] = _coerce_scalar(value[0])
                        stage_group.attrs["chi_squared_best_iteration"] = _coerce_scalar(value[1])
                    elif key == "masked_mse_trace_sample" and isinstance(value, list) and len(value) > 0:
                        stage_group.create_dataset("masked_mse_trace_sample", data=value)
                    elif key == "masked_mse_trace_full" and isinstance(value, list) and len(value) > 0:
                        mse_trace_full_arr = np.array(value, dtype=[('iteration', 'i4'), ('masked_mse', 'f8')])
                        stage_group.create_dataset("masked_mse_trace_full", data=mse_trace_full_arr)
                    elif key == "masked_mse_best" and isinstance(value, tuple):
                        stage_group.attrs["masked_mse_best"] = _coerce_scalar(value[0])
                        stage_group.attrs["masked_mse_best_iteration"] = _coerce_scalar(value[1])
                    elif key == "canonical_detector_distances_mm" and isinstance(value, list) and len(value) > 0:
                        stage_group.create_dataset(
                            "canonical_detector_distances_mm",
                            data=np.asarray(value, dtype=np.float64),
                        )
                    elif key == "param_deltas" and isinstance(value, dict):
                        # Store as JSON string for backward compatibility
                        stage_group.attrs[hdf5_key] = json.dumps(value)
                    elif key == "stage_modes" and isinstance(value, dict):
                        # Store as JSON string
                        stage_group.attrs[hdf5_key] = json.dumps(value)
                    elif key == "perf_counters" and isinstance(value, dict):
                        # Store as JSON string
                        stage_group.attrs[hdf5_key] = json.dumps(value)
                    elif key in ["telemetry_version", "loss_trace_sample", "loss_trace_full", "best_loss_full"]:
                        # Skip telemetry_version (internal field), already handled traces/best_loss above
                        pass
                    else:
                        # Scalar values: store as HDF5 attrs
                        stage_group.attrs[hdf5_key] = _coerce_scalar(value)

            # Legacy single-stage compatibility: mirror Stage A to top-level attrs if only Stage A exists
            if "A" in telemetry_dict and len(telemetry_dict) == 1:
                stage_a_telem = telemetry_dict["A"]
                telem_a_dict = stage_a_telem.to_dict()

                # Mirror key fields to top-level for backward compatibility
                for key, value in telem_a_dict.items():
                    if value is None:
                        continue

                    # Apply field name mapping for top-level attrs
                    hdf5_key = field_name_map.get(key, key)

                    # Handle nested structures at top-level
                    if key == "loss_trace_sample" and isinstance(value, list) and len(value) > 0:
                        diag.create_dataset("refine_loss_trace_sample", data=value)
                    elif key == "loss_trace_full" and isinstance(value, list) and len(value) > 0:
                        loss_trace_full_arr = np.array(value, dtype=[('iteration', 'i4'), ('loss', 'f8')])
                        diag.create_dataset("refine_loss_trace_full", data=loss_trace_full_arr)
                    elif key == "best_loss_full" and isinstance(value, tuple):
                        diag.attrs["refine_best_loss_full"] = _coerce_scalar(value[0])
                        diag.attrs["refine_best_loss_iteration"] = _coerce_scalar(value[1])
                    elif key == "chi_squared_trace_sample" and isinstance(value, list) and len(value) > 0:
                        diag.create_dataset("chi_squared_trace_sample", data=value)
                    elif key == "chi_squared_trace_full" and isinstance(value, list) and len(value) > 0:
                        chi2_trace_arr = np.array(value, dtype=[('iteration', 'i4'), ('chi_squared', 'f8')])
                        diag.create_dataset("chi_squared_trace_full", data=chi2_trace_arr)
                    elif key == "chi_squared_best" and isinstance(value, tuple):
                        diag.attrs["chi_squared_best"] = _coerce_scalar(value[0])
                        diag.attrs["chi_squared_best_iteration"] = _coerce_scalar(value[1])
                    elif key == "masked_mse_trace_sample" and isinstance(value, list) and len(value) > 0:
                        diag.create_dataset("masked_mse_trace_sample", data=value)
                    elif key == "masked_mse_trace_full" and isinstance(value, list) and len(value) > 0:
                        mse_trace_arr = np.array(value, dtype=[('iteration', 'i4'), ('masked_mse', 'f8')])
                        diag.create_dataset("masked_mse_trace_full", data=mse_trace_arr)
                    elif key == "masked_mse_best" and isinstance(value, tuple):
                        diag.attrs["masked_mse_best"] = _coerce_scalar(value[0])
                        diag.attrs["masked_mse_best_iteration"] = _coerce_scalar(value[1])
                    elif key == "canonical_detector_distances_mm" and isinstance(value, list) and len(value) > 0:
                        diag.create_dataset(
                            "canonical_detector_distances_mm",
                            data=np.asarray(value, dtype=np.float64),
                        )
                    elif key == "param_deltas" and isinstance(value, dict):
                        diag.attrs[hdf5_key] = json.dumps(value)
                    elif key in ["telemetry_version", "loss_trace_sample", "loss_trace_full", "best_loss_full", "stage_modes", "perf_counters"]:
                        # Skip internal fields or already handled
                        pass
                    elif key in ["optimizer", "stage", "history_size", "max_iter", "tolerance_grad", "tolerance_change",
                                 "roi_sample_fraction", "roi_count_sampled", "roi_count_total", "status", "message",
                                 "sigma_readout_provenance", "sigma_readout_reference_value", "variance_floor_value",
                                 "variance_floor_clamp_fraction", "canonical_stage_label", "canonical_chi_squared",
                                 "canonical_chi_squared_iteration", "canonical_roi_count"]:
                        # Mirror scalar attrs to top-level
                        diag.attrs[hdf5_key] = _coerce_scalar(value)

    # TORCH-CLI-004: Guard against empty scores collection
    if len(scores) > 0:
        print("Average score:", 100*np.mean(scores), "+-", 100*np.std(scores))
        print("Fraction of spots well modeled= %.1f%%" % (100*sum([s >= 0.5 for s in scores])/len(scores), ))
    else:
        print("Average score: N/A (no ROIs processed)")
        print("Fraction of spots well modeled= N/A (no ROIs processed)")


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
