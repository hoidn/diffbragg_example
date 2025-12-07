# MAP-SCALE-005 Phase A Planning Notes — Loop i=129 (Galph)

## Focus Selection Rationale

### Portfolio Context
- **Tier 0 status:** All items done/blocked/archived
  - ARCH-SIM-CONSTRUCTION-001: blocked_pending_environment (nanobrag_torch oversample issue)
  - ARCH-REFACTOR-001: blocked_pending_architecture (depends on ARCH-SIM-CONSTRUCTION-001)
  - All others: done/archived
- **Tier 1 focus:** MAP-SCALE-SYNC-001 (Calibration Ladder Synchronization roll-up)
  - 4/5 member plans complete: MAP-SCALE-001, MAP-SCALE-002, MAP-SCALE-003 (just completed i=127), MAP-SCALE-004
  - 1/5 pending: MAP-SCALE-005

### Why MAP-SCALE-005 Now
1. **Natural progression:** MAP-SCALE-003 Phase B completed successfully in Ralph i=127 with all tests PASSED
2. **MAP-SCALE-004 already done:** Phase A planning notes claimed "Phase A ready" but implementation.md shows all phases complete (exit criteria 3/3 satisfied per 2025-11-06T010000Z summary.md)
3. **Roll-up completion:** MAP-SCALE-005 is the last uncompleted member plan in MAP-SCALE-SYNC-001
4. **SCALE-007 paydown:** SCALE-007 finding (docs/findings.md:45) mandates telemetry enforcement; MAP-SCALE-003/004 added telemetry fields, but CLI still falls back silently when --refined-mtz fails—MAP-SCALE-005 closes this gap

### SCALE-007 Finding Context
**From docs/findings.md:45:**
> Zero-iteration bridge (`simulate_forward_once`) must emit structure-factor telemetry (`hkl_source`, reflection count, mean amplitude, MTZ path) and DB_AT_024 must fail when refined assets are present but telemetry reports `raw` or is missing, so regressions that drop refined |F| usage are caught immediately.

**Gap:** SCALE-007 enforces telemetry assertions in **tests**, but CLI layer still allows silent fallback (--refined-mtz points to missing file → CLI continues with raw MTZ, hkl_source="raw" in HDF5, no error raised).

**Spec alignment:** docs/spec-db-workflow.md §4 and docs/spec-db-tracing.md §2 establish refined structure factors as normative when explicitly requested; silent fallback violates user intent and risks undetected regressions.

## Phase A Scope

### A1: Reality Check
**Objective:** Confirm current CLI behavior when --refined-mtz points to missing file.

**Expected observation:** CLI completes successfully, emits HDF5 with hkl_source="raw" (fallback), no stderr warning or error exit.

**Validation:** Inspect /tmp/test_fallback.h5 /torch_diagnostics attrs to confirm hkl_source value.

**Artifact:** fallback_reproduction.md (stdout/stderr capture + HDF5 attrs snapshot)

### A2: Spec Citations
**Objective:** Gather normative support for failure-on-fallback policy.

**Key sections to cite:**
- docs/spec-db-workflow.md §4 (Calibration & refined structure-factor workflow): "When refined MTZ is provided, it SHALL be consumed; silent fallback to raw is prohibited"
- docs/spec-db-tracing.md §2: Torch diagnostics SHALL reflect actual inputs used (if refined requested but raw consumed, diagnostics misrepresent reality)
- docs/findings.md SCALE-003, SCALE-004, SCALE-007: Telemetry contract requires accurate provenance; silent fallback breaks contract

**Synthesis:** User intent (--refined-mtz flag) establishes normative expectation; CLI must fail fast when expectation cannot be met (file missing, load error) rather than silently degrading to different input set.

**Artifact:** spec_citations.md (quoted SPEC text + synthesis)

### A3: Guard Design
**Objective:** Define implementation strategy for Phase B.

**Failure surfaces:**
1. **File missing:** --refined-mtz path does not exist on disk
2. **Load error:** load_refined_mtz raises exception (corrupt MTZ, unsupported format)
3. **Telemetry downgrade:** hkl_source becomes "raw" after --refined-mtz flag provided (post-simulation sanity check)

**Error message template:**
```
RuntimeError: --refined-mtz flag provided (/path/to/refined.mtz) but refined structure factors could not be loaded.
Reason: File not found
Please verify the path or omit --refined-mtz to use raw structure factors from --mtzFile.
```

**Guard location:** dbex/refine_one.py::run_nanobrag_backend, immediately after load_refined_mtz call attempt (lines ~380-395 based on MAP-SCALE-003 Phase B analysis)

**Backward compatibility:** Users who never provide --refined-mtz are unaffected (raw MTZ path continues to work as default)

**Artifact:** guard_design.md (failure surfaces + error template + guard location)

### A4: Summary
**Consolidation artifact:** Combines A1-A3 findings, outlines Phase B scope (implementation + regression tests), notes risks.

**Phase B readiness checklist:**
- [ ] A1-A3 artifacts complete
- [ ] Guard design approved (failure surfaces known)
- [ ] Implementation scope clear (run_nanobrag_backend edit + test addition)
- [ ] No spec ambiguities blocking Phase B

**Risks:**
- Environment Freeze compliance: No package changes needed (uses existing dbex modules)
- Backward compatibility: Silent fallback is current behavior; fail-fast is breaking change for users who relied on fallback (but aligns with SCALE-007 normative intent)

## Initiative Typing

**Type:** spec_change (not bugfix)

**Rationale:** Current CLI behavior (silent fallback) is not a bug—it's an unintended design consequence. We're changing normative behavior from "tolerate missing refined MTZ" to "fail when refined MTZ explicitly requested but unavailable". This is a spec-level decision, not just implementation alignment.

**ADR cross-reference:** SCALE-007 finding establishes telemetry enforcement; MAP-SCALE-005 extends enforcement upstream to CLI layer (preventing bad telemetry from being written in the first place).

## Execution Plan for Ralph

Ralph i=129 will:
1. Run CLI with nonexistent --refined-mtz path, capture output, inspect HDF5 hkl_source
2. Read and quote relevant SPEC sections (spec-db-workflow.md §4, spec-db-tracing.md §2, findings.md SCALE-003/004/007)
3. Draft guard design (failure surfaces, error message, guard location)
4. Write summary.md consolidating A1-A3 and Phase B readiness checklist

**Artifacts root:** plans/active/MAP-SCALE-005/reports/2025-12-06T235959Z/

**No production code changes this loop** (planning only).

---

**Next loop (i=130):** Galph reviews Phase A artifacts, transitions to Phase B (implementation_ready), hands Do Now to Ralph for guard implementation + regression test.
