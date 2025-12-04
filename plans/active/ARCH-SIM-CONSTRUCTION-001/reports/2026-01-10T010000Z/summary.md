### Turn Summary (Ralph Implementation — 2026-01-10T010000Z)

Fixed MOSFLM/DENZO auto beam-center formula ((detsize-pixel)/2); 1×1 probe now hits Bragg manifold (Δk=Δl=0, was 0.054), central lobe coverage 48% (was 0%), implied ratio 93.5% of spec; 10×10 architecture test ratio unchanged at ~41% (590M vs 601M), 59% error persists; beam geometry fix complete per Boundary Bisection criterion (Δ<1/N), remaining discrepancy escalated as normalization issue beyond beam centering scope.

Artifacts: `plans/active/ARCH-SIM-CONSTRUCTION-001/reports/2026-01-10T010000Z/` — `square_lattice_probe.log`, `square_lattice_scaling.{json,md}`, `pytest_partiality.log`.
