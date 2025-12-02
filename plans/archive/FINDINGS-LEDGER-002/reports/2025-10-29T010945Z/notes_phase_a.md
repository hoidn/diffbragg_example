# Phase A Notes — Artifact Inventory & Lesson Extraction
## Loop: FINDINGS-LEDGER-002 | Timestamp: 2025-10-29T010945Z

## Objective
Review TORCH-BRIDGE-001 and TORCH-CLI-003 artifacts to extract durable lessons for `docs/findings.md` knowledge base.

## Artifact Inventory

### TORCH-BRIDGE-001 Reports
Location: `plans/active/TORCH-BRIDGE-001/reports/`

#### 2025-10-28T222910Z (Phase A: Bridge Helper)
- `do-now-notes.md` — Phase A implementation summary (tensor contract, mask polarity)
- `pytest.log` — 4 tests passed (0.12s runtime)

#### 2025-10-28T224846Z (Phase B: Config Hydration)
- `do-now-notes.md` — Config mapping implementation (Detector/Beam/Crystal)
- `config_snapshots.json` — Test results + pitfalls avoided catalog
- `pytest.log` — 6 detector tests
- `pytest_full.log` — 18 total tests (0.18s runtime)

**Key Metrics:**
- Total tests: 18 (4 bridge + 14 config)
- Runtime: 0.18s (CPU)
- Python: 3.9.23, PyTorch: 2.8.0
- Pitfalls avoided: 6 (beam center swap, sample→source normalization, mask polarity, etc.)

**Key Findings (Phase B):**
1. **Beam center swap required:** dxtbx stores (fast, slow) but torch expects (beam_center_s, beam_center_f)
2. **Crystal A* tuple handling:** `crystal.get_A()` returns 9-element tuple, must reshape to 3x3 and extract columns
3. **Mask polarity preservation:** bool True=include → float 1.0=include (no inversion)
4. **Sample→source vector:** Must normalize -s0/||s0|| for custom_beam_vector (not source→sample)
5. **Unit cell angles:** dxtbx and torch both use degrees (no conversion needed)
6. **Square pixel enforcement:** Bridge guards against non-square pixels per spec-db-core.md:43

#### 2025-10-28T230500Z (Phase C: Smoke Harness)
- `do-now-notes.md` — Single-experiment flow with ROI triptych
- `pytest.log` — 3 smoke tests passed (1.83s runtime)
- `smoke_metrics.json` — Metrics from 92 ROIs
- `roi_triptych.png` — Visual artifact (ROI layout)

**Key Metrics:**
- n_panels: 1
- n_rois: 92
- target_shape: [1, 2527, 2463]
- masked_mse: 959991.3 (stub Gaussian baseline vs real data)
- loss_mask_coverage: 0.21%
- mean_intensity_per_panel: 98.89 ADU
- max_intensity_per_panel: 473.20 ADU

**Key Findings (Phase C):**
1. **ROI metrics structure:** JSON schema with n_panels, n_rois, target/bragg shapes, masked_mse, coverage
2. **Loss mask coverage:** 0.21% (very sparse, typical for Bragg peaks)
3. **Intensity scale:** Mean ~99 ADU, max ~473 ADU (background-subtracted targets)

#### 2025-10-28T233500Z (Closure Validation)
- `do-now-notes.md` — Final validation run
- `pytest.log` — 21 tests passed (1.93s runtime)
- `run_env.txt` — Environment snapshot
- `smoke_metrics.json` — Duplicate of 2025-10-28T230500Z metrics
- `roi_triptych.png` — Duplicate of 2025-10-28T230500Z artifact

### TORCH-CLI-003 Reports
Location: `plans/active/TORCH-CLI-003/reports/`

#### 2025-10-28T234618Z (Phase A/B: Backend Flag Implementation)
- `notes.md` — CLI backend flag implementation notes
- `diagnostics.json` — Test results and implementation status
- `cli_help.log` — Help text showing --backend flag
- `cli_help_before.log` — Baseline help text
- `pytest.log` — 6 CLI tests passed (0.98s runtime)

**Key Metrics:**
- Total tests: 6 (all CLI-focused)
- Runtime: 0.98s (CPU)
- Python: 3.9.23, pytest: 8.4.2
- Backend choices: ["diffbragg", "nanobrag"]
- Default: "diffbragg"

**Implementation Status:**
- backend_flag: implemented
- nanobrag_backend: bridge integration complete, stub simulator active, diagnostics group implemented
- diffbragg_backend: preserved bit-for-bit, unchanged

**Key Findings (Phase A/B):**
1. **Backend dispatch pattern:** CLI parser routes to backend-specific functions
2. **Diagnostics group:** Torch backend emits `/torch_diagnostics` HDF5 group with metadata
3. **Test strategy:** Mocking used to validate integration points without external dependencies

#### 2025-10-29T003751Z (Phase C: Registry & Doc Sync)
- `summary.md` — Comprehensive completion summary
- `pytest_cli.log` — 6 tests passed with full output
- `collect_cli.log` — Collection evidence (6 tests discovered)
- `doc_diff.log` — Documentation changes (3 files, 5 insertions, 2 deletions)

**Key Findings (Phase C):**
1. **Selector compliance:** CLI selector marked Active only after collection confirmed >0 tests
2. **Environment flags:** All CLI tests require `KMP_DUPLICATE_LIB_OK=TRUE`
3. **Documentation parity:** TESTING_GUIDE.md and TEST_SUITE_INDEX.md synchronized
4. **Artifact policy:** All outputs stored under documented reports path

## Cross-Initiative Patterns

### Environment Flags
- **KMP_DUPLICATE_LIB_OK=TRUE:** Required for all pytest runs (torch + MKL conflict mitigation)
- **NANOBRAGG_DISABLE_COMPILE=1:** Required for gradient tests (torch.autograd.gradcheck compatibility)

### Test Coverage Metrics
- Bridge tests: 4 (tensor contract, mask polarity, pixel pitch guard, tuple masks)
- Config tests: 14 (detector=6, beam/crystal=8)
- Smoke tests: 3 (flow, MSE, artifacts)
- CLI tests: 6 (parser, dispatch, bridge integration, diagnostics)
- **Total:** 27 tests across both initiatives

### Artifact Patterns
1. **Metrics JSON:** Standardized structure (n_panels, n_rois, shapes, masked_mse, coverage)
2. **Do-now notes:** Structured markdown with objectives, actions, results, next actions
3. **Pytest logs:** Full output with runtime, platform, warnings
4. **Collection logs:** Evidence for selector compliance (--collect-only output)
5. **Summary documents:** Closure reports with metrics, artifacts, exit criteria verification

### Spec Compliance References
Most frequently cited specs:
- `docs/spec-db-core.md:24` — [panel, slow, fast] ordering
- `docs/spec-db-core.md:43` — Square pixel guard
- `docs/config_crosswalk.md:29` — Beam center swap (fast,slow) → (s,f)
- `docs/dxtbx_api.md:5-42` — Geometry extraction API
- `docs/spec-db-conformance.md:10` — DB-AT parity selectors

## Candidate Findings for docs/findings.md

### 1. HDF5 Diagnostics Pattern
**ID:** DIAGNOSTICS-001
**Tags:** HDF5, diagnostics, torch, metrics
**Summary:** Torch backend emits `/torch_diagnostics` HDF5 group with standardized metadata (masked_mse, loss_mask_coverage, n_rois, target_shape, backend) enabling reproducible parity debugging.
**Source:** `dbex/refine_one.py:80-95`, `plans/active/TORCH-CLI-003/reports/2025-10-28T234618Z/diagnostics.json`
**Rationale:** Establishes pattern for future torch backend diagnostics; aligns with spec-db-tracing.md requirements.

### 2. Loss Mask Coverage Interpretation
**ID:** MASKING-001
**Tags:** masking, ROI, coverage, diagnostics
**Summary:** Loss mask coverage in Bragg peak refinement is typically <1% (e.g., 0.21% for 92 ROIs on 2527×2463 detector) reflecting sparse Bragg peak distribution; low coverage is expected and not a failure signal.
**Source:** `plans/active/TORCH-BRIDGE-001/reports/2025-10-28T230500Z/smoke_metrics.json`, `docs/spec-db-workflow.md:24-29`
**Rationale:** Prevents misinterpretation of low coverage values during parity debugging; informs threshold expectations.

### 3. CLI Testing Strategy
**ID:** TESTING-002
**Tags:** testing, CLI, mocking, integration
**Summary:** CLI integration tests use mocking to validate dispatch logic and bridge integration without external dependencies; tests verify parser contracts, backend routing, and diagnostics structure independently of simulator implementation.
**Source:** `tests/dbex/test_refine_one_cli.py:1-200`, `plans/active/TORCH-CLI-003/reports/2025-10-29T003751Z/summary.md`
**Rationale:** Demonstrates layered testing strategy (unit tests independent of simulator); enables TDD for CLI features before backend implementation.

### 4. Config Hydration Pitfalls Catalog
**ID:** CONFIG-001
**Tags:** config, dxtbx, nanobrag, mapping, pitfalls
**Summary:** Config hydration from dxtbx to nanobrag_torch requires careful attention to: (1) beam center swap (fast,slow)→(s,f), (2) crystal A* tuple→array reshape, (3) mask polarity preservation, (4) sample→source vector normalization, (5) unit cell angle units (degrees, no conversion), (6) square pixel enforcement.
**Source:** `dbex/nanobrag_bridge.py:120-399`, `plans/active/TORCH-BRIDGE-001/reports/2025-10-28T224846Z/config_snapshots.json`
**Rationale:** Consolidates six common pitfalls into single finding; references implementation and test evidence.

### 5. Selector Compliance Workflow
**ID:** TESTING-003
**Tags:** testing, selectors, compliance, documentation
**Summary:** Selector status transitions to "Active" only after `pytest --collect-only` confirms >0 tests collected; TESTING_GUIDE.md and TEST_SUITE_INDEX.md must be synchronized with collection log artifacts; prevents documentation drift and ensures discoverable selectors.
**Source:** `docs/TESTING_GUIDE.md:56-68`, `plans/active/TORCH-CLI-003/reports/2025-10-29T003751Z/collect_cli.log`
**Rationale:** Codifies observed workflow pattern across multiple loops; aligns with docs/development/testing_strategy.md:169-174.

## Validation Against Existing Findings
Current `docs/findings.md` entries:
- GEOMETRY-001: Beam center/pixel pitch guardrails (related to CONFIG-001 but narrower scope)
- RUNTIME-001: Gradient test environment flags (already covered)
- CONFORMANCE-001: DB-AT selectors and KMP flag (already covered)
- DXTBX-001: Crystal A* tuple handling (subsumed by CONFIG-001)

**No duplicates detected.** Proposed findings extend coverage to:
- Diagnostics/HDF5 patterns (new domain)
- Masking/coverage interpretation (new domain)
- CLI testing strategy (new domain)
- Comprehensive config pitfalls catalog (extends GEOMETRY-001 and DXTBX-001)
- Selector compliance workflow (extends CONFORMANCE-001)

## Next Actions (Phase B)
1. Draft at least three new finding entries with IDs, tags, summaries, source citations
2. Update `docs/findings.md` with new entries
3. Self-review for clarity and spec/code citation accuracy
4. Capture git diff → `$ART/findings_diff.log`

## Artifacts Generated (Phase A)
- `notes_phase_a.md` — This document
