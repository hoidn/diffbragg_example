# Calibration and Scaling (Current Implementation)
Scope: descriptive of current implementation; normative behavior lives in docs/spec-db*.md.

This note defines the precedence and threading of calibration/scaling parameters in the shipped torch backend. Scope: refine_one torch path (nanobrag). DiffBragg inherits CLI flags but does not consume torch_config.

## Precedence and Conflict Policy
- Source order: `torch_config` (if present and parseable) → CLI flags → defaults.
- Overlapping fields (spot_scale_override, adu_per_photon, sigma_rdout, sigma_map, refined_mtz): if both torch_config and CLI provide a value and they differ, fail fast with an explicit error listing both values. No silent overrides. Conflicts between tiers for the same sigma field (e.g., config vs CLI map) are also errors.
- Partial configs: torch_config may be partial; missing fields are filled from CLI/defaults. Record per-field provenance in telemetry.
- Telemetry: write calibration source per field to `/torch_diagnostics` attrs (`calibration_source_<field>=torch_config|cli|default`), plus sigma provenance/reference and HKL source/path.

## ADU ↔ Photon Policy
- `--adu-per-photon` (gain) > 0 triggers conversion of targets and sigma tensors to photons. Without gain, targets stay in ADU and a global scale is refined (global_scale_hint from mean ROI target).
- spot_scale_override is applied post-simulation as `sqrt(scale)`. Calibration metadata overrides CLI if present.
- sigma_floor and sigma_readout share units with the target; both are divided by gain when gain is provided.

## Sigma Handling
- Sources and precedence (normative for torch path): torch_config sigma map (if present and valid) → CLI map (`--sigma-map`) → CLI scalar (`--sigma-rdout`) → dxtbx `external_lookup`. Must be strictly positive, finite, and align with `[panel, slow, fast]`. If none are supplied, abort (no silent zeros).
- Sigma tensors are zeroed outside the loss mask but kept in target units (ADU or photons).
- sigma_floor clamp: variance uses `max(I_model + sigma_readout^2, sigma_floor^2)`; clamp fraction is recorded in stage telemetry.

## Structure Factors
- Preference: refined MTZ when `--refined-mtz` is provided (fail if unreadable); otherwise raw MTZ (`--mtzFile`).
- HKL grid built once (optional halo for tricubic); HKL telemetry records source, count, mean amplitude, path.

## Outputs and Checks
- HDF5 attributes: `sigma_readout`, `sigma_floor` datasets plus calibration provenance and HKL telemetry under `/torch_diagnostics`.
- Expected invariants: positive sigma tensors; gain > 0 when provided; spot_scale_override >= 0; refined MTZ either consumed or aborts (no silent fallback when flag is set).

## Open Items
- No automatic reconciliation when torch_config and CLI disagree; the current behavior SHOULD be fail-fast per above policy.
- Warm-cache perf work is blocked (ENV-CUDA-001); does not affect calibration semantics.*** End Patch
