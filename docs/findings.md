# DBEX Knowledge Base Ledger

| ID | Date | Tags | Summary | Source | Status |
| --- | --- | --- | --- | --- | --- |
| GEOMETRY-001 | 2025-10-28 | geometry, detector, dxtbx | Bridge MUST derive beam center and detector vectors exactly per dxtbx mapping; reject non-square pixel pitch. | docs/spec-db-core.md:35 | Active |
| RUNTIME-001 | 2025-10-28 | runtime, torch.compile, gradcheck | Gradient tests require `NANOBRAGG_DISABLE_COMPILE=1` to avoid Dynamo interference with `torch.autograd.gradcheck`. | docs/pytorch_runtime_checklist.md:26 | Active |
| CONFORMANCE-001 | 2025-10-28 | testing, acceptance, parity | DB-AT parity and workflow profiles define canonical pytest selectors (`-k DB_AT_0XX`) and environment flag `KMP_DUPLICATE_LIB_OK=TRUE`. | docs/spec-db-conformance.md:10 | Active |

