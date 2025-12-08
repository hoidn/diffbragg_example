# Future DB-AT Selector Inventory

**Initiative:** DB-AT-SUITE-CARE-001 Phase D.2
**Loop:** i=192
**Date:** 2025-12-08T112000Z

---

## Executive Summary

This inventory assesses DB-AT selectors beyond DB-AT-024 for onboarding readiness. All selectors in the range DB-AT-025 through DB-AT-050 are already documented in `docs/spec-db-conformance.md`. Several (026-029) already have active tests in TEST_SUITE_INDEX.md. The remaining selectors (025, 030-032, 040, 050) have specification support but lack test implementations.

**Recommendation:** No immediate onboarding action required. DB-AT-028/029 remain failing (blocked by ARCH-SIM-CONSTRUCTION-001). Priority selectors for future onboarding: DB-AT-030 (sigma precedence) and DB-AT-032 (Stage C detector offsets), both of which have complete spec documentation and existing infrastructure to support test authoring.

---

## Selector Inventory

### Already Active (TEST_SUITE_INDEX.md)

| Selector | Purpose | Spec Status | Test Status | Readiness |
|----------|---------|-------------|-------------|-----------|
| DB-AT-026 | Stage-A UB parameterization round-trip | documented | Active | ready (PASS) |
| DB-AT-027 | Stage A Zero-Point Parity | documented | Active | ready (PASS) |
| DB-AT-028 | Stage A Loss-Scale Sanity | documented | Active | blocked (FAIL - chi²/pixel=2.1e5, spec: ≤1e2) |
| DB-AT-029 | Stage A Structure Parity | documented | Active | blocked (FAIL - ROI CC=-0.053, spec: ≥0.2) |

**Source:** `docs/development/TEST_SUITE_INDEX.md:16-19`

**Blockers:**
- DB-AT-028/029 failure root cause traced to ARCH-SIM-CONSTRUCTION-001 (intensity scale mismatch)
- Initiative blocked_pending_environment per `docs/fix_plan.md:27`
- Upstream response clarified SQUARE lattice physics; DBEX-side spec/test changes pending

---

### Defined in Spec, Selector TBD

| Selector | Purpose | Spec Status | Profile | Readiness | Dependencies |
|----------|---------|-------------|---------|-----------|--------------|
| DB-AT-025 | HKL interpolation conformance (tricubic halo) | documented | Workflow Integration | needs_clarification | Stage B/C only (Stage A is `interpolate=False`) |
| DB-AT-030 | Sigma precedence and provenance | documented | Workflow Integration | ready_for_implementation | None; 5 test cases already defined in spec |
| DB-AT-031 | Stage-B ASU mapping and modifier sanity | documented | Stage-B/C | blocked | GRADIENT-003, Stage B grid CPU transfer corruption |
| DB-AT-032 | Stage-C detector distance offsets | documented | Stage-B/C | ready_for_implementation | Stage C already wired (ARCH-REFINE-FLOW-001) |
| DB-AT-040 | Trace schema conformance | documented | Tracing & VIS | ready_for_implementation | Trace mode not yet wired |
| DB-AT-050 | VIS triptych/layout conformance | documented | Tracing & VIS | ready_for_implementation | VIS helpers exist but need harness |

**Source:** `docs/spec-db-conformance.md:27-37, 251-389`

---

## Conformance Profile Coverage

### Forward Equivalence Profile
- DB-AT-001: Active (TEST_SUITE_INDEX.md row exists but xfail-guarded)

### Gradient-Safe Profile
- DB-AT-010: blocked_pending_upstream (ARCH-GRADIENT-FLOW-001)
- DB-AT-011: not assessed (depends on 010)
- DB-AT-027: Active (PASS)
- DB-AT-028: Active (FAIL)
- DB-AT-029: Active (FAIL)

### Workflow Integration Profile (5/7 complete)
- DB-AT-020: Active (PASS)
- DB-AT-021: Active (PASS)
- DB-AT-022: Active (PASS)
- DB-AT-023: Active (PASS)
- DB-AT-024: Active (PASS - requires artifact dir)
- DB-AT-025: TBD
- DB-AT-030: TBD

### Stage-B/C Profile (0/2)
- DB-AT-031: TBD (blocked by GRADIENT-003)
- DB-AT-032: TBD (ready for implementation)

### Tracing & VIS Profile (0/2)
- DB-AT-040: TBD
- DB-AT-050: TBD

---

## Findings Cross-Reference

| Finding ID | Related Selectors | Status | Impact |
|------------|-------------------|--------|--------|
| SIM-CONSTR-PARTIALITY-001 | DB-AT-028/029 | Resolved (spec clarification) | SQUARE scaling now enforced linearly |
| GRADIENT-003 | DB-AT-031 | Active | Stage B HKL grid CPU transfer corruption |
| n/a | DB-AT-030 | n/a | No blocking findings; sigma precedence spec complete |

**Source:** `docs/findings.md:140-141`, `docs/development/TEST_SUITE_INDEX.md:12`

---

## Onboarding Priority Assessment

### High Priority (ready for implementation)
1. **DB-AT-030** (Sigma precedence): Complete spec with 5 test cases (A-E), no blockers, validates sigma_readout provenance telemetry
2. **DB-AT-032** (Stage C detector offsets): Stage C already wired and passing; selector formalizes existing functionality

### Medium Priority (needs infrastructure)
3. **DB-AT-040** (Trace schema): Requires trace mode wiring; spec-db-tracing.md provides complete schema
4. **DB-AT-050** (VIS conformance): VIS helpers exist; needs test harness and artifact validation

### Blocked (awaiting prerequisite work)
5. **DB-AT-025** (HKL interpolation halo): Only applicable to Stage B/C with interpolation enabled; Stage A canonical is `interpolate=False`
6. **DB-AT-031** (Stage B ASU mapping): Blocked by GRADIENT-003 (HKL grid CPU transfer corruption)

---

## Recommendation

**Phase D.2 scoping complete.** No proposed selectors require immediate onboarding beyond what is already tracked in TEST_SUITE_INDEX.md. The failing DB-AT-028/029 selectors are blocked by architectural issues in ARCH-SIM-CONSTRUCTION-001.

**When to revisit:**
1. When ARCH-SIM-CONSTRUCTION-001 resolves (unblocks DB-AT-028/029)
2. When ARCH-GRADIENT-FLOW-001 completes (unblocks DB-AT-010/011/031)
3. When sigma map ingestion feature lands (enables DB-AT-030)
4. When Stage C smoke tests are stable (enables DB-AT-032 formalization)

**Phase D.2 status:** Scoped. No immediate onboarding needed. Next D2 review: when any of the above blockers clears.

---

## Appendix: Spec Citations

### DB-AT-025
> "When `crystal.interpolate=True`, the dense |F| grid MUST include a ±1 halo; any default_F fallback is a failure. Stage A is canonically `interpolate=False`; any Stage-A run that enables interpolation is non-canonical and SHALL be flagged in telemetry." — spec-db-conformance.md:27

### DB-AT-030
> "Goal: Verify `sigma_readout` precedence and telemetry: map > scalar > external_lookup; missing sigma errors. [...] Case D: no map, no scalar, no tiles. CLI MUST refuse to run with a descriptive error mentioning missing sigma." — spec-db-conformance.md:94-106

### DB-AT-031
> "Goal: Validate Stage-B per-reflection (or shell) modifier plumbing, ASU mapping, and gradients with interpolation+halo enforced." — spec-db-conformance.md:360-364

### DB-AT-032
> "Goal: Ensure detector-distance refinement is wired and yields sane chi² behavior." — spec-db-conformance.md:366-370

### DB-AT-040
> "Goal: Validate the trace payload layout and required fields per `docs/spec-db-tracing.md`." — spec-db-conformance.md:372-376

### DB-AT-050
> "Goal: Ensure ROI triptych and residual plots follow the visual standards in `spec-db-vis.md`." — spec-db-conformance.md:378-382
