# diffBragg Patch Progress (2025-10-29T063817Z)

## Status — COMPLETE ✅
- Source patches applied (`diffBraggCUDA.cu`, `diffuse_util.h`)
- `simtbx_diffBragg_ext.so` rebuilt and redeployed
- Smoke tests (CPU + GPU) pass without CUDA assertions
- Environment tagged: `simtbx-patched-diffBraggCUDA708`

## Timeline
| Time (Z) | Action |
| --- | --- |
| 00:05 | Applied guarded `cudaFree` patch (`diffBraggCUDA_cu_line708_fix.patch`) |
| 00:12 | Added `<cassert>` include to `diffuse_util.h` to unblock NVCC (`diffuse_util_assert_include.patch`) |
| 00:15 | `cmake --build … --target simtbx_diffBragg_ext --clean-first` succeeded |
| 00:21 | Deployed rebuilt `.so` to `ext/` and site-packages (`cp …`) |
| 00:23 | Captured CPU/GPU smoke test log (`logs/diffBragg_forward_smoke.log`) |
| 00:25 | Tagged environment (`environment_tag.txt`) & updated findings |

## Command Log
```bash
cmake -S /home/ollie/Documents/easyBragg -B /home/ollie/Documents/easyBragg/build_ext -DCMAKE_BUILD_TYPE=Release
cmake --build /home/ollie/Documents/easyBragg/build_ext --target simtbx_diffBragg_ext --clean-first -- -j$(nproc)
cp /home/ollie/Documents/easyBragg/build_ext/simtbx_diffBragg_ext.so /home/ollie/Documents/easyBragg/ext/simtbx_diffBragg_ext.so
cp /home/ollie/Documents/easyBragg/build_ext/simtbx_diffBragg_ext.so /home/ollie/miniconda3/envs/simtbx/lib/python3.9/site-packages/simtbx_diffBragg_ext.so
python plans/.../logs/diffBragg_forward_smoke.log  # CPU & GPU smoke test
```

## Verification Checklist
- [x] Patch files saved to reports directory
- [x] Source tree reflects patches (guard + `<cassert>`)
- [x] Shared library hash `1506a48bee414ffcec041083b1496a44`
- [x] Smoke test log archived
- [x] `docs/findings.md` updated (DIFFBRAGG-001 → Resolved)
- [x] Environment tag recorded

## Next Steps
Continue NANOBRAG-GOLDEN-001 canonical capture now that `diffBragg_forward` runs cleanly on both CPU and GPU.
