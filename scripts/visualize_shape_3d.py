'''
Visualise a DDSCAT shape.dat target in 3D.

This is an optional analysis script, not required to run DDSCAT

It reads the dipole coordinates from shape.dat and plots the target as a
3D point cloud. Different material numbers are plotted separately.

Usually, only change the USER SETTINGS below.

For very large targets, only a random subset of dipoles is plotted so that
the figure remains responsive. This does NOT change the DDSCAT target itself.
'''

from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

SHAPE_FILE = Path("shape.dat")   # CHANGE THIS PATH

# Maximum number of dipoles to draw
# Increase for a denser figure; decrease if plotting is slow
MAX_POINTS = 30000

POINT_SIZE = 2

# Fixed seed is only used for selecting which points are displayed
# It does NOT modify shape.dat
DISPLAY_SEED = 1


def read_shape(filename):
    """
    Read the dipole table from shape.dat.

    The script finds the line beginning with 'JA' automatically, so it does
    not depend on a fixed number of header lines.
    """

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

# For isotropic targets, ICOMPX identifies the material.
material = data[:, 4].astype(int)


# Downsample only for plotting if the target is very large.
if len(data) > MAX_POINTS:
    rng = np.random.default_rng(DISPLAY_SEED)

    indices = rng.choice(
        len(data),
        size=MAX_POINTS,
        replace=False
    )

    x = x[indices]
    y = y[indices]
    z = z[indices]
    material = material[indices]


fig = plt.figure(figsize=(8, 7))
ax = fig.add_subplot(111, projection="3d")


for material_number in np.unique(material):
    mask = material == material_number

    ax.scatter(
        x[mask],
        y[mask],
        z[mask],
        s=POINT_SIZE,
        label=f"Material {material_number}"
    )


ax.set_xlabel("x [dipole units]")
ax.set_ylabel("y [dipole units]")
ax.set_zlabel("z [dipole units]")

# Keep the same scale on all three axes so spheres look spherical.
x_range = x.max() - x.min()
y_range = y.max() - y.min()
z_range = z.max() - z.min()

largest_range = max(
    x_range,
    y_range,
    z_range
)

x_mid = 0.5 * (x.max() + x.min())
y_mid = 0.5 * (y.max() + y.min())
z_mid = 0.5 * (z.max() + z.min())

half = largest_range / 2

ax.set_xlim(x_mid - half, x_mid + half)
ax.set_ylim(y_mid - half, y_mid + half)
ax.set_zlim(z_mid - half, z_mid + half)

ax.legend()
plt.tight_layout()
plt.show()
