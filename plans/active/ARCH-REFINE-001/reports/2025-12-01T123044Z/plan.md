# Phase B.3 Planning Notes

## Scenario
- Stage B per-reflection helpers still reconstruct HKL halo metadata/ASU maps locally via `compute_hkl_asu_map`, ignoring the `asu_map` tensor emitted by `dbex.nanobrag_bridge.build_structure_factor_grid`.
- Stage C warm-cache retargeting allocates detector/crystal state from `StageAContext` but does not carry the CLI-provided HKL tensors, so final Bragg reconstruction can silently rebuild grids on the wrong device.
- JobContext already bubbles up `asu_map`, `hkl_metadata`, and telemetry provenance; Phase B.3 needs to promote those to `RefinementContext` so every Stage shares the same geometry payload created at CLI ingest.

## Desired Changes
1. **Context surfaces:**
   - Extend `RefinementContext` with `asu_map`, `hkl_indices_grid` (or `None`), and `halo_mask`, keeping them optional but validating the presence of halo metadata when Stage B/C are enabled.
   - `build_refinement_context` should accept these new arguments; when `job_context` supplies them, store on the dataclass. Provide a drop-in fallback (`None`) for legacy tests that still call the builder with the older signature.
   - Update `run_nanobrag_refinement` to pass the new context fields and maintain env guardrails (`job_context` remains the canonical source).

2. **Stage B consumption:**
   - `StageB.run` and `_build_stage_b_params` must first look for `ctx.asu_map` or `inputs['job_context'].asu_map`. When the tensor exists, skip the cctbx call entirely and re-use the provided ASU mapping/halo mask to initialize per-reflection parameters. Device placement should follow the RefinementConfig device.
   - If `asu_map` is missing but `hkl_metadata['has_halo']` is False, fail fast with a spec-citing error so dataset regeneration happens instead of running Stage B without a halo.
   - Preserve the existing fallback path so tests without halos still drop to shell mode with the same warnings.

3. **Stage C warm-cache:**
   - Propagate the context metadata through `StageAContext` so `_retarget_stage_a_simulators` and `_build_final_bragg_from_stage_a_telemetry` re-use the same HKL tensors when Stage C replays Stage A's final state. This keeps Stage C grad-friendly per GRADIENT-004 and eliminates per-panel HKL duplication when CPU fallback is active.

4. **Documentation:**
   - Author `docs/architecture/dbex/refinement/context.idl.md` describing the `RefinementContext` and JobContext surfaces (fields, types, spec citations).
   - Update `docs/architecture/module_map.md` entry for `dbex/refinement/context.py` noting that HKL halo metadata now lives there.

## Validation
- Run the Stage B and Stage C small-detector smokes with telemetry capture to prove the new context fields are populated and that the selectors still pass (logs under this report directory).
- No additional CLI test is required for this loop, but the plan expects Stage B run logs to show the "reused context asu_map" path instead of the fallback warning.
