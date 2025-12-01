"""Torch backend HDF5 writer with ROI scoring and telemetry serialization.

This module consolidates the shared torch output writer previously embedded
in dbex.refine_one, ensuring a single canonical /torch_diagnostics schema
per DIAGNOSTICS-001 and consistent RefinementTelemetry serialization per
ARCH-REFINE-001 Phase C.2.

Dependencies (transitive):
    - h5py, numpy, scipy.optimize (ROI scoring loop)
    - score_trainer.roi_check (roiCheck scorer per legacy DiffBragg parity)
    - RefinementTelemetry dataclass (dbex.refinement) for telemetry serialization

Contracts:
    - write_torch_outputs(args, data_load, bragg, inputs, masked_mse, hkl_telemetry, ...)
      Writes HDF5 with /torch_diagnostics group, ROI triptychs (data/model/bragg/bg/variance),
      per-ROI scores/bragg_scales, and multi-stage RefinementTelemetry when provided.
    - HDF5 schema is byte-for-byte compatible with prior dbex.refine_one._write_torch_outputs
      (DIAGNOSTICS-001), preserving dataset names, attribute keys, and JSON serialization.

Architecture references:
    - docs/architecture/live_backend.md:23 (torch backend I/O migration)
    - docs/spec-db-workflow.md:33 (RefinementEngine/telemetry contract)
    - docs/spec-db-core.md:86-90 (variance model: V = max(I_model + sigma_rdout^2, sigma_floor^2))

Change Log:
    - 2025-12-01 (ARCH-REFINE-001 Phase C.2): Extracted from dbex.refine_one._write_torch_outputs
      to shared module dbex.io.writer; no schema changes, signature identical except
      parameter name (DL→data_load for API clarity).
"""


def write_torch_outputs(
    args,
    data_load,
    bragg,
    inputs,
    masked_mse,
    hkl_telemetry,
    refine_telemetry=None,
    sigma_readout_provenance=None,
    sigma_readout_reference_value=None,
):
    """Write torch backend outputs to HDF5 with diagnostics.

    Serializes ROI-scored triptychs (data/model/bragg/bg/variance), per-ROI scores,
    and multi-stage refinement telemetry under /torch_diagnostics group. Implements
    the canonical schema per DIAGNOSTICS-001 and PHYSICS-LOSS-001/003.

    Args:
        args: Argument namespace from CLI parser with:
            - outFile: Output HDF5 path
            - sigma_floor: Variance floor in target units (default 1.0)
            - adu_per_photon: Optional ADU→photon gain (None or >0)
        data_load: DataLoad object with:
            - data: Target intensities array (n_panels, slow, fast)
            - background_image: Background per panel
            - detector: DIALS Detector with panel metadata
            - pids: Panel IDs per ROI
            - bbox: Bounding boxes per ROI (x1, x2, y1, y2)
        bragg: Simulated Bragg intensities array (n_panels, slow, fast)
        inputs: RefinementInputs namedtuple with:
            - target: Target tensor (same shape as bragg)
            - loss_mask: Boolean mask (1=trusted, 0=excluded)
            - panel_slices: ROI panel slice metadata
            - trusted_mask: Per-panel trusted mask
        masked_mse: Masked mean squared error between target and Bragg (float)
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

    Notes:
        - ROI scoring loop uses score_trainer.roi_check.roiCheck per legacy parity
        - Variance computation follows spec-db-core.md §86-90: V = max(I_model + sigma_rdout^2, sigma_floor^2)
        - HDF5 schema matches prior dbex.refine_one._write_torch_outputs (DIAGNOSTICS-001)
        - Multi-stage telemetry serialization supports RefinementEngine protocol (ARCH-ENGINE-003)
        - TORCH-CLI-004: Score coercion guards against mocked/non-scalar values
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

    for i_sb, (pid, (x1, x2, y1, y2)) in enumerate(zip(data_load.pids, data_load.bbox)):
        bg_im = data_load.background_image[pid, y1:y2, x1:x2]
        assert not np.any(np.isnan(bg_im))
        x = slice(x1, x2, 1)
        y = slice(y1, y2, 1)
        dat_im = data_load.data[pid, y, x]
        bragg_im = bragg[pid, y, x]

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

    # Compute variance per spec-db-core.md §86-90: V = max(I_model + sigma_readout^2, sigma_floor^2)
    variance_subims = []
    # Extract sigma_readout from function parameter (already in target units after _resolve_sigma_readout)
    sigma_readout = sigma_readout_reference_value if sigma_readout_reference_value is not None else 3.0
    # Use args.sigma_floor directly
    sigma_floor_for_variance = args.sigma_floor
    if args.adu_per_photon is not None and args.adu_per_photon > 0:
        sigma_floor_for_variance = args.sigma_floor / args.adu_per_photon

    for i in range(len(scores)):
        variance_i = model_subims[i] + sigma_readout**2
        variance_i = np.maximum(variance_i, sigma_floor_for_variance**2)
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
        h.create_dataset("sigma_floor", data=sigma_floor_for_variance)

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
