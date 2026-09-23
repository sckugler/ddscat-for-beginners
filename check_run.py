'''
Check the progress/status of a DDSCAT run

Normally, you do NOT need to edit this file.
Run it with:

    python3 check_run.py input.toml

It reads the run directory and expected number of wavelength/radius points
from input.toml, then checks qtable and ddscat.log_000.

If your DDSCAT setup writes progress in a different way, this script may need
to be adapted.
'''

from pathlib import Path
import sys
import tomllib


if len(sys.argv) != 2:
    raise SystemExit("Usage: python3 check_run.py input.toml")


with open(sys.argv[1], "rb") as file:
    cfg = tomllib.load(file)


run_directory = Path(cfg["paths"]["run_directory"]).expanduser()

expected = (
    cfg["wavelength"]["count"]
    * cfg["effective_radius"]["count"]
)

qtable = run_directory / "qtable"
logfile = run_directory / "ddscat.log_000"


def count_qtable_rows(filename):
    if not filename.exists():
        return 0

    count = 0

    with open(filename) as file:
        for line in file:
            values = line.split()

            if len(values) < 8:
                continue

            try:
                [float(x) for x in values[:8]]
            except ValueError:
                continue

            count += 1

    return count


finished = count_qtable_rows(qtable)

print(f"qtable rows: {finished} / {expected}")

if logfile.exists():
    text = logfile.read_text(errors="replace")

    if "DDSCAT normal termination" in text:
        print("status: DDSCAT normal termination")
    else:
        print("status: run not normally terminated")
        print("\nLast lines of ddscat.log_000:\n")
        print("\n".join(text.splitlines()[-20:]))
else:
    print("ddscat.log_000 not found")
