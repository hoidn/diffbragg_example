# spec-db-core.md — Core Engine (Normative)

Overview (Normative)
- Purpose: Define the core physics, geometry, units, and data contracts for DBEX + PyTorch refinement that simulates far‑field Bragg diffraction per panel and refines model parameters against masked, background‑subtracted images.
- Scope: Stills (phi_steps=1) with a single lattice envelope; square pixels only; P1 reflections (no symmetry/friedel pairing in the simulator). DiffBragg’s Ncells_def is out of scope in v1.

Status
- Applies to the `nanobrag_torch` backend, which is implemented but non‑default. The current CLI defaults to the legacy DiffBragg backend (`--backend diffbragg`), while `--backend nanobrag` opts into the torch path (Stage A on by default; Stage B/C behind flags). DiffBragg may diverge from these contracts.

Units, Frames, and Conventions (Normative)
- Units:
  - Detector distances/pixel sizes: inputs in mm; internal meters.
  - Crystal: Å and degrees; convert to meters only for geometry‑physics dot products.
  - Wavelength: Å.
  - Output: intensity in photons (physical) from the simulator; ADU used as input target unless user converts.
  - Calibration/units precedence and telemetry requirements are normative per `docs/spec-db-workflow.md` (“Calibration & Unit Conventions” addendum); implementers SHALL follow that ladder and emit the required provenance fields. Required calibration fields and provenance expectations there are binding; runs that omit them are non-conformant even if they execute.
- Frames and vectors:
  - Panel basis (f,s,o) SHALL be orthonormal in lab frame.
  - Beam vector SHALL point sample→source and be normalized.
  - Pixel arrays and masks SHALL use `[panel, slow, fast]` ordering.
- Unit modes:
  - Photon mode: targets, `sigma_readout`, and simulator outputs are in photons; variance `V` is computed in the same units.
  - ADU mode: targets and `sigma_readout` remain in ADU; simulator outputs are converted to ADU before loss (global scale per workflow). Variance `V` is still computed in target units.
- ROI bbox semantics:
  - Bboxes SHALL be `(x0, x1, y0, y1)` with x1,y1 exclusive; slice as `img[pid, y0:y1, x0:x1]`.

Data Contracts (Normative)
- Inputs: Experiment + Reflections
  - Reflection table minimal schema:
    - `id (flex.int)`, `panel (flex.size_t)`, `bbox (flex.int6)`; `xyzobs.px.value` or `xyzcal.px` MAY be present.
    - `bbox` is `(x0, x1, y0, y1, z0, z1)`; Spec‑DB v1 is stills‑only (`phi_steps=1`), so simulators SHALL honor the XY projection `(x0, x1, y0, y1)` and carry the Z extents through unchanged without interpretation.
  - Masks:
    - DIALS trusted mask SHALL be a tuple of `flex.bool` per panel (True=trusted) shaped `(slow, fast)`.
    - DiffBragg hot/bad masks are inverted; if used upstream, inversion SHALL be explicit.
- Variance inputs:
    - The bridge SHALL supply readout-noise estimates `sigma_readout` in the same units as the loss target (photons or ADU/gain). Granularity MAY be per-pixel or per-panel but MUST align with the simulator tensors and be included in `RefinementInputs` so the variance-weighted loss can be formed.
    - `sigma_readout` values SHALL be strictly positive and finite on all trusted pixels. Zero or NaN sigma is non-compliant because it produces infinite IRLS weights when `I_model → 0`.
    - Canonical precedence (highest → lowest, normative for conformance):
      1) Calibrated per-pixel/per-panel `sigma_readout` map (e.g., CLI `--sigma-map` or config payload).
      2) CLI scalar `--sigma-rdout` broadcast to the detector shape.
      3) External tiles (e.g., dxtbx `external_lookup`, sigma tiles embedded in Experiments/MTZ).
      If none of these are available, runs SHALL fail with a descriptive error (no defaults).
    - When detector metadata cannot provide a calibrated dark-RMS (or equivalent) value, the CLI MUST require an explicit override via `--sigma-rdout` (or abort with a descriptive error). Silent fallback to zeros is non-compliant. Legacy pipelines that inject hardcoded sigma defaults (e.g., ~3 ADU) are explicitly non-conformant with Spec‑DB.
    - The bridge SHALL record the provenance of the supplied noise (e.g., `sigma_map`, `sigma_scalar`, `external_lookup`) in `RefinementInputs` telemetry so downstream tools can audit whether instrument data or overrides were used.
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

### Baseline Crystal State and Parameterization (Normative)

- Baseline state:
  - For any mapping-aligned refinement, the crystal state provided by dxtbx/DIALS SHALL be treated as authoritative:
    - `A*_0 = crystal.get_A()` (reciprocal lattice matrix from dxtbx),
    - `c₀ = (a₀, b₀, c₀, α₀, β₀, γ₀)` (baseline unit cell),
    - `B₀ = B(c₀)` (Busing–Levy style reciprocal metric tensor constructed directly from `c₀`),
    - `U₀ = A*_0 @ B₀⁻¹` (baseline orientation matrix),
    - and by construction `A*_mapping = U₀ @ B₀ = A*_0`.
  - Implementations SHALL NOT introduce alternative, incompatible decompositions of `A*_mapping` into `U,B` in production refinement code.
  - Detailed derivations of the incremental UB parameterization live in `writeups/torch_geometry_incremental_ub_parameterization.tex` (normative by reference). Changes to that writeup MUST be mirrored here and in the DB‑AT UB tests.

- Incremental parameterization:
  - Stage‑A refinement parameterizations SHALL be defined as *increments* around the baseline state, not as free absolute `A*`:
    - Orientation parameters represent a small rotation `ΔR(q_delta)` applied to the baseline orientation such that `U(q_delta) = ΔR(q_delta) @ U₀`, where `ΔR` is typically implemented via a unit quaternion increment with the identity quaternion `(1,0,0,0)` encoding “no misset”.
    - Cell parameters represent small perturbations of the baseline cell, producing `B(params) = B(c(params))` via a well‑defined Busing–Levy metric tensor map consistent with dxtbx conventions. Lengths MAY be parameterized via log‑deltas (e.g. `a(params) = a₀·exp(δlog_a)`), while angles use additive deltas around `(α₀, β₀, γ₀)`.
  - At the Stage‑A zero point (all refinement deltas = 0), implementations MUST satisfy:
    - `U(0) = U₀`, `B(0) = B₀`, and `A*(0) = U₀ @ B₀ = A*_mapping`.

- One‑way construction of A*:
  - In production refinement code, `A*` SHALL be constructed only in the forward direction
    `params → (U(params), B(params)) → A*(params) = U(params) @ B(params)`.
  - Implementations SHALL NOT refactor `A*` back into `U,B` (e.g., via ad‑hoc decompositions) inside the refinement loop.
  - Any diagnostic code that performs such decompositions MUST NOT be used to drive the simulator in mapping‑aligned runs and MUST be covered by explicit tests.

Physics Toggles (Normative)
- Polarization: default parity SHALL be `polarization_factor=0.0`, `nopolar=False`, with polarization axis/fraction from DIALS when available; fallback `[0,0,1]`, `0.999`.
- Solid angle and absorption: default SHALL be off to match common DiffBragg PHIL (no thickness); enabling SHALL be explicit.
- dmin: default 0.0 (no resolution cutoff); enabling SHALL be explicit.

Source Handling and Weighting (Normative)
- Sources correspond to multiple beam directions/wavelength bins. By default, simulators SHALL weight all sources equally.
- When explicit per-source weights are provided (e.g., via `-lambda` or equivalent config), they SHALL be interpreted as a per-source weight vector (one coefficient per source) and applied multiplicatively to each source’s contribution. A single global flux/exposure knob MAY be used for overall normalization but MUST NOT be conflated with per-source weights.
- Embedded weights in source files MAY be recorded in telemetry but SHALL NOT override an explicit CLI/config weight vector.
- Telemetry SHALL record whether equal weighting or explicit weights were used and the effective weights.

Interpolation Policy (Normative)
- Stage A (geometry/scale) canonical mode SHALL use nearest‑neighbor sampling of the dense |F| grid (`interpolation=False`). Any Stage‑A run that enables tricubic interpolation is non‑canonical and SHALL be tagged in telemetry (e.g., `stage_a_interpolation_mode="tricubic_experimental"`).
- Stage B and Stage C SHALL use tricubic interpolation (`interpolation=True`) with a ±1 halo; any `default_F` fallback while interpolating is a conformance failure.
- Haloed |F| grids SHALL be declared in metadata when interpolation is enabled so tests can assert halo presence.

Structure Factors (Normative)
- Dense P1 |F| grid and min/max metadata SHALL be provided to the simulator. Tricubic interpolation SHALL require a ±1 halo; otherwise the simulator falls back to `default_F` at the edge.

Objective Function & Variance Model (Normative)
- Simulator mask:
  - `mask_array` SHALL be a 0/1 tensor per panel (1=include), aligned to `(spixels, fpixels)`.
- Loss Function:
  - The refinement objective SHALL be the variance-weighted mean squared error (Chi-squared).
  - Formula: `L = Sum( (I_model - I_obs)^2 / V_detached )` over trusted pixels.
  - `I_model`: The current differentiable model prediction (Bragg + background).
  - `I_obs`: Observed targets (photons or ADU after calibration policy).
- Variance Definition:
  - Variance SHALL be modeled as `V = I_model + sigma_readout^2`, where `I_model` is the current prediction (Bragg + background). Using `I_obs` in the variance term is PROHIBITED.
  - `sigma_readout` is the detector readout noise in photon units derived from the ingestion layer via the CLI-provided `--sigma-rdout/--adu-per-photon` pair or calibrated dark-RMS maps divided by the same gain factor. Values MUST be > 0 per the Data Contracts clause above.
  - A physical lower bound SHALL be enforced: `V = max(I_model + sigma_readout^2, sigma_floor^2)` where `sigma_floor` defaults to the instrument’s published readout noise (≥ 1 photon or the ADU-equivalent) and is configurable via CLI. The clamp exists to prevent infinite weights when `I_model → 0` on GPU backends; telemetry SHALL report `sigma_floor` and the fraction of pixels where the clamp engaged.
  - Shot noise contribution MUST originate solely from `I_model` (Poisson statistics). Readout noise MUST be added in quadrature via `sigma_readout^2`; no other variance terms are permitted unless formally added to this shard.
  - All downstream consumers (background fitting, ROI scoring, loss/gradient accumulation) MUST use the same `V` definition. Deviations SHALL be treated as bugs and recorded in `docs/fix_plan.md`.
- Gradient Mechanics (Canonical for v1):
  - The variance term `V` in the denominator SHALL be detached from the computation graph (treated as a constant) during the backward pass.
  - This implements an Iteratively Reweighted Least Squares (IRLS) approach that prevents “attraction to zero,” where the optimizer lowers `I_model` solely to reduce variance.
- Masking:
  - The loss SHALL be computed only where `(background >= 0) ∧ trusted_mask`, and invalid pixels SHALL NOT contribute to the gradient.

Non‑Goals (Informative)
- Ncells_def (defect envelope) is not modeled in v1.
- Multi‑panel batching inside one Simulator instance is not required; per‑panel simulation is the normative path.

References (Informative)
- docs/config_crosswalk.md, docs/dxtbx_api.md, docs/nanobrag_api.md, docs/simtbx_api.md, docs/dials_api.md.
