# Input for Ralph — 2025-12-05T030000Z

## Summary
ARCH-ENGINE-ARTIFACTS-001 Phase A.3: Wire Stage C to populate bragg_full artifact so engine consumers can access final Bragg without calling reconstruction helpers.

## Mode
Parity

## InitiativeType
architecture

## Focus
ARCH-ENGINE-ARTIFACTS-001 — RefinementEngine artifact channel & final-Bragg unification

## Branch
integration

## Mapped tests
tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip

## Artifacts
plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-05T030000Z/

## Do Now

**Context:**
The artifact channel infrastructure already exists from ARCH-STAGE-CONTEXT-001 Phase B.1:
- `RefinementEngine._artifacts` dict stores per-stage artifacts
- `engine.artifacts` read-only property exposes them
- `StageCArtifacts.bragg_full` field exists but is always None

**Your task:**
Wire Stage C to populate the `bragg_full` field so the final Bragg tensor is available via `engine.artifacts["stage_c"].bragg_full` instead of requiring external reconstruction helpers.

### Implementation Steps

1. **Update `dbex/refinement/stage_c.py::StageC.run()` method:**

   a) Locate where `_run_lbfgs` returns the final `bragg_full` tensor (around line 1242):
      ```python
      bragg_full, loss_trace_sample, perf = self._run_lbfgs(...)
      ```

   b) After this line, convert the torch tensor to CPU-resident numpy array:
      ```python
      # ARCH-ENGINE-ARTIFACTS-001 Phase A.3: Convert final Bragg to numpy for artifact channel
      bragg_full_artifact = bragg_full.cpu().numpy().astype(np.float32)
      ```

   c) Find where `StageCArtifacts` is instantiated (around line 1260) and update it:
      ```python
      artifacts = StageCArtifacts(
          bragg_full=bragg_full_artifact  # Was: bragg_full=None
      )
      ```

2. **Update `dbex/refinement/artifacts.py::StageCArtifacts` docstring:**

   a) Change the text from:
      ```
      Replaces engine._stage_c_bragg_full private attribute
      ```
      To:
      ```
      Always populated by Stage C; replaces engine._stage_c_bragg_full private attribute
      ```

   b) Add a normative requirement bullet:
      ```
      - Stage C MUST populate bragg_full unconditionally (not just when terminal)
      - Cite: docs/spec-db-workflow.md §41 (stage contract + outputs)
      ```

3. **Validate the change:**

   a) Run the Stage C smoke test with small detector:
      ```bash
      AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
      KMP_DUPLICATE_LIB_OK=TRUE \
      DBEX_SMOKE_SIGMA_SOURCE=metadata \
      DBEX_SMOKE_DETECTOR_SIZE=small \
      NANOBRAGG_DISABLE_COMPILE=1 \
      pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip \
          2>&1 | tee plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-05T030000Z/pytest_stage_c_artifact.log
      ```

   b) Test should PASS with no behavioral changes (artifact is just exposing existing tensor)

   c) Optional verification (inspect in debugger or add temporary print):
      - `engine.artifacts["stage_c"].bragg_full` is not None
      - Shape matches `[n_panels, slow, fast]` for small detector: (1, 100, 100)
      - dtype is `numpy.float32`
      - Mean intensity > 0 (sanity check for non-empty)

4. **Update implementation plan:**
   - Edit `plans/active/ARCH-ENGINE-ARTIFACTS-001/implementation.md`
   - Check box `[x] A3: Update Stage C wrapper to emit {"bragg_full": np.ndarray}`

5. **Write loop summary:**
   - Create `plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-05T030000Z/summary.md`
   - Document: Phase A.3 complete, Stage C now emits bragg_full artifact, test passed, ready for Phase B (Stage B wiring)

## How-To Map

### Stage C artifact wiring
```bash
# 1. Edit stage_c.py (2 lines added: tensor conversion + artifact field population)
# Line ~1244 (after _run_lbfgs call):
bragg_full_artifact = bragg_full.cpu().numpy().astype(np.float32)

# Line ~1262 (StageCArtifacts instantiation):
artifacts = StageCArtifacts(bragg_full=bragg_full_artifact)
```

### Docstring update
```bash
# Edit artifacts.py StageCArtifacts docstring
# Add normative requirement: Stage C MUST populate bragg_full unconditionally
```

### Test validation
```bash
cd /home/ollie/Documents/diffbragg_example
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
KMP_DUPLICATE_LIB_OK=TRUE \
DBEX_SMOKE_SIGMA_SOURCE=metadata \
DBEX_SMOKE_DETECTOR_SIZE=small \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_c_detector_microslip \
    2>&1 | tee plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-05T030000Z/pytest_stage_c_artifact.log
```

## Pitfalls To Avoid

1. **Device/dtype mismatch:** Always convert to CPU numpy with `.cpu().numpy().astype(np.float32)` — HDF5 writer expects CPU floats.

2. **Shape validation:** The tensor should already have shape `[n_panels, slow, fast]` from Stage C run. Do NOT reshape.

3. **Conditional population:** Stage C should ALWAYS populate bragg_full (unlike Stage A which only populates when terminal). This is the terminal stage for detector refinement.

4. **Artifact field name:** Use `bragg_full` (not `bragg_final` or `final_bragg`) to match existing dataclass field.

5. **Telemetry vs artifacts:** Do NOT add bragg_full to telemetry dict. It belongs in artifacts only (heavy tensor vs scalar telemetry).

6. **Protected Assets:** Do NOT modify:
   - Stage C LBFGS closure logic
   - Stage C telemetry collection
   - Stage C warm cache retargeting
   - The shape/content of bragg_full tensor itself

7. **Environment:** No package installs. This is pure wiring of existing infrastructure.

## If Blocked

**Missing bragg_full variable:**
- Check line ~1242 in stage_c.py where `_run_lbfgs` returns `(bragg_full, loss_trace_sample, perf)`
- If variable name differs, use the actual name but convert the same way

**Test fails with artifact access error:**
- Verify `StageCArtifacts` was instantiated with `bragg_full=bragg_full_artifact` (not None)
- Check that Stage C returned `StageResult(telemetry=..., artifacts=artifacts)` not just a dict

**Shape/dtype mismatch:**
- Stage C tensor should already be float32 on device
- Conversion to CPU numpy should preserve shape and dtype
- Log shapes: `print(f"bragg_full shape: {bragg_full.shape}, dtype: {bragg_full.dtype}")`

**Import errors:**
- All required imports already present in stage_c.py (numpy via torch)
- StageCArtifacts already imported from artifacts module

## Findings Applied

- **ARCH-STAGE-CONTEXT-001** (artifact channel infrastructure): Reusing existing `_artifacts` dict and `StageResult` protocol
- **ARCH-ENGINE-003** (telemetry enrichment in active path): Artifact emission happens in Stage C run(), not post-hoc
- **POLICY-001** (Environment Freeze): No installs, pure wiring
- **REFINE-FLOW-001** (Stage baseline parity): Stage C artifact must match existing reconstruction helper output (will verify in Phase B)

## Pointers

- **Planning notes:** plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-05T030000Z/phase_a_planning_notes.md (full context)
- **Implementation plan:** plans/active/ARCH-ENGINE-ARTIFACTS-001/implementation.md (Phase A checklist)
- **Artifact dataclass:** dbex/refinement/artifacts.py:98-113 (StageCArtifacts definition)
- **Stage C run:** dbex/refinement/stage_c.py:913-1300 (Stage C run method, target lines ~1242, ~1262)
- **Spec:** docs/spec-db-workflow.md §41 (stage contract + outputs)
- **Baseline selector log:** plans/active/ARCH-ENGINE-ARTIFACTS-001/reports/2025-12-05T030000Z/baseline_collect_only.log (confirms test is healthy)

## Next Up

After Phase A.3 completes:
1. **Phase B.1:** Wire Stage B to populate bragg_full via `build_final_bragg_from_stage_b_telemetry` helper
2. **Phase B.2:** Implement parity harness (≤1e-6 relative MSE vs legacy reconstruction)
3. **Phase C:** Update orchestrator to read artifacts instead of calling helpers directly

**Phase A focus:** Stage C only (simpler, proof-of-concept). Stage B deferred due to CPU fallback complexity.
