Summary: Instrument Stage A warm-sim path with perf counters and surface them via telemetry for `/torch_diagnostics`.
Mode: Perf
Focus: PERF-WARM-SIM-001 — Warm Simulator; Eliminate Per-Iteration Re-Instantiation
Branch: integration
Mapped tests: tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion, tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers
Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-06T081209Z/

Do Now:
- PERF-WARM-SIM-001 — Warm Simulator; Eliminate Per-Iteration Re-Instantiation
  - Implement: dbex/nanobrag_refinement.py::run_nanobrag_refinement — extend `RefinementTelemetry` with an optional `perf_counters` payload and instrument Stage A to populate closure evaluations, `forward_time_ms`, and validation counters while keeping Stage B/C emitting at least empty dictionaries so `/torch_diagnostics` remains schema-compatible.
  - Implement: tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion — assert Stage A telemetry exposes the new perf counters and that values are non-negative/integers as expected.
  - Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion | tee $ARTIFACTS/collect_stage_a.log && KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1 --capture=tee-sys | tee $ARTIFACTS/pytest_stage_a.log
  - Validate: AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers | tee $ARTIFACTS/collect_stage_b.log && KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --maxfail=1 --capture=tee-sys | tee $ARTIFACTS/pytest_stage_b.log
  - Artifacts: plans/active/PERF-WARM-SIM-001/reports/2025-11-06T081209Z/

How-To Map:
- export AUTHORITATIVE_CMDS_DOC=./docs/TESTING_GUIDE.md
- export ARTIFACTS=plans/active/PERF-WARM-SIM-001/reports/2025-11-06T081209Z
- mkdir -p "$ARTIFACTS"
- AUTHORITATIVE_CMDS_DOC=$AUTHORITATIVE_CMDS_DOC pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion | tee "$ARTIFACTS/collect_stage_a.log"
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=$AUTHORITATIVE_CMDS_DOC pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_a_expansion --maxfail=1 --capture=tee-sys | tee "$ARTIFACTS/pytest_stage_a.log"
- AUTHORITATIVE_CMDS_DOC=$AUTHORITATIVE_CMDS_DOC pytest --collect-only tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers | tee "$ARTIFACTS/collect_stage_b.log"
- KMP_DUPLICATE_LIB_OK=TRUE NANOBRAGG_DISABLE_COMPILE=1 AUTHORITATIVE_CMDS_DOC=$AUTHORITATIVE_CMDS_DOC pytest -vv tests/dbex/test_torch_refine_smoke.py::test_stage_b_shell_modifiers --maxfail=1 --capture=tee-sys | tee "$ARTIFACTS/pytest_stage_b.log"
- NANOBRAGG_DISABLE_COMPILE=1 python - <<'PY' | tee "$ARTIFACTS/stage_a_perf_counters.json"
import json, pathlib
from argparse import Namespace
import numpy as np

from dbex.data_load import DataLoad
from dbex.nanobrag_bridge import prepare_refinement_inputs
from dbex.nanobrag_refinement import run_nanobrag_refinement, RefinementConfig

repo = pathlib.Path(__file__).resolve().parents[2]
args = Namespace(
    exptName=str(repo / "refGeom.expt"),
    reflName=str(repo / "refGeom.refl"),
    exptIdx=0,
    maskFile=str(repo / "747_mask.pkl"),
    mtzFile=str(repo / "scaled.mtz"),
    mtzCol="F,SIGF"
)
data = DataLoad(args)
detector = data.Expt.detector
trusted_masks = [np.ones(panel.get_image_size()[::-1], dtype=bool) for panel in detector]

inputs = prepare_refinement_inputs(
    data=data.data,
    background_image=data.background_image,
    trusted_mask=trusted_masks,
    bbox=data.bbox,
    beam=data.Expt.beam,
    detector=detector,
    crystal=data.Expt.crystal,
    hkl_grid=data.structure_factors.hkl_grid,
    hkl_metadata=data.structure_factors.hkl_metadata,
)

config = RefinementConfig(
    enable_hkl_interpolation=True,
    roi_sample_fraction=0.15,
    max_iter=30,
)

_, telemetry = run_nanobrag_refinement(
    inputs=inputs,
    detector=detector,
    beam=data.Expt.beam,
    crystal=data.Expt.crystal,
    hkl_grid=data.structure_factors.hkl_grid,
    hkl_metadata=data.structure_factors.hkl_metadata,
    config=config,
    baseline_crystal=data.Expt.crystal,
)

telemetry_a = telemetry["A"]
payload = telemetry_a.perf_counters or {}
payload.setdefault("roi_count_sampled", telemetry_a.roi_count_sampled)
print(json.dumps(payload, indent=2))
PY

Pitfalls To Avoid:
- Keep Environment Freeze intact; no package installs or new dependencies.
- Perf counters must not mutate Stage A sampling order or change loss traces (REFINE-002 guard).
- Use `time.perf_counter()` around CPU work only; do not pull in async torch timers.
- Preserve existing telemetry keys and types; append perf counters without renaming current fields (DIAGNOSTICS-001).
- Ensure Stage B/C pathways still instantiate telemetry even if perf counters are currently empty.
- Avoid writing large intermediate blobs to repo root—keep artifacts under `$ARTIFACTS`.
- If Stage A perf counters require new imports, restrict them to stdlib and keep top-level import ordering stable.
- Do not drop the Stage A warm cache helper; instrumentation must wrap it without reintroducing rebuilds.
- Maintain Stage A improvement gate (≥0.1%) and check messages for early_stop semantics.
- Keep collect-only logs before pytest invocations to satisfy TESTING-003.

If Blocked:
- Tee failing command output to "$ARTIFACTS/blocker.log", note exception plus relevant counters, set docs/fix_plan.md status to `blocked` with the failure signature, and capture the retry condition in galph_memory.md before stopping.

Findings Applied (Mandatory):
- PERF-WARM-001 — Stage A warm cache already hoists detector construction; perf counters must observe this path without reintroducing rebuilds.
- DIAGNOSTICS-001 — Extend `/torch_diagnostics` metrics while preserving existing schema and downstream readers.
- REFINE-001 — Keep scale warm-start/clamp semantics intact while instrumenting the closure.
- REFINE-002 — Maintain ≥0.1% Stage A improvement gate when emitting telemetry.
- CONFIG-001 — Trusted mask polarity/dtype must remain float32 {0,1} when reused inside perf counters.
- RUNTIME-001 — Run smokes with `NANOBRAGG_DISABLE_COMPILE=1` for determinism.
- TESTING-003 — Collect-only logs precede targeted pytest runs and live in the artifacts directory.

Pointers:
- dbex/nanobrag_refinement.py:589 — Stage A closure currently records loss traces; wrap timers and counters here.
- dbex/nanobrag_refinement.py:308 — `RefinementTelemetry` dataclass to extend with optional perf counters.
- dbex/nanobrag_refinement.py:1329 — Stage B telemetry assembly; ensure new field defaults don't break this path.
- tests/dbex/test_torch_refine_smoke.py:291 — Stage A telemetry assertions to expand for perf counters.
- docs/development/testing_strategy.md:169 — Selector/collect-only cadence guardrails.
- docs/pytorch_runtime_checklist.md:26 — Required runtime flags for deterministic CPU runs.

Next Up (optional):
- Capture baseline vs improved timings using the new perf counters and document the delta in docs/findings.md.
- Extend warm cache/perf counters to Stage B shell modifiers once Stage A metrics are validated.
