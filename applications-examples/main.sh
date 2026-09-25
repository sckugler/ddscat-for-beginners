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

set -euo pipefail

# ---------------------------------------------------------------------------
# Working directory
# ---------------------------------------------------------------------------

work_dir="${SLURM_SUBMIT_DIR:-$(pwd)}"

cd "$work_dir"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

config="${1:-input.toml}"

# ---------------------------------------------------------------------------
# Generate DDSCAT run directories
# ---------------------------------------------------------------------------

echo "============================================================"
echo "Generating DDSCAT runs"
echo "============================================================"

python3 "generate_ddscat.py" "$config"

# ---------------------------------------------------------------------------
# Read paths from TOML
# ---------------------------------------------------------------------------

mapfile -t settings < <(
    python3 - "$config" <<'PY'
import sys
import tomllib
from pathlib import Path

with open(sys.argv[1], "rb") as file:
    config = tomllib.load(file)

print(Path(config["paths"]["run_directory"]).expanduser().resolve())
print(Path(config["paths"]["ddscat_executable"]).expanduser().resolve())
PY
)

run_directory="${settings[0]}"
ddscat_executable="${settings[1]}"

# ---------------------------------------------------------------------------
# Basic checks
# ---------------------------------------------------------------------------

if [[ ! -d "$run_directory" ]]; then
    echo "ERROR: Run directory does not exist:"
    echo "       $run_directory"
    exit 1
fi

if [[ ! -x "$ddscat_executable" ]]; then
    echo "ERROR: DDSCAT executable not found or not executable:"
    echo "       $ddscat_executable"
    exit 1
fi

# ---------------------------------------------------------------------------
# Find all DDSCAT run directories
# ---------------------------------------------------------------------------

mapfile -t run_dirs < <(
    find "$run_directory" \
        -type f \
        -name 'ddscat.par' \
        -printf '%h\n' \
        | sort -V
)

if [[ ${#run_dirs[@]} -eq 0 ]]; then
    echo "ERROR: No DDSCAT run directories found in:"
    echo "       $run_directory"
    exit 1
fi

# ---------------------------------------------------------------------------
# Run DDSCAT for every radius × dipole resolution
# ---------------------------------------------------------------------------

echo ""
echo "============================================================"
echo "DDSCAT runs"
echo "============================================================"
echo "Run directory : $run_directory"
echo "Executable    : $ddscat_executable"
echo "Number of runs: ${#run_dirs[@]}"
echo "Host          : $(hostname)"
echo "Start time    : $(date)"
echo "============================================================"
echo ""


for run_dir in "${run_dirs[@]}"; do

    echo ""
    echo "------------------------------------------------------------"
    echo "Starting run"
    echo "Directory: $run_dir"
    echo "Time: $(date)"
    echo "------------------------------------------------------------"

    cd "$run_dir"

    if [[ ! -f "ddscat.par" ]]; then
        echo "ERROR: ddscat.par not found in:"
        echo "       $run_dir"
        exit 1
    fi

    echo "Running DDSCAT..."

    "$ddscat_executable"

    if [[ ! -f "qtable" ]]; then
        echo "ERROR: DDSCAT finished, but no qtable was produced in:"
        echo "       $run_dir"
        exit 1
    fi

    echo "Finished run"
    echo "qtable found:"
    ls -lh qtable

done

# ---------------------------------------------------------------------------
# Finished
# ---------------------------------------------------------------------------

echo ""
echo "============================================================"
echo "All DDSCAT runs completed successfully"
echo "============================================================"
echo "Number of runs: ${#run_dirs[@]}"
echo "End time      : $(date)"
echo "============================================================"

# ---------------------------------------------------------------------------
# Analyse DDSCAT results
# ---------------------------------------------------------------------------

echo ""
echo "============================================================"
echo "Starting DDSCAT / Mie analysis"
echo "============================================================"
echo ""

cd "$work_dir"

python3 run_ddscat_pipeline.py --analysis-only "$config"

echo ""
echo "============================================================"
echo "Complete pipeline finished successfully"
echo "End time: $(date)"
echo "============================================================"

# ---------------------------------------------------------------------------