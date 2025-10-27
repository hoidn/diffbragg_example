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
 
See supporting API references: docs/nanobrag_api.md, docs/simtbx_api.md, docs/dxtbx_api.md, docs/dials_api.md.

## Phase 0 – Environment & Baseline (1–2 days)
- Install `nanobrag_torch` in editable mode from `./nanoBragg2` and add it as a `pyproject.toml` dependency for the `dbex` package.
- Run the bundled CPU and CUDA smoke tests (`docs/development/pytorch_runtime_checklist.md`) to confirm the simulator works on the target hardware.
- Capture the current DiffBragg output for a representative dataset (`refine_one` HDF5 + ROI scores) as the baseline for parity checks.
- Ensure `KMP_DUPLICATE_LIB_OK=TRUE` is set in the environment before importing torch (long‑lived workers and CLI).

## Phase 1 – Data Preparation Bridge (2–3 days)

### Objectives
Provide a bridge that converts `DataLoad` outputs and DIALS experiment metadata into tensors and configuration objects consumable by `nanobrag_torch`.

### Tasks
- Extend `DataLoad` usage with a helper (e.g., `prepare_refinement_inputs(args)`) that returns:
  - `target_tensor`: background-subtracted image (`data - background`) with invalid pixels zeroed.
  - `mask_tensor`: boolean mask where the background estimate is trusted (`background >= 0`).
  - `panel_slices`: list of per-panel `(panel_id, slice_y, slice_x)` selectors for reconstructing the final image.
- Units: If `adu_per_photon` is available (DiffBragg parameter or panel metadata), convert ADU→photons for `target_tensor`; otherwise retain ADU and introduce a learnable global scale in Phase 2.
- Mask format: Accept only DIALS pickled masks (tuple of flex.bool per panel). Invert the trusted mask to “hot/bad” as needed before persisting to the DiffBragg‑style path (for reproducibility with the legacy flow).
- From `ExperimentList[exptIdx]`, build:
  - `CrystalConfig`: populate unit cell lengths/angles from `crystal.get_unit_cell().parameters()`. Inject MOSFLM A* via columns of `crystal.get_A()` to seed orientation. Set spindle/phi from goniometer/scan; for stills use `phi_steps=1`, `osc_range_deg=0`.
  - `BeamConfig`: wavelength (`beam.get_wavelength()`), polarization axis/fraction when present; `polarization_factor=0.0`, `nopolar=False` for parity; default to axis [0,0,1], fraction 0.999 if absent.
  - `DetectorConfig` per panel (CUSTOM convention): for each `detector[i]`, use panel axes as `custom_*` vectors; `distance_mm=panel.get_directed_distance()`. Compute beam center from `panel.get_beam_centre(beam.get_s0())` then assign `beam_center_s/beam_center_f` (swap dxtbx fast/slow). Mark `beam_center_source="explicit"`. Set `custom_beam_vector` to normalized sample→source (−s0).
- Create an adapter module (`dbex.nanobrag_bridge`) encapsulating the above logic and returning a `RefinementInputs` dataclass with tensors and configs already on the target torch `device`.
 
References: docs/simtbx_api.md (ROI semantics, masks), docs/dxtbx_api.md (detector/beam/crystal), docs/nanobrag_api.md (DetectorConfig mapping).

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
1. **Stage A – Crystal + scale (Nabc, orientation, scale):**
   - Freeze structure-factor parameters; optimize crystal parameters for `N_stage_a` iterations using masked MSE:
     ```python
     loss = torch.mean(((bragg - target_tensor)[mask_tensor]) ** 2)
     ```
   - Warm-start the next stage using the final parameter values.
2. **Stage B – Structure factor tweaks (optional):**
   - Enable tricubic interpolation (`crystal.interpolate = True`) to obtain differentiable Fhkl gradients.
   - Optimize a small set of global modifiers (e.g., per-resolution shell scale or `torch.nn.Parameter` multipliers) instead of all individual reflections to reduce dimensionality.
3. **Stage C – Detector microslip:**
   - Introduce small rotation/translation parameters per panel (bounded via `tanh`) to mimic the DiffBragg geometry refinement.
   - Run a short optimization stage with a reduced learning rate.

Each stage runs within a single training loop, swapping optimizer parameter groups and learning rates rather than rebuilding the model.

### Logging
 - Emit structured logs (JSON lines) recording stage transitions, losses, and parameter deltas to simplify validation against the baseline.
- Runtime/caching: Reuse a warmed Simulator per panel while changing differentiable parameters. Rebuild the Detector/Simulator when changing tensor shapes (panel dimensions, oversample factors, ROI detectors).
 
References: docs/nanobrag_api.md (runtime/caching).

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
- Include a parity check against the `simple_cubic` golden configuration shipped with nanobrag_torch for a sanity gate before real data.
 
References: docs/nanobrag_api.md (golden parity assumptions).

### Documentation Deliverables
- `reports/nanobrag_validation.md` summarizing results.
- Update project README with backend selection instructions and limitations.

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
