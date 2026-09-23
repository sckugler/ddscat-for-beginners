'''
Visualise one z-slice through a custom DDSCAT shape.dat file

This is an analysis/example script, not required to run DDSCAT
Change SHAPE_FILE, SLICE_Z and optionally POINT_SIZE near the top
'''

from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt


# CHANGE THESE VALUES
SHAPE_FILE = Path("shape.dat")
SLICE_Z = 0
POINT_SIZE = 8


# shape.dat columns:
# JA IX IY IZ ICOMPX ICOMPY ICOMPZ
data = np.loadtxt(
    SHAPE_FILE,
    skiprows=7
)

x = data[:, 1]
y = data[:, 2]
z = data[:, 3]

# For isotropic materials, ICOMPX is enough to identify the material.
material = data[:, 4].astype(int)

slice_mask = (z == SLICE_Z)

plt.figure(figsize=(6, 6))

for material_number in np.unique(material):
    selection = (
        slice_mask
        & (material == material_number)
    )

    plt.scatter(
        x[selection],
        y[selection],
        s=POINT_SIZE,
        label=f"Material {material_number}"
    )

plt.xlabel("x")
plt.ylabel("y")
plt.axis("equal")
plt.legend()
plt.tight_layout()
plt.show()
