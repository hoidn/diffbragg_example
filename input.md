Summary: Stage canonical DB_AT_001 DiffBragg and torch forward captures with fresh evidence for NANOBRAG-GOLDEN-001.
Mode: Parity
Focus: NANOBRAG-GOLDEN-001 — Replace fallback DB-AT-001 golden dataset
Branch: integration
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001; KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/dbex/test_db_at_001_parity.py -k DB_AT_001
Artifacts: plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T080253Z/{environment_status.md,golden_dataset/legacy/,golden_dataset/torch/,golden_dataset/logs/canonical_capture.log,metrics/metrics_summary.md,collect_db_at_001_forward.log,collect_db_at_001_parity.log}
Do Now:
  1. NANOBRAG-GOLDEN-001.A1 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Create the 2025-10-29T080253Z report skeleton and capture environment evidence (`which python`, `python -c "import nanobrag_torch, simtbx.diffBragg"` status, `md5sum` of `simtbx_diffBragg_ext.so`) into environment_status.md; tests: none — evidence-only.
  2. NANOBRAG-GOLDEN-001.A2+A3 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Copy canonical capture helpers into the new report directory and run `CUDA_VISIBLE_DEVICES=0 KMP_DUPLICATE_LIB_OK=TRUE libtbx.python capture_forward.py` to emit refreshed DiffBragg legacy tensors, torch `[panel, slow, fast]` stacks, and metrics; tests: none — evidence-only.
  3. NANOBRAG-GOLDEN-001.D1 (plans/active/NANOBRAG-GOLDEN-001/implementation.md) — Archive metrics/ROI summaries, refresh DB_AT_001 collect-only logs under 2025-10-29T080253Z, and prep doc/test updates for the new artifact paths; tests: KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001; KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001.
Priorities & Rationale:
- docs/forward_equivalence.md:21 — DiffBragg baseline capture is required before any torch parity comparison, anchoring Do Now step A2.
- docs/forward_equivalence.md:26 — Torch forward capture must hydrate configs from the bridge to pair with the DiffBragg baseline, motivating A3 execution.
- docs/spec-db-core.md:20 — Canonical tensors have to respect `[panel, slow, fast]` ordering and bbox semantics, informing output validation in A2/A3.
- docs/nanobrag_api.md:28 — Beam-center swapping and mask alignment rules guide simulator configuration during canonical capture.
- docs/spec-db-conformance.md:23 — DB_AT_001 acceptance demands artifact logging and threshold checks, driving the metrics archive and doc sync in D1.
- docs/TESTING_GUIDE.md:85 — Active selector entries must link to current collect-only logs, so D1 includes fresh DB_AT_001 evidence.
How-To Map:
- `mkdir -p plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T080253Z/{golden_dataset/legacy,golden_dataset/torch,golden_dataset/logs,metrics}`
- `python - <<'PY' > plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T080253Z/environment_status.md`
`from pathlib import Path`
`import hashlib, importlib, sys`
`env = {}`
`env["python"] = sys.executable`
`modules = {"nanobrag_torch": "nanobrag_torch", "simtbx.diffBragg": "simtbx.diffBragg"}`
`for label, modname in modules.items():`
`    mod = importlib.import_module(modname)`
`    env[label] = getattr(mod, "__file__", "built-in")`
`so_path = Path(env["simtbx.diffBragg"]).with_suffix(".so")`
`if so_path.exists():`
`    env["simtbx_diffBragg_ext.md5"] = hashlib.md5(so_path.read_bytes()).hexdigest()`
`for key, value in env.items():`
`    print(f"{key}: {value}")`
`PY`
- `cp plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T063817Z/capture_forward.py plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T080253Z/`
- `CUDA_VISIBLE_DEVICES=0 KMP_DUPLICATE_LIB_OK=TRUE libtbx.python plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T080253Z/capture_forward.py |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T080253Z/golden_dataset/logs/canonical_capture.log`
- `python - <<'PY' > plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T080253Z/metrics/metrics_summary.md`
`import json, pathlib`
`root = pathlib.Path("plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T080253Z")`
`metrics = json.loads((root/"golden_dataset"/"metrics.json").read_text())`
`summary = {`
`    "median_correlation": metrics.get("median_correlation"),`
`    "median_rmse": metrics.get("median_rmse"),`
`    "localization_success_rate": metrics.get("localization_success_rate"),`
`    "loss_mask_coverage": metrics.get("loss_mask_coverage"),`
`    "n_panels": metrics.get("n_panels"),`
`}`
`for key, value in summary.items():`
`    print(f"{key}: {value}")`
`PY`
- `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001 |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T080253Z/collect_db_at_001_forward.log`
- `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001 |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T080253Z/collect_db_at_001_parity.log`
- Update `docs/TESTING_GUIDE.md` §2.1 and `docs/development/TEST_SUITE_INDEX.md` with the 2025-10-29T080253Z log paths and metrics references once evidence is captured.
Pitfalls To Avoid:
- Do not reuse artifacts from prior timestamps; ensure every output lives under 2025-10-29T080253Z.
- Keep CUDA device pinned to GPU 0 and avoid simultaneous runs that could reintroduce diffBragg cleanup issues noted in DIFFBRAGG-001.
- Preserve `[panel, slow, fast]` ordering when validating outputs to avoid silent regressions against spec-db-core.md:20.
- Monitor loss mask dtype conversions; enforce boolean masks before computing metrics to honour CONFIG-001.
- Capture full stdout/stderr for canonical capture; missing logs block doc sync requirements.
- Do not modify the frozen environment; treat import failures as blockers per policy.
- Confirm `_temp.mtz` cleanup occurs to avoid stale structure-factor grids contaminating reruns.
- Ensure ROI ordering matches refGeom indices to maintain deterministic parity traces per PARITY-001.
- Verify torch device memory frees between panels if capture_forward.py is edited; OOM kills the loop.
- Avoid running unrelated pytest selectors; focus on the mapped DB_AT_001 evidence only.
Environment: Frozen simtbx environment; no package installs, rebuilds, or CUDA driver changes allowed. Missing imports must be logged as blockers instead of patched in-loop.
If Blocked: Archive failure logs under 2025-10-29T080253Z/golden_dataset/logs/, append a `blocked` attempt in docs/fix_plan.md noting the error signature, update galph_memory next_action to `switch_focus`, and notify supervisor that NANOBRAG-GOLDEN-001 remains blocked pending the recorded issue.
Findings Applied (Mandatory):
- CONFIG-001 — Enforces dxtbx→torch mapping rules (beam center swap, mask polarity) during canonical capture.
- PARITY-001 — Maintains deterministic ROI ordering and traceability for parity diagnostics.
- DIFFBRAGG-001 — Verifies the patched CUDA cleanup path before trusting DiffBragg outputs.
- TESTING-003 — Requires fresh collect-only logs and doc sync for Active selectors.
Doc Sync Plan (Mandatory):
- Forward equivalence (DB_AT_001) — `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_forward_equivalence_complete.py -k DB_AT_001 |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T080253Z/collect_db_at_001_forward.log` (update docs/TESTING_GUIDE.md §2.1 and docs/development/TEST_SUITE_INDEX.md Implementation Coverage).
- Parity harness (DB_AT_001) — `KMP_DUPLICATE_LIB_OK=TRUE pytest --collect-only -q tests/dbex/test_db_at_001_parity.py -k DB_AT_001 |& tee plans/active/NANOBRAG-GOLDEN-001/reports/2025-10-29T080253Z/collect_db_at_001_parity.log` (refresh docs/TESTING_GUIDE.md §2.1 and docs/development/TEST_SUITE_INDEX.md DB-AT table).
