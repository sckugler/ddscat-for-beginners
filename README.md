# DDSCAT run workflow

This repository contains a small wrapper around DDSCAT. DDSCAT itself is treated as a black box: the user sets the simulation parameters in one file, the Python helper creates `ddscat.par`, and `main.sh` runs DDSCAT.
 
For installation and background information, see the accompanying manual (`main.txt`) and the official DDSCAT User Guide. 
 
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
-- VISUAL --                                                                                                                                                                           6         3,217         Top
