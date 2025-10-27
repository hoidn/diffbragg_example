# Spec Authoring Guide (DiffBragg / DBEX + PyTorch + Workflow)

This guide distills the effective patterns from the nanoBragg Spec A shards and adapts them for drafting specs that cover DiffBragg/DBEX, PyTorch runtime, and the surrounding workflow. The goal is a spec set that is auditable, implementation‑agnostic, and directly testable.

Audience: engineers authoring or reviewing specs; owners of DBEX/PyTorch integration and workflow tooling.

Non‑goals: duplicating SOPs or tutorials already maintained under `docs/`; the spec should link to those.

--------------------------------------------------------------------------------

1) Sharded Spec Architecture (Emulate)
- Rationale: Separate concerns reduce coupling and keep each shard reviewable. Cross‑link shards for a single normative contract.
- Recommended shards (filenames suggested):
  - `spec-db-core.md` (normative): physics, geometry, units, detector conventions; data contracts for reflections/ROIs/masks; required inputs/outputs.
  - `spec-db-runtime.md` (normative): PyTorch execution guardrails (vectorization, device/dtype neutrality, differentiability), environment variables.
  - `spec-db-workflow.md` (normative): end‑to‑end pipeline (Experiment/Reflection ingestion → ROI/background → masking/trusted range → calibration → simulation → loss).
  - `spec-db-interfaces.md` (normative): CLI/API surface, precedence rules, environment resolution (e.g., `NB_C_BIN`).
  - `spec-db-conformance.md` (normative): acceptance tests and C↔PyTorch parity suite with runnable commands.
  - `spec-db-tracing.md` (normative): tracing/instrumentation obligations and trace comparison workflow.
- Coordination: a short index (like `spec-a.md`) must list shards and declare that together they form the normative spec; keep shards consistent across edits.

2) Normative Voice and Rule Levels
- Use SHALL/SHOULD/MAY and avoid ambiguous phrasing. Keep prescriptive content in the spec; move “how to” steps to SOPs.
- Mark sections as “(Normative)” or “(Informative)” where helpful.
- Example: “BBox SHALL be inclusive on lower bounds and exclusive on upper bounds and MUST be sliceable as `img[pid, y0:y1, x0:x1]` without `+1` adjustments.”

3) Contract‑First With Tests (Executable Contracts)
- Every major requirement MUST map to a named acceptance test with a runnable command. Include:
  - A stable id: `DB-AT-00X`.
  - Setup parameters, expected behavior, and failure modes.
  - Canonical command lines (e.g., `KMP_DUPLICATE_LIB_OK=TRUE NB_C_BIN=... pytest -v ... -k DB-AT-00X`).
- Maintain a 1:1 spec‑to‑test table in `spec-db-conformance.md`.

4) Data Contracts (Be Unambiguous)
- Reflection table minimal schema for ROI/background:
  - Required: `id (flex.int)`, `panel (flex.size_t)`, `xyzobs.px.value (flex.vec3_double)` or `xyzcal.px`, `bbox (flex.int6: x0,x1,y0,y1,z0,z1)`.
  - Semantics: upper bounds exclusive; lower inclusive; fast axis is x, slow axis is y.
  - Panel indices: zero-based, identical ordering across detector, raw data tiles, masks.
- Masks:
  - DIALS generate_mask file format: tuple of `flex.bool` per panel, shape `(slow, fast)`, `True`=trusted.
  - DiffBragg hotpixel mask: NumPy or tuple of `flex.bool` with `True`=bad pixel. If ingesting a DIALS trusted mask, explicitly invert before use.
  - Trusted range: detector panels define an inclusive `[min, max]` window; default dynamic masks SHALL apply this window.
- Shapes:
  - Full images and masks SHALL be `(n_panels, slow, fast)`.
  - ROI slicing SHALL use Python semantics: `img[pid, y0:y1, x0:x1]`.

5) Units, Conventions, and Geometry (Copy The Precision)
- State units and conversions once (Å, mm, meters; degrees↔radians) and refer back; do not restate in each shard.
- Detector and pixel indexing conventions SHALL be explicit:
  - Pixel grids use `(slow, fast)` order internally; `meshgrid(..., indexing="ij")`.
  - Integer pixel indices refer to pixel leading edge/corner unless otherwise stated.
- Detector rotation order, pivot behavior (BEAM vs SAMPLE), and beam center relations should mirror the clarity of `spec-a-core.md`.

6) PyTorch Runtime Guardrails (Make Them Normative)
- Vectorization is mandatory: no Python loops when batched helpers exist.
- Device/dtype neutrality: no `.cpu()`/`.cuda()` in compiled paths; co‑locate tensors up front.
- Differentiability: forbid `.item()`, `.detach()`, and gradient‑breaking `torch.linspace` endpoints; require alternatives using `arange` arithmetic.
- Environment: `KMP_DUPLICATE_LIB_OK=TRUE` must be set in all Python entry points importing torch.
- Conformance profile “Gradient‑Safe” SHALL include running `torch.autograd.gradcheck` for differentiable parameters.

7) Tracing and Parity (Single Source of Truth)
- Instrumentation MUST reuse production helpers to avoid drift (no re‑deriving physics for trace only).
- Parity workflow SHALL define:
  - C trace generation (instrumented runner precedence, `NB_C_BIN` resolution).
  - PyTorch trace generation scripts.
  - First‑divergence diff procedure and unit validation before numeric compare.

8) Conformance Profiles (Opt‑In Bundles)
- Define named profiles with clear gates, e.g.:
  - C‑Parity Profile: image correlation thresholds, peak alignment, deterministic seeds.
  - Gradient‑Safe Profile: gradcheck passes, no graph breaks, dtype permutations.
  - Workflow Integration Profile: reflection/mask ingestion conformance, ROI background semantics, calibration handling.
- Each profile SHALL list the DB‑AT acceptance tests required to pass.

9) Interfaces (CLI/API) and Precedence Rules
- Document flag/env precedence deterministically (e.g., `--c-bin` > `NB_C_BIN` > default runner path).
- Specify input discovery order, ROI parameter precedence (`deltaQ` vs fixed shoebox), and any implicit defaults.

10) Cross‑References and Protected Assets
- Cross‑link SOPs and checklists (debugging detector geometry, testing strategy, PyTorch runtime checklist) rather than duplicating them. State that those documents are part of the spec contract by reference.
- Respect the Protected Assets Rule for `docs/index.md`; if a spec move impacts it, update that index in the same change with rationale.

11) Change Control and Versioning
- Version tags per shard (e.g., `v1.3`) and a short CHANGELOG in the shard footer.
- PR checklist: spec edits accompanied by updated acceptance tests and passing CI; shard cross‑refs updated; conformance profile gates unchanged or explicitly bumped.

12) Authoring Checklist (Quick)
- Define scope and shard target; confirm no duplication with existing shards.
- Write normative rules with SHALL/SHOULD; add data contracts and units/conventions as needed.
- Add acceptance tests with ids, setup, expected behavior, and runnable commands.
- Add cross‑references to SOPs/tools; avoid inline procedures.
- Validate tests locally; wire into `spec-db-conformance.md`.
- Version the shard; update the root spec index.

13) Minimal Shard Template (Copy‑Paste)
```
# spec-db-<name>.md — <Shard Title>

Overview (Normative)
- Purpose and scope in one paragraph.
- Out of scope (short list).

Requirements (Normative)
- R1: ... (SHALL ...)
- R2: ... (SHOULD ...)

Data Contracts (Normative)
- Inputs: columns/fields, dtypes/shapes, inclusivity/exclusivity.
- Outputs: shapes, sentinel values, units.

Acceptance Tests (Normative)
- DB-AT-00X <title>
  - Setup: ...
  - Expectation: ...
  - Command: KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests/... -k DB-AT-00X

References (Informative)
- SOPs, debugging checklists, architecture docs, code pointers.

Version
- vX.Y — YYYY‑MM‑DD — short summary of changes.
```

14) Common Pitfalls To Call Out In Spec Language
- Off‑by‑one bbox upper bounds (must be exclusive).
- Mask polarity mismatches (trusted vs bad‑pixel masks).
- Panel ordering inconsistencies across reflections, detector, and image stacks.
- Graph breaks from `.item()` or `torch.linspace` endpoints; CPU tensors leaked into CUDA ops.
- MOSFLM ±0.5 pixel beam center adjustments and axis swaps; detector pivot mode vs 2θ axis assumptions.

--------------------------------------------------------------------------------

Adopt this guide when introducing new shards or revising existing ones. The strength of the nanoBragg Spec A approach lies in clear, test‑anchored contracts; use the same discipline for DiffBragg/DBEX + PyTorch so teams can reason about behavior, validate it quickly, and evolve with confidence.

