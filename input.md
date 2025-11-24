# TORCH-REFINE-004 Phase 8: Fix Telemetry Attribute Loss in Engine Delegation

## Summary
Fix `run_nanobrag_refinement` engine delegation path to preserve Stage B custom attributes (stage_b_mode, n_asu_unique, optimizer_type, asu_modifier_stats) through the asdict()→reconstruction flow.

## Mode
none

## Focus
TORCH-REFINE-004 — Stage B Per-Reflection Mode Migration (Phase 8: Final Wrapper Bug Fix)

## Branch
integration

## Mapped tests
- `tests/dbex/test_stage_b_asu_mapping.py` (Phase 6 unit regression)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers` (shell regression)
- `tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke` (per-reflection E2E, MUST PASS)

## Artifacts
`plans/active/TORCH-REFINE-004/reports/2025-11-24T103302Z/`

## Do Now

**Context:** Ralph's Phase 8 wrapper fixes (commit 6705471) correctly implemented custom attribute serialization in wrapper + engine, but `run_nanobrag_refinement`'s engine delegation path loses attributes when calling `asdict()` → `RefinementTelemetry(**dict)`. Root cause: `asdict()` only serializes dataclass fields, NOT arbitrary attributes added after construction (see `phase_8_final_blocker_analysis.md` lines 40-52).

**Implement:** Fix `dbex/nanobrag_refinement.py:4904-4916` to preserve custom attributes:

1. **Read planning analysis:**
   - `plans/active/TORCH-REFINE-004/reports/2025-11-24T103302Z/phase_8_final_blocker_analysis.md`
   - Focus on "Fix Specification" section (lines 54-133) and "Alternative: Simpler Pattern" (lines 109-123)

2. **Apply Alternative pattern fix** (recommended: simpler, less error-prone):
   - Location: `dbex/nanobrag_refinement.py:4904-4916` (for-loop over `engine_telemetry.items()`)
   - **REPLACE** lines 4909-4914 with:
     ```python
     for stage_name, telem_obj in engine_telemetry.items():
         # Add engine protocol fields directly to existing object (preserves custom attrs)
         telem_obj.engine_protocol = engine_protocol
         telem_obj.stage_modes = stage_modes

         legacy_key = stage_name_map.get(stage_name, stage_name)
         telemetry_out[legacy_key] = telem_obj  # Use original object, preserve custom attrs
     ```
   - **Rationale:** Engine already restored custom attributes (engine.py:161-168); this pattern avoids asdict() entirely and preserves all engine work.

3. **Validation protocol (4 tests):**
   ```bash
   # Compilation check
   python -c "from dbex.refinement.stage_b import StageB; print('OK')"

   # Phase 6 unit regression (no changes expected)
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   DBEX_SMOKE_DETECTOR_SIZE=small \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -xvs tests/dbex/test_stage_b_asu_mapping.py \
     > plans/active/TORCH-REFINE-004/reports/2025-11-24T103302Z/pytest_phase6_regression.log 2>&1

   # Shell mode regression (no changes expected)
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   DBEX_SMOKE_DETECTOR_SIZE=small \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -xvs tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers \
     > plans/active/TORCH-REFINE-004/reports/2025-11-24T103302Z/pytest_shell_regression.log 2>&1

   # Per-reflection smoke (TARGET: MUST PASS)
   AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
   DBEX_SMOKE_SIGMA_SOURCE=cli_override \
   DBEX_SMOKE_DETECTOR_SIZE=small \
   KMP_DUPLICATE_LIB_OK=TRUE \
   NANOBRAGG_DISABLE_COMPILE=1 \
   pytest -xvs tests/dbex/test_torch_refine_smoke.py::test_stage_b_per_reflection_smoke \
     > plans/active/TORCH-REFINE-004/reports/2025-11-24T103302Z/pytest_per_reflection_smoke.log 2>&1
   ```

4. **Decision synthesis:**
   - **Path A (SUCCESS):** All 4 tests PASS (5/5 Phase 6 unit, shell regression PASS, per-reflection E2E PASS)
     - Action: Write `decision.json` with `"outcome": "success"`, `"tests_passed": "4/4"`, `"phase_8_status": "complete"`
     - Mark Phase 8 ✓ COMPLETE
     - Next: Return to Galph for Phase 9 planning (default enforcement + docs)

   - **Path B (PARTIAL):** Per-reflection test still fails but error changed (progress made)
     - Action: Write `decision.json` with `"outcome": "partial"`, `"blocker": "<new error text>"`, `"hypothesis": "<root cause guess>"`
     - Capture full pytest output (last 100 lines) in `decision.json` for Galph triage
     - Do NOT attempt further fixes; escalate to Galph

   - **Path C (REGRESSION):** Phase 6 unit or shell regression fails (new bug introduced)
     - Action: Write `decision.json` with `"outcome": "regression"`, `"failed_test": "<test selector>"`, `"error": "<traceback>"`
     - Revert changes, return to Galph with blocker report

   - **Path D (SYNTAX):** Compilation fails (Python syntax error)
     - Action: Fix syntax error immediately (typo/indentation), rerun validation
     - If 2nd attempt fails, revert and escalate to Galph

5. **Write summary.md:**
   - Use Turn Summary template (3-5 sentences: what shipped/advanced, main problem + handling, next step, Artifacts line)
   - Prepend to existing `plans/active/TORCH-REFINE-004/reports/2025-11-24T103302Z/summary.md` (or create if missing)

6. **Commit:**
   ```bash
   git add -A
   git commit -m "TORCH-REFINE-004 Phase 8: Fix telemetry attribute loss (asdict preservation) — tests: per-reflection PASS"
   git push
   ```

## How-To Map

```bash
# Step 1: Read analysis
cat plans/active/TORCH-REFINE-004/reports/2025-11-24T103302Z/phase_8_final_blocker_analysis.md

# Step 2: Apply fix (REPLACE lines 4909-4914 in dbex/nanobrag_refinement.py)
# Use Edit tool with old_string = lines 4909-4914 (from "for stage_name, telem_obj" to "telemetry_out[legacy_key] = RefinementTelemetry(**telem_dict)")
# new_string = Alternative pattern (7 lines, see Do Now step 2)

# Step 3: Validation (4 tests, see Do Now step 3)

# Step 4: Decision synthesis (see Do Now step 4)

# Step 5: Write summary.md (see Do Now step 5)

# Step 6: Commit (see Do Now step 6)
```

## Pitfalls To Avoid

1. **DO NOT** use 3-part fix pattern (Part 1-3 in analysis) — use Alternative pattern (simpler, recommended)
2. **DO NOT** modify engine.py or stage_b.py — fix is ONLY in nanobrag_refinement.py lines 4909-4914
3. **DO NOT** call asdict() in the fix — Alternative pattern avoids asdict() entirely
4. **DO NOT** mutate `stage_modes` dict based on actual modes — keep existing logic (line 4854 hardcodes "shell")
5. **DO NOT** attempt multiple fix iterations — if Path B/C/D occurs, escalate to Galph immediately
6. **Environment Freeze:** No installs, code-only fix

## If Blocked

1. Capture full error traceback (last 100 lines of pytest output)
2. Write `decision.json` with `"outcome": "blocked"`, `"error": "<traceback>"`, `"hypothesis": "<guess>"`
3. Append to Attempts History with timestamp, blocker description, artifacts path
4. Return to Galph with blocker report (do NOT attempt workarounds)

## Findings Applied

- **POLICY-001:** Environment Freeze ✓ (code-only fix)
- **ARCH-ENGINE-002:** Lazy imports ✓ (no import changes)
- **ARCH-REFINE-FLOW-001:** Engine delegation pattern ✓ (fix preserves engine contract, custom attributes restored per engine.py:161-168)
- **REFINE-001/002/005:** Scale warm-start, acceptance gate, halo mandatory ✓ (no changes to refinement logic)
- **spec:59/60/61/107:** Per-reflection SHALL be default (Phase 9), shell fallback permitted ✓, halo mandatory ✓, Adam for large param counts ✓

## Pointers

- Root cause analysis: `plans/active/TORCH-REFINE-004/reports/2025-11-24T103302Z/phase_8_final_blocker_analysis.md`
- Fix target: `dbex/nanobrag_refinement.py:4904-4916` (engine delegation telemetry enrichment block)
- Engine attribute restoration: `dbex/refinement/engine.py:161-168` (reference for what attributes to preserve)
- Wrapper attribute assignment: `dbex/refinement/stage_b.py:456-475` (reference for what attributes are added)
- Test specification: `tests/dbex/test_torch_refine_smoke.py:1640-1698` (per-reflection smoke test exit criteria)
- Planning analysis: `plans/active/TORCH-REFINE-004/reports/2025-11-24T092549Z/phase_7_planning_analysis.md` (Phase 7 integration background)

## Next Up

**After Phase 8 SUCCESS (Path A):**
- Galph plans Phase 9: Default enforcement + E2E validation + docs
- Scope: Change RefinementConfig default `stage_b_mode="per_reflection"` (1-line), update CLI help text, refresh docs/TESTING_GUIDE.md + TEST_SUITE_INDEX.md
- Estimated effort: 1-2 loops (~2-3 hours)

**After Phase 8 BLOCKED (Path B/C):**
- Galph triages new blocker, assesses whether fix attempt #3 is viable or escalation required per repeat-failure enforcement
- Options: (A) Reclassify root cause + new implementation fix, (B) Weaken test assertion (NOT ALLOWED per spec:59), (C) Mark TORCH-REFINE-004 blocked pending upstream fix
