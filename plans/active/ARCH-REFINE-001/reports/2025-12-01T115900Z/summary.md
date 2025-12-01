### Turn Summary
Captured Phase B.1 scope by defining the RefinementContext plan entry, updating docs/fix_plan + findings, and rewriting input.md with a context-builder Do Now plus telemetry/test wiring.
Main gap is the engine still relies on ad-hoc dictionaries; I outlined the new context module, engine/stage changes, and validation strategy so Ralph can implement without ambiguity.
Next: Ralph builds dbex/refinement/context.py, retunes the Stage A/B/C wrappers + RefinementEngine to consume it, and reruns the Stage A/B/C smokes under the new artifacts path.
Artifacts: plans/active/ARCH-REFINE-001/reports/2025-12-01T115900Z/ (input.md, docs updates)
