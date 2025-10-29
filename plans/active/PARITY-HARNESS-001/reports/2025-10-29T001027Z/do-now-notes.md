# Do Now Notes — PARITY-HARNESS-001 Phase B

**Focus:** PARITY-HARNESS-001 — Author DB-AT parity harness specs
**Timestamp:** 2025-10-29T001027Z
**Engineer:** Ralph
**Mode:** Docs

---

## Do Now Items (from input.md)

### 1. B1 — Draft docs/parity_harness_spec.md ✓

**Action:** Draft docs/parity_harness_spec.md with normative DB-AT-001/002 datasets, env flags, metrics, and trace workflow

**Completed:**
- Created `docs/parity_harness_spec.md` (600+ lines, 8 sections)
- Section 2: DB-AT-001 (Simple Cubic Parity)
  - §2.1: Test objectives (correlation ≥0.99, residual RMS, trace parity)
  - §2.2: Golden data requirements (location, artifacts, checksum verification)
  - §2.3: Configuration parity (critical parameters, validation rules)
  - §2.4: Environment configuration (KMP_DUPLICATE_LIB_OK=TRUE, canonical command)
  - §2.5: Metrics computation (required core metrics, optional extended metrics, Python helper)
  - §2.6: Trace capture workflow (pixel selection, 20+ checkpoints, naming convention)
  - §2.7: Artifact layout (parity/ subdirectory structure)
  - §2.8: Pass/fail criteria
- Section 3: DB-AT-002 (Determinism Validation)
  - §3.1: Test objectives (same-seed bitwise equality, diff-seed independence)
  - §3.2: Environment configuration (CUDA_VISIBLE_DEVICES='', TORCHDYNAMO_DISABLE=1, etc.)
  - §3.3: Test scenarios (same-seed, diff-seed, platform fingerprint)
  - §3.4: Metrics computation (bitwise_equal, correlation thresholds, percent_pixels_differ)
  - §3.5: RNG seed propagation (seed contract, LCG determinism)
  - §3.6: Artifact layout (determinism/ subdirectory)
  - §3.7: Pass/fail criteria
- Section 4: Artifact Policy (Cross-Test)
  - §4.1: Directory structure (parity/ and determinism/ layout)
  - §4.2: Artifact capture macro
  - §4.3: Metrics JSON schema (required and optional fields)
  - §4.4: Fix plan integration (required lines)
- Section 5: Cross-Document Synchronization
  - §5.1: Required documentation updates
  - §5.2: Synchronization checklist
- Section 6: Known Gaps & Future Work
  - §6.1: Tooling gaps (5 helpers identified)
  - §6.2: Golden data accessibility
  - §6.3: Platform-specific determinism

**Spec Citations:**
- docs/spec-db-conformance.md:10-48
- docs/development/testing_strategy.md:1-451
- docs/spec-db-tracing.md:10-26
- docs/TESTING_GUIDE.md:1-91
- docs/development/c_to_pytorch_config_map.md
- docs/spec-db-core.md:24,43,51
- docs/spec-db-runtime.md:18-21
- docs/pytorch_runtime_checklist.md:26,31
- docs/architecture.md ADR-05

### 2. B2 — Update implementation.md Phase B checklist ✓

**Action:** Update plans/active/PARITY-HARNESS-001/implementation.md Phase B checklist with sub-tasks tied to the new spec

**Completed:**
- Marked B1-B3 checklist items complete with sub-item detail
- Added "Status" section: Phase B Complete (2025-10-29T001027Z)
- Added "Deliverables" section documenting parity_harness_spec.md structure
- Updated "Notes & Risks" with resolution status:
  - Trace workflow addressed in parity_harness_spec.md §2.6 ✓
  - Golden data mitigation documented in §6.2
  - Tooling gaps identified in §6.1 for Phase C

### 3. B3 — Publish metrics/trace template and artifact layout ✓

**Action:** Publish metrics/trace template and artifact layout snippet in docs/parity_harness_spec.md and capture copies under the report path

**Completed:**

1. **Embedded in parity_harness_spec.md:**
   - Metrics JSON schema in §4.3
   - Trace requirements in §2.6
   - Artifact layout in §4.1
   - Python helper function in §2.5

2. **Evidence artifacts created:**
   - `plans/active/PARITY-HARNESS-001/reports/2025-10-29T001027Z/parity/metrics_template.json`
     - Annotated JSON with required core metrics, metadata, optional fields
     - Comment fields explaining semantics and spec references
   - `plans/active/PARITY-HARNESS-001/reports/2025-10-29T001027Z/parity/trace_requirements.md`
     - Normative trace naming conventions
     - Required 20+ checkpoints (pix0_vector, basis_vectors, R, solid_angle, k_in, k_out, S, Miller indices, structure factors, lattice factors, final_intensity)
     - Format requirements (float64 precision, units)
     - First divergence workflow
     - Integration notes for nanobrag_torch
   - `plans/active/PARITY-HARNESS-001/reports/2025-10-29T001027Z/parity/artifact_layout.md`
     - Normative directory structure
     - Example DB-AT-001/002 runs
     - Artifact capture macro (shell script)
     - Required artifacts by test
     - Fix plan integration pattern
     - Checksum validation

---

## Test Collection Commands

Per input.md lines 5-6, validated selectors:

**DB_AT_001:**
```bash
KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q -k DB_AT_001
```
**Result:** 0 tests collected (27 deselected) — Expected (selector planned)
**Log:** collect_DB_AT_001.log

**DB_AT_002:**
```bash
KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q -k DB_AT_002
```
**Result:** 0 tests collected (27 deselected) — Expected (selector planned)
**Log:** collect_DB_AT_002.log

---

## Findings Applied

### CONFORMANCE-001 (docs/findings.md:7)
- Harness spec keeps DB-AT selectors and KMP_DUPLICATE_LIB_OK=TRUE canonical
- Application: All canonical commands in §2.4, §3.2 match TESTING_GUIDE.md

### RUNTIME-001 (docs/findings.md:6)
- Determinism guidance reiterates NANOBRAGG_DISABLE_COMPILE=1 and related flags
- Application: §3.2 includes NANOBRAGG_DISABLE_COMPILE=1 with rationale synchronized to testing_strategy.md:1.6

---

## Pitfalls Avoided

Per input.md lines 24-31:

- ✓ Included correlation ≥0.99 requirement in §2.8
- ✓ Documented determinism env flags (CUDA_VISIBLE_DEVICES='', TORCHDYNAMO_DISABLE=1, NANOBRAGG_DISABLE_COMPILE=1) in §3.2
- ✓ Documented golden data verification steps with checksum validation in §2.2
- ✓ Referenced docs/index.md and prompt_sources_map.json in §5.1 (synchronization for Phase C)
- ✓ Captured artifacts under report directory (parity/ subdirectory)
- ✓ Embedded trace capture workflow from spec-db-tracing.md in §2.6
- ✓ Standardized metrics schema with proposed correlation/MSE/RMSE/max|Δ|/sum_ratio core fields in §4.3

---

## Phase B Deliverables Summary

**Primary Documentation:**
- `docs/parity_harness_spec.md` — 600+ line normative specification

**Evidence Artifacts (Templates):**
- `metrics_template.json` — Annotated JSON schema
- `trace_requirements.md` — 20+ checkpoints, naming conventions, workflow
- `artifact_layout.md` — Directory structure, examples, capture macro

**Updated Plans:**
- `plans/active/PARITY-HARNESS-001/implementation.md` — Phase B marked complete

**Test Collection Logs:**
- `collect_DB_AT_001.log` — 0 tests (expected)
- `collect_DB_AT_002.log` — 0 tests (expected)

---

## Next Actions

Per summary.md and implementation.md:

**Immediate (Phase C):**
- C1: Update TESTING_GUIDE.md §2 and TEST_SUITE_INDEX.md with artifact expectations
- C2: Add parity_harness_spec.md to index.md and prompt_sources_map.json
- C3: Capture final evidence and update fix_plan.md

**Future (Implementation):**
- Author DB-AT-001 test scaffold (tests/test_db_at_001.py)
- Author DB-AT-002 test scaffold (tests/test_db_at_002.py)
- Implement helper utilities (§6.1):
  - compute_parity_metrics() — correlation/MSE/RMSE computation
  - trace capture fixture — nanobrag_torch debug_config integration
  - diff heatmap generator — matplotlib visualization
  - golden data loader — checksum validation
  - metrics JSON writer — standardized output

---

## Execution Time

- Start: 2025-10-29T001027Z
- End: 2025-10-29T~001500Z (estimated)
- Duration: ~28 minutes (docs-only mode, no code execution)
