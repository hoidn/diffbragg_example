### Turn Summary
Analyzed Phase C1 parity failure showing raw U-matrix achieves perfect parity (3.5e-18) but det(U₀)=1.000557 (not in SO(3)); quaternion projection loses 0.06% volume scaling, degrading parity to ~4e-05.
Chose Alternative Path 3 (accept parity gap, test convergence) as pragmatic sensitivity probe before deeper dxtbx audit—quaternion may still improve convergence by eliminating the symmetric strain gradient artifact that blocked TORCH-REFINE-002E.
Next: Ralph runs Phase C2/C3 with quaternion U-matrix mode (Phase 5 A_scale_only/D_full variants); if A_scale_only maintains CC ≥ 0.99 + stable χ², accept quaternion and document GEOMETRY-004; otherwise escalate to GEOMETRY-PARITY-003.
Artifacts: plans/active/TORCH-GEOMETRY-PARITY-002/reports/2025-11-22T114945Z/ (input.md, summary.md)
