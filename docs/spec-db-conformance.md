# spec-db-conformance.md — Acceptance Tests (Normative)

Overview (Normative)
- Purpose: Define executable acceptance tests (DB‑AT‑XXX) that collectively certify a build as conformant with Spec DB.

Status
- These acceptance tests target the forthcoming `nanobrag_torch` backend and are currently placeholders. They are not wired to the existing DiffBragg CLI.
- Until the torch backend is available, use `python -m dbex.refine_one` (see `dbex/refine_one.py:5-26`) and treat these tests as future work.
Conformance Profiles (Normative)
- Forward Equivalence Profile:
  - DB‑AT‑001 Forward equivalence smoke (DiffBragg vs `nanobrag_torch` forward pass; run without refinement and compare coarse ROI metrics per `plans/nanobrag_integration_plan.md` Phase 1).
- Gradient‑Safe Profile:
  - DB‑AT‑010 Gradcheck on refined parameters (cell logs/angles, quaternion seed → XYZ).
  - DB‑AT‑011 No graph breaks under runtime mask/loss operations.
- Workflow Integration Profile:
  - DB‑AT‑020 DIALS reflection ingestion (bbox exclusivity, panel ordering) sanity.
  - DB‑AT‑021 Mask polarity and shape conformance (trusted mask → simulator/loss).
  - DB‑AT‑022 ROI background semantics (−1 outside ROI, masked MSE).
  - DB‑AT‑023 ADU vs photons policy (flag honored; scale init for ADU mode).
  - DB‑AT‑024 Mapping consistency (zero‑iteration forward vs data‑minus‑background overlay).

Acceptance Tests (Normative)
- DB‑AT‑001 Forward equivalence smoke
  - Setup: Using the same `DataLoad` inputs, generate a single forward `Bragg` tensor with the legacy DiffBragg pipeline and the torch bridge (no parameter updates). Compare coarse metrics (ROI correlation ≥ 0.2, localized intensity per `plans/nanobrag_integration_plan.md` Phase 1) and capture visual overlays/logs. Optional trace capture for representative pixels is described in `docs/forward_equivalence.md`. If thresholds are not met, emit diagnostic artifacts instead of failing the run.
  - Expectation: median ROI correlation ≥ 0.2 and ≥90% of sampled ROIs contain a local intensity maximum within the central half-box; failing runs SHOULD attach diagnostic overlays instead of asserting.
  - Command: `KMP_DUPLICATE_LIB_OK=TRUE pytest -v tests -k DB_AT_001` (selector MAY xfail when only diagnostic evidence is captured).
- DB‑AT‑020 Reflection ingestion sanity
  - Setup: load .expt/.refl; extract first ROI; slice data with bbox; verify shape, exclusivity, panel ordering.
  - Expectation: `shoebox.shape == (y1-y0, x1-x0)`; panel indices align.
  - Command: `pytest -v tests -k DB_AT_020`
- DB‑AT‑021 Mask polarity and shape
  - Setup: load DIALS trusted mask; convert to simulator mask; verify mask/loss application on sample ROIs.
  - Expectation: simulator zeros masked pixels post‑compute; loss excludes masked/background‑invalid pixels.
  - Command: `pytest -v tests -k DB_AT_021`
- DB‑AT‑022 ROI background semantics
  - Setup: run simtbx background; confirm −1 sentinel outside ROIs; optional recompute with trusted mask.
  - Expectation: sentinel logic correct; ROI coverage matches reflection metadata.
  - Command: `pytest -v tests -k DB_AT_022`
- DB‑AT‑023 Calibration policy
  - Setup: run with and without `--adu-per-photon`; compare scale behavior and loss.
  - Expectation: photon mode yields scale near 1; ADU mode learns positive scale with stable initialization.
  - Command: `pytest -v tests -k DB_AT_023`
 - DB‑AT‑024 Mapping consistency
  - Setup: build per‑panel configs from a real Experiment; run a forward pass with initial parameters; evaluate K ROIs (e.g., 32) for correlation and localization.
  - Expectation: median ROI correlation ≥ 0.2 and ≥90% ROIs contain a local intensity maximum within the central half‑box.
  - Command: `pytest -v tests -k DB_AT_024`

Notes (Informative)
- Provide real commands in the test suite once scaffolding is in place; these are placeholders for the conformance contract.

References (Informative)
- docs/spec-db-core.md; docs/spec-db-runtime.md; docs/spec-db-workflow.md.
