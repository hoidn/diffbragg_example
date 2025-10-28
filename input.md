Summary: Restore the PyTorch runtime checklist doc and align all references so runtime guardrails are discoverable.
Mode: Docs
Focus: DOC-RUNTIME-004 — Restore docs/pytorch_runtime_checklist.md
Branch: integration
Mapped tests: none — evidence-only
Artifacts: plans/active/DOC-RUNTIME-004/reports/2025-10-28T233723Z/{notes.md,checklist_head.log,summary.md}
Do Now:
  1. DOC-RUNTIME-004 — A1 (plans/active/DOC-RUNTIME-004/implementation.md) — tests: none; run `rg 'pytorch_runtime_checklist' -n` and catalog every reference plus the missing symlink target in notes.md alongside key guardrails from docs/spec-db-runtime.md:10-20 and docs/spec-db-conformance.md:10-48.
  2. DOC-RUNTIME-004 — A2 (plans/active/DOC-RUNTIME-004/implementation.md) — tests: none; replace the broken symlink with a restored docs/pytorch_runtime_checklist.md that captures environment flags, runtime guardrails, acceptance hooks, and cites the spec shards gathered in A1.
  3. DOC-RUNTIME-004 — B1 (plans/active/DOC-RUNTIME-004/implementation.md) — tests: none; update docs/index.md and docs/development/testing_strategy.md:27 to reference the restored checklist path/title and ensure narrative alignment.
  4. DOC-RUNTIME-004 — B2 (plans/active/DOC-RUNTIME-004/implementation.md) — tests: none; synchronize docs/prompt_sources_map.json and any prompt files that cite the old symlink so they resolve to the new checklist.
  5. DOC-RUNTIME-004 — C1 (plans/active/DOC-RUNTIME-004/implementation.md) — tests: none; capture `head -n 40 docs/pytorch_runtime_checklist.md` into checklist_head.log under the artifact path and verify the Markdown renders key sections.
  6. DOC-RUNTIME-004 — C2 (plans/active/DOC-RUNTIME-004/implementation.md) — tests: none; summarize restoration steps, remaining gaps, and validation evidence in summary.md and record Metrics/Artifacts lines in docs/fix_plan.md.
Priorities & Rationale:
  - Uphold runtime guardrails defined in docs/spec-db-runtime.md:10-20 so engineers retain canonical guidance when the checklist is restored.
  - Maintain acceptance-test readiness per docs/spec-db-conformance.md:10-48 by documenting the DB-AT hooks inside the checklist.
  - Resolve the knowledge-base dependency highlighted in docs/findings.md (RUNTIME-001, CONFORMANCE-001) so cited references remain valid.
  - Keep documentation maps accurate by aligning docs/index.md:142-150 and docs/prompt_sources_map.json:1-49 with the restored file.
  - Ensure prompts and workflow guides (prompts/main.md:12-73) continue to reference a live checklist without manual path fixes later.
How-To Map:
  - export ART=plans/active/DOC-RUNTIME-004/reports/2025-10-28T233723Z; mkdir -p "$ART"; touch "$ART/notes.md" "$ART/summary.md"
  - rg 'pytorch_runtime_checklist' -n > "$ART/notes.md"; append spec guardrail excerpts via `nl -ba docs/spec-db-runtime.md | sed -n '10,40p'`
  - Restore docs/pytorch_runtime_checklist.md using apply_patch or cat > file <<'EOF' (ensure ASCII) and cite spec shard anchors.
  - Update docs/index.md, docs/development/testing_strategy.md, docs/prompt_sources_map.json, and prompts/* as needed; note edits in "$ART/notes.md".
  - head -n 40 docs/pytorch_runtime_checklist.md | tee "$ART/checklist_head.log"; record command + results in summary.md.
Pitfalls To Avoid:
  - Do not recreate the broken symlink; ensure the checklist is a repo-local file.
  - Preserve spec citations exactly (e.g., docs/spec-db-runtime.md:10 for guardrails).
  - Keep prompt edits minimal—only adjust paths referencing the checklist.
  - Avoid altering external nanoBragg2 references that remain valid in historical docs.
  - Retain Metrics/Artifacts placeholders when updating docs/fix_plan.md.
  - Confirm docs/index.md anchors stay in sync with headings to prevent stale links.
  - Ensure artifact directory only stores lightweight text outputs (notes/logs).
  - Maintain ASCII encoding throughout the restored doc.
  - Verify no lingering references still point to docs/development/pytorch_runtime_checklist.md.
If Blocked: If source material for the checklist cannot be reconstructed, note the gap in docs/fix_plan.md Attempts History (Metrics: pending; Artifacts: pending) and capture the missing upstream dependency in summary.md before returning to planning.
Findings Applied (Mandatory): RUNTIME-001 — plan reasserts NANOBRAGG_DISABLE_COMPILE guard via restored checklist guidance; CONFORMANCE-001 — plan preserves KMP_DUPLICATE_LIB_OK and DB-AT selector documentation within the checklist.
