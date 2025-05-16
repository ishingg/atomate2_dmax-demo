"""
Job maker for polymer structure generation using PSP AmorphousBuilder.
"""
from dataclasses import dataclass, field
from pathlib import Path
from jobflow import Maker, job
import os

from atomate2.dmax.generators.polymer_structure import build_amorphous_structure

@dataclass
class PSPStructureMaker(Maker):
    """
    Maker to generate amorphous polymer structures from SMILES via PSP.

    Attributes
    ----------
    smiles : str
        SMILES of the repeating polymer unit with attachment points.
    left_cap : str
        SMILES of the left cap group with attachment point.
    right_cap : str
        SMILES of the right cap group with attachment point.
    length : int
        Number of monomers per chain.
    num_molecules : int
        Number of polymer chains in the box.
    density : float
        Initial packing density for the builder (g/cm3).
    box_type : str
        Box type code for PSP (e.g., 'c' for cubic).
    out_dir : Path
        Output directory for the generated structure.
    num_conf : int = 0
        Number of conformers to generate.
    loop : bool = False
        Whether to loop until target density is reached.
    """
    name: str = "psp_structure_generation"
    smiles: str = field(default="[*]")
    left_cap: str = field(default="[*]")
    right_cap: str = field(default="[*]")
    length: int = 1
    num_molecules: int = 1
    density: float = 0.1
    box_type: str = "c"
    out_dir: Path = field(default_factory=Path)
    num_conf: int = 1
    loop: bool = False

    @job
    def make(self) -> object:
        """
        Build the amorphous structure and return the PSPBuilder instance (`amor`).
        This builder is used for forcefield parametrization downstream.
        """
        # determine absolute output directory: if user-specified out_dir is not default '.', use it; else use cwd
        default_dir = Path('.')
        if self.out_dir is None or Path(self.out_dir) == default_dir:
            outdir = os.getcwd()
        else:
            outdir = str(Path(self.out_dir).absolute())
        amor = build_amorphous_structure(
            smiles=self.smiles,
            left_cap=self.left_cap,
            right_cap=self.right_cap,
            length=self.length,
            num_molecules=self.num_molecules,
            density=self.density,
            box_type=self.box_type,
            out_dir=outdir,
            num_conf=self.num_conf,
            loop=self.loop,
        )
        return amor
