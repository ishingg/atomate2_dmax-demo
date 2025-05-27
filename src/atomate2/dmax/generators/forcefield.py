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
    Generate an OPLS-AA LAMMPS file via PSP's get_opls.
    Returns the full path to the generated .lmp file.
    """
    # unwrap wrapper if present
    if hasattr(amor, 'get_builder'):
        # reconstruct the PSPBuilder and ensure its cell is built
        builder = amor.get_builder()
        # build cell dimensions (if not already present)
        try:
            builder.Build()
        except Exception:
            pass  # ignore if already built
        outdir = amor.out_dir
    else:
        builder = amor
        outdir = getattr(builder, 'OutDir', None)
    if not outdir:
        raise ValueError('PSP builder instance missing OutDir attribute')
    # define default output filename in builder directory
    if output_fname is None:
        output_fname = os.path.join(outdir, 'amor_opls.lmp')
    # call PSP to generate OPLS file
    orig_cwd = os.getcwd()
    try:
        os.chdir(outdir)
        # generate OPLS data file, builder now has cell dims
        builder.get_opls(output_fname=output_fname)
    finally:
        os.chdir(orig_cwd)
    return output_fname


def parametrize_foyer(amor, forcefield_name: str = "oplsaa", output_fname: str | None = None) -> str:
    """
    Use a PSPBuilderWrapper (`amor`) or a PDB file path to generate a LAMMPS data file via Foyer.
    Returns path to generated .lammps file.
    """
    # determine PDB file path
    if hasattr(amor, 'get_builder'):
        outdir = amor.out_dir
        pdb_file = os.path.join(outdir, 'packmol', 'packmol.pdb')
    elif isinstance(amor, (str, Path)) and str(amor).lower().endswith('.pdb'):
        pdb_file = str(amor)
    else:
        raise ValueError('Input must be a PSPBuilderWrapper or a .pdb file path')
    if not os.path.exists(pdb_file):
        raise FileNotFoundError(f'pdb file not found: {pdb_file}')
    # dynamic imports for Foyer/GMSO
    import importlib
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
    # run foyer parametrization
    structure_mb = mb_load(pdb_file)
    gmso_top = from_mbuild(structure_mb)
    ff = FoyerFFs.get_ff(forcefield_name).to_gmso_ff()
    apply(top=gmso_top, forcefields=ff, identify_connections=False)
    # write output file
    if output_fname is None:
        output_fname = os.path.join(os.getcwd(), f'amor_{forcefield_name}.lammps')
    write_lammpsdata(gmso_top, filename=output_fname, atom_style='full')
    return output_fname


def parametrize_gaff2_pysimm(amor) -> str:
    """
    Parameterize using PSP-based GAFF2 with pysimm atom typing.
    Returns path to generated LAMMPS file.
    """
    # unwrap wrapper if present
    if hasattr(amor, 'get_builder'):
        builder = amor.get_builder()
        outdir = amor.out_dir
    else:
        builder = amor
        outdir = getattr(amor, 'OutDir', None)
    if not outdir:
        raise ValueError('PSP builder instance missing OutDir for GAFF2 pysimm')
    # change to output directory, run get_gaff2
    orig_cwd = os.getcwd()
    try:
        os.chdir(outdir)
        # generate GAFF2 file with pysimm typing
        builder.get_gaff2(output_fname='amor_pysimm.lmps', atom_typing='pysimm')
    finally:
        os.chdir(orig_cwd)
    # return the full path to generated file
    return os.path.join(outdir, 'amor_pysimm.lmps')


def parametrize_gaff2_antechamber(amor) -> str:
    """
    Parameterize using PSP-based GAFF2 with antechamber atom typing.
    Returns path to generated LAMMPS file.
    """
    # unwrap wrapper if present
    if hasattr(amor, 'get_builder'):
        builder = amor.get_builder()
        outdir = amor.out_dir
    else:
        builder = amor
        outdir = getattr(amor, 'OutDir', None)
    if not outdir:
        raise ValueError('PSP builder instance missing OutDir for GAFF2 antechamber')
    # change to output directory, run get_gaff2
    orig_cwd = os.getcwd()
    try:
        os.chdir(outdir)
        # generate GAFF2 file with antechamber typing
        builder.get_gaff2(output_fname='amor_antechamber.lmps', atom_typing='antechamber')
    finally:
        os.chdir(orig_cwd)
    # return the full path to generated file
    return os.path.join(outdir, 'amor_antechamber.lmps')


def parametrize_auto(amor) -> str:
    """
    Automatic forcefield selection: default to PSP OPLS (ligpargen), then foyer, then GAFF2 pysimm, then GAFF2 antechamber.
    Adds debug output to trace failures.
    """
    # Try LigParGen
    print("parametrize_auto: attempting LigParGen OPLS-AA parametrization...")
    try:
        path = parametrize_ligpargen(amor)
        print("parametrize_auto: LigParGen succeeded ->", path)
        return path
    except Exception as e:
        print(f"parametrize_auto: LigParGen failed: {e}")
    # Try Foyer
    print("parametrize_auto: attempting Foyer parametrization...")
    try:
        path = parametrize_foyer(amor)
        print("parametrize_auto: Foyer succeeded ->", path)
        return path
    except Exception as e:
        print(f"parametrize_auto: Foyer failed: {e}")
    # Try GAFF2 pysimm
    print("parametrize_auto: attempting GAFF2 pysimm parametrization...")
    try:
        path = parametrize_gaff2_pysimm(amor)
        print("parametrize_auto: GAFF2 pysimm succeeded ->", path)
        return path
    except Exception as e:
        print(f"parametrize_auto: GAFF2 pysimm failed: {e}")
    # Fallback to GAFF2 antechamber
    print("parametrize_auto: attempting GAFF2 antechamber parametrization...")
    path = parametrize_gaff2_antechamber(amor)
    print("parametrize_auto: GAFF2 antechamber succeeded ->", path)
    return path

    print(f"[DEBUG] After mainBOSS2LAMMPS, outdir contents = {os.listdir(os.getcwd())}")
