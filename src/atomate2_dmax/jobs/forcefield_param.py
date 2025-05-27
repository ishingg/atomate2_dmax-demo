import os
import shutil

@job(output_schema=None)
def make(self, amor) -> str:
    """
    Generate LAMMPS data file from PSP builder `amor` or its wrapper.
    By default uses automatic selection.
    """
    # only auto method supported
    if self.method != "auto":
        raise NotImplementedError(
            f"Explicit method '{self.method}' not supported; only 'auto'."
        )
    # reconstruct wrapper if needed
    if isinstance(amor, dict):
        amor = PSPBuilderWrapper.from_dict(amor)
    # run parametrization in the builder's output directory
    data_path = parametrize_auto(amor)
    # move generated file into this job's working directory
    cwd = os.getcwd()
    fname = os.path.basename(data_path)
    dest = os.path.join(cwd, fname)
    shutil.move(data_path, dest)
    return dest