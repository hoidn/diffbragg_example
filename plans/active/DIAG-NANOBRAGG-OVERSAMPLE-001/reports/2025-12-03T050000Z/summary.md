### Turn Summary
Corrected root cause from "single config mutation" to "290 configs created with wrong default"; traced to 6 stage_a_utils.py call sites missing oversample parameter.
Planned Phase C config threading fix: add RefinementConfig.oversample field, update 2 signatures, pass to 6 factories and ~5 callers (15-20 lines, LOW risk).
Next: Ralph implements threading, expects 292/292 oversample=3 in debug logs and DB-AT-028/029 PASS in clean validation.
Artifacts: plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-03T050000Z/ (phase_c_planning.md, comprehensive input.md)
