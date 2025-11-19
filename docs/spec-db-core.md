# spec-db-core.md — Core Engine (Normative)

Overview (Normative)
- Purpose: Define the core physics, geometry, units, and data contracts for DBEX + PyTorch refinement that simulates far‑field Bragg diffraction per panel and refines model parameters against masked, background‑subtracted images.
- Scope: Stills (phi_steps=1) with a single lattice envelope; square pixels only; P1 reflections (no symmetry/friedel pairing in the simulator). DiffBragg’s Ncells_def is out of scope in v1.

Status
- This shard applies to the planned `nanobrag_torch` backend. The current CLI and legacy flow use DiffBragg and may differ from the contracts below.
- Until the torch backend lands, use `python -m dbex.refine_one` (see `dbex/refine_one.py:5-26`).

Units, Frames, and Conventions (Normative)
- Units:
  - Detector distances/pixel sizes: inputs in mm; internal meters.
  - Crystal: Å and degrees; convert to meters only for geometry‑physics dot products.
  - Wavelength: Å.
  - Output: intensity in photons (physical) from the simulator; ADU used as input target unless user converts.
- Frames and vectors:
  - Panel basis (f,s,o) SHALL be orthonormal in lab frame.
  - Beam vector SHALL point sample→source and be normalized.
  - Pixel arrays and masks SHALL use `[panel, slow, fast]` ordering.
- ROI bbox semantics:
  - Bboxes SHALL be `(x0, x1, y0, y1)` with x1,y1 exclusive; slice as `img[pid, y0:y1, x0:x1]`.

Data Contracts (Normative)
- Inputs: Experiment + Reflections
  - Reflection table minimal schema:
    - `id (flex.int)`, `panel (flex.size_t)`, `bbox (flex.int6)`; `xyzobs.px.value` or `xyzcal.px` MAY be present.
  - Masks:
    - DIALS trusted mask SHALL be a tuple of `flex.bool` per panel (True=trusted) shaped `(slow, fast)`.
    - DiffBragg hot/bad masks are inverted; if used upstream, inversion SHALL be explicit.
- Outputs: Bragg prediction and HDF5 (optional)
  - Full‑frame Bragg tensor SHALL be `(n_panels, slow, fast)` and align with DataLoad.data.
  - HDF5 viewer output MAY include `data/roiN`, `model/roiN`, `bragg/roiN`, `bg/roiN`, and `score` for each ROI as implemented today.

Geometry Mapping (Normative)
- dxtbx → Simulator mapping SHALL follow docs/dxtbx_api.md and docs/config_crosswalk.md:
  - `distance_mm = panel.get_directed_distance()`.
  - Beam center SHALL be assigned as `(beam_center_s, beam_center_f) = (slow_mm, fast_mm)` with `beam_center_source="explicit"`.
  - `custom_fdet_vector`, `custom_sdet_vector`, `custom_odet_vector` SHALL be set from panel axes; `custom_beam_vector = -s0/||s0||`.
  - Pixel pitch SHALL be square: `px_fast_mm == px_slow_mm`. If not, the bridge MUST raise.
  - `spixels = slow_px`, `fpixels = fast_px` from `panel.get_image_size()`.

Physics Toggles (Normative)
- Polarization: default parity SHALL be `polarization_factor=0.0`, `nopolar=False`, with polarization axis/fraction from DIALS when available; fallback `[0,0,1]`, `0.999`.
- Solid angle and absorption: default SHALL be off to match common DiffBragg PHIL (no thickness); enabling SHALL be explicit.
- dmin: default 0.0 (no resolution cutoff); enabling SHALL be explicit.

Structure Factors (Normative)
- Dense P1 |F| grid and min/max metadata SHALL be provided to the simulator. Tricubic interpolation SHALL require a ±1 halo; otherwise the simulator falls back to `default_F` at the edge.

Masks and Loss Policy (Normative)
- Simulator mask:
  - `mask_array` SHALL be a 0/1 tensor per panel (1=include), aligned to `(spixels, fpixels)`.
- Loss mask:
  - The loss SHALL be computed only over `(background >= 0) ∧ trusted_mask`.

Noise / Variance Model (Normative)
- Per-pixel variance SHALL be modeled as `V = model_Lambda + sigma_r^2`, where `model_Lambda`
  is the expected photon signal (Bragg prediction plus background) and `sigma_r` is the detector
  readout noise expressed in photon units.
- Shot noise contribution MUST originate solely from `model_Lambda` (Poisson statistics). Readout
  noise MUST be added in quadrature via `sigma_r^2`; no other variance terms are permitted unless
  formally added to this spec shard.
- `sigma_r` SHALL be derived from the ingestion layer: either the CLI-provided
  `--sigma-r/--adu-per-photon` pair or calibrated per-pixel dark-RMS maps divided by the same gain
  factor. Upstream normalization MUST guarantee that `sigma_r` matches the units of
  `model_Lambda`.
- All downstream consumers (background fitting, ROI scoring, loss/gradient accumulation) MUST use
  the same `V` definition. Deviations SHALL be treated as bugs and recorded in docs/fix_plan.md.
- Workflow documents (e.g., `docs/spec-db-workflow.md` steps 2 and 6) SHOULD reference this
  section rather than redefining variance policy.

Non‑Goals (Informative)
- Ncells_def (defect envelope) is not modeled in v1.
- Multi‑panel batching inside one Simulator instance is not required; per‑panel simulation is the normative path.

References (Informative)
- docs/config_crosswalk.md, docs/dxtbx_api.md, docs/nanobrag_api.md, docs/simtbx_api.md, docs/dials_api.md.
