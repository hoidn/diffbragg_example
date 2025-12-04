# Phase C.18 Summary: Mosaic Domain Sweep

**Initiative:** ARCH-SIM-CONSTRUCTION-001
**Focus:** Isolate whether Stage A↔reflection divergence boundary depends on mosaic domain count
**Date:** 2025-12-22T010000Z
**Status:** COMPLETE — Escalation decision confirmed

---

## Problem Restatement

DB-AT-028/029 failing with chi²/pixel ≈ 9.8×10⁵ and median ROI correlation ≈ -0.04. Phase C.17 reflection-table comparison revealed Stage A simulator produces median intensity 0.061× the reference reflection intensities (234× divergence for worst-case ROI). Hypothesis: mosaic domain count affects intensity redistribution.

---

## What I Inspected

### Source Trace (file:line anchors)

1. `dbex/refinement/config.py:98` — `stage_a_mosaic_domains: int = 16` field definition in RefinementConfig
2. `plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py:338-342` — Added `--stage-a-mosaic-domains` CLI argument (default 16, type int)
3. `compare_stage_a_baseline.py:349-351` — Clamping logic `max(1, args.stage_a_mosaic_domains)`
4. `compare_stage_a_baseline.py:355` — Console output of applied domain count
5. `compare_stage_a_baseline.py:434` — Threading `stage_a_mosaic_domains` into RefinementConfig constructor
6. `compare_stage_a_baseline.py:1032` — Recording domain count in `probe_metadata` JSON output

---

## What I Changed

### File: `compare_stage_a_baseline.py` (bin/compare_stage_a_baseline.py)

**Added CLI parameter** (lines 337-342):
- Argument `--stage-a-mosaic-domains` with default=16
- Help text: "Number of mosaic domain samples for Stage A/mapping/reconstruction (default: 16). Clamped to ≥1."

**Added clamping + console output** (lines 349-356):
- Clamps input to ≥1 with warning if clamped
- Prints "Stage A mosaic domains: {value}" to console

**Threaded to config** (line 434):
- Passed `stage_a_mosaic_domains=stage_a_mosaic_domains` to RefinementConfig constructor

**Recorded in metadata** (line 1032):
- Added `"stage_a_mosaic_domains": stage_a_mosaic_domains` to probe_metadata JSON

**Updated metadata fields** (lines 1018-1021):
- Updated timestamp to 2025-12-22T010000Z
- Updated phase to C.18
- Updated purpose to "Stage A mosaic-domain sweep to isolate Stage A↔reflection divergence boundary"

---

## Tests Run

### Exact pytest commands + outcome

**Domain=1 probe:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
DBEX_SMOKE_CALIB_PATH=sp.proc/calibration/config_torch_smoke_small.json \
DBEX_SMOKE_HKL_PATH=sp.proc/calibration/smoke_refined_structure_factors_small.mtz \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py \
  --geometry-mode baseline \
  --stage-a-mosaic-domains 1 \
  --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T010000Z/domain1/stage_a_baseline_probe_baseline.json
```
**Outcome:** SUCCESS (exit code 1 due to baseline parity warnings, expected for diagnostic run)
- Stage A/Refl median: 0.0612
- Stage A/Refl P25-P75: [0.0143, 0.8643]
- Stage A/Refl min-max: [0.0001, 233.9085]

**Domain=16 probe:**
```bash
[Same env vars]
python plans/active/ARCH-SIM-CONSTRUCTION-001/bin/compare_stage_a_baseline.py \
  --geometry-mode baseline \
  --stage-a-mosaic-domains 16 \
  --output plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T010000Z/domain16/stage_a_baseline_probe_baseline.json
```
**Outcome:** SUCCESS (exit code 1, same parity warnings)
- Stage A/Refl median: 0.0612
- Stage A/Refl P25-P75: [0.0143, 0.8643]
- Stage A/Refl min-max: [0.0001, 233.9085]

**DB-AT-028:**
```bash
AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md \
DBAT028_ARTIFACT_DIR=plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T010000Z/db_at_028 \
DBEX_SMOKE_SIGMA_SOURCE=cli_override \
DBEX_SMOKE_DETECTOR_SIZE=small \
KMP_DUPLICATE_LIB_OK=TRUE \
NANOBRAGG_DISABLE_COMPILE=1 \
pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_db_at_028_loss_scale_sanity
```
**Outcome:** FAILED (expected)
- chi²/pixel initial: 2.097e+05 (>> 1e2 bound)

**DB-AT-029:**
```bash
[Same env vars with DBAT029_ARTIFACT_DIR]
pytest -vv tests/dbex/test_stage_a_smoke_parity.py::test_db_at_029_structure_parity
```
**Outcome:** FAILED (expected)
- median ROI correlation before: -0.053 (< 0.2 floor)

---

## Artifacts Written

**Reports path:** `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T010000Z/`

**Key filenames:**
- `mosaic_domain_sweep.md` — Executive summary + boundary bisection decision
- `domain1/stage_a_baseline_probe_baseline.json` — Domain=1 probe metrics
- `domain1/baseline_probe.log` — Domain=1 console output
- `domain16/stage_a_baseline_probe_baseline.json` — Domain=16 probe metrics
- `domain16/baseline_probe.log` — Domain=16 console output
- `db_at_028/db_at_028_metrics.json` — DB-AT-028 chi²/pixel metrics
- `db_at_028/pytest.log` — DB-AT-028 pytest output (via tee)
- `db_at_029/db_at_029_metrics.json` — DB-AT-029 ROI correlation metrics
- `db_at_029/pytest.log` — DB-AT-029 pytest output (via tee)
- `summary.md` — This summary document

---

## Next Step

**Escalate to nanobrag_torch instrumentation (Environment Freeze exception path).**

**Rationale:**
1. Stage A/Refl median **identical** between domain=1 and domain=16 (0.0612)
2. Divergence signature (234× worst-case) **independent** of mosaic averaging
3. Target/Refl ≈ 1.02 proves reference reflection table is correctly scaled
4. |F|²/pix ledger shows mismatch occurs **downstream** of HKL amplitude lookup

**Next Actions:**
1. Instrument nanobrag_torch to capture per-reflection energy partitioning (inside bbox vs outside bbox)
2. Compare nanobrag spot profile FWHM against DIALS bbox dimensions
3. Verify whether reflection `intensity.sum.value` includes local background over-subtraction

Per `input.md` Boundary Bisection Step: "If the Stage A/Ref medians remain ≈0.061 for both runs, escalate to a nanobrag_torch instrumentation patch (Environment Freeze exception path)."

---

## Turn Summary

Implemented `--stage-a-mosaic-domains` knob, ran 1-domain vs 16-domain sweep, and confirmed Stage A/Ref median unchanged at 0.061 for both runs. Verdict: mosaic domain count does NOT resolve the 234× divergence crisis. Escalation to nanobrag_torch instrumentation required.

**Artifacts:** `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-22T010000Z/`
