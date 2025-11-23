### Turn Summary
Analyzed Ralph's blocker from loop i=216 and identified new root cause: warm cache simulator reuse with post-creation HKL data updates breaks gradient flow.
Device fix (parameters on CPU) was correct but insufficient—the gradient chain breaks when nanobrag_torch simulators cache HKL data internally and don't see later updates.
Next: Ralph applies one-line fix (disable warm cache for CPU fallback), runs full+small detector tests, validates cold path preserves gradients without regressing CUDA warm path.
Artifacts: plans/active/ARCH-REFINE-FLOW-001/reports/2025-11-23T104525Z/ (root_cause_hypothesis.md, input.md)
