'''
Generate porous spherical shape.dat targets for DDSCAT FROM_FILE.

This script is only needed if you want to create porous custom targets.
Change the values in the USER SETTINGS section near the top.

USE_FIXED_SEED = True  -> same random target every time
USE_FIXED_SEED = False -> new random target every time
'''

from pathlib import Path
import numpy as np


OUTPUT_DIRECTORY = Path("porous_targets")

# Outer radius in dipole-lattice units
# RADIUS = 35 gives approximately D/d = 70.
# increasing this value increases the number of dipoles/resolution
RADIUS = 35  # CHANGE THIS

# Porosity = fraction of dipoles removed from the compact sphere
POROSITIES = [
    0.0,
    0.1,
    0.2,
    0.3,
    0.4,
    0.5,
    0.6,
]  # CHANGE THIS

# Choose how the random target is generated
# True:
#   the same seed is used every time, so the same porous geometry
#   is generated again. This is useful for reproducibility
# False:
#   no fixed seed is used, so a new random porous geometry is
#   generated each time the script is run
USE_FIXED_SEED = True  # CHANGE THIS

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

            r2 = (
                ix**2
                + iy**2
                + iz**2
            )

            if r2 <= RADIUS**2:
                coordinates.append(
                    (ix, iy, iz)
                )

coordinates = np.array(
    coordinates,
    dtype=int
)

n_compact = len(coordinates)


if USE_FIXED_SEED:
    rng = np.random.default_rng(SEED)
else:
    rng = np.random.default_rng()


# One random ordering is reused for all porosities in this run
# Higher-porosity targets therefore remove additional dipoles
# from the same compact sphere
order = rng.permutation(
    n_compact
)


def write_shape(filename, xyz):

    with open(filename, "w") as file:

        file.write("Porous spherical target\n")
        file.write(f"{len(xyz)} = NAT\n")
        file.write("1.0 0.0 0.0 = A1\n")
        file.write("0.0 1.0 0.0 = A2\n")
        file.write("1.0 1.0 1.0 = lattice spacings\n")
        file.write("0.0 0.0 0.0 = X0\n")
        file.write("JA IX IY IZ ICOMPX ICOMPY ICOMPZ\n")

        for ja, (ix, iy, iz) in enumerate(
            xyz,
            start=1
        ):
            # 1 1 1 = material 1 in x, y and z.
            file.write(
                f"{ja} {ix} {iy} {iz} 1 1 1\n"
            )


for porosity in POROSITIES:

    n_keep = round(
        n_compact
        * (1.0 - porosity)
    )

    selected = coordinates[
        order[:n_keep]
    ]

    label = (
        f"P{int(round(100 * porosity)):02d}"
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
        selected
    )

    print(
        f"{label}: {len(selected)} / {n_compact} dipoles"
    )
