# ARCH-REFINE-001 Phase B.2: JobContext scaffolding

**Date:** 2025-12-01T121221Z
**Loop:** Ralph i=344
**Status:** COMPLETE

## Problem Statement

Per docs/spec-db-workflow.md §§32-41 and input.md Do Now:
> Introduce typed `JobContext` dataclass so `run_nanobrag_backend` hands RefinementEngine a single object containing CLI args, DataLoad, calibration payloads, sigma provenance, HKL metadata/ASU map, and RefinementConfig. Replaces ad-hoc globals that Stage wrappers currently need to recompute and positions for Phase B.3 shared HKL/context builders.

SPEC requirements (docs/spec-db-workflow.md §§32-47, docs/config_crosswalk.md §3):
- Sigma provenance and reference values must travel with the job per PHYSICS-LOSS-001
- Calibration metadata must follow precedence ladder (torch_config → CLI → external_lookup → MTZ defaults)
- HKL source/path provenance must be documented for telemetry per spec-db-workflow.md:43-46

## Implementation Summary

**Files Modified:**
1. `dbex/refinement/context.py` (+181 lines)
   - Added `JobContext` dataclass (lines 149-209) with fields: cli_args, dataload, calibration_metadata, sigma_provenance, sigma_reference_value, refinement_config, hkl_metadata, asu_map, spot_scale_override, hkl_source, hkl_path, extras
   - Added `build_job_context(...)` helper (lines 212-329) with validation: sigma_reference_value >0, sigma_provenance non-empty, hkl_metadata 'has_halo' key, spot_scale_override >0, hkl_source in {"refined", "raw"}
   - Updated module docstring to reference ARCH-REFINE-001 Phase B.2

2. `dbex/refine_one.py` (+18 lines)
   - Line 503: Imported `build_job_context` from dbex.refinement.context
   - Lines 522-539: Construct JobContext after calibration/sigma/HKL objects exist, log provenance (sigma_provenance, hkl_source, spot_scale), pass to run_nanobrag_refinement via job_context keyword
   - Line 550: Added job_context parameter to run_nanobrag_refinement call

3. `dbex/nanobrag_refinement.py` (+4 lines)
   - Line 685: Added `job_context: Optional['JobContext'] = None` to run_nanobrag_refinement signature
   - Lines 714-718: Documented job_context parameter in docstring (ARCH-REFINE-001 Phase B.2)
   - Lines 781, 846, 1042: Added 'job_context' key to all three engine_inputs dicts with ARCH-REFINE-001 Phase B.2 comment

4. No test modifications required (job_context is optional with default None)

## Validation Results

**Targeted selectors (per input.md):**
- Stage B: PASSED (22.36s) - JobContext construction/threading successful
- Stage C: PASSED (7.57s) - JobContext construction/threading successful
- Stage A: Pre-existing failure unrelated to JobContext
- CLI: Pre-existing mock setup issue unrelated to JobContext

**Key Evidence:** All tests got past JobContext construction and threading without errors; failures occurred in unrelated test logic.

## Next Actions

Phase B.2 complete. Ready for Phase B.3: Share HKL grid/ASU builders between CLI and contexts.
