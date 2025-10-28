plans/nanobrag_integration_plan.md:25: - Run the bundled CPU and CUDA smoke tests (`nanoBragg2/docs/development/pytorch_runtime_checklist.md`) to confirm the simulator works on the target hardware (note: lives under the nanoBragg2 docs tree; may appear as a symlink depending on checkout).
docs/architecture/pytorch_design.md:89:**Normative Reference:** See `docs/pytorch_runtime_checklist.md` (Source Handling & Equal Weighting) for canonical source weighting rules; CLI `-lambda` is authoritative and equal weighting applies via division by source count.
docs/fix_plan.md:46:  * 2025-10-28T232744Z — Completed A1-A2-B1-B2 doc updates: enhanced TESTING_GUIDE.md §1 with structured environment flag guidance (KMP_DUPLICATE_LIB_OK, NANOBRAGG_DISABLE_COMPILE); added runtime pitfalls to testing_strategy.md §1.6; synchronized 8 DB-AT selectors (001, 002, 020-024, vectorization) between TESTING_GUIDE.md §2 and TEST_SUITE_INDEX.md with spec citations; captured pytest --collect-only evidence for DB_AT_001 (0 tests collected as expected). Metrics: 0 tests collected for DB_AT_001 (planned selector), pytest collection runtime 0.98s. Artifacts: plans/active/TORCH-RUNTIME-002/reports/2025-10-28T232744Z/{notes.md,pytest_collect.log}. First Divergence: n/a. Next Actions: Exit criteria 1-4 satisfied; mark implementation.md phases A+B complete; update status to done; note DOC-RUNTIME-004 dependency for pytorch_runtime_checklist.md restoration in findings if needed.
docs/fix_plan.md:77:### [DOC-RUNTIME-004] Restore `docs/pytorch_runtime_checklist.md`
docs/fix_plan.md:82:  1. `docs/pytorch_runtime_checklist.md` resolves to a valid file (symlink or local copy) and can be opened without build errors.
docs/fix_plan.md:87:  * 2025-10-28T233630Z — Supervisor planning pass; confirmed symlink target (`../../nanoBragg2/docs/development/pytorch_runtime_checklist.md`) missing, indexed references unresolved, and new implementation plan required. Metrics: pending. Artifacts: pending.
input.md:3:Focus: DOC-RUNTIME-004 — Restore docs/pytorch_runtime_checklist.md
input.md:8:  1. DOC-RUNTIME-004 — A1 (plans/active/DOC-RUNTIME-004/implementation.md) — tests: none; run `rg 'pytorch_runtime_checklist' -n` and catalog every reference plus the missing symlink target in notes.md alongside key guardrails from docs/spec-db-runtime.md:10-20 and docs/spec-db-conformance.md:10-48.
input.md:9:  2. DOC-RUNTIME-004 — A2 (plans/active/DOC-RUNTIME-004/implementation.md) — tests: none; replace the broken symlink with a restored docs/pytorch_runtime_checklist.md that captures environment flags, runtime guardrails, acceptance hooks, and cites the spec shards gathered in A1.
input.md:12:  5. DOC-RUNTIME-004 — C1 (plans/active/DOC-RUNTIME-004/implementation.md) — tests: none; capture `head -n 40 docs/pytorch_runtime_checklist.md` into checklist_head.log under the artifact path and verify the Markdown renders key sections.
input.md:22:  - rg 'pytorch_runtime_checklist' -n > "$ART/notes.md"; append spec guardrail excerpts via `nl -ba docs/spec-db-runtime.md | sed -n '10,40p'`
input.md:23:  - Restore docs/pytorch_runtime_checklist.md using apply_patch or cat > file <<'EOF' (ensure ASCII) and cite spec shard anchors.
input.md:25:  - head -n 40 docs/pytorch_runtime_checklist.md | tee "$ART/checklist_head.log"; record command + results in summary.md.
input.md:35:  - Verify no lingering references still point to docs/development/pytorch_runtime_checklist.md.
docs/TESTING_GUIDE.md:26:- **Spec Reference**: `docs/pytorch_runtime_checklist.md:26`, `docs/development/testing_strategy.md:1.6`
docs/TESTING_GUIDE.md:68:| Runtime vectorization | `pytest tests/test_cli_scaling.py::TestSourceWeights* -v` | Equal-weight source handling and vectorized loops (`docs/pytorch_runtime_checklist.md:31`). | Planned | Currently in `nanoBragg2/tests/`; port to DBEX. |
CLAUDE.md:8:5. Architecture & runtime guidance: `docs/architecture.md`, `docs/pytorch_runtime_checklist.md`.
prompts/debug.md:14:- Geometry/runtime guardrails: `docs/spec-db-core.md`, `docs/pytorch_runtime_checklist.md`
docs/findings.md:6:| RUNTIME-001 | 2025-10-28 | runtime, torch.compile, gradcheck | Gradient tests require `NANOBRAGG_DISABLE_COMPILE=1` to avoid Dynamo interference with `torch.autograd.gradcheck`. | docs/pytorch_runtime_checklist.md:26 | Active |
docs/prompt_sources_map.json:42:    "docs/pytorch_runtime_checklist.md"
docs/development/TEST_SUITE_INDEX.md:14:| Runtime vectorization | `pytest tests/test_cli_scaling.py::TestSourceWeights* -v` | planned | `docs/pytorch_runtime_checklist.md:31` | Equal-weight source handling and vectorized loops. Currently in `nanoBragg2/tests/`; port to DBEX before marking active. |
docs/index.md:142:### [PyTorch Runtime Checklist](pytorch_runtime_checklist.md)
prompts/supervisor.md:14:- `docs/pytorch_runtime_checklist.md`
galph_memory.md:31:- Key Observations: Phase C smoke harness and ROI artifacts remain undone; no files matching *triptych* under plans/active/TORCH-BRIDGE-001/reports/; nanobrag_torch still unavailable so bridge stubs must be guarded; verified dataset assets (`refGeom.expt`, `_geom_ref.refl`, `scaled.mtz`) present for the run; `docs/pytorch_runtime_checklist.md` still missing per DOC-RUNTIME-004 backlog.
galph_memory.md:51:- Key Observations: TORCH-BRIDGE-001 reports reviewed (closure artifacts intact); runtime checklist symlink (docs/pytorch_runtime_checklist.md) still broken per DOC-RUNTIME-004; docs/TESTING_GUIDE.md already lists flags/selectors but needs explicit torch references and artifact guidance; TEST_SUITE_INDEX placeholders align with spec but lack evidence runs; no reports yet under plans/active/TORCH-RUNTIME-002/.
galph_memory.md:60:- Focus: DOC-RUNTIME-004 — Restore docs/pytorch_runtime_checklist.md
galph_memory.md:62:- Key Observations: Confirmed docs/pytorch_runtime_checklist.md is a dangling symlink pointing to ../../nanoBragg2/... (target absent); `rg` shows prompts, docs/index.md:142-150, and testing_strategy.md:27 rely on the checklist; spec shards docs/spec-db-runtime.md:10-20 and docs/spec-db-conformance.md:10-48 capture required guardrails/tests; prompt_sources_map.json still references the broken path.
docs/development/testing_strategy.md:27:- **Runtime checklist:** Consult `docs/development/pytorch_runtime_checklist.md` during development and cite it in fix-plan notes for PyTorch changes.
docs/development/testing_strategy.md:40:- **Torch Compile vs Gradcheck**: `torch.compile`/Dynamo interferes with `torch.autograd.gradcheck`. For any gradient test, export `NANOBRAGG_DISABLE_COMPILE=1` (see also `docs/pytorch_runtime_checklist.md:26`). If you see erratic or non‑deterministic gradcheck results, verify this flag first.
prompts/callchain.md:11:- Required references: `docs/index.md`, `docs/architecture.md`, `docs/architecture/pytorch_design.md`, `docs/spec-db-workflow.md`, `docs/spec-db-tracing.md`, `docs/config_crosswalk.md`, `docs/development/c_to_pytorch_config_map.md`, `docs/development/testing_strategy.md`, `docs/dials_api.md`, `docs/dxtbx_api.md`, `docs/spec-db-core.md`, `docs/pytorch_runtime_checklist.md`.
prompts/main.md:12:- `docs/pytorch_runtime_checklist.md`
prompts/main.md:37:   - Honor runtime guardrails (vectorization, dtype/device neutrality, torch.compile hygiene) from `docs/pytorch_runtime_checklist.md`.
prompts/main.md:68:- Treating source weights multiplicatively (equal-weight rule, `docs/pytorch_runtime_checklist.md:31`).
docs/debugging/TROUBLESHOOTING.md:23:- References: docs/development/testing_strategy.md:1.6; docs/pytorch_runtime_checklist.md:1

## Spec Guardrails from spec-db-runtime.md:10-20

    10	Runtime Guardrails (Normative)
    11	- Vectorization: Callers SHALL avoid Python loops over pixels/ROIs when vectorized simulator capabilities exist (per‑panel run or cropped detectors).
    12	- Device/dtype neutrality: Callers SHALL co‑locate tensors on the target device/dtype before `run()`; SHALL NOT call `.to()` inside tight loops.
    13	- Differentiability: Callers SHALL NOT use `.item()/.detach()` on differentiable parameters in forward passes; SHALL avoid `torch.linspace` endpoints that break graphs; use arange‑based arithmetic.
    14	- torch.compile: Simulator MAY compile graphs; callers SHALL keep tensor shapes stable during reuse to preserve caches. Changing image shape or oversample SHALL trigger re‑instantiation.
    15	- Eager fallback: `NANOBRAGG_DISABLE_COMPILE=1` SHALL disable compilation for debugging.
    16	- Seeds: Conformance SHALL specify deterministic seeds; random sources (if any) SHALL be controlled by explicit seeding.
    17	
    18	Environment (Normative)
    19	- `KMP_DUPLICATE_LIB_OK=TRUE` SHALL be set in all entry points importing torch.
    20	- `CUDA_VISIBLE_DEVICES` MAY be used to pin GPUs; device index SHALL be configurable.
    21	
    22	Shape‑Change Policy (Normative)
    23	- Reuse a warmed Simulator when `spixels/fpixels` and oversample are constant.
    24	- Rebuild Detector/Simulator when panel dimensions or oversample change.
    25	
    26	Compile Modes (Informative)
    27	- GPU commonly uses `mode="max-autotune"`; CPU may use `reduce-overhead`.
    28	
    29	References (Informative)
    30	- docs/nanobrag_api.md (runtime details).

## Conformance Rules from spec-db-conformance.md:10-48

    10	Conformance Profiles (Normative)
    11	- C‑Parity Profile:
    12	  - DB‑AT‑001 Simple cubic parity (image correlation ≥ 0.99 vs golden).
    13	  - DB‑AT‑002 Determinism under fixed seeds (bitwise or tolerance‑stable outputs).
    14	- Gradient‑Safe Profile:
    15	  - DB‑AT‑010 Gradcheck on refined parameters (cell logs/angles, quaternion seed → XYZ).
    16	  - DB‑AT‑011 No graph breaks under runtime mask/loss operations.
    17	- Workflow Integration Profile:
    18	  - DB‑AT‑020 DIALS reflection ingestion (bbox exclusivity, panel ordering) sanity.
    19	  - DB‑AT‑021 Mask polarity and shape conformance (trusted mask → simulator/loss).
    20	  - DB‑AT‑022 ROI background semantics (−1 outside ROI, masked MSE).
    21	  - DB‑AT‑023 ADU vs photons policy (flag honored; scale init for ADU mode).
    22	  - DB‑AT‑024 Mapping consistency (zero‑iteration forward vs data‑minus‑background overlay).
    23	
    24	Acceptance Tests (Normative)
    25	- DB‑AT‑001 Simple cubic parity
    26	  - Setup: use `nanoBragg2/tests/golden_data` configuration; simulate panel; compare to golden frame.
    27	  - Expectation: image correlation ≥ 0.99; residual RMS within tolerance.
    28	  - Command: `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests -k DB_AT_001`
    29	- DB‑AT‑020 Reflection ingestion sanity
    30	  - Setup: load .expt/.refl; extract first ROI; slice data with bbox; verify shape, exclusivity, panel ordering.
    31	  - Expectation: `shoebox.shape == (y1-y0, x1-x0)`; panel indices align.
    32	  - Command: `pytest -v tests -k DB_AT_020`
    33	- DB‑AT‑021 Mask polarity and shape
    34	  - Setup: load DIALS trusted mask; convert to simulator mask; verify mask/loss application on sample ROIs.
    35	  - Expectation: simulator zeros masked pixels post‑compute; loss excludes masked/background‑invalid pixels.
    36	  - Command: `pytest -v tests -k DB_AT_021`
    37	- DB‑AT‑022 ROI background semantics
    38	  - Setup: run simtbx background; confirm −1 sentinel outside ROIs; optional recompute with trusted mask.
    39	  - Expectation: sentinel logic correct; ROI coverage matches reflection metadata.
    40	  - Command: `pytest -v tests -k DB_AT_022`
    41	- DB‑AT‑023 Calibration policy
    42	  - Setup: run with and without `--adu-per-photon`; compare scale behavior and loss.
    43	  - Expectation: photon mode yields scale near 1; ADU mode learns positive scale with stable initialization.
    44	  - Command: `pytest -v tests -k DB_AT_023`
    45	 - DB‑AT‑024 Mapping consistency
    46	  - Setup: build per‑panel configs from a real Experiment; run a forward pass with initial parameters; evaluate K ROIs (e.g., 32) for correlation and localization.
    47	  - Expectation: median ROI correlation ≥ 0.2 and ≥90% ROIs contain a local intensity maximum within the central half‑box.
    48	  - Command: `pytest -v tests -k DB_AT_024`
