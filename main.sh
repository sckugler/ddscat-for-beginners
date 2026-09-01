#!/bin/bash
#SBATCH --job-name=ddscat
#SBATCH --partition=student-l
#SBATCH --qos=long
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=1-00:00:00
#SBATCH --mem=8G
#SBATCH --output=ddscat_%j.out
#SBATCH --error=ddscat_%j.err

set -euo pipefail

config="${1:-input.toml}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python "$script_dir/generate_ddscat.py" "$config"

mapfile -t settings < <(
    python - "$config" <<'PY'
import sys
import tomllib
from pathlib import Path

with open(sys.argv[1], "rb") as file:
    config = tomllib.load(file)

print(Path(config["paths"]["run_directory"]).expanduser())
print(Path(config["paths"]["ddscat_executable"]).expanduser())
PY
)

run_directory="${settings[0]}"
ddscat_executable="${settings[1]}"

cd "$run_directory"

echo "running DDSCAT in $run_directory"
echo "executable: $ddscat_executable"

"$ddscat_executable"
