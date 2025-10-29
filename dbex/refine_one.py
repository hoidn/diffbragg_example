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
    """Run PyTorch nanobrag_torch refinement backend."""
    import h5py
    import numpy as np
    from dbex.nanobrag_bridge import prepare_refinement_inputs

    print(f"[nanobrag backend] Preparing refinement inputs from DataLoad...")

    # Prepare inputs via bridge
    inputs = prepare_refinement_inputs(
        data=DL.data,
        background_image=DL.background_image,
        trusted_mask=DL.trusted_mask,
        bbox=DL.bbox,
        pids=DL.pids,
        detector=DL.detector
    )

    print(f"[nanobrag backend] Target shape: {inputs.target.shape}")
    print(f"[nanobrag backend] Loss mask coverage: {inputs.loss_mask.mean():.4%}")
    print(f"[nanobrag backend] Number of ROIs: {len(inputs.panel_slices)}")

    # Stub Bragg tensor (Gaussian peaks) until nanobrag_torch simulator is available
    # This will be replaced with:
    # from nanobrag_torch import forward_model
    # Bragg = forward_model(detector_config, beam_config, crystal_config, ...)
    print(f"[nanobrag backend] Generating stub Bragg tensor (will use real simulator when available)...")
    Bragg = _stub_bragg_tensor(inputs.target.shape)

    # Compute masked MSE for torch diagnostics
    masked_diff = np.where(inputs.loss_mask, inputs.target - Bragg, 0.0)
    masked_mse = (masked_diff ** 2).sum() / inputs.loss_mask.sum()

    print(f"[nanobrag backend] Masked MSE: {masked_mse:.2e}")

    # Score ROIs and write HDF5 output
    _write_torch_outputs(args, DL, Bragg, inputs, masked_mse)

    print(f"Visualize using `python -m dbex.look {args.outFile}`")


def _stub_bragg_tensor(shape):
    """Generate stub Bragg tensor with Gaussian peaks for testing."""
    import numpy as np

    # Create Gaussian peaks at ROI centers (very simple stub)
    stub = np.random.randn(*shape).astype(np.float32) * 5 + 100
    stub = np.maximum(stub, 0.0)  # No negative intensities
    return stub


def _write_torch_outputs(args, DL, Bragg, inputs, masked_mse):
    """Write torch backend outputs to HDF5 with diagnostics."""
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

        # Add torch diagnostics group
        diag = h.create_group("torch_diagnostics")
        diag.attrs["masked_mse"] = float(masked_mse)
        diag.attrs["loss_mask_coverage"] = float(inputs.loss_mask.mean())
        diag.attrs["n_rois"] = len(inputs.panel_slices)
        diag.attrs["target_shape"] = str(inputs.target.shape)
        diag.attrs["backend"] = "nanobrag"

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
