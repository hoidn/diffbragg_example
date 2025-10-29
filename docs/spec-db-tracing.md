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

Parity Workflow (Normative)
1) Generate a torch golden reference trace for the panel/pixel under test (e.g., from a prior validated run).
2) Generate a PyTorch trace for the current build with identical inputs.
3) Validate inputs first (units, vectors, A* columns, detector basis), then compare stepwise outputs to locate first divergence.
4) Only after root cause resolution, update conformance tests and re‑run the full suite.

Commands (Informative)
- Provide CLI/API to enable trace flags and pick target pixels.

References (Informative)
- docs/nanobrag_api.md (debug_config); nanoBragg2/specs/spec-a-parallel.md for parity strategies.
