# Input for Loop i=114

## Summary
Diagnose calibration_metadata threading break causing Phase A.2 cold-path test to see None instead of spot_scale_override, producing 2.83× scale mismatch despite canonical API refactor.

## Mode
none

## ActionType
evidence_collection

## DecisionStatus
exploring

## InitiativeType
architecture

## Focus
ARCH-IMPL-CONFORMANCE-001 — Architecture / Implementation Contract Alignment

## Branch
integration

## Mapped tests
- `tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path` (diagnostic, expect FAIL with detailed logging)
- `tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale` (warm-cache regression check, expect PASS)

## Artifacts
`plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T090000Z/`

## Findings Applied (Mandatory)
- **SCALE-002** (docs/findings.md:39): DiffBragg spot_scale_override re-applied as sqrt factor post-simulation. Canonical owner API is `dbex/refinement/scaling_utils.py::apply_sqrt_spot_scale`.
- **SCALE-008** (docs/findings.md:42): Stage A warm-cache baseline authority. Calibration metadata must thread from simulate_forward_once → Stage A context → reconstruction helpers.
- **SCALE-009** (docs/findings.md:43): Reconstruction cold path must match Stage A scaling when param_state="initial". Current status: VIOLATED (64.6% rel_error, 2.83× scale factor drift).
- **ARCH-FACTORY-001** (docs/findings.md:90): create_unified_simulator is forward-only factory, separate from refinement closure paths. Used by reconstruction cold path at reconstruction.py:245-324.

## Pointers

### Spec/Arch References
- `docs/spec-db-core.md:60-140` — Simulator construction and calibration contracts
- `docs/architecture/calibration_scaling.md:14` — Calibration threading requirements
- `plans/active/ARCH-IMPL-CONFORMANCE-001/implementation.md:89-101` — Phase B checklist
- `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T090000Z/phase_b5_planning.md` — This loop's planning document

### Code References
- `dbex/refinement/scaling_utils.py:35-111` — Canonical apply_sqrt_spot_scale API (owner)
- `dbex/refinement/reconstruction.py:216-221` — effective_calibration_metadata defaulting logic
- `dbex/refinement/reconstruction.py:501-509` — apply_sqrt_spot_scale call site
- `tests/architecture/test_scale_contracts.py:254-262` — RefinementConfig with calibration_metadata threading (Ralph's i=112 fix)
- `tests/architecture/test_scale_contracts.py:267-280` — build_final_bragg_from_stage_a_telemetry cold-path call

### Evidence
- `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T060000Z/pytest_phase_a2_extended_timeout.log:13-15` — Raw vs scaled output IDENTICAL (proving apply_sqrt_spot_scale saw None)
- `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T060000Z/summary.md` — Loop i=113 diagnostic summary

## ARCH Contracts (mandatory)

### ARCH-CONTRACT-002: Post-Run Scaling Pattern
- **Owner module/API**: `dbex/refinement/scaling_utils.py::apply_sqrt_spot_scale`
- **Responsibility**: Apply sqrt(spot_scale_override) to raw simulator outputs per SCALE-002
- **Consumers**: Stage A (stage_a.py:442-443), reconstruction (reconstruction.py:506), mapping (simulate_forward_once via nanobrag_bridge.py:1457)
- **Failure classification**: **Architecture conformance failure**
  - Reconstruction cold path calls apply_sqrt_spot_scale with None calibration_metadata despite test threading it to RefinementConfig
  - Either (a) config.calibration_metadata not hydrated, or (b) calibration_metadata parameter not passed through call chain
  - This violates ARCH-CONTRACT-002 requirement that all consumers receive identical calibration_metadata

### ARCH-CONTRACT-001: Stage A vs Reconstruction Scaling Alignment
- **Owner module/API**: Stage A forward path (`build_mapping_stage_a_context` → `simulate_forward_once`)
- **Responsibility**: Authoritative zero-iteration Bragg baseline for DB-AT-027/028/029
- **Consumers**: Reconstruction helpers (build_final_bragg_from_stage_a_telemetry with param_state="initial")
- **Failure classification**: **Architecture conformance failure**
  - Reconstruction cold path produces 2.83× scale mismatch vs Stage A baseline
  - Root cause: calibration_metadata threading break prevents apply_sqrt_spot_scale from executing
  - Violates parity contract (docs/spec-db-core.md:60-140 requires ≤1e-6 rel_error)

## Do Now (hard validity contract)

**This is an evidence-collection loop.** No production code changes are permitted. Only add temporary diagnostic logging to trace calibration_metadata threading.

### Step 1: Add calibration tracing to test_scale_contracts.py

File: `tests/architecture/test_scale_contracts.py`

At line 262 (after `config = RefinementConfig(...)`), add:
```python
# GALPH DIAGNOSTIC: Trace calibration threading (loop i=114)
print(f"\n[CALIBRATION TRACE] test_scale_contracts.py:262 → RefinementConfig created")
print(f"  config.calibration_metadata: {config.calibration_metadata}")
if config.calibration_metadata is not None:
    print(f"  spot_scale_override: {config.calibration_metadata.get('spot_scale_override')}")
```

At line 280 (after `bragg_reconstruction_cold = build_final_bragg_from_stage_a_telemetry(...)`), add:
```python
# GALPH DIAGNOSTIC: Confirm calibration was passed
print(f"\n[CALIBRATION TRACE] build_final_bragg_from_stage_a_telemetry returned")
print(f"  bragg_reconstruction_cold.mean(): {bragg_reconstruction_cold.mean():.6e}")
```

### Step 2: Add calibration tracing to reconstruction.py

File: `dbex/refinement/reconstruction.py`

At line 221 (after `effective_calibration_metadata = calibration_metadata or config.calibration_metadata`), add:
```python
# GALPH DIAGNOSTIC: Trace calibration defaulting (loop i=114)
print(f"\n[CALIBRATION TRACE] reconstruction.py:221 → effective_calibration_metadata resolved")
print(f"  calibration_metadata (param): {calibration_metadata}")
print(f"  config.calibration_metadata: {config.calibration_metadata}")
print(f"  effective_calibration_metadata: {effective_calibration_metadata}")
if effective_calibration_metadata is not None:
    print(f"  spot_scale_override: {effective_calibration_metadata.get('spot_scale_override')}")
```

At line 509 (after `bragg_scaled_np = apply_sqrt_spot_scale(bragg_prescaled_np, effective_calibration_metadata)`), add:
```python
# GALPH DIAGNOSTIC: Confirm apply_sqrt_spot_scale executed (loop i=114)
print(f"\n[CALIBRATION TRACE] reconstruction.py:509 → apply_sqrt_spot_scale returned")
print(f"  bragg_prescaled_np.mean(): {bragg_prescaled_np.mean():.6e}")
print(f"  bragg_scaled_np.mean(): {bragg_scaled_np.mean():.6e}")
ratio = bragg_scaled_np.mean() / bragg_prescaled_np.mean() if bragg_prescaled_np.mean() != 0 else float('inf')
print(f"  ratio (scaled/prescaled): {ratio:.6f}")
```

### Step 3: Add calibration tracing to scaling_utils.py

File: `dbex/refinement/scaling_utils.py`

At line 88 (after `# Extract spot_scale_override, defaulting to None`), add:
```python
# GALPH DIAGNOSTIC: Trace apply_sqrt_spot_scale inputs (loop i=114)
print(f"\n[CALIBRATION TRACE] scaling_utils.py:88 → apply_sqrt_spot_scale entry")
print(f"  calibration_metadata: {calibration_metadata}")
if calibration_metadata is not None:
    print(f"  spot_scale_override: {calibration_metadata.get('spot_scale_override')}")
```

At line 111 (after `return bragg * sqrt_spot_scale`), replace with:
```python
# GALPH DIAGNOSTIC: Trace scaling execution (loop i=114)
print(f"\n[CALIBRATION TRACE] scaling_utils.py:111 → applying sqrt_spot_scale={sqrt_spot_scale:.6e}")
print(f"  bragg.mean() BEFORE: {bragg.mean():.6e}")
result = bragg * sqrt_spot_scale
print(f"  bragg.mean() AFTER: {result.mean():.6e}")
return result
```

### Step 4: Run diagnostic test

```bash
cd /home/ollie/Documents/diffbragg_example
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
pytest -vv tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale_cold_path \
  > plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T090000Z/pytest_phase_b5_trace.log 2>&1
```

### Step 5: Analyze trace log and write decision doc

Review `pytest_phase_b5_trace.log` and identify which hop shows None:

Create `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T090000Z/phase_b5_decision.md` with:
- Section 1: Trace Evidence — Paste relevant log excerpts showing calibration values at each hop
- Section 2: Root Cause — State which scenario (A/B/C from phase_b5_planning.md) matches the evidence
- Section 3: Fix Path — Exact code change needed (config constructor fix, parameter threading fix, or test fix)
- Section 4: Next Action — Either "implement fix in Phase B.6" OR "escalate to supervisor if unexpected scenario"

### Step 6: Regression check (warm-cache test)

After analysis, run warm-cache test to confirm it still PASSES:

```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
pytest -vv tests/architecture/test_scale_contracts.py::test_stage_a_vs_reconstruction_scale \
  > plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T090000Z/pytest_warm_cache_regression.log 2>&1
```

Expected: PASS (warm-cache path uses stage_a_ctx.bragg_zero_iter, skips reconstruction cold path entirely).

## Forbidden This Loop

- NO production code changes (Stage A, reconstruction, scaling_utils, config factories)
- NO test logic changes beyond adding print statements
- NO new tests or test refactoring
- NO changes to dbex/refinement/config.py (defer to Phase B.6 if Scenario A confirmed)

## How-To Map

### Environment Setup
```bash
export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
cd /home/ollie/Documents/diffbragg_example
```

### Execution Sequence
1. Add diagnostic logging (Steps 1-3)
2. Run cold-path test with full output capture (Step 4)
3. Analyze trace log, identify None hop (Step 5)
4. Write phase_b5_decision.md with root cause determination
5. Run warm-cache regression (Step 6)
6. Commit diagnostic artifacts only (NOT the logging changes)

### Artifact Destinations
- `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T090000Z/pytest_phase_b5_trace.log`
- `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T090000Z/pytest_warm_cache_regression.log`
- `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T090000Z/phase_b5_decision.md`
- `plans/active/ARCH-IMPL-CONFORMANCE-001/reports/2026-01-14T090000Z/summary.md` (this loop's summary)

## Pitfalls To Avoid

1. **No premature fixes**: This is evidence-only. Do not fix config/test/reconstruction until decision doc confirms root cause.
2. **Preserve logging format**: Use `[CALIBRATION TRACE]` prefix for all diagnostic output so grep works.
3. **Check ALL hops**: Trace must show test → config → reconstruction → scaling_utils. Missing any hop = incomplete diagnosis.
4. **Regression hygiene**: Warm-cache test must still PASS. If it fails, logging broke something; remove logging and retry.
5. **Commit discipline**: Do NOT commit the logging changes. Only commit artifacts (*.log, *.md).
6. **Decision quality**: phase_b5_decision.md MUST state exact file:line fix path, not just "threading is broken."

## If Blocked

If trace logs show unexpected scenario (e.g., calibration_metadata present at ALL hops but apply_sqrt_spot_scale still returns identity):
1. Write phase_b5_decision.md documenting the unexpected state
2. Mark ARCH-IMPL-CONFORMANCE-001 Phase B.5 as blocked
3. Escalate to Galph with artifact pointers and hypothesis for why threading appears correct but scaling fails
4. Do NOT attempt speculative fixes without supervisor approval
