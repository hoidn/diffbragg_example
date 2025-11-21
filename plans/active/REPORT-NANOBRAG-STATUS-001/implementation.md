# REPORT-NANOBRAG-STATUS-001 — Nanobrag Progress Reporting Pack

## Purpose
Package current nanobrag-based refinement telemetry (loss traces, parameter deltas) and representative ROI visuals into a meeting-ready progress pack for the collaboration group.

Scope: reporting only. No runtime/toolchain changes and no external installs. Operate on existing HDF5 outputs, tests, and artifacts already present in the workspace per Environment Freeze.

## Inputs
- Recent HDF5 outputs from `dbex.refine_one --backend nanobrag` runs, including `/torch_diagnostics` group and ROI datasets (`data/roi*`, `model/roi*`, `bragg/roi*`, `bg/roi*`).
- Existing test artifacts that capture parity/progress metrics (if any).
- Repository metadata: plan status, implemented features vs. `plans/nanobrag_integration_plan.md`.

## Deliverables
- `reports/nanobrag_validation.md` — concise summary with links to generated artifacts and a plan-vs-status checklist (Phase 0–5 and Stage A/B/C).
- JSON summaries (and optional figures) under `plans/active/REPORT-NANOBRAG-STATUS-001/reports/<YYYY-MM-DDTHHMMSSZ>/` capturing:
  - Stage telemetry: `loss_trace_sample`, `loss_trace_full`, `best_loss_full`, `param_deltas`, optimizer config, `hkl_source` provenance.
  - ROI snapshot manifest for selected panels/indices (triptych references).
  - Plan vs. implementation status matrix.
 - When describing perf behavior or ROI sampling in the report, reuse the existing PERF-WARM-SIM-001 telemetry contract (`roi_count_*`, `cache_mode`, `roi_mode`, `forward_time_ms`) and Stage A ROI semantics where available. If additional metrics are needed, evolve that contract within PERF-WARM-SIM-001 (or a successor perf initiative) and then consume the new fields here, rather than inventing a reporting-specific perf schema.

Note: If plotting libraries are unavailable, emit JSON + markdown tables only, and record the missing import as a blocker in `docs/fix_plan.md` Attempts History.

## Exit Criteria
1) One self‑contained `reports/nanobrag_validation.md` summary checked into the repo.
2) ≥1 recent HDF5 run parsed; loss traces and parameter-delta tables included (Stage A mandatory; B/C if enabled).
3) At least one figures/tables section showing Stage A progress (and B/C if present). If figures cannot be generated in the frozen environment, include tables and note the limitation.
4) Plan‑vs‑status checklist presented, mapping `plans/nanobrag_integration_plan.md` milestones to current implementation.

## Tasks (no code changes)
- Inventory candidate HDF5 outputs (torch backend) and select the most recent viable file.
- Parse `/torch_diagnostics` to extract optimizer/telemetry fields; compute any derived metrics needed for the summary.
- Select representative ROIs (e.g., top/bottom quartile by score or deterministic sample) and reference their datasets for visualization or tabular summaries.
- Generate `reports/nanobrag_validation.md`:
  - Overview: scope, environment constraints.
  - Status matrix: Phase 0–5 and Stage A/B/C (done/partial/deferred) with file pointers.
  - Telemetry snapshots: loss traces (sample/full), parameter deltas; HKL source provenance (refined vs raw MTZ).
  - ROI snapshot section: path references to ROI datasets; residual statistics.
  - Open gaps/risks and next steps.
- Emit JSON summaries under `plans/active/REPORT-NANOBRAG-STATUS-001/reports/<timestamp>/` for reproducibility; link them from the report.

## Operational Constraints
- Environment Freeze: do not install/upgrade packages or fetch external dependencies. If optional plotting libraries are missing, fall back to JSON/tables and record the limitation in `docs/fix_plan.md`.
- Read‑only interaction with existing outputs; do not modify simulator code or rerun pipelines unless explicitly green‑lit in a separate initiative.

## Artifacts Structure
```
plans/active/REPORT-NANOBRAG-STATUS-001/
  implementation.md
  reports/
    <YYYY-MM-DDTHHMMSSZ>/
      telemetry_summary.json
      roi_manifest.json
      (optional) loss_traces.png
      (optional) param_deltas.png
reports/
  nanobrag_validation.md
```

## Relationship to Integration Plan
This plan delivers the “Validation & Documentation” reporting artifact referenced by `plans/nanobrag_integration_plan.md` (Phase 5). The integration plan remains unchanged; this plan provides the reporting track to present current progress without altering runtime code.
