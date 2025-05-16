"""
Forcefield parametrization for a polymer Structure using LigParGen or Foyer.
"""
from pathlib import Path
from pymatgen.core.structure import Structure
import os


try:
    from foyer import Forcefield
except ImportError:
    Forcefield = None


def parametrize_ligpargen(amor, output_fname: str | None = None) -> str:
    """
    Use PSP AmorphousBuilder `amor` to generate an OPLS-AA LAMMPS file via its get_opls method.

    Returns path to generated .lmps file.
    """
    outdir = getattr(amor, 'OutDir', None)
    if outdir is None:
        raise ValueError('PSP builder instance missing OutDir attribute')
    # default output filename
    if output_fname is None:
        output_fname = os.path.join(outdir, 'amor_opls.lmps')
    # invoke PSP's OPLS method
    amor.get_opls(output_fname=output_fname)
    return output_fname


def parametrize_foyer(amor, forcefield_name: str = "oplsaa", output_fname: str | None = None) -> str:
    """
    Use PSP AmorphousBuilder `amor` to generate a LAMMPS data file via Foyer.
    Expects packmol.pdb in `amor.OutDir/packmol`.

    Returns path to generated .lammps file.
    """
    from mbuild import load as mb_load
    from forcefield_utilities import FoyerFFs
    from gmso.external.convert_mbuild import from_mbuild
    from gmso.parameterization import apply
    from gmso.formats.lammpsdata import write_lammpsdata

    outdir = getattr(amor, 'OutDir', None)
    if outdir is None:
        raise ValueError('PSP builder instance missing OutDir for Foyer parametrization')
    # packmol subdirectory contains packmol.pdb
    packdir = os.path.join(outdir, 'packmol')
    pdb = os.path.join(packdir, 'packmol.pdb')
    if not os.path.exists(pdb):
        # fallback: search OutDir for any .pdb
        files = [f for f in os.listdir(outdir) if f.endswith('.pdb')]
        if files:
            pdb = os.path.join(outdir, files[0])
        else:
            raise FileNotFoundError(f'packmol.pdb not found in {packdir} or {outdir}')
    # load with mbuild
    structure_mb = mb_load(pdb)
    # convert to GMSO topology & apply forcefield
    top = from_mbuild(structure_mb)
    ff = FoyerFFs.get_ff(forcefield_name).to_gmso_ff()
    apply(top=top, forcefields=ff, identify_connections=False)
    # write out
    if output_fname is None:
        output_fname = os.path.join(outdir, f'amor_{forcefield_name}.lammps')
    write_lammpsdata(top, filename=output_fname, atom_style='full')
    return output_fname


def parametrize_gaff2_pysimm(amor) -> str:
    """
    Parameterize using PSP-based GAFF2 with pysimm (placeholder stub).
    """
    raise NotImplementedError("GAFF2 pysimm parametrization not implemented yet.")


def parametrize_gaff2_antechamber(amor) -> str:
    """
    Parameterize using PSP-based GAFF2 with antechamber (placeholder stub).
    """
    raise NotImplementedError("GAFF2 antechamber parametrization not implemented yet.")


def parametrize_auto(amor) -> str:
    """
    Automatic forcefield selection: default to PSP OPLS (ligpargen), then foyer, then GAFF2 pysimm, then GAFF2 antechamber.
    """
    try:
        return parametrize_ligpargen(amor)
    except Exception:
        try:
            return parametrize_foyer(amor)
        except Exception:
            try:
                return parametrize_gaff2_pysimm(amor)
            except Exception:
                return parametrize_gaff2_antechamber(amor)
