'''
Visualise a 2D slice through a DDSCAT shape.dat target.

This is an optional analysis script, not required to run DDSCAT.

It is useful for checking:
- whether a sphere/ellipsoid has the expected shape,
- where pores are located,
- how different materials are distributed inside one grain.

Change the USER SETTINGS below.
'''

from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt



SHAPE_FILE = Path("shape.dat")   # CHANGE THIS PATH

# Choose "xy", "xz", or "yz"
PLANE = "xy"

# Coordinate of the slice along the remaining axis
# 0 gives a central slice for targets centred near zero
SLICE_POSITION = 0

POINT_SIZE = 10


def read_shape(filename):
    lines = filename.read_text().splitlines()

    start = None

    for i, line in enumerate(lines):
        if line.strip().upper().startswith("JA"):
            start = i + 1
            break

    if start is None:
        raise ValueError(
            "Could not find the 'JA IX IY IZ ...' header in shape.dat."
        )

    rows = []

    for line in lines[start:]:
        values = line.split()

        if len(values) < 7:
            continue

        try:
            rows.append(
                [int(float(value)) for value in values[:7]]
            )
        except ValueError:
            continue

    if not rows:
        raise ValueError("No dipole rows found in shape.dat.")

    return np.array(rows)


data = read_shape(SHAPE_FILE)

x = data[:, 1]
y = data[:, 2]
z = data[:, 3]

# For an isotropic material assignment:
# 1 = first material listed in ddscat.par
# 2 = second material, etc.
material = data[:, 4].astype(int)


if PLANE == "xy":
    mask = z == SLICE_POSITION
    horizontal = x[mask]
    vertical = y[mask]
    horizontal_label = "x [dipole units]"
    vertical_label = "y [dipole units]"

elif PLANE == "xz":
    mask = y == SLICE_POSITION
    horizontal = x[mask]
    vertical = z[mask]
    horizontal_label = "x [dipole units]"
    vertical_label = "z [dipole units]"

elif PLANE == "yz":
    mask = x == SLICE_POSITION
    horizontal = y[mask]
    vertical = z[mask]
    horizontal_label = "y [dipole units]"
    vertical_label = "z [dipole units]"

else:
    raise ValueError(
        'PLANE must be "xy", "xz", or "yz".'
    )


slice_material = material[mask]

if len(horizontal) == 0:
    raise ValueError(
        "No dipoles found in this slice. "
        "Try a different SLICE_POSITION."
    )


plt.figure(figsize=(7, 7))

for material_number in np.unique(slice_material):
    selection = slice_material == material_number

    plt.scatter(
        horizontal[selection],
        vertical[selection],
        s=POINT_SIZE,
        label=f"Material {material_number}"
    )


plt.xlabel(horizontal_label)
plt.ylabel(vertical_label)

plt.axis("equal")
plt.legend()
plt.tight_layout()
plt.show()
