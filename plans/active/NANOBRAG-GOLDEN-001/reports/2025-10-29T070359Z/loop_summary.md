# NANOBRAG-GOLDEN-001 Loop Summary (2025-10-29T070359Z)

## Loop Type
Docs-only reality-check loop documenting blocker under Environment Freeze constraints.

## Objectives
1. Extract and document the diffBragg_forward failure details from prior attempt
2. Audit torch-side artifacts and fixture manifests to confirm canonical dataset gap
3. Re-run collect-only for DB_AT_001 selectors to maintain testing documentation currency
4. Update fix_plan.md with blocked status and new Attempts History entry

## Completion Status
✓ All Do Now tasks completed (4/4)

## Key Findings
### DiffBragg Forward Blocker
- **Root Cause**: simtbx C++/CUDA cleanup bug at `diffBraggCUDA.cu:708`
- **Impact**: Cannot generate full-panel DiffBragg baseline (`bragg_diffbragg.npy`)
- **Workaround Status**: ROI-level output via `dbex.refine_one` works; standalone `diffBragg_forward` fails on both CPU (devId=-1) and GPU (devId=0)
- **Environment Freeze**: Cannot patch simtbx source per `CLAUDE.md` and `docs/index.md:8`

### Canonical Dataset Gap
- Current fixture: `simple_cubic_fallback` (synthetic, from PARITY-HARNESS-002)
- No canonical nanoBragg2 or DiffBragg full-panel tensors under 2025-10-29T063817Z reports
- Exit criteria require paired DiffBragg/torch baselines per `docs/forward_equivalence.md:21-52`

### Plan Re-Scope Options
1. **Accept ROI-level parity**: Revise exit criteria to use `dbex.refine_one` HDF5 outputs (92 ROIs × 12×12)
2. **Decouple captures**: Generate torch tensors independently, defer DiffBragg baseline requirement
3. **Wait for simtbx patch**: Block until upstream fixes diffBraggCUDA.cu:708 cleanup bug

## Artifacts Generated
| Artifact | Size | Description |
|----------|------|-------------|
| blocking_summary.md | 3.0K | Root cause, impact, workarounds, return conditions |
| torch_gap_notes.md | 1.8K | Manifest audit, plan re-scope options |
| logs/diffbragg_forward_excerpt.log | 953B | Last 150 lines of canonical_capture.log with CUDA error |
| logs/roi_refine_one.log | 1.3M | ROI-level refine_one output for reference |
| collect_db_at_001_parity.log | 1.2K | 14 tests collected, 0.23s |
| collect_db_at_001_forward.log | 1.2K | 1 test collected, 0.99s |

## Testing Evidence
- **DB_AT_001 parity selector**: 14 tests collected (Active per TESTING-003)
- **DB_AT_001 forward equivalence selector**: 1 test collected (Active per TESTING-003)
- **Total**: 15 tests, both selectors maintain >0 collection requirement

## Metrics
- 4/4 Do Now tasks completed
- 2/2 collect-only commands successful
- 2 artifact docs authored (blocking_summary.md, torch_gap_notes.md)
- 0 code changes (docs-only loop per mode)
- 1 fix_plan.md Attempts History entry added
- 1 status transition: `in_progress` → `blocked`

## Applied Findings
- **DIFFBRAGG-001** (docs/findings.md:15): Documents C++/CUDA bug and ROI-level workaround
- **CONFORMANCE-001** (docs/findings.md:7): DB_AT_001 acceptance thresholds remain documented during block
- **TESTING-003** (docs/findings.md:13): Selector evidence stays current when adjusting ledger status

## Next Actions
Return control to supervisor with:
- **Status**: blocked
- **next_action**: switch_focus
- **Return conditions**:
  1. External simtbx patch timeline guidance
  2. Plan revision to accept ROI-level baselines
  3. Decoupled torch-only canonical dataset generation authorization

## Spec References
- `docs/spec-db-core.md:20-41` — Tensor contracts `[panel, slow, fast]`
- `docs/forward_equivalence.md:21-52` — Exit criteria requiring paired baselines
- `docs/spec-db-conformance.md:23-26` — DB_AT_001 acceptance thresholds
- `docs/findings.md:15` — DIFFBRAGG-001 blocker documentation
- `docs/TESTING_GUIDE.md:85-86` — DB_AT_001 selector documentation requirements
- `CLAUDE.md` — Environment Freeze policy
- `docs/index.md:8` — Runtime pre-provisioning constraint

## Documentation Updates
- `docs/fix_plan.md`: New Attempts History entry (2025-10-29T070359Z), status → `blocked`
- All testing documentation remains synchronized with current selector evidence
