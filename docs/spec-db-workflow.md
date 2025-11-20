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
6) Loss (Masked MSE)
   - Loss SHALL be `mean(((Bragg - target)[loss_mask])^2)`.
7) Refinement Protocol Architecture
   - **Engine Contract:** The internal Python API (`RefinementEngine` or equivalent) SHALL accept an ordered list of Stage objects and MUST NOT hardcode the Stage A→B→C flow.
   - **CLI Contract (v1):** `refine_one.py` SHALL instantiate the default sequence based on CLI flags:
     1. Stage A (always)
     2. Stage B (only when `--optimize-fhkl` is supplied)
     3. Stage C (only when `--optimize-det` is supplied)
   - **Configuration:** External configuration files (YAML/JSON) are out of scope for v1.
   - Stage Interface:
     1. **Active Parameters:** Each stage MUST enumerate which parameter groups (Crystal, Detector, Source, Structure factors, Scale) are trainable; all others MUST be frozen.
     2. **Optimizer Config:** Learning rate schedule (or optimizer choice), convergence tolerance, and max iterations MUST be set per stage.
     3. **Physics Toggles:** Flags such as interpolation on/off, HKL padding requirements, polarization/solid-angle parity MUST be declared so simulators can be configured deterministically.
   - State Persistence:
     - Simulator/optimizer state (current best parameters) MUST persist between stages, and telemetry MUST be aggregated per stage (e.g., `history["stage_0_A"]`, `history["stage_1_C"]`).
   - Standard Stages (Normative Definitions):
    - **Stage A (Geometry & Scale):**
      - Trainable: Unit cell logs/angles, orientation (quaternion → XYZ), global scale.
      - Fixed: Structure factors, detector geometry, source spectrum.
      - Physics: Tricubic interpolation (`interpolation=True`) is preferred for smooth orientation/cell gradients whenever the |F| grid includes a ±1 halo; nearest-neighbor (`interpolation=False`) remains a permitted fallback when halo support is unavailable.
    - **Stage B (Structure Factors — optional):**
      - Trainable: Per-reflection Fhkl multipliers SHALL be the default.
      - Symmetry Constraint: Multipliers MUST be keyed by unique Asymmetric Unit (ASU) indices so Friedel mates `(h,k,l)` and `(-h,-k,-l)` share the same parameter.
      - Parameterization: All multipliers MUST be softplus-backed to enforce positivity; aggregated per-shell/global modifiers remain OPTIONAL fallbacks when required by data volume or memory.
      - Fixed: Geometry, global scale unless explicitly declared otherwise.
      - Physics: Tricubic interpolation (`interpolation=True`) with ±1 HKL halo; default_F fallbacks are failure conditions.
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
