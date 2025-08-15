"""
Flow for Dynamic Mechanical Analysis (DMA) simulations.

Chains structure generation and forcefield parametrization.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import os

from jobflow import Flow, Maker  # ensure Flow is imported

from dmax.jobs.structure_generation import PSPStructureMaker
from dmax.jobs.forcefield_param import ForceFieldMaker
from dmax.schemas.task import DmaxDataGenerationFlowDocument


@dataclass
class BaseDataGenerationFlow(Maker):
    #these vars are all place holders, to be replaced by info from frontend 
    name: str = "DMAcon workflow"
    out_dir: Path | None = None
    
    def make(
        self,
        smiles: str = "[*]CC[*]",
        left_cap: str = "C",
        right_cap: str = "C",
        length: int = 10,
        num_molecules: int = 5,
        density: float = 0.8,
        box_type: str = "c",
        num_conf: int = 1,
        loop: bool = False
    ) -> Flow:
        # determine working directory
        wd = str(self.out_dir) if self.out_dir else None
        # structure generation
        struct_job = PSPStructureMaker(
            smiles=smiles,
            left_cap=left_cap,
            right_cap=right_cap,
            length=length,
            num_molecules=num_molecules,
            # default the density value 
            density=density,
            box_type=box_type,
            out_dir=wd,
            num_conf=num_conf,
            loop=loop,
            return_builder=True,
        ).make()
        # forcefield
        ff_job = ForceFieldMaker(out_dir=wd).make(struct_job.output)
        # assemble final document using task documents from each job
        struct_doc = struct_job.output  # DmaxStructureTaskDocument
        ff_doc = ff_job.output  # DmaxForceFieldTaskDocument
        doc = DmaxDataGenerationFlowDocument(
            packmol_pdb=struct_doc.packmol_pdb,
            polymer_pdb=struct_doc.polymer_pdb,
            lammps_data=ff_doc.lammps_data,
        )
        # return a Flow chaining the structure and forcefield jobs
        return Flow([struct_job, ff_job], doc, name=self.name)
