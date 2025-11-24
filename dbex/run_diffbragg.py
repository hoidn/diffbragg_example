
from copy import deepcopy
import logging
import os
from pathlib import Path
from typing import Optional

import numpy as np

from dials.array_family import flex
from dxtbx.model import ExperimentList
from libtbx.phil import parse
from simtbx.command_line.hopper import phil_scope
from simtbx.diffBragg import hopper_utils, utils, hopper_io
from simtbx.modeling.forward_models import diffBragg_forward

def detector_refinement(model_df, Expt, Refs, params, scratch_dir: Optional[Path] = None):
    """
    Refine detector geometry using DiffBragg backend.

    Args:
        model_df: Model dataframe for refinement
        Expt: DIALS Experiment object
        Refs: DIALS Reflections table
        params: DiffBragg refinement parameters
        scratch_dir: Optional temporary directory for scratch files.
                     If None, uses current working directory (backward compat).

    Returns:
        Updated Experiment object with refined detector

    Notes:
        Scratch files written (when scratch_dir is provided):
        - geom_ref/_geom_ref.expt: Experiment list
        - geom_ref/_geom_ref.refl: Reflections table
        - geom_ref/_geom_ref.pkl: Model dataframe pickle
        - geom_ref/_geom_groups.txt: Panel group assignments
        - geom_out/diffBragg_detector.expt: Refined detector output
    """
    # Setup scratch directory structure
    if scratch_dir is None:
        scratch_dir = Path.cwd()  # Backward compatibility

    geom_ref_dir = scratch_dir / "geom_ref"
    geom_ref_dir.mkdir(parents=True, exist_ok=True)

    geom_out_dir = scratch_dir / "geom_out"

    # Write input files to geom_ref directory
    new_El = ExperimentList()
    new_El.append(Expt)
    new_El.as_file(str(geom_ref_dir / "_geom_ref.expt"))
    Refs.as_file(str(geom_ref_dir / "_geom_ref.refl"))
    Refs['id'] = flex.int(len(Refs), 0)
    model_df["geom_exp"] = str(geom_ref_dir / "_geom_ref.expt")
    model_df["geom_ref"] = str(geom_ref_dir / "_geom_ref.refl")
    model_df["geom_exp_idx"] = 0
    model_df.to_pickle(str(geom_ref_dir / "_geom_ref.pkl"))
    from simtbx.diffBragg.refiners import geometry
    with open(str(geom_ref_dir / "_geom_groups.txt"), "w") as o:
        for i_p in range(len(Expt.detector)):
            o.write("%d %d\n" % (i_p, i_p))

    # Configure geometry refinement with scratch directory paths
    params_geom = deepcopy(params)
    params_geom.fix.Fhkl = True
    params_geom.refiner.panel_group_file = str(geom_ref_dir / "_geom_groups.txt")
    params_geom.geometry.fix.panel_rotations = [0, 0, 0]
    params_geom.geometry.fix.panel_translations = [0, 0, 1]
    params_geom.geometry.input_pkl = str(geom_ref_dir / "_geom_ref.pkl")
    params_geom.geometry.save_state_freq = 100000
    params_geom.filter_during_refinement.enable = False
    params_geom.outdir = str(geom_out_dir)
    params_geom.max_process = 1
    params_geom.geometry.optimize = True

    # Run geometry refinement
    geometry.geom_min(params_geom)

    # Read refined detector from output directory
    new_det = ExperimentList.from_file(str(geom_out_dir / "diffBragg_detector.expt"))[0].detector
    Expt.detector = new_det
    return Expt


def run_diffbragg(data_load, devId=0, num_macro=5):
    """
    :param data_load: instance of diffbragg_example.data_load.DataLoad
    :param devId: CUDA gpu device Id
    :param num_macro: number of refinement macro cycles
    :return:
    """

    logger = logging.getLogger("diffBragg.main")
    logger.setLevel(logging.DEBUG)

    # parameters object that controls hopper refinement

    xtal_refine_phil= os.path.dirname(__file__) + "/dbconfig/xtal_refine.phil"
    fhkl_refine_phil= os.path.dirname(__file__) + "/dbconfig/fhkl_refine.phil"
    config = open(xtal_refine_phil, "r").read()
    config2 = open(fhkl_refine_phil, "r").read()
    params = phil_scope.fetch(sources=[parse(config)]).extract()
    params.fix.Ndef = False
    params_fhkl = phil_scope.fetch(sources=[parse(config2)]).extract()
    for prm in (params, params_fhkl):
        prm.simulator.structure_factors.mtz_name = data_load.args.mtzFile
        prm.simulator.structure_factors.mtz_column = data_load.args.mtzCol
        prm.roi.hotpixel_mask = data_load.args.maskFile

    Expt = deepcopy(data_load.Expt)
    Finds = data_load.F.indices()
    Famps = data_load.F.data()
    FMap = {h: amp for h, amp in zip(Finds, Famps)}
    for cycle in range(num_macro):

        # REFINEMENT OF XTAL
        ref_out = hopper_utils.refine(Expt, data_load.Refs, params, return_modeler=True, free_mem=True, gpu_device=devId)
        Expt, _, Modeler, SIM, x = ref_out
        mdl_parm = hopper_utils.get_param_from_x(x, Modeler, as_dict=True)

        for prm in [params, params_fhkl]:
            prm.init.Nabc = mdl_parm['Na'], mdl_parm['Nb'], mdl_parm['Nc']
            prm.init.Ndef = mdl_parm['Nd'], mdl_parm['Ne'], mdl_parm['Nf']
            prm.init.G = mdl_parm['scale']

        # REFINEMENT OF FHKL
        ref_out_fhkl = hopper_utils.refine(Expt, data_load.Refs, params_fhkl, return_modeler=True, free_mem=True, gpu_device=devId)
        _, _, Modeler_fhkl, SIM_fhkl, x_hkl = ref_out_fhkl
        Fidx_to_asu = {i: hkl for hkl, i in SIM_fhkl.asu_map_int.items()}
        refined = np.where(SIM_fhkl.Fhkl_scales != 1)[0]
        new_amps = {}
        for i in refined:
            asu = Fidx_to_asu[i]
            if asu in FMap:
                scale = SIM_fhkl.Fhkl_scales[i]
                new_amp = np.sqrt(scale) * FMap[asu]
                new_amps[asu] = new_amp

        for i_hkl, hkl in enumerate(Finds):
            if hkl in new_amps:
                Famps[i_hkl] = new_amps[hkl]

        Fopt = data_load.F.customized_copy(data=Famps)
        Fopt.as_mtz_dataset(column_root_label="F").mtz_object().write("_temp.mtz")
        for prm in [params, params_fhkl]:
            prm.simulator.structure_factors.mtz_name = "_temp.mtz"
            prm.simulator.structure_factors.mtz_column = "F(+),SIGF(+),F(-),SIGF(-)"
        FMap = {h: amp for h, amp in zip(Fopt.indices(), Fopt.data())}
        params.filter_during_refinement.enable = False
        params_fhkl.filter_during_refinement.enable = False

        model_df = hopper_io.save_to_pandas(x_hkl, Modeler_fhkl, SIM_fhkl, data_load.args.exptName, params_fhkl, Expt, 0,
                                            data_load.args.reflName, None, 0, write_expt=False, write_pandas=False,
                                            exp_idx=data_load.args.exptIdx)

        # REFINEMENT OF DETECTOR
        Expt = detector_refinement(model_df, Expt, data_load.Refs, params_fhkl)

    # with te optimized model from diffBragg, we can predict a model value at every pixel
    energies = [utils.ENERGY_CONV / Expt.beam.get_wavelength()]
    fluxes = [SIM_fhkl.D.flux]
    mdl_parm = hopper_utils.get_param_from_x(x_hkl, Modeler_fhkl, as_dict=True)
    Bragg = diffBragg_forward(
        Expt.crystal, Expt.detector, Expt.beam, Fopt,
        energies, fluxes,
        oversample=SIM_fhkl.D.oversample,
        Ncells_abc=(mdl_parm['Na'], mdl_parm['Nb'], mdl_parm['Nc']),
        Ncells_def=(mdl_parm['Nd'], mdl_parm['Ne'], mdl_parm['Nf']),
        beamsize_mm=SIM_fhkl.D.beamsize_mm, device_Id=devId,
        spot_scale_override=mdl_parm['scale'],
        cuda=(devId >= 0),
        num_phi_steps=SIM_fhkl.D.phisteps, delta_phi=SIM_fhkl.D.phistep_deg,
        spindle_axis=SIM_fhkl.D.spindle_axis, no_Nabc_scale=True
    )
    return Bragg

