• 1. API

  - Public entry points remain Simulator, Crystal, Detector, and the config dataclasses; the simulator
    wires them together, normalizes device/dtype, and should be treated as the supported programmatic
    surface (src/nanobrag_torch/simulator.py:429-569).
  - read_hkl_file / try_load_hkl_or_fdump mirror the C loader (dense grid + metadata) and are safe for
    direct ingestion in integrations (src/nanobrag_torch/io/hkl.py:19-307).
  - Package version is 0.1.0, so expect pre-1.0 API evolution; the CLI—and your host process—must
    set KMP_DUPLICATE_LIB_OK=TRUE before importing torch (src/nanobrag_torch/__init__.py:7, src/
    nanobrag_torch/__main__.py:19-29).
  - CUDA/CPU builds rely on torch.compile; the simulator wraps the pure kernel with mode="max-
    autotune"/"reduce-overhead" and falls back (or obeys NANOBRAGG_DISABLE_COMPILE=1) automatically
    (src/nanobrag_torch/simulator.py:612-634).
  - Device/dtype neutrality is enforced by pre-casting detector/crystal tensors—avoid doing .to() or
    allocating new tensors inside your call site loops (src/nanobrag_torch/simulator.py:488-569).
  - Config dataclasses validate geometry, beam, ROI, and twotheta axes, so prefer them over ad-hoc
    dictionaries (src/nanobrag_torch/config.py:88-399, src/nanobrag_torch/config.py:496-569).

  2. Detector

  - Geometry operates in meters; pass mm inputs to DetectorConfig and let the model convert and cache
    (src/nanobrag_torch/models/detector.py:40-140).
  - The MOSFLM +0.5 offset is only applied when beam_center_source="auto", so set "explicit" for beam
    centers imported from DIALS (src/nanobrag_torch/models/detector.py:108-122, src/nanobrag_torch/
    config.py:186-327).
  - Basis vectors for MOSFLM/XDS/DIALS/ADXV plus full CUSTOM overrides (including beam vector) are
    handled in _calculate_basis_vectors; supply custom vectors for arbitrary dxtbx panels (src/
    nanobrag_torch/models/detector.py:1121-1320).
  - ROI bounds and mask_array must match (spixels, fpixels); masks are multiplied as floats inside
    Simulator.run (src/nanobrag_torch/config.py:232-396, src/nanobrag_torch/simulator.py:1183-1223).
  - Pivot defaults follow the C rules—distance ⇒ BEAM, close_distance ⇒ SAMPLE, custom vectors force
    SAMPLE—so override explicitly if your panel metadata expects a different pivot (src/nanobrag_torch/
    config.py:244-327).
  - Multi-panel layouts currently require one Detector per panel; get_pixel_coords exposes a single
    (spixels, fpixels, 3) array to stitch yourself (src/nanobrag_torch/models/detector.py:770-836).

  3. Beam

  - Keeping BeamConfig.polarization_factor=0.0 reproduces the C-style Kahn computation; set nopolar=True
    to disable polarization outright (src/nanobrag_torch/config.py:515-523).
  - Multi-source mode expects (n,3) directions plus optional wavelength/weight tensors; the
    simulator pre-casts them once and sums sources with equal weighting per spec (src/nanobrag_torch/
    config.py:510-513, src/nanobrag_torch/simulator.py:538-565, src/nanobrag_torch/simulator.py:405-
    416).
  - Resolution cutoff is exposed via BeamConfig.dmin; scattering vectors failing the threshold
    are skipped before HKL lookup (src/nanobrag_torch/config.py:531-533, src/nanobrag_torch/
    simulator.py:160-165).
  - Solid-angle/absorption toggles are tied to oversample_omega/oversample_thick; use them when you need
    per-subpixel corrections (src/nanobrag_torch/simulator.py:993-1140).
  - Fluence / flux / exposure relationships are recomputed in BeamConfig.__post_init__, so provide
    whichever pair you calibrate and let the config infer the third (src/nanobrag_torch/config.py:537-
    557).
  - Remember to set KMP_DUPLICATE_LIB_OK=TRUE in long-lived refinement workers as well (src/
    nanobrag_torch/__main__.py:19-29, tests/test_suite.py:276-314).

  4. Crystal

  - CrystalConfig holds unit-cell metrics, misset Euler angles, MOSFLM reciprocal matrices, spindle/
    phi, mosaic parameters, and N_cells, all convertible to tensors for gradients (src/nanobrag_torch/
    config.py:88-157, src/nanobrag_torch/models/crystal.py:72-118).
  - The lattice pipeline matches C: default reciprocal construction, optional MOSFLM injection, static
    misset on reciprocal vectors, real-vector recomputation, and reciprocal recomputation for metric
    duality (src/nanobrag_torch/models/crystal.py:520-884).
  - get_rotated_real_vectors applies phi then mosaic rotations and rebuilds reciprocal batches with
    shape (phi_steps, mosaic_domains, 3) (src/nanobrag_torch/models/crystal.py:990-1152).
  - Input validation guards non-physical lengths/angles; consider optimizing over constrained parameters
    (log lengths, bounded angles) before writing back to the config (src/nanobrag_torch/models/
    crystal.py:173-190).
  - For stills use the default phi_steps=1; for scans set phi_start_deg, osc_range_deg, phi_steps,
    and spindle_axis prior to run() (src/nanobrag_torch/config.py:118-144, src/nanobrag_torch/models/
    crystal.py:1015-1126).
  - Loading MOSFLM A* columns (e.g., from dxtbx A) into mosflm_* bypasses the canonical orientation
    and uses your reciprocal frame directly (src/nanobrag_torch/config.py:112-131, src/nanobrag_torch/
    models/crystal.py:640-743).

  5. Structure Factors

  - HKL readers load dense P1 grids, rounding indices to integers and filling unspecified reflections
    with default_F (src/nanobrag_torch/io/hkl.py:19-205).
  - Crystal.get_structure_factor chooses nearest-neighbour or tricubic interpolation via
    self.interpolate, with tricubic requiring a ±2 halo and auto-disabling when out-of-bounds (src/
    nanobrag_torch/models/crystal.py:221-380).
  - Toggle interpolation explicitly by setting crystal.interpolate = True; when tracing, the last
    4×4×4 neighborhood is cached for diagnostics (src/nanobrag_torch/models/crystal.py:112-125, src/
    nanobrag_torch/models/crystal.py:448-467).
  - The kernel multiplies F_cell * F_latt and squares it, so inputs should be |F| amplitudes;
    intensities or partial biasing should be converted upstream (src/nanobrag_torch/simulator.py:205-
    219).
  - There is no dedicated setter, but assigning the (grid, metadata) tuple from read_hkl_file
    to crystal.hkl_data/hkl_metadata is the supported in-memory path (src/nanobrag_torch/models/
    crystal.py:105-208).
  - Friedel mates are not synthesized; supply whichever symmetry-expanded grid you intend to refine,
    including Bijvoet partners if needed (src/nanobrag_torch/io/hkl.py:71-111).

  6. Simulator.run

  - run() pulls oversampling defaults, auto-selects oversample when config sets -1, converts
    lattice vectors to meters, and reuses cached pixel coordinates/ROI masks (src/nanobrag_torch/
    simulator.py:764-838).
  - Output is an (spixels, fpixels) tensor on the simulator’s device/dtype, with ROI/masks applied
    multiplicatively before return (src/nanobrag_torch/simulator.py:1183-1276).
  - ROI bounds and masks must match detector dimensions; mismatches raise during config validation (src/
    nanobrag_torch/config.py:232-396, src/nanobrag_torch/simulator.py:1183-1223).
  - Polarization, solid angle, and absorption obey the oversample_* flags, matching nanoBragg’s “last
    value” semantics when left false (src/nanobrag_torch/simulator.py:993-1140).
  - Final scaling divides by the step count and multiplies by r_e^2 and fluence, keeping physical units
    aligned with C (src/nanobrag_torch/simulator.py:1153-1176).
  - Debug hooks (printout, trace_pixel) live in the constructor; when enabled, they emit per-pixel
    traces and the cached tricubic neighborhood without polluting production runs (src/nanobrag_torch/
    simulator.py:495-504, src/nanobrag_torch/simulator.py:1497-1539).

  7. Helpers

  - No official dxtbx bridge is shipped yet, but the code supports a helper that maps panel axes/beam
    vectors into DetectorConfig and MOSFLM A* columns into CrystalConfig; the snippets below illustrate
    the pattern.
  - Contributions adding such helpers under src/nanobrag_torch/io/ (plus docs/tests) would be welcome.
  - Ensure helpers set beam_center_source="explicit" and reuse the CUSTOM convention when ingesting
    arbitrary panel frames (src/nanobrag_torch/models/detector.py:108-122, src/nanobrag_torch/models/
    detector.py:1121-1320).
  - Derive the unit beam vector from s0; flip it if its dot product with the detector normal is negative
    so it points toward the detector (src/nanobrag_torch/models/detector.py:988-1012).
  - When bridging crystals, capture unit-cell parameters from dxtbx and plug the A matrix columns into
    mosflm_* to bypass canonical orientation (src/nanobrag_torch/config.py:112-131, src/nanobrag_torch/
    models/crystal.py:640-743).
  - Remember to propagate scan metadata (phi_start_deg, osc_range_deg, spindle axis) when building
    configs from dxtbx experiments (src/nanobrag_torch/config.py:118-144, src/nanobrag_torch/models/
    crystal.py:1015-1126).

  8. Performance

  - Expect a 0.5–6 s cold compile followed by near-C throughput; reuse a warmed simulator for batch
    refinement as suggested in the README (README_PYTORCH.md:440-505).
  - Set NANOBRAGG_DISABLE_COMPILE=1 only for debugging or gradcheck; it forces eager mode (src/
    nanobrag_torch/simulator.py:612-620).
  - Keep all tensors on a consistent device/dtype—the simulator already pre-casts detector/crystal state
    to avoid graph breaks (src/nanobrag_torch/simulator.py:488-569).
  - Memory tiling is manual today; iterate over panels or define ROIs for large frames (src/
    nanobrag_torch/models/detector.py:770-836, src/nanobrag_torch/config.py:232-241).
  - CUDA uses torch.compile(mode="max-autotune"); no extra call-site flags are required for graph
    capture (src/nanobrag_torch/simulator.py:620-634).
  - Pixel coordinates, ROI masks, and source tensors are cached in the simulator, so mutate configs
    in place and re-run rather than rebuilding the object each iteration (src/nanobrag_torch/
    simulator.py:538-812).

  9. Validation

  - The simple_cubic golden configuration (100 Å cell, 1024² detector, wavelength 6.2 Å) is the
    canonical parity check and ships with commands and binaries under tests/golden_data (tests/
    golden_data/README.md:21-40, tests/test_suite.py:271-339).
  - Matching nanoBragg defaults means oversample=-1, polarization enabled, and dmin=0, mirroring
    the CLI commands in the golden README (src/nanobrag_torch/config.py:212-215, src/nanobrag_torch/
    config.py:515-533, src/nanobrag_torch/simulator.py:778-804).
  - Higher-level regression tests (e.g., tests/test_at_parallel_012.py) compare PyTorch outputs against
    stored C frames using correlation metrics (tests/test_at_parallel_012.py:7-189).
  - Use the same HKL inputs (or default_F) listed in the golden README to keep parity tight (tests/
    golden_data/README.md:21-40, tests/test_suite.py:310-324).
  - CLI and test harnesses already enforce KMP_DUPLICATE_LIB_OK=TRUE, matching the recommended runtime
    environment (src/nanobrag_torch/__main__.py:19-29, tests/test_suite.py:276-314).

  10. Assumptions

  - Your detector summary is correct: CUSTOM/DIALS conventions with beam_center_source="explicit"
    avoid MOSFLM offsets, and multi-panel images should be stitched from per-panel detectors (src/
    nanobrag_torch/models/detector.py:108-122, src/nanobrag_torch/models/detector.py:770-836).
  - Geometry uses meters while lattice physics uses Angstroms before conversion, and the final intensity
    carries r_e² × fluence scaling (src/nanobrag_torch/models/detector.py:56-68, src/nanobrag_torch/
    models/crystal.py:520-884, src/nanobrag_torch/simulator.py:1153-1176).
  - Structure factors are dense P1 |F| grids with optional tricubic interpolation; handle symmetry/
    Friedel upstream (src/nanobrag_torch/io/hkl.py:19-205, src/nanobrag_torch/models/crystal.py:221-
    380).
  - Orientation control is via misset Euler angles or MOSFLM reciprocal vectors; quaternions aren’t
    exposed yet, so wrap your own reparameterization if you need one (src/nanobrag_torch/config.py:104-
    145, src/nanobrag_torch/models/crystal.py:520-884).
  - Still images can rely on defaults, while scans should populate spindle/phi/mosaic fields to match
    DiffBragg behavior (src/nanobrag_torch/config.py:118-144, src/nanobrag_torch/models/crystal.py:1015-
    1126).

  Examples

  - Helper functions bridging dxtbx metadata, enabling tricubic interpolation, and running a panel end-
    to-end:

  import numpy as np
  import torch

  from nanobrag_torch.config import (
      DetectorConfig, DetectorConvention, DetectorPivot,
      CrystalConfig, BeamConfig,
  )
  from nanobrag_torch.models.detector import Detector
  from nanobrag_torch.models.crystal import Crystal
  from nanobrag_torch.simulator import Simulator
  from nanobrag_torch.io import read_hkl_file


  def detector_from_panel(panel, beam, device, dtype):
      px_fast, px_slow = panel.get_pixel_size()
      fast_count, slow_count = panel.get_image_size()
      fast_axis = np.array(panel.get_fast_axis(), dtype=np.float64)
      slow_axis = np.array(panel.get_slow_axis(), dtype=np.float64)
      normal = np.cross(fast_axis, slow_axis)
      normal /= np.linalg.norm(normal)
      origin_mm = np.array(panel.get_origin(), dtype=np.float64)
      distance_mm = float(np.dot(-origin_mm, normal))
      fast_mm, slow_mm = panel.get_beam_centre(beam.get_s0())
      beam_vec = np.array(beam.get_s0(), dtype=np.float64)
      beam_vec /= np.linalg.norm(beam_vec)
      if np.dot(beam_vec, normal) < 0.0:
          beam_vec = -beam_vec

      det_cfg = DetectorConfig(
          distance_mm=distance_mm,
          pixel_size_mm=float(px_fast),
          spixels=slow_count,
          fpixels=fast_count,
          beam_center_f=float(fast_mm),
          beam_center_s=float(slow_mm),
          beam_center_source="explicit",
          detector_convention=DetectorConvention.CUSTOM,
          detector_pivot=DetectorPivot.BEAM,
          custom_fdet_vector=tuple(fast_axis),
          custom_sdet_vector=tuple(slow_axis),
          custom_odet_vector=tuple(normal),
          custom_beam_vector=tuple(beam_vec),
      )
      return Detector(det_cfg, device=device, dtype=dtype)


  def crystal_from_dxtbx(crystal, n_cells, device, dtype):
      a, b, c, alpha, beta, gamma = crystal.get_unit_cell().parameters()
      A = np.array(crystal.get_A(), dtype=np.float64)
      cryst_cfg = CrystalConfig(
          cell_a=a,
          cell_b=b,
          cell_c=c,
          cell_alpha=alpha,
          cell_beta=beta,
          cell_gamma=gamma,
          N_cells=n_cells,
          mosflm_a_star=A[:, 0],
          mosflm_b_star=A[:, 1],
          mosflm_c_star=A[:, 2],
      )
      return Crystal(cryst_cfg, device=device, dtype=dtype)


  def enable_tricubic(crystal):
      crystal.interpolate = True
      h = torch.tensor([0.1], device=crystal.device, dtype=crystal.dtype, requires_grad=True)
      k = torch.tensor([0.2], device=crystal.device, dtype=crystal.dtype, requires_grad=True)
      l = torch.tensor([0.3], device=crystal.device, dtype=crystal.dtype, requires_grad=True)
      F = crystal.get_structure_factor(h, k, l)
      F.sum().backward()
      return h.grad, k.grad, l.grad


  def simulate_panel(panel, beam, crystal, fhkl_path, device="cuda"):
      torch_device = torch.device(device)
      dtype = torch.float32

      det = detector_from_panel(panel, beam, torch_device, dtype)
      xtal = crystal_from_dxtbx(crystal, n_cells=(1, 1, 1), device=torch_device, dtype=dtype)

      F_grid, metadata = read_hkl_file(fhkl_path, device=torch_device, dtype=dtype)
      xtal.hkl_data, xtal.hkl_metadata = F_grid, metadata

      beam_cfg = BeamConfig(
          wavelength_A=beam.get_wavelength(),
          dmin=0.0,
      )
      sim = Simulator(xtal, det, beam_config=beam_cfg, device=torch_device, dtype=dtype)
      return sim.run()

  Next steps

  1. Warm a simulator instance on representative panels (CPU and CUDA) to compile once before plugging
     it into DBEx.
  2. Verify parity against the simple_cubic golden frame after wiring the dxtbx bridge to ensure
     configuration matching before tuning gradients.


     ---

ROI / Background API

  - get_roi_background_and_selection_flags returns (rois, panel_ids, tilt_abc, selection_flags,
    background[, cov]); background is allocated as np.full_like(imgs, -1.) so every untouched pixel
    stays at the −1 sentinel (cctbx_project/simtbx/diffBragg/utils.py:414-603, :472).
  - imgs is indexed [panel, slow, fast]; every ROI tuple is (x1, x2, y1, y2) in fast/slow order and
    is consumed with Python slice semantics (data[pid, y1:y2, x1:x2]), so x2/y2 are exclusive bounds
    (utils.py:449, :475-493, :587; ROI construction in get_roi_from_spot/determine_shoebox_ROI follows
    the same ordering, utils.py:331-363, :606-620).
  - panel_ids is a plain integer list pulled straight from the reflection table’s panel column, matching
    the first axis of imgs from image_data_from_expt (utils.py:482-483, cctbx_project/simtbx/diffBragg/
    hopper_utils.py:514-541).
  - tilt_abc stores one (a, b, c) triple per ROI; with use_robust_estimation=False the plane is fit and
    the optional covariance returned when ret_cov=True (utils.py:554-566, :588-601). Robust estimation
    simply forces (0, 0, median) but keeps the same shape (utils.py:532-552).
  - selection_flags (your bg_is_good) indicate whether each ROI survived edge checks, hot-pixel
    limits, plane-fit sanity checks, and ROI size tests; ROIs that fail still get planes written into
    background, but their flag is False so you can drop them later (utils.py:479-592). Options you
    listed only influence which pixels are fit or clamped—they never alter ROI ordering or the −1
    sentinel behavior (utils.py:485-546, :571-574).

  Image Units & Calibration

  - image_data_from_expt simply wraps imageset.get_raw_data and converts the result to a float64 NumPy
    stack—no pedestal subtraction, gain correction, or unit conversion happens here (utils.py:725-748).
  - The refinement pipeline converts those raw ADU counts to photons by dividing by
    params.refiner.adu_per_photon immediately after loading (hopper_utils.py:514-521); you should mirror
    that if PyTorch expects photon units.
  - Trusted-range and gain metadata live on each dxtbx panel (Detector model). Masks can be tightened
    either via explicit params.roi.trusted_range or by pulling Detector[pid].get_trusted_range(); pixels
    outside the range are cleared from the trust mask (hopper_utils.py:630-641).
  - Additional per-panel masking hooks (e.g., removing top-N intensities, strong-spot-only selection)
    are applied after ROI extraction but before flattening, so upstream callers see the same ordering
    regardless (hopper_utils.py:644-655, :678-708).

  Hot Pixel / External Masks

  - roi.hotpixel_mask is read with utils.load_mask, which expects a DIALS-style pickled mask (tuple
    of flex.bool per panel); it is converted to a NumPy boolean array shaped like the raw data
    (utils.py:1066-1080).
  - During ROI gathering the mask is inverted (hotpix_mask = ~trusted) so True means “hot/bad pixel,”
    and the same array is used both for hard rejection and for counting hot pixels inside each ROI
    (hopper_utils.py:516-520, utils.py:484-493).
  - Other formats (NPY/NPZ/HDF5) are not consumed here—only the pickle reader is implemented—so external
    masks must be converted first (see utils.save_numpy_mask_as_flex, utils.py:1061-1064).

  MTZ Handling

  - open_mtz scans every Miller array in the file for the requested label (default fobs(+)fobs(-)),
    asserts it exists, and converts the array to amplitudes if needed; no scaling or unit conversion is
    applied (utils.py:963-990).
  - If the MTZ supplies merged F,SIGF, ma.as_amplitude_array() yields a non-anomalous amplitude array;
    calling generate_bijvoet_mates() after loading replicates values into both hands so later stages can
    assume Bijvoet pairs are present (mirroring the pattern used when building arrays from PDB models,
    utils.py:950-959).
  - When separate F(+),F(-) columns are present the returned array already carries anomalous flags;
    generate_bijvoet_mates() is idempotent, so leaving it in place keeps refinement and PyTorch paths
    aligned.
  - Magnitudes remain in whatever units the MTZ stored (typically electrons); downstream scaling is
    handled by refinement parameters rather than inside these helpers.

  Energy / Flux Interactions

  - ENERGY_CONV is the sole conversion constant (ℎc/e ≈ 12398.42 eV·Å) defined in simtbx.nanoBragg.utils
    (cctbx_project/simtbx/nanoBragg/utils.py:15) and imported by DiffBragg utilities (utils.py:20).
  - Background/ROI helpers never touch flux or wavelength; they operate on the already-scaled image
    data you hand them. Flux weighting only enters when spectra are parsed or simulators are configured
    (e.g., load_spectra_file computes energies with ENERGY_CONV / λ, utils.py:1052-1057).
  - As a result, keeping the target/model scales consistent boils down to matching the ADU→photon
    conversion and any per-panel masks—no hidden rescaling happens in the ROI path.

  Example Check

  import numpy as np
  from dxtbx.model.experiment_list import ExperimentListFactory
  from dials.array_family import flex
  from simtbx.diffBragg import utils

  KMP_DUPLICATE_LIB_OK = True  # set in your environment before importing torch

  expts = ExperimentListFactory.from_json_file("path/to/shot.expt", check_format=False)
  exp = expts[0]
  refls = flex.reflection_table.from_file("path/to/shot.refl")

  data = utils.image_data_from_expt(exp)          # raw ADU, shape (panels, slow, fast)
  hotpix = data < 0                               # example bad-pixel mask
  packet = utils.get_roi_background_and_selection_flags(
      refls, data, shoebox_sz=12, reject_roi_with_hotpix=False,
      pad_for_background_estimation=3, use_robust_estimation=False,
      hotpix_mask=hotpix, weighted_fit=False)
  bbox, pids, tilt, flags, background = packet

  print("data", data.shape, data.dtype, data.min(), data.max())
  print("background", background.shape, np.unique(background[background < 0]))
  for i in range(min(3, len(bbox))):
      x1, x2, y1, y2 = bbox[i]
      pid = pids[i]
      roi = data[pid, y1:y2, x1:x2]
      bg = background[pid, y1:y2, x1:x2]
      print(i, "pid", pid, "bbox", (x1, x2, y1, y2),
            "roi mean", roi.mean(), "bg mean", bg.mean(),
            "tilt", tilt[i], "selected", flags[i])

  Next steps

  1. Run the snippet against one of your dbex shots to confirm shapes/sentinels match expectations
     before wiring the PyTorch adapter.
  2. If you need different mask formats, convert them to the DIALS pickle (e.g., via
     save_numpy_mask_as_flex) so they stay compatible with utils.load_mask.


dials: 
• Reflection Schema

  - id is a flex.int column (experiment index) and is used to pick the matching Experiment before
    loading images (dials/src/dials/array_family/flex_ext.py:269, cctbx_project/simtbx/diffBragg/
    utils.py:725).
  - panel is stored as flex.size_t, zero-based in detector order; downstream code indexes
    detector[ref["panel"]] and image stacks with it (dials/src/dials/array_family/flex_ext.py:269,
    dials/src/dials/algorithms/integration/integrator_stills.py:92).
  - xyzobs.px.value is a flex.vec3_double centroid (fast, slow, frame) used for ROI centres when
    centroid='obs' (dials/src/dials/array_family/flex_ext.py:283, cctbx_project/simtbx/diffBragg/
    utils.py:331-358).
  - bbox is a flex.int6 laid out as (x0, x1, y0, y1, z0, z1) and feeds ROI extents as well as overlap
    checks (dials/src/dials/command_line/augment_spots.py:71-76, cctbx_project/simtbx/diffBragg/
    utils.py:475-506).
  - The optional delta-Q ROI path requires either rlp or s1; add_rlp_column backfills from s1 when
    present (cctbx_project/simtbx/diffBragg/utils.py:366-409).

  BBox Semantics

  - DIALS consistently iterates for x in range(bbox[0], bbox[1]) etc., showing the upper bounds are
    exclusive while lower bounds are inclusive (dials/src/dials/array_family/shoebox_extractor.h:87-
    105).
  - bbox.parts() returns (x0, x1, y0, y1, z0, z1) so fast (x) precedes slow (y) (dials/src/dials/
    command_line/augment_spots.py:71-76).
  - DiffBragg slices ROIs as imgs[pid, j1:j2, i1:i2], so Python slicing matches DIALS’ exclusive upper
    convention with no +1 adjustment required (cctbx_project/simtbx/diffBragg/utils.py:513-518).
  - determine_shoebox_ROI clamps extents to detector limits while preserving the same inclusive/
    exclusive semantics (cctbx_project/simtbx/diffBragg/utils.py:620-629).

  Mask Workflow

  - dials.util.masking.generate_mask builds per-panel flex.bool grids shaped (slow, fast) with trusted
    pixels set True (dials/src/dials/util/masking.py:203-339).
  - dials.generate_mask pickles those tuples to disk; each entry aligns with the detector panel order
    (dials/src/dials/command_line/generate_mask.py:132-149).
  - DiffBragg loads masks through utils.load_mask, returning a NumPy stack (n_panels, slow, fast);
    prm.roi.hotpixel_mask expects True for bad pixels, so invert a DIALS trusted mask before use
    (cctbx_project/simtbx/diffBragg/utils.py:1066-1080, cctbx_project/simtbx/diffBragg/phil.py:1156-
    1163).
  - Image masks from dxtbx also apply the detector’s trusted_range by default (dxtbx/src/dxtbx/
    imageset.h:888-920, dxtbx/src/dxtbx/model/panel.h:458-481); replicate that behaviour if you bypass
    ImageSet.get_mask().

  Image Calibration

  - image_data_from_expt exposes raw detector values exactly as stored in the imageset (no automatic
    pedestal or gain correction) (cctbx_project/simtbx/diffBragg/utils.py:725-748).
  - Per-panel gain and pedestal metadata are available via panel.get_gain() / panel.get_pedestal() for
    calibration logic (dxtbx/src/dxtbx/model/panel.h:135-154).
  - ImageSet.get_gain() synthesises a gain map when panels declare non-unit gains, otherwise it defers
    to external lookup tables (dxtbx/src/dxtbx/imageset.h:728-768).
  - panel.get_trusted_range() gives the inclusive ADU limits used to form the default mask; treat
    anything outside that window as untrusted when mirroring DIALS (dxtbx/src/dxtbx/model/panel.h:172-
    175).

  Shapes & Ordering

  - get_roi_background_and_selection_flags expects detector data shaped (n_panels, slow, fast) and
    seeds the returned background image with -1 outside accepted ROIs (cctbx_project/simtbx/diffBragg/
    utils.py:449-506).
  - Mask arrays returned by load_mask or produced by DIALS share that axis order, so mask[pid, y0:y1,
    x0:x1] lines up with imgs[pid, ...] (cctbx_project/simtbx/diffBragg/utils.py:485-486, 1066-1080).
  - The panel column always indexes the same detector slot used to fetch image tiles (dials/src/dials/
    algorithms/integration/integrator_stills.py:92-108), keeping reflection metadata, raw data, and
    masks aligned.

  Example snippet:

  from dials.array_family import flex
  from dxtbx.model.experiment_list import ExperimentListFactory
  from simtbx.diffBragg import utils as diff_utils
  import numpy as np

  refls = flex.reflection_table.from_file("strong.refl")
  print({k: type(refls[k]) for k in ("id", "panel", "bbox", "xyzobs.px.value")})

  expts = ExperimentListFactory.from_json_file("models.expt", check_format=False)
  expt = expts[refls[0]["id"]]
  stack = diff_utils.image_data_from_expt(expt)  # (n_panels, slow, fast)

  pid = int(refls[0]["panel"])
  x0, x1, y0, y1, _, _ = refls[0]["bbox"]
  shoebox = stack[pid, y0:y1, x0:x1]
  assert shoebox.shape == (y1 - y0, x1 - x0)

  mask = diff_utils.load_mask("hot.mask")
  hot_block = mask[pid, y0:y1, x0:x1]
  # If mask came from dials.generate_mask, flip it before saving to hot.mask:
  # hot_mask = np.logical_not(trusted_mask)

  Next steps:

  1. Run the snippet against one of your experiment/reflection pairs to sanity-check ROI slicing and
     mask alignment.
  2. Decide whether to invert any DIALS-generated mask before wiring it into prm.roi.hotpixel_mask so
     DiffBragg sees True at bad pixels.

-----
 Detector Mapping

  - panel.get_origin(), get_fast_axis(), and get_slow_axis() return lab-frame vectors; the origin is
    measured in millimetres, while the axes are unit vectors forming the detector basis (dxtbx/src/
    dxtbx/model/virtual_panel.h:190-208). Pixel metrics come from panel.get_pixel_size() (fast, slow in
    mm) and panel.get_image_size() (fast, slow in pixels) (dxtbx/src/dxtbx/model/panel_data.h:66-84).
  - Beam-centre helpers: panel.get_beam_centre(beam.get_s0()) yields the fast/slow coordinates in
    millimetres and panel.get_beam_centre_px(...) converts the same intersection to pixels (dxtbx/src/
    dxtbx/model/virtual_panel.h:231-270, dxtbx/src/dxtbx/model/panel.h:214-236). Remember to swap to
    slow/fast ordering when filling DetectorConfig.beam_center_s/beam_center_f.
  - The panel distance used by nanobrag_torch should come from the signed plane distance
    (panel.get_directed_distance() in mm, positive if the normal points towards the beam; dxtbx/src/
    dxtbx/model/virtual_panel.h:222-224). For tilted panels this already accounts for the projection
    along the panel normal, so no extra geometry is required—supply the detector basis vectors instead
    of trying to rederive tilt angles.
  - When mapping into DetectorConfig, set detector_convention=DetectorConvention.CUSTOM, provide
    custom_fdet_vector, custom_sdet_vector, and custom_odet_vector directly from the panel axes, set
    custom_beam_vector to the sample-to-source unit vector (see Beam section), and mark the beam centre
    as explicit to skip MOSFLM offsets. Supplying any custom vectors forces SAMPLE pivoting, which
    mirrors nanoBragg’s behaviour for bespoke geometries (src/nanobrag_torch/config.py:244-318). Use
    distance_mm and close_distance_mm from panel.get_directed_distance() to preserve the same pivot
    radius in _calculate_pix0_vector (src/nanobrag_torch/models/detector.py:373-633).
  - Panel ordering is stable across the toolchain: image_data_from_expt(expt) stacks raw arrays in
    detector index order (cctbx_project/simtbx/diffBragg/utils.py:725-748), and ROI helpers consume and
    emit pids keyed to the same index (cctbx_project/simtbx/diffBragg/utils.py:1423-1452).
  - Detector metadata comes straight from the panel API: gain/pedestal (dxtbx/src/dxtbx/model/
    panel.h:135-154), trusted range (dxtbx/src/dxtbx/model/panel_data.h:86-100), thickness and
    absorption length (dxtbx/src/dxtbx/model/panel_data.h:102-120). These values should feed any masking
    or loss weighting you build around nanobrag_torch.

  Beam Mapping

  - DIALS stores wavelength in ångströms (beam.get_wavelength() simply returns the stored value; dxtbx/
    src/dxtbx/model/beam.h:256-277). beam.get_s0() is the incident wavevector pointing from source to
    sample with magnitude 1/λ (dxtbx/src/dxtbx/model/beam.h:279-287), so the unit vector from sample
    towards the source is -s0/|s0|. Use that for DetectorConfig.custom_beam_vector and any simulator
    orientation you require.
  - Polarization information is exposed through beam.get_polarization_normal() (lab-frame unit vector)
    and beam.get_polarization_fraction() (scalar in [0,1]) (dxtbx/src/dxtbx/model/beam.h:308-322). For
    facilities that omit metadata, a common default is σ≈0.98 with the polarization plane horizontal.
  - The optional source distance is available as beam.get_sample_to_source_distance() in millimetres
    (dxtbx/src/dxtbx/model/beam.h:399-406). nanobrag_torch.BeamConfig expects wavelength in Å, distances
    in mm, and can carry the polarization parameters directly (src/nanobrag_torch/config.py:496-560).

  Crystal Mapping

  - crystal.get_unit_cell().parameters() returns (a, b, c, α, β, γ) in ångströms/degrees, suitable for
    the corresponding CrystalConfig fields (dxtbx/src/dxtbx/model/crystal.h:495-500).
  - Orientation matrices follow the standard DIALS definitions: U is the orthonormal rotation, B
    is the reciprocal metric, and A = U·B maps Miller indices to reciprocal vectors in Å⁻¹ (dxtbx/
    src/dxtbx/model/crystal.h:475-493). Columns of A give a*, b*, c*, which can be copied into
    CrystalConfig.mosflm_a_star/b_star/c_star.
  - Real-space vectors are reconstructed by inverting A, preserving the canonical dual (dxtbx/src/dxtbx/
    model/crystal.h:503-511).
  - Rotation metadata comes from the goniometer and scan: goniometer.get_rotation_axis() is a unit
    vector in the lab frame (dxtbx/src/dxtbx/model/goniometer.h:138-147); scan.get_oscillation() yields
    start and step in radians (use get_oscillation_in_deg() for degrees) and scan.get_num_images()
    supplies φ step counts (dxtbx/src/dxtbx/model/scan.h:284-308, dxtbx/src/dxtbx/model/scan.h:350-
    352). For still shots (no scan), keep phi_steps=1 and osc_range_deg=0; for rotation data set
    phi_start_deg, osc_range_deg, and phi_steps to maintain parity with nanoBragg’s φ loop.

  End-to-End Extraction Snippet

  from __future__ import annotations

  import numpy as np
  from dxtbx.model.experiment_list import ExperimentListFactory
  from nanobrag_torch.config import (
      BeamConfig,
      CrystalConfig,
      DetectorConfig,
      DetectorConvention,
      DetectorPivot,
  )

  expts = ExperimentListFactory.from_json_file("path/to/shot.expt", check_format=False)
  expt = expts[0]
  panel = expt.detector[0]
  beam = expt.beam
  crystal = expt.crystal

  origin_mm = tuple(panel.get_origin())
  fast_axis = tuple(panel.get_fast_axis())
  slow_axis = tuple(panel.get_slow_axis())
  normal_axis = tuple(panel.get_normal())
  pixel_size_fast, pixel_size_slow = panel.get_pixel_size()
  fast_px, slow_px = panel.get_image_size()
  beam_fast_mm, beam_slow_mm = panel.get_beam_centre(beam.get_s0())
  beam_fast_px, beam_slow_px = panel.get_beam_centre_px(beam.get_s0())
  distance_mm = panel.get_directed_distance()

  print("origin (mm):", origin_mm)
  print("fast/slow axes:", fast_axis, slow_axis)
  print("pixel size (mm):", (pixel_size_fast, pixel_size_slow))
  print("image size (px):", (fast_px, slow_px))
  print("beam centre (mm fast/slow):", (beam_fast_mm, beam_slow_mm))
  print("beam centre (px fast/slow):", (beam_fast_px, beam_slow_px))
  print("distance_mm:", distance_mm)

  s0 = np.array(beam.get_s0())
  beam_dir_sample_to_source = tuple(-s0 / np.linalg.norm(s0))

  detector_cfg = DetectorConfig(
      detector_convention=DetectorConvention.CUSTOM,
      detector_pivot=DetectorPivot.SAMPLE,
      distance_mm=distance_mm,
      close_distance_mm=distance_mm,
      pixel_size_mm=pixel_size_fast,
      spixels=slow_px,
      fpixels=fast_px,
      beam_center_s=beam_slow_mm,
      beam_center_f=beam_fast_mm,
      beam_center_source="explicit",
      custom_fdet_vector=fast_axis,
      custom_sdet_vector=slow_axis,
      custom_odet_vector=normal_axis,
      custom_beam_vector=beam_dir_sample_to_source,
  )

  beam_cfg = BeamConfig(
      wavelength_A=beam.get_wavelength(),
      polarization_factor=beam.get_polarization_fraction(),
      polarization_axis=tuple(beam.get_polarization_normal()),
      nopolar=False,
      source_distance_mm=beam.get_sample_to_source_distance(),
  )

  from scitbx import matrix
  A = matrix.sqr(crystal.get_A())
  crystal_cfg = CrystalConfig(
      cell_a=crystal.get_unit_cell().parameters()[0],
      cell_b=crystal.get_unit_cell().parameters()[1],
      cell_c=crystal.get_unit_cell().parameters()[2],
      cell_alpha=crystal.get_unit_cell().parameters()[3],
      cell_beta=crystal.get_unit_cell().parameters()[4],
      cell_gamma=crystal.get_unit_cell().parameters()[5],
      mosflm_a_star=A.column(0),
      mosflm_b_star=A.column(1),
      mosflm_c_star=A.column(2),
      spindle_axis=tuple(expt.goniometer.get_rotation_axis()),
      phi_start_deg=expt.scan.get_oscillation_in_deg()[0] if expt.scan else 0.0,
      osc_range_deg=expt.scan.get_oscillation_in_deg()[1] if expt.scan else 0.0,
      phi_steps=expt.scan.get_num_images() if expt.scan else 1,
  )

  Next Steps

  1. Verify pixel-size symmetry before feeding DIALS data to DetectorConfig; if fast/slow spacings
     differ, add explicit support for rectangular pixels in nanobrag_torch.
  2. Pipe per-panel trusted range/gain into your loss/masking stage so nanobrag_torch ignores saturated
     or untrusted samples.
  3. Run a single-frame parity check (e.g. nb-compare) once the bridge is in place to confirm beam
     centre/distance alignment.

Addendum: Follow‑Up Clarifications From Maintainer

Detector Geometry

- Rectangular pixels: Only square pixels are supported today. DetectorConfig.pixel_size_mm is a single scalar and both fast/slow grids are scaled by that value (src/nanobrag_torch/models/detector.py:830-858). CUSTOM basis vectors are normalized; attempting to hide anisotropy there will break downstream consumers (solid angle, auto-oversample). Workaround: instantiate a separate Detector per unique pixel size, or wait for planned pixel_size_s_mm/pixel_size_f_mm fields.
- ROI compute vs. mask: ROI bounds and mask_array are applied after full-frame intensity is computed (src/nanobrag_torch/simulator.py:1183-1223). To truly simulate only a subarray, build a dedicated detector whose dimensions equal the ROI and offset the beam center accordingly. Example:

  def detector_for_roi(det, x0, x1, y0, y1):
      width = x1 - x0
      height = y1 - y0
      px = det.config.pixel_size_mm
      cfg = DetectorConfig(
          distance_mm=det.config.distance_mm,
          pixel_size_mm=px,
          spixels=height,
          fpixels=width,
          beam_center_s=det.config.beam_center_s - y0 * px,
          beam_center_f=det.config.beam_center_f - x0 * px,
          beam_center_source="explicit",
          detector_convention=det.config.detector_convention,
          custom_fdet_vector=tuple(det.fdet_vec.cpu().tolist()),
          custom_sdet_vector=tuple(det.sdet_vec.cpu().tolist()),
          custom_odet_vector=tuple(det.odet_vec.cpu().tolist()),
          custom_beam_vector=tuple(det.beam_vector.cpu().tolist()),
      )
      return Detector(cfg, device=det.device, dtype=det.dtype)

  Simulate the ROI with a fresh Simulator built on that cropped detector and stitch the results back into the panel image. There is no built‑in tiling or multi‑panel batching; pattern is panel loop + optional ROI splitting. If slicing detector.get_pixel_coords() directly, adjust beam center and pix0 as well before run().

Beam & Units

- ADU vs photons: nanoBragg outputs physical photons. If adu_per_photon is available (DiffBragg style), convert ADU → photons. If not available, keep ADU targets and use a learnable global scale; polarization and solid‑angle are multiplicative and remain valid either way.
- Polarization defaults: For parity, set BeamConfig.polarization_factor=0.0, nopolar=False, and pass DIALS polarization normal/fraction when present. If absent, use axis [0,0,1] and fraction 0.999 (same as C defaults).

Crystal Orientation

- Misset application: Misset angles are applied after MOSFLM A* injection. compute_cell_tensors honors mosflm_* first, then rotates the reciprocal basis by misset_deg via XYZ extrinsic rotations (src/nanobrag_torch/models/crystal.py:640-743; utils/geometry.py:122-189). If using quaternions, keep them in your model and convert to XYZ each forward pass; assign crystal.config.misset_deg before run().
- Stills defaults: For stills, use phi_steps=1, osc_range_deg=0, mosaic_domains=1, mosaic_spread_deg=0; no artificial mosaic is required for stability.

Structure Factors

- In‑memory ingestion: No dedicated in‑memory constructor yet. Loader expects a dense P1 grid with integer HKL bounds (src/nanobrag_torch/io/hkl.py:19-205). To build from cctbx miller array without disk, iterate reflections to find min/max, allocate the tensor, fill amplitudes, and assign to crystal.hkl_data / crystal.hkl_metadata. The supported on‑disk path is text HKL → read_hkl_file.
- Tricubic halo/padding: Tricubic needs a ±1 neighborhood (four points per dimension). If the halo is incomplete, interpolation disables itself and returns default_F (src/nanobrag_torch/models/crystal.py:359-379). Padding like FDUMP’s +1 plane avoids fallback; alternatively, expand the reflection set by at least two indices beyond the highest HKL sampled. Use BeamConfig.dmin to keep lookups in‑bounds.

Conventions

- Beam vector: DetectorConfig.custom_beam_vector must point from sample to source (i.e., −beam.get_unit_s0()) to satisfy scattering vector conventions (src/nanobrag_torch/simulator.py:155-165).
- Beam center ordering: Public ordering is (beam_center_s, beam_center_f). dxtbx returns (fast, slow), so swap before assignment. Set beam_center_source="explicit" to disable MOSFLM +0.5 offset.

Runtime Notes

- ROI defaults: Omitted ROI bounds default to the full detector (src/nanobrag_torch/config.py:360-398).
- torch.compile & caching: Compiled kernel depends on tensor shapes passed to the physics kernel. Mutating numeric parameters (cell, wavelength, beam center) is fine. Changing geometry that alters shapes (panel dimensions, oversample factors) requires re‑instantiating Detector/Simulator or invalidating cached pixel coords. Best practice: reuse a warmed Simulator for parameter tweaks; rebuild on geometry/shape changes.

Open Work Items (non‑blocking for initial integration)

1) Rectangular‑pixel support via separate fast/slow pixel size fields.  
2) In‑memory structure‑factor helper consuming cctbx miller arrays directly.  
3) ROI‑aware execution path that skips pixel allocation for masked regions.
