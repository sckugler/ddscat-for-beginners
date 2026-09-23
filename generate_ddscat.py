from pathlib import Path
import shutil
import sys
import tomllib


if len(sys.argv) != 2:
    raise SystemExit("Usage: python3 generate_ddscat.py input.toml")


config_file = Path(sys.argv[1])

with open(config_file, "rb") as file:
    cfg = tomllib.load(file)


paths = cfg["paths"]
target = cfg["target"]
wavelength = cfg["wavelength"]
radius = cfg["effective_radius"]
numerics = cfg["numerics"]
polarization = cfg["polarization"]

run_directory = Path(paths["run_directory"]).expanduser()
run_directory.mkdir(parents=True, exist_ok=True)

# Copy material into the run directory
material_source = Path(paths["material_file"]).expanduser()
shutil.copy2(material_source, run_directory / "diel.dat")

shape = target["shape"].upper()

if shape == "FROM_FILE":
    # Custom target: copy the supplied shape.dat.
    shape_source = Path(target["shape_file"]).expanduser()
    shutil.copy2(shape_source, run_directory / "shape.dat")
    shape_block = "'FROM_FILE' = CSHAPE\n"

elif shape == "ELLIPSOID":
'''
for ELLIPSOID, these values are the particle dimensions measured in units of the dipole spacing d.
d = distance between neighbouring dipoles on the DDSCAT lattice
D = physical diameter of the particle along that axis
Therefore D/d tells us approximately how many dipole spacings
fit across the particle diameter.
in this example I use [70, 70, 70] -> sphere with D/d ≈ 70 in x, y and z
A larger D/d means more dipoles and a finer numerical resolution.
It does NOT mean that the particle is 70 um large!
The physical size is set separately by the effective radius later
'''
shape_parameters = [70.0, 70.0, 70.0]
    sx, sy, sz = target["shape_parameters"]
    shape_block = (
        "'ELLIPSOID' = CSHAPE\n"
        f"{sx} {sy} {sz}\n"
    )

else:
    raise ValueError(f"Unsupported target shape: {shape}")


text = f"""'========== Parameter file for DDSCAT 7.3 =========='

'**** Preliminaries ****'
'NOTORQ' = CMDTRQ
'{numerics["solver"]}' = CMDSOL
'{numerics["fft"]}' = CMDFFT
'{numerics["polarizability"]}' = CALPHA
'NOTBIN' = CBINFLAG

'**** Initial Memory Allocation ****'
100 100 100

'**** Target Geometry and Composition ****'
{shape_block}1 = NCOMP
'diel.dat'

'**** Additional Nearfield calculation? ****'
0 = NRFLD
0.0 0.0 0.0 0.0 0.0 0.0

'**** Error Tolerance ****'
{numerics["tolerance"]} = TOL

'**** Maximum number of iterations ****'
{numerics["max_iterations"]} = MXITER

'**** Interaction cutoff parameter ****'
{numerics["gamma"]} = GAMMA

'**** Angular resolution ****'
{numerics["etasca"]} = ETASCA

'**** Vacuum wavelengths (micron) ****'
{wavelength["minimum_um"]} {wavelength["maximum_um"]} {wavelength["count"]} '{wavelength["spacing"]}'

'**** Refractive index of ambient medium ****'
1.0 = NAMBIENT

'**** Effective Radii (micron) ****'
{radius["minimum_um"]} {radius["maximum_um"]} {radius["count"]} '{radius["spacing"]}'

'**** Define Incident Polarizations ****'
(0,0) (1.,0.) (0.,0.)
{polarization["iorth"]} = IORTH

'**** Specify which output files to write ****'
0 = IWRKSC

'**** Prescribe Target Rotations ****'
0.0 0.0 1 = BETAMI BETAMX NBETA
0.0 0.0 1 = THETMI THETMX NTHETA
0.0 0.0 1 = PHIMIN PHIMAX NPHI

'**** Specify first IWAV, IRAD, IORI ****'
0 0 0

'**** Select Elements of S_ij Matrix to Print ****'
6 = NSMELTS
11 12 21 22 31 41

'**** Specify Scattered Directions ****'
'LFRAME'
1
0.0 0.0 180.0 5.0
"""

output = run_directory / "ddscat.par"
output.write_text(text)

print(f"Wrote {output}")
