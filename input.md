# Input for Ralph — Loop i=129

## Summary
Complete MAP-SCALE-005 Phase A (CLI refined telemetry enforcement reality check and guard design). Reproduce current CLI fallback behavior when refined MTZ is missing, gather spec citations supporting failure-on-fallback policy, and define precise failure surfaces with user-facing error messaging strategy.

## Mode
Planning

## ActionType
planning

## DecisionStatus
exploring

## InitiativeType
spec_change

## Focus
[MAP-SCALE-SYNC-001] — Calibration Ladder Synchronization (member plan: MAP-SCALE-005 Phase A)

## Branch
integration

## Mapped tests
None — planning loop (Phase A design artifacts only, no production changes)

## Artifacts
`plans/active/MAP-SCALE-005/reports/2025-12-06T235959Z/`

## Findings Applied (Mandatory)
- **SCALE-003** (dbex/nanobrag_bridge.py:843-1106): Zero-iteration torch helper must ingest DiffBragg-refined |F| amplitudes and √spot_scale; Phase A will confirm CLI paths honor this.
- **SCALE-004** (dbex/nanobrag_bridge.py:959-965): CLI must forward beam/crystal calibration metadata to simulator; Phase A will check whether refined MTZ absence triggers proper failure vs silent fallback.
- **SCALE-006** (dbex/refine_one.py:162-248): CLI must ingest calibration before invoking simulator; Phase A will test whether missing refined MTZ reverts to raw without error.
- **SCALE-007** (dbex/nanobrag_bridge.py:843-1106, tests/dbex/test_mapping_consistency.py:272-358): Zero-iteration bridge must emit structure-factor telemetry and tests must fail when refined assets are present but telemetry reports `raw` or is missing; Phase A will extend this to CLI by defining failure surfaces when `--refined-mtz` is explicit but ingestion fails.

## ARCH Contracts (mandatory)
1. **ARCH-CONTRACT-CALIBRATION-001** (dbex/refine_one.py): CLI backend SHALL populate hkl_source based on --refined-mtz vs --mtzFile precedence; currently falls back silently when refined MTZ load fails.
   - Owner module/API: dbex/refine_one.py::run_nanobrag_backend
   - Failure classification: **implementation bug within architecture** (silent fallback violates SCALE-007 telemetry enforcement intent)

2. **ARCH-CONTRACT-STRUCTURE-FACTORS-001** (dbex/nanobrag_bridge.py): Bridge SHALL construct hkl_telemetry dict from function params + computed stats; currently reports "raw" when refined MTZ missing.
   - Owner module/API: dbex/nanobrag_bridge.py::simulate_forward_once
   - Failure classification: **implementation bug within architecture** (fallback logic correct per bridge contract, but CLI must enforce before delegating)

3. **ARCH-CONTRACT-WRITER-001** (dbex/io/writer.py): Writer SHALL serialize hkl_telemetry to HDF5 attrs; no enforcement that hkl_source matches user intent.
   - Owner module/API: dbex/io/writer.py::write_torch_outputs
   - Failure classification: **not a failure** (writer correctly persists whatever telemetry it receives; enforcement belongs upstream at CLI layer)

## Do Now (hard validity contract)

### Focus
[MAP-SCALE-005] Phase A — CLI refined telemetry enforcement reality check and guard design

### Tasks
1. **Reality Check (A1):**
   - Reproduce current CLI fallback behavior when `--refined-mtz` points to missing file
   - Run: `python -m dbex.refine_one --backend nanobrag -e tests/fixtures/golden_data/simple_cubic/refined.expt -r tests/fixtures/golden_data/simple_cubic/refined.refl -i 0 -o /tmp/test_fallback.h5 -m tests/fixtures/golden_data/simple_cubic/747_mask.pkl -z tests/fixtures/golden_data/simple_cubic/refined_structure_factors.mtz --refined-mtz /nonexistent/path.mtz --torch-config tests/fixtures/golden_data/simple_cubic/config_torch.json`
   - Capture stdout/stderr and inspect HDF5 `/torch_diagnostics` attrs to confirm `hkl_source` value (expect "raw" fallback)
   - Document observed behavior in `plans/active/MAP-SCALE-005/reports/2025-12-06T235959Z/fallback_reproduction.md`

2. **Spec Citations Gathering (A2):**
   - Read and cite relevant sections from:
     - docs/spec-db-workflow.md §4 (Calibration & refined structure-factor workflow)
     - docs/spec-db-tracing.md §2 (Torch diagnostics artifact expectations)
     - docs/findings.md (SCALE-003, SCALE-004, SCALE-007)
   - Synthesize spec support for failure-on-fallback policy (why silent fallback violates normative behavior)
   - Document citations in `plans/active/MAP-SCALE-005/reports/2025-12-06T235959Z/spec_citations.md`

3. **Guard Design (A3):**
   - Define precise failure surfaces:
     a) Refined MTZ file missing or unreadable
     b) load_refined_mtz raises exception
     c) telemetry downgrade (hkl_source becomes "raw" after --refined-mtz flag)
   - Draft user-facing error message template (actionable, references flag and expected file path)
   - Specify where guard should live (run_nanobrag_backend after load attempt, before simulation)
   - Document design in `plans/active/MAP-SCALE-005/reports/2025-12-06T235959Z/guard_design.md`

4. **Planning Summary (A4):**
   - Consolidate findings from A1-A3
   - Outline Phase B scope (implementation + tests)
   - Note any risks (Environment Freeze compliance, backward compatibility)
   - Write `plans/active/MAP-SCALE-005/reports/2025-12-06T235959Z/summary.md`

### Validation
No tests for planning loop. Phase B will add regression coverage.

### Artifacts
All outputs under `plans/active/MAP-SCALE-005/reports/2025-12-06T235959Z/`:
- fallback_reproduction.md
- spec_citations.md
- guard_design.md
- summary.md

## Forbidden This Loop
- No production code changes (planning-only loop)
- Do not extend plan-local diagnostic scripts (probe freeze policy)

## How-To Map
```bash
# A1: Reality check (reproduce fallback)
cd /home/ollie/Documents/diffbragg_example
export KMP_DUPLICATE_LIB_OK=TRUE
export NANOBRAGG_DISABLE_COMPILE=1
python -m dbex.refine_one --backend nanobrag \
  -e tests/fixtures/golden_data/simple_cubic/refined.expt \
  -r tests/fixtures/golden_data/simple_cubic/refined.refl \
  -i 0 -o /tmp/test_fallback.h5 \
  -m tests/fixtures/golden_data/simple_cubic/747_mask.pkl \
  -z tests/fixtures/golden_data/simple_cubic/refined_structure_factors.mtz \
  --refined-mtz /nonexistent/path.mtz \
  --torch-config tests/fixtures/golden_data/simple_cubic/config_torch.json 2>&1 | tee plans/active/MAP-SCALE-005/reports/2025-12-06T235959Z/cli_fallback_stdout.log

# Inspect HDF5 telemetry
python -c "import h5py; f = h5py.File('/tmp/test_fallback.h5', 'r'); print('hkl_source:', f['/torch_diagnostics'].attrs.get('hkl_source', 'MISSING'))"

# A2: Read specs
# (Use Read tool on docs/spec-db-workflow.md, docs/spec-db-tracing.md, docs/findings.md)

# A3: Design guard
# (Write guard_design.md with failure surfaces and error message template)

# A4: Summary
# (Consolidate A1-A3 into summary.md)
```

## Pitfalls To Avoid
1. **Type discipline:** This is spec_change (not bugfix) because we're changing CLI behavior from silent-fallback to fail-fast; document rationale in spec_citations.md.
2. **No stacking on cliffs:** Not applicable (no recent failures).
3. **Parity-first interpretation:** Not applicable (no DMI).
4. **Evidence→Action contract:** Planning loop must end with Phase B readiness checklist (guard design complete, implementation scope known).
5. **Environment Freeze:** Do not install packages; reproduction uses existing fixtures and CLI.
6. **Probe saturation:** Not applicable (no new probes, docs-only).
7. **Shadow-pipeline guard:** Not applicable (no scripts).
8. **Findings paydown:** SCALE-007 finding applied; Phase A extends enforcement from test harness to CLI layer.
9. **Initiative budget:** First loop for MAP-SCALE-005, no budget concerns.
10. **Dwell enforcement:** First planning loop for this focus, dwell=0.

## If Blocked
If SCALE-007 spec language is ambiguous about CLI enforcement scope:
1. Mark A2 as requiring spec amendment and record in spec_citations.md
2. Propose spec language update (CLI MUST fail when --refined-mtz provided but not consumed)
3. Continue with guard design assuming spec amendment acceptance
4. Note dependency in summary.md (Phase B blocked pending spec ratification)
