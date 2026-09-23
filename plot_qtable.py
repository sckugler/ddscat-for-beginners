"""
this file makes a quick overview plot from qtable.

Usually, you only need to change the plotting options marked below
(e.g. linear/log axes). The run directory is read from input.toml.

Run with:

    python3 plot_qtable.py input.toml

For more specialised comparisons, use the scripts in scripts/.
"""

from pathlib import Path
import sys
import tomllib

import numpy as np
import matplotlib.pyplot as plt


if len(sys.argv) != 2:
    raise SystemExit("Usage: python3 plot_qtable.py input.toml")


with open(sys.argv[1], "rb") as file:
    cfg = tomllib.load(file)


run_directory = Path(cfg["paths"]["run_directory"]).expanduser()
qtable = run_directory / "qtable"

# Change these to "linear" if preferred
X_SCALE = "log"
Y_SCALE = "log"


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


data = read_qtable(qtable)

wavelength = data[:, 1]
qext = data[:, 2]
qabs = data[:, 3]
qsca = data[:, 4]

plt.figure(figsize=(8, 5.5))
plt.plot(wavelength, qabs, label="Qabs")
plt.plot(wavelength, qsca, label="Qsca")
plt.plot(wavelength, qext, label="Qext")

plt.xscale(X_SCALE)
plt.yscale(Y_SCALE)

plt.xlabel(r"Wavelength $\lambda$ [$\mu$m]")
plt.ylabel("Efficiency")

plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()

output = run_directory / "qtable_overview.png"
plt.savefig(output, dpi=200) #comment this out if you don't want to save the file
plt.show()

print(f"Saved {output}")
