# Input for Ralph — ARCH-SIM-CONSTRUCTION-001 Phase A.1 Evidence Collection

**Summary:** Compare simulator construction paths between Stage A (training) and reconstruction helpers to identify calibration threading differences

**Mode:** none (evidence collection)

**InitiativeType:** architecture

**Focus:** ARCH-SIM-CONSTRUCTION-001 — Simulator Construction Convention Alignment (Training vs Reconstruction)

**Branch:** integration

**Mapped tests:** none — evidence-only

**Artifacts:** `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-02T233717Z/`

---

## Do Now

### Context

ARCH-REFACTOR-001 Phase D.3 lifecycle escalation: bugfix (commit 6db57f45) implemented correctly and executes as expected (log_scale_baseline=20.14, scale_factor=5.57e8), but tests DB-AT-028/029 still FAIL because simulator raw output is ~10^4.4× too small (bragg_panel mean=1.8e-14 vs expected ~4.3e-10). This suggests systematic convention mismatch in how simulators are constructed between training (Stage A) and reconstruction helpers.

**Hypothesis:** Reconstruction builds simulators via `create_unified_simulator(..., spot_scale_override=None)` while Stage A applies calibration metadata at factory construction time, producing outputs that differ by factor ~23,900.

**Lifecycle status:** New architecture initiative opened per repeat-failure guard. This is Phase A.1 evidence collection—no implementation changes this loop.

---

### Evidence Collection Tasks

#### Task 1: Trace Stage A Simulator Construction

**File to read:** `dbex/refinement/stage_a.py`

**Focus areas:**
- Lines ~400-600: How does Stage A build simulators? (Warm cache vs cold path)
- Look for `create_unified_simulator` call sites
- Identify arguments passed to factory: `spot_scale_override`, `calibration_metadata`, `gain`, `sigma`
- Check if simulators are reused from context or built fresh each loop
- Note how `log_scale_baseline = log(sqrt(spot_scale_override))` is established

**Output:** Write analysis to `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-02T233717Z/stage_a_simulator_construction.md`

Include:
- Factory call site(s) with line numbers
- Arguments passed (especially spot_scale_override)
- Warm vs cold path logic
- How calibration metadata flows from RefinementContext → factory

#### Task 2: Trace Reconstruction Simulator Construction

**File to read:** `dbex/refinement/reconstruction.py`

**Function:** `build_final_bragg_from_stage_a_telemetry` (lines 140-230)

**Focus areas:**
- Lines 140-190: Simulator construction logic
- Identify `create_unified_simulator` call site
- Check arguments: is `spot_scale_override` passed or None?
- Check if `calibration_metadata` is threaded to factory
- Note any post-hoc scaling applied after simulator.run()

**Output:** Write analysis to `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-02T233717Z/reconstruction_simulator_construction.md`

Include:
- Factory call site with line numbers
- Arguments passed (especially spot_scale_override)
- How telemetry (`param_deltas_a`) is used
- Any scaling applied before or after forward model run

#### Task 3: Compare Factory Calls Side-by-Side

**Goal:** Create comparison table showing differences

**Output:** Write to `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-02T233717Z/factory_call_comparison.md`

Format as table:
```markdown
| Aspect | Stage A (Training) | Reconstruction Helper |
|--------|-------------------|----------------------|
| File:Line | ... | ... |
| spot_scale_override arg | ... | ... |
| calibration_metadata arg | ... | ... |
| gain arg | ... | ... |
| sigma arg | ... | ... |
| Warm/Cold path | ... | ... |
| Post-run scaling | ... | ... |
```

Identify the key difference(s) that could explain 10^4.4× magnitude discrepancy.

#### Task 4: Review Ralph's Debug Evidence

**Files to read:**
- `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T000000Z_galph_phase_d3_fix_diagnosis/ralph_findings.md`
- `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T000000Z_galph_phase_d3_fix_diagnosis/at028/db_at_028_metrics.json`

**Extract:**
- `spot_scale_override` value (should be ~3.1e17)
- `log_scale_baseline` value (should be ~20.14)
- `scale_factor` value (should be ~5.57e8)
- `bragg_panel` raw output (currently ~1.8e-14, should be ~4.3e-10)
- Missing factor calculation: confirm ~23,900 ≈ 10^4.38

**Output:** Write to `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-02T233717Z/debug_metrics_analysis.md`

Include:
- Actual values from metrics JSON
- Expected values from spec/physics
- Missing factor calculation
- Hypothesis on what could produce this specific missing factor (e.g., sqrt(gain)? photon↔ADU conversion?)

---

## How-To Map

### Step 1: Read Stage A simulator construction
```bash
# Read Stage A simulator setup
# Focus on create_unified_simulator call sites
# Note warm cache vs cold path logic
```

### Step 2: Read reconstruction simulator construction
```bash
# Read reconstruction.py::build_final_bragg_from_stage_a_telemetry
# Focus on lines 140-190 (simulator construction)
# Note factory arguments
```

### Step 3: Create comparison artifacts
```bash
# Write 4 analysis files to reports directory:
# - stage_a_simulator_construction.md
# - reconstruction_simulator_construction.md
# - factory_call_comparison.md
# - debug_metrics_analysis.md
```

### Step 4: Synthesize findings
```bash
# Create summary.md with:
# - Key differences identified
# - Plausible root cause(s)
# - Recommended next steps (Phase B probe or Phase C fix)
```

---

## Pitfalls To Avoid

1. **Do NOT implement any fixes** — This is evidence collection only
2. **Do NOT run tests** — No validation needed this loop
3. **Do NOT write code** — Analysis artifacts only (markdown reports)
4. **Be comprehensive** — Read surrounding context, not just target lines
5. **Cross-reference spec docs** — Cite `docs/spec-db-core.md §§20-40` (calibration) and `docs/architecture/calibration_scaling.md` (spot_scale threading) when relevant
6. **Check both warm and cold paths** — Stage A may have different logic for cached vs fresh simulators
7. **Look for post-hoc scaling** — Check if either path applies scaling after simulator.run() instead of at construction
8. **Note telemetry structure** — Reconstruction only has access to `param_deltas_a` dict, not original `calibration_metadata`
9. **Environment Freeze** — Do not install packages (no imports expected to fail)
10. **Right-sized analysis** — Keep markdown reports concise (1-2 pages each), not exhaustive code dumps

---

## If Blocked

1. **Missing calibration_metadata in reconstruction context:** This may be the root cause. Document it and note whether param_deltas_a includes spot_scale_override or only log_scale_baseline.

2. **Factory signature unclear:** Read `dbex/nanobrag_bridge.py::create_unified_simulator` to understand what parameters it accepts and how it applies them.

3. **Multiple code paths found:** Document all paths (e.g., warm cache ROI mode vs panel mode vs cold path) and note which one the failing tests use.

4. **Unclear telemetry structure:** Read `dbex/refinement/context.py` and `dbex/refinement/stage_a.py` to see how telemetry is serialized and what fields are available to reconstruction helper.

---

## Findings Applied

**Relevant findings from knowledge base:**
- **ARCH-FACTORY-001:** Unified simulator factory (cold path context)
- **TOOLING-VIS-001 Phase D.C:** Log_scale baseline separation for calibrated runs
- **DB-AT-027:** Stage A mapping parity with calibration metadata
- **GRADIENT-004:** Warm cache path constraints

**Adherence notes:**
- Evidence collection aligns with architecture initiative type (no spec/test changes)
- Focuses on internal convention alignment per ARCH-FACTORY-001
- Uses calibration semantics from TOOLING-VIS-001 and DB-AT-027 as reference
- Respects warm cache path documented in GRADIENT-004

---

## Pointers

**Spec/Architecture:**
- `docs/spec-db-core.md §§20-40` — Geometry/crystal/calibration contracts
- `docs/architecture/calibration_scaling.md` — ADU↔photon policy, spot_scale threading
- `plans/active/ARCH-SIM-CONSTRUCTION-001/implementation.md` — Full initiative plan

**Code References:**
- `dbex/refinement/stage_a.py` (~400-600) — Stage A simulator construction
- `dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry` (140-230) — Reconstruction simulator construction
- `dbex/nanobrag_bridge.py::create_unified_simulator` — Factory implementation
- `dbex/refinement/context.py` — Telemetry and context dataclasses

**Evidence:**
- `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T000000Z_galph_phase_d3_fix_diagnosis/ralph_findings.md` — Ralph's debug analysis (commit 6db57f45)
- `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T000000Z_galph_phase_d3_fix_diagnosis/at028/db_at_028_metrics.json` — Debug metrics
- `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T233717Z_galph_phase_d3_lifecycle_event/lifecycle_analysis.md` — Lifecycle escalation rationale

**Fix-Plan:**
- `docs/fix_plan.md` — ARCH-SIM-CONSTRUCTION-001 entry (Tier 0, in_progress)

---

## Next Up (optional)

If you finish evidence collection early and have clear findings:
1. Draft a hypothesis statement for Phase B (root cause confirmation)
2. Sketch the minimal fix strategy (which file to change, what arguments to pass)
3. Note any additional evidence needed before implementation

Do NOT proceed to Phase B probe or Phase C fix without explicit approval from Galph.

---

## Doc Sync Plan

**Not required this loop** — No tests run, no code changes. Evidence artifacts only.

---

## Normative References

**Calibration threading:** `docs/spec-db-core.md §§20-40` — Simulators must apply calibration metadata (gain, sigma, spot_scale_override) at construction time per factory contract.

**Spot-scale application timing:** `docs/architecture/calibration_scaling.md` — spot_scale_override must be applied before forward model runs, not post-hoc.

**Factory contract:** `docs/architecture/module_map.md` — `dbex.refinement.reconstruction` helpers must use factory with calibration awareness.

Ralph should read these sections directly if architecture questions arise.
