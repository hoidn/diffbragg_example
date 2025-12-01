"""IO utilities for DBEX torch backend outputs.

This module provides shared serialization and output writing helpers
for the nanobrag_torch backend, consolidating telemetry schema and
HDF5 emission logic that was previously embedded in CLI wrappers.

Key exports:
    write_torch_outputs: Serialize ROI-scored triptychs + /torch_diagnostics to HDF5
"""

from dbex.io.writer import write_torch_outputs

__all__ = ["write_torch_outputs"]
