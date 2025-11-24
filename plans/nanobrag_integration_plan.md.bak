# Integrating `nanobrag_torch` as the Refinement Backend

## Overview
- Replace the DiffBragg `hopper`-based optimizer in `dbex` with a PyTorch refinement loop powered by `nanobrag_torch`, while leaving the trusted simtbx/DIALS data-preparation pipeline intact.
- Produce the full Bragg model image (`Bragg`) matching `DataLoad.data` so the downstream ROI scoring and visualization code remain unchanged.
- Maintain scientific equivalence by mirroring the staged refinement strategy (crystal → Fhkl → detector) and validating against the existing workflow.

Estimated timeline: 12–18 engineering days (5 phased milestones with validation).

## Incorporated Clarifications (from tool maintainers)
- Multi‑panel: Simulate one Detector per DIALS panel; stitch into `[panel, slow, fast]`. Use CUSTOM convention with explicit beam center (no MOSFLM +0.5 offset).
- Detector mapping: Use `panel.get_directed_distance()` for distance; set `beam_center_s/beam_center_f` in that order, swapping dxtbx’s return `(fast, slow)` to `(s, f)`. Provide `custom_*` basis vectors from panel axes; set `custom_beam_vector` to sample→source (normalized −s0).
- ROI semantics: simtbx background fills non‑ROI pixels with −1; ROI bbox is `(x1, x2, y1, y2)` with exclusive upper bounds; arrays are indexed `[panel, slow, fast]`. ROI/mask in nanobrag_torch is applied after compute; to compute only a subarray, build a cropped Detector.
- Masks: DiffBragg hot pixel mask loader expects a DIALS pickled mask (tuple of flex.bool per panel). Mask logic in DiffBragg inverts the “trusted” mask; confirm orientation and invert as needed before saving.
- Units: image_data_from_expt returns raw ADU; DiffBragg divides by `adu_per_photon` to get photons. For PyTorch, either convert to photons (preferred if metadata exists) or keep ADU and learn a global scale.
- Polarization: For parity, use `polarization_factor=0.0`, `nopolar=False`, polarization axis/Fraction from DIALS when available; else default axis [0,0,1], fraction 0.999.
- Structure factors: No official in‑memory setter; build a dense P1 grid and assign `crystal.hkl_data` and `hkl_metadata`, or round indices and use `io.hkl.read_hkl_file`. Tricubic needs a ±1 halo; otherwise it falls back to default_F.
- Compile/runtime: Reuse a warmed Simulator for fixed shapes; re‑instantiate if detector size/oversample changes (shape changes invalidate compiled kernel caches). ROI defaults to full detector when omitted.
- Pixel geometry: Only square pixels supported per Detector; if fast/slow pitch differs across hardware, instantiate separate Detectors per unique pixel size or defer until `pixel_size_s_mm/pixel_size_f_mm` lands.
 
See supporting API references: docs/nanobrag_api.md (including `ExperimentModel` Stage‑A parameterization), docs/simtbx_api.md, docs/dxtbx_api.md, docs/dials_api.md.

## Stage Policy (Refinement Source Separation)

- Stage A (Crystal + Global Scale): Simulator SHOULD enable tricubic interpolation with a ±1 halo to retain smooth gradients. Nearest-neighbor lookup is a permitted fallback only when halo support is unavailable. Grid bounds derive from the MTZ envelope; UB changes do not require grid rebuild in this stage.
- Stage B (ASU Fhkl Modifiers): Simulator SHALL enable tricubic interpolation and the |F| grid MUST include a ±1 halo in h/k/l. Any default_F fallback when interpolation is enabled is a failure condition for Stage B, and per-ASU symmetry constraints MUST be enforced.

Mapping-Aligned Baseline (Stage A → B/C)
- For any refinement that claims Spec-DB mapping parity, Stage A defines the canonical baseline:
  - Geometry, masks, sigma tensors, and `RefinementInputs` are constructed per DB-AT-024 and `spec-db-conformance.md` (Mapping-Aligned Stage-A Initialization).
  - The Stage A zero point (all geometry deltas zero, baseline scale) MUST reproduce the `simulate_forward_once` Bragg tensor for the same `RefinementInputs` and HKL grid.
- Stage B and Stage C SHALL be implemented strictly as extensions of this mapping-aligned Stage A baseline:
  - Stage B (structure factors) refines Fhkl multipliers on top of the Stage A zero point without introducing a new geometry or loss definition.
  - Stage C (detector microslip) applies detector distance deltas relative to the same Stage A mapping geometry and MUST preserve the variance-weighted loss semantics already validated for Stage A.

## Phase 0 – Environment & Baseline (verification only, 1–2 days)
- Environment Freeze: Do not install or upgrade packages, clone external repos, or modify toolchains. If `nanobrag_torch` or its tests are unavailable, record a blocker in `docs/fix_plan.md` and proceed with evidence‑only steps.
- Verify imports and runtime flags without modification:
  - `python -c "import dbex; import torch; print(torch.__version__)"`
  - Confirm `KMP_DUPLICATE_LIB_OK=TRUE` is exported for torch-based tests.
- If nanoBragg docs are present in the workspace, you MAY run the bundled CPU/CUDA smoke tests for verification only (`nanoBragg/docs/development/pytorch_runtime_checklist.md`). Do not attempt to fetch/install missing components.
- Capture the current DiffBragg output for a representative dataset (`refine_one` HDF5 + ROI scores) as the baseline for parity checks.

## Phase 1 – Data Preparation Bridge (2–3 days)

### Objectives
Provide a bridge that converts `DataLoad` outputs and DIALS experiment metadata into tensors and configuration objects consumable by `nanobrag_torch`.

### Tasks
- Extend `DataLoad` usage with a helper (e.g., `prepare_refinement_inputs(args)`) that returns:
  - `target_tensor`: background-subtracted image (`data - background`) with invalid pixels zeroed.
  - `bg_mask_tensor`: boolean mask where the background estimate is trusted (`background >= 0`).
  - `trusted_mask_tensor`: boolean mask from the DIALS trusted mask (1 = include, 0 = exclude), panel-aligned.
  - `panel_slices`: list of per-panel `(panel_id, slice_y, slice_x)` selectors for reconstructing the final image.
- Units: If `adu_per_photon` is available (DiffBragg parameter or panel metadata), convert ADU→photons for `target_tensor`; otherwise retain ADU and introduce a learnable global scale in Phase 2.
- Mask format: Accept only DIALS pickled masks (tuple of flex.bool per panel). Invert the trusted mask to “hot/bad” as needed before persisting to the DiffBragg‑style path (for reproducibility with the legacy flow).
- From `ExperimentList[exptIdx]`, build:
  - `CrystalConfig`: populate unit cell lengths/angles from `crystal.get_unit_cell().parameters()`. Inject MOSFLM A* via columns of `crystal.get_A()` to seed orientation. Set spindle/phi from goniometer/scan; for stills use `phi_steps=1`, `osc_range_deg=0`.
  - `BeamConfig`: wavelength (`beam.get_wavelength()`), polarization axis/fraction when present; `polarization_factor=0.0`, `nopolar=False` for parity; default to axis [0,0,1], fraction 0.999 if absent.
  - `DetectorConfig` per panel (CUSTOM convention): for each `detector[i]`, use panel axes as `custom_*` vectors; `distance_mm=panel.get_directed_distance()`. Compute beam center from `panel.get_beam_centre(beam.get_s0())` then assign `beam_center_s/beam_center_f` (swap dxtbx fast/slow). Mark `beam_center_source="explicit"`. Set `custom_beam_vector` to normalized sample→source (−s0).
- Create an adapter module (`dbex.nanobrag_bridge`) encapsulating the above logic and returning a `RefinementInputs` dataclass with tensors and configs already on the target torch `device`.
 
References: docs/simtbx_api.md (ROI semantics, masks), docs/dxtbx_api.md (detector/beam/crystal), docs/nanobrag_api.md (DetectorConfig mapping).

### Detector Pixel Geometry And Dimensions
- Pixel size and square‑pixel guard:
  - Extract `px_fast_mm, px_slow_mm = panel.get_pixel_size()`; enforce `abs(px_fast_mm - px_slow_mm) <= 1e-9` or raise a clear error (rectangular pixels unsupported in a single Detector; see docs/nanobrag_api.md).
  - Set `DetectorConfig.pixel_size_mm = px_fast_mm`.
- Image dimensions (ordering note):
  - Extract `fast_px, slow_px = panel.get_image_size()`.
  - Set `DetectorConfig.spixels = slow_px`, `DetectorConfig.fpixels = fast_px`.

### Mask Handling (Simulator And Loss)
- Load DIALS pickled masks (tuple of flex.bool per panel) to a boolean array `[panel, slow, fast]`, then convert to a device‑local torch tensor.
- Simulator: set `DetectorConfig.mask_array = trusted_mask.float()` (1 = include, 0 = exclude). Do not invert.
- Loss: build `loss_mask = (background >= 0) & trusted_mask` and apply in the variance-weighted loss so simulator and loss share the same inclusion policy.
- If persisting a DiffBragg‑style “hot/bad” mask for ROI preprocessing, invert at save time only.
- Optional background recomputation for parity: If a trusted mask is available, you may re‑run `simtbx.diffBragg.utils.get_roi_background_and_selection_flags` using that mask (instead of `data < 0`) to align background estimation with DiffBragg’s masked ROI semantics; otherwise use the existing `DataLoad.background_image`.

### Units And Scaling
- Images are ADU; simulator outputs photons. Choose one:
  - Provide `--adu-per-photon` and convert `target_tensor = target_tensor / adu_per_photon`.
  - Otherwise keep ADU and rely on a learnable global scale (initialize by mean(target)/mean(sim_initial) over a few ROIs for stability).
 - No `no_Nabc_scale` flag: nanobrag_torch’s lattice factor includes N_cells amplitude by construction; rely on the global scale parameter to absorb any differences relative to DiffBragg’s `no_Nabc_scale` behavior.
  

### Multi-panel Handling (resolved)
 - Treat each DIALS panel independently: `nanobrag_torch` currently models one panel per `Detector`.
 - Generate per-panel detector configs (`PanelConfig`) with:
   - `distance_mm`: `panel.get_directed_distance()` (mm).
   - `beam_center_(s,f)`: from `panel.get_beam_centre(beam.get_s0())` in mm; swap ordering (s,f) for DetectorConfig.
   - `fast_axis`, `slow_axis`, and normal from the panel; map to `custom_*` vectors; use `custom_beam_vector` = sample→source.
 - During simulation, loop over panels, run `NanoBraggSimulator` once per panel, and place the resulting tensor back into the correct slice of a preallocated full-frame tensor:
  ```python
  bragg = torch.zeros_like(target_tensor)
  for panel_id, slices in panel_slices:
      cfg = panel_configs[panel_id]
      sim = build_panel_simulator(cfg, crystal_cfg, beam_cfg, device)
      bragg_panel = sim.run()
      bragg[(panel_id,) + slices] = bragg_panel
  ```
 - This yields a stacked `Bragg` tensor with identical shape/order as `DataLoad.data`, resolving the TODO in `refine_one`.
- Compute‑saving option: If runtime is constrained, simulate per‑ROI by constructing a cropped `DetectorConfig` for each ROI (dimensions set to ROI size and beam center offset by the crop), run a short simulator, and stitch results. Note ROI/mask alone does not reduce compute in nanobrag_torch.

References: docs/nanobrag_api.md (ROI‑only compute), docs/dials_api.md (bbox slicing).

### Consistency Smoke Test (mapping sanity)
- Purpose: verify geometry/beam/crystal mapping before any refinement.
- Steps:
  - Build per‑panel DetectorConfig/BeamConfig/CrystalConfig from `Expt` and `DataLoad` as above.
  - Run a single forward simulation to produce a full‑frame `Bragg` tensor (no parameter updates).
  - For a sample of ROIs (e.g., 32): compute correlation between `Bragg[roi]` and `data[roi] - background[roi]` and verify predicted intensity is spatially localized within the ROI.
  - Produce an overlay HDF5 (or PNGs) for quick visual inspection.
- Acceptance (tunable): median ROI correlation ≥ 0.2 and at least 90% of ROIs have a local max within the central half‑box. If thresholds fail, dump panel geometry, beam center, and basis vectors for debugging.

## Phase 2 – PyTorch Model & Parameterization (3–4 days)

### Objectives
Implement a differentiable refinement model with physically constrained parameters.

### Tasks
- Define `NanoBraggRefinementModel(torch.nn.Module)`:
  - Accepts immutable configuration (panel list, background tensors, structure-factor lookup grid).
  - Registers refinable parameters with stable parameterizations:
    - Unit-cell lengths (`log_a`, etc.) stored as `nn.Parameter`; expose lengths via `torch.exp`.
    - Cell angles: optimize in radians with a bounded re-parameterization to keep them within `(ε, π-ε)`.
    - Crystal orientation: manage a unit quaternion internally; convert to XYZ extrinsic angles each `forward()` and assign to `crystal.config.misset_deg` (applied after MOSFLM A* injection).
    - Overall scale: `softplus`-parameterized scalar to keep positive.
    - Optional: per-ROI or per-panel scales if needed (lazy-initialized from ones).
  - Structure factors:
     - Convert `DataLoad.F` (`cctbx` miller array) to a dense P1 grid in memory: iterate indices, find min/max, allocate tensor, fill amplitudes, and assign `crystal.hkl_data` and `crystal.hkl_metadata`. Alternatively, export to HKL and use `read_hkl_file`.
     - Ensure a ±1 halo or pad like FDUMP to keep tricubic active near the grid edges; otherwise `crystal.interpolate` falls back to `default_F`.
     - Store as a non-trainable buffer initially; add an optional refinement head later (see Open Questions).
 
References: docs/nanobrag_api.md (IO, tricubic halo).
- Seed physical parameters:
  - Lattice factor: set `CrystalConfig.N_cells` via CLI `--nabc a b c` (preferred) or default `(20, 20, 20)` to mirror xtal_refine PHIL; set `CrystalConfig.shape = SQUARE`, `CrystalConfig.fudge = 1.0`.
  - No `N_def` analog in nanobrag_torch; ignore DiffBragg’s `Ncells_def` initially.
  - Global scale: initialize near mean(target)/mean(sim_initial) when training in ADU; initialize near 1.0 in photon mode.
- Implement `forward()` to:
  1. Materialize `CrystalConfig`, `BeamConfig`, and per-panel `DetectorConfig` with the current parameter values.
  2. Invoke the panel simulation loop (Phase 1) to produce the full `Bragg` tensor.
  3. Return a tuple `(bragg_tensor, aux)` where `aux` bundles current physical parameters for logging.

### Outputs
- Drop-in function `run_nanobrag_refinement(inputs, optimizer_cfg)` returning:
  - Final `Bragg` tensor on CPU (numpy array) for ROI scoring.
  - History object with loss trace and parameter snapshots.

## Phase 3 – Training Schedule & Loss (3 days)

### Objectives
Mirror the staged refinement logic from DiffBragg to maintain convergence characteristics.

### Strategy
6) Loss (Variance-Weighted / Chi-Squared)
   - Loss SHALL be `Sum( (Bragg - target)^2 / (Bragg.detach() + sigma_rdout^2) )` over trusted pixels.
   - This implements an IRLS (Iteratively Reweighted Least Squares) objective. `Bragg.detach()` prevents the optimizer from minimizing the variance term to cheat the loss.
   - `sigma_rdout` must be in photon units.
7) Staging
   - Stage A (Geometry & Scale): Simulator SHOULD use tricubic interpolation (`interpolate=True`) if halo is available to ensure smooth gradients for orientation; nearest-neighbor is a permitted fallback.
   - Stage B (Structure Factors): Refine **per-reflection multipliers** (Full Fhkl).
     • **ASU Mapping:** The bridge MUST generate an `asu_mapping_tensor` mapping dense grid indices to unique ASU indices (symmetry constrained).
     • **Gather/Scatter:** The engine uses `torch.gather` to map unique params to the grid.
     • Requires differentiable HKL interpolation (tricubic) with ±1 halo.

Each stage runs within a single training loop, swapping optimizer parameter groups and learning rates rather than rebuilding the model.

### Optimizer Choice (prioritize L‑BFGS)
- Use `torch.optim.LBFGS` as the primary optimizer for Stage A (cell/orientation/scale) and Stage C (detector normal translations). Rationale: Strong curvature information and low parameter count per stage typically yield faster, more stable convergence than first‑order methods.
- Implementation notes:
  - Use a closure that recomputes `(bragg, loss)` end‑to‑end; set `line_search_fn=None` (default) and tune `max_iter`, `history_size` (e.g., 10), `tolerance_grad`, and `tolerance_change`.
  - Maintain parameterizations for constraints (logs for lengths, bounded angles, quaternion→XYZ) so box constraints are not required (PyTorch LBFGS has no bounds).
  - To keep step latency reasonable, optionally evaluate the loss over a fixed ROI minibatch (e.g., 1–2 tiles per panel) during LBFGS inner iterations, and refresh the ROI sample every few outer cycles; validate on full loss periodically.
  - Fall back to Adam (or SGD) only for Stage B ASU multipliers or when experimenting with very large ROI batches that make LBFGS closures too expensive.

### Logging
- Emit structured logs (JSON lines) recording stage transitions, losses, and parameter deltas to simplify validation against the baseline.
- Runtime/caching: Reuse a warmed Simulator per panel while changing differentiable parameters. Rebuild the Detector/Simulator when changing tensor shapes (panel dimensions, oversample factors, ROI detectors).

References: docs/nanobrag_api.md (runtime/caching).

### Refinement Nucleus (new)

Purpose: Define the minimal, verifiable core of the torch refinement loop that can be delivered first and expanded in subsequent iterations. The nucleus focuses on a tiny parameter set, deterministic masked MSE loss, and LBFGS closure semantics with explicit convergence gates and telemetry.

Scope (Stage A first):
- Parameters (initial nucleus):
  - Global scale (ADU mode) or `spot_scale_override` proxy when training in photons
  - One crystal DoF to start (e.g., `cell_a` or a single small orientation perturbation)
- Loss: Variance-weighted Chi-squared (`sum((Bragg - target_tensor)^2 / (Bragg.detach() + sigma_rdout^2))` on the masked subset) evaluated in float64 under gradcheck; float32 otherwise (device/dtype neutral)
- ROI policy: Evaluate loss on a fixed, deterministic subset of ROIs (e.g., 1–2 tiles per panel) during LBFGS inner iterations; validate full-frame loss every `M` outer steps (M≥1). Record both traces.

LBFGS Closure (normative):
- Use `torch.optim.LBFGS(params, history_size≈10, max_iter≈20, line_search_fn=None)`
- Closure recomputes `(bragg, loss)` end-to-end with current parameter values; zeroes grads; calls `loss.backward()`; returns `loss`
- Convergence tolerances:
  - `tolerance_grad`: 1e-7 to 1e-6 (tunable per dataset size)
  - `tolerance_change`: 1e-9 to 1e-7 (tunable)
  - Additional guard: stop early if rolling median of full-loss deltas over the last K validations (K≈3) is ≤ ε (e.g., 1e-5 relative)

Rollback / Early-stop Rules:
- If full-frame validation loss increases by > δ (e.g., 2%) compared to the best seen, revert to the best snapshot and stop
- If gradients are NaN/Inf or any simulator call fails, abort and emit an explicit failure status in telemetry (no partial commits)

Optimizer Telemetry (to HDF5 `/torch_diagnostics`):
- `optimizer`: "LBFGS"; `history_size`, `max_iter`, `tolerance_grad`, `tolerance_change`
- `stage`: "A|B|C" label; `roi_sample_fraction`; `roi_count_sampled`; `roi_count_total`
- `loss_trace_sample`: per-iteration sample-ROI loss values
- `loss_trace_full`: periodic full-frame loss values with iteration index
- `best_loss_full`: best observed full-frame loss and iteration index
- `param_deltas`: per-parameter initial → final snapshot (small JSON with names and deltas)
- `status`: "ok|early_stop|rollback|error" and `message` for failures

Gradient Boundaries (clarification):
- Bridge outputs (targets, masks, telemetry) are numpy/CPU and non‑differentiable by design.
- The differentiable surface begins in refinement: convert inputs to torch tensors once, then keep them on the autograd path through `nanobrag_torch` and the masked‑MSE loss.
- Prohibited anywhere on the optimization path (closure and callees): `.cpu()`, `.detach()`, `.numpy()`, `.item()` on values that influence the forward pass, or `with torch.no_grad()`.
- Allowed detaches: zero‑iteration diagnostics, ROI viewer, HDF5 writes — only outside the LBFGS step/closure.
- Stage B requires differentiable HKL sampling (e.g., tricubic interpolation); if not enabled, Stage B remains out‑of‑scope for that loop.
- Calibration metadata (spot_scale_override, flux/exposure, N_cells) are constants unless explicitly promoted to trainable parameters.
- Test‑only helpers (`simulate_forward_torch`, `compute_masked_mse_loss`) exist for DB‑AT‑010 and MUST NOT be invoked by the production optimization closure.

Acceptance for the Nucleus (Stage A):
- On canonical assets, masked MSE decreases by ≥ X% (e.g., 5–10%) within N≤20 LBFGS steps on the deterministic ROI sample and is non-increasing across the last K validations (K≈3) on the full frame
- `param_deltas` show non-zero updates for at least the chosen DoF and the scale parameter
- Telemetry present with all required keys; no NaN/Inf in final loss

Extensibility:
- After the nucleus: widen Stage A parameter set (full crystal logs/angles), enable Stage C (detector normal translations), and optionally Stage B (ASU multipliers) with the same closure + telemetry contract.

### Stage B — Structure-Factor Refinement

Purpose: Refine structure factors with DiffBragg-equivalent symmetry constraints.

- Default mode (required): Per-ASU multipliers
  - Maintain one positive parameter per unique ASU index; apply as `F′ = Scatter(G_asu, asu_map) * |F|`.
  - Scatter multipliers across `(h,k,l)` and `(-h,-k,-l)` mates; gather summed gradients back to `G_asu`.
  - Requires tricubic interpolation with a ±1 halo so gradients flow through Fhkl samples.
  - Telemetry: `stage_b_mode="asu_scatter"`, `param_count`, `loss_trace_sample/full`, `param_deltas`, optional `fopt_writeback_stats`.

Notes
- ROI minibatching may be used inside the LBFGS closure to control cost; validate on full loss periodically.
- Choose the mode via CLI/config flag; default to `shell` for production, use `per_reflection` for diagnostics/parity reports.

## Phase 4 – CLI Integration & Output (2 days)

### Tasks
- Add a new entry point (`dbex.refine_one_torch` or feature flag) that:
  - Parses existing CLI arguments plus an optional `--backend {diffbragg, nanobrag}` switch.
  - Calls the Phase 1 bridge to obtain tensors/configs.
  - Runs `run_nanobrag_refinement`.
  - Writes the `Bragg` array and derived HDF5 datasets with the same layout as the legacy path, fulfilling the TODO:
    ```python
    Bragg_np = bragg_tensor.cpu().numpy()
    ```
  - Persists optimizer diagnostics into an auxiliary group (`/torch_diagnostics`) for debugging.
- Ensure ROI scoring (`score_trainer.roi_check`) operates on the new `Bragg` array without modification.
- Update `dbex/look.py` to optionally overlay PyTorch diagnostics if present (non-blocking enhancement).

## Phase 5 – Validation & Documentation (3–4 days)

### Synthetic Tests
- Generate a synthetic diffraction image with known parameters using `nanobrag_torch` and verify the refinement recovers them when seeded with offsets.

### Parity Tests
 - Run both backends on the baseline dataset(s) and compare:
   - Final loss / ROI scores.
   - Refined cell parameters, orientation matrices, detector adjustments.
   - Residual maps (`target - Bragg`) saved as images for visual inspection.
 - Document acceptable tolerances (e.g., Δa < 0.1 Å, ROI score within 2 %).
- Include a parity check against the designated parity dataset once it exists; until then, document the skip and dataset gap before moving to real data.
 
References: docs/nanobrag_api.md (golden parity assumptions).

### Documentation Deliverables
- `reports/nanobrag_validation.md` summarizing results.
- Update project README with backend selection instructions and limitations.

## Filesystem and Tempfile Policy
- Torch backend:
  - Avoid on‑disk artifacts during refinement; perform all structure‑factor and parameter updates in memory.
  - When exporting HKL for debugging or parity tests, write under a `TemporaryDirectory()` and clean up on exit.
- DiffBragg fallback (legacy):
  - Replace hardcoded filenames in the legacy DiffBragg path (`_geom_ref.*`, `_geom_groups.txt`, `_geom.out`, `_temp.mtz`) with paths under a `TemporaryDirectory()` context to avoid polluting the working tree.
  - Keep an opt‑in flag (e.g., `--debug-save-artifacts`) to persist outputs for debugging when needed; default is ephemeral.

## Deliverables Checklist
- [ ] `dbex/nanobrag_bridge.py` (or similar) with conversion utilities.
 - [ ] `dbex/torch_model.py` implementing `NanoBraggRefinementModel`.
 - [ ] Updated CLI/entry point with backend toggle.
 - [ ] Automated tests covering data preparation and a short refinement smoke test.
 - [ ] Validation report with parity metrics.
 - [ ] HDF5 outputs containing `Bragg` arrays for both backends.
 - [ ] In‑memory cctbx→dense F grid helper (or HKL export) and optional padding utility for tricubic halos.
 - [ ] Optional ROI‑cropped Detector builder utility for performance‑sensitive runs.
 
References: docs/simtbx_api.md, docs/dxtbx_api.md, docs/dials_api.md, docs/nanobrag_api.md.

## Open Questions & Follow-ups
1. **Rectangular pixel support:** Current Detector supports square pixels only. If fast/slow pitch differs, plan either separate Detector instances per unique pixel size or defer until `pixel_size_s_mm/pixel_size_f_mm` is available.
2. **Structure‑factor refinement scope:** Decide between per‑reflection, per‑shell, or fixed Fhkl strategy after initial performance/gradient tests with tricubic enabled.
3. **Beam polarization & spectral distribution:** Start with single‑source; evaluate multi‑source beam and polarization metadata prevalence in our datasets before enabling.
4. **Gradient stability for large crystals:** For large `N_cells`, consider gradient clipping or smoothing if needed; monitor during synthetic tests.
5. **Memory/performance:** If full‑frame per‑panel simulation exceeds memory budgets, adopt ROI‑cropped Detectors and panel batching. Consider contributing ROI‑aware execution upstream when time permits.
