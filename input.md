# TORCH-REFINE-004 Phase 6 Planning — Per-Reflection ASU Mapping & Parameterization Design

## Summary
Design per-reflection Fhkl modifier parameterization with ASU (asymmetric unit) index mapping for Stage B, assess parameter counts, and recommend optimizer choice (LBFGS vs Adam) based on parameter scale.

## Mode
**Docs**

## Focus
**TORCH-REFINE-004 — Stage B Per-Reflection Mode Migration (Phase 6: ASU Mapping & Parameterization Planning)**

## Branch
`integration` (expected working branch)

## Mapped Tests
**None — evidence-only** (planning loop, no code changes)

## Artifacts
**Directory:** `plans/active/TORCH-REFINE-004/reports/2025-11-24T125000Z/`

**Expected Outputs:**
- `phase_6_planning_analysis.md` — Comprehensive ASU mapping design (algorithm, cctbx API usage, parameter count estimates, optimizer recommendation, risk mitigation)
- `asu_pseudocode.py` — Pseudocode for ASU index computation (NOT production code, just design sketch)
- `parameter_count_analysis.md` — Estimates for common space groups (P1, P21, P432, etc.) with justification
- `optimizer_decision.md` — LBFGS vs Adam trade-off analysis with memory/convergence considerations
- `decision.json` — 4-path decision synthesis (A: proceed to Phase 6 implementation, B: refine design, C: blocked by cctbx unavailable, D: fallback to shell mode only)
- `summary.md` — Turn Summary (per end-of-loop hygiene requirements)

## Do Now

**Objective:** Plan Phase 6 per-reflection parameterization design WITHOUT writing production code. This is a pure planning loop to answer 4 key questions before implementation:

1. **ASU Mapping Algorithm:** How do we compute `hkl_asu_map: torch.Tensor[int64]` shape `(h_count, k_count, l_count)` mapping each HKL grid voxel to its unique ASU index?
2. **Parameter Count:** How many unique ASU reflections exist for typical space groups (P1, P21, P432, etc.) and test fixtures?
3. **Optimizer Choice:** Should Stage B use LBFGS (spec default) or Adam (spec-permitted for large parameter counts)?
4. **Risk Mitigation:** How do we handle edge cases (halo voxels, cctbx unavailability, symmetry op failures)?

**9-Step Planning Protocol:**

### 1. Read Context (30 minutes)
Read the following documents in order:
- `docs/spec-db-workflow.md:58-61` — Stage B normative requirements (per-reflection SHALL be default, shell mode MUST NOT be default)
- `plans/active/TORCH-REFINE-004/implementation.md` — Phases 1-5 complete (shell mode working), Phase 6-9 pending
- `plans/active/TORCH-REFINE-004/reports/2025-11-24T125000Z/focus_selection_decision.md` — Supervisor's focus selection rationale and scope analysis
- `docs/spec-db-core.md` — Structure factor conventions and HKL grid semantics
- `docs/architecture/pytorch_design.md §1.1.1` — HKL halo requirements and interpolation

### 2. Analyze cctbx.miller Asymmetric Unit API (45 minutes)
**Objective:** Determine how to map (h,k,l) Miller indices to unique ASU indices using cctbx symmetry operations.

**Tasks:**
- Search codebase for existing cctbx.miller usage:
  ```bash
  grep -r "cctbx.miller\|from cctbx import miller\|miller.set\|miller.array" simtbx_project/ dbex/ --include="*.py" | head -20
  ```
- Inspect `simtbx_project/` or `dbex/data_load.py` for MTZ ingestion patterns (space group extraction, symmetry operations).
- Find cctbx API for ASU mapping (likely `cctbx.miller.set.map_to_asu()` or `cctbx.sgtbx.space_group.asu()`).
- Document API signature, inputs (space group, Miller indices), outputs (ASU index or equivalent reflection).
- Note: If cctbx.miller is unavailable or API is unclear, document this as blocker (Path C decision).

**Deliverable:** Section in `phase_6_planning_analysis.md` titled "cctbx.miller ASU API Analysis" with:
- API function name and signature
- Example usage (pseudocode or reference to existing code)
- Input requirements (space group object, Miller index array)
- Output format (ASU index, equivalent reflection, or symmetry mapping)

### 3. Design ASU Index Computation Algorithm (60 minutes)
**Objective:** Write pseudocode for computing `hkl_asu_map` tensor from HKL grid + space group.

**Algorithm Sketch:**
```python
# Pseudocode (NOT production code)
def compute_hkl_asu_map(hkl_grid: np.ndarray, space_group_info: cctbx.sgtbx.space_group_info) -> torch.Tensor:
    """
    Map each HKL grid voxel to its unique ASU index.

    Args:
        hkl_grid: shape (h_count, k_count, l_count, 3) — Miller indices for each voxel
        space_group_info: cctbx space group object (from MTZ header)

    Returns:
        hkl_asu_map: torch.Tensor[int64] shape (h_count, k_count, l_count)
                     Values are ASU indices 0..n_asu_unique-1
                     Halo voxels (outside MTZ range) map to index 0 with fixed modifier=1.0
    """
    # Step 1: Extract Miller indices from grid (h, k, l)
    miller_indices = hkl_grid[..., :3].reshape(-1, 3)  # (n_voxels, 3)

    # Step 2: Create cctbx.miller.set from indices + space group
    miller_set = cctbx.miller.set(crystal_symmetry=space_group_info, indices=miller_indices)

    # Step 3: Map to ASU using cctbx symmetry operations
    asu_miller_set = miller_set.map_to_asu()  # Returns equivalent reflections in ASU

    # Step 4: Assign unique integer index to each ASU reflection
    unique_asu_indices, inverse_map = np.unique(asu_miller_set.indices(), return_inverse=True, axis=0)

    # Step 5: Reshape inverse_map back to (h_count, k_count, l_count)
    hkl_asu_map = torch.tensor(inverse_map, dtype=torch.int64).reshape(hkl_grid.shape[:3])

    return hkl_asu_map, len(unique_asu_indices)  # (map, n_asu_unique)
```

**Tasks:**
- Write refined pseudocode in `asu_pseudocode.py` (NOT a production module, just planning artifact).
- Address edge cases:
  - **Halo voxels:** HKL grid includes ±1 halo beyond MTZ range (spec-db-workflow.md:61). These voxels have no structure factor. Map them to ASU index 0 with fixed `asu_modifiers[0] = 1.0` (non-trainable).
  - **Symmetry failures:** If cctbx.miller.set construction fails (invalid indices, symmetry mismatch), log warning and fallback to shell mode (spec-permitted fallback per spec:60).
  - **Memory:** ASU index computation is one-time cost during Stage B setup, not per-iteration.
- Identify dependencies: `cctbx.miller`, `cctbx.sgtbx`, `hkl_metadata["space_group"]` (already available from MTZ ingestion per MAP-SCALE-001).

**Deliverable:** `asu_pseudocode.py` with refined algorithm + edge case handling notes.

### 4. Estimate Parameter Counts (30 minutes)
**Objective:** Estimate `n_asu_unique` for common space groups to guide optimizer choice.

**Tasks:**
- Review test fixtures:
  - `tests/fixtures/golden_data/refGeom/` — Check MTZ space group (likely P1 or low symmetry)
  - Canonical detector smoke tests — Space group used
- Calculate theoretical ASU fraction for common space groups:
  - **P1** (no symmetry): ASU = full sphere, `n_asu ≈ n_hkl / 1 ≈ 50K-100K` (HIGH parameter count)
  - **P21** (2-fold symmetry): ASU ≈ 1/2 sphere, `n_asu ≈ 25K-50K` (MEDIUM-HIGH)
  - **P432** (48-fold symmetry): ASU ≈ 1/48 sphere, `n_asu ≈ 1K-2K` (LOW, LBFGS feasible)
- Document parameter count implications:
  - **n_asu < 10K:** LBFGS feasible (limited-memory scales well, spec default per spec:107)
  - **n_asu ≥ 10K:** Consider Adam (spec:107 allows "Stage B MAY use L-BFGS or Adam")

**Deliverable:** `parameter_count_analysis.md` with:
- Table of space groups (P1, P21, P432, etc.) with estimated `n_asu` ranges
- Test fixture space group identification
- Parameter count gate recommendation (e.g., "Use Adam if n_asu ≥ 10000")

### 5. Assess LBFGS vs Adam Trade-Offs (30 minutes)
**Objective:** Recommend optimizer for Stage B per-reflection mode based on parameter count and spec guidance.

**Analysis:**
- **LBFGS Advantages:**
  - Spec default (spec:107 "Default optimizer SHALL be L-BFGS")
  - Better convergence for well-conditioned problems
  - No learning rate tuning
- **LBFGS Disadvantages:**
  - Limited-memory approximation degrades with >10K parameters
  - Full closure recomputation per line search (expensive for large HKL grids)
- **Adam Advantages:**
  - Scales well to large parameter counts (10K-100K)
  - Per-parameter adaptive learning rates
  - Spec-permitted (spec:107 "Stage B MAY use Adam")
- **Adam Disadvantages:**
  - Requires learning rate tuning (suggest 1e-3 default, 1e-4 fallback)
  - Slower convergence than LBFGS for small parameter counts

**Recommendation Logic:**
```python
if n_asu_unique < 10000:
    optimizer = "LBFGS"  # Spec default, better convergence
else:
    optimizer = "Adam"   # Spec-permitted, scales better
    learning_rate = 1e-3  # Default per Stage B heuristics
```

**Deliverable:** `optimizer_decision.md` with:
- Trade-off analysis table (LBFGS vs Adam)
- Parameter count gate (n_asu < 10K → LBFGS, ≥ 10K → Adam)
- Learning rate recommendation for Adam case (1e-3 default, cite reasoning)

### 6. Write Phase 6 Planning Analysis (45 minutes)
**Objective:** Consolidate all planning outputs into comprehensive analysis document.

**Structure:**
```markdown
# Phase 6 Planning Analysis — Per-Reflection ASU Mapping & Parameterization

## Executive Summary
- ASU mapping algorithm: cctbx.miller.set.map_to_asu() approach
- Parameter count estimates: P1 ~50K, P21 ~25K, P432 ~2K
- Optimizer recommendation: LBFGS for n_asu < 10K, Adam for ≥ 10K
- Risk mitigation: Halo voxels → ASU index 0 (fixed), cctbx unavailable → fallback shell mode

## cctbx.miller ASU API Analysis
[From Step 2]

## ASU Index Computation Algorithm
[From Step 3, reference asu_pseudocode.py]

## Parameter Count Analysis
[From Step 4, reference parameter_count_analysis.md]

## Optimizer Decision
[From Step 5, reference optimizer_decision.md]

## Risk Mitigation
- R1 (ASU index computation complexity): Use cctbx.miller.set.map_to_asu(), fallback to shell mode if unavailable
- R2 (Parameter count explosion): Dynamic optimizer selection based on n_asu threshold (10K gate)
- R3 (HKL halo handling): Map halo voxels to ASU index 0 with fixed modifier=1.0

## Implementation Checklist (Phase 6 Next Loop)
- [ ] Extend `compute_hkl_shell_lookup` to `compute_hkl_asu_map` in dbex/nanobrag_refinement.py
- [ ] Add `asu_modifiers: nn.Parameter` initialization in Stage B setup
- [ ] Implement dynamic optimizer selection (LBFGS vs Adam) based on n_asu count
- [ ] Add halo voxel guard (ASU index 0 fixed modifier)
- [ ] Unit test ASU mapping (synthetic P1/P432 space groups, verify symmetry equivalence)

## Decision Paths
- **Path A:** All planning questions answered, cctbx API confirmed, proceed to Phase 6 implementation next loop (RECOMMENDED)
- **Path B:** Algorithm design unclear, need refinement (additional planning loop)
- **Path C:** cctbx.miller unavailable or API incompatible, blocked (escalate to upstream or fallback shell mode only)
- **Path D:** Parameter count too high (>100K), per-reflection mode infeasible, stick with shell mode as primary (violates spec, document exception)

## Confidence Assessment
- cctbx API availability: HIGH (~95%) — Already in environment per upstream tools
- Algorithm correctness: MEDIUM (~80%) — Symmetry equivalence logic needs validation
- Parameter count estimates: MEDIUM (~75%) — Test fixture space groups unknown
- Optimizer choice: HIGH (~90%) — Well-established heuristics from literature

## Estimated Implementation Effort (Post-Planning)
- Phase 6 implementation: 1-2 loops (~2-4 hours)
- Phase 7 optimization loop: 1 loop (~1-2 hours)
- Phase 8 tests: 1 loop (~2 hours)
- **Total:** 2-4 loops (~5-8 hours) for Phases 6-8 combined
```

### 7. Decision Synthesis (15 minutes)
**Objective:** Produce `decision.json` with 4-path decision tree for supervisor review.

**Decision Criteria:**
- **Path A (Proceed to Phase 6 Implementation):**
  - cctbx.miller API confirmed available
  - ASU mapping algorithm pseudocode complete
  - Parameter count estimates documented
  - Optimizer recommendation clear (LBFGS vs Adam gate)
  - Risk mitigation strategies defined
  - **Confidence:** HIGH (~85%)
- **Path B (Refine Design):**
  - ASU mapping algorithm unclear or edge cases unresolved
  - cctbx API usage ambiguous
  - Parameter count estimates too uncertain
  - **Confidence:** MEDIUM (~60%)
- **Path C (Blocked by cctbx Unavailable):**
  - cctbx.miller not in environment (violates Environment Freeze, cannot install)
  - cctbx API incompatible or broken
  - **Confidence:** LOW (~30%)
- **Path D (Fallback Shell Mode Only):**
  - Parameter count >100K makes per-reflection infeasible
  - cctbx unavailable and no workaround
  - Violates spec (per-reflection SHALL be default), document exception
  - **Confidence:** LOW (~20%)

**decision.json Format:**
```json
{
  "focus": "TORCH-REFINE-004",
  "phase": "6_planning",
  "timestamp": "2025-11-24T125000Z",
  "path": "A",  # A/B/C/D
  "rationale": "cctbx.miller API confirmed, pseudocode complete, parameter count estimates documented, optimizer recommendation clear",
  "confidence": 0.85,
  "next_action": "proceed_to_phase_6_implementation",
  "blockers": [],
  "artifacts": ["phase_6_planning_analysis.md", "asu_pseudocode.py", "parameter_count_analysis.md", "optimizer_decision.md"]
}
```

### 8. Write summary.md Turn Summary (10 minutes)
**Objective:** Create human-readable Turn Summary per end-of-loop hygiene requirements.

**Format:** Single level-3 heading `### Turn Summary`, 3-5 short sentences covering:
1. What you shipped/advanced (Phase 6 planning complete OR blocker identified)
2. Main problem and how you handled it (ASU mapping design, optimizer choice, etc.)
3. Single next step (Phase 6 implementation OR design refinement OR escalate blocker)
4. Artifacts line pointing to reports directory

**Example:**
```markdown
### Turn Summary
Completed Phase 6 planning analysis for per-reflection ASU mapping using cctbx.miller symmetry operations; parameter count estimates range 2K (P432) to 50K (P1) with LBFGS < 10K gate / Adam ≥ 10K recommendation.
ASU index computation pseudocode designed with halo voxel handling (map to index 0 fixed modifier) and cctbx unavailable fallback to shell mode.
Next: Phase 6 implementation (extend compute_hkl_asu_map helper, add asu_modifiers parameter, dynamic optimizer selection).
Artifacts: plans/active/TORCH-REFINE-004/reports/2025-11-24T125000Z/ (phase_6_planning_analysis.md, asu_pseudocode.py, parameter_count_analysis.md, optimizer_decision.md, decision.json)
```

Prepend this block to `plans/active/TORCH-REFINE-004/reports/2025-11-24T125000Z/summary.md` (create if doesn't exist).

### 9. Commit Planning Artifacts (5 minutes)
**Objective:** Commit all planning artifacts with clear message.

**Commands:**
```bash
git add plans/active/TORCH-REFINE-004/reports/2025-11-24T125000Z/
git commit -m "RALPH: TORCH-REFINE-004 Phase 6 planning — ASU mapping design (tests: not run)"
git push
```

**Important:** Use `tests: not run` in commit message since this is planning-only loop (no code execution).

## How-To Map

**Step 1: Read Context**
```bash
# Read spec and planning context
cat docs/spec-db-workflow.md | grep -A 10 "Stage B"
cat plans/active/TORCH-REFINE-004/implementation.md
cat plans/active/TORCH-REFINE-004/reports/2025-11-24T125000Z/focus_selection_decision.md
cat docs/spec-db-core.md | grep -A 5 "structure factor\|HKL"
cat docs/architecture/pytorch_design.md | grep -A 10 "halo"
```

**Step 2: Analyze cctbx.miller API**
```bash
# Search for existing cctbx.miller usage in codebase
grep -r "cctbx.miller\|from cctbx import miller\|miller.set\|miller.array" simtbx_project/ dbex/ --include="*.py" | head -30

# Inspect MTZ ingestion for space group extraction
cat dbex/data_load.py | grep -A 20 "space_group\|MTZ\|mtz"

# Check if cctbx is available
python -c "from cctbx import miller, sgtbx; print('cctbx available')" 2>&1 || echo "cctbx unavailable (Path C blocker)"
```

**Step 3: Design ASU Index Computation**
Write pseudocode to `plans/active/TORCH-REFINE-004/reports/2025-11-24T125000Z/asu_pseudocode.py` (use Write tool, NOT a production module).

**Step 4: Estimate Parameter Counts**
```bash
# Check test fixture space groups
grep -r "space_group\|P 1\|P 21\|P 43" tests/fixtures/golden_data/ | head -10

# Document estimates in parameter_count_analysis.md
```
Use Write tool to create `plans/active/TORCH-REFINE-004/reports/2025-11-24T125000Z/parameter_count_analysis.md`.

**Step 5: Assess LBFGS vs Adam**
Use Write tool to create `plans/active/TORCH-REFINE-004/reports/2025-11-24T125000Z/optimizer_decision.md`.

**Step 6: Write Planning Analysis**
Use Write tool to create `plans/active/TORCH-REFINE-004/reports/2025-11-24T125000Z/phase_6_planning_analysis.md` consolidating Steps 2-5.

**Step 7: Decision Synthesis**
Use Write tool to create `plans/active/TORCH-REFINE-004/reports/2025-11-24T125000Z/decision.json`.

**Step 8: Turn Summary**
Use Write tool to create/prepend `plans/active/TORCH-REFINE-004/reports/2025-11-24T125000Z/summary.md`.

**Step 9: Commit**
```bash
git add plans/active/TORCH-REFINE-004/reports/2025-11-24T125000Z/
git commit -m "RALPH: TORCH-REFINE-004 Phase 6 planning — ASU mapping design (tests: not run)"
git push
```

## Pitfalls To Avoid

1. **Do NOT write production code** — This is planning-only. No edits to `dbex/nanobrag_refinement.py` or test files. All code is pseudocode in artifacts directory.

2. **Do NOT install packages** — Environment Freeze enforced. If cctbx.miller is unavailable, document as Path C blocker, do NOT `pip install cctbx`.

3. **Do NOT execute tests** — No `pytest` runs this loop. Validation is conceptual (pseudocode review), not execution.

4. **HKL halo handling is MANDATORY** — Per spec-db-workflow.md:61, halo voxels (±1 beyond MTZ range) must exist for differentiable interpolation. Map these to ASU index 0 with fixed modifier=1.0 (non-trainable).

5. **Shell mode is fallback, NOT default** — Per spec:60, "Shell Mode MUST NOT be the default." Design must make per-reflection the config default (`stage_b_mode="per_reflection"` when unspecified).

6. **Parameter count affects optimizer choice** — Do NOT hard-code LBFGS. Dynamic selection based on `n_asu_unique` threshold (suggest 10K gate per spec:107 guidance).

7. **Space group is REQUIRED input** — ASU mapping depends on `hkl_metadata["space_group"]` from MTZ. If missing, Stage B setup must fail gracefully with clear error message (not silent fallback).

8. **Symmetry equivalence is non-trivial** — ASU mapping is MORE complex than shell radius calculation (which only uses `sqrt(h²+k²+l²)`). cctbx.miller handles Friedel pairs, systematic absences, and symmetry operations. Do NOT attempt manual symmetry logic without cctbx.

9. **Memory considerations** — ASU index map (`hkl_asu_map`) is one-time cost during Stage B setup, stored on-device. For 512³ HKL grid + int64, ~1GB GPU memory. Document this in planning analysis.

10. **Gradient flow validation deferred** — This planning loop does NOT validate gradients. Phase 7 implementation will add gradient check (finite-difference test for `asu_modifiers` parameter).

## If Blocked

**Scenario 1: cctbx.miller unavailable**
- **Action:** Document Path C in decision.json.
- **Rationale:** "cctbx.miller not found via `from cctbx import miller` test. Environment Freeze prevents installation."
- **Recommendation:** Escalate to supervisor with blocker note. Fallback option: implement shell mode as primary (violates spec, requires exception documentation).
- **Log:** `plans/active/TORCH-REFINE-004/reports/2025-11-24T125000Z/cctbx_unavailable_blocker.md`

**Scenario 2: cctbx API incompatible**
- **Action:** Document API signature mismatch in planning analysis.
- **Rationale:** "cctbx.miller.set.map_to_asu() signature differs from expected; cannot determine ASU mapping approach."
- **Recommendation:** Research alternative cctbx API (e.g., `cctbx.sgtbx.space_group.asu()`) or request maintainer clarification.
- **Log:** `plans/active/TORCH-REFINE-004/reports/2025-11-24T125000Z/cctbx_api_mismatch.md`

**Scenario 3: Parameter count >100K infeasible**
- **Action:** Document Path D in decision.json.
- **Rationale:** "Test fixture space group P1 has n_asu ≈ 100K unique reflections. Per-reflection mode requires >100K parameters, exceeding practical Adam parameter scale."
- **Recommendation:** Stick with shell mode as primary implementation (violates spec, document exception in `docs/findings.md` with justification).
- **Log:** `plans/active/TORCH-REFINE-004/reports/2025-11-24T125000Z/parameter_count_infeasible.md`

**Scenario 4: Algorithm design unclear**
- **Action:** Document Path B in decision.json.
- **Rationale:** "ASU mapping algorithm edge cases unresolved (halo voxels, systematic absences, Friedel pairs). Requires additional planning iteration."
- **Recommendation:** Extend planning with focused investigation (e.g., test cctbx.miller on synthetic P1/P432 datasets, capture edge case behaviors).
- **Log:** `plans/active/TORCH-REFINE-004/reports/2025-11-24T125000Z/algorithm_refinement_needed.md`

## Findings Applied (Mandatory)

**Relevant Finding IDs from Knowledge Base:**
- **REFINE-001** (LBFGS scale warm-start) — Stage B inherits global scale from Stage A final state, no re-initialization.
- **REFINE-002** (acceptance gate) — Stage B improvement gate (chi² improvement vs Stage A final) is separate from Stage A nucleus gate.
- **REFINE-005** (HKL halo mandatory) — Differentiable tricubic interpolation requires ±1 halo grid; halo voxels map to ASU index 0 with fixed modifier=1.0.
- **SCALE-001** (structure factors unscaled) — Structure factors from MTZ are NOT pre-multiplied by scale; modifiers applied post-interpolation in forward model.
- **SCALE-002** (global post-simulation factor) — √spot_scale applied after Simulator, not before; ASU modifiers are per-reflection, not global scale.
- **PHYSICS-LOSS-001** (variance-weighted loss consistency) — Stage B uses same `V = I_model + sigma²` denominator as Stage A; chi² and masked_mse both logged.
- **POLICY-001** (Environment Freeze) — Use existing cctbx.miller, do NOT install new packages. If cctbx unavailable, fallback to shell mode (violates spec but permitted under blocker).
- **ARCH-ENGINE-002** (lazy imports) — Import cctbx.miller inside Stage B setup function to avoid circular dependencies and module-level import failures.
- **spec-db-workflow.md:59** (per-reflection SHALL be default) — "Per-reflection Fhkl multipliers mapped to unique ASU indices SHALL be the default (Parity Mode)." Core normative requirement.
- **spec-db-workflow.md:60** (shell mode fallback) — "Shell Mode MUST NOT be the default." Shell mode permitted as optimization/regularization but not primary path.
- **spec-db-workflow.md:61** (tricubic + halo mandatory) — "Tricubic interpolation (`interpolation=True`) with ±1 HKL halo is MANDATORY." Non-negotiable for Stage B.
- **spec-db-workflow.md:107** (optimizer flexibility) — "Stage B MAY use L-BFGS or Adam." Dynamic selection based on parameter count threshold (10K gate).

**Adherence Notes:**
- **REFINE-005 + spec:61:** Halo voxel handling designed (ASU index 0 fixed modifier).
- **SCALE-001/002:** Modifier application order preserved (post-interpolation, not pre-simulation).
- **PHYSICS-LOSS-001:** Stage B telemetry includes chi² and masked_mse dual metrics per existing pattern.
- **POLICY-001:** cctbx.miller availability checked, no installation attempted if missing (Path C blocker).
- **spec:59:** Per-reflection as default enforced in design (config default `stage_b_mode="per_reflection"`).
- **spec:107:** LBFGS vs Adam decision logic documented with parameter count gate (10K threshold).

## Pointers

**Specs:**
- `docs/spec-db-workflow.md:58-61` — Stage B normative requirements (per-reflection default, shell fallback, tricubic + halo)
- `docs/spec-db-workflow.md:102-115` — Optimization strategy (LBFGS default, Adam permitted, gradient hygiene)
- `docs/spec-db-core.md:57-80` — Variance definition and structure factor conventions

**Architecture:**
- `docs/architecture/pytorch_design.md §1.1.1` — HKL halo requirements and interpolation semantics

**Implementation Plans:**
- `plans/active/TORCH-REFINE-004/implementation.md:1-38` — Phases 1-5 complete (shell mode), Phase 6-9 pending (per-reflection mode)
- `plans/active/TORCH-REFINE-004/reports/2025-11-24T125000Z/focus_selection_decision.md` — Supervisor's focus selection rationale

**Fix Plan:**
- `docs/fix_plan.md:227-239` — TORCH-REFINE-004 entry (status, exit criteria, dependency satisfied)

**Findings:**
- `docs/findings.md` — REFINE-001/002/005, SCALE-001/002, PHYSICS-LOSS-001, POLICY-001, ARCH-ENGINE-002

**Testing:**
- `docs/TESTING_GUIDE.md` — Test selector conventions and environment requirements (will be updated in Phase 9)
- `docs/development/TEST_SUITE_INDEX.md` — Test registry (will be updated in Phase 9)

## Next Up (Optional)

If you finish early (all 9 steps complete with decision.json Path A confidence ≥80%), you MAY optionally:
1. Draft Phase 6 implementation checklist (tasks for next loop) in planning analysis.
2. Identify specific code locations for Phase 6 edits (e.g., `dbex/nanobrag_refinement.py:XXXX` where `compute_hkl_asu_map` should be added).
3. List unit test cases for ASU mapping validation (synthetic P1/P432 space groups, verify symmetry equivalence).

Do NOT proceed to Phase 6 implementation code edits. Next loop will be ready_for_implementation per Implementation Floor rule.

## Doc Sync Plan (Conditional)

**Not applicable this loop** — No tests added/renamed. Registry sync deferred to Phase 8 (test authoring loop).

## Mapped Tests Guardrail

**Not applicable this loop** — Evidence-only planning, no test execution. Phase 8 will add `test_stage_b_per_reflection_default` selector.

## Normative Math/Physics

**Do NOT paraphrase spec equations.** When referencing Stage B variance-weighted loss (PHYSICS-LOSS-001), point to exact spec section:
- "See `docs/spec-db-core.md:57-68` (Variance Definition: `V = I_model + sigma²` detached denominator)"
- "See `docs/spec-db-workflow.md:58-61` (Stage B normative requirements)"

Do NOT write pseudo-math like "loss = sum((data - model)² / variance)". Direct Ralph to read the normative spec for exact formulation.
