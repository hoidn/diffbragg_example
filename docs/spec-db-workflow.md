# spec-db-workflow.md — Workflow and Staging (Normative)

Overview (Normative)
- Purpose: Specify the end‑to‑end pipeline from data ingestion through masking/calibration to simulation, loss, and staged refinement.

Status
- This workflow targets the planned `nanobrag_torch` backend. The current repository exposes only the DiffBragg entry point and may not reflect these steps verbatim.
- For now, run `python -m dbex.refine_one` (see `dbex/refine_one.py:5-26`).

Pipeline (Normative)
1) Ingest Experiment/Reflections (DIALS/dxtbx)
   - Read `.expt` and `.refl`; filter by `id == exptIdx`.
   - Extract panel geometry (origin, axes, pixel size, image size, directed distance, beam centre) and beam/crystal parameters.
2) Background Estimation (simtbx)
   - Call `get_roi_background_and_selection_flags` to produce `background_image` with −1 outside ROIs and collect ROI bboxes + pids.
   - Optional parity: recompute background using a DIALS trusted mask rather than `data < 0`.
3) Mask Preparation
   - Trusted mask (tuple of flex.bool per panel) SHALL be converted to boolean arrays `[panel, slow, fast]`.
   - Simulator mask SHALL be 0/1 floats (1=include). Loss mask SHALL be `(background >= 0) ∧ trusted_mask`.
4) Calibration Policy (ADU vs Photons)
   - If `--adu-per-photon` is provided, target SHALL be converted to photons by dividing by this factor; else target remains in ADU.
   - A learnable global positive scale SHALL be included when training in ADU; recommended initialization is mean(target)/mean(sim_initial) over a small ROI sample.
5) Per‑Panel Simulation
   - Build one Detector per panel (CUSTOM convention), with square‑pixel guard and explicit beam centre.
   - Run Simulator per panel and stitch into a full‑frame `Bragg` tensor matching `[panel, slow, fast]`.
   - ROI‑only compute MAY be used by constructing cropped Detectors per ROI and stitching outputs.
6) Loss (Variance-Weighted / Chi-Squared)
   - Loss SHALL be `Sum( (Bragg - target)^2 / (Bragg.detach() + sigma_rdout^2) )` over trusted pixels.
   - This approximates an IRLS (Iteratively Reweighted Least Squares) objective compatible with Poisson + Readout noise.
   - The denominator `V = I_model + sigma_rdout^2` MUST be detached from the computation graph to prevent attraction to infinity.

7) Refinement Protocol Architecture
   - **Engine Contract:** The internal Python API (`RefinementEngine` or equivalent) SHALL accept an ordered list of Stage objects and MUST NOT hardcode the Stage A→B→C flow.
   - **Standard Stages (Normative Definitions):**
    - **Stage A (Geometry & Scale):**
      - Trainable: Unit cell logs/angles, orientation (quaternion → XYZ), global scale.
      - Fixed: Structure factors, detector geometry, source spectrum.
      - Physics: Tricubic interpolation (`interpolation=True`) is preferred for smooth orientation/cell gradients whenever the |F| grid includes a ±1 halo; nearest-neighbor (`interpolation=False`) remains a permitted fallback when halo support is unavailable.
    - **Stage B (Structure Factors — optional):**
      - Trainable: Per-reflection Fhkl multipliers mapped to unique ASU indices SHALL be the default (Parity Mode).
      - Fallback: Aggregated per-shell modifiers (Shell Mode) are PERMITTED as an optimization or regularization strategy but MUST NOT be the default.
      - Physics: Tricubic interpolation (`interpolation=True`) with ±1 HKL halo is MANDATORY.
     - **Stage C (Detector):**
       - Trainable: Per-panel translation along detector normal (distance offsets).
       - Fixed: Crystal, scale, Fhkl.
       - Physics: Tricubic interpolation (`interpolation=True`) is MANDATORY so detector motion yields differentiable HKL gradients.

Optimization Strategy (Normative)
- Default optimizer SHALL be L‑BFGS for Stage A and Stage C, implemented via `torch.optim.LBFGS` with a closure that recomputes the full loss.
- Parameterization MUST enforce constraints without bound constraints (e.g., logs for lengths, bounded map for angles, quaternion→XYZ for misset).
- ROI minibatching MAY be used inside the L‑BFGS closure for cost control, provided periodic full‑image validation confirms descent (documented in logs).
- Stage B (structure-factor modifiers) MAY use L‑BFGS or Adam; default SHOULD be L‑BFGS unless per-reflection parameter counts make limited-memory methods impractical.

Gradient Hygiene (Normative)
- Inputs to optimization MUST be torch tensors constructed at loop start; the loss MUST be computed purely from torch tensors on the same graph.
- The optimization path (LBFGS closure and any functions it calls) MUST NOT call `.cpu()`, `.detach()`, `.numpy()`, `.item()`, or run under `with torch.no_grad()` for values that influence the forward pass.
- HDF5 persistence and viewer artifacts MUST be written from detached copies outside the optimization step.
- Stage parameter sets MUST be enumerated per stage; non‑active parameters are treated as constants.
- Stage B assumes differentiable HKL interpolation in nanobrag_torch; if it is unavailable or broken, treat this as an upstream defect rather than introducing non‑differentiable fallbacks in the optimization path.

Outputs (Normative)
- Full‑frame `Bragg` tensor on the simulator device; HDF5 outputs MAY mirror viewer layout for ROIs.

References (Informative)
- docs/spec-db-core.md; docs/config_crosswalk.md; plans/nanobrag_integration_plan.md.
