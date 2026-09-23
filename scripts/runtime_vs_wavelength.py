'''
Read timing information from ddscat.log_000 and plot CPU time vs wavelength.

This is an optional analysis script, not required to run DDSCAT.
Change RUN, IORTH and plot scales near the top if needed.
'''

from pathlib import Path
import re

import numpy as np
import matplotlib.pyplot as plt


# CHANGE THIS TO THE DDSCAT RUN DIRECTORY
RUN = Path(".")

# Must match ddscat.par.
# IORTH = 2 means two orthogonal incident polarizations
IORTH = 2

# Change to "linear" if preferred.
X_SCALE = "log"
Y_SCALE = "log"


def read_wavelengths(filename):
    wavelength = []

    with open(filename) as file:
        for line in file:
            values = line.split()

            if len(values) < 8:
                continue

            try:
                row = [float(x) for x in values[:8]]
            except ValueError:
                continue

            wavelength.append(row[1])

    return np.array(wavelength)


def read_timings(filename):
    solver = []
    scattering = []
    section = None

    with open(filename) as file:

        for line in file:

            if "Timing results for:" in line:

                if "PBCGS2" in line:
                    section = "solver"

                elif "SCAT" in line:
                    section = "scattering"

                else:
                    section = None

                continue

            if "CPU time (sec)" not in line:
                continue

            match = re.search(
                r"([0-9.Ee+-]+)\s*=\s*CPU time",
                line
            )

            if not match:
                continue

            value = float(match.group(1))

            if section == "solver":
                solver.append(value)

            elif section == "scattering":
                scattering.append(value)

    return (
        np.array(solver),
        np.array(scattering)
    )


wavelength = read_wavelengths(
    RUN / "qtable"
)

solver, scattering = read_timings(
    RUN / "ddscat.log_000"
)

expected = len(wavelength) * IORTH

if (
    len(solver) != expected
    or len(scattering) != expected
):
    raise ValueError(
        "Unexpected number of timing entries. "
        "Check IORTH and whether the run finished."
    )

solver = (
    solver
    .reshape(-1, IORTH)
    .sum(axis=1)
)

scattering = (
    scattering
    .reshape(-1, IORTH)
    .sum(axis=1)
)

plt.figure(figsize=(8, 5.5))

plt.plot(
    wavelength,
    solver,
    marker="o",
    markersize=3,
    label="PBCGS2"
)

plt.plot(
    wavelength,
    scattering,
    marker="o",
    markersize=3,
    label="Scattering"
)

plt.xscale(X_SCALE)
plt.yscale(Y_SCALE)

plt.xlabel(r"Wavelength $\lambda$ [$\mu$m]")
plt.ylabel("CPU time [s]")

plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()
