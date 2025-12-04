Summary: Catalog every plan-local probe script and classify thin wrappers vs shadow pipelines so Phase A of ARCH-PROBE-FREEZE-001 can hand off a decision-carrying inventory.
Mode: Docs
ActionType: planning
DecisionStatus: exploring
InitiativeType: architecture
Focus: ARCH-PROBE-FREEZE-001 — Probe Freeze & Logging Consolidation
Branch: integration
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --maxfail=1 --disable-warnings --collect-only tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells
Artifacts: plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-27T200000Z/
Findings Applied (Mandatory): No relevant findings — new architecture compliance loop
Pointers:
  - plans/active/ARCH-PROBE-FREEZE-001/implementation.md:1-54 — Phase A exit criteria require probe inventory artifacts (`probe_inventory.{md,json}`) plus classification.
  - prompts/supervisor.md:252-287 — Scriptization + diagnostic_script_policy define the thin-wrapper rule and growth caps; enforceable contract for plan-local scripts.
  - docs/architecture/data_telemetry_flow.md:1-35 — Owner modules for telemetry/logging; shadow pipelines must migrate back inside this flow.
ARCH Contracts (mandatory):
  - prompts/supervisor.md:252-287 — Owner: diagnostic_script_policy (supervisor). Failure: architecture conformance failure (plan scripts re-implement simulator/mapping semantics).
  - docs/architecture/data_telemetry_flow.md:1-35 — Owner: dbex.refinement.{inputs,stage_a} logging flow. Failure: architecture conformance failure (telemetry captured outside canonical pipeline).
Do Now (hard validity contract)
1. Implement: `plans/active/ARCH-PROBE-FREEZE-001/bin/collect_probe_inventory.py::main` — Write a thin-wrapper CLI that crawls `plans/active/**/bin` (py/sh) and emits JSON entries (`script_path`, `initiative_id`, `language`, `imports_torch`, `calls_owner_api`, `lines_of_code`). Keep it read-only (pathlib/os/json only) and write the stub to `plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-27T200000Z/probe_inventory_raw.json`.
2. Implement: `plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-27T200000Z/probe_inventory.md` (and `.json`) — Manually review each script, classify as `thin_wrapper`, `shadow_pipeline`, or `retire_candidate`, note the owner API (e.g., `dbex.refine_one`, `dbex/refinement/stage_a.py`, `nanobrag_torch.Simulator`), list decision-carrying outputs, and recommend the telemetry/logging hook that should replace it. The Markdown table must summarize per-initiative counts and highlight which scripts already exceed the diagnostic_script_policy growth caps; JSON should mirror the table with machine-readable fields so the future enforcement test can consume it. Update `plans/active/ARCH-PROBE-FREEZE-001/implementation.md` Phase A checklist to reflect completion.
Mapped Validation (pytest): `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --maxfail=1 --disable-warnings --collect-only tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells` (guard that architecture tests still import after adding the catalog tooling/documents).
Artifacts deliverables:
  - `plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-27T200000Z/probe_inventory.md`
  - `plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-27T200000Z/probe_inventory.json`
  - `plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-27T200000Z/probe_inventory_raw.json`
How-To Map:
  1. Run `python plans/active/ARCH-PROBE-FREEZE-001/bin/collect_probe_inventory.py --out plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-27T200000Z/probe_inventory_raw.json` to generate the starter list.
  2. For each entry, open the script, decide whether it only orchestrates owner APIs or re-implements physics, and capture notes (owner module, duplicated semantics) in a spreadsheet/notes doc before compiling the md/json artifacts.
  3. Summarize totals (per initiative + classification) at the top of the Markdown file; include a “Next logging hook” column mapping each shadow pipeline to the production module that must gain telemetry in Phase B.
  4. Update Phase A checkboxes in `plans/active/ARCH-PROBE-FREEZE-001/implementation.md`, then run the mapped pytest command.
Pitfalls To Avoid:
  - Do not extend any existing plan-local probe scripts (ARCH-PROBE-FREEZE guard stays in effect).
  - Keep the collector script thin; no simulator/mapping imports or physics code.
  - Do not delete or edit probes yet; this loop only catalogs them.
  - Ensure artifact filenames match ledger expectation (`probe_inventory.{md,json}`) or the supervisor loop will treat the exit criteria as unmet.
  - Record initiative ownership accurately; many scripts live under other plans with nested reports.
If Blocked:
  - If a script cannot be read (missing deps), log the path + error inside `probe_inventory.md`, add a `status="blocked"` entry in `probe_inventory.json`, and flag the blocker in docs/fix_plan.md / galph_memory before pausing the loop.
