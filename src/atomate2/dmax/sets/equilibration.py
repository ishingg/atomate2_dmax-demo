"""
LAMMPS InputSet for polymer structure equilibration.
"""
from pymatgen.io.lammps.generators import BaseLammpsSetGenerator


class StructureEquilibrationSet(BaseLammpsSetGenerator):
    """
    InputSet generating an in.lammps for structure equilibration of a polymer.
    Uses the `in.master_structure_equilibration` template.

    Parameters
    ----------
    temperature : float
        Target temperature in K.
    pressure : float
        Target pressure in bar.
    nsteps : int
        Number of MD steps.
    timestep : float
        Time step in ps.
    """
    def __init__(
        self,
        temperature: float = 300.0,
        pressure: float = 1.0,
        nsteps: int = 100000,
        timestep: float = 1.0,
        **kwargs,
    ):
        super().__init__(**kwargs)
        # template filename (must be available in the package resources)
        self.template = "in.master_structure_equilibration"
        # default values for the template variables
        self.settings.update({
            "temperature": temperature,
            "pressure": pressure,
            "nsteps": nsteps,
            "timestep": timestep,
        })
        # LAMMPS will read this as in.lammps by default
