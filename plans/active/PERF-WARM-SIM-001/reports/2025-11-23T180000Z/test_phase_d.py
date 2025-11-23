#!/usr/bin/env python
"""Minimal test to validate Phase D Stage C retargeting without engine delegation."""

import torch
import pytest

# Import test fixtures
from tests.dbex.test_torch_refine_smoke import (
    test_stage_c_detector_microslip,
    refgeom_dataload,
    refinement_inputs,
    hkl_data,
    smoke_detector_size,
    smoke_sigma_source
)

if __name__ == "__main__":
    # Run the test using pytest's fixture system
    pytest.main([__file__, "-v", "-s"])
