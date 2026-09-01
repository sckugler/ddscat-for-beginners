#!/usr/bin/env python3

from pathlib import Path
import re
import sys
import tomllib

import matplotlib.pyplot as plt
import numpy as np


data_pattern = re.compile(
    r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)[Ee][+-]?\d+$"
)


def load_config(filename):
    with open(filename, "rb") as file:
        return tomllib.load(file)


def read_qtable(filename):
    rows = []

    with open(filename) as file:
        for line in file:
            values = line.split()

            if len(values) < 8:
                continue

            if not (
                data_pattern.match(values[0])
                and data_pattern.match(values[1])
            ):
                continue

            rows.append([float(value) for value in values[:8]])

    if not rows:
        raise ValueError(f"no DDSCAT data rows found in {filename}")

    return np.array(rows)


def main(config_filename):
    config = load_config(config_filename)
    run_directory = Path(config["paths"]["run_directory"]).expanduser()

    data = read_qtable(run_directory / "qtable")

    wavelength = data[:, 1]
    qext = data[:, 2]
    qabs = data[:, 3]
    qsca = data[:, 4]

    order = np.argsort(wavelength)
    wavelength = wavelength[order]
    qext = qext[order]
    qabs = qabs[order]
    qsca = qsca[order]

    plt.figure(figsize=(8, 5.5))
    plt.plot(wavelength, qabs, label=r"$Q_{\rm abs}$")
    plt.plot(wavelength, qsca, label=r"$Q_{\rm sca}$")
    plt.plot(wavelength, qext, label=r"$Q_{\rm ext}$")

    plt.xscale("log")
    plt.yscale("log")
    plt.xlabel(r"Wavelength $\lambda$ [$\mu$m]")
    plt.ylabel("Efficiency")
    plt.title("DDSCAT efficiencies")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()

    output_file = run_directory / "qtable_overview.png"
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"saved: {output_file}")


if __name__ == "__main__":
    config_filename = sys.argv[1] if len(sys.argv) > 1 else "input.toml"
    main(config_filename)
