
import pickle
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple

import numpy as np
from simtbx.diffBragg import utils
from dials.array_family import flex
from dxtbx.model import ExperimentList


def _coerce_panel_array(
    panel_payload,
    expected_panel_shape: Sequence[int],
    panel_index: int,
    source_path: Path
) -> np.ndarray:
    """
    Convert a single panel payload (numpy array, flex array, list) into a numpy array
    with the expected (slow, fast) shape.
    """
    slow, fast = expected_panel_shape
    # Convert flex arrays or numpy-like payloads into numpy arrays
    if hasattr(panel_payload, "as_numpy_array"):
        arr = panel_payload.as_numpy_array()
    else:
        arr = np.asarray(panel_payload)

    arr = np.asarray(arr, dtype=np.float32)

    if arr.shape == (slow, fast):
        return arr

    if arr.ndim == 1 and arr.size == slow * fast:
        return arr.reshape((slow, fast))

    raise ValueError(
        f"Sigma map panel {panel_index} from '{source_path}' has shape {arr.shape}, "
        f"expected {(slow, fast)} per spec-db-core.md:32-40."
    )


def load_sigma_readout_map(path: str, expected_shape: Sequence[int]) -> np.ndarray:
    """
    Load a calibrated sigma_readout tensor from disk.

    Supports:
        - .npy files containing a [panel, slow, fast] stack
        - .npz archives with an array stored under 'sigma' or a single unnamed array
        - Pickled tuples/lists of per-panel arrays (numpy or flex) aligned to detector panels

    Args:
        path: Filesystem path to the sigma map asset.
        expected_shape: Shape tuple matching DataLoad.data (panel, slow, fast).

    Returns:
        np.ndarray float32 tensor shaped like expected_shape with strictly positive values.
    """
    expected_shape = tuple(int(dim) for dim in expected_shape)
    if len(expected_shape) != 3:
        raise ValueError(
            f"Expected sigma map shape (panels, slow, fast), got {expected_shape}."
        )

    n_panels, slow, fast = expected_shape
    asset_path = Path(path)
    if not asset_path.exists():
        raise FileNotFoundError(f"Sigma map file not found: {asset_path}")

    suffix = asset_path.suffix.lower()
    sigma_array: np.ndarray

    if suffix in {".npy"}:
        sigma_array = np.load(asset_path)
    elif suffix in {".npz"}:
        with np.load(asset_path) as payload:
            if "sigma" in payload.files:
                sigma_array = payload["sigma"]
            elif len(payload.files) == 1:
                sigma_array = payload[payload.files[0]]
            else:
                raise ValueError(
                    f"Sigma map .npz archive '{asset_path}' contains multiple datasets "
                    "but none named 'sigma'. Provide a single array or name the dataset 'sigma'."
                )
    else:
        # Assume pickled tuple/list of per-panel arrays
        with open(asset_path, "rb") as fh:
            payload = pickle.load(fh)

        if not isinstance(payload, (list, tuple)):
            raise ValueError(
                f"Sigma map '{asset_path}' must be a .npy, .npz, or pickled tuple/list "
                "of per-panel arrays."
            )

        if len(payload) != n_panels:
            raise ValueError(
                f"Sigma map '{asset_path}' has {len(payload)} panels, "
                f"expected {n_panels} to align with detector panels."
            )

        panel_arrays = [
            _coerce_panel_array(panel_payload, (slow, fast), idx, asset_path)
            for idx, panel_payload in enumerate(payload)
        ]
        sigma_array = np.stack(panel_arrays, axis=0)

    sigma_array = np.asarray(sigma_array, dtype=np.float32)

    if sigma_array.shape != expected_shape:
        if sigma_array.ndim == 1 and sigma_array.size == n_panels * slow * fast:
            sigma_array = sigma_array.reshape(expected_shape)
        else:
            raise ValueError(
                f"Sigma map '{asset_path}' shape {sigma_array.shape} does not match "
                f"expected data shape {expected_shape}. Ensure arrays are [panel, slow, fast] "
                "per spec-db-core.md:20-34."
            )

    if not np.all(np.isfinite(sigma_array)):
        raise ValueError(
            f"Sigma map '{asset_path}' contains NaN or Inf values. "
            "Per spec-db-core.md:32-68, readout noise must be finite."
        )
    if np.any(sigma_array <= 0):
        raise ValueError(
            f"Sigma map '{asset_path}' contains non-positive values. "
            "spec-db-core.md:32-34 requires strictly positive readout noise."
        )

    return sigma_array.astype(np.float32, copy=False)


# External lookup attributes that may contain calibrated readout-noise tiles
_EXTERNAL_SIGMA_KEYS = (
    "pedestal",
    "dark",
    "sigma",
    "sigma_rdout",
    "readout",
    "noise",
)


def _load_external_lookup_sigma_map(
    imageset,
    expected_shape: Sequence[int]
) -> Tuple[Optional[np.ndarray], Optional[Dict[str, object]]]:
    """Harvest calibrated sigma tiles embedded in a DIALS imageset.

    Parameters
    ----------
    imageset: dxtbx ImageSet-like
        Experiment.imageset object exposing `.external_lookup` metadata.
    expected_shape: Sequence[int]
        Detector-aligned shape `(panel, slow, fast)` to validate metadata tiles.

    Returns
    -------
    (np.ndarray | None, dict | None)
        Float32 tensor shaped like ``expected_shape`` plus provenance metadata
        when calibrated tiles exist; otherwise ``(None, None)``.

    Notes
    -----
    spec-db-core.md:32-68 mandates that readout noise tensors be strictly
    positive, finite, and aligned to `[panel, slow, fast]`. This helper copies
    the external lookup payload into numpy arrays so the original metadata is
    never mutated.
    """
    expected = tuple(int(dim) for dim in expected_shape)
    if len(expected) != 3:
        raise ValueError(
            f"Expected sigma map shape (panels, slow, fast), got {expected}."
        )

    if imageset is None or not hasattr(imageset, "external_lookup"):
        return None, None

    lookup = imageset.external_lookup
    source_item = None
    source_key = None

    for key in _EXTERNAL_SIGMA_KEYS:
        item = getattr(lookup, key, None)
        data = getattr(item, "data", None)
        if data is None:
            continue
        n_tiles = getattr(data, "n_tiles", lambda: 0)()
        if n_tiles == 0:
            continue
        source_item = item
        source_key = key
        break

    if source_item is None:
        return None, None

    n_panels, slow, fast = expected
    image_data = source_item.data
    n_tiles = image_data.n_tiles()

    if n_tiles != n_panels:
        raise ValueError(
            f"External lookup '{source_key}' provides {n_tiles} tiles but detector "
            f"requires {n_panels} panels. Ensure metadata tiles align with the detector "
            "panel count per spec-db-core.md:20-34."
        )

    panel_arrays = []
    for panel_idx in range(n_tiles):
        tile = image_data.tile(panel_idx)
        flex_tile = tile.data()
        panel_array = np.array(
            flex_tile.as_numpy_array(), dtype=np.float32, copy=True
        )
        if panel_array.shape != (slow, fast):
            raise ValueError(
                f"External lookup '{source_key}' tile {panel_idx} has shape "
                f"{panel_array.shape}, expected {(slow, fast)} per spec-db-core.md:20-34."
            )
        if not np.all(np.isfinite(panel_array)):
            raise ValueError(
                f"External lookup '{source_key}' tile {panel_idx} contains NaN/Inf values."
            )
        if np.any(panel_array <= 0):
            raise ValueError(
                f"External lookup '{source_key}' tile {panel_idx} contains non-positive values."
            )
        panel_arrays.append(panel_array)

    sigma_map = np.stack(panel_arrays, axis=0).astype(np.float32, copy=False)
    metadata = {
        "lookup_key": source_key,
        "filename": getattr(source_item, "filename", None),
        "tile_count": n_tiles,
    }
    return sigma_map, metadata


class DataLoad:
    """
    A utility class for loading and preparing crystallographic data necessary
    for differential Bragg analysis (or similar processing).

    This class reads data from MTZ, DIALS Experiment List, and DIALS
    Reflection Table files, and performs initial data preparation, such as
    generating Bijvoet mates and extracting raw image data for a specific
    experiment.
    """

    def __init__(self, args):
        """
        Initializes the DataLoad object by parsing input files and extracting
        data for a specified experiment.

        :param args: An object or namespace containing configuration arguments.
                     Required attributes include:
                     - ``mtzFile``: Path to the MTZ file.
                     - ``mtzCol``: Column name for structure factors in the MTZ file.
                     - ``exptName``: Path to the DIALS Experiment List file.
                     - ``exptIdx``: Index of the experiment to load.
                     - ``reflName``: Path to the DIALS Reflection Table file.
        :type args: object
        """
        self.args = args

        # --- Structure Factor Data ---
        F = utils.open_mtz(args.mtzFile, args.mtzCol)
        self.F = F.generate_bijvoet_mates()
        """
        A :py:class:`cctbx.miller.array` containing the structure factor
        amplitudes ($|F|$) including generated **Bijvoet mates**.
        """

        # --- Experiment List and Reflection Table ---
        # Select the specific experiment
        self.Expt = ExperimentList.from_file(args.exptName)[args.exptIdx]
        """
        A single :py:class:`dxtbx.model.Experiment` object for the experiment
        specified by ``args.exptIdx``.
        """

        # Select reflections belonging to the specific experiment
        Refs = flex.reflection_table.from_file(args.reflName)
        self.Refs = Refs.select(Refs['id'] == args.exptIdx)
        """
        A filtered :py:class:`flex.reflection_table` containing only reflections
        associated with the current experiment ID.
        """

        # --- Pixel Data and Background Estimates ---
        # Get the raw image data from the experiment
        self.data = utils.image_data_from_expt(self.Expt)
        """
        A :py:class:`np.ndarray` array of the raw image pixel values.
        """

        # Get the pixel data and background estimates near the reflections
        self.bbox, self.pids, self.tilt_coefs, self.bg_is_good, self.background_image = \
            utils.get_roi_background_and_selection_flags(
                self.Refs, self.data, use_robust_estimation=False, shoebox_sz=12,
                reject_roi_with_hotpix=False,
                pad_for_background_estimation=3, hotpix_mask=self.data < 0, weighted_fit=False)
        self.bbox
        """
        A list/array of the **bounding boxes** (regions of interest) for each
        reflection on the detector.
        """
        self.pids
        """
        An array of **panel IDs** indicating which detector panel each reflection
        is located on.
        """
        self.tilt_coefs
        """
        The **coefficients** (e.g., from a plane fit) used for the background
        estimation model near the reflections.
        """
        self.bg_is_good
        """
        A **boolean array** flagging whether the background estimation was
        considered successful/reliable for each reflection.
        """
        self.background_image
        """
        A np.ndarray the same size of self.data of the **estimated background** pixels for the regions
        of interest and pixels set to -1 otherwise.
        """

        # --- Trusted Mask and Geometry Fixtures ---
        # Load DIALS trusted mask per spec-db-core.md:29-55 if provided
        # Expected format: tuple of flex.bool per panel (True=trusted) shaped (slow, fast)
        if hasattr(args, 'maskFile') and args.maskFile is not None:
            with open(args.maskFile, 'rb') as f:
                mask_raw = pickle.load(f)

            # Convert DIALS mask tuple to numpy array [panel, slow, fast]
            # flex.bool has .all() method returning (slow, fast) dimensions
            if isinstance(mask_raw, tuple):
                mask_list = []
                for panel_mask in mask_raw:
                    slow, fast = panel_mask.all()
                    arr = np.asarray(panel_mask, dtype=bool).reshape((slow, fast))
                    mask_list.append(arr)
                trusted_mask_array = np.array(mask_list)
            else:
                # If already array-like, ensure correct dtype/shape
                trusted_mask_array = np.asarray(mask_raw, dtype=bool)

            # Guard: validate mask polarity (True should be majority for include semantics)
            # Per spec-db-core.md:29, DIALS trusted mask uses True=trusted polarity
            true_fraction = np.mean(trusted_mask_array)
            if true_fraction < 0.5:
                raise ValueError(
                    f"Trusted mask appears inverted: only {true_fraction*100:.1f}% True pixels. "
                    f"Expected True=include polarity per spec-db-core.md:29. "
                    f"Mask shape: {trusted_mask_array.shape}, file: {args.maskFile}"
                )

            self.trusted_mask = trusted_mask_array
            """
            A boolean :py:class:`np.ndarray` with shape ``[panel, slow, fast]`` where
            ``True`` indicates a trusted/good pixel (include in analysis).
            Polarity follows DIALS convention (True=trusted) per spec-db-core.md:29.
            """
        else:
            # No mask file provided - create a fully-trusted mask matching data shape
            self.trusted_mask = np.ones_like(self.data, dtype=bool)
            """
            A boolean :py:class:`np.ndarray` with shape ``[panel, slow, fast]`` where
            ``True`` indicates a trusted/good pixel (include in analysis).
            When no maskFile is provided, all pixels are trusted by default.
            """

        self.sigma_readout_map = None
        self.sigma_readout_map_source = None
        self.sigma_readout_map_metadata = None
        self._initialize_sigma_readout_map()
        """
        Optional calibrated sigma_readout tensor (`np.ndarray`) matching `self.data`.
        Loaded from CLI --sigma-map when provided or dxtbx external_lookup metadata
        when available. `sigma_readout_map_source` records the provenance
        ("cli_map" vs "external_lookup") and `sigma_readout_map_metadata`
        captures helper-level provenance (lookup key, filenames, etc.).
        """

        # Expose detector/beam/crystal fixtures for bridge compatibility
        self.detector = self.Expt.detector
        """
        The :py:class:`dxtbx.model.Detector` object from the experiment.
        Required by prepare_refinement_inputs for pixel pitch validation.
        """

        self.beam = self.Expt.beam
        """
        The :py:class:`dxtbx.model.Beam` object from the experiment.
        Provides wavelength, polarization, and beam direction metadata.
        """

        self.crystal = self.Expt.crystal
        """
        The :py:class:`dxtbx.model.Crystal` object from the experiment.
        Provides unit cell, space group, and orientation matrix.
        """

    # ------------------------------------------------------------------
    # Sigma map initialization helpers
    # ------------------------------------------------------------------
    def _initialize_sigma_readout_map(self) -> None:
        """Populate `sigma_readout_map` from CLI assets or metadata."""
        sigma_map_path = getattr(self.args, "sigma_map", None)
        if sigma_map_path:
            self.sigma_readout_map = load_sigma_readout_map(
                sigma_map_path,
                self.data.shape
            )
            self.sigma_readout_map_source = "cli_map"
            self.sigma_readout_map_metadata = {"path": str(sigma_map_path)}
            return

        imageset = getattr(self.Expt, "imageset", None)
        metadata_map, metadata = _load_external_lookup_sigma_map(
            imageset,
            self.data.shape
        )
        if metadata_map is not None:
            self.sigma_readout_map = metadata_map
            self.sigma_readout_map_source = "external_lookup"
            self.sigma_readout_map_metadata = metadata
