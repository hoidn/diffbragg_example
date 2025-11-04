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

    return ap


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

    # Prepare inputs via bridge (with optional ADU→photon conversion)
    inputs = prepare_refinement_inputs(
        data=DL.data,
        background_image=DL.background_image,
        trusted_mask=DL.trusted_mask,
        bbox=DL.bbox,
        pids=DL.pids,
        detector=DL.detector,
        adu_per_photon=args.adu_per_photon
    )

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
    device = torch.device('cpu')  # Force CPU for reproducibility

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

    hkl_grid, hkl_metadata = build_structure_factor_grid(
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

        # Instantiate models
        detector_model = Detector(detector_config)
        crystal_model = Crystal(crystal_config)

        # Attach HKL data to crystal model
        crystal_model.hkl_data = hkl_grid
        crystal_model.hkl_metadata = hkl_metadata

        # Run simulator with optional beam_config (SCALE-005: enables sample clipping when N_cells present)
        if calibration_metadata is not None:
            simulator = Simulator(
                detector=detector_model,
                crystal=crystal_model,
                beam_config=beam_config
            )
        else:
            simulator = Simulator(detector=detector_model, crystal=crystal_model)
        panel_output = simulator.run()  # Returns torch.Tensor on device

        # Move to CPU and convert to numpy
        panel_output_np = panel_output.cpu().detach().numpy().astype(np.float32)

        # Apply sqrt(spot_scale_override) post-simulation (SCALE-002)
        panel_output_scaled = panel_output_np * sqrt_spot_scale

        # Store in Bragg array
        Bragg[panel_id] = panel_output_scaled

    print(f"[nanobrag backend] Simulator complete. Bragg shape: {Bragg.shape}")
    print(f"[nanobrag backend] Bragg stats: min={Bragg.min():.3e}, max={Bragg.max():.3e}, mean={Bragg.mean():.3e}")

    # Compute masked MSE for torch diagnostics
    masked_diff = np.where(inputs.loss_mask, inputs.target - Bragg, 0.0)
    masked_mse = (masked_diff ** 2).sum() / inputs.loss_mask.sum()

    print(f"[nanobrag backend] Masked MSE: {masked_mse:.2e}")

    # Prepare structure-factor telemetry for diagnostics (SCALE-003)
    hkl_telemetry = {
        "hkl_source": hkl_source,
        "hkl_n_reflections": len(hkl_indices),
        "hkl_mean_amplitude": float(hkl_amplitudes.mean()),
        "hkl_path": hkl_path if hkl_path else ""
    }

    # Score ROIs and write HDF5 output
    _write_torch_outputs(args, DL, Bragg, inputs, masked_mse, hkl_telemetry)

    print(f"Visualize using `python -m dbex.look {args.outFile}`")


def _write_torch_outputs(args, DL, Bragg, inputs, masked_mse, hkl_telemetry):
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
        print("roi=%d : score= %.1f" % (i_sb, score*100))

        model_subims.append(mod_im)
        data_subims.append(dat_im)
        bg_subims.append(bg_im)
        bragg_subims.append(bragg_im)
        opt_bragg_scales.append(opt_bragg_scale)
        scores.append(score)

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

        # Structure-factor telemetry (SCALE-003: track refined vs raw MTZ)
        diag.attrs["hkl_source"] = hkl_telemetry["hkl_source"]
        diag.attrs["hkl_n_reflections"] = int(hkl_telemetry["hkl_n_reflections"])
        diag.attrs["hkl_mean_amplitude"] = float(hkl_telemetry["hkl_mean_amplitude"])
        diag.attrs["hkl_path"] = str(hkl_telemetry["hkl_path"])

    print("Average score:", 100*np.mean(scores), "+-", 100*np.std(scores))
    print("Fraction of spots well modeled= %.1f%%" % (100*sum([s >= 0.5 for s in scores])/len(scores), ))


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
