### Turn Summary
Opened TORCH-GEOMETRY-PARITY-003 to investigate why det(U₀)=1.000557 and design hybrid parameterization after quaternion U-matrix catastrophically failed (chi² +125687%, CC→-0.045).
Pure SO(3) approaches are ruled out; the 0.06% volume scaling in mapping A* must be preserved via isotropic scale factor s or the gradient flow collapses despite perfect zero-point parity.
Next: Phase A dxtbx audit (crystal.get_A() vs get_unit_cell(), compute det(A*), det(B_ideal), det(U)), metadata review, numerical precision validation, then hypothesis decision before Phase B parameterization design.
Artifacts: plans/active/TORCH-GEOMETRY-PARITY-003/reports/2025-11-22T121500Z/ (implementation.md)
