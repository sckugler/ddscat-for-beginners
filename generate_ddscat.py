#!/usr/bin/env python3

from pathlib import Path
import shutil
import sys
import tomllib


def load_config(filename):
    with open(filename, "rb") as file:
        return tomllib.load(file)


def copy_input_file(source, destination):
    source = Path(source).expanduser()
    destination = Path(destination).expanduser()

    if not source.exists():
        raise FileNotFoundError(f"input file not found: {source}")

    destination.parent.mkdir(parents=True, exist_ok=True)

    if source.resolve() != destination.resolve():
        shutil.copy2(source, destination)


def validate_spacing(value, name):
    value = value.upper()
    allowed = {"LIN", "LOG", "INV"}

    if value not in allowed:
        raise ValueError(
            f"{name} spacing must be one of {sorted(allowed)}, got {value!r}"
        )

    return value


def triplet(values, name):
    if len(values) != 3:
        raise ValueError(f"{name} must contain exactly three values")
    return values


def build_parameter_file(config):
    paths = config["paths"]
    target = config["target"]
    radius = config["effective_radius"]
    wavelength = config["wavelength"]
    numerics = config["numerics"]
    orientation = config["orientation"]
    output = config["output"]
    scattering = config["scattering"]

    shape = target["shape"].upper()
    wavelength_spacing = validate_spacing(wavelength["spacing"], "wavelength")
    radius_spacing = validate_spacing(radius["spacing"], "effective radius")

    memory = triplet(numerics["memory"], "memory")
    beta = triplet(orientation["beta"], "beta")
    theta = triplet(orientation["theta"], "theta")
    phi = triplet(orientation["phi"], "phi")

    if wavelength["count"] < 1:
        raise ValueError("wavelength count must be at least 1")

    if radius["count"] < 1:
        raise ValueError("effective-radius count must be at least 1")

    lines = [
        "' ========== Parameter file for DDSCAT 7.3 =========='",
        "'**** Preliminaries ****'",
        "'NOTORQ' = CMDTRQ",
        f"'{numerics['solver'].upper()}' = CMDSOL",
        f"'{numerics['fft'].upper()}' = CMDFFT",
        f"'{numerics['polarizability'].upper()}' = CALPHA",
        "'NOTBIN' = CBINFLAG",
        "'**** Initial Memory Allocation ****'",
        f"{int(memory[0])} {int(memory[1])} {int(memory[2])}",
        "'**** Target Geometry and Composition ****'",
        f"'{shape}' = CSHAPE",
    ]

    if shape == "FROM_FILE":
        shape_file = target.get("shape_file")
        if not shape_file:
            raise ValueError("target.shape_file is required when shape = FROM_FILE")
        lines.append("no SHPAR parameters needed")
    elif shape == "ELLIPSOID":
        parameters = target.get("shape_parameters")
        if parameters is None or len(parameters) != 3:
            raise ValueError(
                "target.shape_parameters must contain three values for ELLIPSOID"
            )
        lines.append(" ".join(str(value) for value in parameters))
    else:
        raise ValueError(
            "this helper supports FROM_FILE and ELLIPSOID targets; "
            "other DDSCAT target types can be added to generate_ddscat.py"
        )

    nearfield = 1 if numerics.get("nearfield", False) else 0
    mueller = output["mueller_elements"]
    planes = scattering["planes"]

    lines.extend(
        [
            "1 = NCOMP",
            "'diel.dat'",
            "'**** Additional Nearfield calculation? ****'",
            f"{nearfield} = NRFLD",
            "0.0 0.0 0.0 0.0 0.0 0.0",
            "'**** Error Tolerance ****'",
            f"{numerics['tolerance']:.8g} = TOL",
            "'**** Maximum number of iterations ****'",
            f"{int(numerics['max_iterations'])} = MXITER",
            "'**** Interaction cutoff parameter ****'",
            f"{numerics['gamma']:.8g} = GAMMA",
            "'**** Angular resolution ****'",
            f"{numerics['eta_sca']:.8g} = ETASCA",
            "'**** Vacuum wavelengths (micron) ****'",
            (
                f"{wavelength['minimum_um']} {wavelength['maximum_um']} "
                f"{int(wavelength['count'])} '{wavelength_spacing}'"
            ),
            "'**** Refractive index of ambient medium ****'",
            f"{numerics['ambient_refractive_index']} = NAMBIENT",
            "'**** Effective Radii (micron) ****'",
            (
                f"{radius['minimum_um']} {radius['maximum_um']} "
                f"{int(radius['count'])} '{radius_spacing}'"
            ),
            "'**** Define Incident Polarizations ****'",
            "(0,0) (1.,0.) (0.,0.)",
            f"{int(output['iorth'])} = IORTH",
            "'**** Specify which output files to write ****'",
            f"{int(output['write_sca'])} = IWRKSC",
            "'**** Prescribe Target Rotations ****'",
            f"{beta[0]} {beta[1]} {int(beta[2])} = BETAMI BETAMX NBETA",
            f"{theta[0]} {theta[1]} {int(theta[2])} = THETMI THETMX NTHETA",
            f"{phi[0]} {phi[1]} {int(phi[2])} = PHIMIN PHIMAX NPHI",
            "'**** Specify first IWAV, IRAD, IORI ****'",
            "0 0 0",
            "'**** Select Elements of S_ij Matrix to Print ****'",
            f"{len(mueller)} = NSMELTS",
            " ".join(str(int(value)) for value in mueller),
            "'**** Specify Scattered Directions ****'",
            f"'{scattering['frame'].upper()}'",
            str(len(planes)),
        ]
    )

    for plane in planes:
        if len(plane) != 4:
            raise ValueError("each scattering plane must contain four values")
        lines.append(" ".join(str(value) for value in plane))

    return "\n".join(lines) + "\n"


def prepare_run(config_filename):
    config = load_config(config_filename)
    paths = config["paths"]

    run_directory = Path(paths["run_directory"]).expanduser()
    run_directory.mkdir(parents=True, exist_ok=True)

    copy_input_file(
        paths["material_file"],
        run_directory / "diel.dat",
    )

    shape = config["target"]["shape"].upper()
    if shape == "FROM_FILE":
        copy_input_file(
            config["target"]["shape_file"],
            run_directory / "shape.dat",
        )

    parameter_text = build_parameter_file(config)
    parameter_file = run_directory / "ddscat.par"
    parameter_file.write_text(parameter_text)

    executable = Path(paths["ddscat_executable"]).expanduser()
    if not executable.exists():
        raise FileNotFoundError(f"DDSCAT executable not found: {executable}")

    print(f"run directory: {run_directory}")
    print(f"parameter file: {parameter_file}")
    print(f"material copied to: {run_directory / 'diel.dat'}")

    if shape == "FROM_FILE":
        print(f"shape copied to: {run_directory / 'shape.dat'}")


if __name__ == "__main__":
    config_filename = sys.argv[1] if len(sys.argv) > 1 else "input.toml"
    prepare_run(config_filename)
