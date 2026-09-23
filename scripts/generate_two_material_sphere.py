'''
Generate spherical DDSCAT shape.dat targets containing two materials

This script is only needed if you want an explicit two-material target with
FROM_FILE. It is not required for a homogeneous ELLIPSOID target

Material 1 and material 2 refer to the order of the dielectric files in
ddscat.par:

    2 = NCOMP
    'material_1.dat'
    'material_2.dat'

For an isotropic dipole:
    1 1 1 -> material 1
    2 2 2 -> material 2

The example below randomly replaces part of a compact sphere with material 2

Change the USER SETTINGS below
'''

from pathlib import Path

import numpy as np


OUTPUT_DIRECTORY = Path("two_material_targets")

# RADIUS = 35 corresponds to approximately D/d = 70.
RADIUS = 35

# Fraction of the grain volume assigned to material 2.
MATERIAL_2_FRACTIONS = [
    0.0,
    0.1,
    0.2,
    0.3,
    0.4,
    0.5,
    0.6,
]

# Fixed seed -> reproducible material distribution
USE_FIXED_SEED = True
SEED = 20260902


OUTPUT_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True
)


coordinates = []

limit = int(np.ceil(RADIUS)) + 2

for ix in range(-limit, limit + 1):
    for iy in range(-limit, limit + 1):
        for iz in range(-limit, limit + 1):

            if (
                ix**2
                + iy**2
                + iz**2
                <= RADIUS**2
            ):
                coordinates.append(
                    (ix, iy, iz)
                )


coordinates = np.array(
    coordinates,
    dtype=int
)

n_dipoles = len(coordinates)


if USE_FIXED_SEED:
    rng = np.random.default_rng(SEED)
else:
    rng = np.random.default_rng()


# One ordering is used for all fractions so the material-2 region grows
# consistently as the requested fraction increases.
order = rng.permutation(
    n_dipoles
)


def write_shape(filename, xyz, material_number):

    with open(filename, "w") as file:

        file.write("Two-material spherical target\n")
        file.write(f"{len(xyz)} = NAT\n")
        file.write("1.0 0.0 0.0 = A1\n")
        file.write("0.0 1.0 0.0 = A2\n")
        file.write("1.0 1.0 1.0 = lattice spacings\n")
        file.write("0.0 0.0 0.0 = X0\n")
        file.write("JA IX IY IZ ICOMPX ICOMPY ICOMPZ\n")

        for ja, ((ix, iy, iz), mat) in enumerate(
            zip(xyz, material_number),
            start=1
        ):
            file.write(
                f"{ja} "
                f"{ix} {iy} {iz} "
                f"{mat} {mat} {mat}\n"
            )


for fraction in MATERIAL_2_FRACTIONS:

    n_material_2 = round(
        fraction * n_dipoles
    )

    materials = np.ones(
        n_dipoles,
        dtype=int
    )

    materials[
        order[:n_material_2]
    ] = 2


    label = (
        f"F{int(round(100 * fraction)):02d}"
    )

    directory = (
        OUTPUT_DIRECTORY
        / label
    )

    directory.mkdir(
        exist_ok=True
    )


    write_shape(
        directory / "shape.dat",
        coordinates,
        materials
    )


    print(
        f"{label}: "
        f"{n_material_2} dipoles material 2, "
        f"{n_dipoles - n_material_2} dipoles material 1"
    )
