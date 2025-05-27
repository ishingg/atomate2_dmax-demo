"""
Flow for Dynamic Mechanical Analysis (DMA) simulations.

Chains structure generation and forcefield parametrization.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jobflow import Flow, Maker

from atomate2.dmax.jobs.structure_generation import PSPStructureMaker
from atomate2.dmax.jobs.forcefield_param import ForceFieldMaker


@dataclass
class BaseDataGenerationFlow(Maker):
    name: str = "DMA workflow"
    smiles: str = "[*]CC[*]"
    left_cap: str = "C"
    right_cap: str = "C"
    length: int = 10
    num_molecules: int = 5
    density: float = 0.8
    box_type: str = "c"
    out_dir: Path | None = None
    num_conf: int = 1
    loop: bool = False

    def make(self) -> Flow:
        # determine working directory
        wd = str(self.out_dir) if self.out_dir else None
        # structure generation
        struct_job = PSPStructureMaker(
            smiles=self.smiles,
            left_cap=self.left_cap,
            right_cap=self.right_cap,
            length=self.length,
            num_molecules=self.num_molecules,
            density=self.density,
            box_type=self.box_type,
            out_dir=wd,
            num_conf=self.num_conf,
            loop=self.loop,
            return_builder=True,
        ).make()
        # forcefield
        ff_job = ForceFieldMaker(out_dir=wd).make(struct_job.output)
        # collect outputs
        result = {
            "pdb_molecule": f"{wd}/molecules/polymer.pdb" if wd else None,
            "pdb_amorphous": f"{wd}/packmol/packmol.pdb" if wd else None,
            "lammps_data": ff_job.output,
        }
        # return a Flow chaining the structure and forcefield jobs
        return Flow([struct_job, ff_job], result, name=self.name)
