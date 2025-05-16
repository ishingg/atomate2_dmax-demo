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
    Use PSP AmorphousBuilder `amor` or wrapper to generate an OPLS-AA LAMMPS file via get_opls.

    Returns path to generated .lmps file.
    """
    cwd = os.getcwd()
    # unwrap wrapper if present
    if hasattr(amor, 'get_builder'):
        wrapper = amor
        # re-create builder; packmol.pdb already present in outdir/packmol
        builder = wrapper.get_builder()
        outdir = wrapper.out_dir
    else:
        builder = amor
        outdir = getattr(builder, 'OutDir', None)
    if not outdir:
        raise ValueError('PSP builder instance missing OutDir attribute')
    if output_fname is None:
        output_fname = os.path.join(cwd, 'amor_opls.lmps')
    # call PSP get_opls on real builder, ensuring CWD is the builder's output dir
    cwd = os.getcwd()
    try:
        os.chdir(outdir)
        builder.get_opls(output_fname=output_fname)
    finally:
        os.chdir(cwd)
    return output_fname


def parametrize_foyer(amor, forcefield_name: str = "oplsaa", output_fname: str | None = None) -> str:
    """
    Use PSP AmorphousBuilder `amor` or wrapper to generate a LAMMPS data file via Foyer.
    Expects packmol.pdb in `amor.OutDir/packmol`.

    Returns path to generated .lammps file.
    """
    # dynamic imports for Foyer/GMSO using importlib
    import importlib
    try:
        mb_module = importlib.import_module('mbuild')
        mb_load = getattr(mb_module, 'load')
        ffutils_mod = importlib.import_module('forcefield_utilities')
        FoyerFFs = getattr(ffutils_mod, 'FoyerFFs')
        conv_mod = importlib.import_module('gmso.external.convert_mbuild')
        from_mbuild = getattr(conv_mod, 'from_mbuild')
        param_mod = importlib.import_module('gmso.parameterization')
        apply = getattr(param_mod, 'apply')
        write_mod = importlib.import_module('gmso.formats.lammpsdata')
        write_lammpsdata = getattr(write_mod, 'write_lammpsdata')
    except ImportError as e:
        raise ImportError(
            "Install mbuild, forcefield_utilities, and gmso to enable Foyer parametrization."
        ) from e

    # unwrap wrapper if present
    if hasattr(amor, 'get_builder'):
        wrapper = amor
        builder = wrapper.get_builder()
        outdir = wrapper.out_dir
    else:
        builder = amor
        outdir = getattr(builder, 'OutDir', None)
    if not outdir:
        raise ValueError('PSP builder instance missing OutDir for Foyer parametrization')
    # locate packmol output
    packdir = os.path.join(outdir, 'packmol')
    pdb_file = os.path.join(packdir, 'packmol.pdb')
    if not os.path.exists(pdb_file):
        # fallback: search outdir for any .pdb
        files = [f for f in os.listdir(outdir) if f.endswith('.pdb')]
        if files:
            pdb_file = os.path.join(outdir, files[0])
        else:
            raise FileNotFoundError(f'packmol.pdb not found in {packdir} or {outdir}')
    # load structure with mbuild and convert to GMSO topology
    structure_mb = mb_load(pdb_file)
    gmso_top = from_mbuild(structure_mb)
    # apply foyer forcefield
    ff = FoyerFFs.get_ff(forcefield_name).to_gmso_ff()
    apply(top=gmso_top, forcefields=ff, identify_connections=False)
    # write output file
    if output_fname is None:
        output_fname = os.path.join(outdir, f'amor_{forcefield_name}.lammps')
    write_lammpsdata(gmso_top, filename=output_fname, atom_style='full')
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
