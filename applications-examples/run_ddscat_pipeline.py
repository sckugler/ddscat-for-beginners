#!/usr/bin/env python3

# ----------------------------------------------------------------------------------
# run_ddscat_pipeline.py
#
# All-in-one pipeline:
#
#   1. Submit DDSCAT convergence runs via Slurm
#   2. Read all DDSCAT qtables
#   3. Read the corresponding pre-calculated Mie solution from optool
#   4. Compare DDSCAT and Mie for absorption and scattering
#   5. Calculate absolute and relative RMSE
#   6. Produce convergence plots
#
# Expected run structure:
#
#   runs/
#       a_0.01um/
#           ndip_100/
#           ndip_300/
#           ndip_1000/
#           ...
#       a_0.03um/
#           ndip_100/
#           ...
#       ...
#
# Expected Mie structure:
#
#   /example-data/dust_models_mie/
#       astrosil_0.01um/
#           dustkappa.dat
#       astrosil_0.03um/
#           dustkappa.dat
#       astrosil_0.1um/
#           dustkappa.dat
#       ...
#
# ----------------------------------------------------------------------------------


# ----------------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------------

from pathlib import Path

import argparse
import re
import subprocess
import time
import tomllib

import matplotlib.pyplot as plt
import numpy as np

# ----------------------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------------------

# This needs to be adjusted to the actual ddscat executable directory!
DDSCAT_DIR = Path("~/DDA/src/ddscat")

DDSCAT_INPUT = DDSCAT_DIR / "input.toml"
DDSCAT_MAIN = DDSCAT_DIR / "main.sh"

# ----------------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------------

def load_config(filename):

    with open(filename, "rb") as f:

        return tomllib.load(f)

def parse_arguments():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "config",
        nargs="?",
        default=str(DDSCAT_INPUT),
        help="Path to the TOML configuration file.",
    )

    parser.add_argument(
        "--analysis-only",
        action="store_true",
        help="Do not submit DDSCAT; analyse existing DDSCAT results only.",
    )

    return parser.parse_args()

# ----------------------------------------------------------------------------------
# Run DDSCAT
# ----------------------------------------------------------------------------------

def run_ddscat(config_file):

    print()
    print("============================================================")
    print("Submitting DDSCAT")
    print("============================================================")

    result = subprocess.run(
        [
            "sbatch",
            str(DDSCAT_MAIN),
            str(config_file),
        ],
        cwd=DDSCAT_DIR,
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:

        raise RuntimeError(
            f"Failed to submit DDSCAT:\n"
            f"{result.stderr}"
        )

    job_id = result.stdout.strip().split()[-1]

    print(f"Submitted DDSCAT job {job_id}")
    print("Waiting for DDSCAT to finish...")

    while True:

        check = subprocess.run(
            [
                "squeue",
                "-j",
                job_id,
                "-h",
            ],
            text=True,
            capture_output=True,
        )

        if not check.stdout.strip():
            break

        time.sleep(10)

    result = subprocess.run(
        [
            "sacct",
            "-j",
            job_id,
            "--format=State",
            "--noheader",
        ],
        text=True,
        capture_output=True,
    )

    states = result.stdout.strip().split()

    if not states:

        raise RuntimeError(f"Could not determine Slurm status for job {job_id}")

    # sacct can return several entries, e.g.:
    #
    # COMPLETED
    # COMPLETED
    #
    # The first one is the batch job itself.

    state = states[0]

    if not state.startswith("COMPLETED"):

        raise RuntimeError(f"DDSCAT job {job_id} did not complete successfully: {state}")

    print(f"DDSCAT job {job_id} completed successfully.")

# ----------------------------------------------------------------------------------
# Read one DDSCAT qtable
# ----------------------------------------------------------------------------------

def read_qtable(qtable):

    data_lines = []

    with open(qtable, "r") as f:

        for line in f:

            parts = line.split()

            if len(parts) < 5:
                continue

            try:

                float(parts[0])
                float(parts[1])
                float(parts[2])
                float(parts[3])
                float(parts[4])

                data_lines.append(line)

            except ValueError:

                pass

    if not data_lines:

        raise RuntimeError(f"No numerical data found in {qtable}")

    data = np.loadtxt(data_lines, ndmin=2)

    wavelength = data[:, 1]
    qabs = data[:, 3]
    qsca = data[:, 4]

    return wavelength, qabs, qsca

# ----------------------------------------------------------------------------------
# Read actual number of dipoles from target.out
# ----------------------------------------------------------------------------------

def read_actual_dipoles(target_out):

    if not target_out.exists():
        return None

    with open(target_out, "r", errors="ignore") as f:

        text = f.read()

    # Look for lines containing NAT.
    #
    # Typical DDSCAT output contains information about the number
    # of dipoles in the target.
    #
    # We deliberately accept several possible formats.

    patterns = [
        r"^\s*(\d+)\s*=\s*NAT\b",
        r"\bNAT\s*=\s*(\d+)",
        r"\bNAT\s*[:=]\s*(\d+)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.MULTILINE | re.IGNORECASE,
        )

        if match:

            return int(match.group(1))

    return None

# ----------------------------------------------------------------------------------
# Read all DDSCAT runs
# ----------------------------------------------------------------------------------

def read_all_ddscat(run_base_dir):

    results = {}

    successful_runs = 0
    failed_runs = []

    radius_dirs = sorted(
        run_base_dir.glob("a_*um"),
        key=lambda path: float(
            path.name
            .removeprefix("a_")
            .removesuffix("um")
        ),
    )

    if not radius_dirs:
        raise RuntimeError(f"No radius directories found in {run_base_dir}")

    print()
    print("============================================================")
    print("DDSCAT runs found")
    print("============================================================")

    for radius_dir in radius_dirs:

        radius = float(radius_dir.name.removeprefix("a_").removesuffix("um"))
        ndip_dirs = sorted(radius_dir.glob("ndip_*"), key=lambda path: float(path.name.removeprefix("ndip_")))

        if not ndip_dirs:

            print()
            print(f"WARNING: No dipole runs found for a = {radius:g} um")

            continue

        print()
        print(f"a = {radius:g} um")

        radius_results = {}

        for run_dir in ndip_dirs:

            target_ndip = int(run_dir.name.removeprefix("ndip_"))

            qtable = run_dir / "qtable"
            target_file = run_dir / "target.out"

            # ---------------------------------------------------------
            # Check whether qtable exists
            # ---------------------------------------------------------

            if not qtable.exists():

                print(f"  WARNING: Skipping target = {target_ndip:>7d}: qtable missing")

                failed_runs.append({
                    "radius": radius,
                    "target_ndip": target_ndip,
                    "run_directory": run_dir,
                    "reason": "qtable missing",
                })

                continue

            # ---------------------------------------------------------
            # Try reading qtable
            # ---------------------------------------------------------

            try:

                wavelength, qabs, qsca = read_qtable(qtable)

            except (RuntimeError, ValueError, OSError) as exc:

                print(f"  WARNING: Skipping target = {target_ndip:>7d}: {exc}")

                failed_runs.append({
                    "radius": radius,
                    "target_ndip": target_ndip,
                    "run_directory": run_dir,
                    "reason": str(exc),
                })

                continue

            # ---------------------------------------------------------
            # Try reading actual number of dipoles
            # ---------------------------------------------------------

            actual_ndip = None

            if target_file.exists():

                try:

                    actual_ndip = read_actual_dipoles(target_file)

                except (RuntimeError, ValueError, OSError) as exc:

                    print(f"  WARNING: Could not read actual dipole count for target = {target_ndip}: {exc}")

            else:

                print(f"  WARNING: target.out missing for target = {target_ndip}")

            # ---------------------------------------------------------
            # Store successful run
            # ---------------------------------------------------------

            radius_results[target_ndip] = {
                "wavelength": wavelength,
                "qabs": qabs,
                "qsca": qsca,
                "target_ndip": target_ndip,
                "actual_ndip": actual_ndip,
                "run_directory": run_dir,
            }

            successful_runs += 1

            if actual_ndip is None:

                print(f"  target = {target_ndip:>7d} dipoles (actual NAT not found)")

            else:

                print(f"  target = {target_ndip:>7d} -> actual = {actual_ndip:>7d} dipoles")

        # -------------------------------------------------------------
        # Only add radius if at least one successful run exists
        # -------------------------------------------------------------

        if radius_results:

            results[radius] = radius_results

        else:

            print(f"  WARNING: No successful DDSCAT runs for a = {radius:g} um")

    # -----------------------------------------------------------------
    # Check whether anything could be loaded
    # -----------------------------------------------------------------

    if not results:

        raise RuntimeError("No successful DDSCAT qtables could be read.")

    # -----------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------

    print()
    print("============================================================")
    print("DDSCAT read summary")
    print("============================================================")
    print(f"Successful runs: {successful_runs}")
    print(f"Failed runs:     {len(failed_runs)}")

    if failed_runs:

        print()
        print("Skipped runs:")

        for failed in failed_runs:

            print(f"  a = {failed['radius']:g} um, target = {failed['target_ndip']} dipoles")
            print(f"    Reason: {failed['reason']}")
            print(f"    Run:    {failed['run_directory']}")

    print("============================================================")
    print()

    return results

# ----------------------------------------------------------------------------------
# Find Mie directory
# ----------------------------------------------------------------------------------

def get_mie_directory(mie_base_dir, radius):

    directory = (mie_base_dir / f"astrosil_{radius:g}um")

    return directory

# ----------------------------------------------------------------------------------
# Read Mie / optool result
# ----------------------------------------------------------------------------------

def read_mie(mie_base_dir, radius, rho):

    mie_directory = get_mie_directory(mie_base_dir, radius)

    filename = mie_directory / "dustkappa.dat"

    if not filename.exists():

        raise FileNotFoundError(f"Mie file not found for a = {radius:g} um:\n {filename}")

    data_lines = []

    with open(filename, "r") as f:

        for line in f:

            parts = line.split()

            if len(parts) != 4:
                continue

            try:

                float(parts[0])
                float(parts[1])
                float(parts[2])
                float(parts[3])

                data_lines.append(line)

            except ValueError:

                pass

    if not data_lines:

        raise RuntimeError(f"No numerical data found in {filename}")

    data = np.loadtxt(data_lines, ndmin=2)

    wavelength = data[:, 0]
    kabs = data[:, 1]
    ksca = data[:, 2]

    radius_cm = radius * 1e-4

    qabs = ((4.0 / 3.0) * rho * radius_cm * kabs)
    qsca = ((4.0 / 3.0) * rho * radius_cm * ksca)

    return wavelength, qabs, qsca

# ----------------------------------------------------------------------------------
# Compare DDSCAT against Mie
# ----------------------------------------------------------------------------------

def compare(wavelength_dd, qabs_dd, qsca_dd, wavelength_mie, qabs_mie, qsca_mie):

    # --------------------------------------------------------
    # Only interpolate within the Mie wavelength range
    # --------------------------------------------------------

    valid = ((wavelength_dd >= wavelength_mie.min()) & (wavelength_dd <= wavelength_mie.max()))

    wavelength_dd = wavelength_dd[valid]
    qabs_dd = qabs_dd[valid]
    qsca_dd = qsca_dd[valid]

    if len(wavelength_dd) == 0:

        raise RuntimeError("DDSCAT and Mie wavelength ranges do not overlap.")

    qabs_mie_interp = np.interp(wavelength_dd, wavelength_mie, qabs_mie)
    qsca_mie_interp = np.interp(wavelength_dd, wavelength_mie, qsca_mie)

    # --------------------------------------------------------
    # Relative differences
    #
    # Avoid division by values extremely close to zero.
    # --------------------------------------------------------

    abs_mask = qabs_mie_interp > 0
    sca_mask = qsca_mie_interp > 0

    rel_abs = ((qabs_dd[abs_mask] - qabs_mie_interp[abs_mask]) / qabs_mie_interp[abs_mask])
    rel_sca = ((qsca_dd[sca_mask] - qsca_mie_interp[sca_mask]) / qsca_mie_interp[sca_mask])

    # --------------------------------------------------------
    # Absolute RMSE
    # --------------------------------------------------------

    rmse_abs = np.sqrt(np.mean((qabs_dd - qabs_mie_interp) ** 2))
    rmse_sca = np.sqrt(np.mean((qsca_dd - qsca_mie_interp) ** 2))

    # --------------------------------------------------------
    # Relative RMSE
    # --------------------------------------------------------

    relative_rmse_abs = np.sqrt(np.mean(rel_abs ** 2))
    relative_rmse_sca = np.sqrt(np.mean(rel_sca ** 2))

    return {
        "wavelength": wavelength_dd,
        "qabs_mie": qabs_mie_interp,
        "qsca_mie": qsca_mie_interp,
        "rel_abs": rel_abs,
        "rel_sca": rel_sca,
        "rmse_abs": rmse_abs,
        "rmse_sca": rmse_sca,
        "relative_rmse_abs": relative_rmse_abs,
        "relative_rmse_sca": relative_rmse_sca,
    }

# ----------------------------------------------------------------------------------
# Plot convergence for one grain size
# ----------------------------------------------------------------------------------

def plot_radius(radius, ddscat_results, wavelength_mie, qabs_mie, qsca_mie, output_dir):

    output_dir.mkdir(parents=True, exist_ok=True)

    # ========================================================
    # Absorption
    # ========================================================

    fig, ax = plt.subplots()

    ax.plot(wavelength_mie, qabs_mie, "--", linewidth=2, label="Mie")

    for target_ndip, result in ddscat_results.items():

        actual_ndip = result["actual_ndip"]

        if actual_ndip is None:

            label = f"N = {target_ndip}"

        else:

            label = f"N = {actual_ndip}"

        ax.plot(result["wavelength"], result["qabs"], label=label)

    ax.set_xlabel(r"Wavelength [$\mu$m]")
    ax.set_ylabel(r"$Q_{\rm abs}$")

    ax.set_xscale("log")
    ax.set_yscale("log")

    ax.set_title(rf"DDSCAT convergence: $a={radius:g}\,\mu$m")

    ax.legend()

    fig.tight_layout()

    filename = (output_dir / f"comparison_abs_convergence_{radius:g}um.png")

    fig.savefig(filename, dpi=300,)

    plt.close(fig)

    # ========================================================
    # Scattering
    # ========================================================

    fig, ax = plt.subplots()

    ax.plot(wavelength_mie, qsca_mie, "--", linewidth=2, label="Mie",)

    for target_ndip, result in ddscat_results.items():

        actual_ndip = result["actual_ndip"]

        if actual_ndip is None:

            label = f"N = {target_ndip}"

        else:

            label = f"N = {actual_ndip}"

        ax.plot(result["wavelength"], result["qsca"], label=label)

    ax.set_xlabel(r"Wavelength [$\mu$m]")
    ax.set_ylabel(r"$Q_{\rm sca}$")

    ax.set_xscale("log")
    ax.set_yscale("log")

    ax.set_title(rf"DDSCAT convergence: $a={radius:g}\,\mu$m")

    ax.legend()

    fig.tight_layout()

    filename = (output_dir / f"comparison_sca_convergence_{radius:g}um.png")

    fig.savefig(filename, dpi=300)

    plt.close(fig)

# ----------------------------------------------------------------------------------
# Plot RMSE versus dipole number
# ----------------------------------------------------------------------------------

def plot_rmse_vs_dipoles(all_statistics, output_dir):

    output_dir.mkdir(parents=True, exist_ok=True)

    # ========================================================
    # Absorption
    # ========================================================

    fig, ax = plt.subplots()

    for radius, statistics in all_statistics.items():

        ndip = []
        rmse = []

        for target_ndip, result in statistics.items():

            actual_ndip = result["actual_ndip"]

            if actual_ndip is None:

                actual_ndip = target_ndip

            ndip.append(actual_ndip)
            rmse.append(result["relative_rmse_abs"])

        order = np.argsort(ndip)

        ax.plot(np.array(ndip)[order], np.array(rmse)[order], marker="o", label=rf"$a={radius:g}\,\mu$m")

    ax.axhline(0.05, linestyle="--", linewidth=1.5, label="5% threshold")
    ax.axhline(0.01, linestyle=":", linewidth=1.5, label="1% threshold")

    ax.set_xlabel("Number of DDSCAT dipoles")
    ax.set_ylabel("Relative RMSE")

    ax.set_xscale("log")
    ax.set_yscale("log")

    ax.legend()

    fig.tight_layout()

    fig.savefig(output_dir / "convergence_relative_rmse_absorption.png", dpi=300)

    plt.close(fig)

    # ========================================================
    # Scattering
    # ========================================================

    fig, ax = plt.subplots()

    for radius, statistics in all_statistics.items():

        ndip = []
        rmse = []

        for target_ndip, result in statistics.items():

            actual_ndip = result["actual_ndip"]

            if actual_ndip is None:

                actual_ndip = target_ndip

            ndip.append(actual_ndip)
            rmse.append(result["relative_rmse_sca"])

        order = np.argsort(ndip)

        ax.plot(np.array(ndip)[order], np.array(rmse)[order], marker="o", label=rf"$a={radius:g}\,\mu$m")

    ax.axhline(0.05, linestyle="--", linewidth=1.5, label="5% threshold")
    ax.axhline(0.01, linestyle=":", linewidth=1.5, label="1% threshold")

    ax.set_xlabel("Number of DDSCAT dipoles")
    ax.set_ylabel("Relative RMSE")

    ax.set_xscale("log")
    ax.set_yscale("log")

    ax.legend()

    fig.tight_layout()

    fig.savefig(output_dir / "convergence_relative_rmse_scattering.png", dpi=300)

    plt.close(fig)

# ----------------------------------------------------------------------------------
# Print statistics
# ----------------------------------------------------------------------------------

def print_comparison_statistics(all_statistics):

    print()
    print(
        "================================================================================"
    )
    print(
        "DDSCAT vs Mie convergence"
    )
    print(
        "================================================================================"
    )

    for radius, statistics in all_statistics.items():

        print()
        print(
            f"Grain radius: {radius:g} um"
        )

        print(
            "--------------------------------------------------------------------------------"
        )

        print(
            f"{'Target N':>10} "
            f"{'Actual N':>12} "
            f"{'Abs RMSE':>14} "
            f"{'Abs rel.RMSE':>16} "
            f"{'Sca RMSE':>14} "
            f"{'Sca rel.RMSE':>16}"
        )

        print(
            "--------------------------------------------------------------------------------"
        )

        for target_ndip, result in statistics.items():

            actual_ndip = result["actual_ndip"]

            if actual_ndip is None:

                actual_string = "?"

            else:

                actual_string = str(
                    actual_ndip
                )

            print(
                f"{target_ndip:>10d} "
                f"{actual_string:>12} "
                f"{result['rmse_abs']:>14.4e} "
                f"{result['relative_rmse_abs']:>16.4e} "
                f"{result['rmse_sca']:>14.4e} "
                f"{result['relative_rmse_sca']:>16.4e}"
            )

    print()
    print(
        "================================================================================"
    )

# ----------------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------------

def main():

    args = parse_arguments()

    # --------------------------------------------------------
    # Load configuration
    # --------------------------------------------------------

    config_file = Path(args.config).expanduser().resolve()
    config = load_config(config_file)

    run_base_dir = (Path(config["paths"]["run_directory"]).expanduser().resolve())
    mie_base_dir = (Path(config["paths"]["mie_directory"]).expanduser().resolve())
    output_dir = (Path(config["paths"]["plot_directory"]).expanduser().resolve())

    rho = config.get("material", {}).get("density_g_cm3", 2.71)

    # --------------------------------------------------------
    # Run DDSCAT
    # --------------------------------------------------------

    if not args.analysis_only:

        run_ddscat(config_file)

    # --------------------------------------------------------
    # Read DDSCAT results
    # --------------------------------------------------------

    ddscat_results = read_all_ddscat(run_base_dir)

    # --------------------------------------------------------
    # Read Mie and compare for every grain size
    # --------------------------------------------------------

    all_statistics = {}

    for radius, radius_results in ddscat_results.items():

        print()
        print("------------------------------------------------------------")
        print(f"Reading Mie reference for a = {radius:g} um")

        wavelength_mie, qabs_mie, qsca_mie = read_mie(mie_base_dir, radius, rho)

        statistics = {}

        for target_ndip, result in radius_results.items():

            statistics[target_ndip] = compare(
                result["wavelength"],
                result["qabs"],
                result["qsca"],
                wavelength_mie,
                qabs_mie,
                qsca_mie)

            statistics[target_ndip]["actual_ndip"] = result["actual_ndip"]

        all_statistics[radius] = statistics

        # ----------------------------------------------------
        # Individual convergence plots for this radius
        # ----------------------------------------------------

        plot_radius(radius, radius_results, wavelength_mie, qabs_mie, qsca_mie, output_dir)

    # --------------------------------------------------------
    # Print statistics
    # --------------------------------------------------------

    print_comparison_statistics(all_statistics)

    # --------------------------------------------------------
    # Global convergence plots
    # --------------------------------------------------------

    plot_rmse_vs_dipoles(all_statistics, output_dir)

    print()
    print("Plots written to:")
    print(f"  {output_dir}")
    print()

# ----------------------------------------------------------------------------------

if __name__ == "__main__":

    main()

# ----------------------------------------------------------------------------------