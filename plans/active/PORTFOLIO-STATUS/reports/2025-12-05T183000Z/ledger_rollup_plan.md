# Ledger Roll-up Coverage Plan — 2025-12-05T183000Z

## Scope
- Phase B3 of PORTFOLIO-STATUS: add durable fix-plan coverage for the 34 active plan directories highlighted in the 2025-12-05T150000Z classification report.
- Produce repeatable roll-up definitions so `docs/fix_plan.md` can reference grouped initiatives instead of seven separate plan bullets per suite.
- Back the doc work with an updated `plan_inventory.py` helper so future drift checks output the same groupings without manual grep.

## Roll-up Targets and Required Content
| Roll-up ID | Member Plans | Initiative Type | Spec / Doc References | Exit Criteria Notes |
| --- | --- | --- | --- | --- |
| `DB-AT-SUITE-CARE-001` | DB-AT-002, DB-AT-010, DB-AT-020, DB-AT-021, DB-AT-022, DB-AT-023, DB-AT-024 | harness | `docs/spec-db-conformance.md` §§DB-AT-002–029 | Ledger section must cite each selector, surface latest artifact timestamps, and encode acceptance criteria (median ROI correlation ≥0.2, chi²/pixel ≤1e2, determinism gates). |
| `MAP-SCALE-SYNC-001` | MAP-SCALE-001…005 | spec_change (calibration ladder) | `docs/spec-db-workflow.md` "Calibration & Unit Conventions", `docs/config_crosswalk.md` | Document calibration precedence per plan, note dependency on sigma provenance work, and add exit criteria for spot-scale alignment plus telemetry provenance. |
| `PHYSICS-LOSS-001` | PHYSICS-LOSS-001 | bugfix | `docs/spec-db-core.md` §Objective Function, `docs/TESTING_GUIDE.md` §1.4 | Promote existing implementation.md content into fix-plan entry (goals, completed phases, remaining risks). |
| `TORCH-GEOMETRY-SYNC-001` | TORCH-GEOMETRY-CONVERGENCE-001, TORCH-GEOMETRY-PARITY-002/003, TORCH-GEOMETRY-UB-REALIGN-001 | architecture | `docs/spec-db-core.md` §Baseline Crystal State, `docs/spec-db-workflow.md` §Stage A | Capture zero-point invariants, dependencies on ARCH-REFINE-001, and planned probes for UB realignment.
| `TORCH-REFINE-CLEANUP-001` | TORCH-REFINE-001/002/002D/002E/003 | architecture/perf | `docs/spec-db-workflow.md` §Stage B/C, `docs/spec-db-runtime.md` §Vectorization | Track outstanding Stage A/B/C telemetry cleanups, note Stage B ASU gradient issues, and define gating selectors.
| `TORCH-CLI-BRIDGE-ROLLUP-001` | TORCH-BRIDGE-001, TORCH-CLI-003, TORCH-CLI-004 | architecture + harness | `docs/spec-db-interfaces.md`, `docs/config_crosswalk.md`, `docs/architecture.md` | Ledger entry must anchor CLI backend flag, telemetry schema work, and bridge responsibility split, with clear dependency on REPORT-NANOBRAG-STATUS-001 output schema.
| `FORWARD-EQUIV-COVERAGE-001` | FORWARD-EQUIV-001/002, PARITY-HARNESS-002 | diagnostics | `docs/forward_equivalence.md`, `docs/spec-db-conformance.md` DB-AT-001 | Capture parity thresholds (median ROI corr ≥0.2, localization ≥90%), trace artifact requirements, and ties to NANOBRAG-GOLDEN-001 dataset refreshes.
| `TOOLING-VIS-001` | TOOLING-VIS-001 | diagnostics | `docs/spec-db-vis.md` | Add goals around canonical triptychs/residual plots and specific acceptance metrics (z-score histograms within ±3σ, radial profile overlays).
| `DOCS-ROADMAP-001` | DOCS-ROADMAP-001 | docs | `docs/index.md`, `docs/development/testing_strategy.md` | Ensure ledger states publication cadence, dependencies on portfolio archive moves, and exit criteria for roadmap freshness.
| `RUNTIME-VEC-001` | RUNTIME-VEC-001 | perf | `docs/pytorch_runtime_checklist.md`, `docs/spec-db-runtime.md` | Reference required smoke selectors (vectorization tests), dyno guardrails, and environment flags enforced by TESTING_GUIDE.
| `REPORT-NANOBRAG-STATUS-001` | REPORT-NANOBRAG-STATUS-001 | tooling | `docs/TESTING_GUIDE.md`, `docs/development/testing_strategy.md` | Capture scope for reporting scripts (status dashboards, parity metrics) and ensure exit criteria reference CLI artifacts and scriptization policy.
| `NANOBRAG-GOLDEN-001` | NANOBRAG-GOLDEN-001 | harness | `docs/development/testing_strategy.md` §2.5, `docs/prompt_sources_map.json` (spec sources) | Ledger entry must describe golden dataset refresh cadence, trace outputs (images + trace logs), and gating selectors that consume the dataset.
| `ARCH-SPLIT-001` | ARCH-SPLIT-001 | architecture | `docs/architecture.md`, `plans/active/ARCH-SPLIT-001/implementation.md` | Clarify whether initiative remains active or should be archived; exit criteria revolve around interface split ADR.

## Script Enhancements Required
1. **Roll-up config file support**
   - Accept `--rollup-config plans/active/PORTFOLIO-STATUS/rollups.json` describing mapping from roll-up IDs to member directories.
   - Emit `rollup_report.md` summarizing, for each roll-up, last report timestamps, missing implementation flags, and whether a fix-plan entry already exists.
2. **Bucket columns in JSON output**
   - Extend `inventory.json` entries with computed `bucket` (active_missing, archive_ready, missing_plan) to align with `classification.md` buckets.
3. **Unit tests**
   - Add a minimal pytest module under `plans/active/PORTFOLIO-STATUS/tests/test_plan_inventory.py` that seeds a temporary directory structure and asserts the new bucket + roll-up functionality.
   - Tests should run via `pytest -q plans/active/PORTFOLIO-STATUS/tests/test_plan_inventory.py` and be referenced in `input.md` to satisfy the validating-selector requirement.

## Fix-Plan Update Requirements
- For each roll-up, add a dedicated `### [ID]` section under “Active / Pending Initiatives” with:
  1. Dependencies (other initiatives + relevant spec docs).
  2. Initiative type & tier.
  3. Goals/Exit Criteria referencing the member plan directories and the spec clauses above.
  4. Working plan pointer (multiple directories acceptable when listed explicitly) and artifact path expectations.
  5. Attempts History bullet linking to `plans/active/PORTFOLIO-STATUS/reports/2025-12-05T150000Z/classification.md` plus the latest report under each member plan (e.g., DB-AT-022’s 2025-11-04T055500Z run).
- Update the Plan Directory Inventory appendix to cite this new roll-up classification artifact and note that the automation guard now depends on the roll-up config file.

## References
- `plans/active/PORTFOLIO-STATUS/reports/2025-12-05T150000Z/classification.md`
- `docs/spec-db-conformance.md`, `docs/spec-db-core.md`, `docs/spec-db-workflow.md`, `docs/spec-db-interfaces.md`, `docs/spec-db-vis.md`
- `docs/TESTING_GUIDE.md`, `docs/development/testing_strategy.md`, `docs/pytorch_runtime_checklist.md`
