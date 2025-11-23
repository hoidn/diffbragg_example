### Turn Summary (i=192 ralph)
Extracted first Stage A helper function (_build_stage_a_params, ~328 lines) from inline LBFGS closure per approved multi-loop strategy.
Helper not yet wired into runtime (no behavior change, no regression guard needed).
Compilation check PASSED, all 3 parameterization modes preserved (cell+misset, U-matrix, incremental UB).
Next loop (i=193) will extract _build_stage_a_lbfgs_closure with nested compute_loss and closure functions.
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T040000Z/ (helper1_extraction_summary.md, compilation_check.log)

### Turn Summary (supervisor)
Reviewed Ralph's Phase B1a blocker (i=191: extraction scope exceeded capacity after accidental git reversion) and approved multi-loop extraction strategy.
Split Phase B1a into 3 sub-loops: loop1 extract helper 1 only (~335 lines), loop2 extract helper 2 only (~575 lines nested functions), loop3 extract helper 3 + refactor main function + regression guard.
Authored simplified Phase B1a-loop1 Do Now for Ralph (extract `_build_stage_a_params` ONLY, compilation verification, no regression guard needed).
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T040000Z/ (summary.md), input.md (loop1 instructions), implementation.md (updated Phase B checklist with B1a-loop1/loop2/loop3 sub-phases)
