### Turn Summary (Ralph Loop 2026-01-08T010000Z)

Validated and documented the SQUARE lattice normalization fix (commit ac4ddea0) which drops the oversample² factor for integral semantics. Architecture test confirms steps_scalar=1 ✓, and parity improved from 0.0058% to 41.5%, but 58.5% error remains (observed 601M vs expected 1.45B). Single-pixel probe shows 0/169 subpixels hit the sincg central lobe despite the normalization fix. Remaining error documented as "beyond normalization scope" and requires further investigation of oversample grid sampling or sincg peak capture strategy.

Artifacts: Patch file (`patches/square_lattice_steps_fix.patch`), environment tag (`patches/environment_tag.md`), rebuild log (`pip_rebuild.log`), probe results (`square_lattice_probe.log`, `square_lattice_scaling.{json,md}`), architecture test (`pytest_partiality.log`), updated `docs/findings.md::SIM-CONSTR-PARTIALITY-001`, and `docs/fix_plan.md` status entry.
