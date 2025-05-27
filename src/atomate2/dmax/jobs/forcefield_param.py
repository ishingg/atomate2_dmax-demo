"""
Job maker for polymer forcefield parametrization via LigParGen or Foyer.
"""
from dataclasses import dataclass, field
from pathlib import Path
from jobflow import Maker, job
import os
import shutil
import importlib

from atomate2.dmax.generators.forcefield import parametrize_auto, parametrize_foyer
from atomate2.dmax.generators.polymer_structure import PSPBuilderWrapper

@dataclass
class ForceFieldMaker(Maker):
    """
    Maker to parametrize polymer structures.

    Attributes
    ----------
    amor : PSPBuilder instance
        PSPBuilder instance needed for forcefield parametrization.
    method : str
        'ligpargen' or 'foyer'.
    forcefield_name : str | None
        Name of the forcefield for foyer.
    """
    name: str = "forcefield_parametrization"
    method: str = field(default="auto")
    out_dir: str | None = None

    @job(output_schema=None)
    def make(self, amor) -> str:
        """
        Generate LAMMPS data file from PSP builder `amor` or its wrapper.
        By default uses automatic selection.
        """
        # stand-alone .pdb input: delegate to parametrize_foyer
        if isinstance(amor, str) and amor.lower().endswith('.pdb'):
            return parametrize_foyer(amor)
        # other inputs: expect builder wrapper or its serialized dict
        if not (isinstance(amor, dict) or hasattr(amor, 'get_builder')):
            raise ValueError('Support inputs: PSPBuilderWrapper (or its dict) or path to .pdb')
        # reconstruct wrapper if needed
        if isinstance(amor, dict):
            amor = PSPBuilderWrapper.from_dict(amor)
        # ensure parametrization uses the original builder output directory
        orig_dir = amor.out_dir
        amor.out_dir = orig_dir
        # run automatic parametrization where the build files live
        data_path = parametrize_auto(amor)
        # move the generated data file into the job's own working directory
        cwd = os.getcwd()
        dest = os.path.join(cwd, os.path.basename(data_path))
        shutil.move(data_path, dest)
        return dest
