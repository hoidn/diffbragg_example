# HKL Coverage Analysis — DIAG-NANOBRAGG-OVERSAMPLE-001 Phase F

## Overview

Detector size: small

Device: cpu

## HKL Grid Metadata

- h_range: 49
- k_range: 57
- l_range: 63
- has_halo: False

## Stage A Warm-Cache Results

- Total queries: 9,437,184
- In-bounds: 0 (0.00%)
- Out-of-bounds: 9,437,184
- Observed h range: [28.0, 47.0]
- Observed k range: [28.0, 51.0]
- Observed l range: [37.0, 59.0]

## simulate_forward_once Results

- Total queries: 9,437,184
- In-bounds: 0 (0.00%)
- Out-of-bounds: 9,437,184
- Observed h range: [28.0, 47.0]
- Observed k range: [28.0, 51.0]
- Observed l range: [37.0, 59.0]

## Interpretation

**Both paths miss the HKL grid** — suggests upstream structure-factor grid issue.
Recommend opening ARCH-SIM-HKL-BOUNDS-001 to realign HKL sources.

