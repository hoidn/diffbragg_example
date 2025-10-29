Summary: Document the diffBragg forward failure and re-scope NANOBRAG-GOLDEN-001 under the Environment Freeze constraints.
Mode: Docs
Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
Branch: integration
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001; KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001
Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T070359Z/{blocking_summary.md,torch_gap_notes.md,logs/diffbragg_forward_excerpt.log,collect_db_at_001_parity.log,collect_db_at_001_forward.log}
Do Now:
  1. NANOBRAG-GOLDEN-001::A2 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Extract the diffBragg forward failure details from 2025-10-29T063817Z/golden_dataset/logs/canonical_capture.log, copy the critical lines into the new report directory, and summarize why baseline export remains blocked (GPU assert, lack of full-panel output). tests: none.
  2. NANOBRAG-GOLDEN-001::A3 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Audit torch-side artifacts and fixture manifests to confirm the canonical dataset gap, capturing the findings in torch_gap_notes.md with manifest hashes and plan re-scope notes. tests: none.
  3. NANOBRAG-GOLDEN-001::B2 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Re-run collect-only for DB_AT_001 parity and forward selectors, archiving fresh logs under the new report to keep TESTING_GUIDE.md alignment. tests: KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001; KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001.
  4. NANOBRAG-GOLDEN-001::D3 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Update docs/fix_plan.md Attempts History and status to `blocked`, reference the new artifacts, and log the reality-check outcome plus return condition. tests: none.
Priorities & Rationale:
- docs/forward_equivalence.md:21-33 — Exit criteria require paired DiffBragg/torch artifacts, so the plan must document why the DiffBragg half is blocked.
- docs/spec-db-core.md:20-33 — Canonical tensors must be `[panel, slow, fast]`; the blocker prevents producing these arrays, informing the summary.
- docs/spec-db-conformance.md:23-26 — DB_AT_001 acceptance thresholds justify keeping parity selectors documented with current evidence during the block.
- docs/findings.md:15 — DIFFBRAGG-001 mandates treating the diffBraggCUDA.cu:708 assert as a hard blocker without environment changes.
- docs/TESTING_GUIDE.md:85-86 — Collect-only evidence for DB_AT_001 must stay current when adjusting ledger status.
How-To Map:
- `mkdir -p plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T070359Z/logs`
- `tail -n 150 plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T063817Z/golden_dataset/logs/canonical_capture.log > plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T070359Z/logs/diffbragg_forward_excerpt.log`
- `cp plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T063817Z/golden_dataset/logs/diffbragg_refine_one.log plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T070359Z/logs/roi_refine_one.log`
- `python - <<'PY' > plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T070359Z/torch_gap_notes.md`
`import json, pathlib, hashlib
manifest_path = pathlib.Path('tests/fixtures/golden_data/simple_cubic/manifest.json')
manifest = json.loads(manifest_path.read_text())
hashes = {name: data['sha256'] for name, data in manifest['files'].items()}
print('# Torch Dataset Gap Notes')
print(f"Manifest dataset_name: {manifest['dataset_name']}")
print('Hashes:')
for name, digest in hashes.items():
    print(f"- {name}: {digest}")
print('\nNo canonical torch outputs present under plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T063817Z/.')
PY`
- `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001 |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T070359Z/collect_db_at_001_parity.log`
- `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001 |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T070359Z/collect_db_at_001_forward.log`
- Use apply_patch to update plans/active/NANOBRAG-GOLDEN-001/implementation.md and docs/fix_plan.md with the blocked status and new Attempts History entry.
Pitfalls To Avoid:
- Do not rerun setup_env.sh or modify packages; Environment Freeze forbids env changes.
- Avoid editing fixtures under tests/fixtures/golden_data/ until canonical tensors exist.
- Keep prior report directories intact; new evidence must live under 2025-10-29T070359Z/.
- Capture the exact CUDA assert lines; do not summarize without log context.
- Ensure collect-only commands include KMP_DUPLICATE_LIB_OK=TRUE to match documented selectors.
- Leave Metrics/Artifacts placeholders in ledger entries populated before handoff.
- Do not mark A2/A3 complete—clearly label them blocked pending simtbx patch.
If Blocked: Archive the failed command output in the new report, append a `blocked` note with return condition to docs/fix_plan.md Attempts History, update galph_memory with `next_action=switch_focus`, and halt further work on NANOBRAG-GOLDEN-001 until external guidance arrives.
Findings Applied (Mandatory):
- DIFFBRAGG-001 — Treat diffBragg_forward runtime asserts as hard blockers and document evidence instead of patching simtbx.
- CONFORMANCE-001 — Maintain DB_AT_001 selector documentation and environment flags while the canonical dataset remains unavailable.
- TESTING-003 — Refresh collect-only logs before adjusting ledger status so docs stay authoritative.
- PARITY-001 — Preserve deterministic ROI ordering in logged artifacts to keep first-divergence tooling viable.
Doc Sync Plan (Mandatory):
- `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001 |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T070359Z/collect_db_at_001_parity.log`
- `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001 |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T070359Z/collect_db_at_001_forward.log`
- Update docs/TESTING_GUIDE.md §2 and docs/development/TEST_SUITE_INDEX.md references to point at the 2025-10-29T070359Z collect-only logs once captured, retaining selector status.
