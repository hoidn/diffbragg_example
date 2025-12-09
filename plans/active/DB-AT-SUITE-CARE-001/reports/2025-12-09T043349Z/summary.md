### Turn Summary

Filed sincg aggregation investigation request to nanoBragg maintainers per ARCH-SIM-CONSTRUCTION-001 lifecycle_decision.md Option A.
Bug is NOT in sincg kernel (verified <1e-4% vs reference) — it's in subpixel aggregation when oversample>1 (F_latt 11% of expected, intensity 9.4%).
Next: Await upstream response to `~/Documents/nanoBragg/inbox/sincg_aggregation_bug_investigation_2025_12_09.md`.

Artifacts: plans/active/DB-AT-SUITE-CARE-001/reports/2025-12-09T043349Z/ (summary.md)

---

## Loop i=247 (Ralph) — Maintainer Request Filed

**Mode:** Active (ARCH-SIM-CONSTRUCTION-001 Option A execution)

**Action Taken:**
1. Investigated sincg bug evidence from 39 diagnostic loops (C.1-C.39)
2. Confirmed sincg kernel is CORRECT:
   - Per-axis sincg matches NumPy float64 reference to < 1e-4% median relative error
   - oversample=1 achieves 0.0005% error (virtually perfect parity)
3. Identified bug location: **subpixel AGGREGATION** when oversample > 1
   - F_latt amplitude: 11% of expected (4206.5 vs 38,048)
   - Intensity: 9.4% of expected (deficit in raw subpixel sum BEFORE omega)
4. Filed maintainer request: `~/Documents/nanoBragg/inbox/sincg_aggregation_bug_investigation_2025_12_09.md`

**Request Contents:**
- Executive summary with proof sincg kernel is NOT the bug
- Bug location hypothesis (3 candidate code paths)
- Minimal Python reproducer
- Key diagnostic evidence from probes
- Impact assessment (blocks DB-AT-028, DB-AT-029, Tier 0 initiatives)

**Portfolio Status:** ARCH-SIM-CONSTRUCTION-001 remains `blocked_pending_environment`, now with active maintainer request.

**Next:** Await upstream response to sincg aggregation investigation.
