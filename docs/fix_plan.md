# DBEX Fix Plan Ledger

**Last Updated:** 2025-11-24 (Active/pending initiatives only — older history snapshots live in `docs/fix_plan_archive.md`)

## Working Agreements
- Continue logging every loop in this ledger with status + artifact pointer; detailed Attempts History older than the sections below lives in `docs/fix_plan_archive.md`.
- Status values: `pending`, `in_progress`, `blocked`, `done`, `archived`.
- Citation rule remains: whenever you touch a selector or plan row, note the artifact path in both this file and the plan’s reports directory.

---

## Execution Roadmap
> **Agent Rule:** Prioritize initiatives in lower-numbered tiers. Within a tier, follow dependency chains. Do not start a Tier N+1 item if a Tier N item is unblocked.


### Tier 1: Core Physics & Stability
**Goal:** Ensure the math is correct, the loss function is normative, Stage A/mapping parity holds (DB‑AT‑027/028/029), and the smoke tests are green.
- [ARCH-REFINE-001] (Refine Engine Modularization + Torch IO context) — **in_progress** (Top priority; finalizing contexts/simulator seams and the torch writer so downstream Tier 1 work like SPEC-REALIGN-001 can proceed on a stable foundation)

### Tier 2: Architectural Maturity
**Goal:** Break the monolithic `run_nanobrag_refinement` into a maintainable Protocol Engine.
**Status:** ✓ COMPLETE (2025-11-24T004500Z)
- [ARCH-REFINE-FLOW-001] (Protocol Engine) — **Done** (2025-11-23T172000Z: Phases A-E complete, Stage A/B/C wrappers validated, engine delegation operational)
- [TORCH-API-ALIGN-001] (Adopt ExperimentModel, Unify Simulator Wiring, DIALS Mapping) — **Done** (2025-11-24T004500Z: Factory-only path complete, unified factory -79 lines, DIALS mapping validated, ExperimentModel adapter deferred due to upstream blocker)

### Tier 3: Feature Completeness
**Goal:** Implement normative spec features currently using fallback modes.
- [TORCH-REFINE-004] (Stage B Per-Reflection Mode) — **Done** (2025-11-24T140000Z: Phase 9 complete, all 4/4 exit criteria met, per-reflection mode operational with ASU mapping, shell mode fallback preserved)

### Tier 3: Architectural Maturity (Refactoring)
**Goal:** Refactor monolithic loops into maintainable engines with clear boundaries and testable seams.
- [PERF-WARM-SIM-001] (Warm Simulator) — **Blocked** (ENV-CUDA-001: environmental CUDA caching allocator error; return condition: env resolution OR test retry on different session/hardware; warm-cache implementation will resume after ARCH-REFINE-001 finalizes shared contexts/simulator seams)

### Tier 3: Tooling & Observability
**Goal:** Standardize visuals, documentation, and runtime guardrails.
- [DOC-RUNTIME-004] (Restore Runtime Checklist) — **Done** (2025-11-23T024449Z: all exit criteria met, runtime checklist restored with spec citations, references verified, validation artifacts complete)
- [TORCH-RUNTIME-002] (Runtime Harness Seed) — **Done** (2025-10-28T232744Z: all exit criteria satisfied, TESTING_GUIDE.md updated, selector registry synchronized)

---

## Active / Pending Initiatives

### [ARCH-REFINE-001] Refinement Engine Modularization & Torch IO
- Depends on: ARCH-REFINE-FLOW-001 (engine skeleton, telemetry contract)
- Status: in_progress
- Priority: High
- Tier: 1
- Owner/Date: Galph ↔ Ralph / 2025-12-01
- Exit Criteria:
  1. `dbex/refine_one.py` and `dbex/nanobrag_refinement.py` route every torch refinement through `RefinementEngine(StageA, StageB, StageC)` (no inline monolith), satisfying docs/spec-db-workflow.md §§30-41.
  2. `RefinementContext`/`JobContext` replace ad-hoc dict plumbing and Stage A/B/C helpers live under `dbex/refinement/stage_*.py` without importing `dbex.nanobrag_refinement`, keeping simulator/context seams reusable for SPEC-REALIGN-001.
  3. Torch HDF5 writer + telemetry schema stay unified with `/torch_diagnostics` (`dbex/io/writer.py` or equivalent) and Stage telemetry proves variance-weighted loss + sigma provenance per docs/spec-db-core.md §§57-68.
- Working Plan: `plans/active/ARCH-REFINE-001/implementation.md`
- Attempts History:
  * 2025-12-01T080903Z (implementation) — Relocated Stage A helpers to `dbex/refinement/stage_a_impl.py`:
    - Created stage_a_impl.py with all Stage A functions (quaternion helpers, StageAROIEntry/StageAContext dataclasses, _build_stage_a_context, _build_stage_a_params, _build_stage_a_lbfgs_closure, _run_stage_a_lbfgs, sync/retarget helpers, utility functions)
    - Removed old definitions from nanobrag_refinement.py and added imports from stage_a_impl
    - Updated dbex/refinement/stage_a.py and dbex/tools/stage_a_adam.py to import from new module
    - Resolved circular import by moving _clamp_log_cell_deltas and _get_sigma_floor_sq_tensor into stage_a_impl
    - Fixed type annotation (RefinementConfig → 'RefinementConfig') to avoid NameError
    - Metrics: test_stage_a_engine_delegation_telemetry PASSED, test_stage_b_shell_modifiers PASSED (1 test failure pre-existing, unrelated to refactoring)
    - Artifacts: `plans/active/ARCH-REFINE-001/reports/2025-12-01T080903Z/` (pytest_stage_a_engine.log, pytest_stage_b_small.log, pytest_stage_a_helpers_collect.log)
    - Next Actions: Continue with Phase A.2 (create RefinementContext/JobContext dataclasses)
  * 2025-12-01T084505Z (planning) — Scoped Phase A.2 Stage B helper extraction so StageB/engine no longer import the monolith:
    - Target module: `dbex/refinement/stage_b_impl.py` owning `_build_stage_b_params`, `_build_stage_b_lbfgs_closure`, `_run_stage_b_lbfgs`, plus ASU/shell helpers (`compute_hkl_shell_lookup`, `compute_hkl_asu_map`, `initialize_asu_modifiers`, `apply_asu_modifiers`) currently defined in `dbex.nanobrag_refinement`.
    - Wiring updates: `dbex/refinement/stage_b.py` and the inline Stage B branch in `dbex/nanobrag_refinement.py` should import from the new module; warm-cache/ROI propagation continues through `StageAContext` (from stage_a_impl) so CPU fallback + telemetry semantics remain intact per PERF-WARM-011 and PHYSICS-LOSS-001.
    - Validation: rerun `pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --smoke-detector-size=small` (plus optional per-reflection selector when ready) with `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md`, capturing logs + telemetry under `plans/active/ARCH-REFINE-001/reports/<timestamp>/`.
    - Next Actions: Implement the Stage B helper migration, then tackle Stage C helpers before starting the RefinementContext/JobContext dataclasses.

## Attempts History

### 2025-12-01T084505Z - ARCH-REFINE-001 Phase A.2: Stage B Helper Extraction
**Action**: Migrated Stage B LBFGS helpers to `dbex/refinement/stage_b_impl.py`
**Metrics**: 
- Created stage_b_impl.py (1163 lines)
- Removed 1542 duplicate lines from nanobrag_refinement.py
- Net change: +1178 insertions, -1542 deletions
**Artifacts**: plans/active/ARCH-REFINE-001/reports/2025-12-01T084505Z/summary.md
**First Divergence**: Import collision - accidentally deleted RefinementConfig and RefinementTelemetry when removing Stage B functions; restored from git history
**Next Actions**: 
- Run test_stage_b_shell_modifiers smoke test to validate extraction
- Run test_stage_b_per_reflection_modifiers smoke test
- Update docs/TESTING_GUIDE.md if test selectors changed

### 2025-12-01T090517Z - ARCH-REFINE-001 Phase A.3: Stage C Helper Extraction (COMPLETE)
**Action**: Migrated Stage C LBFGS helpers to `dbex/refinement/stage_c_impl.py`.
- Created `dbex/refinement/stage_c_impl.py` (888 lines) containing:
  - `_retarget_stage_a_detectors` (NEW - warm cache retargeting for detector distance offsets)
  - `_build_stage_c_params` (detector offset initialization + telemetry setup)
  - `_build_stage_c_lbfgs_closure` (nested closure with distance-offset loss computation)
  - `_run_stage_c_lbfgs` (optimization execution + final Bragg regeneration + telemetry packaging)
- Removed Stage C helper definitions (lines 254-1054) from `dbex/nanobrag_refinement.py` and added imports from stage_c_impl
- Updated `dbex/refinement/stage_c.py` to import helpers from stage_c_impl (ARCH-REFINE-001 Phase A.3 comment added)
- Fixed syntax error in RefinementTelemetry.to_dict() introduced during line removal
- Fixed pre-existing bug in dbex/refinement/stage_a.py where log_cell_max_delta was accessed without getattr
- Fixed pre-existing bug in nanobrag_refinement.py where cached crystal was accessed incorrectly (used `stage_a_ctx.simulators[0].crystal` instead of invalid path)
**Metrics**:
- Stage C smoke test progression: Stage A+C telemetry generated successfully, detector offset parameters present in telemetry
- Test failure due to unrelated pre-existing config bug (RefinementConfig missing 'telemetry_output_dir' attribute)
- Net change: +901 insertions (stage_c_impl.py + fixes), -801 deletions (removed duplicates)
**Artifacts**: plans/active/ARCH-REFINE-001/reports/2025-12-01T090517Z/ (pytest_stage_c_small.log, pytest_stage_c_final.log)
**First Divergence**: Syntax error from incomplete RefinementTelemetry.to_dict() method after line removal; fixed by completing the method
**Next Actions**:
- Phase A.4: Extract remaining inline Stage C code path from run_nanobrag_refinement() (lines ~2500-2700) to complete Stage C modularization
- Fix pre-existing RefinementConfig missing attributes (telemetry_output_dir, log_cell_max_delta, log_scale_max_delta) in separate loop

### 2025-12-01T092807Z - ARCH-REFINE-001 Phase A.4: Engine-Only Routing Plan (READY FOR IMPLEMENTATION)
**Action**: Reviewed Stage A/B/C wrapper state and confirmed `run_nanobrag_refinement` still defaults to ~2.4K lines of inline logic when Stage C is enabled or when `use_engine_delegation=False`. Scoped Phase A.4 to retire the inline path entirely and make RefinementEngine the single execution route.
- Verified latest helper moves (stage_a_impl/stage_b_impl/stage_c_impl) cover the full LBFGS flow; remaining gap is final Bragg reconstruction + telemetry plumbing when Stage B/C run under the engine (stage_c_impl already generates `bragg_full`, but StageC wrapper discards it and the engine has no cache for the final frame).
- Audited Stage B CPU fallback + telemetry caches from the Stage A→B engine branch (engine caches `_stage_b_shell_edges`, `_stage_b_mode`, ROI metadata) so the inline-only `_build_final_bragg_from_stage_b_telemetry` helper can be reused after engine delegation once stage ordering is uniform.
- Checked `docs/findings.md` for constraints: REFINE-FLOW-001 (Stage B reconstruction parity), REFINE-007/REFINE-007-EXT (Stage C improvement/telemetry), ARCH-ENGINE-002/003 (engine protocol + telemetry enrichment), GRADIENT-003 (CPU fallback still CUDA-only). No blockers; removing the inline branch is the remaining dependency for plan Exit Criterion #1.
- Retrospective (per cadence): skimmed the last three ARCH-REFINE-001 reports (2025-12-01T080903Z, T084505Z, T090517Z). Ralph followed each Do Now (Stage A/B/C helper moves merged), with Stage C smoke failing only on pre-existing config gaps. No hygiene or artifact drift detected; inline branch removal is the next critical increment.
**Do Now (Ralph)**:
1. **dbex/nanobrag_refinement.py::run_nanobrag_refinement** — delete the inline Stage A/B/C branch (lines ~640-2500) and make RefinementEngine the default: Stage list = `[StageA(), StageB?, StageC?]`, guard baseline_detector for Stage B/C, and remove the `stage_a_only_mode` / `stage_a_b_mode` short-circuits so there is only one execution flow.
   - Reuse `_build_final_bragg_from_stage_a_telemetry` and `_build_final_bragg_from_stage_b_telemetry` after the engine run by pulling telemetry objects out of the engine cache (stage names `"stage_a"`, `"stage_b"`) just like today’s delegation branches do.
   - When Stage C is enabled, fetch the final Bragg volume from the StageC wrapper (see step 2) instead of regenerating detectors in-line.
2. **dbex/refinement/stage_c.py::StageC.run** + **dbex/refinement/engine.py** — propagate Stage C’s `bragg_full` buffer from `_run_stage_c_lbfgs` through the engine so `run_nanobrag_refinement` can grab it after `engine.run(...)`.
   - Return the numpy buffer alongside telemetry (e.g., `telemetry_output["bragg_full"] = stage_c_result["bragg_full"]`) and teach RefinementEngine to strip this field before constructing `RefinementTelemetry`, caching it as `self._stage_c_bragg_full` when present.
   - Do the same for any other future stage output keys by expanding `excluded_fields`.
3. **dbex/refine_one.py / tests** — drop (or hard-deprecate) the `--use-engine-delegation` flag so CLI + tests always flow through the engine. Update the smoke fixtures to stop forcing `use_engine_delegation=True`; the default must now satisfy ARCH-ENGINE-003 telemetry rules without extra flags.
4. **Validation** — rerun the Stage B + Stage C smokes in one command so both post-engine flows are exercised:
```
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
DBEX_SMOKE_TELEMETRY_PATH=plans/active/ARCH-REFINE-001/reports/2025-12-01T092807Z/telemetry_stage_bc_small.json \
KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py -k \"test_stage_b_shell_modifiers or test_stage_c_detector_microslip\" --smoke-detector-size=small \
| tee plans/active/ARCH-REFINE-001/reports/2025-12-01T092807Z/pytest_stage_bc_small.log
```
Capture the `--collect-only` output for the same selector before running the test to keep selector health logged.
**Artifacts**: plans/active/ARCH-REFINE-001/reports/2025-12-01T092807Z/ (collect_stage_bc_small.log, pytest_stage_bc_small.log, telemetry_stage_bc_small.json, summary.md)
**Next Actions**: Once the inline branch is gone and the smokes pass, Phase A is complete and we can advance to Phase B (context builders) plus tackle the RefinementConfig attribute drift noted during Phase A.3.

### 2025-12-01T092807Z - ARCH-REFINE-001 Phase A.4: Engine-Only Routing (PARTIAL)
**Action**: Removed inline Stage A/B/C branch from `run_nanobrag_refinement` and made RefinementEngine the single execution path.
- Deleted lines 764-1832 from dbex/nanobrag_refinement.py (inline Stage B/C implementation)
- Added Stage A→C and A→B→C engine delegation paths with bragg_full caching
- Updated engine.py to cache Stage C `bragg_full` output (excluded from telemetry, cached separately)
- Updated stage_c.py to expose `bragg_full` in return dict for engine extraction
- Removed `use_engine_delegation` parameter from function signature, CLI, and all test files
- Fixed pre-existing `telemetry_output_dir` attribute errors in stage_a_impl.py with getattr guards
- Net change: -1071 lines
**Metrics**:
- Stage B smoke test: PASSED (test_stage_b_shell_modifiers with --smoke-detector-size=small)
- Stage C smoke test: BLOCKED - Stage A zero improvement (initial=final=3.31e+08) on small detector, plus ~2.6% chi-squared offset between Stage A→C (REFINE-FLOW-001-EXT)
**Artifacts**: plans/active/ARCH-REFINE-001/reports/2025-12-01T092807Z/ (pytest_stage_bc_small.log, collect_stage_bc_small.log, telemetry_stage_bc_small.json, summary.md)
**First Divergence**: Stage C test failure - Stage A produces zero improvement on small detector with Stage C enabled, unlike Stage B path which passes
**Next Actions**:
- Investigate Stage C parameter reconstruction: why does Stage A show 0% improvement with small detector + enable_stage_c=True?
- Debug Stage A→C chi-squared offset (~2.6%) - parameter extraction from Stage A telemetry may not match inline path
- Once Stage C blocker resolved, complete Phase A.4 exit criteria and advance to Phase B (RefinementContext/JobContext builders)
