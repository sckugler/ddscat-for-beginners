#!/bin/bash

# Slurm settings
# These lines are only used when the script is submitted with:
#     sbatch main.sh input.toml
# If you run the script locally with:
#     bash main.sh input.toml
# Slurm ignores these lines.

#SBATCH --job-name=ddscat

# CHANGE THIS if your cluster uses a different partition.
#SBATCH --partition=student-l

# CHANGE THIS if your cluster uses a different QoS,
# or remove the line if no QoS is required.
#SBATCH --qos=long

# DDSCAT is normally run here as a serial program.
# One node, one task and one CPU are therefore sufficient.
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1

# CHANGE THIS if the calculation needs more or less time.
# format: days-hours:minutes:seconds
#SBATCH --time=1-00:00:00

# CHANGE THIS if a larger calculation needs more memory.
#SBATCH --mem=8G
# Stop the script immediately if one command fails.
set -e


# Input file
# The script expects exactly one argument:
#     bash main.sh input.toml
# or
#     sbatch main.sh input.toml

if [ "$#" -ne 1 ]; then
    echo "Usage: bash main.sh input.toml"
    exit 1
fi


CONFIG="$1"

# Generate DDSCAT input files
# This calls generate_ddscat.py, which reads input.toml and:
# - creates the run directory
# - writes ddscat.par
# - copies the material file to diel.dat
# - copies shape.dat if FROM_FILE is used

python3 generate_ddscat.py "$CONFIG"


# Read paths from input.toml
# Instead of hard-coding paths here, the script reads them directly from the TOML configuration file.

RUN_DIRECTORY=$(python3 - "$CONFIG" <<'PY'
import sys
import tomllib

with open(sys.argv[1], "rb") as file:
    cfg = tomllib.load(file)

print(cfg["paths"]["run_directory"])
PY
)


DDSCAT_EXECUTABLE=$(python3 - "$CONFIG" <<'PY'
import sys
import tomllib

with open(sys.argv[1], "rb") as file:
    cfg = tomllib.load(file)

print(cfg["paths"]["ddscat_executable"])
PY
)

# DDSCAT must be started inside the run directory because it looks for ddscat.par in the current working directory

cd "$RUN_DIRECTORY"


# Start the compiled DDSCAT executable.
"$DDSCAT_EXECUTABLE"
