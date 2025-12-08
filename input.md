# Input for Ralph (Loop i=177)

## Summary
Execute REPORT-NANOBRAG-STATUS-001 Phase B — Update `reports/nanobrag_validation.md` with current telemetry from the selected HDF5 file.

## BindingForRalph
- **ActionType:** implementation
- **DecisionStatus:** patch_ready
- **InitiativeType:** tooling

## SupervisorMode
Docs (reporting pack finalization — minimal code in update script only)

## Focus
REPORT-NANOBRAG-STATUS-001 — Nanobrag Progress Reporting Pack — Phase B (Report Finalization)

## Branch
integration

## Mapped Tests
- None — this is a reporting/docs-only loop; no production test validation required

## Artifacts
`plans/active/REPORT-NANOBRAG-STATUS-001/reports/2025-12-08T071251Z/`

## Findings Applied (Mandatory)
- **PROBE-FREEZE-001** (Plan-local probe policy): Minimal inline Python for HDF5 parsing; no new persistent scripts
  - Adherence: Use inline Python or existing tools only; no new `bin/` scripts
- **DIAGNOSTICS-001** (Diagnostic artifact expectations): Artifacts follow established JSON/markdown patterns
  - Adherence: Artifacts routed to `reports/2025-12-08T071251Z/`
- No other findings directly applicable to this reporting task

## Pointers
- Implementation plan: `plans/active/REPORT-NANOBRAG-STATUS-001/implementation.md`
- Phase A artifacts: `plans/active/REPORT-NANOBRAG-STATUS-001/reports/2025-12-08T010000Z/`
  - Selected HDF5: `./plans/active/TORCH-REFINE-004/reports/2025-11-05T210730Z/nanobrag_stage_progress.h5`
  - Telemetry schema: `telemetry_schema.json`
  - Plan-vs-status matrix: `plan_status_matrix_draft.md`
- Existing validation report: `reports/nanobrag_validation.md` (needs update)
- Fix plan entry: `docs/fix_plan.md` lines 512-537

---

## ARCH Contracts (mandatory)
- **Environment Freeze**: No package installs; read-only HDF5 parsing
  - Owner: CLAUDE.md
  - Classification: Reporting update — if plotting libraries unavailable, emit JSON/tables only

---

## Do Now

**Focus:** REPORT-NANOBRAG-STATUS-001 Phase B — Report Finalization

**Implement:** `reports/nanobrag_validation.md::update_with_current_telemetry`

**Validating Pytest Selector:** None (docs-only loop)

### Background
Phase A complete (i=176): Selected `./plans/active/TORCH-REFINE-004/reports/2025-11-05T210730Z/nanobrag_stage_progress.h5` as primary HDF5 source. Telemetry schema documented showing loss traces (initial 981638 → final 979335, 0.235% improvement), 92 ROIs, and schema gaps (missing param_deltas, optimizer_config, hkl_source).

Existing `reports/nanobrag_validation.md` uses older HDF5 from `2025-11-05T184233Z`. Update it to:
1. Reference the newer selected HDF5
2. Refresh loss telemetry numbers
3. Update plan-vs-status matrix per Phase A draft
4. Add schema gaps section documenting telemetry not yet implemented

### Phase B Tasks

#### B1 — Parse Telemetry from Selected HDF5

Extract and format loss convergence data:

```python
import h5py
import json

selected = "./plans/active/TORCH-REFINE-004/reports/2025-11-05T210730Z/nanobrag_stage_progress.h5"
with h5py.File(selected, 'r') as f:
    diag = f['torch_diagnostics']

    # Loss trace
    loss_full = diag['refine_loss_trace_full'][...]
    print(f"Loss trace: {loss_full}")

    # ROI count
    roi_count = len([k for k in f['data'].keys() if k.startswith('roi')])
    print(f"ROI count: {roi_count}")

    # Sample loss values
    loss_sample = diag['refine_loss_trace_sample'][...]
    print(f"Loss samples: {loss_sample}")
```

**Output:** `reports/2025-12-08T071251Z/parsed_telemetry.json`

#### B2 — Update reports/nanobrag_validation.md

Update the existing report with:
1. **HDF5 Source**: Change to `plans/active/TORCH-REFINE-004/reports/2025-11-05T210730Z/nanobrag_stage_progress.h5`
2. **Loss Telemetry**: Update table with 981638 → 979335 (0.235% improvement)
3. **Phase Status**: Incorporate Phase A matrix showing Phase 3 Partial, Phase 4 Done, Phase 5 In Progress
4. **Stage Status**: Stage A Done (convergence verified), Stage B Partial, Stage C Blocked
5. **Schema Gaps Section**: Add new section documenting missing telemetry fields (param_deltas, optimizer_config, hkl_source, perf metrics)
6. **Blockers Section**: Update with current tier 0 blockers (ARCH-GRADIENT-FLOW-001, PERF-WARM-SIM-001, ARCH-SIM-CONSTRUCTION-001)
7. **Artifacts Path**: Update to `plans/active/REPORT-NANOBRAG-STATUS-001/reports/2025-12-08T071251Z/`

#### B3 — Generate Convergence Table

Create markdown table showing iteration-by-iteration loss:

| Iteration | Loss | Δ from Initial | % Change |
|-----------|------|----------------|----------|
| 0 | 981638.31 | — | — |
| 5 | 979336.00 | -2302.31 | -0.235% |
| 10 | 979335.56 | -2302.75 | -0.235% |

**Output:** Include in `reports/nanobrag_validation.md` and `reports/2025-12-08T071251Z/convergence_table.md`

#### B4 — Cross-Reference Stage C Regression

Document the Stage C blocker per PERF-WARM-SIM-001:
- Stage C chi² regression: +0.067% above tolerance
- Link to PERF-WARM-SIM-001 in fix_plan.md
- Note panel-loss divergence as root cause

#### B5 — Author Phase B Summary

Create `reports/2025-12-08T071251Z/summary.md` with:
1. Telemetry parsed from selected HDF5
2. Validation report updated
3. Convergence table generated
4. Exit criteria validation

---

## How-To Map

```bash
# Set environment
cd /home/ollie/Documents/diffbragg_example
export ARTIFACT_DIR=plans/active/REPORT-NANOBRAG-STATUS-001/reports/2025-12-08T071251Z
export KMP_DUPLICATE_LIB_OK=TRUE

# B1: Parse telemetry (inline Python)
python3 -c "
import h5py
import json
selected = './plans/active/TORCH-REFINE-004/reports/2025-11-05T210730Z/nanobrag_stage_progress.h5'
with h5py.File(selected, 'r') as f:
    diag = f['torch_diagnostics']
    loss_full = diag['refine_loss_trace_full'][...]
    roi_count = len([k for k in f['data'].keys() if k.startswith('roi')])
    result = {
        'loss_trace': [{'iteration': int(r[0]), 'loss': float(r[1])} for r in loss_full],
        'roi_count': roi_count,
        'initial_loss': float(loss_full[0][1]),
        'final_loss': float(loss_full[-1][1]),
        'improvement_pct': round((1 - loss_full[-1][1]/loss_full[0][1]) * 100, 3)
    }
    print(json.dumps(result, indent=2))
"

# B2: Update reports/nanobrag_validation.md with Edit tool
# B3: Create convergence_table.md in ARTIFACT_DIR
# B4: Add Stage C regression note to validation report
# B5: Author summary.md
```

---

## Forbidden This Loop
- **No production code changes** — Reporting/docs only
- **No package installs** — Environment Freeze
- **No new persistent scripts** — Use inline Python for HDF5 parsing per PROBE-FREEZE-001

## Pitfalls To Avoid
1. **Don't run refinement** — Only parse existing HDF5 outputs
2. **Don't modify HDF5 files** — Read-only access
3. **Preserve existing report structure** — Update sections, don't rewrite entirely
4. **Use actual numbers from telemetry** — Don't copy placeholder values
5. **Link to fix_plan.md entries** — Cross-reference blockers properly

## If Blocked
If HDF5 parsing fails:
1. Document the error in `reports/2025-12-08T071251Z/error.md`
2. Fall back to Phase A telemetry_schema.json data
3. Note limitation in validation report

---

## Exit Criteria Validation (Phase B)

| Criterion | Expected | Validation |
|-----------|----------|------------|
| Telemetry parsed | Loss trace + ROI count | parsed_telemetry.json |
| Validation report updated | HDF5 source, loss table, phase status, blockers | reports/nanobrag_validation.md diff |
| Convergence table | Iteration-by-iteration loss | convergence_table.md |
| Summary authored | Phase B closure | summary.md |

---

## Output Artifacts Expected

1. `plans/active/REPORT-NANOBRAG-STATUS-001/reports/2025-12-08T071251Z/parsed_telemetry.json`
2. `plans/active/REPORT-NANOBRAG-STATUS-001/reports/2025-12-08T071251Z/convergence_table.md`
3. `plans/active/REPORT-NANOBRAG-STATUS-001/reports/2025-12-08T071251Z/summary.md`
4. Updated `reports/nanobrag_validation.md`

---

## Implement Target
`reports/nanobrag_validation.md::update_with_current_telemetry` (docs update)

## Validating Pytest Selectors
None — docs-only loop

---

## Next Up (optional)
If Phase B completes successfully:
- Validate all 4 exit criteria per implementation.md
- If met, mark REPORT-NANOBRAG-STATUS-001 as done in fix_plan.md
- Select next focus from Tier 1 (DB-AT-SUITE-CARE-001 Phase D maintenance or TORCH-CLI-BRIDGE-ROLLUP-001)
