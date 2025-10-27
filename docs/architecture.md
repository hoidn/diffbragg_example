# DBEX + PyTorch — Implementation Architecture

Document version: 0.1 (aligned to Spec DB shards)
Spec precedence: docs/spec-db.md (normative); this doc records ADRs, module layout, and developer guidance.

## 1) System Overview

Purpose
- Replace DiffBragg’s optimizer in dbex with a PyTorch‑backed simulator (nanobrag_torch) while retaining DIALS/dxtbx/simtbx for ingestion, ROI/background, and viewer tooling.

Key Ideas
- Per‑panel simulation and stitching to form a full‑frame Bragg tensor shaped `[panel, slow, fast]` identical to `DataLoad.data`.
- Masked MSE over `(background >= 0) ∧ trusted_mask` for refinement; optional ROI‑only compute via cropped Detectors.
- Staged refinement: Stage A (crystal+scale), Stage B (optional F modifiers), Stage C (detector normal translations).

Out‑of‑Scope (v1)
- Separate “defect envelope” (DiffBragg Ncells_def) and per‑reflection Fhkl scaling.
- Rectangular pixels inside a single Detector (square pixels enforced).

## 2) Components and Responsibilities

Existing (dbex/)
- `data_load.py` — Loads Experiment/Reflections/MTZ; runs simtbx background/ROI; exposes:
  - `Expt` (dxtbx Experiment), `Refs` (flex.reflection_table subset),
  - `data` (np array `[panel, slow, fast]`),
  - `background_image` (−1 outside ROIs), `bbox`, `pids` (panel ids).
- `run_diffbragg.py` — Legacy DiffBragg pipeline (kept for back‑compat only).
- `refine_one.py` — CLI driver (to be extended with a torch backend or a sibling entrypoint).
- `look.py` — HDF5 viewer for ROI triptychs.

New (proposed)
- `dbex/nanobrag_bridge.py` — Adapters from dxtbx/simtbx → nanobrag_torch and tensors
  - Builds DetectorConfig (CUSTOM) per panel, BeamConfig, CrystalConfig (unit cell + MOSFLM A*),
  - Converts cctbx Miller array → dense P1 F grid (with optional padding for tricubic halo),
  - Returns tensors: `target_tensor`, `bg_mask_tensor` (background >= 0), `trusted_mask_tensor` (trusted), and `panel_slices`.
- `dbex/torch_model.py` — Refinement model + loop
  - `NanoBraggRefinementModel` with parameters: cell logs/angles, misset (quaternion→XYZ), global scale, optional shell scales;
  - `run_nanobrag_refinement(inputs, optimizer_cfg)` implementing staged schedule.
- `dbex/refine_one_torch.py` (or `--backend nanobrag`) — CLI glue: parse, bridge, refine, write HDF5.

External
- nanobrag_torch (simulator, configs, tricubic F interpolation), dxtbx/DIALS (Experiment, Reflections, geometry), simtbx.diffBragg.utils (image/ROI/background), cctbx (MTZ/F).

## 3) Data Flow and Interactions

End‑to‑End
1) CLI → parse inputs (`.expt/.refl/.mtz`, mask path, exptIdx, device, flags like `--adu-per-photon`, `--nabc`).
2) DataLoad → load Experiment, select reflections for `exptIdx`, get raw images (`data`) and background (`background_image`), ROI bboxes and panel ids.
3) Bridge → build per‑panel DetectorConfig (square‑pixel guard, explicit beam centre, sample→source beam vector), CrystalConfig (unit cell + A*), BeamConfig; build dense F grid; materialize tensors:
   - `target_tensor = data - background` (or photons if converted),
   - `bg_mask_tensor = (background >= 0)`,
   - `trusted_mask_tensor` from DIALS pickled mask (True=trusted),
   - `panel_slices` for each panel (for stitching).
4) Refinement → staged loop produces `bragg_tensor`:
   - Per‑panel Simulator.run(); stitch into `[panel, slow, fast]` full frame.
   - Loss = masked MSE over `(bg_mask_tensor & trusted_mask_tensor)`.
5) Output → HDF5 datasets and ROI viewer compatible with current layout.

Interactions
- Trusted mask feeds both the simulator (`DetectorConfig.mask_array`) and the loss mask; polarity is 1=include (no inversion for simulator path).
- Optional parity: re‑run simtbx background with the trusted mask to replicate DiffBragg ROI filtering logic.

## 4) Parameter Mapping and Refinement

Detector (per panel)
- Fixed: basis vectors, beam vector, beam centre, pixel size, spixels/fpixels.
- Refined (Stage C v1): distance (translation along detector normal) per panel, initialized to 0 mm.
- Optional future: in‑plane beam centre offsets; small rotations with tight bounds.

Beam
- Fixed: wavelength, polarization axis/fraction (or default axis [0,0,1], fraction 0.999).
- Optional future: multi‑source divergence/dispersion.

Crystal
- Refine (Stage A): cell lengths (logs), angles (bounded map), orientation (quaternion→XYZ misset), global intensity scale.
- Fixed: N_cells (set by `--nabc` or default `(20,20,20)`), shape=SQUARE, mosaic/domains=0, phi_steps=1.
- Not modeled: DiffBragg’s Ncells_def envelope; rely on global scale to absorb `no_Nabc_scale` differences.

Structure Factors
- Fixed (v1): dense P1 |F| grid; enable tricubic with ±1 halo; optional small per‑shell/global modifiers in Stage B.

## 5) ADRs (Architecture Decision Records)

ADR‑01: Square‑Pixel Enforcement
- Require `px_fast_mm == px_slow_mm` per panel; raise if violated. Mixed pitches must use separate Detectors for now.

ADR‑02: ADU vs Photon Policy
- If `--adu-per-photon` provided, convert target to photons; else keep ADU and include a learnable global scale (initialized via a mean ratio on a few ROIs).

ADR‑03: Per‑Panel Simulation
- Simulate panels independently and stitch outputs; optional ROI‑only compute via cropped Detector configs with beam‑centre offsets.

ADR‑04: Geometry Refinement Scope (v1)
- Only distance offsets along detector normal per panel in Stage C; rotations remain fixed. Reassess after parity and performance validation.

ADR‑05: Ignore Ncells_def
- Do not emulate DiffBragg’s defect envelope; stick to a single lattice shape (SQUARE) with N_cells and use global scale to reconcile amplitude differences.

ADR‑06: Compile Cache Discipline
- Reuse warmed Simulator while shapes are constant; rebuild Detector/Simulator upon shape changes (panel dims, oversample) to avoid invalid caches.

ADR‑07: Mask Polarity and Loss Mask
- Use DIALS trusted mask (True=include) directly in simulator; define loss mask as `(background >= 0) & trusted_mask`.

## 6) Runtime Guidelines

Environment
- Set `KMP_DUPLICATE_LIB_OK=TRUE` before importing torch; allow `NANOBRAGG_DISABLE_COMPILE=1` to force eager mode for debugging.

Device/Dtype
- Co‑locate tensors on target device/dtype prior to run; avoid `.to()` in hot loops.

Determinism
- Fix seeds for reproducible tests; document any sources of nondeterminism.

## 7) Error Handling and Guards

Hard Errors
- Rectangular pixel panels in single‑panel mapping; mask shape mismatches; missing mandatory inputs.

Runtime Guards
- Bounds check ROI bboxes (exclusive upper bounds); enforce panel index alignment across reflections, image stacks, and masks.

## 8) Performance Notes

Throughput
- Expect panel‑wise GPU acceleration; test with small tiles first.

Memory Strategies
- Prefer per‑panel loops; for very large frames, adopt ROI tiling with cropped Detectors and stitch results.

Compile Shapes
- Keep `spixels/fpixels` and oversample fixed within runs to reuse compiled kernels.

## 9) Module Layout (Proposed)

```
dbex/
  data_load.py             # simtbx ingestion and background/ROI
  nanobrag_bridge.py       # dxtbx/simtbx → nanobrag_torch configs; tensor prep
  torch_model.py           # NanoBraggRefinementModel; staged refinement loop
  refine_one_torch.py      # CLI wrapper (or backend flag in refine_one.py)
  look.py                  # Viewer (unchanged)
  run_diffbragg.py         # Legacy (kept for back‑compat)
```

## 10) Outputs and I/O

HDF5
- Maintain current layout for viewer compatibility; add `/torch_diagnostics` group for optional logs.

Debug Artifacts
- Use TemporaryDirectory for any on‑disk HKL exports; add `--debug-save-artifacts` to persist when needed.

## 11) Open Items (Non‑Blocking)

- Rectangular pixel support in a single Detector (fast/slow pitch).
- In‑memory helper to inject cctbx Miller arrays directly into torch without HKL round‑trip.
- ROI‑aware simulator mode that reduces compute instead of post‑masking only.

## 12) References

- specs: docs/spec-db.md (core, runtime, workflow, interfaces, conformance, tracing)
- APIs: docs/nanobrag_api.md, docs/simtbx_api.md, docs/dxtbx_api.md, docs/dials_api.md
- Crosswalk: docs/config_crosswalk.md
- Plan: plans/nanobrag_integration_plan.md

