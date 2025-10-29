# Parity Harness Audit Notes — PARITY-HARNESS-001 A1

**Focus**: DB-AT-001/002 parity harness groundwork
**Timestamp**: 2025-10-29T000004Z
**Mode**: Docs
**Engineer**: Ralph

---

## A1: Documentation Gap Analysis

### Current State Summary

**DB-AT-001 (Simple cubic parity)**
- **Spec**: `docs/spec-db-conformance.md:25-28`
  - Setup: use `nanoBragg2/tests/golden_data` configuration; simulate panel; compare to golden frame
  - Expectation: image correlation ≥ 0.99; residual RMS within tolerance
  - Command: `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests -k DB_AT_001`
  - Status: Placeholder (normative contract exists but no test implementation)

- **Testing Guide**: `docs/TESTING_GUIDE.md:61`
  - Selector: `pytest -v tests -k DB_AT_001`
  - Purpose: Validates simple cubic parity per spec
  - Status: Planned (requires golden data; correlation ≥0.99)
  - Notes: Smoke/acceptance taxonomy, artifact policy in §3-4

- **Test Suite Index**: `docs/development/TEST_SUITE_INDEX.md:7`
  - Selector: `pytest -v tests -k DB_AT_001`
  - Status: planned
  - Spec Reference: `docs/spec-db-conformance.md:24`
  - Notes: Uses golden data under `nanoBragg2/tests/golden_data`; validates simple cubic correlation ≥0.99

- **Testing Strategy**: `docs/development/testing_strategy.md:25-36`
  - Section 2.1: Golden Reference Data structure (`.bin`, trace logs, JSON metadata)
  - Section 2.3: Golden Suite test cases (simple_cubic baseline case)
  - Section 2.5: Validation Matrix (AT ↔ tests ↔ commands)
  - Notes: Detailed parity workflow, trace capture requirements, metrics definitions

**DB-AT-002 (Determinism)**
- **Spec**: `docs/spec-db-conformance.md:13`
  - Profile: C-Parity Profile element
  - Expectation: Determinism under fixed seeds (bitwise or tolerance-stable outputs)
  - Status: Placeholder in conformance profile

- **Testing Guide**: `docs/TESTING_GUIDE.md:62`
  - Selector: `pytest -v tests -k DB_AT_002`
  - Purpose: Bitwise/tolerance equality with locked RNG seeds
  - Status: Planned
  - Environment: See `docs/development/testing_strategy.md` §2.7

- **Test Suite Index**: `docs/development/TEST_SUITE_INDEX.md:8`
  - Selector: `pytest -v tests -k DB_AT_002`
  - Status: planned
  - Spec Reference: `docs/development/testing_strategy.md:2.7`
  - Notes: Requires fixtures that lock RNG seeds and check bitwise/tolerance equality. Environment: CPU-only, CUDA_VISIBLE_DEVICES=''

- **Testing Strategy**: `docs/development/testing_strategy.md:202-315`
  - Section 2.7: Comprehensive determinism validation workflow
  - Authoritative tests: test_at_parallel_013.py (cross-platform), test_at_parallel_024.py (mosaic/misset RNG)
  - Environment guards: CUDA_VISIBLE_DEVICES='', TORCHDYNAMO_DISABLE=1, NANOBRAGG_DISABLE_COMPILE=1
  - Metrics: bitwise equality, correlation ≥0.9999999, statistical independence tests
  - Commands: Detailed reproduction commands and artifact expectations

### Gap Analysis

#### DB-AT-001 Gaps
1. **No test implementation**: Selector collects 0 tests (confirmed via pytest --collect-only)
2. **Golden data location uncertain**: Spec references `nanoBragg2/tests/golden_data` but unclear if accessible in DBEX context
3. **Missing harness spec**: No concrete test scaffold, fixture setup, or metrics collection template
4. **Artifact schema undefined**: No documented metrics.json structure for parity runs beyond general guidance in testing_strategy.md §2.5
5. **Trace capture workflow**: spec-db-tracing.md:15-26 provides normative requirements but no DBEX-specific implementation
6. **Configuration parity**: testing_strategy.md §2 emphasizes configuration parity as critical but no DBEX-specific crosswalk to golden data params

#### DB-AT-002 Gaps
1. **No test implementation**: Selector collects 0 tests (confirmed via pytest --collect-only)
2. **Fixture missing**: No seed-locking fixtures in DBEX tests/ directory
3. **Environment setup**: Comprehensive environment guards documented in testing_strategy.md:2.7 but not yet integrated into DBEX workflow
4. **Metrics undefined**: No DBEX-specific thresholds or artifact templates for determinism validation
5. **Platform fingerprinting**: testing_strategy.md references platform fingerprinting (test_at_parallel_013.py) but no DBEX equivalent

#### Cross-Cutting Gaps
1. **Metrics template**: No standardized metrics.json schema for parity runs (should include: correlation, MSE, RMSE, max|Δ|, sum ratios, SSIM optional)
2. **Artifact routing**: General artifact policy exists (TESTING_GUIDE.md §3) but no parity-specific subdirectory convention
3. **Trace integration**: spec-db-tracing.md defines workflow but no concrete DBEX helper or fixture
4. **Golden data access**: Unclear if `nanoBragg2/tests/golden_data` is available or needs DBEX-local mirror
5. **Command canonicalization**: Environment flags documented but no shell alias/wrapper to reduce friction (testing_strategy.md §2.5.2)
6. **CI integration**: No mention of parity gates in CI (testing_strategy.md §2.6 references visual parity harness but not DBEX-specific)

### Documentation Strengths
1. **Comprehensive testing philosophy**: testing_strategy.md provides excellent three-tier approach and detailed parity workflow
2. **Environment flags well-documented**: TESTING_GUIDE.md §1 and testing_strategy.md §1.6 provide clear rationale and scope
3. **Spec citations**: Existing docs cross-reference spec shards consistently
4. **Selector synchronization**: TESTING_GUIDE.md and TEST_SUITE_INDEX.md are already in sync for DB-AT-001/002 placeholders
5. **Tracing contract**: spec-db-tracing.md provides clear normative requirements (per-pixel trace, production code paths, first divergence workflow)

### Alignment with Exit Criteria

**Exit Criterion 1**: Draft normative harness specs for DB-AT-001/002
- **Current**: Placeholder specs exist in conformance.md with correlation thresholds and command scaffolds
- **Needed**: Promote to actionable checklists with datasets, fixture setup, metrics collection, trace capture workflow

**Exit Criterion 2**: Publish supporting blueprint under implementation.md
- **Current**: Phase A-C structure exists in implementation plan
- **Needed**: Populate Phase B with concrete harness tasks (test scaffold, fixtures, metrics template, trace helpers)

**Exit Criterion 3**: Sync TESTING_GUIDE.md and TEST_SUITE_INDEX.md
- **Current**: Selectors present with placeholders; environment flags documented
- **Needed**: Add artifact expectations (metrics.json schema, trace logs, diff heatmaps) and parity-specific subdirectory convention

**Exit Criterion 4**: Update index.md and prompt_sources_map.json
- **Current**: References exist but point to general testing docs
- **Needed**: Add explicit harness spec reference once authored (e.g., docs/parity_harness_spec.md or enhanced conformance.md section)

---

## Findings Applied

**CONFORMANCE-001** (`docs/findings.md:7`)
- DB-AT selectors and environment flags (`KMP_DUPLICATE_LIB_OK=TRUE`) are authoritative per conformance spec
- Applied: Audit confirms all selectors documented with correct env flags in TESTING_GUIDE.md §1.1-1.3
- Gap: NANOBRAGG_DISABLE_COMPILE=1 documented for gradcheck (TESTING_GUIDE.md:1.2) but not explicitly linked to future DB-AT-002 determinism tests

**RUNTIME-001** (`docs/findings.md:6`)
- Gradient tests require NANOBRAGG_DISABLE_COMPILE=1 to avoid Dynamo interference
- Applied: Documented in testing_strategy.md:1.6 and TESTING_GUIDE.md:1.2 with detailed rationale
- Note: Future gradcheck in parity context (if any) must honor this flag

---

## Next Actions (feeds into A2/A3)

1. **Review prior artifacts** (A2):
   - Extract reusable metrics schema from TORCH-BRIDGE-001 smoke_metrics.json
   - Extract diagnostics structure from TORCH-CLI-003 diagnostics.json
   - Document metrics fields required for parity runs vs general smoke tests

2. **Define artifact strategy** (A3):
   - Propose parity-specific subdirectory: `plans/active/<initiative>/reports/<timestamp>/parity/`
   - Define metrics.json template: `{correlation, mse, rmse, max_abs_diff, sum_ratio, n_pixels, dtype, device, golden_path, py_path}`
   - Define trace log naming convention: `golden_trace_panel{p}_s{s}_f{f}.log` and `py_trace_panel{p}_s{s}_f{f}.log`
   - Note requirement for diff heatmap artifacts (PNG or similar)

3. **Phase B prep**:
   - Identify minimal golden dataset for DB-AT-001 (simple cubic case from nanoBragg2/tests/golden_data or generate DBEX-local)
   - Draft test scaffold structure: fixture for golden data loading, parametrized test over dtypes/devices, metrics collection helper
   - Plan trace capture helper integration (spec-db-tracing.md workflow)

---

## References
- `docs/spec-db-conformance.md:10-48` — Normative acceptance test definitions
- `docs/development/testing_strategy.md:1-451` — Comprehensive testing philosophy and parity workflow
- `docs/TESTING_GUIDE.md:1-91` — Canonical environment flags and test taxonomy
- `docs/development/TEST_SUITE_INDEX.md:1-21` — Selector registry synchronized with TESTING_GUIDE
- `docs/spec-db-tracing.md:1-26` — Normative tracing requirements and parity workflow
- `docs/findings.md` — Knowledge base (CONFORMANCE-001, RUNTIME-001)
- `plans/active/TORCH-BRIDGE-001/reports/2025-10-28T233500Z/smoke_metrics.json` — Smoke test metrics reference
- `plans/active/TORCH-CLI-003/reports/2025-10-28T234618Z/diagnostics.json` — CLI diagnostics reference
