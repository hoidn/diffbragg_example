# Implementation Plan — DOC-RUNTIME-004

ID: DOC-RUNTIME-004
Title: Restore docs/pytorch_runtime_checklist.md
Owner: Unassigned
Status: in_progress

## Goals
- Provide a self-contained PyTorch runtime checklist within the DBEX docs tree.
- Ensure all supervisor/engineer prompts and ledgers can resolve and cite the checklist without broken links.
- Capture validation artifacts demonstrating the restored checklist is discoverable and aligned with runtime specs.

## Phases Overview
- Phase A — Checklist Restoration
- Phase B — Reference Alignment
- Phase C — Validation & Artifact Capture

## Exit Criteria
1. `docs/pytorch_runtime_checklist.md` materially exists (not a broken symlink) and opens in the repo.
2. Content reflects runtime guardrails from `docs/spec-db-runtime.md` and acceptance selectors from `docs/spec-db-conformance.md`.
3. `docs/index.md`, `docs/prompt_sources_map.json`, and downstream prompts reference the restored file correctly.
4. Artifact report records validation commands/logs proving the checklist renders and references resolve.

## Phase A — Checklist Restoration
### Checklist
- [x] A1: Inventory existing references and gather source material (spec shards, prior notes) for the runtime checklist.
- [x] A2: Restore `docs/pytorch_runtime_checklist.md` with canonical sections (environment flags, runtime guardrails, acceptance hooks).

## Phase B — Reference Alignment
### Checklist
- [x] B1: Update `docs/index.md` and any inline references to reflect the restored checklist location/title.
- [x] B2: Synchronize `docs/prompt_sources_map.json` and prompts (if needed) to ensure the new file path resolves.

## Phase C — Validation & Artifact Capture
### Checklist
- [x] C1: Verify the checklist renders (e.g., `head -n 40 docs/pytorch_runtime_checklist.md`) and capture the command output under the reports directory.
- [x] C2: Document verification steps and resulting artifacts in `plans/active/DOC-RUNTIME-004/reports/<timestamp>/summary.md`.

## Artifacts Index
- Reports root: `plans/active/DOC-RUNTIME-004/reports/`
