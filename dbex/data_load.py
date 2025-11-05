
import pickle
import numpy as np
from simtbx.diffBragg import utils
from dials.array_family import flex
from dxtbx.model import ExperimentList


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
