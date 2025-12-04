Summary: Promote the smoke calibration capture probe into `dbex.calibration`/`dbex.tools` so DiffBragg metadata bundles are emitted by owner modules with canonical CLIs.
Mode: none
ActionType: implementation_ready
DecisionStatus: localized
InitiativeType: architecture
Focus: ARCH-PROBE-FREEZE-001 — Probe Freeze & Logging Consolidation
Branch: integration
Mapped tests:
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE libtbx.python -m dbex.tools.capture_smoke_calibration --expt sp.proc/idx-0000_sigma_metadata.expt --refl refGeom.refl --mask 747_mask.pkl --mtz scaled.mtz --out-config plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-30T150000Z/capture_full/config_torch_smoke.json --refined-mtz-out plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-30T150000Z/capture_full/smoke_refined_structure_factors.mtz --manifest plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-30T150000Z/capture_full/smoke_calibration_manifest.json --num-macro 3 | tee plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-30T150000Z/capture_full/capture_full.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE libtbx.python -m dbex.tools.capture_smoke_calibration --expt sp.proc/refGeom_small/refGeom_small.expt --refl sp.proc/refGeom_small/refGeom_small.refl --mask sp.proc/refGeom_small/refGeom_small_mask.pkl --mtz scaled.mtz --out-config plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-30T150000Z/capture_small/config_torch_smoke_small.json --refined-mtz-out plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-30T150000Z/capture_small/smoke_refined_structure_factors_small.mtz --manifest plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-30T150000Z/capture_small/smoke_calibration_small_manifest.json --num-macro 3 | tee plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-30T150000Z/capture_small/capture_small.log
  - AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md PYTEST_ADDOPTS='' pytest --collect-only tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" > plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-30T150000Z/collect_db_at_028_029.log
Artifacts: plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-30T150000Z/
Findings Applied (Mandatory):
  - STAGEA-001 — Calibration provenance must flow through owner modules; replacing the plan script keeps Stage A telemetry authoritative.
  - SCALE-004 — HKL/calibration precedence lives in production helpers; canonical capture tooling enforces this contract.
Pointers:
  - plans/active/ARCH-PROBE-FREEZE-001/implementation.md:Phase B — B6 checklist and guardrails for the capture migration.
  - plans/active/TOOLING-VIS-001/bin/capture_smoke_calibration.py:1-360 — Existing 330+ LOC shadow pipeline that must become a shim.
  - docs/data_dependency_manifest.md:40-110 — Canonical smoke calibration bundle requirements and existing generation commands to update.
ARCH Contracts (mandatory):
  - Diagnostic Script Policy (prompts/supervisor.md:272-309) — Owner: `dbex.tools.capture_smoke_calibration`; failure type: architecture conformance violation (shadow pipeline outside owner APIs).
  - Calibration/Data Dependency Manifest (docs/data_dependency_manifest.md:40-140) — Owner: `dbex.calibration.*`; failure type: implementation bug (canonical generation commands drifted into plan scripts).
  - Calibration & Scaling Architecture (docs/architecture/calibration_scaling.md:1-160) — Owner: `dbex.calibration`; failure type: architecture conformance (calibration bundle emission must live in the calibration layer).
Do Now (hard validity contract)
1. Implement: `dbex/calibration/smoke_capture.py` — lift the capture logic out of the plan script into reusable helpers (DataLoad ingestion, hopper macro-cycles, manifest writer) with docstrings referencing docs/data_dependency_manifest.md. Ensure helpers accept explicit paths/kwargs so callers can control output directories without touching repo-tracked configs.
2. Implement: `dbex/tools/capture_smoke_calibration.py::main` — expose the existing CLI surface (`--expt/--refl/--mask/--mtz/--out-config/--refined-mtz-out/--manifest/--num-macro`) and call the new helpers. Add a README entry under `dbex/tools/README.md` summarizing usage + sample command (`libtbx.python -m dbex.tools.capture_smoke_calibration ...`).
3. Implement: `plans/active/TOOLING-VIS-001/bin/capture_smoke_calibration.py` — reduce to a compatibility shim (`from dbex.tools import capture_smoke_calibration as tool; tool.main()`) with a docstring pointing at the canonical owner CLI. No residual business logic may remain.
4. Implement: Documentation updates — refresh `docs/data_dependency_manifest.md` generation commands to reference `python -m dbex.tools.capture_smoke_calibration`, update any TOOLING-VIS-001 plan notes referencing the legacy script, and ensure new helper modules/docstrings cite diagnostic_script_policy.
5. Implement: Validation + artifacts — run the two mapped capture commands (full + small datasets) directing outputs into `capture_full/` and `capture_small/` under this loop’s report directory. Each run must leave behind config JSON, refined MTZ (if requested), manifest JSON, SHA256 notes, and the tee’d log showing macro cycles completed. Append the pytest collect-only log for DB-AT-028/029 to the root artifacts directory.
Forbidden This Loop:
  - no new plan-local probe scripts or telemetry forks; all capture logic must live under `dbex.calibration`/`dbex.tools`.
  - do not overwrite the tracked `sp.proc/calibration/config_torch_smoke*.json` or `smoke_refined_structure_factors*.mtz`; validation outputs belong under the artifacts directory only.
How-To Map:
  1. Author the new helper + CLI modules and run `python -m compileall dbex/calibration` if needed to catch import errors.
  2. Replace the plan script with a shim, then update docs (Data Dependency Manifest + any README/plan notes) to point at the new CLI.
  3. Create `capture_full/` and `capture_small/` under the artifacts path, run the mapped commands, and ensure manifests/logs/configs reside there. Finally, run the pytest collect-only guard and store the output per above.
Pitfalls To Avoid:
  - Do not leave residual DiffBragg logic inside `plans/active/**/bin`; the shim must only call the owner CLI.
  - Avoid hard-coding repo-relative paths inside the helper; accept explicit `Path` args so future initiatives can re-use it.
  - Keep manifests self-consistent (generator command, file SHA256, manifest SHA256) to satisfy docs/data_dependency_manifest.md requirements.
  - Ensure logging matches previous behavior (INFO-level banner + macro-cycle messages) so existing automation can parse the output.
  - Do not clobber existing calibration bundles in `sp.proc/calibration/`; store validation outputs under this loop’s report tree.
  - Preserve libtbx imports (phil_scope/hopper_utils) and validate they work under the standard interpreter invoked by the CLI.
  - Capture command output via `tee` so artifact directories contain the full log even if the run fails mid-cycle.
  - Update `dbex/tools/__init__.py` if needed to expose the new CLI for discoverability.
If Blocked:
  - Document the blocker in `plans/active/ARCH-PROBE-FREEZE-001/reports/2025-12-30T150000Z/blockers.md`, update docs/fix_plan.md Attempts History with the evidence, and ping Galph. If DiffBragg capture crashes, attach the log + traceback and stop before editing the environment.
Doc Sync Plan (Conditional): Not required — no pytest selectors added or renamed.
