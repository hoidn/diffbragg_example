# Ralph Input — TOOLING-VIS-001 Phase B.2 (Auto-Generate Triptych Report)

## Summary
Add `--report-dir` CLI flag to `dbex/refine_one.py` that automatically generates triptych PNGs for all ROIs after refinement completes, eliminating need for manual `dbex.look --export-triptychs` invocation.

## Mode
Docs (CLI enhancement with manual validation)

## Focus
TOOLING-VIS-001 — Standardized Visual Diagnostics (Phase B.2: Auto-Generate Summary Report)

## Branch
integration

## Mapped Tests
none — manual validation (compilation check + CLI smoke tests)

## Artifacts
```
plans/active/TOOLING-VIS-001/reports/2025-11-24T120000Z/
  phase_b2_planning_analysis.md           (comprehensive planning, already written by Galph)
  validation_compilation.log              (python -c import check)
  cli_test_legacy.txt                     (manual legacy backend test command + output summary)
  cli_test_torch.txt                      (manual torch backend test command + output summary)
  decision.json                           (4-path decision tree outcome)
  summary.md                              (Turn Summary)
```

## Do Now

**Objective:** Implement Phase B.2 per planning analysis — add optional `--report-dir <path>` flag that auto-generates triptych PNGs using `dbex.vis.plot_triptych`.

### Context Priming (READ FIRST)
1. Read `plans/active/TOOLING-VIS-001/reports/2025-11-24T120000Z/phase_b2_planning_analysis.md` (comprehensive planning with design decisions, code template, validation strategy)
2. **Phase A API Reference**: `dbex.vis.plot_triptych(data, model, variance, filename=None, hkl=None, correlation=None)` — validated in Phase A tests (tests/dbex/test_vis_triptych.py)
3. **Phase B.1 HDF5 Structure**: HDF5 files now contain `data/roi%d`, `model/roi%d`, `variance/roi%d`, `sigma_readout`, `sigma_floor` datasets (both Legacy and Torch backends)
4. **Similar Pattern**: `dbex/look.py` lines 170-189 (export_triptychs method) shows working example of iterating over ROIs and calling `plot_triptych`

### Implementation Protocol (10 steps)

**Step 1: Add CLI Argument**
- File: `dbex/refine_one.py`
- Location: argparse section (~line 30-60)
- Add:
  ```python
  parser.add_argument('--report-dir', type=str, default=None,
                      help='Optional directory to save triptych report (PNG per ROI)')
  ```

**Step 2: Implement Helper Function**
- File: `dbex/refine_one.py`
- Location: End of file (~line 250-300, before `if __name__ == "__main__"`)
- Function name: `_generate_triptych_report(h5_path: str, report_dir: str) -> None`
- Template in planning analysis (pseudocode section)
- Key requirements:
  - Import `dbex.vis.plot_triptych` (lazy import inside function OK)
  - Create `report_dir` with `Path(report_dir).mkdir(parents=True, exist_ok=True)`
  - Open HDF5 file read-only: `with h5py.File(h5_path, 'r') as h5:`
  - Detect number of ROIs: `while f"data/roi{n_rois}" in h5: n_rois += 1`
  - Loop over ROIs, read `data/roi%d`, `model/roi%d`, `variance/roi%d` datasets
  - Graceful degradation: if variance missing, print warning and skip ROI
  - Call `plot_triptych(data, model, variance, filename=str(out_png))`
  - Try/except around each ROI to prevent one failure from blocking others
  - Print final message: `print(f"Triptych report saved to: {report_dir}")`
- Estimated: 40-50 lines

**Step 3: Integrate Helper Calls**
- File: `dbex/refine_one.py`
- Locations:
  - Legacy backend: After HDF5 write (~line 270), before `print("Done")`
  - Torch backend: After HDF5 write (~line 690), before `print("Done")`
- Pattern:
  ```python
  if args.report_dir:
      _generate_triptych_report(args.out, args.report_dir)
  ```
- Ensure HDF5 file is closed before calling helper (add explicit close or verify context manager usage)
- Estimated: 6-10 lines (2 call sites)

**Step 4: Compilation Check**
- Command: `python -c "from dbex.refine_one import main; print('Compilation OK')"`
- Log output to `validation_compilation.log`
- Expected: "Compilation OK" with no import errors

**Step 5: Manual CLI Test (Legacy Backend)**
- If smoke test data available (e.g., golden_data/simple_cubic/), construct command:
  ```bash
  python -m dbex.refine_one --backend diffbragg \
    -e <expt.json> -r <refl.refl> -i 0 \
    -o /tmp/tooling_vis_test_legacy.h5 \
    --report-dir /tmp/tooling_vis_triptychs_legacy \
    -m <mask.pickle> -z <mtz.mtz>
  ```
- Document command in `cli_test_legacy.txt`
- If data not available, document skeleton command and note "requires manual validation with real data"
- **Do NOT run actual refinement if it takes >5 minutes** — compilation check is sufficient for this loop; full manual validation can be deferred to user testing
- Verify `/tmp/tooling_vis_triptychs_legacy/` directory created (if run completes)
- Verify PNG files present (if run completes)

**Step 6: Manual CLI Test (Torch Backend)**
- Same as Step 5 with `--backend nanobrag`
- Document in `cli_test_torch.txt`

**Step 7: Backward Compatibility Test**
- Command: `python -m dbex.refine_one --help | grep report-dir`
- Verify `--report-dir` appears in help text
- Note: Actual backward compat test (running without flag) deferred to user testing (requires full dataset)

**Step 8: Decision Synthesis**
- Write `decision.json` with 4-path decision tree:
  - **Path A (all_validations_pass)**: Compilation OK, helper logic correct (code inspection), CLI arg present → Phase B.2 ✓ COMPLETE
  - **Path B (compilation_ok_minor_issues)**: Compilation OK, helper has minor bugs → fix and re-validate
  - **Path C (hdf5_read_errors)**: HDF5 dataset access fails → debug dataset names/structure
  - **Path D (plot_triptych_api_mismatch)**: API call fails → check Phase A implementation, align arguments
- Record outcome in `decision.json` with rationale

**Step 9: Artifacts and Turn Summary**
- Write `summary.md` per Turn Summary format (3-5 sentences: what shipped, main problem/solution, next step)
- Archive all validation logs in reports directory

**Step 10: Commit**
- Message: `TOOLING-VIS-001 Phase B.2: auto-generate triptych report (--report-dir flag) — tests: manual validation`
- Git add + commit + push

## How-To Map

### Compilation Check
```bash
cd /home/ollie/Documents/diffbragg_example
python -c "from dbex.refine_one import main; print('Compilation OK')" > plans/active/TOOLING-VIS-001/reports/2025-11-24T120000Z/validation_compilation.log 2>&1
```

### Manual CLI Tests (Optional — Defer if Data Unavailable)
If golden_data exists:
```bash
# Legacy backend
python -m dbex.refine_one --backend diffbragg \
  -e golden_data/simple_cubic/expt_000000.json \
  -r golden_data/simple_cubic/indexed_000000.refl \
  -i 0 \
  -o /tmp/tooling_vis_test_legacy.h5 \
  --report-dir /tmp/tooling_vis_triptychs_legacy \
  -m golden_data/simple_cubic/mask.pickle \
  -z golden_data/simple_cubic/mtz.mtz \
  2>&1 | tee plans/active/TOOLING-VIS-001/reports/2025-11-24T120000Z/cli_test_legacy.txt

# Torch backend
python -m dbex.refine_one --backend nanobrag \
  -e golden_data/simple_cubic/expt_000000.json \
  -r golden_data/simple_cubic/indexed_000000.refl \
  -i 0 \
  -o /tmp/tooling_vis_test_torch.h5 \
  --report-dir /tmp/tooling_vis_triptychs_torch \
  -m golden_data/simple_cubic/mask.pickle \
  -z golden_data/simple_cubic/mtz.mtz \
  2>&1 | tee plans/active/TOOLING-VIS-001/reports/2025-11-24T120000Z/cli_test_torch.txt
```
**NOTE**: If refinement takes >5 minutes or golden_data unavailable, document command skeleton only and note "deferred to user testing". Compilation check is PRIMARY validation gate for this loop.

### Decision JSON Template
```json
{
  "loop": "i=273",
  "focus": "TOOLING-VIS-001",
  "phase": "B.2",
  "objective": "auto-generate triptych report",
  "validation_results": {
    "compilation_check": "PASS|FAIL",
    "cli_arg_present": "PASS|FAIL",
    "helper_function_logic": "correct|has_bugs",
    "manual_tests": "deferred|partial|pass"
  },
  "outcome": "Path A: all_validations_pass | Path B: minor_issues | Path C: hdf5_errors | Path D: api_mismatch",
  "rationale": "<brief explanation>",
  "next_action": "commit_phase_b2_complete | fix_bugs | debug_hdf5 | fix_api"
}
```

## Pitfalls To Avoid

1. **HDF5 File Still Open**: Ensure HDF5 file written by backend is closed before `_generate_triptych_report` opens it (add explicit `.close()` or verify context manager usage in backend code).
2. **Missing Variance Graceful Degradation**: Don't crash if `variance/roi%d` dataset missing (old HDF5 files); print warning and skip ROI.
3. **Large ROI Count Performance**: Don't optimize prematurely; sequential generation acceptable for Phase B.2 (progress bar is Phase B.3 enhancement if needed).
4. **API Mismatch**: Use same `plot_triptych` call pattern as `dbex/look.py` lines 174-180 (`plot_triptych(data, model, variance, filename=str(out_png))`).
5. **Absolute vs Relative Paths**: `report_dir` should support both; use `Path(report_dir).mkdir(parents=True, exist_ok=True)` to handle path creation robustly.
6. **No pytest Selectors**: This is a CLI enhancement, not core refinement logic; manual validation sufficient per galph_prompt §action_types.
7. **Environment Freeze**: Assume h5py/matplotlib/numpy already available (Phase A tests passed); do NOT propose `pip install`.
8. **Backward Compatibility**: `--report-dir` is optional (default None); existing CLI invocations without flag should work unchanged.
9. **Try/Except per ROI**: Wrap each ROI's triptych generation in try/except so one failure doesn't block the rest (e.g., malformed dataset, plot_triptych error).
10. **Print Report Location**: User needs to know where files were saved; print `f"Triptych report saved to: {report_dir}"` at end of helper.

## If Blocked

- **Blocker Type 1 (Compilation error)**: Debug import/syntax error, fix in same loop.
- **Blocker Type 2 (HDF5 structure unknown)**: Read Phase B.1 implementation in `dbex/refine_one.py` lines 236-263 (Legacy) and 665-689 (Torch) to confirm dataset names.
- **Blocker Type 3 (plot_triptych API unclear)**: Read `dbex/vis/triptych.py` and `tests/dbex/test_vis_triptych.py` to confirm API signature.
- **Blocker Type 4 (Golden data unavailable)**: Document manual test commands as "requires user data" and proceed with compilation check only (sufficient for Phase B.2 code completion).
- Record blocker in `decision.json` with `outcome="blocked"` and return to Galph.

## Findings Applied

- **POLICY-001 (Environment Freeze)**: No new dependencies; use existing h5py/matplotlib/numpy validated in Phase A.
- **PHYSICS-LOSS-001 (Variance Formula)**: Variance datasets validated in Phase B.1 per spec-db-core.md §86-90 (`V = max(I_model + sigma_readout^2, sigma_floor^2)`).
- **spec-db-vis.md §7-11 (Triptych Layout)**: 3-panel layout [Data|Model|Residuals Z-Score], colormaps viridis/seismic, origin='upper' (implemented in Phase A).
- **spec-db-vis.md §19 (Z-Score Definition)**: Z=(Data-Model)/sqrt(Variance) with NaN for masked pixels (implemented in Phase A `compute_z_scores`).
- **CLAUDE.md Incremental Progress**: Small focused enhancement (~70 lines), backward compatible (opt-in flag), delivers immediate user value.
- **CLAUDE.md Code Quality**: Clear docstring for helper function, try/except per ROI, graceful degradation for missing variance.

## Pointers

- Planning Analysis: `plans/active/TOOLING-VIS-001/reports/2025-11-24T120000Z/phase_b2_planning_analysis.md` (comprehensive scope, design decisions, code template)
- Phase A API: `dbex/vis/triptych.py::plot_triptych` (validated in `tests/dbex/test_vis_triptych.py` lines 10-50)
- Phase B.1 HDF5: `dbex/refine_one.py` lines 236-263 (Legacy), 665-689 (Torch) — variance dataset structure
- Similar Pattern: `dbex/look.py` lines 170-189 (`export_triptychs` method) — working example of ROI iteration + `plot_triptych` calls
- Spec: `docs/spec-db-vis.md` §7-11, §16-24 (triptych layout, colormaps, Z-scores)
- Implementation Plan: `plans/active/TOOLING-VIS-001/implementation.md` — Phase B checklist
- Fix Plan: `docs/fix_plan.md` lines 195-210 — TOOLING-VIS-001 status and Attempts History

## Next Up

If Phase B.2 completes successfully with all validations passing (Path A):
- **Option 1**: Phase C.1 (Refactor interactive viewer in `dbex/look.py` to use `dbex.vis` for grid layout) — 2-3 loops, MEDIUM risk
- **Option 2**: Mark TOOLING-VIS-001 as "substantial progress" (Phases A+B complete, 2/3 exit criteria satisfied) and pivot to another Tier 3 initiative
- **Option 3**: Phase B.3 enhancement (multi-page PDF report, progress bar, etc.) — LOW priority

Galph will assess Phase B.2 outcome and select next focus per Execution Roadmap and WIP cap.

## Doc Sync Plan

Not applicable (no test selectors added this loop).

## Mapped Tests Guardrail

Not applicable (manual validation only for CLI enhancement).

## Normative Math/Physics

Not applicable (no physics/math changes; uses existing Phase A `plot_triptych` API).
