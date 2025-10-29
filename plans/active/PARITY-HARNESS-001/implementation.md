# Implementation Plan — PARITY-HARNESS-001

## Initiative
- ID: PARITY-HARNESS-001
- Title: Author DB-AT parity harness specs
- Owner: Unassigned
- Status: in_progress

## Goals
- Translate Spec DB parity acceptance tests (DB-AT-001/002) into actionable harness documentation and checklists.
- Synchronize parity documentation across spec shards, testing guides, and prompt sources.

## Phases Overview
- Phase A — Evidence Audit: inventory existing parity specs, selectors, and artifacts to ground the harness scope.
- Phase B — Harness Blueprint: author normative parity harness spec and phased checklist aligned with DB-AT requirements.
- Phase C — Cross-Doc Sync: propagate references to the new harness doc and update prompt/source maps.

## Exit Criteria
1. Normative harness specification for DB-AT-001 and DB-AT-002 documented with datasets, metrics, and tolerance targets (`docs/spec-db-conformance.md:10-36`, `docs/development/testing_strategy.md:1-160`).
2. `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` entries for `DB_AT_001`/`DB_AT_002` include commands, env flags, and artifact expectations consistent with the harness spec.
3. `docs/index.md` and `docs/prompt_sources_map.json` reference the harness specification and this implementation plan.
4. Artifact report captures evidence of doc updates and selector synchronization under `plans/active/PARITY-HARNESS-001/reports/<timestamp>/`.

## Phase A — Evidence Audit
### Checklist
- [x] A1: Catalog current parity guidance across `docs/spec-db-conformance.md`, `docs/development/testing_strategy.md`, and `docs/TESTING_GUIDE.md`; note gaps vs exit criteria.
- [x] A2: Inspect prior parity-related artifacts (`plans/active/TORCH-BRIDGE-001/`, `plans/active/TORCH-CLI-003/`) for reusable metrics or lessons to anchor the harness spec.
- [x] A3: Define artifact strategy (`reports/<timestamp>/`) for parity harness documentation (log commands, summary.md blueprint).

### Status
**Phase A Complete** (2025-10-29T000004Z)

### Deliverables
- **Audit Notes**: `plans/active/PARITY-HARNESS-001/reports/2025-10-29T000004Z/audit_notes.md`
  - Gap analysis for DB-AT-001/002 across conformance spec, testing strategy, testing guide, and test suite index
  - Identified 6 gaps per test (12 cross-cutting gaps total)
  - Documented strengths (comprehensive testing philosophy, well-documented environment flags)
  - Mapped findings to exit criteria alignment
- **Doc Refs Summary**: `plans/active/PARITY-HARNESS-001/reports/2025-10-29T000004Z/doc_refs.json`
  - Extracted reusable metrics from TORCH-BRIDGE-001 (masked_mse, shape validation, mask coverage)
  - Extracted test execution patterns from TORCH-CLI-003 (runtime metadata, pass/fail structure)
  - Proposed standardized metrics.json schema (required: correlation, mse, rmse, max_abs_diff, sum_ratio, etc.)
  - Proposed trace log structure per spec-db-tracing.md requirements
  - Proposed parity/ subdirectory convention
  - Environment flags summary consolidated from TESTING_GUIDE and testing_strategy
  - Identified 5 gaps requiring new tooling (correlation computation, trace capture, diff heatmap generation, golden data loader, metrics writer)
  - Documented 6 recommendations for Phase B harness blueprint
- **Test Collection Logs**:
  - `pytest_collect_DB_AT_001.log` — 0 tests collected (expected, selector planned)
  - `pytest_collect_DB_AT_002.log` — 0 tests collected (expected, selector planned)

### Notes & Risks
- Golden datasets (`nanoBragg2/tests/golden_data/`) may be missing locally; document mitigations if unavailable.
- **Mitigation (A3)**: Artifact strategy documented in doc_refs.json includes fallback to DBEX-local golden mirror if nanoBragg2 path inaccessible.

## Phase B — Harness Blueprint
### Checklist
- [x] B1: Draft `docs/parity_harness_spec.md` (or equivalent) detailing inputs, commands, and evaluation metrics for DB-AT-001/002, citing spec shards.
  - Completed: `docs/parity_harness_spec.md` authored with 8 sections covering DB-AT-001 (§2) and DB-AT-002 (§3)
  - Includes: Golden data requirements, configuration parity, environment flags, metrics computation, trace capture workflow, artifact layout, pass/fail criteria
  - Citations: spec-db-conformance.md, testing_strategy.md, spec-db-tracing.md, TESTING_GUIDE.md, c_to_pytorch_config_map.md
- [x] B2: Encode phased harness rollout tasks in this implementation plan (update checklist statuses, add sub-items if needed).
  - Completed: Phase B checklist updated with deliverables and artifact references
  - Next: Phase C cross-doc sync tasks remain (C1-C3)
- [x] B3: Prepare metrics/trace capture template (e.g., `metrics.json` schema) and reference it within the harness spec.
  - Completed: Metrics JSON schema defined in `docs/parity_harness_spec.md` §4.3 with required and optional fields
  - Completed: Trace naming convention and content requirements in §2.6
  - Completed: Artifact directory structure in §4.1
  - Completed: Python helper function `compute_parity_metrics()` in §2.5 (reference implementation)

### Status
**Phase B Complete** (2025-10-29T001027Z)

### Deliverables
- **Parity Harness Spec**: `docs/parity_harness_spec.md`
  - 8 normative sections defining DB-AT-001/002 harness requirements
  - Metrics JSON schema (§4.3) with required core metrics (correlation, MSE, RMSE, max_abs_diff, sum_ratio) and optional extended metrics
  - Trace capture workflow (§2.6) with 20+ required trace checkpoints per testing_strategy.md §117
  - Artifact layout (§4.1) with parity/ and determinism/ subdirectories
  - Environment configuration (§2.4, §3.2) synchronized with TESTING_GUIDE.md §1
  - Pass/fail criteria (§2.8, §3.7) aligned with spec-db-conformance.md thresholds
  - Tooling gaps documented (§6.1) for Phase C implementation
  - Cross-document synchronization checklist (§5.2)
- **Implementation Plan Update**: This file, Phase B section updated with completion status

### Notes & Risks
- Ensure diagnostics align with tracing requirements (`docs/spec-db-tracing.md:15-60`) to avoid divergent workflows. ✓ Addressed in parity_harness_spec.md §2.6
- Golden data accessibility unverified; mitigation options documented in §6.2 (verify path, create DBEX-local mirror, or document generation procedure)
- Helper utilities (correlation computation, trace capture, diff heatmap, golden loader, metrics writer) identified as Phase C sub-tasks (§6.1)

## Phase C — Cross-Doc Sync
### Checklist
- [ ] C1: Update `docs/TESTING_GUIDE.md` §2 and `docs/development/TEST_SUITE_INDEX.md` entries for DB-AT-001/002 with finalized harness details and selectors.
- [ ] C2: Add harness references to `docs/index.md` and `docs/prompt_sources_map.json`; confirm prompt discoverability.
- [ ] C3: Capture final evidence report (`summary.md`, `doc_diffs.log`) under `plans/active/PARITY-HARNESS-001/reports/<timestamp>/` and update `docs/fix_plan.md` Attempts History with Metrics/Artifacts lines.

### Notes & Risks
- Keep documentation updates synchronized to avoid conflicting instructions across prompts.

## Artifacts Index
- Reports root: `plans/active/PARITY-HARNESS-001/reports/`
- Latest run: Pending (`<YYYY-MM-DDTHHMMSSZ>/`)
