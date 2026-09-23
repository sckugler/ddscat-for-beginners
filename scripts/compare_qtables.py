'''
Compare Qabs from two DDSCAT qtable files.

This is an analysis/example script, not required to run DDSCAT.
Change only the file paths and plotting options near the top.
'''

from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt


# CHANGE THESE PATHS
REFERENCE = Path("reference/qtable")
COMPARISON = Path("comparison/qtable")

# Change to "linear" if preferred
X_SCALE = "log"


def read_qtable(filename):
    rows = []

    with open(filename) as file:
        for line in file:
            values = line.split()

            if len(values) < 8:
                continue

            try:
                rows.append([float(x) for x in values[:8]])
            except ValueError:
                continue

    return np.array(rows)


reference = read_qtable(REFERENCE)
comparison = read_qtable(COMPARISON)

if len(reference) != len(comparison):
    raise ValueError("The qtables have different numbers of rows.")

wavelength = reference[:, 1]

if not np.allclose(wavelength, comparison[:, 1]):
    raise ValueError("The qtables use different wavelength grids.")

ratio = comparison[:, 3] / reference[:, 3]

plt.figure(figsize=(8, 5.5))
plt.plot(wavelength, ratio)
plt.axhline(1, linestyle="--", linewidth=1)

plt.xscale(X_SCALE)

plt.xlabel(r"Wavelength $\lambda$ [$\mu$m]")
plt.ylabel(r"$Q_{\rm abs}/Q_{\rm abs,ref}$")

plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()
