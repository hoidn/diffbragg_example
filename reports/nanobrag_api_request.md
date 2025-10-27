# Request: API Clarifications and Guidance for Integrating `nanobrag_torch`

Hello nanoBragg team,

We are integrating `nanobrag_torch` (PyTorch implementation) as the refinement backend in the dbex project while retaining simtbx/DIALS for data preparation (background/ROIs and Experiment/Detector/Beam metadata). Our goal is to generate a full-frame Bragg image matching DIALS’ multi‑panel layout and to run gradient‑based refinement over crystal parameters (and possibly limited structure‑factor adjustments), with validation parity to our current DiffBragg workflow.

We reviewed your codebase (notably `src/nanobrag_torch/simulator.py`, `src/nanobrag_torch/models/{crystal.py,detector.py}`, `src/nanobrag_torch/config.py`, `src/nanobrag_torch/io/hkl.py`) and have targeted questions. Your answers (and any code snippets) will let us finish the bridge with minimal back‑and‑forth.

## 1) Public API Surface and Stability
- What is the recommended public API for programmatic use?
  - Classes/methods/modules you consider stable: e.g., `Simulator` (constructor + `run()`), `models.Crystal`, `models.Detector`, config dataclasses, `io.hkl` helpers.
- Do you follow semantic versioning for these APIs? Which parts are experimental or subject to change?
- Is `torch.compile` officially supported for `Simulator.run()` on CUDA across devices? Any known graph‑breakers to avoid from the call site (e.g., device/dtype transitions, Python control flow)?

## 2) Detector Geometry: Conventions, Units, Multi‑Panel
- Conventions: We see `DetectorConfig.detector_convention` with MOSFLM/XDS/DIALS/ADXV/CUSTOM.
  - For DIALS experiments, what is the recommended way to instantiate a `Detector` that exactly matches a dxtbx `Detector` panel’s geometry?
  - Does `CUSTOM` fully support setting basis vectors and beam vector explicitly via `DetectorConfig.custom_*` fields to match arbitrary dxtbx panels?
  - Any examples/pitfalls for mapping dxtbx panel origin/fast/slow vectors (lab space) into `DetectorConfig` (distance_mm, beam center, basis vectors, pivot)?
- Beam center and MOSFLM +0.5 pixel offset:
  - Please confirm that for explicit beam centers (as from dxtbx) no +0.5 offset is applied (logic appears to key on `beam_center_source=="explicit"`).
  - Any additional caveats when using DIALS convention?
- Units: Detector geometry uses meters internally while crystal/physics uses Angstroms. Are there additional unit boundaries we must honor (beam vector direction, pixel coordinates)?
- Multi‑panel support:
  - Our current plan is to simulate one `Detector` per DIALS panel and stitch results into a full image. Is there a built‑in or recommended batched multi‑panel API, or is per‑panel instantiation the intended pattern?
  - If batching is available/planned, what is the public API and expected output shape?

## 3) Beam Model: Polarization, Multi‑Source, dmin
- Polarization semantics: We see defaults that match C behavior when `polarization_factor=0.0` (geometry‑dependent Kahn factor).
  - For parity with C, should callers leave `polarization_factor=0.0` unless explicitly overriding?
- Multi‑source beam:
  - Recommended way to populate `BeamConfig.source_directions`, `source_wavelengths`, `source_weights`? Any constraints on shapes/broadcasting for multi‑source mode?
- High‑resolution cutoff:
  - Is `BeamConfig.dmin` the correct public knob for d‑spacing culling, and is it applied in `Simulator.run()` as expected (interaction with oversampling or other toggles)?

## 4) Crystal Orientation, Unit Cell, and Rotation
- Orientation from dxtbx:
  - Our source is dxtbx’s `Experiment.crystal` (reciprocal space A matrix). What’s your recommended strategy to set orientation?
    - Option A: Convert dxtbx A (or A*) to Euler/quaternion and populate orientation (e.g., via `misset_deg` or a public quaternion API if available).
    - Option B: Use MOSFLM A* injection (`CrystalConfig.mosflm_*`). If so, could you share a reference mapping (dxtbx → MOSFLM) to avoid sign/convention errors?
  - Any helper utilities or preferred parameterizations to avoid gimbal lock and keep gradients stable (e.g., quaternions)?
- Unit‑cell parameters:
  - Confirm arbitrary triclinic cells are supported and differentiable via `Crystal` cell_* fields.
  - Recommended bounds/safe parameterizations (e.g., optimize logs of lengths, squash angles into (ε, π−ε))?
- Spindle/phi/mosaic:
  - For stills vs scans, which `CrystalConfig` fields are critical (`phi_steps`, `osc_range_deg`, `spindle_axis`)? Are defaults designed for parity with the C implementation?

## 5) Structure Factors: Ingestion, Interpolation, Indexing
- In‑memory injection:
  - We start with fixed Fhkl (from MTZ via cctbx) and may enable limited refinement later.
  - What’s the recommended way to inject a dense F grid (and metadata) directly, bypassing file I/O?
    - Is there a `Crystal.set_structure_factors(F_grid, metadata)` or similar public API?
    - If not, should we call `io.hkl.read_hkl_file()` on a generated HKL file / FDUMP cache, or can we provide tensors directly to `Crystal`?
- Interpolation:
  - Public API to enable tricubic interpolation for differentiable F lookups (we see `Crystal.interpolate`) — any constraints on grid padding, boundary behavior, required granularity?
- Indexing semantics:
  - Are HKL assumed P1 with integer indices and no symmetry reduction?
  - How should we handle Friedel pairs (Bijvoet)? Should we pre‑symmetrize upstream, or supply raw indices for all encountered reflections?
  - Expected amplitude units: |F| vs intensity. Any scaling assumptions to match the C implementation?

## 6) `Simulator.run()` Contract
- Please confirm the public `run()` signature and behavior:
  - Inputs: provided via constructor (`Crystal`, `Detector`, configs). Any dynamic inputs per call?
  - Output: intensity tensor shape (slow × fast), dtype, and device behavior (returns on simulator device)?
  - ROI and mask: `DetectorConfig.roi_*` and `mask_array` appear to be the knobs to restrict computation. Any special handling (0/1 vs boolean)?
  - Oversampling: Which flags (`DetectorConfig.oversample`, `oversample_omega/polar/thick`) are public and supported? Recommended defaults for refinement?
  - Solid angle and absorption: Confirm whether `run()` applies obliquity and absorption when configured; any gotchas when aligning to experimental units?
  - Intensity normalization: Output units appear consistent with `r_e^2 × fluence`. If experimental images are in ADU or counts, do you recommend a single learnable global scale to absorb calibration?
- Debug/trace hooks:
  - Supported way to enable tracing (per‑pixel h,k,l diagnostics) and extract results (e.g., `Crystal._last_tricubic_neighborhood`)? Any performance caveats on GPU?

## 7) DIALS/DXTBX Mapping: Reference Helper Requests
To minimize integration errors, could you share (or accept a PR for) a reference helper that builds a `nanobrag_torch` `DetectorConfig`/`Detector` from a dxtbx panel?
- Inputs: dxtbx panel origin (mm), fast/slow axes (unit vectors), pixel size (mm), panel dimensions, and beam vector (`s0`).
- Outputs: `DetectorConfig` ready for use, including:
  - Convention selection (DIALS or CUSTOM with custom basis vectors)
  - `beam_center_s/f` consistent with your internal math
  - Pivot selection (BEAM vs SAMPLE) per your rules

Likewise, a small helper to construct `CrystalConfig` from dxtbx crystal (unit cell + A matrix) and beam wavelength would be very helpful.

## 8) Performance, Memory, and Batching Guidance
- Recommended practices for:
  - `torch.compile` modes on CUDA (e.g., max‑autotune vs default)
  - Device/dtype hygiene (we’ll keep everything on one device/dtype and avoid `.to()` in loops)
  - Batching across panels/ROIs to manage memory footprint (any built‑in tiling helpers?)
- Any known performance pitfalls to avoid beyond what’s in `README_PYTORCH.md` (e.g., Python‑side per‑pixel ops)?

## 9) Validation Parity With C and Reference Values
- Do you have a reference configuration (cell, wavelength, detector geometry) where PyTorch and C outputs match numerically (within tolerance)? A self‑contained example we can embed in tests would be ideal.
- Recommended default settings (oversample, dmin, polarization) most likely to match canonical outputs?

## 10) Assumption Check (please confirm or correct)
- Detector: For DIALS, prefer DIALS or CUSTOM convention and supply basis vectors/beam vector explicitly; no MOSFLM +0.5 offsets when `beam_center_source="explicit"`.
- Multi‑panel: Simulate each panel via its own `Detector` instance and stitch into `[panel, slow, fast]`; no official multi‑panel batch API yet.
- Units: Detector distances/pixel sizes in meters internally; cell in Angstroms; `Simulator` outputs physical intensity consistent with `r_e^2` and fluence.
- Structure factors: Provide dense P1 grid with |F| amplitudes; tricubic interpolation can be enabled for good gradients; symmetry/Bijvoet handled upstream.
- Orientation: Prefer quaternion or MOSFLM A* injection over Euler angles to avoid gimbal lock; spindle/phi/mosaic optional for stills with defaults matching C unless overridden.

## Artifacts/Examples Requested
- Code snippet: Build `DetectorConfig` from a dxtbx panel (DIALS geometry).
- Code snippet: Map dxtbx crystal (A matrix) to `CrystalConfig` (orientation/cell).
- Code snippet: Enable tricubic interpolation for Fhkl and confirm gradient paths work.
- Minimal end‑to‑end example: panel → `Simulator.run()` → image tensor.

Thanks very much for your time and for nanoBragg’s PyTorch implementation. With the above clarifications we can complete a robust integration and contribute validation results back to you.

