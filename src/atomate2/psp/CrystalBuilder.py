import numpy as np
import pandas as pd
import os
from scipy.spatial.distance import cdist
import time
import multiprocessing
from joblib import Parallel, delayed
from psp import PSP_lib as bd
from psp import output_lib as lib
from tqdm import tqdm


class Builder:
    def __init__(
        self,
        VaspInp_list,
        NSamples=5,
        InputRadius='auto',
        MinAtomicDis=2.0,
        OutDir='crystals',
        Polymer=True,
        Optimize=False,
        NumCandidate=50,
        NCores=0,
    ):
        self.VaspInp_list = VaspInp_list
        self.NSamples = NSamples
        self.InputRadius = InputRadius
        self.MinAtomicDis = MinAtomicDis
        self.OutDir = os.path.join(OutDir, "")
        self.NCores = NCores
        self.Polymer = Polymer
        self.Optimize = Optimize
        self.NumCandidate = NumCandidate

    def BuildCrystal(self):
        start_1 = time.time()
        lib.print_psp_info()  # Print PSP info
        lib.print_input("CrystalBuilder")
        if self.Optimize is False:
            self.NumCandidate == 'All'
        if self.NCores <= 0:
            ncore_print = 'All'
        else:
            ncore_print = self.NCores

        print(
            " ----------------------------------------------- INPUT --------------------------------------------- ",
            "\n",
            "List of chain models (POSCAR): ",
            self.VaspInp_list,
            "\n",
            "Are they infinite polymer chains?: ",
            self.Polymer,
            "\n",
            "Number of samples: ",
            self.NSamples,
            "\n",
            "Optimize models: ",
            self.Optimize,
            "\n",
            "Number of models to be selected: ",
            self.NumCandidate,
            "\n",
            "Minimum atomic distance (angstrom): ",
            self.MinAtomicDis,
            "\n",
            "Number of cores: ",
            ncore_print,
            "\n",
            "Output directory: ",
            self.OutDir,
            "\n",
        )

        build_dir(self.OutDir)
        # result = []

        if self.NCores == 0:
            self.NCores = multiprocessing.cpu_count() - 1

        NCores_opt = 1
        NCores = self.NCores

        if self.Polymer is True:
            if isinstance(self.NSamples, int):
                print(
                    ' maximum number of possible crustals for each polymer chain: ',
                    self.NSamples * self.NSamples * self.NSamples,
                    "\n",
                )
            else:
                print(
                    ' maximum number of possible crustals for each polymer chain: ',
                    len(self.NSamples[0])
                    * len(self.NSamples[1])
                    * len(self.NSamples[2]),
                    "\n",
                )
        else:
            if isinstance(self.NSamples, int):
                print(
                    ' maximum number of possible crustals for each chain: ',
                    self.NSamples ** 8,
                    "\n",
                )
            else:
                print(
                    ' maximum number of possible crustals for each polymer chain: ',
                    len(self.NSamples[0])
                    * len(self.NSamples[1])
                    * len(self.NSamples[2])
                    * len(self.NSamples[3])
                    * len(self.NSamples[4])
                    * len(self.NSamples[5])
                    * len(self.NSamples[6])
                    * len(self.NSamples[7]),
                    "\n",
                )

        if self.Polymer is True:
            result = Parallel(n_jobs=NCores)(
                delayed(CrystalBuilderMainPolymer)(
                    VaspInp,
                    self.NSamples,
                    self.InputRadius,
                    self.MinAtomicDis,
                    self.OutDir,
                    self.Optimize,
                    self.NumCandidate,
                    NCores_opt,
                )
                for VaspInp in tqdm(self.VaspInp_list, desc="Building models ...")
            )
        else:
            result = Parallel(n_jobs=NCores)(
                delayed(CrystalBuilderMain)(
                    VaspInp,
                    self.NSamples,
                    self.InputRadius,
                    self.MinAtomicDis,
                    self.OutDir,
                    self.Optimize,
                    self.NumCandidate,
                    NCores_opt,
                )
                for VaspInp in tqdm(self.VaspInp_list, desc="Building models ...")
            )

        output = []
        for i in result:
            output.append([i[0].replace('.vasp', ''), i[1], i[2]])

        output = pd.DataFrame(output, columns=['ID', 'Count', 'radius'])
        end_1 = time.time()
        lib.print_out(output, "Crystal model", np.round((end_1 - start_1) / 60, 2))
        return output


def readvasp(inputvasp):
    basis_vec = []
    Num_atom = []
    xyz_coordinates = []
    with open(inputvasp, 'r') as f:
        content = [line.rstrip() for line in f]
        file_info = content[0]
        for vec in content[2:5]:
            basis_vec.append(vec.split())
        basis_vec = pd.DataFrame(basis_vec)
        for atoms in content[5:7]:
            Num_atom.append(atoms.split())
        Num_atom = pd.DataFrame(Num_atom)

        nats = 0
        for nat in np.array(Num_atom.iloc[1]):
            nats += int(nat)

        # Do not read all the lines in the POSCAR generated by VASP.
        for xyz in content[8: 8 + nats]:
            xyz_coordinates.append(xyz.split())

        # There are two modes in writing coordinated, Direct and Cartesian
        if str(content[7]).startswith('D'):
            rprim = np.array(basis_vec)
            xred = np.array(xyz_coordinates)
            xcart = np.matmul(
                np.transpose(rprim).astype(float), np.transpose(xred).astype(float)
            )
            xyz_coordinates = pd.DataFrame(np.transpose(xcart)).astype(float)
        elif str(content[7]).startswith('C'):
            xyz_coordinates = pd.DataFrame(xyz_coordinates).astype(float)
    xyz_coordinates.columns = [1, 2, 3]
    return file_info, basis_vec, Num_atom, xyz_coordinates


# Center of origin + peri_circle
def Center_XY_r(xyz_coordinates, angle, r_cricle):
    xyz_copy = xyz_coordinates.copy()
    X_avg = xyz_copy[1].mean()
    Y_avg = xyz_copy[2].mean()
    xyz_copy[1] = xyz_copy[1] - X_avg + np.cos(np.deg2rad(angle)) * r_cricle
    xyz_copy[2] = xyz_copy[2] - Y_avg + np.sin(np.deg2rad(angle)) * r_cricle
    return xyz_copy


def create_crystal_vasp(
    filename,
    first_poly,
    second_poly,
    Num_atom,
    basis_vec,
    file_info,
    cry_info,
    MinAtomicDis,
    Polymer=True,
):
    crystal_struc = pd.DataFrame()
    row1 = 0
    for col in Num_atom.columns:
        crystal_struc = pd.concat(
            [
                crystal_struc,
                first_poly.loc[row1: row1 + int(Num_atom[col].values[1]) - 1],
                second_poly.loc[row1: row1 + int(Num_atom[col].values[1]) - 1],
            ]
        )
        row1 += int(Num_atom[col].values[1])

    Crystal_Num_atom = Num_atom.copy()
    Crystal_Num_atom.loc[1] = 2 * Crystal_Num_atom.loc[1].astype(int)
    keep_space = MinAtomicDis  # in angstrom

    crystal_struc[1] = crystal_struc[1] - crystal_struc[1].min() + keep_space / 2
    crystal_struc[2] = crystal_struc[2] - crystal_struc[2].min() + keep_space / 2

    with open(filename, 'w') as f:
        f.write(file_info + ' (' + cry_info + ')\n')
        f.write('1.0' + '\n')
        a_vec = crystal_struc[1].max() - crystal_struc[1].min() + keep_space
        b_vec = crystal_struc[2].max() - crystal_struc[2].min() + keep_space

        if Polymer is True:
            c_vec = basis_vec.loc[2, 2]
        else:
            c_vec = crystal_struc[3].max() - crystal_struc[3].min() + keep_space

        f.write(' ' + str(a_vec) + ' ' + str(0.0) + ' ' + str(0.0) + '\n')
        f.write(' ' + str(0.0) + ' ' + str(b_vec) + ' ' + str(0.0) + '\n')
        f.write(' ' + str(0.0) + ' ' + str(0.0) + ' ' + str(c_vec) + '\n')

        f.write(Crystal_Num_atom.to_string(header=False, index=False))
        f.write('\nCartesian\n')
        f.write(crystal_struc.to_string(header=False, index=False))


# Translation
# INPUT: XYZ-coordinates and distance
# OUTPUT: A new sets of XYZ-coordinates
def tl(unit, dis):
    unit_copy = unit.copy()
    unit_copy[3] = unit_copy[3] + dis  # Z direction
    return unit_copy


# Distance between two points
def CalDis(x1, x2, x3, y1, y2, y3):
    return np.sqrt((x1 - y1) ** 2 + (x2 - y2) ** 2 + (x3 - y3) ** 2)


# This function try to create a directory
# If it fails, the program will be terminated.
def build_dir(path):
    try:
        #        os.mkdir(path)
        os.makedirs(path)
    except OSError:
        pass


# Rotate on XY plane
# INPUT: XYZ-coordinates and angle in Degree
# OUTPUT: A new sets of XYZ-coordinates
def rotateXY(xyz_coordinates, theta):  # XYZ coordinates and angle
    unit = xyz_coordinates.copy()
    R_z = np.array(
        [
            [np.cos(theta * np.pi / 180.0), -np.sin(theta * np.pi / 180.0)],
            [np.sin(theta * np.pi / 180.0), np.cos(theta * np.pi / 180.0)],
        ]
    )
    oldXYZ = unit[[1, 2]].copy()
    XYZcollect = []
    for eachatom in np.arange(oldXYZ.values.shape[0]):
        rotate_each = oldXYZ.iloc[eachatom].values.dot(R_z)
        XYZcollect.append(rotate_each)
    newXYZ = pd.DataFrame(XYZcollect)
    unit[[1, 2]] = newXYZ[[0, 1]]
    return unit


# for VaspInp in VaspInp_list:
def CrystalBuilderMainPolymer(
    VaspInp,
    NSamples,
    Input_radius,
    MinAtomicDis,
    OutDir,
    Optimize,
    NumCandidate,
    NCores_opt,
):
    file_info, basis_vec, Num_atom, xyz_coordinates = readvasp(
        VaspInp.replace('.vasp', '') + '.vasp'
    )
    VaspInp = VaspInp.split('/')[-1].replace('.vasp', '')
    print(" Crystal model building started for", VaspInp, "...")
    build_dir(OutDir + VaspInp)  # .split('/')[-1])

    if isinstance(NSamples, int):
        samples = NSamples - 1
        tm = np.around(
            np.arange(
                0,
                max(xyz_coordinates[3].values)
                - min(xyz_coordinates[3].values)
                + (max(xyz_coordinates[3].values) - min(xyz_coordinates[3].values))
                / samples,
                (max(xyz_coordinates[3].values) - min(xyz_coordinates[3].values))
                / samples,
            ),
            decimals=2,
        )
        rm1 = np.around(np.arange(0, 180 + (180 / samples), 180 / samples), decimals=1)
        rm2 = np.around(
            np.arange(0, 360 + (360 / samples), 360 / samples), decimals=1
        )  # 0 and 180 degree creates problems

        # Total samples
        samp = [tm, rm1, rm2]

        # Number of digits in total number of crystal models
        digits = bd.len_digit_number(NSamples * NSamples * NSamples)

    elif isinstance(NSamples, list):
        if len(NSamples) == 3 and isinstance(NSamples[0], list) is True:
            samp = NSamples.copy()
            # Number of digits in total number of crystal models
            digits = bd.len_digit_number(len(samp[0]) * len(samp[1]) * len(samp[2]))
        else:
            print("There is an error in inputs: Check 'NSamples'")
            exit()
    else:
        print("There is an error in inputs: Check 'NSamples'")
        exit()

    first_poly = Center_XY_r(xyz_coordinates, 0.0, 0.0)

    # Calculate distance between two chains
    if Input_radius == 'auto':
        radius = (
            np.sqrt(
                (
                    (first_poly[1].max() - first_poly[1].min())
                    * (first_poly[1].max() - first_poly[1].min())
                )
                + (
                    (first_poly[2].max() - first_poly[2].min())
                    * (first_poly[2].max() - first_poly[2].min())
                )
            )
            + MinAtomicDis
        )

    else:
        radius = float(Input_radius)

    count = 0
    for i in tqdm(samp[0], desc=VaspInp):
        for j in samp[2]:
            for k in samp[1]:
                second_poly_tl = tl(xyz_coordinates, i)
                second_poly_rm1 = rotateXY(second_poly_tl, j)
                second_poly_rm2 = Center_XY_r(second_poly_rm1, k, radius)

                if Input_radius == 'auto':
                    # Calculate distance between atoms in first_unit and second_unit
                    dist = cdist(
                        first_poly[[1, 2, 3]].values, second_poly_rm2[[1, 2, 3]].values,
                    )
                    dist[np.isnan(dist)] = 0.0
                    dist = dist.flatten()

                    adj_radius = radius - (min(dist) - MinAtomicDis)
                    second_poly_rm2 = Center_XY_r(second_poly_rm1, k, adj_radius)

                    dist = cdist(
                        first_poly[[1, 2, 3]].values, second_poly_rm2[[1, 2, 3]].values,
                    )
                    dist[np.isnan(dist)] = 0.0
                    dist = dist.flatten()
                    while min(dist) < MinAtomicDis or min(dist) >= MinAtomicDis + 0.5:
                        if min(dist) < MinAtomicDis:
                            adj_radius += 0.4
                            second_poly_rm2 = Center_XY_r(
                                second_poly_rm1, k, adj_radius
                            )
                            dist = cdist(
                                first_poly[[1, 2, 3]].values,
                                second_poly_rm2[[1, 2, 3]].values,
                            )
                            dist[np.isnan(dist)] = 0.0
                            dist = dist.flatten()
                        elif min(dist) >= MinAtomicDis + 0.5:
                            adj_radius -= 0.4
                            if adj_radius < 0.5:
                                break
                            second_poly_rm2 = Center_XY_r(
                                second_poly_rm1, k, adj_radius
                            )
                            dist = cdist(
                                first_poly[[1, 2, 3]].values,
                                second_poly_rm2[[1, 2, 3]].values,
                            )
                            dist[np.isnan(dist)] = 0.0
                            dist = dist.flatten()

                count += 1
                create_crystal_vasp(
                    os.path.join(
                        OutDir,
                        VaspInp,
                        'cryst_out-' + str(count).zfill(digits) + '.vasp',
                    ),
                    first_poly,
                    second_poly_rm2,
                    Num_atom,
                    basis_vec,
                    file_info,
                    'CrystalBuilder Info:: Translation: '
                    + str(i)
                    + '; '
                    + 'Rotation 1 '
                    + str(j)
                    + '; '
                    + 'Rotation 2 '
                    + str(k),
                    MinAtomicDis,
                )
    print(" Crystal model building completed for", VaspInp)
    if Optimize is True:
        print(" Optimizing crystal models started for", VaspInp, "...")
        bd.screen_Candidates(
            OutDir + VaspInp, NumCandidate=NumCandidate, NCores_opt=NCores_opt
        )
        print(" Optimizing crystal models completed for", VaspInp)
    return VaspInp, count, radius


# for VaspInp in VaspInp_list:
def CrystalBuilderMain(
    VaspInp,
    NSamples,
    Input_radius,
    MinAtomicDis,
    OutDir,
    Optimize,
    NumCandidate,
    NCores_opt,
):
    file_info, basis_vec, Num_atom, xyz_coordinates = readvasp(
        VaspInp.replace('.vasp', '') + '.vasp'
    )
    VaspInp = VaspInp.split('/')[-1].replace('.vasp', '')
    print(" Crystal model building started for", VaspInp, "...")
    build_dir(OutDir + VaspInp)  # .split('/')[-1])

    if isinstance(NSamples, int):
        samples = NSamples - 1
        tm = np.around(
            np.arange(
                0,
                max(xyz_coordinates[3].values)
                - min(xyz_coordinates[3].values)
                + (max(xyz_coordinates[3].values) - min(xyz_coordinates[3].values))
                / samples,
                (max(xyz_coordinates[3].values) - min(xyz_coordinates[3].values))
                / samples,
            ),
            decimals=2,
        )
        rm1 = np.around(np.arange(0, 180 + (180 / samples), 180 / samples), decimals=1)
        rm2 = np.around(
            np.arange(0, 360 + (360 / samples), 360 / samples), decimals=1
        )  # Rotation in X and Y axes

        # Total samples
        samp = [tm, rm1, rm2, rm2, rm2, rm2, rm2, rm2]

        # Number of digits in total number of crystal models
        digits = bd.len_digit_number(NSamples ** 8)

    elif isinstance(NSamples, list):
        if len(NSamples) == 8 and isinstance(NSamples[0], list) is True:
            samp = NSamples.copy()

            # Number of digits in total number of crystal models
            digits = bd.len_digit_number(
                len(samp[0])
                * len(samp[1])
                * len(samp[2])
                * len(samp[3])
                * len(samp[4])
                * len(samp[5])
                * len(samp[6])
                * len(samp[7])
            )

        else:
            print("There is an error in inputs: Check 'NSamples'")
            exit()
    else:
        print("There is an error in inputs: Check 'NSamples'")
        exit()

    first_poly = Center_XY_r(xyz_coordinates, 0.0, 0.0)

    # Calculate distance between two chains
    if Input_radius == 'auto':
        radius = (
            np.sqrt(
                (
                    (first_poly[1].max() - first_poly[1].min())
                    * (first_poly[1].max() - first_poly[1].min())
                )
                + (
                    (first_poly[2].max() - first_poly[2].min())
                    * (first_poly[2].max() - first_poly[2].min())
                )
            )
            + MinAtomicDis
        )

    else:
        radius = float(Input_radius)

    # Number of digits in total number of crystal models
    # digits = bd.len_digit_number(NSamples ** 8)

    count = 0
    for i in tqdm(samp[0], desc=VaspInp + " Generating models"):  # Second poly
        for j in samp[2]:  # Second poly
            for k in samp[1]:  # Second poly
                for aX in samp[3]:  # Second poly
                    for aY in samp[4]:  # Second poly
                        for bX in samp[5]:  # First poly
                            for bY in samp[6]:  # First poly
                                for bZ in samp[7]:  # First poly

                                    first_poly_bX = bd.rotateXYZOrigin(
                                        first_poly, bX, 0.0, 0.0
                                    )
                                    first_poly_bY = bd.rotateXYZOrigin(
                                        first_poly_bX, 0.0, bY, 0.0
                                    )
                                    first_poly_moved = bd.rotateXYZOrigin(
                                        first_poly_bY, 0.0, 0.0, bZ
                                    )

                                    second_poly_tl = tl(xyz_coordinates, i)
                                    second_poly_rm1 = rotateXY(second_poly_tl, j)
                                    second_poly_rm2_aX = bd.rotateXYZOrigin(
                                        second_poly_rm1, aX, 0.0, 0.0
                                    )
                                    second_poly_rm2_aY = bd.rotateXYZOrigin(
                                        second_poly_rm2_aX, 0.0, aY, 0.0
                                    )
                                    second_poly_moved = Center_XY_r(
                                        second_poly_rm2_aY, k, radius
                                    )

                                    if Input_radius == 'auto':
                                        # Calculate distance between atoms in first_unit and second_unit
                                        dist = cdist(
                                            first_poly_moved[[1, 2, 3]].values,
                                            second_poly_moved[[1, 2, 3]].values,
                                        )
                                        dist[np.isnan(dist)] = 0.0
                                        dist = dist.flatten()

                                        adj_radius = radius - (min(dist) - MinAtomicDis)
                                        second_poly_moved = Center_XY_r(
                                            second_poly_rm2_aY, k, adj_radius
                                        )

                                        dist = cdist(
                                            first_poly_moved[[1, 2, 3]].values,
                                            second_poly_moved[[1, 2, 3]].values,
                                        )
                                        dist[np.isnan(dist)] = 0.0
                                        dist = dist.flatten()
                                        while (
                                            min(dist) < MinAtomicDis
                                            or min(dist) >= MinAtomicDis + 0.5
                                        ):
                                            if min(dist) < MinAtomicDis:
                                                adj_radius += 0.4
                                                second_poly_moved = Center_XY_r(
                                                    second_poly_rm2_aY, k, adj_radius
                                                )
                                                dist = cdist(
                                                    first_poly_moved[[1, 2, 3]].values,
                                                    second_poly_moved[[1, 2, 3]].values,
                                                )
                                                dist[np.isnan(dist)] = 0.0
                                                dist = dist.flatten()
                                            elif min(dist) >= MinAtomicDis + 0.5:
                                                adj_radius -= 0.4
                                                if adj_radius < 0.5:
                                                    break
                                                second_poly_moved = Center_XY_r(
                                                    second_poly_rm2_aY, k, adj_radius
                                                )
                                                dist = cdist(
                                                    first_poly_moved[[1, 2, 3]].values,
                                                    second_poly_moved[[1, 2, 3]].values,
                                                )
                                                dist[np.isnan(dist)] = 0.0
                                                dist = dist.flatten()

                                    count += 1
                                    create_crystal_vasp(
                                        os.path.join(
                                            OutDir,
                                            VaspInp,
                                            'cryst_out-'
                                            + str(count).zfill(digits)
                                            + '.vasp',
                                        ),
                                        first_poly_moved,
                                        second_poly_moved,
                                        Num_atom,
                                        basis_vec,
                                        file_info,
                                        'CrystalBuilder Info:: Translation: '
                                        + str(i)
                                        + '; '
                                        + 'Rotation 1 '
                                        + str(j)
                                        + '; '
                                        + 'Rotation 2 '
                                        + str(k),
                                        MinAtomicDis,
                                        Polymer=False,
                                    )
    print(" Crystal model building completed for", VaspInp)
    if Optimize is True:
        print(" Optimizing crystal models started for", VaspInp, "...")
        bd.screen_Candidates(
            OutDir + VaspInp, NumCandidate=NumCandidate, NCores_opt=NCores_opt
        )
        print(" Optimizing crystal models completed for", VaspInp)

    return VaspInp, count, radius
