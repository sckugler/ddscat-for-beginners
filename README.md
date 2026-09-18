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

The Examples download is important because it contains the `examples_exp`
directory used throughout this repository.

A convenient directory structure is

```text
DDA/
├── src/
│   └── ddscat
├── examples_exp/
├── diel/
└── doc/

# DDSCAT run workflow

This repository is meant to help getting familiar with DDSCAT without having to understand the code itself. The user defines the simulation parameters in one file (input.toml), additional Python scripts then create the file `ddscat.par`, and `main.sh` runs DDSCAT.

For installation and necessairy background information, see the accompanying manual and the official DDSCAT User Guide.

## Files in this repository

```text
.
├── input.toml
├── generate_ddscat.py
├── main.sh
├── check_run.py
├── plot_qtable.py
└── main.txt
```

The workflow uses one user-editable input file:

- `input.toml`: paths, target, wavelength grid, effective radius and numerical settings

The scripts are:

- `generate_ddscat.py`: creates the run directory and `ddscat.par`
- `main.sh`: prepares the input files and runs DDSCAT; it can be submitted with Slurm
- `check_run.py`: checks how many wavelength/radius combinations finished and inspects the DDSCAT log
- `plot_qtable.py`: makes a first overview plot from `qtable`

## Before running

DDSCAT must already be compiled. The path to the executable is set in `input.toml`:

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

The helper copies the material into the run directory as `diel.dat` and the custom geometry as `shape.dat`. `ddscat.par` therefore contains short local file names. This also avoids problems with long material paths in DDSCAT.

For a built-in ellipsoid target, use:

```toml
shape = "ELLIPSOID"
shape_parameters = [70.0, 70.0, 70.0]
```

Use equal shape parameters for a sphere. The values are passed directly to DDSCAT as `SHPAR1`, `SHPAR2`, and `SHPAR3`; consult the DDSCAT manual before changing them.

## 1. Edit `input.toml`

The most commonly changed entries are:

```toml
[paths]
ddscat_executable = "/star/home/USER/DDA/src/ddscat"
run_directory = "/star/data/USER/DDSCAT/example_run"
material_file = "/star/home/USER/DDA/diel/astrosil"

[target]
shape = "FROM_FILE"
shape_file = "/star/data/USER/DDSCAT/shapes/shape.dat"

[effective_radius]
minimum_um = 1.0
maximum_um = 1.0
count = 1
spacing = "LIN"

[wavelength]
minimum_um = 0.3
maximum_um = 100.0
count = 60
spacing = "LOG"
```

`LIN`, `LOG`, and `INV` are accepted for the wavelength and effective-radius grids.

The numerical settings normally do not need to be changed for a first run. In particular:

```toml
[numerics]
tolerance = 1.0e-5
max_iterations = 1000
solver = "PBCGS2"
fft = "GPFAFT"
polarizability = "GKDLDR"
```

## 2. Generate the DDSCAT input files

From the repository directory:

```bash
python generate_ddscat.py input.toml
```

For a `FROM_FILE` target, the run directory should then contain:

```text
ddscat.par
shape.dat
diel.dat
```

For an `ELLIPSOID` target, `shape.dat` is not needed because DDSCAT generates the target internally.

It is a good idea to inspect the generated parameter file before the first run:

```bash
cat /path/to/run_directory/ddscat.par
```

## 3. Run DDSCAT locally

The same shell script can be run directly without Slurm:

```bash
bash main.sh input.toml
```

The script first regenerates the input files and then starts the DDSCAT executable inside the configured run directory.

A successful calculation should eventually report:

```text
DDSCAT normal termination
```

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

Adjust these lines for the local cluster if necessary. A serial DDSCAT executable should normally request one CPU. Requesting more CPUs does not make a serial build faster.

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

## 5. Check whether the calculation finished

Run:

```bash
python check_run.py input.toml
```

For a calculation with 60 wavelengths and one effective radius, a complete `qtable` should report:

```text
qtable rows: 60 / 60
status: DDSCAT normal termination
```

If DDSCAT failed, the script prints the final lines of the log. A common convergence error is:

```text
FATAL ERROR IN PROCEDURE: ZBCG2WP
ITERN>ITERMX
```

This means that the iterative solver reached `max_iterations` before reaching the requested tolerance. Do not automatically increase the iteration limit: first check whether the chosen dipole resolution is appropriate for the wavelength and refractive index.

## 6. Important output files

DDSCAT can create many files. The most useful ones for a first analysis are:

- `qtable`: one row per wavelength/effective-radius combination; contains `Qext`, `Qabs`, `Qsca`, `g`, and related quantities
- `qtable2`: additional wavelength-dependent quantities
- `wXXXrXXX.avg`: detailed averaged results for one wavelength and effective radius
- `wXXXrXXXkXXX.sca`: angular scattering and Mueller-matrix information when requested
- `target.out`: information about the target geometry
- `ddscat.log_000`: numerical log and convergence information

The main efficiency factors satisfy

```text
Qext = Qabs + Qsca
```

DDSCAT defines an efficiency from its corresponding cross section using the effective radius:

```text
Q = C / (pi * a_eff^2)
```

For porous targets, remember that `a_eff` is the equal-material-volume radius and can differ from the outer physical radius of the target.

## 7. Make a quick plot

After a successful run:

```bash
python plot_qtable.py input.toml
```

This creates:

```text
qtable_overview.png
```

inside the run directory and plots `Qabs`, `Qsca`, and `Qext` as functions of wavelength.

## Minimal workflow

For an already compiled DDSCAT installation, the complete workflow is therefore:

```bash
cp input.toml my_input.toml
nano my_input.toml
python generate_ddscat.py my_input.toml
sbatch main.sh my_input.toml
python check_run.py my_input.toml
python plot_qtable.py my_input.toml
```

The only file that normally needs to be edited for a new simulation is the copied TOML input file.
