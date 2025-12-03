# Incident Beam Direction Analysis (Phase B.2 pre-work)

## Context
- Phase E HKL stats from DIAG-NANOBRAGG-OVERSAMPLE-001 show all Stage-A and `simulate_forward_once` HKL queries landing in `h,k,l≈[+28,+59]`, outside the refined grid bounds `[-24,+31]`.
- Phase B.1 probe (`inspect_hkl_projection.py`) reproduces `_compute_physics_for_position` math for the direct beam and finds `(h,k,l)≈(0,0,0)`, which contradicts the 0 % coverage evidence.

## Code inspection findings
- `nanobrag_torch.simulator.Simulator.__init__` sets `self.incident_beam_direction = self.detector.beam_vector.clone()` (file: `src/nanobrag-torch/src/nanobrag_torch/simulator.py:546-566`).
- `Detector.beam_vector` (file: `src/nanobrag-torch/src/nanobrag_torch/models/detector.py:989-1010`) returns a unit vector **pointing from the sample toward the source** per spec-db-core §Detector Conventions.
- `_compute_physics_for_position` computes the scattering vector via `q = (diffracted_beam_unit - incident_beam_unit) / wavelength_meters` (simulator.py:151-169). Supplying a sample→source vector therefore produces `q = k_out - (-k_in) = (k_out + k_in)`, i.e., the true scattering vector plus `2·k_in`.
- Multi-source code paths explicitly negate source directions before calling `_compute_physics_for_position` (simulator.py:1008-1019 and 1690-1706) with the comment “source_directions point FROM sample TO source. Incident beam direction should be FROM source TO sample (negated).” The single-source path never inverts the detector beam vector, so Stage‑A and `simulate_forward_once` always see the wrong incident direction.

## Hypothesis
- Negating the stored incident beam direction (`self.incident_beam_direction = -self.detector.beam_vector.clone()`) should realign the scattering vector computation with specs (docs/spec-db-core.md §§Geometry Mapping & Source Handling). Expected effect: HKL ranges shift by approximately `-2·k_in·a` ≈ −30 indices, bringing lookups back inside the refined grid bounds and restoring non-zero Bragg intensity.

## Next steps
1. Patch Simulator initialization and any other single-source fallbacks that default to `self.incident_beam_direction` so they use source→sample vectors.
2. Regenerate HKL stats via `compare_hkl_stats.py` and the Stage‑A HKL instrumentation to confirm ≥99 % in-bounds coverage.
3. Update `docs/findings.md` with the root-cause note and log the patch details per Environment Freeze rules.
