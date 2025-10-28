# Implementation Plan — TORCH-CLI-003

ID: TORCH-CLI-003
Title: Wire torch backend flag into CLI
Owner: Unassigned
Status: pending

## Goals
- Introduce a backend flag in `dbex.refine_one` to select between DiffBragg and `nanobrag_torch`.
- Maintain output compatibility and document usage.

## Phases Overview
- Phase A — CLI Flag & Wiring
- Phase B — Diagnostics & Docs

## Exit Criteria
1. `dbex.refine_one` accepts `--backend {diffbragg,nanobrag}` with default `diffbragg`.
2. Torch branch emits `Bragg` tensor and diagnostics matching legacy layout.
3. Update docs/index.md entry for CLI to reflect backend flag.
4. Entry validated by running torch CLI smoke.

## Phase A — CLI Flag & Wiring
### Checklist
- [ ] A1: Add `--backend` option and plumb to execution path
- [ ] A2: Wire torch path to `nanobrag_bridge` and model run (guarded behind flag)

## Phase B — Diagnostics & Docs
### Checklist
- [ ] B1: Log minimal diagnostics for torch path; update CLI help
- [ ] B2: Update docs/index.md entry and confirm smoke selector

## Artifacts Index
- Reports root: `plans/active/TORCH-CLI-003/reports/`
