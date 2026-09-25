#!/usr/bin/env python3

# =============================================================================
# generate_ddscat.py
#
# Generate a DDSCAT convergence grid:
#
#     grain radius x target dipole number
#
# For spherical ELLIPSOID targets, the target dipole number is converted into
# a DDSCAT shape resolution N, where N is approximately the number of lattice
# spacings across the grain diameter.
#
# The actual number of dipoles is determined by DDSCAT and later read from
# target.out.
# =============================================================================

from pathlib import Path
import shutil
import sys
import tomllib
import math

# =============================================================================
# Configuration
# =============================================================================

def load_config(filename):

    with open(filename, "rb") as file:
        return tomllib.load(file)

# =============================================================================
# Helpers
# =============================================================================

def copy_input_file(source, destination):

    source = Path(source).expanduser()
    destination = Path(destination).expanduser()

    if not source.exists():
        raise FileNotFoundError(f"Input file not found: {source}")

    destination.parent.mkdir(parents=True, exist_ok=True)

    if source.resolve() != destination.resolve():
        shutil.copy2(source, destination)


def validate_spacing(value, name):

    value = value.upper()

    allowed = {"LIN", "LOG", "INV"}

    if value not in allowed:
        raise ValueError(f"{name} spacing must be one of {sorted(allowed)}, got {value!r}")

    return value


def triplet(values, name):

    if len(values) != 3: 
        raise ValueError(f"{name} must contain exactly three values")

    return values

# =============================================================================
# Convert target dipoles to DDSCAT shape resolution
# =============================================================================

def dipoles_to_resolution(target_dipoles):

    """
    Convert an approximate desired number of dipoles into the DDSCAT
    ELLIPSOID resolution.

    For a spherical target:

        N_dip ~ pi/6 * resolution^3

    Therefore:

        resolution ~ (6*N_dip/pi)^(1/3)

    The result is rounded to the nearest integer.
    """

    if target_dipoles <= 0:
        raise ValueError(f"Target dipole number must be positive, got {target_dipoles}")

    resolution = (6.0 * target_dipoles / math.pi) ** (1.0 / 3.0)
    resolution = max(1, int(round(resolution)))

    return resolution


def approximate_dipoles(resolution):

    """
    Geometrical estimate for the number of occupied lattice sites
    in a spherical target.
    """

    return (math.pi / 6.0* resolution**3)


# =============================================================================
# Build ddscat.par
# =============================================================================

def build_parameter_file(config, shape_parameters, radius_um,):

    paths = config["paths"]
    target = config["target"]
    wavelength = config["wavelength"]
    numerics = config["numerics"]
    orientation = config["orientation"]
    output = config["output"]
    scattering = config["scattering"]

    shape = target["shape"].upper()

    wavelength_spacing = validate_spacing(wavelength["spacing"], "wavelength")

    memory = triplet(numerics["memory"], "memory")
    beta = triplet(orientation["beta"], "beta")
    theta = triplet(orientation["theta"], "theta")

    phi = triplet(orientation["phi"], "phi")

    if wavelength["count"] < 1:
        raise ValueError("wavelength count must be at least 1")

    if shape != "ELLIPSOID":
        raise ValueError("This convergence pipeline currently supports ELLIPSOID targets only.")

    lines = [

        "' ========== Parameter file for DDSCAT 7.3 =========='",

        "'**** Preliminaries ****'",
        "'NOTORQ' = CMDTRQ",
        f"'{numerics['solver'].upper()}' = CMDSOL",
        f"'{numerics['fft'].upper()}' = CMDFFT",
        f"'{numerics['polarizability'].upper()}' = CALPHA",
        "'NOTBIN' = CBINFLAG",

        "'**** Initial Memory Allocation ****'",
        f"{int(memory[0])} "
        f"{int(memory[1])} "
        f"{int(memory[2])}",

        "'**** Target Geometry and Composition ****'",
        "'ELLIPSOID' = CSHAPE",

        " ".join(
            str(value)
            for value in shape_parameters
        ),

        "1 = NCOMP",
        "'diel.dat'",

        "'**** Additional Nearfield calculation? ****'",
        f"{1 if numerics.get('nearfield', False) else 0} = NRFLD",
        "0.0 0.0 0.0 0.0 0.0 0.0",

        "'**** Error Tolerance ****'",
        f"{numerics['tolerance']:.8g} = TOL",

        "'**** Maximum number of solver iterations ****'",
        f"{int(numerics['max_iterations'])} = MXITER",

        "'**** Interaction cutoff parameter ****'",
        f"{numerics['gamma']:.8g} = GAMMA",

        "'**** Angular resolution ****'",
        f"{numerics['eta_sca']:.8g} = ETASCA",

        "'**** Vacuum wavelengths (micron) ****'",
        (
            f"{wavelength['minimum_um']} "
            f"{wavelength['maximum_um']} "
            f"{int(wavelength['count'])} "
            f"'{wavelength_spacing}'"
        ),

        "'**** Refractive index of ambient medium ****'",
        f"{numerics['ambient_refractive_index']} = NAMBIENT",

        "'**** Effective Radii (micron) ****'",
        (
            f"{radius_um} "
            f"{radius_um} "
            f"1 "
            "'LIN'"
        ),

        "'**** Define Incident Polarizations ****'",
        "(0,0) (1.,0.) (0.,0.)",
        f"{int(output['iorth'])} = IORTH",

        "'**** Specify which output files to write ****'",
        f"{int(output['write_sca'])} = IWRKSC",

        "'**** Prescribe Target Rotations ****'",
        (
            f"{beta[0]} {beta[1]} {int(beta[2])} "
            "= BETAMI BETAMX NBETA"
        ),

        (
            f"{theta[0]} {theta[1]} {int(theta[2])} "
            "= THETMI THETMX NTHETA"
        ),

        (
            f"{phi[0]} {phi[1]} {int(phi[2])} "
            "= PHIMIN PHIMAX NPHI"
        ),

        "'**** Specify first IWAV, IRAD, IORI ****'",
        "0 0 0",

        "'**** Select Elements of S_ij Matrix to Print ****'",
        f"{len(output['mueller_elements'])} = NSMELTS",

        " ".join(
            str(int(value))
            for value in output["mueller_elements"]
        ),

        "'**** Specify Scattered Directions ****'",
        f"'{scattering['frame'].upper()}'",
        str(len(scattering["planes"])),
    ]

    for plane in scattering["planes"]:

        if len(plane) != 4:
            raise ValueError("Each scattering plane must contain four values")

        lines.append(" ".join(str(value) for value in plane))

    return "\n".join(lines) + "\n"

# =============================================================================
# Main preparation
# =============================================================================

def prepare_runs(config_filename):

    config = load_config(config_filename)

    paths = config["paths"]
    target = config["target"]

    base_run_directory = (Path(paths["run_directory"]).expanduser().resolve())
    executable = (Path(paths["ddscat_executable"]).expanduser().resolve())

    if not executable.exists():
        raise FileNotFoundError(f"DDSCAT executable not found: {executable}")

    if target["shape"].upper() != "ELLIPSOID":
        raise ValueError("The convergence generator currently supports ELLIPSOID targets only.")

    radii = target["radii_um"]
    target_dipoles = target["target_dipoles"]

    if not radii:
        raise ValueError("target.radii_um must not be empty")

    if not target_dipoles:
        raise ValueError("target.target_dipoles must not be empty")

    for radius in radii:

        if radius <= 0:
            raise ValueError(f"Grain radius must be positive: {radius}")

    for ndip in target_dipoles:

        if ndip <= 0:
            raise ValueError(f"Target dipole number must be positive: {ndip}")

    # -------------------------------------------------------------------------
    # Generate resolution mapping
    # -------------------------------------------------------------------------

    resolution_mapping = {}

    for ndip in target_dipoles:

        resolution = dipoles_to_resolution(ndip)
        resolution_mapping[ndip] = resolution

    # -------------------------------------------------------------------------
    # Print summary
    # -------------------------------------------------------------------------

    print()
    print("=" * 70)
    print("DDSCAT convergence-run preparation")
    print("=" * 70)

    print(f"Base directory : {base_run_directory}")
    print(f"DDSCAT         : {executable}")

    print(
        "Radii [um]     : "
        + ", ".join(
            f"{radius:g}"
            for radius in radii
        )
    )

    print()
    print(
        f"{'Target N_dip':>15} "
        f"{'Resolution':>15} "
        f"{'Estimated N_dip':>20}"
    )

    print("-" * 55)

    for ndip in target_dipoles:

        resolution = resolution_mapping[ndip]

        estimated = approximate_dipoles(resolution)

        print(
            f"{ndip:>15g} "
            f"{resolution:>15d} "
            f"{estimated:>20.0f}"
        )

    print("=" * 70)
    print()

    # -------------------------------------------------------------------------
    # Generate one run for every radius × dipole resolution
    # -------------------------------------------------------------------------

    run_count = 0

    for radius in radii:

        for ndip in target_dipoles:

            resolution = resolution_mapping[ndip]

            estimated_ndip = approximate_dipoles(
                resolution
            )

            run_directory = (
                base_run_directory
                / f"a_{radius:g}um"
                / f"ndip_{ndip:g}"
            )

            run_directory.mkdir(
                parents=True,
                exist_ok=True
            )

            # -------------------------------------------------------------
            # Material
            # -------------------------------------------------------------

            copy_input_file(
                paths["material_file"],
                run_directory / "diel.dat"
            )

            # -------------------------------------------------------------
            # DDSCAT geometry
            #
            # For a sphere:
            #
            #     shape = [N, N, N]
            #
            # and the effective radius is set separately in ddscat.par.
            # -------------------------------------------------------------

            shape_parameters = [
                float(resolution),
                float(resolution),
                float(resolution),
            ]

            # -------------------------------------------------------------
            # Parameter file
            # -------------------------------------------------------------

            parameter_text = build_parameter_file(config, shape_parameters, radius)
            parameter_file = (run_directory / "ddscat.par")
            parameter_file.write_text(parameter_text)

            # -------------------------------------------------------------
            # Metadata
            # -------------------------------------------------------------

            metadata = (
                f"radius_um = {radius}\n"
                f"target_dipoles = {ndip}\n"
                f"shape_resolution = {resolution}\n"
                f"estimated_dipoles = {estimated_ndip:.0f}\n"
            )

            (
                run_directory / "run_info.txt"
            ).write_text(metadata)

            # -------------------------------------------------------------
            # Print
            # -------------------------------------------------------------

            print(
                f"Created: "
                f"a={radius:g} um, "
                f"target N={ndip:g}, "
                f"resolution={resolution}, "
                f"estimated N={estimated_ndip:.0f}"
            )

            run_count += 1

    print()
    print("=" * 70)
    print(
        f"Prepared {run_count} DDSCAT runs."
    )
    print("=" * 70)
    print()

# =============================================================================
# Entry point
# =============================================================================

if __name__ == "__main__":

    config_filename = (sys.argv[1] if len(sys.argv) > 1 else "input.toml")
    prepare_runs(config_filename)