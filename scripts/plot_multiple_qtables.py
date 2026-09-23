'''
Plot Qabs from several DDSCAT qtable files in one figure.

This is an analysis/example script, not required to run DDSCAT.
Edit the RUNS dictionary and plotting options near the top.
'''

from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt


# ADD OR REMOVE RUNS HERE
RUNS = {
    "reference": Path("reference/qtable"),
    "run 2": Path("run_2/qtable"),
    "run 3": Path("run_3/qtable"),
}

# Change to "linear" if preferred
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


plt.figure(figsize=(8, 5.5))

for label, filename in RUNS.items():
    data = read_qtable(filename)

    plt.plot(
        data[:, 1],
        data[:, 3],
        label=label
    )

plt.xscale(X_SCALE)
plt.yscale(Y_SCALE)

plt.xlabel(r"Wavelength $\lambda$ [$\mu$m]")
plt.ylabel(r"$Q_{\rm abs}$")

plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()
