### Turn Summary
Implemented mask coverage diagnostics (≥50% threshold guard) in reconstruction cold path with per-panel coverage stats, JSON artifact emission, and probe script enhancements for --use-reconstruction-helper mode.
Tests DB-AT-028/029 still fail with chi²=2.098e+05, but mask_coverage.json confirms 90.4% coverage (above threshold), mask injected, DEBUG block logged all telemetry.
Next: Supervisor should analyze why reconstruction outputs remain discrepant despite mask parity; chi² 2× worse than Phase C.5 suggests another issue beyond trusted-mask threading.
Artifacts: plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2025-12-10T090000Z/ (mask_coverage.json, pytest_db_at_028_029.log, probe script with new flags)

---

# ARCH-SIM-CONSTRUCTION-001 Intensity + Calibration Metrics Summary

## Reconstruction Helper Mode

**CLI Arguments:**
- `--use-reconstruction-helper`: False
- `--disable-trusted-mask`: False

Note: This probe was attempted but hit implementation issues. The actual validation occurred via DB-AT-028/029 tests which successfully exercised the reconstruction helper's mask coverage guard.
