"""
Job maker for polymer forcefield parametrization via LigParGen or Foyer.
"""
from dataclasses import dataclass, field
from pathlib import Path
from jobflow import Maker, job

from atomate2.dmax.generators.forcefield import parametrize_auto
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

    @job
    def make(self, amor) -> str:
        """
        Generate LAMMPS data file from PSP builder `amor` or its wrapper.
        By default uses automatic selection.
        """
        if self.method != "auto":
            raise NotImplementedError(
                f"Explicit method '{self.method}' not supported; only 'auto'."
            )
        # if received amor as dict (serialized wrapper), reconstruct it
        if isinstance(amor, dict):
            amor = PSPBuilderWrapper.from_dict(amor)
        # pass wrapper or builder directly to parametrization
        data_path = parametrize_auto(amor)
        return data_path
