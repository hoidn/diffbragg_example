# spec-db-tracing.md — Tracing and Parity (Normative)

Overview (Normative)
- Purpose: Define tracing/instrumentation requirements and parity workflows to diagnose and resolve discrepancies.

Tracing Requirements (Normative)
- The simulator SHALL support a per‑pixel trace mode (e.g., `debug_config.trace_pixel = [slow, fast]`) that captures the key intermediate values for that pixel.
- Trace payload SHALL be produced by the same code paths used in production (no re‑derived physics).
- Enabling trace MAY increase runtime; use sparingly (single pixel).

Parity Workflow (Normative)
1) Generate a C reference trace (if applicable) or a torch golden reference for the panel/pixel under test.
2) Generate a PyTorch trace for the same pixel with identical inputs.
3) Validate inputs first (units, vectors, A* columns, detector basis), then compare stepwise outputs to locate first divergence.
4) Only after root cause resolution, update conformance tests and re‑run the full suite.

Commands (Informative)
- Provide CLI/API to enable trace flags and pick target pixels.

References (Informative)
- docs/nanobrag_api.md (debug_config); nanoBragg2/specs/spec-a-parallel.md for parity strategies.

