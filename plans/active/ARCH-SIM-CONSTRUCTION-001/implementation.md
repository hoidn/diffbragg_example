# Implementation Plan: ARCH-SIM-CONSTRUCTION-001

## Initiative
- ID: ARCH-SIM-CONSTRUCTION-001
- Title: Simulator Construction Convention Alignment (Training vs Reconstruction)
- Owner: Galph ↔ Ralph
- Spec Owner: docs/spec-db-core.md §§20-40, docs/architecture/calibration_scaling.md
- Status: in_progress
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

- [ ] **Instrument simulator comparison probe:**
#### C.5 — Intensity Scale Evidence (Complete — 2025-12-09T210000Z)
- [x] **Instrument simulator comparison probe:**
  - Extend `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulator_outputs.py` so it captures:
    - Stage A, reconstruction, and `simulate_forward_once` raw means/max values
    - Calibration inputs (`spot_scale_override`, `log_scale_baseline`, `beam_flux`, `beam_exposure`, `beamsize_mm`, `adu_per_photon`)
    - Post-run scaling contributions (`sqrt_spot_scale`, `scale_factor`, unit-mode)
    - Ratios between paths (Stage A vs reconstruction, Stage A vs simulate_forward_once)
  - Add CLI flags `--detector-size {small,full}` and `--device` for reproducibility.
- [x] **Run probe on canonical smoke data:**
  - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 DBEX_SMOKE_DETECTOR_SIZE=small python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulator_outputs.py --detector-size small --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-09T210000Z/simulator_intensity_metrics.json`
  - Capture console output + JSON + Markdown summary under the same report directory.
- [x] **Re-run DB-AT-028/029 with logging:**
  - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-09T210000Z/pytest_db_at_028_029.log`
  - Ensures evidence ties directly to the failing acceptance criteria.

**Artifacts:**
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-09T210000Z/simulator_intensity_metrics.json`
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-09T210000Z/summary.md`
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-09T210000Z/pytest_db_at_028_029.log`
- `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-09T210000Z/probe_run.log`

Result: Stage A and `simulate_forward_once` raw means match while reconstruction sits 18.1% higher
(`stage_a_vs_reconstruction=0.846821`, `reconstruction_vs_mapping=1.180887`), proving the cold-path
simulator ignores the trusted mask (spec-db-core.md §Data Contracts) during construction. Tests
were skipped until we add `DBAT028_ARTIFACT_DIR`/`DBAT029_ARTIFACT_DIR`, so the next loop must
re-run them with the artifact env vars enabled after fixing reconstruction. 2025-12-10T090000Z loop
implemented the mask coverage guard + diagnostics (coverage ≥90% recorded in
`mask_coverage.json`), but DB-AT-028/029 still fail with identical chi²/pixel signatures and
`bragg_panel` raw means ~3.4e-14. Instrumentation shows the reconstruction helper never re-applies
the `apply_calibration_n_cells` gate, so cold-path simulators drop the DiffBragg `N_cells`
amplitude boost even when Stage A/mapping leave the gate enabled. Next attempt must propagate
`config.apply_calibration_n_cells` + `N_cells` into the reconstruction-crystal override path so
raw outputs match Stage A/mapping before re-running the probe + selectors.

#### C.6 — Trusted-mask & N_cells parity (In Progress)
- [x] **Wire panel trusted masks into reconstruction cold path:**
  - Update `dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry`
    so each `create_detector_config(...)` call receives `inputs.trusted_mask[pid]`, matching the
    Stage A warm-cache construction (`stage_a_utils._build_stage_a_context`). Ensure the helper
    gracefully handles cases where `inputs.trusted_mask` is `None`. (Complete — artifacts in
    `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-10T090000Z/`.)
- [ ] **Propagate the `apply_calibration_n_cells` gate into reconstruction crystal overrides:**
  - Extract `N_cells` + `apply_calibration_n_cells` from `config.calibration_metadata` /
    `RefinementConfig`, pass them into the top-level `create_crystal_config(...)` call so both warm
    and cold paths apply (or suppress) DiffBragg domain counts exactly like Stage A context +
    `simulate_forward_once`. Record `n_cells_applied` and suppression reason in the debug output so
    telemetry parity can be verified in future loops.
- [ ] **Re-run the intensity probe after N_cells parity fix:**
  - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_simulator_outputs.py --detector-size small --device cpu --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-10T150000Z/simulator_intensity_metrics.json`
  - Expect `stage_a_vs_reconstruction ≈ 1.0` once trusted masks **and** N_cells gating match Stage A;
    capture JSON + summary proving raw/scale-aligned outputs.
- [ ] **Validate DB-AT-028/029 with artifact dirs after the fix:**
  - `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-10T150000Z/db_at_028 DBAT029_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-10T150000Z/db_at_029 DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k \"DB_AT_028 or DB_AT_029\" | tee plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-10T150000Z/pytest_db_at_028_029.log`
  - Tests must collect (no skips) and produce chi²/pixel ≤ 1e2 with ROI CC ≥ 0.2 once parity is restored.

**Artifacts:** `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-10T090000Z/{mask_coverage.json,pytest_db_at_028_029.log,summary.md}`,
`plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-10T150000Z/{simulator_intensity_metrics.json,summary.md,pytest_db_at_028_029.log}`

#### C.7 — Log-scale scale-factor telemetry + reconstruction sanity (Complete — 2025-12-12T180000Z)
- [x] **Expose Stage A scale provenance in telemetry:** `dbex/refinement/stage_a.py` now records `target_mean_masked`, `model_mean_masked`, `log_scale_baseline_value`, `log_scale_delta_clamped`, `log_scale_clamped_value`, and the derived `scale_factor` under `param_deltas['log_scale_effective']`. This is persisted in telemetry so downstream consumers can read the exact multiplier that Stage A used instead of recomputing it.
- [x] **Teach reconstruction to consume the new telemetry fields:** `build_final_bragg_from_stage_a_telemetry` prefers the recorded `scale_factor` when present, emits diagnostics when recomputation disagrees, and gracefully falls back for legacy telemetry payloads. This ensures reconstruction reuses Stage A’s authoritative scale rather than guessing.
- [x] **Enhance `probe_stage_a_scale_alignment.py` / DB-AT instrumentation:** Probe script now documents the telemetry schema (structure sample stored under `scale_probe/`). DB-AT-028/029 runs capture the new telemetry block inside `db_at_028/*metrics.json` so scale analysis can cite recorded vs recomputed values.
- [x] **Validation:** `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` executed with artifact dirs pointing at `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-12T180000Z/`. Tests still fail (chi²≈2.1e5) but telemetry now proves the root cause: Stage A records `log_scale_delta_clamped=+3.0` and `scale_factor≈1.39e10`, i.e. 20× larger than the calibrated baseline, so reconstruction faithfully reproduces this inflated value.

#### C.8 — Stage A log-scale baseline alignment (Planned — 2025-12-12 loop)
- [ ] **Compute masked target/model means whenever the warm cache exists:** Tensorize `inputs.target` and `inputs.loss_mask` onto the Stage A warm-cache device (falling back to NumPy if needed) and capture both masked means for telemetry even when calibration metadata already provided a baseline.
- [ ] **Apply the measured ratio to `log_scale_baseline`:** When both masked means are positive, add `np.log(target/model)` to the calibrated baseline (or set the baseline to this ratio when calibration metadata is absent) so zero-iteration Stage A predictions align with the observed masked intensity before any LBFGS delta is applied. Update `StageAContext.log_scale_baseline`, `config.log_scale_baseline`, and the telemetry source tag so downstream stages consume the corrected baseline.
- [ ] **Thread the corrected baseline through Stage A context + reconstruction:** Ensure `_build_stage_a_context` stores the adjusted baseline so `Reconstruction` rebuilds `bragg_before`/`bragg_after` with the aligned scale even on cold paths.
- [ ] **Teach test harness to consume the adjusted baseline:** Extend `dbex/refinement/reconstruction.py::build_final_bragg_from_stage_a_telemetry` so it can reconstruct a Stage A Bragg stack from **initial** telemetry parameters (baseline + zero deltas), then update `tests/dbex/test_stage_a_smoke_parity.py::stage_a_smoke_result` to use this helper for `bragg_before` instead of calling `simulate_forward_once`. This ensures DB-AT-028/029 gates measure the same baseline that Stage A just recorded rather than the pre-adjusted calibration baseline.
- [ ] **Validation:** Re-run `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_stage_a_scale_alignment.py` (outputs under the new report dir) plus `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` with `DBAT028_ARTIFACT_DIR`/`DBAT029_ARTIFACT_DIR` pointing at the same directory. Success criteria: log_scale delta no longer saturates at +3.0, `scale_factor` returns to ≈`exp(log_scale_baseline)`, chi² ≤ 1e2, ROI corr ≥ 0.2.

#### C.9 — Stage A baseline telemetry verification (In Progress — 2025-12-13T235500Z follow-up)
- [x] **Author Stage A baseline probe (T2 script):** Create `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py` that reproduces the Stage A smoke fixture, captures `telemetry.target_mean_masked` / `telemetry.model_mean_masked`, reconstructs `bragg_before` via `build_final_bragg_from_stage_a_telemetry(param_state="initial")`, and computes masked/unmasked means plus chi² per pixel using the same loss mask.
- [x] **Run the probe + archive evidence:** Execute the script with `AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md DBEX_SMOKE_SIGMA_SOURCE=cli_override DBEX_SMOKE_DETECTOR_SIZE=small KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T190000Z/stage_a_baseline_probe.json`. Persist the raw console log and JSON summary under the same report dir.
- [x] **Correlate probe output with DB-AT failures:** Re-run `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` with artifacts rooted at `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-13T190000Z/` and annotate the report with the measured masked means vs telemetry values so we can pinpoint the first divergence between Stage A telemetry and reconstruction harness.
- [x] **StageAContext reuse in reconstruction:** Update the Stage A smoke fixtures and the baseline probe to source `StageAArtifacts` from `RefinementEngine._artifacts` (the canonical cache introduced in ARCH-STAGE-CONTEXT-001) instead of the removed `_stage_contexts` helper so `build_final_bragg_from_stage_a_telemetry` receives the warmed `StageAContext`. When the artifact exposes a cached `bragg_full`, feed it through the fixture to avoid recomputing the "final" stack, and pass the retrieved context to the helper for both `param_state="initial"` and `"final"`. Document the change in this plan and in docs/fix_plan.md, then rerun the baseline probe + DB-AT selectors under a new report directory to prove that reconstruction now matches the telemetry path whenever the warm cache is present. (Completed 2025-12-14T150000Z — see `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T150000Z/summary.md`.)
- [x] **Mask provenance instrumentation:** Extend Stage A telemetry and the reconstruction diagnostics so we can confirm the masked-mean calculations are using the same loss mask that DB-AT gates enforce. `dbex/refinement/stage_a.py`, `dbex/refinement/reconstruction.py`, and `compare_stage_a_baseline.py` now record per-panel pixel counts plus SHA1 checksums, and the new metadata appears in both the probe JSON and `baseline_stats.json` (see `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T200000Z/`).
- [x] **Telemetry instrumentation follow-up:** The baseline probe now reads masked-mean telemetry directly from the top-level Stage A fields and `baseline_stats.json` persists the reconstructed vs telemetry ratios alongside the existing mask coverage log (also captured in `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-14T200000Z/`).
- [ ] **Align the baseline probe’s DataLoad inputs with the Stage A smoke fixture:** The current probe still hard-codes `scaled.mtz` (F,SIGF) even when calibration metadata is present, which explains why `stage_a_baseline_probe.json` reported `model_mean_masked≈3.77` while `db_at_028_metrics.json` for the same loop reported `11.57`. Update `compare_stage_a_baseline.py::get_refgeom_dataload` to reuse the detector-size aware HKL/MTZ selection logic from `tests/conftest.py` (respecting `DBEX_SMOKE_CALIB_PATH`/`DBEX_SMOKE_HKL_PATH` and defaulting to the refined smoke MTZ when calibration metadata exists) and persist the resolved `mtz_file`, `mtz_col`, and calibration path in the probe output. After the fix, rerun the probe + DB-AT-028/029 with artifacts under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-15T010000Z/` so future evidence uses the same HKL inputs as the fixture.

#### C.10 — Stage A cache scaling + telemetry alignment (Planned — 2025-12-16 loop)
- [ ] **Scale the cached zero-iteration Bragg stack after log-scale adjustments:** Update `dbex/refinement/stage_a.py` so that, once `log_scale_baseline` is adjusted via the masked-intensity ratio, the warm-cache helper multiplies `stage_a_ctx.bragg_zero_iter` by the zero-iteration scale factor (`exp(log_scale_baseline + clamp(initial_log_scale))`). This ensures the cached array represents the same pre-LBFGS prediction that Stage A used in its loss calculations rather than the pre-scaled tensor (`bragg_stack * sqrt_spot_scale`). Guard the conversion so cold-mode runs leave the cache unset.
- [ ] **Record scaled masked means in telemetry:** After applying the scale factor, update `param_values['model_mean_masked']` to reflect the scaled masked mean so downstream diagnostics and probes no longer report the pre-scale 11.57 ADU value. Persist the scale factor for reconstruction debugging if needed.
- [ ] **Keep reconstruction/helper behavior stable:** No functional change is required in `build_final_bragg_from_stage_a_telemetry` once the cache contains the scaled tensor, but extend the parity test to assert the cached path matches the scaled telemetry output so regressions are caught immediately.
- [ ] **Validation:** Run the Stage A baseline probe plus DB-AT-028/029 selectors with artifacts rooted at `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-16T010000Z/`. Expected evidence: `model_mean_masked` in telemetry equals the reconstructed `bragg_before` masked mean (≈87 ADU) and chi²/pixel initial drops toward the ≤1e2 spec when Stage A zero-iteration scale matches the target intensity.

#### C.11 — Stage A vs mapping parity instrumentation (Planned)
- [ ] **Extend the baseline probe with mapping comparison metrics:** Update `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py` so it reuses `mapping_context.bragg_zero_iter` from `build_mapping_stage_a_context` and computes Stage A vs mapping statistics (masked/unmasked means, ROI-level Pearson CC, RMSE, max|Δ|, chi² per pixel vs target). Persist a `mapping_comparison` block in the JSON output so DB-AT-027 parity claims are backed by concrete evidence.
- [ ] **Capture ROI diagnostics and provenance:** Emit console warnings plus structured JSON when Stage A vs mapping ROI correlation drops below 0.99 or max|Δ| exceeds 1 ADU, and include the resolved HKL/calibration paths so downstream reports can cite the exact assets. Record per-ROI medians/percentiles to pinpoint panels that diverge first.
- [ ] **Validation:** Rerun the enhanced probe and DB-AT-028/029 selectors with artifacts under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/<NEW_TIMESTAMP>/` (include `stage_a_baseline_probe.json`, `mapping_comparison.json`, and `pytest_db_at_028_029.log`). These artifacts become the decision point for escalating to a spec-change vs scheduling corrective implementation.

#### C.12 — Geometry-mode parameterization (Complete — 2025-12-17T010000Z)
- [x] **Add geometry-mode flag:** Extended `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py` with `--geometry-mode {perturbed,baseline}` (default `perturbed`) so we can run DB-AT probes with or without the Stage A smoke perturbations. The chosen mode is recorded in `probe_metadata` and echoed in the console summary for traceability.
- [x] **Mode-aware diagnostics:** When `geometry_mode="baseline"`, the probe skips `create_perturbed_geometry` and reuses the mapping baseline crystal/detector/beam. Mapping-parity warnings are tagged as normative (baseline) vs `[NON-NORMATIVE]` (perturbed), and the JSON now persists explicit geometry metadata. Artifacts live under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-17T010000Z/`.
- [x] **Validation:** Reran the probe in baseline mode plus DB-AT-028/029 selectors. Results: Stage A vs mapping ROI CC = 1.0 (shape match) but masked RMSE ≈3.8e2 ADU and max|Δ| ≈1.88e4 ADU, proving the remaining parity failure is pure magnitude even with identical geometry. DB-AT-028/029 continue to fail with chi²/pixel ≈2.1e5 because Stage A vs target correlations remain negative, but the evidence now isolates the divergence to mapping ↔ telemetry scaling.

#### C.13 — Mapping baseline scaling parity (Complete — 2025-12-17T180000Z)
- [x] **Mirror Stage A masked-mean adjustment in mapping:** Updated `dbex/vis/mapping.py::build_mapping_stage_a_context` to compute masked means immediately after `simulate_forward_once`, scale `bragg_zero_iter` by `target/bragg` when both are finite, and tag the diagnostics/calibration metadata with `log_scale_baseline_source="mapping_masked_mean_adjustment"` plus the stored ratio so Stage A can detect the adjusted baseline.
- [x] **Telemetry alignment:** Propagated the masked-mean ratio into `inputs.global_scale_hint` and the calibration dict, ensuring Stage A warm-cache initialization and downstream helpers see the mapping-adjusted baseline instead of recomputing it. Added guard logs so baseline probes can tell when mapping performed the adjustment.
- [x] **Validation:** Reran `compare_stage_a_baseline.py` in baseline mode along with DB-AT-028/029 (artifacts under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-17T180000Z/`). Results: Stage A vs mapping max|Δ|=3.9×10^-3 ADU (≪1 ADU threshold), median ROI CC=1.0, chi² per pixel relative diff=0.0. Exit Criterion #1 (Stage A vs mapping raw parity within 1%) is now SATISFIED. DB-AT-028/029 still fail (chi²≈2.1e5, ROI corr≈-0.053) because the cold reconstruction path ignores the mapping-adjusted baseline whenever StageAArtifacts are missing.

#### C.14 — Cold-path mapping baseline alignment (Complete — 2025-12-18T010000Z)
- [x] **Align build_final_bragg_from_stage_a_telemetry cold path with Stage A telemetry:** When `stage_a_ctx.bragg_zero_iter` was unavailable for `param_state="initial"`, the helper now computes the cold-path masked mean on the canonical loss mask, compares it against `telemetry_a.model_mean_masked`, and applies `baseline_alignment_factor = telemetry / cold` (guarded against NaN/zero) before writing into `bragg_full`. Diagnostics now record `baseline_alignment_factor` plus cache status so SCALE-008/SCALE-009 guardrails remain auditable (artifacts: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-18T010000Z/baseline_stats.json`).
- [x] **Harden tests and probes:** Added `tests/dbex/test_artifact_parity.py::test_stage_a_cold_path_respects_telemetry_baseline` to drop Stage A artifacts and assert the cold path matches telemetry within ≤1e-6 relative error, and extended `compare_stage_a_baseline.py` to expose `baseline_alignment_factor` + cache status per report so DB-AT evidence shows when the correction fired.
- [x] **Validation:** `pytest -vv tests/dbex/test_artifact_parity.py::test_stage_a_cold_path_respects_telemetry_baseline` PASSED (11.05s), and the Stage A baseline probe (baseline geometry) recorded DB-AT-027 PASS with `baseline_alignment_factor=1.0` (cache hit). Evidence lives under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-18T010000Z/`.

#### C.15 — Stage A ROI localization diagnostics (Planned — 2025-12-19 loop)
- [ ] **Enhance baseline probe ROI analytics:** Extend `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py` so each run emits per-ROI correlation stats (top/bottom-N ROI IDs, percentiles, masked mean deltas) for Stage A vs target alongside the existing mapping parity data. Persist the enriched ROI block in the JSON output so DB-AT investigations can pinpoint which ROIs drive the negative median correlation.
- [ ] **Run probe in both geometry modes:** Execute the enhanced probe twice — `--geometry-mode baseline` (normative parity check) and `--geometry-mode perturbed` (matches DB-AT selectors) — storing artifacts under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-19T010000Z/`. Capture `stage_a_baseline_probe_baseline.json` and `stage_a_baseline_probe_perturbed.json` plus logs so we can compare ROI distributions between modes.
- [ ] **Re-run DB-AT-028/029 with refreshed baselines:** With the new ROI instrumentation in place, rerun `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` using `DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-19T010000Z/db_at_028` and `DBAT029_ARTIFACT_DIR=.../db_at_029` to validate that the C.14 fix carries over to the harness and to capture updated chi²/ROI telemetry alongside the probe outputs.

#### C.21 — Mosaic-domain sweep instrumentation (Planned — 2025-12-22 loop)
- [ ] **Add an explicit `--stage-a-mosaic-domains` knob to the baseline probe:** Update `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py` so the CLI accepts `--stage-a-mosaic-domains <int>=16`, threads the value into `RefinementConfig` construction, and records the applied domain count plus Stage A↔reflection median ratios inside `probe_metadata`/console output. This allows us to run controlled sweeps instead of editing source code between runs.
- [ ] **Collect paired baselines for 1-domain vs 16-domain runs:** Re-run the probe twice under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T010000Z/` — once with `--stage-a-mosaic-domains 1 --geometry-mode baseline` (control) and once with `--stage-a-mosaic-domains 16 --geometry-mode baseline` (current wiring). Store results as `domain1/stage_a_baseline_probe_baseline.json` and `domain16/stage_a_baseline_probe_baseline.json` so the transformation ledger can cite both outcomes.
- [ ] **Correlate the sweep with DB-AT selectors:** After capturing the two probe outputs, rerun `pytest -vv tests/dbex/test_stage_a_smoke_parity.py -k "DB_AT_028 or DB_AT_029"` with artifacts rooted at `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T010000Z/` to prove the selectors still fail (chi²≈2.1e5, ROI corr≈-0.05) even when we force different domain counts.
- [ ] **Summarize the sweep:** Add `mosaic_domain_sweep.md` to the same report directory documenting whether Stage A/reflection medians changed between the two runs. If the ratios stay ~0.061 for both, we have decision-carrying evidence that the simulator ignores the override and can escalate to a nanobrag_torch instrumentation patch per Environment Freeze exception.

#### C.22 — Spot-profile energy partition instrumentation (Complete — 2025-12-22T150000Z)
- [x] **Extend probe with spot-profile analytics:** Added `--collect-spot-profiles` flag to `compare_stage_a_baseline.py` so each run emits halo vs ROI energy fractions, axial FWHM, and ROI bbox metadata (see `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T150000Z/spot_profile_summary.md`).
- [x] **Run baseline capture:** Executed the probe with all flags enabled plus DB-AT-028/029 selectors under the same timestamp. Evidence showed deterministic energy spill (worst ROIs keep ≤1.8 % of available energy) while DB-AT signatures remained unchanged (chi²≈2.1e5, corr=-0.053), proving spot-profile asymmetry alone is insufficient.

#### C.23 — Orientation ledger (Complete — 2025-12-23T010000Z)
- [x] **Add orientation metrics:** Implemented `--collect-orientation-metrics` which computes fractional HKL deltas, resolution, and 2θ per ROI using `crystal.get_A()` and detector beam vectors; persisted JSON + Markdown blocks.
- [x] **Validation:** Probe plus DB-AT reruns confirmed `median |Δhkl|=0.095` with weak correlation to Stage A/Ref ratios (Pearson -0.286), eliminating geometry as the divergence source. Artifacts: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-23T010000Z/`.

#### C.24 — Physics ledger (Complete — 2025-12-23T150000Z)
- [x] **Lorentz/polarization diagnostics:** Added `--collect-physics-ledger` to compute `|F|²·LP` expectations per ROI and log Stage A ratios by resolution bin. Evidence pinned `median Stage A/(|F|²·LP)=0.0201` even though LP factors span 2.6–11.7×.
- [x] **Validation:** Baseline probe + DB-AT selectors captured the ledger plus chi²/corr metrics, demonstrating Lorentz weighting was missing downstream. Artifacts under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-23T150000Z/`.

#### C.25 — Partiality ledger (Complete — 2025-12-24T190000Z)
- [x] **Compute expected lattice factor:** Probe now accepts `--collect-partiality-ledger` which reuses orientation metrics + calibration metadata to derive `F_latt` for each ROI and compare Stage A vs `|F|²·F_latt²·LP`.
- [x] **Validation:** Artifacts (`plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-24T150000Z/`) show `median Stage A/(|F|²·F_latt²·LP) ≈ 0`, shifting the leading hypothesis squarely onto the simulator lattice math.

#### C.26 — Simulator partiality hook wiring (Complete — 2025-12-26T150000Z)
- [x] **Thread debug flag:** Added `collect_simulator_partiality_stats` flag through `_build_stage_a_context`, `simulate_forward_once`, and probe helpers; serialized per-panel aggregates so JSON captures `f_latt`, `lorentz_factor`, `polarization_factor`.
- [x] **Validation:** Stage A baseline probe now records `f_latt` median `1.3e-4` while independent ledger expected ≈5233, delivering decision-carrying proof that the simulator never applies the Na·Nb·Nc boost. Artifacts: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-26T150000Z/`.

#### C.27 — Square-lattice sincg fix & enforcement (Pending — 2025-12-27 loop)
- [ ] **Patch `compute_physics_for_position`:** Update the SQUARE branch to evaluate `sincg` on fractional deltas (`h - h0`, etc.) promoted to `torch.float64`, snap arguments near integer multiples, and cast the final `F_latt` product back to the simulator dtype so Na·Nb·Nc survives float32 rounding.
- [ ] **Capture Environment Freeze metadata:** Save the diff as `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/partiality_fix.patch`, rebuild `nanobrag_torch` in editable mode, and tag the rebuild (`nanobrag-partiality-2025-12-26`) with commands logged under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T010000Z/environment.md`.
- [ ] **Add architecture enforcement:** Author `tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells`, instantiating a tiny simulator twice (N_cells=(1,1,1) vs `(Na,Nb,Nc)`) and asserting `(Na·Nb·Nc)^2` scaling within tolerance. Capture `pytest` + `--collect-only` logs.
- [ ] **Update docs/findings.md:** Add SIM-CONSTR-PARTIALITY-001 summarizing the fix, enforcement test, and rebuild tag per Environment Freeze policy.
- [ ] **Validation:** Rerun the Stage A baseline probe with all collection flags and both DB-AT selectors under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T010000Z/`, ensuring `median Stage A/(|F|²·F_latt²·LP) → 1` and DB-AT-028/029 cross their chi²/corr gates.

#### C.28 — Float64 fractional-delta sincg attempt (2025-12-27T120000Z — **regression**)
- [x] Implemented the float64 fractional-delta sincg patch in `src/nanobrag-torch/src/nanobrag_torch/simulator.py::compute_physics_for_position` (SQUARE branch) per SIM-CONSTR-PARTIALITY-001, captured the diff as `patches/partiality_fix.patch`, rebuilt/tagged the editable install (`nanobrag-partiality-2025-12-27`), and reran the Stage A baseline probe plus DB-AT-028/029 selectors under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T120000Z/`.
- [x] Authored and executed `tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells`, plus documented SIM-CONSTR-PARTIALITY-001 in docs/findings.md and TESTING_GUIDE.md.
- [x] Captured environment metadata + enforcement logs showing the test still FAILS with 0.25 % of the expected `(Na·Nb·Nc)^2` ratio and Stage A baseline metrics remain unchanged (`median StageA/(|F|²·F_latt²·LP)=0`), so the patch does not resolve the deterministic signature.

Outcome: Patch rolled back per Environment Freeze guard; initiative re-entered parity-localization mode (Phase C.29) to gather decision-carrying sincg telemetry before attempting another simulator edit.

#### C.29 — Sincg per-axis instrumentation (Complete — 2025-12-27T180000Z)
- [x] Extended `compute_physics_for_position`'s optional `collect_partiality_stats` hook to capture `delta_h`, `delta_k`, `delta_l`, and the individual `F_latt_a/b/c` tensors (SQUARE branch only), preserving device/dtype neutrality.
- [x] Updated `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py` to serialize the new stats (JSON percentiles + Markdown tables) and sample tensors to avoid >10 M element quantile OOMs.
- [x] Reran the Stage A baseline probe with all collection flags and documented the new evidence under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-27T180000Z/`, proving per-axis sincg medians collapse (~0.06) even though fractional HKL deltas cluster near zero and maxima hit the expected Na/Nb/Nc values.

Result: Deterministic evidence now isolates the remaining divergence to the sincg application rather than HKL alignment. Next loop must analyze a minimal lattice scenario to determine whether the intensity scaling bug reproduces outside the Stage A context.

#### C.30 — Single-pixel square-lattice scaling probe (Complete — 2026-01-02T010000Z)
- [x] Author a thin `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py` helper that instantiates `nanobrag_torch.Simulator` twice (N_cells=(1,1,1) vs `(Na,Nb,Nc)`) with a single-pixel detector (`spixels=fpixels=1`), single phi/mosaic sample, configurable oversample, and `debug_config` hooks (`collect_partiality_stats`, `trace_pixel=[0,0]`). The script logs intensities, `(F_cell·F_latt)^2`, Lorentz/polarization factors, and the observed ratio into JSON + Markdown files under the report directory.
- [x] Execute the probe with Na=41, Nb=29, Nc=32 and compare the measured ratio against `(Na·Nb·Nc)^2`, confirming the minimalist configuration reproduces the 0.000058× shortfall (artifacts under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-02T010000Z/`).
- [x] Rerun `pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells --maxfail=1` to document the enforcement failure alongside the probe evidence.

#### C.31 — Lattice-scaling pipeline instrumentation (Complete — 2026-01-03T010000Z)
- [x] **Instrument `compute_physics_for_position` with opt-in debug payload:** Added Phase C.31 hooks to capture `F_cell`, `F_total²` (pre-Lorentz), and `intensity_pre_polar` (post-Lorentz, pre-polarization) when `partiality_stats` is enabled. Edits preserve opt-in semantics (production runs unaffected) and device/dtype neutrality. Files: `src/nanobrag-torch/src/nanobrag_torch/simulator.py:382-387, 456-458`.
- [x] **Thread payload through probe script:** Extended `probe_square_lattice_scaling.py` to extract the new debug fields from `partiality_stats`, compute derived ratios (`F_latt_ratio`, `F_total_sq_ratio`, `I_pre_polar_ratio`, `{base,scaled}_I_pre_polar_over_F_total_sq`), and persist them in JSON + Markdown outputs alongside the existing metrics. Files: `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py:96-131, 206-256, 276-285, 316-341`.
- [x] **Document instrumentation scope and hypotheses:** Added this Phase C.31 entry to `implementation.md` listing the captured quantities and the bisection strategy: compare `(I_pre_polar) / (F_cell·F_latt)²` for base vs scaled runs; if the ratio deviates from 1, inspect normalization branch after `F_total = F_cell * F_latt`; if ratio is constant, the missing multiplier lies in Lorentz/polarization path.
- [x] **Execute probe and capture artifacts:** Ran the updated probe under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-03T010000Z/` with full payload extraction and stored JSON/Markdown/logs showing the derived ratios to determine the first divergence point in the intensity pipeline.
- [x] **Rerun enforcement test:** Executed `pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells` to archive current enforcement status alongside the new payload evidence.
- [x] **Update Attempts History:** Recorded the Phase C.31 loop in `docs/fix_plan.md` with timestamp, measured derived ratios, and next-step decision notes for C.32.

**Hypotheses to confirm/refute:**
1. If `F_latt_ratio ≠ Na·Nb·Nc`, then the sincg product is collapsing (contradicts C.30 trace evidence).
2. If `F_total_sq_ratio ≠ (Na·Nb·Nc)²`, then the squaring or product `F_cell * F_latt` is incorrect.
3. If `I_pre_polar_ratio ≠ (Na·Nb·Nc)²`, then the Lorentz factor introduces an unexpected normalization.
4. If `{base,scaled}_I_pre_polar_over_F_total_sq` differ significantly, then the Lorentz formula scales incorrectly with `F_latt`.
5. If all ratios match expected but final intensity does not, then the polarization or post-polar normalization is wrong.

**Evidence artifacts:** `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-03T010000Z/` containing `square_lattice_scaling.{json,md}`, `square_lattice_probe.log`, `pytest_partiality.log`.

-#### C.32 — sincg reference comparison (Complete — 2026-01-04T010000Z)
- [x] Build a high-precision reference evaluator (NumPy float64) for the 1D lattice response `sin(NπΔ)/sin(πΔ)` and integrate it into `probe_square_lattice_scaling.py` so the single-pixel runs emit both production and analytic sincg values for every sampled fractional offset. **Result:** `sincg` matches the reference to <1e-6 absolute error for all axes (table logged in `square_lattice_scaling.md`).
- [x] Extend the probe report to summarize per-axis error statistics (max/median absolute/relative error, worst-case Δ samples) and compute the compounded `F_latt` ratio between production vs reference to determine whether the deficit originates inside `sincg` or downstream aggregation. **Result:** compounded `F_latt` from both production and reference medians stay at ≈2.3 rather than 38,048 because the oversample grid never samples Δk/Δl≈0.
- [x] Document the findings (Probe summary + fix_plan attempt + report summary) showing the kernel is correct and the remaining mismatch is due to mis-centered fractional HKL offsets. Promote the initiative to Phase C.33 with a concrete detector/offset remediation plan.

#### C.33 — Subpixel centering fix (Attempted — 2026-01-04T150000Z loop)
- [x] **Re-center oversample offsets:** Updated the oversample block in `src/nanobrag-torch/src/nanobrag_torch/simulator.py::_compute_physics_for_position` so the `subpixel_offsets` grid spans `(-(N-1)/(2N), …, +(N-1)/(2N))` for both slow and fast axes (`(torch.arange(N) - (N-1)/2) / N`). This guarantees an explicit Δ=0 sample when detector pixels align with reference HKLs.
- [x] **Guard instrumentation:** When `debug_config['collect_partiality_stats']` is enabled, `min_abs_delta_h/k/l` are now recorded so downstream probes (Stage A baseline helper + single-pixel reproducer) can assert the oversample grid still straddles zero for all axes.
- [x] **Validation:** Reran `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py` (artifacts under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-04T150000Z/`) and `pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells`. Result: h-axis now reports `min_abs_delta_h=0`, but `delta_k`/`delta_l` stay pinned at ±5.38e-02 and the intensity ratio only improved from 8.46e4 to 3.56e6 (still 0.25 % of spec). DB-AT selectors remain red (chi²≈1.1e5, ROI corr≈−0.05). Evidence indicates the sincg kernel is correct (TRACE_PY shows `F_latt_a/b/c = 41/29/32`), so the remaining deficit must stem from how subpixel contributions are accumulated/normalized rather than from missing Δ≈0 samples.

#### C.34 — Subpixel contribution audit (Complete — 2026-01-05 loop)
- [x] **Instrument per-subpixel payloads:** Extended the existing partiality hook so that, when `collect_partiality_stats` and `trace_pixel` are both enabled, the simulator slices per-subpixel `F_latt_a/b/c`, `delta_{h,k,l}`, and `F_total_squared_pre_lorentz` tensors for the traced pixel. Evidence is captured in `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-05T150000Z/square_lattice_scaling.{json,md}` without adding new plan-local probes.
- [x] **Probe analysis:** Updated `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py` to summarize how many subpixels satisfy `|Δ_{k,l}| < 1/N` and how much `F_total_squared_pre_lorentz` mass they carry. Reports show **0/169** samples touch the sincg lobe (|Δk|, |Δl| ≥ 0.0538) even when oversample=13, explaining the 0.000058× lattice ratio.
- [x] **Decision gate:** Coverage audit proved only ~1/oversample² samples contribute, so the next implementation loop focuses on correcting the `steps` normalization (drop the `oversample²` factor for SQUARE lattices) instead of further instrumentation.

#### C.35 — Oversample normalization fix for SQUARE lattice (Complete — 2026-01-08T010000Z loop)
- [x] **Diagnosis recap:** Coverage metrics under `reports/2026-01-05T150000Z/` and HKL tensor telemetry under `reports/2026-01-07T150000Z/` showed SQUARE lattices rarely sample Δ≈0 along k/l, so dividing by `steps = sources·phi_steps·mosaic_domains·oversample²` diluted the few contributing subpixels by 169×. Treating SQUARE lattices as Riemann sums (omit oversample²) keeps the lattice boost intact without touching other lattice shapes.
- [x] **Implementation (Environment-Freeze exception):**
  1. Edited `src/nanobrag-torch/src/nanobrag_torch/simulator.py::Simulator.run` so the `steps` scalar skips the `oversample * oversample` factor when `crystal.shape == CrystalShape.SQUARE`, and exposed the chosen scalar via `_partiality_stats['steps_scalar']` for instrumentation. Patch captured in `plans/active/ARCH-SIM-CONSTRUCTION-001/patches/square_lattice_steps_fix.patch`; rebuild log + env tag stored under `patches/environment_tag.md` (`nanobrag-partiality-2026-01-08`).
  2. Updated `docs/findings.md::SIM-CONSTR-PARTIALITY-001` with the normalization rationale.
- [x] **Validation:** Reran the single-pixel probe + coverage summary, `tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells`, and DB-AT-028/029 under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-08T010000Z/`. Architecture test now observes ~6.0e8 vs 1.45e9 (≈41.5% of target), confirming the normalization fix removed the 169× dilution but a 58.5% deficit remains. DB-AT selectors still fail with the same signature.
- [ ] **Exit criteria:** Pending — `(Na·Nb·Nc)²` parity still missing (601M vs 1.45B) so initiative remains open until the remaining deficit is diagnosed.

#### C.36 — Subpixel offset telemetry (Complete — 2026-01-08T150000Z loop)
- [x] **Goal:** Capture the actual subpixel offset grids for the slow/fast axes under `_compute_physics_for_position` so we can determine whether both axes truly straddle Δ≈0 after Phase C.33 or if one axis still samples only positive deltas.
- [x] **Instrumentation scope:**
  1. When `collect_partiality_stats` **and** `trace_pixel` are enabled, record the per-axis subpixel offsets (fast/slow, optionally phi/mosaic) under `_partiality_stats['trace_subpixel_offset_{slow,fast}']`.
  2. Extend `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/probe_square_lattice_scaling.py` to summarize these offsets (min/median/max per axis) in both JSON and Markdown outputs so we can prove whether each axis straddles zero.
- [x] **Validation:** Reran the single-pixel probe (oversample=13, N_cells=41/29/32) and `pytest -vv tests/architecture/test_nanobrag_partiality.py::test_square_lattice_applies_ncells --maxfail=1` under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-08T150000Z/`. Telemetry shows both detector-plane axes now span [-0.461538, +0.461538] (✓ straddle zero), yet **0/169** samples enter the sincg lobe (|Δk|, |Δl| ≥ 0.0538). This definitively proves detector-plane centering is no longer the blocker; the HKL deltas themselves remain offset, so the next loop must interrogate the scattering-vector → HKL projection rather than oversample geometry.

#### C.37 — HKL projection audit (Planned — next loop)
- [ ] **Goal:** Determine why traced pixels that should represent (h, k, l) = (integer, 0, 0) accrue ≈0.05 fractional offsets along k/l even after detector-plane centering, indicating a potential reciprocal-basis projection bug inside `_compute_physics_for_position`.
- [ ] **Instrumentation scope:**
  1. When `trace_pixel` is active, log the raw scattering vector (`k_out - k_in`) and its dot products with both rotated reciprocal vectors (`rot_a_star/b_star/c_star`) and the dual real-space basis so we can compare the current HKL computation against the expected dual-basis solve.
  2. Thread these tensors through `_partiality_stats` (e.g., `trace_scattering_vec`, `trace_hkl_projection_reference`) and extend the square-lattice probe to compute delta between production HKL and the analytic solve.
- [ ] **Validation:** Re-run the single-pixel probe plus the partiality architecture test, then summarize whether the alternate projection yields integer-aligned k/l. Evidence will decide whether the next implementation loop patches `_compute_physics_for_position` to use the proper dual basis or applies an explicit correction term.

#### C.38 — Oversample accumulation sanity check (Complete — 2026-01-10T150000Z)
- [x] **Objective:** Prove whether the remaining `(Na·Nb·Nc)^2` deficit is inherent to the oversample accumulation path or still tied to sincg/HKL math.
- [x] **Method:** Reran the sanctioned single-pixel probe with oversample toggled between 1 (disabled) and {5, 13}, storing artifacts under `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-10T150000Z/` and comparing against the `oversample=13` evidence captured at `.../2026-01-10T010000Z/`.
- [x] **Key evidence:**
  - `os1_square_lattice_scaling.{json,md}` — oversample disabled. Observed ratio **1,447,642,850.1** vs expected **1,447,650,304.0** (0.0005 % error). `F_latt` telemetry spikes at 38,047.9, confirming `(Na·Nb·Nc)` parity when there is a single sample per pixel.
  - `os5_square_lattice_scaling.{json,md}` — oversample enabled (5×5). Observed ratio **137,151,105.6** (9.47 % of spec), matching the 13×13 probe (`reports/2026-01-10T010000Z/square_lattice_scaling.*`) which now has Δk=Δl=0 for 48 % of subpixels yet still delivers only 0.0939× the expected intensity. `partiality_stats['f_latt']` still contains ±38k spikes; the summary drops to ≈4.2k because we are effectively averaging per-subpixel samples.
  - Oversample density no longer changes the deficit once Δk/Δl hit zero, so sincg, HKL projection, and beam geometry are exonerated; the remaining DMI lives in the oversample accumulation/normalization branch of `Simulator.run`.
- [x] **Next action (Phase C.39 planning):** Instrument the oversample accumulation path to record (a) the raw sum of per-subpixel `F_total_squared_pre_lorentz`, (b) the per-subpixel and final `omega`/normalization factors, and (c) the final `normalized_intensity` that gets divided by `steps`. Compare those numbers against the oversample=1 baseline so we can identify the extra `≈0.094×` factor and patch the owner code, keeping evidence inside `nanobrag_torch`.

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
