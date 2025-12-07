# Spec Citations (A2): Normative Support for Fail-Fast Policy

## Summary

The spec **already requires fail-fast behavior** when refined MTZ is explicitly requested but cannot be consumed. The current implementation complies with this normative requirement. This document consolidates spec citations supporting the existing enforcement.

## Primary Normative Citation

### spec-db-workflow.md:47 (Normative Conversion Sequence)

> **Normative conversion sequence:** (1) ingest metadata, decide unit_mode/gain; (2) apply gain if needed to target/sigma*; (3) resolve calibration payload via precedence; **(4) build HKL grid (refined preferred, else raw; fail if refined requested but missing)**; (5) construct configs/context with calibration (log_scale_baseline = log(sqrt(spot_scale_override)) in ADU mode, 0 in photon mode); (6) apply variance model `V = max(I_model + sigma_readout^2, sigma_floor^2)`; (7) emit full telemetry.

**Interpretation:**

- **"refined preferred, else raw"**: When no explicit `--refined-mtz` flag is provided, the CLI may fall back to raw MTZ (`-z/--mtzFile`) without error
- **"fail if refined requested but missing"**: When `--refined-mtz` flag is explicitly provided, the run SHALL fail if the refined MTZ cannot be loaded

**Compliance Status:** ✅ **COMPLIANT**

- Implementation at `dbex/refine_one.py:382-389` raises `RuntimeError` when `load_refined_mtz()` fails
- Error message clearly states: "When --refined-mtz is provided, refined structure factors MUST be consumed."

## Supporting Citations

### spec-db-workflow.md:34 (Calibration Precedence Ladder)

> **Precedence ladder** (highest → lowest): torch_config (if provided) → CLI overrides → external_lookup payloads → refined MTZ metadata → raw MTZ defaults → hardcoded defaults. ... **refined MTZ, when requested, SHALL be consumed or the run SHALL fail fast (no silent fallback to raw).**

**Interpretation:**

- Refined MTZ is positioned in the precedence ladder above raw MTZ defaults
- The phrase "when requested" corresponds to the `--refined-mtz` CLI flag
- "SHALL fail fast (no silent fallback to raw)" is an explicit normative constraint

**Compliance Status:** ✅ **COMPLIANT**

- The implementation does not silently fall back when `--refined-mtz` load fails
- The run terminates with a clear error before simulation begins

### spec-db-workflow.md:45 (Telemetry/Provenance Requirements)

> **Telemetry/provenance:** `/torch_diagnostics` SHALL include the required keyset defined in `spec-db-interfaces.md` (HDF5 Output Schema), covering calibration sources/values (spot_scale_override, sigma_readout/sigma_floor with provenance, beam flux/exposure, beamsize_mm, N_cells, unit_mode/gain), **HKL source/path, interpolation/halo flags**, device profile, scale baselines/clamps, and **any precedence conflicts or fallbacks**.

**Interpretation:**

- HDF5 telemetry MUST record `hkl_source` (raw vs refined) and `hkl_path`
- Any fallback from refined to raw MUST be recorded in telemetry (but this only applies if the fallback is **permitted**, not when it's an error condition)

**Compliance Status:** ✅ **COMPLIANT**

- When `--refined-mtz` is NOT provided, telemetry correctly records `hkl_source="raw"` and the raw MTZ path
- When `--refined-mtz` IS provided but fails, the run terminates before telemetry is written (no opportunity for silent downgrade)

### spec-db-workflow.md:46 (Runtime Enforcement Pattern)

> **Runtime enforcement:** runs missing `sigma_readout` (no map, scalar, or external tiles) or missing `sigma_floor` MUST error before simulation/refinement begins; DB‑AT selectors MAY assume these checks have already been enforced.

**Interpretation:**

- This establishes a **precedent pattern** for CLI-level enforcement: when required inputs are missing, fail fast before simulation
- Refined MTZ (when explicitly requested via `--refined-mtz`) falls into the same category as `sigma_readout` / `sigma_floor`

**Compliance Status:** ✅ **COMPLIANT**

- The refined MTZ check occurs at `dbex/refine_one.py:382`, immediately after sigma resolution and before simulation/refinement
- Aligns with the enforcement pattern for other required calibration inputs

## Findings.md Citations (Supporting Evidence)

### SCALE-007 (Telemetry Enforcement Intent)

> **SCALE-007** (dbex/nanobrag_bridge.py:843-1106, tests/dbex/test_mapping_consistency.py:272-358): Zero-iteration bridge must emit structure-factor telemetry and **tests must fail when refined assets are present but telemetry reports `raw` or is missing**; Phase A will extend this to CLI by defining failure surfaces when `--refined-mtz` is explicit but ingestion fails.

**Interpretation:**

- SCALE-007 establishes a **test harness enforcement** for telemetry downgrade detection
- The finding anticipated extending this enforcement to the CLI layer when `--refined-mtz` is provided
- The phrase "when --refined-mtz is explicit but ingestion fails" directly describes the scenario tested in A1

**Current Status:**

The CLI **already implements** the enforcement described in SCALE-007:

- When `--refined-mtz` ingestion fails, the run terminates with an error (not a telemetry downgrade)
- This is **stronger** than the test harness enforcement (which detects downgrade after-the-fact)
- The CLI enforcement is **preventive** (blocks execution), not **detective** (post-execution assertion)

### SCALE-003 & SCALE-004 (Calibration Alignment Dependency)

> **SCALE-003**: Zero-iteration torch helper must ingest DiffBragg-refined |F| amplitudes and √spot_scale...
>
> **SCALE-004**: CLI must forward beam/crystal calibration metadata to simulator; Phase A will check whether refined MTZ absence triggers proper failure vs silent fallback.

**Interpretation:**

- These findings establish that refined structure factors must be paired with calibration metadata
- SCALE-004 explicitly anticipated checking "proper failure vs silent fallback"
- The A1 reality check confirms **proper failure** is already implemented

## Normative Requirement Summary

### When --refined-mtz IS PROVIDED

1. **Load MUST succeed** or run MUST terminate with clear error
2. **Telemetry MUST record** `hkl_source="refined"` and the refined MTZ path (if run succeeds)
3. **NO silent fallback** to raw MTZ is permitted

### When --refined-mtz IS NOT PROVIDED

1. **CLI MAY use** raw MTZ from `-z/--mtzFile` without error
2. **Telemetry MUST record** `hkl_source="raw"` and the raw MTZ path
3. **Console log SHOULD indicate** "Using raw structure factors from <path>" for clarity

### Current Implementation Compliance

| Requirement | Status | Evidence |
|------------|--------|----------|
| Fail fast when --refined-mtz load fails | ✅ COMPLIANT | `dbex/refine_one.py:382-389` raises RuntimeError |
| Error message is actionable | ✅ COMPLIANT | Message includes file path, expected columns, and MUST statement |
| Telemetry records hkl_source correctly | ✅ COMPLIANT | Verified via h5py inspection in A1 |
| No silent fallback on --refined-mtz failure | ✅ COMPLIANT | Run terminates before simulation |
| Raw MTZ fallback allowed when flag omitted | ✅ COMPLIANT | Verified in A1 baseline test |

## Conclusion

The spec **already requires** the fail-fast behavior currently implemented in `dbex/refine_one.py:382-389`. This initiative was predicated on the assumption that silent fallback was occurring and needed to be replaced with enforcement. That assumption is **incorrect**.

### Recommended Phase B Scope Revision

Instead of implementing new enforcement (which already exists), Phase B should:

1. **Add regression test** ensuring `--refined-mtz /nonexistent/path.mtz` continues to fail fast
2. **Update ARCH-CONTRACT-CALIBRATION-001** to reflect actual implementation (fail-fast, not silent fallback)
3. **Validate SCALE-007 compliance** by confirming the CLI error path satisfies telemetry enforcement intent
4. **Document user-facing error quality** and ensure consistency with other CLI enforcement messages

### Alternative: Close as Already Satisfied

If stakeholders confirm that:

- The existing error message meets quality standards
- Regression test coverage is adequate (or will be added via separate test harness initiative)
- ARCH-CONTRACT updates are accepted as docs-only work

Then **MAP-SCALE-005 could be closed** as "already satisfied by existing implementation."

## Artifacts

- Normative citations extracted from `docs/spec-db-workflow.md:34,45-47`
- Supporting citations from `docs/findings.md` (SCALE-003, SCALE-004, SCALE-007)
- Compliance verified via `plans/active/MAP-SCALE-005/reports/2025-12-06T235959Z/fallback_reproduction.md`
