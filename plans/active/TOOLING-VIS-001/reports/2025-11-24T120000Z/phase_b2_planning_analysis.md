# TOOLING-VIS-001 Phase B.2 Planning Analysis
**Date:** 2025-11-24T120000Z
**Focus:** Phase B.2 — Auto-Generate Summary Report in `refine_one.py`
**Type:** Planning

## Context

**Phase A ✓ COMPLETE** (2025-11-24T111500Z): Core visualization library (`dbex.vis` module) with `plot_triptych` and `compute_z_scores` validated (3/3 tests PASSED).

**Phase B.1 ✓ COMPLETE** (2025-11-24T115000Z): Variance HDF5 extension implemented in both Legacy and Torch backends, saving `variance/roi%d`, `sigma_readout`, `sigma_floor` datasets per spec-db-core.md §86-90.

**Phase B.2-lite ✓ COMPLETE** (2025-11-24T115000Z): Static triptych export capability added to `dbex/look.py` via `--export-triptychs <dir>` flag.

**Remaining Work:** Original implementation.md Phase B.2 ("Update `dbex/refine_one.py` to generate a static report on exit") is still pending. This is the **auto-generate summary report** feature that produces triptych PNGs automatically without manual `dbex.look` invocation.

## Objective

Add optional `--report-dir <path>` flag to `dbex/refine_one.py` CLI that, when specified, automatically calls `dbex.vis.plot_triptych` for all ROIs after refinement completes, producing a standard visual report.

## Scope Analysis

### Implementation Locations

1. **CLI Argument** (`dbex/refine_one.py`):
   - Add `--report-dir` argparse argument (optional, default None)
   - Location: ~line 30-60 (argparse section)
   - Estimated: 5-10 lines

2. **Report Generation Helper**:
   - New function `_generate_triptych_report(h5_path, report_dir)` that:
     - Opens HDF5 file (read-only)
     - Iterates over ROIs (read `data/roi%d`, `model/roi%d`, `variance/roi%d`)
     - Calls `dbex.vis.plot_triptych` for each ROI
     - Creates `report_dir` if it doesn't exist
   - Location: End of `dbex/refine_one.py` (~line 250-300)
   - Estimated: 40-50 lines

3. **Main Function Integration**:
   - Call `_generate_triptych_report` after HDF5 write, before script exit
   - Location: Legacy backend ~line 270, Torch backend ~line 690
   - Estimated: 6-10 lines (2 call sites with conditional check)

**Total Code:** ~55-70 lines

### Design Decisions

**Q1: Should `--report-dir` be backend-specific or unified?**
**A:** Unified. Both Legacy and Torch backends write the same HDF5 structure (after Phase B.1 variance extension), so the report generation logic can be identical.

**Q2: Should report generation happen inside or outside the backend-specific code?**
**A:** Outside. Extract HDF5 path from backend returns, call report generation helper in `main()` after backend completes. This keeps backends clean and makes the feature optional/pluggable.

**Q3: What happens if variance datasets are missing (e.g., old HDF5 files)?**
**A:** Helper should gracefully degrade or skip ROIs with missing variance. Add try/except around variance read, log warning, use fallback (e.g., `variance=None` → skip Z-score panel in triptych). However, since Phase B.1 ensures variance is saved, this should not occur for new runs.

**Q4: Should we generate a single multi-page PDF or individual PNG files?**
**A:** Individual PNG files (one per ROI), matching the `dbex/look.py --export-triptychs` pattern. Multi-page PDF is a Phase B.3 enhancement if desired.

**Q5: Filename convention?**
**A:** `roi_{idx:04d}_triptych.png` to match `dbex/look.py` export pattern.

**Q6: Should the CLI print the report directory location?**
**A:** Yes. Add `print(f"Triptych report saved to: {report_dir}")` after generation completes.

### Code Template (Pseudocode)

```python
# dbex/refine_one.py

def _generate_triptych_report(h5_path: str, report_dir: str) -> None:
    """Generate triptych PNGs for all ROIs in HDF5 file."""
    from pathlib import Path
    from dbex.vis import plot_triptych
    import h5py

    report_path = Path(report_dir)
    report_path.mkdir(parents=True, exist_ok=True)

    with h5py.File(h5_path, 'r') as h5:
        # Determine number of ROIs
        n_rois = 0
        while f"data/roi{n_rois}" in h5:
            n_rois += 1

        if n_rois == 0:
            print("Warning: No ROIs found in HDF5 file, skipping triptych report.")
            return

        for roi_idx in range(n_rois):
            try:
                data = h5[f"data/roi{roi_idx}"][:]
                model = h5[f"model/roi{roi_idx}"][:]
                variance = h5[f"variance/roi{roi_idx}"][:] if f"variance/roi{roi_idx}" in h5 else None

                if variance is None:
                    print(f"Warning: Variance missing for ROI {roi_idx}, skipping.")
                    continue

                out_png = report_path / f"roi_{roi_idx:04d}_triptych.png"
                plot_triptych(data, model, variance, filename=str(out_png))
            except Exception as e:
                print(f"Warning: Failed to generate triptych for ROI {roi_idx}: {e}")
                continue

    print(f"Triptych report saved to: {report_dir}")

# In main():
def main():
    # ... existing argparse ...
    parser.add_argument('--report-dir', type=str, default=None,
                        help='Optional directory to save triptych report (PNG per ROI)')

    # ... run legacy or torch backend ...
    if args.backend == 'diffbragg':
        # ... existing legacy code ...
        # After HDF5 write:
        if args.report_dir:
            _generate_triptych_report(args.out, args.report_dir)
    else:
        # ... existing torch code ...
        # After HDF5 write:
        if args.report_dir:
            _generate_triptych_report(args.out, args.report_dir)
```

## Validation Strategy

**No pytest selectors required** for this feature (Phase B.2 is CLI enhancement, not core refinement logic).

**Validation Protocol:**
1. **Compilation Check**: `python -c "from dbex.refine_one import main; print('Compilation OK')"`
2. **Manual CLI Test** (Legacy backend):
   ```bash
   python -m dbex.refine_one --backend diffbragg \
     -e <expt.json> -r <refl.refl> -i 0 \
     -o /tmp/test_report.h5 \
     --report-dir /tmp/test_triptychs \
     <other required flags>
   ```
   - Verify `/tmp/test_triptychs/` exists with `roi_0000_triptych.png`, etc.
   - Verify PNG files are valid (can be opened with image viewer)
   - Verify CLI prints "Triptych report saved to: /tmp/test_triptychs"
3. **Manual CLI Test** (Torch backend):
   - Same as above with `--backend nanobrag`
4. **Backward Compatibility**: Run without `--report-dir` flag, verify no errors (feature is opt-in)

**Decision Paths:**
- **Path A (All validations PASS)**: Phase B.2 ✓ COMPLETE, commit, proceed to Phase C planning or mark TOOLING-VIS-001 substantial progress.
- **Path B (Compilation OK, manual tests show minor issues)**: Fix issues in same loop, re-validate.
- **Path C (HDF5 read errors)**: Debug helper logic, ensure variance datasets are accessed correctly.
- **Path D (plot_triptych errors)**: Check Phase A implementation, ensure API contract matches.

## Risk Analysis

| Risk | Severity | Mitigation |
|------|----------|------------|
| **R1: Missing variance datasets in old HDF5 files** | LOW | Graceful degradation with warning message (try/except around variance read). Phase B.1 ensures new runs have variance. |
| **R2: Large number of ROIs (e.g., 1000+) makes report generation slow** | LOW | Acceptable for Phase B.2; optimization (parallel generation, progress bar) is Phase B.3 enhancement. Print progress message per 10 ROIs if needed. |
| **R3: HDF5 file still open when report generation tries to read** | MEDIUM | Ensure HDF5 file is closed before calling report generation (add explicit `h5.close()` or use context manager). |
| **R4: plot_triptych API mismatch (e.g., expects different arguments)** | LOW | Phase A validated `plot_triptych` API in tests. Use same call pattern as `dbex/look.py --export-triptychs`. |

## Estimated Effort

- **Implementation**: 1.5 hours (CLI arg 15 min, helper function 1 hour, integration 15 min)
- **Validation**: 1 hour (compilation check 5 min, manual tests 45 min, backward compat 10 min)
- **Documentation**: 15 min (update `docs/index.md` CLI usage example, inline docstring)
- **Total**: ~2.5 hours (single loop feasible)

## Confidence

**HIGH (~85%)**

**Rationale:**
- Clear scope (add CLI flag + helper function)
- Phase A API (`plot_triptych`) already validated
- Phase B.1 HDF5 structure known and stable
- Manual validation sufficient (no pytest complexity)
- Similar pattern exists in `dbex/look.py --export-triptychs`

## Applied Findings

- **POLICY-001 (Environment Freeze)**: No new dependencies, uses existing h5py/matplotlib/numpy.
- **PHYSICS-LOSS-001 (Variance Formula)**: Variance datasets validated in Phase B.1 per spec-db-core.md §86-90.
- **spec-db-vis.md §7-11/16-23**: Triptych layout, colormaps, Z-score definition (already implemented in Phase A).
- **CLAUDE.md Incremental Progress**: Small, focused enhancement (~70 lines), backward compatible (opt-in flag).

## Exit Criteria (Phase B.2 Specific)

1. `--report-dir <path>` CLI flag added to `dbex/refine_one.py` argparse.
2. Helper function `_generate_triptych_report` implemented and integrated into both Legacy and Torch backends.
3. Compilation check passes.
4. Manual CLI tests (Legacy + Torch backends) produce valid triptych PNGs in specified directory.
5. Backward compatibility validated (runs without `--report-dir` flag succeed unchanged).
6. CLI prints report directory location after generation.

## Next Actions

Ralph executes Phase B.2 implementation per 10-step protocol:
1. Read this planning analysis
2. Add `--report-dir` argparse argument to `dbex/refine_one.py`
3. Implement `_generate_triptych_report` helper function (~40-50 lines)
4. Integrate helper calls in main() for both backends (~6-10 lines)
5. Run compilation check: `python -c "from dbex.refine_one import main; print('Compilation OK')"`
6. Manual CLI test (Legacy backend) with smoke test data (if available) or document command for future validation
7. Manual CLI test (Torch backend) similarly
8. Backward compatibility test (no `--report-dir` flag)
9. Decision synthesis (Path A/B/C/D)
10. Commit with message "TOOLING-VIS-001 Phase B.2: auto-generate triptych report (--report-dir flag) — tests: manual validation"

---

**Estimated delivery:** Single loop (~2.5 hours)
**Confidence:** HIGH (~85%)
**Dwell status:** dwell=0 planning (first planning loop for Phase B.2 after Phase B.1+B.2-lite completion)
**Implementation Floor:** Next loop MUST be ready_for_implementation per max-1-docs-only-loop rule.
