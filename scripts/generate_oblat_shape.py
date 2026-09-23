'''
Generate an oblate ellipsoidal DDSCAT shape.dat target.

This script is optional. DDSCAT can already create a homogeneous ellipsoid
internally with CSHAPE = ELLIPSOID. Use this script when you specifically want
a shape.dat target, for example to add porosity or multiple materials later.

The semi-axes below are measured in dipole-lattice units

Example:
    A_X = 35
    A_Y = 35
    A_Z = 20

gives a grain that is flattened along z

Change the USER SETTINGS below
'''

from pathlib import Path

import numpy as np



OUTPUT_FILE = Path("shape.dat")

# Semi-axes in units of the dipole spacing d.
A_X = 35
A_Y = 35
A_Z = 20


coordinates = []


for ix in range(-A_X, A_X + 1):
    for iy in range(-A_Y, A_Y + 1):
        for iz in range(-A_Z, A_Z + 1):

            ellipsoid = (
                (ix / A_X)**2
                + (iy / A_Y)**2
                + (iz / A_Z)**2
            )

            if ellipsoid <= 1.0:
                coordinates.append(
                    (ix, iy, iz)
                )


coordinates = np.array(
    coordinates,
    dtype=int
)


with open(OUTPUT_FILE, "w") as file:

    file.write("Oblate ellipsoidal target\n")
    file.write(f"{len(coordinates)} = NAT\n")
    file.write("1.0 0.0 0.0 = A1\n")
    file.write("0.0 1.0 0.0 = A2\n")
    file.write("1.0 1.0 1.0 = lattice spacings\n")
    file.write("0.0 0.0 0.0 = X0\n")
    file.write("JA IX IY IZ ICOMPX ICOMPY ICOMPZ\n")

    for ja, (ix, iy, iz) in enumerate(
        coordinates,
        start=1
    ):
        file.write(
            f"{ja} {ix} {iy} {iz} 1 1 1\n"
        )


print(
    f"Wrote {OUTPUT_FILE}"
)

print(
    f"N = {len(coordinates)} dipoles"
)

print(
    "Full dimensions in dipole units: "
    f"{2*A_X} x {2*A_Y} x {2*A_Z}"
)
