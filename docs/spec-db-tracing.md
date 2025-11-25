# spec-db-tracing.md — Tracing and Parity (Normative)

Overview (Normative)
- Purpose: Define tracing/instrumentation requirements and parity workflows to diagnose and resolve discrepancies.

Status
- Tracing and parity requirements apply to the planned `nanobrag_torch` backend. The legacy DiffBragg path has different instrumentation.
- Use `python -m dbex.refine_one` for the current CLI (see `dbex/refine_one.py:5-26`).

Tracing Requirements (Normative)
- The simulator SHALL support a per‑pixel trace mode (e.g., `debug_config.trace_pixel = [slow, fast]`) that captures the key intermediate values for that pixel.
- Trace payload SHALL be produced by the same code paths used in production (no re‑derived physics).
- Enabling trace MAY increase runtime; use sparingly (single pixel).
- Minimum trace schema (normative):
  - Required fields per traced pixel: incident `s0`/beam vector, `pixel_pos_lab`, detector normal, solid angle term, absorption term (if enabled), HKL fractional coords used for lookup, structure‑factor sample (with interpolation neighbors if applicable), Bragg contribution before masks, background contribution (if modeled), variance terms (`sigma_readout`, `sigma_floor`, `variance`), final masked model value.
  - Format: HDF5 group `/trace/<panel>/<slow>_<fast>/` (panel index as stored in `RefinementInputs`) with scalar datasets for each field above; implementations MAY add extra fields but SHALL include at least these with consistent names.

Parity Workflow (Normative)
1) Generate a torch golden reference trace for the panel/pixel under test (e.g., from a prior validated run).
2) Generate a PyTorch trace for the current build with identical inputs.
3) Validate inputs first (units, vectors, A* columns, detector basis), then compare stepwise outputs to locate first divergence.
4) Only after root cause resolution, update conformance tests and re‑run the full suite.

Commands (Informative)
- Provide CLI/API to enable trace flags and pick target pixels.

References (Informative)
- docs/nanobrag_api.md (debug_config); nanoBragg2/specs/spec-a-parallel.md for parity strategies.
