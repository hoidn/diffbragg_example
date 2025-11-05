Summary: Capture a fresh nanobrag run and script the telemetry into a stakeholder-ready validation report.
Mode: Docs
Focus: REPORT-NANOBRAG-STATUS-001 — Nanobrag Progress Reporting Pack
Branch: integration
Mapped tests: tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata
Artifacts: plans/active/REPORT-NANOBRAG-STATUS-001/reports/2025-11-05T184233Z/

Do Now:
- REPORT-NANOBRAG-STATUS-001 — Nanobrag Progress Reporting Pack
  - Implement: plans/active/REPORT-NANOBRAG-STATUS-001/bin/emit_nanobrag_summary.py::main — parse the targeted nanobrag CLI HDF5 output to emit telemetry/ROI JSON and update reports/nanobrag_validation.md with the Phase 5 status tables and findings cross-references.
  - Validate: KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata --maxfail=1
  - Artifacts: plans/active/REPORT-NANOBRAG-STATUS-001/reports/2025-11-05T184233Z/

How-To Map:
- export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
- export REPORT_NANOBRAG_ARTIFACTS=plans/active/REPORT-NANOBRAG-STATUS-001/reports/2025-11-05T184233Z
- mkdir -p plans/active/REPORT-NANOBRAG-STATUS-001/bin "$REPORT_NANOBRAG_ARTIFACTS"
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python -m dbex.refine_one --backend nanobrag -e refGeom.expt -r refGeom.refl -i 0 -o "$REPORT_NANOBRAG_ARTIFACTS/nanobrag_stage_progress.h5" -m 747_mask.pkl -z scaled.mtz --mtzCol F,SIGF | tee "$REPORT_NANOBRAG_ARTIFACTS/refine_cli.log"
- python plans/active/REPORT-NANOBRAG-STATUS-001/bin/emit_nanobrag_summary.py --input "$REPORT_NANOBRAG_ARTIFACTS/nanobrag_stage_progress.h5" --out-dir "$REPORT_NANOBRAG_ARTIFACTS" --report-path reports/nanobrag_validation.md
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest --collect-only tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata | tee "$REPORT_NANOBRAG_ARTIFACTS/collect_cli_diag.log"
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -v tests/dbex/test_refine_one_cli.py::test_torch_diagnostics_metadata --maxfail=1 | tee "$REPORT_NANOBRAG_ARTIFACTS/pytest_cli_diag.log"

Pitfalls To Avoid:
- Honor the Environment Freeze: do not install packages; use only existing refGeom assets and torch runtime.
- Keep nanobrag CLI runs device/dtype neutral (KMP_DUPLICATE_LIB_OK=TRUE, NANOBRAGG_DISABLE_COMPILE=1) to avoid non-deterministic torch.compile side effects.
- Verify the generated HDF5 contains `/torch_diagnostics`; if absent, stop and log the failure rather than fabricating telemetry.
- Preserve SCALE-006 provenance by ensuring the CLI emits refined HKL telemetry (hkl_source must be `refined`); document any fallback per SCALE-007.
- Emit JSON/Markdown under the initiative reports directory only; do not pollute top-level repo folders with intermediate files.
- Capture pytest collection and run logs via `tee` into the artifacts directory to satisfy TESTING-003 documentation policy.

If Blocked:
- Record the failing command, error text, and HDF5 path in docs/fix_plan.md Attempts History, flag the initiative `blocked`, and log the blocker plus required follow-up in galph_memory.md before exiting.

Findings Applied (Mandatory):
- SCALE-006 — CLI runs must forward refined calibration metadata to the nanobrag bridge; confirm telemetry shows refined provenance.
- SCALE-007 — Document telemetry guardrails and assert refined HKL usage inside the summary.
- REFINE-002 — Report the ≥0.1 % Stage A improvement gate when presenting loss trace results.
- TESTING-003 — Archive collect-only and pytest logs alongside artifacts to keep documentation synchronized.

Pointers:
- plans/nanobrag_integration_plan.md:261 — Phase 5 validation/documentation deliverables reference for the report outline.
- docs/TESTING_GUIDE.md:90 — CLI telemetry selector coverage spelling out loss-trace and refined HKL expectations.
- docs/findings.md:22 — SCALE-006/SCALE-007 guardrails defining calibration + refined HKL telemetry requirements.
- docs/fix_plan.md:16 — Exit criteria explicitly requiring torch_diagnostics loss traces and parameter tables.

Next Up (optional):
- Add a follow-on CLI smoke that asserts the generated JSON summaries include Stage B/C placeholders once those stages ship.

Doc Sync Plan (Conditional):
- None — no new selectors added or renamed; reuse existing CLI telemetry test documentation.
