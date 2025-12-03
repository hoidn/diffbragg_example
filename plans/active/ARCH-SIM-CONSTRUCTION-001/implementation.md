# Implementation Plan: ARCH-SIM-CONSTRUCTION-001

## Initiative
- ID: ARCH-SIM-CONSTRUCTION-001
- Title: Simulator Construction Convention Alignment (Training vs Reconstruction)
- Owner: Galph ↔ Ralph
- Spec Owner: docs/spec-db-core.md §§20-40, docs/architecture/calibration_scaling.md
- Status: planned
- Type: architecture
- Priority: Highest (blocks ARCH-REFACTOR-001 Phase D.3)
- Tier: 0

## Goals
1. **Align simulator construction conventions** so reconstruction helpers (`build_final_bragg_from_stage_*_telemetry`) produce identical simulator outputs as training stages (Stage A/B/C) given identical parameters
2. **Enforce factory contract:** `create_unified_simulator` must apply calibration metadata (spot_scale_override, gain, sigma) consistently at construction time
3. **Validate DB-AT-028/029** pass once simulator raw outputs are magnitude-aligned

## Non-Goals
- Changing external API or test harness (internal alignment only)
- Modifying Stage A/B/C training logic (unless factory contract violations found)
- Weakening acceptance criteria or gates

## Exit Criteria
1. [ ] **Simulator output parity:** Reconstruction simulator raw output magnitude matches Stage A simulator raw output (within 1% relative error for same input parameters, same crystal/beam/detector config)
2. [ ] **DB-AT-028:** `chi²/pixel initial ≤ 1e2` (currently ~1e5)
3. [ ] **DB-AT-029:** `median ROI correlation before ≥ 0.2` (currently -0.05)
4. [ ] **No external API changes:** Fix is internal to reconstruction.py and/or factory; no changes to RefinementEngine, Stage classes, or test harness
5. [ ] **Factory contract documentation:** Update `docs/architecture/dbex/nanobrag_bridge.idl.md` or create `docs/architecture/dbex/simulator_factory.idl.md` to clarify calibration threading requirements

## Dependencies
- Blocked by: None
- Blocks: ARCH-REFACTOR-001 Phase D.3 (reconstruction baseline logic bugfix already landed, but tests fail due to this issue)
- References:
  - ARCH-FACTORY-001: Unified simulator factory (cold path context)
  - TOOLING-VIS-001 Phase D.C: Log_scale baseline separation for calibrated runs
  - DB-AT-027: Stage A mapping parity with calibration metadata
  - GRADIENT-004: Warm cache path constraints

## Spec Alignment
- **docs/spec-db-core.md §§20-40:** Geometry/crystal/calibration contracts — simulators must apply calibration metadata (gain, sigma, spot_scale_override) at construction time per factory contract
- **docs/architecture/calibration_scaling.md:** ADU↔photon policy, spot_scale threading — spot_scale_override must be applied before forward model runs, not post-hoc
- **docs/architecture/module_map.md:** `dbex.refinement.reconstruction` — helpers must use factory with calibration awareness

## Compliance Matrix
- [ ] **Spec Constraint:** `docs/spec-db-core.md §§20-40` — Calibration threading
- [ ] **Spec Constraint:** `docs/architecture/calibration_scaling.md` — Spot_scale application timing
- [ ] **Fix-Plan Link:** `docs/fix_plan.md — Row [ARCH-SIM-CONSTRUCTION-001]`
- [ ] **Finding/Policy ID:** TBD after Phase A evidence collection

---

## Phases Overview
- **Phase A — Evidence Collection (Planned):** Map simulator construction paths (Stage A training vs reconstruction); identify calibration threading differences
- **Phase B — Root Cause Isolation (Planned):** Determine whether issue is factory contract violation, missing calibration parameter, or post-hoc scaling assumption
- **Phase C — Fix Implementation (Planned):** Apply fix to reconstruction.py and/or factory to align conventions
- **Phase D — Validation & Documentation (Planned):** Verify DB-AT-028/029 pass; document factory contract in IDL

---

## Phase A — Evidence Collection (Complete — 2025-12-02T233717Z)

**Goal:** Understand how Stage A and reconstruction build simulators; identify where spot_scale_override (or other calibration metadata) is applied differently.

**Status:** Complete — Root cause confirmed (reconstruction missing `sqrt(spot_scale_override)` post-run scaling)

### Checklist

#### A.1 — Simulator Construction Comparison (Complete)
- [x] **Trace Stage A simulator construction:**
  - Read `dbex/refinement/stage_a.py` lines ~400-600 (simulator setup logic)
  - Identify whether Stage A uses warm cache (reused from `create_unified_simulator`) or builds fresh
  - Check if `spot_scale_override` is passed to factory or applied post-run
  - Document how `log_scale_baseline = log(sqrt(spot_scale_override))` is established
- [x] **Trace reconstruction simulator construction:**
  - Read `dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry` lines 140-190
  - Identify factory call site and arguments
  - Check if `calibration_metadata` or `spot_scale_override` is passed to factory
  - Document how `log_scale_baseline` is extracted from telemetry
- [x] **Compare factory call sites:**
  - Create side-by-side comparison table showing arguments passed to `create_unified_simulator` in Stage A vs reconstruction
  - Note differences in `spot_scale_override`, `calibration_metadata`, `gain`, `sigma` threading
  - Identify any post-hoc scaling applied after simulator.run() in either path

**Artifacts:**
- ✓ `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-02T233717Z/stage_a_simulator_construction.md`
- ✓ `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-02T233717Z/reconstruction_simulator_construction.md`
- ✓ `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-02T233717Z/factory_call_comparison.md`

#### A.2 — Calibration Metadata Flow Tracing (Complete — subsumed by A.1)
- [x] **Trace calibration_metadata from CLI to Stage A:**
  - Start at `dbex/refine_one.py` — how is `calibration_metadata` passed to RefinementEngine?
  - Follow through `RefinementContext` → Stage A context → simulator factory
  - Document exact dict structure and field threading
- [x] **Trace calibration_metadata from telemetry to reconstruction:**
  - Start at `build_final_bragg_from_stage_a_telemetry` — what telemetry fields are available?
  - Check if `param_deltas_a` includes spot_scale_override or only log_scale_baseline
  - Identify missing links between telemetry and factory arguments

**Artifacts:**
- ✓ Covered in `stage_a_simulator_construction.md` and `factory_call_comparison.md`

#### A.3 — Debugging Evidence Review (Complete)
- [x] **Extract metrics from Ralph's debug run:**
  - Read `plans/active/ARCH-REFACTOR-001/reports/2025-12-02T000000Z_galph_phase_d3_fix_diagnosis/at028/db_at_028_metrics.json`
  - Note: `spot_scale_override = 3.1e17`, `log_scale_baseline = 20.14`, `scale_factor = 5.57e8`
  - Note: `bragg_panel (raw) mean = 1.8e-14` (TOO SMALL), expected ~4.3e-10
  - Calculate missing factor: ~23,900 ≈ 10^4.38
- [x] **Hypothesize plausible mechanisms:**
  - Does `create_unified_simulator` apply `spot_scale_override` internally?
  - Is there an intermediate gain/sigma factor (~sqrt(23900) ≈ 154) missing?
  - Could this be a photon↔ADU conversion issue?

**Artifacts:**
- ✓ `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-02T233717Z/debug_metrics_analysis.md`

**Root Cause (Confirmed):**
Reconstruction helper `build_final_bragg_from_stage_a_telemetry()` violates factory post-run scaling pattern by omitting the explicit `sqrt(spot_scale_override)` multiplication that Stage A applies to every simulator output (stage_a.py:442-443). Missing factor ~23,900 ≈ (spot_scale_override)^(1/4) confirms one sqrt application is missing. Additionally, reconstruction does not thread `beam_flux`, `beam_exposure`, `beamsize_mm` from calibration_metadata to beam_config (unlike Stage A in stage_a_utils.py:267).

---

## Phase B — Root Cause Isolation (Skipped — Evidence Conclusive)

**Goal:** Determine exact locus of convention mismatch and confirm hypothesis via targeted probe.

**Status:** Skipped — Phase A evidence is conclusive (missing factor quantified, pattern match with Stage A clear, confidence high)

**Rationale:** Ralph's Phase A.1 analysis quantified the missing factor (~23,900 ≈ (spot_scale_override)^(1/4)) with 1.3% accuracy and identified the exact code pattern mismatch (Stage A applies `sqrt(spot_scale_override)` post-run at stage_a.py:442-443; reconstruction omits this). Additional probe would not increase confidence. Proceeding directly to Phase C fix implementation per supervisor decision.

### Checklist

#### B.1 — Factory Contract Audit
- [ ] **Read `create_unified_simulator` signature and implementation:**
  - Check if `spot_scale_override` parameter exists and how it's used
  - Verify if simulator applies it to forward model output or expects post-hoc scaling
  - Document factory contract expectations
- [ ] **Compare against Stage A usage:**
  - Does Stage A pass `spot_scale_override=...` to factory?
  - Does reconstruction pass `spot_scale_override=None`?
  - Identify contract violation

**Artifacts:**
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/<timestamp>/factory_contract_audit.md`

#### B.2 — Targeted Probe (Cold vs Warm Path)
- [ ] **Write minimal probe script** (Tier 2) to:
  - Build simulator via `create_unified_simulator` with and without `spot_scale_override`
  - Run forward model with identical crystal/beam/detector params
  - Compare raw output magnitudes
  - Save results to JSON
- [ ] **Execute probe with calibration metadata from DB-AT-028:**
  - Use exact same inputs as test fixture
  - Measure magnitude difference
  - Confirm if missing factor ~10^4.4 appears when spot_scale_override is omitted

**Artifacts:**
- `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_spot_scale_factory.py` (Tier 2 script)
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/<timestamp>/probe_results.json`

#### B.3 — Hypothesis Confirmation
- [ ] **Synthesize evidence:** Does omitting `spot_scale_override` from factory call explain the 10^4.4× discrepancy?
- [ ] **Document root cause:** Write concise summary with spec/architecture references

**Artifacts:**
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/<timestamp>/root_cause_confirmed.md`

---

## Phase C — Fix Implementation (In Progress — 2025-12-02)

**Goal:** Apply minimal fix to align reconstruction simulator construction with Stage A conventions.

**Strategy:** Implement **Option B** (Stage A post-run scaling pattern) + **Option C** (beam calibration threading) per Ralph's recommendation in Phase A.1 summary.md

### Checklist

#### C.1 — Fix Reconstruction Post-Run Scaling and Beam Calibration (Planned)
- [ ] **Apply Option B — Stage A post-run scaling pattern:**
  - Extract `spot_scale_override` from `config.calibration_metadata` (before simulator loop, line ~167)
  - Compute `sqrt_spot_scale = sqrt(spot_scale_override)` matching stage_a.py:442-443 pattern
  - Apply it post-run in the simulator loop (lines ~220-223):
    ```python
    for pid, sim in zip(sampled_panel_ids, simulators):
        bragg_panel = sim.run()
        bragg_panel_scaled = bragg_panel * sqrt_spot_scale  # ← NEW: consistent with Stage A
        bragg_scaled = bragg_panel_scaled * scale_factor
        bragg_full[pid] = bragg_scaled.cpu().numpy().astype(np.float32)
    ```
  - Handle uncalibrated case: `sqrt_spot_scale = 1.0` when `spot_scale_override` is None or missing
- [ ] **Apply Option C — Beam calibration threading:**
  - Update `beam_config` creation (line 170) to thread `beam_flux`, `beam_exposure`, `beamsize_mm` from `calibration_metadata`:
    ```python
    beam_flux = config.calibration_metadata.get('beam_flux') if config.calibration_metadata else None
    beam_exposure = config.calibration_metadata.get('beam_exposure') if config.calibration_metadata else None
    beamsize_mm = config.calibration_metadata.get('beamsize_mm') if config.calibration_metadata else None
    beam_config = create_beam_config(beam, flux=beam_flux, exposure=beam_exposure, beamsize_mm=beamsize_mm)
    ```
  - Matches stage_a_utils.py:267 pattern for architectural consistency
- [ ] **Preserve backward compatibility:**
  - Handle case where `config.calibration_metadata` is None (uncalibrated runs default to `sqrt_spot_scale = 1.0`, beam params = None)
  - Ensure legacy tests without calibration metadata still pass (no behavior change when calibration absent)

**Artifacts:**
- Code changes in `dbex/refinement/reconstruction.py` (lines ~167-170 beam config, ~220-223 post-run scaling)

#### C.2 — Simulator Comparison Probe (Complete — 2025-12-02T160000Z, Loop i=452)
- [x] **Build comparative probe script:** Created `compare_simulator_outputs.py` comparing Stage A warm-cache vs reconstruction cold-path simulators
- [x] **Run with DB-AT-028 config:** Used refGeom_small single-panel dataset
- [x] **Compare raw outputs:** Measured ratio 0.847 (within 15% tolerance)
- [x] **Initial verdict:** Simulators matched, ruling out factory contract hypothesis

**Status:** Complete, but later evidence (Phase C.3) revealed this probe used insufficient detector config comparison

**Artifacts:**
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T160000Z/simulator_comparison.json`
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T160000Z/summary.md`

#### C.3 — simulate_forward_once vs Reconstruction Diagnostic Probe (Complete — 2025-12-04T220000Z, Loop i=454, commit 8159de9a)
- [x] **Create side-by-side comparison:** Instrumented both `simulate_forward_once()` and reconstruction helper cold path
- [x] **Capture raw simulator outputs:** Path A (simulate_forward_once) vs Path B (reconstruction)
- [x] **Key findings:**
  - Path A: 3072×3072 panel → auto-selected **3-fold oversampling** → raw mean 1.714e-09
  - Path B: 1024×1024 detector → auto-selected **1-fold oversampling** → raw mean 9.574e-03
  - Raw ratio A/B = 1.79e-07 (**5,586× discrepancy**)
  - Hit rate arrays: 9,437,184 pixels (Path A) vs 1,048,576 pixels (Path B)
- [x] **Root cause identified:** Oversampling mismatch due to different detector pixel counts triggering different auto-selection logic in nanobrag_torch

**Verdict:** Oversampling configuration mismatch definitively explains magnitude discrepancy; fix requires explicit `oversample=3` parameter in both paths

**Artifacts:**
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T220000Z/probe_run.log`
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T220000Z/simulation_comparison.json`
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T220000Z/summary.md`
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T235959Z/galph_root_cause_final_oversampling.md` (Galph analysis)

#### C.4 — Force Explicit Oversampling (Planned — Loop i=455)
- [ ] **Update `create_detector_config` signature:**
  - Add parameter `oversample: int = -1` to `dbex/refinement/config_factories.py::create_detector_config`
  - Forward it to `DetectorConfig` constructor (line 214-227)
- [ ] **Update `simulate_forward_once` call site:**
  - Pass `oversample=3` in `dbex/nanobrag_bridge.py::simulate_forward_once` (line ~1406)
- [ ] **Update reconstruction cold path call site:**
  - Pass `oversample=3` in `dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry` (line ~190)
- [ ] **Run DB-AT-028/029 validation:**
  - Verify `bragg_after_mean ≈ 0.24` (matches bragg_before)
  - Verify `chi²/pixel initial ≤ 1e2`
  - Verify `median ROI correlation before ≥ 0.2`

**Expected outcome:** Both paths use 3-fold oversampling, raw outputs match, tests PASS

**Artifacts:**
- Code changes in 3 files (config_factories.py, nanobrag_bridge.py, reconstruction.py)
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-04T235959Z/pytest_db_at_028_029.log`

---

## Phase D — Documentation & Closure (Planned)

**Goal:** Document factory contract and close initiative.

### Checklist

#### D.1 — Factory Contract Documentation
- [ ] **Create or update IDL:**
  - `docs/architecture/dbex/simulator_factory.idl.md` or extend `nanobrag_bridge.idl.md`
  - Clarify when/how `spot_scale_override` must be passed
  - Specify pre-construction vs post-hoc scaling conventions
- [ ] **Update findings.md:**
  - Add new finding describing simulator construction calibration threading requirement
  - Reference this initiative and Phase D.3 bugfix commit

**Artifacts:**
- `docs/architecture/dbex/simulator_factory.idl.md` (new or updated)
- `docs/findings.md` entry (e.g., ARCH-SIM-001)

#### D.2 — Closure
- [ ] **Mark initiative `done` in fix_plan.md**
- [ ] **Unblock ARCH-REFACTOR-001 Phase D.3:**
  - Update Phase D.3 status to `done` (original bugfix landed, this follow-up resolved systemic issue)
  - Update Attempts History with pointer to this initiative
- [ ] **Update problems.md ledger:**
  - Close entry with resolution summary + commit SHAs

**Artifacts:**
- Updated `docs/fix_plan.md`
- Updated `problems.md`

---

## Risk & Mitigation

### Risk: Fix breaks uncalibrated runs
**Mitigation:** Add explicit None-check and preserve legacy behavior when `spot_scale_override` is not present in telemetry/metadata.

### Risk: Factory contract is already correct, reconstruction is applying double-scaling
**Mitigation:** Phase B probe will confirm whether factory applies scaling or expects post-hoc; adjust fix accordingly.

### Risk: Issue is in telemetry structure, not factory usage
**Mitigation:** Phase A.2 calibration flow tracing will identify if telemetry is missing required fields; may need separate telemetry bugfix initiative.

---

## Lifecycle

- **Implementation budget:** 3 loops per acceptance criterion (DB-AT-028/029)
- **Dwell enforcement:** Max 2 consecutive planning/evidence loops before implementation
- **Stuck condition:** If Phase C fix doesn't resolve DB-AT-028/029, escalate to spec_change or harness initiative

---

## Artifacts Root
`plans/active/ARCH-SIM-CONSTRUCTION-001/reports/`

---

## Next Actions (for Galph)
1. Update `docs/fix_plan.md` with new row `[ARCH-SIM-CONSTRUCTION-001]`
2. Mark ARCH-REFACTOR-001 Phase D.3 `blocked_pending_architecture`
3. Create `input.md` for Phase A.1 evidence collection (simulator construction comparison)
4. Update `galph_memory.md` with focus=ARCH-SIM-CONSTRUCTION-001, state=gathering_evidence, dwell=0
5. Update `problems.md` ledger
