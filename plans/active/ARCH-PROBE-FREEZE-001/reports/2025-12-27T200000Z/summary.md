### Turn Summary (Ralph — 2025-12-04T021600Z)

Cataloged 53 plan-local probe scripts across 20 initiatives with comprehensive classification (45 thin_wrappers, 7 shadow_pipelines, 1 retire_candidate). Identified 16 scripts exceeding 400 LOC growth cap per diagnostic_script_policy. Delivered probe_inventory.{md,json} artifacts with migration priorities for 7 shadow pipelines requiring owner API telemetry hooks in Phase B. Phase A exit criteria A1+A2 satisfied.

**Artifacts:** `plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-27T200000Z/{probe_inventory.md,probe_inventory.json,probe_inventory_raw.json}`

---

# ARCH-PROBE-FREEZE-001 — Phase A Scoping (2025-12-27T200000Z)

## Context
- Problems ledger entry “Freeze plan-local probe scripts…” remains unchecked, so this loop prioritizes ARCH-PROBE-FREEZE-001 per supervisor guardrails.
- docs/fix_plan.md §ARCH-PROBE-FREEZE-001 lists Phase A (catalog) as the next action; no inventory artifacts exist yet.
- `prompts/supervisor.md` (§10 diagnostic_script_policy) flags the thin-wrapper rule and growth caps; repeated Stage-A parity loops have already exceeded the probe budget.

## Evidence Collected
- Enumerated plan-local `bin/` directories: 19 initiatives host >50 runnable scripts; Stage-A/SCALE initiatives alone contribute 15 heavy probes that duplicate simulator + reconstruction semantics.
- Highest-risk scripts (shadow pipelines) based on content review: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py`, `probe_stage_a_scale_alignment.py`, `compare_simulator_outputs.py`, `plans/active/TOOLING-VIS-001/bin/compare_stage_a_mapping_parity.py`, and `plans/active/TORCH-REFINE-002E/bin/compare_mapping_vs_stage_a_forward.py` — all construct detectors/simulators directly and compute ROI stats outside production logging.
- Thin-wrapper exemplars that can remain once cataloged: `plans/active/PORTFOLIO-STATUS/bin/plan_inventory.py`, `plans/active/ARCH-REFINE-FLOW-001/bin/minimal_cpu_bragg_reproducer.py` (delegates to CLI), `plans/active/DB-AT-024/bin/compute_zero_iteration_metrics.py` (calls owner Stage-A helper). These illustrate the desired pattern.

## Plan for Ralph (Phase A1–A3)
1. **Collector tooling (A1)** — Author `plans/active/ARCH-PROBE-FREEZE-001/bin/collect_probe_inventory.py` that walks `plans/active/**/bin/*` and emits a base JSON stub capturing script path, owning initiative, shebang/language, and quick heuristics (imports torch?, touches stage impl?). Keep it thin (Pathlib/os only) so it stays a diagnostic wrapper, not a new probe.
2. **Manual classification (A2)** — Use the collector output plus light code reads to label each script as `thin_wrapper`, `shadow_pipeline`, or `retire_candidate`. Record owner APIs touched (e.g., `dbex.refine_one`, `nanobrag_torch.Simulator`), whether it mutates tensors, and notes about duplicated semantics. Store human-readable table + rollups in `plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-27T200000Z/probe_inventory.md` and machine-readable JSON in the same directory.
3. **Cross-references (A3)** — For every `shadow_pipeline` entry, capture: (a) which production module already owns the semantics (spec reference), (b) which initiative currently depends on the script, and (c) migration candidate for telemetry/logging. Add a short “Next hook” column tying each to Stage A / reconstruction / simulator logging gaps so Phase B (telemetry migration) has clear targets.

## Exit Signals for this Loop
- `collect_probe_inventory.py` exists with CLI usage documented in the report; scripts list stored as JSON stub.
- `probe_inventory.md` lists all 52 scripts with initiative grouping, classification, owner API, and migration notes; counts summarized at top (e.g., thin wrappers vs shadow pipelines).
- docs/fix_plan.md Attempts History updated with this scoping decision + artifact path; galph_memory + input refreshed accordingly.

## Next Supervisory Check
- Once Ralph delivers the inventory, verify that Phase A checklist items in implementation.md are checked, ensure ledger references match, and green-light Phase B telemetry migrations.
