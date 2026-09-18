# DDSCAT for Beginners

A small collection of notes and Python scripts for setting up, running, and
analysing DDSCAT calculations.

This repository was created during a summer internship at
Christian-Albrechts-Universität zu Kiel and is intended as a practical
starting point for users who are new to DDSCAT.

> **Code note:** Some of the Python and shell code in this repository was
> developed with assistance from large language models, including ChatGPT
> (OpenAI). The scripts were reviewed, modified, and tested on the calculations
> used during this project. Paths and numerical parameters should still be
> checked before using them for a new setup.

## Documentation

A more detailed introduction is available here:

**[Running DDSCAT — A Beginner's Guide (PDF)](docs/ddscat_for_beginners.pdf)**

The manual explains the main DDSCAT input files, `ddscat.par`, material files,
custom `shape.dat` targets, important output files, convergence checks, and a
complete example calculation.

## Installing DDSCAT

DDSCAT itself is not included in this repository.

Download DDSCAT 7.3.4 from the official DDSCAT download page:

**https://ddscat.wikidot.com/downloads**

Download both:

1. **DDSCAT 7.3.4 FORTRAN code**
2. **DDSCAT 7.3.4 Examples**

The example package is needed for the `examples_exp` directory used throughout
this repository. If it is not already included in your DDSCAT directory,
download the examples separately and place `examples_exp` next to `src`.

A convenient directory structure is:

```text
DDA/
├── src/
│   └── ddscat
├── examples_exp/
├── diel/
└── doc/
```

The exact location does not matter, but the paths in `input.toml` must be
changed accordingly.

### Compile DDSCAT

DDSCAT is written in Fortran. On Linux, `gfortran` can be used.

```bash
gfortran --version
```

Compile DDSCAT from the source directory:

```bash
cd ~/DDA/src
make ddscat
```

The resulting executable should be located at something like:

```text
~/DDA/src/ddscat
```

Check that it exists with:

```bash
ls -l ~/DDA/src/ddscat
```

## Python requirements

The helper scripts use Python 3. Some analysis scripts additionally require
NumPy, Matplotlib, and SciPy.

```bash
python3 -m pip install numpy matplotlib scipy
```

The automated workflow uses Python 3.11 or newer.

---

# DDSCAT run workflow

This repository is meant to help users get familiar with DDSCAT without
having to understand the Fortran source code itself.

The main workflow is:

```text
input.toml
    ↓
generate_ddscat.py
    ↓
ddscat.par
    ↓
main.sh
    ↓
DDSCAT
    ↓
qtable / .avg / .sca / log files
```

The user normally only edits `input.toml`. The Python helper then generates
`ddscat.par`, and `main.sh` starts DDSCAT.

For background information on the individual DDSCAT parameters, see the
accompanying manual and the official DDSCAT User Guide.

## Files in this repository

```text
.
├── README.md
├── input.toml
├── generate_ddscat.py
├── main.sh
├── check_run.py
├── plot_qtable.py
├── main.txt
├── docs/
│   └── ddscat_for_beginners.pdf
└── scripts/
    ├── compare_qtables.py
    ├── generate_porous_sphere.py
    ├── plot_multiple_qtables.py
    ├── plot_shape_slice.py
    ├── runtime_vs_ice_fraction.py
    ├── runtime_vs_oblateness.py
    ├── runtime_vs_porosity.py
    └── runtime_vs_wavelength.py
```

The workflow uses one user-editable input file:

- `input.toml` — paths, target, wavelength grid, effective radius and numerical settings

The main scripts are:

- `generate_ddscat.py` — creates the run directory and `ddscat.par`
- `main.sh` — prepares the input files and runs DDSCAT; it can also be submitted with Slurm
- `check_run.py` — checks how many wavelength/radius combinations finished and inspects the DDSCAT log
- `plot_qtable.py` — makes a first overview plot from `qtable`

The additional scripts in `scripts/` are small examples used during the
project. They can be adapted for other targets and directory structures.

---

## Before running

DDSCAT must already be compiled.

Set the path to the executable in `input.toml`:

```toml
ddscat_executable = "/star/home/USER/DDA/src/ddscat"
```

A material file is always required:

```toml
material_file = "/star/home/USER/DDA/diel/astrosil"
```

For a custom target using `FROM_FILE`, a geometry file is also required:

```toml
shape = "FROM_FILE"
shape_file = "/star/data/USER/DDSCAT/shapes/shape.dat"
```

The helper copies the material into the run directory as `diel.dat` and the
custom geometry as `shape.dat`. `ddscat.par` therefore contains short local
file names. This also avoids problems with long material paths in DDSCAT.

For a built-in ellipsoid target, use:

```toml
shape = "ELLIPSOID"
shape_parameters = [70.0, 70.0, 70.0]
```

Equal values give a sphere. The shape parameters are passed directly to
DDSCAT as `SHPAR1`, `SHPAR2`, and `SHPAR3`; consult the DDSCAT manual before
changing them.

---

## 1. Edit `input.toml`

The most commonly changed entries are:

```toml
[paths]

# Change these paths for your system.
ddscat_executable = "/star/home/USER/DDA/src/ddscat"
run_directory = "/star/data/USER/DDSCAT/example_run"
material_file = "/star/home/USER/DDA/diel/astrosil"

[target]

# Use "FROM_FILE" for a custom shape.dat target.
# Use "ELLIPSOID" for a built-in ellipsoid/sphere.
shape = "FROM_FILE"

# Only needed for FROM_FILE.
shape_file = "/star/data/USER/DDSCAT/shapes/shape.dat"

[effective_radius]

# Grain radius/radius range in micrometres.
minimum_um = 1.0
maximum_um = 1.0
count = 1

# LIN = linear spacing
# LOG = logarithmic spacing
# INV = inverse spacing
spacing = "LIN"

[wavelength]

# Wavelength range in micrometres.
minimum_um = 0.3
maximum_um = 100.0
count = 60

# LOG is useful for wavelength ranges spanning several orders of magnitude.
# Change to LIN for equally spaced wavelengths.
spacing = "LOG"
```

`LIN`, `LOG`, and `INV` are accepted for the wavelength and effective-radius
grids.

The numerical settings normally do not need to be changed for a first run:

```toml
[numerics]

# Iterative solver convergence tolerance.
tolerance = 1.0e-5

# Maximum number of solver iterations.
max_iterations = 1000

solver = "PBCGS2"
fft = "GPFAFT"
polarizability = "GKDLDR"
```

---

## 2. Generate the DDSCAT input files

From the repository directory:

```bash
python3 generate_ddscat.py input.toml
```

For a `FROM_FILE` target, the run directory should then contain:

```text
ddscat.par
shape.dat
diel.dat
```

For an `ELLIPSOID` target, `shape.dat` is not needed because DDSCAT generates
the target internally.

It is a good idea to inspect the generated parameter file before the first
run:

```bash
cat /path/to/run_directory/ddscat.par
```

---

## 3. Run DDSCAT locally

The same shell script can be run directly without Slurm:

```bash
bash main.sh input.toml
```

The script first regenerates the input files and then starts the DDSCAT
executable inside the configured run directory.

A successful calculation should eventually report:

```text
DDSCAT normal termination
```

---

## 4. Run DDSCAT with Slurm

The Slurm settings are at the top of `main.sh`:

```bash
#SBATCH --job-name=ddscat
#SBATCH --partition=student-l
#SBATCH --qos=long
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=1-00:00:00
#SBATCH --mem=8G
```

Adjust these lines for the local cluster if necessary.

A serial DDSCAT executable should normally request one CPU. Requesting more
CPUs does not make a serial build faster.

Submit the run with:

```bash
sbatch main.sh input.toml
```

Check the queue with:

```bash
squeue -u $USER
```

The Slurm standard output and error files are named approximately:

```text
ddscat_<jobid>.out
ddscat_<jobid>.err
```

---

## 5. Check whether the calculation finished

Run:

```bash
python3 check_run.py input.toml
```

For a calculation with 60 wavelengths and one effective radius, a complete
`qtable` should report something like:

```text
qtable rows: 60 / 60
status: DDSCAT normal termination
```

If DDSCAT failed, the script prints the final lines of the log.

A common convergence error is:

```text
FATAL ERROR IN PROCEDURE: ZBCG2WP
ITERN>ITERMX
```

This means that the iterative solver reached `max_iterations` before reaching
the requested tolerance.

Do not automatically increase the iteration limit. First check whether the
selected wavelength, material and dipole resolution are reasonable.

---

## 6. Important output files

DDSCAT can create many output files. The most useful ones for a first analysis
are:

- `qtable` — main wavelength-dependent quantities such as `Qext`, `Qabs`, `Qsca`, and `g`
- `qtable2` — additional wavelength-dependent quantities
- `wXXXrXXX.avg` — detailed averaged result for one wavelength and effective radius
- `wXXXrXXXkXXX.sca` — angular scattering and Mueller-matrix information when requested
- `target.out` — information about the target geometry
- `ddscat.log_000` — numerical log, timing information, and solver convergence

The main efficiency factors satisfy:

```text
Qext = Qabs + Qsca
```

DDSCAT defines an efficiency from its corresponding cross section using:

```text
Q = C / (pi * a_eff^2)
```

For porous targets, remember that `a_eff` is the equal-material-volume radius.
It can differ from the outer physical radius of the grain.

---

## 7. Make a quick plot

After a successful run:

```bash
python3 plot_qtable.py input.toml
```

This creates:

```text
qtable_overview.png
```

inside the run directory and plots `Qabs`, `Qsca`, and `Qext` as functions of
wavelength.

---

## Additional analysis scripts

The `scripts/` directory contains small scripts used during the project.

### `compare_qtables.py`

Compares the absorption efficiency from two DDSCAT runs and plots

```text
Qabs / Qabs_reference
```

Useful for comparing porosity, shape, composition, or resolution.

Change the paths near the beginning of the file:

```python
REFERENCE = Path("run_reference/qtable")
COMPARISON = Path("run_other/qtable")
```

### `plot_multiple_qtables.py`

Plots `Qabs(lambda)` from several runs in one figure.

Edit the `RUNS` dictionary at the beginning of the file to add or remove
calculations.

### `plot_shape_slice.py`

Plots a central slice through a custom `shape.dat`.

Change:

```python
SHAPE_FILE = Path("shape.dat")
SLICE_Z = 0
```

The material number stored in `ICOMPX` is used to distinguish different
materials.

### `generate_porous_sphere.py`

Generates custom porous spherical targets as `shape.dat` files.

Change the porosity list near the beginning:

```python
POROSITIES = [
    0.0,
    0.1,
    0.2,
    0.3,
    0.4,
    0.5,
    0.6,
]
```

A fixed random seed is used so that the generated targets are reproducible.

### Runtime scripts

The runtime scripts read the timing information written to `ddscat.log_000`.

Available examples are:

- `runtime_vs_wavelength.py`
- `runtime_vs_porosity.py`
- `runtime_vs_oblateness.py`
- `runtime_vs_ice_fraction.py`

These scripts are intended as examples. Change the directory paths at the
beginning to match your own run structure.

---

## Plotting choices

The analysis scripts contain settings such as:

```python
X_SCALE = "log"
Y_SCALE = "log"
```

Change either value to:

```python
"linear"
```

for a linear axis.

This only changes the plot. It does not change the wavelength distribution
used by DDSCAT.

The DDSCAT wavelength grid itself is controlled separately in `input.toml`:

```toml
spacing = "LOG"
```

Available DDSCAT spacing options are:

- `LIN` — equally spaced in wavelength
- `LOG` — equally spaced in logarithmic wavelength
- `INV` — equally spaced in inverse wavelength

---

## Minimal workflow

For an already compiled DDSCAT installation, the complete workflow is:

```bash
cp input.toml my_input.toml
nano my_input.toml

python3 generate_ddscat.py my_input.toml

sbatch main.sh my_input.toml

python3 check_run.py my_input.toml
python3 plot_qtable.py my_input.toml
```

For a local run without Slurm:

```bash
bash main.sh my_input.toml
```

The copied TOML input file is normally the only file that needs to be edited
for a new simulation.

---

## References and further information

- B. T. Draine & P. J. Flatau, DDSCAT User Guide
- B. T. Draine & P. J. Flatau (1994), *Discrete-dipole approximation for
  scattering calculations*, Journal of the Optical Society of America A,
  11, 1491.
- Official DDSCAT download page:
  **https://ddscat.wikidot.com/downloads**
