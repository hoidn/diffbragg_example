Summary: Extend Stage A warm-cache helpers and the HKL comparison probe so we capture per-panel HKL stats from both Stage A and simulate_forward_once, then document the evidence so the HKL mismatch can hand off cleanly to the next initiative.
Mode: none
InitiativeType: diagnostics
Focus: DIAG-NANOBRAGG-OVERSAMPLE-001 — nanobrag_torch Oversample Parameter Investigation
Branch: integration
Mapped tests: KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBEX_SMOKE_DETECTOR_SIZE=small pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small
Artifacts: plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-09T153000Z/

Do Now:
- Implement: dbex/refinement/stage_a_utils.py::_build_stage_a_context — add an optional `debug_config: Optional[Dict[str, Any]] = None` parameter (default None), pass it through to every `Simulator` instantiation (panel + ROI caches), and make sure the docstring/comment block notes HKL stats collection so production runs stay untouched unless the flag is set.
- Implement: plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/bin/compare_hkl_stats.py — import `RefinementConfig`, `_build_stage_a_context`, and `build_structure_factor_grid`, reuse the mapping context inputs to build a Stage A warm-cache context with `debug_config={'collect_hkl_stats': True}`, run each cached simulator once to harvest `simulator.hkl_stats`, aggregate those stats (per-panel + totals) next to the existing `simulate_forward_once` section, and update both `hkl_stats_comparison.json` and `summary.md` so they report Stage A vs mapping side-by-side.
- Document: plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/implementation.md (Phase F checklist + Attempts History), docs/fix_plan.md (DIAG-NANOBRAGG-OVERSAMPLE-001 entry), and docs/findings.md (DIAG-OVERSAMPLE-001 row) with the new Stage A vs mapping evidence and artifact path so the ledger + knowledge base match reality.
- Collect Evidence: `NANOBRAGG_DISABLE_COMPILE=1 python plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/bin/compare_hkl_stats.py --detector-size small --out-dir plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-09T153000Z/` (capture stdout to compare_hkl_stats.log, keep JSON + summary in the artifacts directory).
- Verify: `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBEX_SMOKE_DETECTOR_SIZE=small pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small` to prove the Stage A warm-cache changes remain inert outside diagnostics.

How-To Map:
1. `export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md`
2. `export ARTIFACTS=plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/reports/2025-12-09T153000Z`
3. `NANOBRAGG_DISABLE_COMPILE=1 python plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/bin/compare_hkl_stats.py --detector-size small --out-dir $ARTIFACTS > $ARTIFACTS/compare_hkl_stats.log 2>&1`
4. `KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBEX_SMOKE_DETECTOR_SIZE=small pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --smoke-detector-size=small`

Pitfalls To Avoid:
- Keep `debug_config` defaulting to None so Stage A production runs never pay for HKL stats; only the diagnostics script should enable it.
- When building the Stage A context inside the probe, reuse `RefinementConfig`/ROI-mode logic so cached simulators match what Stage A would actually construct (don’t hand-wave mask/ROI choices).
- Do not mutate `MappingStageAContext.inputs` in-place while harvesting stats; clone tensors or work on copies if you need to move them.
- Ensure the comparison script writes JSON + summary to the provided artifacts directory (no temp dirs) and that both sections clearly cite which path (Stage A vs simulate_forward_once) produced the stats.
- Stage A smoke selectors run long; pin `DBEX_SMOKE_DETECTOR_SIZE=small` and `NANOBRAGG_DISABLE_COMPILE=1` so the run matches the TESTING_GUIDE recipe and doesn’t silently flip to CUDA.

If Blocked:
- If `_build_stage_a_context` fails to instantiate with the new `debug_config`, capture the stack trace plus the inputs you passed, drop them under `$ARTIFACTS/` (e.g., `stage_a_context_failure.log`), and add a note to docs/fix_plan.md Attempts History so we know whether it’s a config or simulator regression.
- If the comparison script still only emits simulate_forward_once stats, stop after the first failure, save the partial JSON/logs, and mark DIAG-NANOBRAGG-OVERSAMPLE-001 blocked_pending_script_fix in docs/fix_plan.md so we don’t keep planning work without evidence.

Findings Applied (Mandatory):
- docs/findings.md:51 (DIAG-OVERSAMPLE-001 HKL coverage mismatch) — this loop extends the evidence with Stage A warm-cache stats.
- docs/findings.md:106 (DIAG-OVERSAMPLE-001 oversample debug history) — keep the Environment Freeze context in mind when touching Simulator instrumentation.

Pointers:
- dbex/refinement/stage_a_utils.py:180 (warm-cache helper that now needs the optional debug_config hook)
- plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/bin/compare_hkl_stats.py (Phase F probe to extend)
- plans/active/DIAG-NANOBRAGG-OVERSAMPLE-001/implementation.md (Phase F checklist + context)
- docs/fix_plan.md:166-195 (DIAG-NANOBRAGG-OVERSAMPLE-001 Attempts History)
- docs/findings.md:51 (current HKL coverage finding that needs the new artifact reference)

Next Up (optional):
1. Once Stage A vs mapping stats are captured, open ARCH-SIM-HKL-BOUNDS-001 to investigate the reciprocal-space transform / HKL grid alignment problem.
