# PARITY-HARNESS-001 Phase B Summary

**Focus:** PARITY-HARNESS-001 — Author DB-AT parity harness specs
**Phase:** B (Harness Blueprint)
**Timestamp:** 2025-10-29T001027Z
**Engineer:** Ralph
**Mode:** Docs

---

## Objectives Completed

Phase B of PARITY-HARNESS-001 focused on drafting normative parity harness specifications for DB-AT-001 (simple cubic parity) and DB-AT-002 (determinism validation), updating the implementation plan, and publishing metrics/trace templates.

### B1: Draft Parity Harness Specification ✓

**Deliverable:** `docs/parity_harness_spec.md`

**Content Summary:**
- 8 normative sections (600+ lines)
- DB-AT-001 specification (§2): Golden data requirements, configuration parity, environment configuration, metrics computation, trace capture workflow, artifact layout, pass/fail criteria
- DB-AT-002 specification (§3): Determinism objectives, environment guards, test scenarios (same-seed, diff-seed), RNG seed propagation, metrics computation, artifact layout
- Cross-test artifact policy (§4): Directory structure, metrics JSON schema, artifact capture macro, fix plan integration
- Cross-document synchronization (§5): Required documentation updates and synchronization checklist
- Known gaps & future work (§6): Tooling gaps, golden data accessibility, platform-specific determinism

**Key Features:**
- **Metrics JSON Schema** (§4.3): Standardized schema with required core metrics (correlation, MSE, RMSE, max_abs_diff, sum_ratio, golden_sum, py_sum, n_pixels) and optional extended metrics (SSIM, runtime, hardware, versions)
- **Trace Requirements** (§2.6): 20+ required checkpoints per testing_strategy.md §117 (pix0_vector, basis_vectors, R, solid_angle, obliquity_factor, k_in, k_out, S, Miller indices, structure factors, lattice factors, final intensity)
- **Artifact Layout** (§4.1): Normative directory structure with parity/ and determinism/ subdirectories
- **Environment Configuration** (§2.4, §3.2): Synchronized with TESTING_GUIDE.md §1 (KMP_DUPLICATE_LIB_OK, NANOBRAGG_DISABLE_COMPILE, CUDA_VISIBLE_DEVICES, TORCHDYNAMO_DISABLE)
- **Pass/Fail Criteria** (§2.8, §3.7): Aligned with spec-db-conformance.md thresholds (correlation ≥0.99 for DB-AT-001, bitwise equality for DB-AT-002 same-seed)
- **Python Helper** (§2.5): Reference implementation of `compute_parity_metrics()` function

**Spec Citations:**
- `docs/spec-db-conformance.md:10-48` — Acceptance test definitions
- `docs/development/testing_strategy.md:1-451` — Testing philosophy and parity workflow
- `docs/spec-db-tracing.md:10-26` — Tracing requirements
- `docs/TESTING_GUIDE.md:1-91` — Environment flags
- `docs/development/c_to_pytorch_config_map.md` — Configuration parity
- `docs/spec-db-core.md:24,43,51` — Data contracts
- `docs/spec-db-runtime.md:18-21` — Runtime guardrails
- `docs/pytorch_runtime_checklist.md:26,31` — Runtime checklist
- `docs/architecture.md` ADR-05 — Deterministic sampling

### B2: Update Implementation Plan ✓

**Deliverable:** `plans/active/PARITY-HARNESS-001/implementation.md` (Phase B section)

**Changes:**
- Marked B1-B3 checklist items complete with sub-item detail
- Added Phase B "Status" section: **Phase B Complete (2025-10-29T001027Z)**
- Added Phase B "Deliverables" section with comprehensive artifact summary
- Updated "Notes & Risks" with resolution status (trace workflow addressed in parity_harness_spec.md §2.6, golden data mitigation documented in §6.2, tooling gaps identified in §6.1)

### B3: Publish Metrics/Trace Templates ✓

**Deliverables:**

1. **Metrics JSON Template**
   - Path: `plans/active/PARITY-HARNESS-001/reports/2025-10-29T001027Z/parity/metrics_template.json`
   - Content: Annotated JSON with required core metrics, required metadata, optional extended metrics
   - Includes comment fields explaining field semantics and spec references

2. **Trace Requirements Template**
   - Path: `plans/active/PARITY-HARNESS-001/reports/2025-10-29T001027Z/parity/trace_requirements.md`
   - Content: Normative trace naming conventions, required checkpoints (20+ fields), format requirements, pixel selection strategy, first divergence workflow, integration notes
   - Spec references: parity_harness_spec.md §2.6, spec-db-tracing.md:10-26, testing_strategy.md:117

3. **Artifact Layout Template**
   - Path: `plans/active/PARITY-HARNESS-001/reports/2025-10-29T001027Z/parity/artifact_layout.md`
   - Content: Normative directory structure, example DB-AT-001/002 runs, artifact capture macro, required artifacts by test, fix plan integration pattern, checksum validation
   - Includes shell macro for artifact directory creation and environment capture

---

## Artifacts Generated

### Primary Documentation
- `docs/parity_harness_spec.md` — 600+ line normative specification

### Templates (Evidence Artifacts)
- `plans/active/PARITY-HARNESS-001/reports/2025-10-29T001027Z/parity/metrics_template.json`
- `plans/active/PARITY-HARNESS-001/reports/2025-10-29T001027Z/parity/trace_requirements.md`
- `plans/active/PARITY-HARNESS-001/reports/2025-10-29T001027Z/parity/artifact_layout.md`

### Test Collection Logs
- `plans/active/PARITY-HARNESS-001/reports/2025-10-29T001027Z/collect_DB_AT_001.log`
- `plans/active/PARITY-HARNESS-001/reports/2025-10-29T001027Z/collect_DB_AT_002.log`

### Updated Documentation
- `plans/active/PARITY-HARNESS-001/implementation.md` — Phase B section updated

---

## Test Collection Results

Per `input.md` lines 5-6, validated selectors via pytest --collect-only:

**DB_AT_001:**
```bash
KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q -k DB_AT_001
```
**Result:** 0 tests collected (27 deselected) — Expected (selector planned, no implementation yet)
**Log:** `plans/active/PARITY-HARNESS-001/reports/2025-10-29T001027Z/collect_DB_AT_001.log`

**DB_AT_002:**
```bash
KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q -k DB_AT_002
```
**Result:** 0 tests collected (27 deselected) — Expected (selector planned, no implementation yet)
**Log:** `plans/active/PARITY-HARNESS-001/reports/2025-10-29T001027Z/collect_DB_AT_002.log`

---

## Findings Applied

### CONFORMANCE-001 (`docs/findings.md:7`)
- **Finding:** DB-AT selectors and KMP_DUPLICATE_LIB_OK=TRUE are authoritative per conformance spec
- **Application:** All canonical commands in parity_harness_spec.md §2.4, §3.2 include KMP_DUPLICATE_LIB_OK=TRUE; selectors match TESTING_GUIDE.md §2 exactly

### RUNTIME-001 (`docs/findings.md:6`)
- **Finding:** Gradient tests require NANOBRAGG_DISABLE_COMPILE=1 to avoid Dynamo interference
- **Application:** DB-AT-002 environment configuration (§3.2) includes NANOBRAGG_DISABLE_COMPILE=1 with detailed rationale; synchronized with testing_strategy.md:1.6

---

## Phase B Exit Criteria Assessment

Per `plans/active/PARITY-HARNESS-001/implementation.md` Phase B checklist:

- [x] **B1:** Draft parity_harness_spec.md detailing inputs, commands, metrics for DB-AT-001/002 ✓
  - Delivered: 8 normative sections with comprehensive specifications
  - Citations: 10+ spec shard references

- [x] **B2:** Encode phased harness rollout tasks in implementation plan ✓
  - Delivered: Phase B checklist updated with completion status and deliverables
  - Next: Phase C cross-doc sync tasks (C1-C3)

- [x] **B3:** Prepare metrics/trace capture templates ✓
  - Delivered: metrics_template.json, trace_requirements.md, artifact_layout.md
  - References: Templates embedded in parity_harness_spec.md §2.5, §2.6, §4.1, §4.3

**Status:** Phase B Complete

---

## Gaps Identified for Phase C

Per `docs/parity_harness_spec.md` §6.1, the following helper utilities are required but not yet implemented:

1. **Correlation computation helper** — `compute_parity_metrics()` function (reference implementation in §2.5)
2. **Trace capture integration** — Fixture using `nanobrag_torch` debug_config
3. **Diff heatmap generator** — Matplotlib-based visualization helper
4. **Golden data loader** — Fixture with checksum validation (per §2.2)
5. **Metrics JSON writer** — Standardized output helper

**Mitigation:** These will be addressed incrementally during Phase C or when DB-AT-001/002 test implementations begin. Helper stubs can be authored in `tests/conftest.py` or `tests/fixtures/parity_helpers.py` as needed.

---

## Next Actions

Per `input.md` Phase B scope and `plans/active/PARITY-HARNESS-001/implementation.md`:

1. **Phase C (Cross-Doc Sync):**
   - C1: Update `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` entries for DB-AT-001/002 with finalized harness details (environment flags already synchronized; artifact expectations and parity subdirectory convention need explicit documentation)
   - C2: Add harness references to `docs/index.md` and `docs/prompt_sources_map.json` for discoverability
   - C3: Capture final evidence report and update `docs/fix_plan.md` Attempts History with Metrics/Artifacts lines

2. **Future Implementation:**
   - Author DB-AT-001 test scaffold (`tests/test_db_at_001.py`) with golden data loading fixture
   - Author DB-AT-002 test scaffold (`tests/test_db_at_002.py`) with seed-locking fixture
   - Implement helper utilities identified in §6.1

---

## References

- `input.md` — Phase B Do Now steps (lines 7-9)
- `plans/active/PARITY-HARNESS-001/implementation.md` — Initiative plan with Phase A-C structure
- `docs/parity_harness_spec.md` — Normative harness specification (primary deliverable)
- `docs/spec-db-conformance.md:10-48` — Acceptance test definitions
- `docs/development/testing_strategy.md:1-451` — Testing philosophy
- `docs/spec-db-tracing.md:10-26` — Tracing workflow
- `docs/TESTING_GUIDE.md:1-91` — Environment flags and test taxonomy
- `docs/findings.md` — Knowledge base (CONFORMANCE-001, RUNTIME-001)
