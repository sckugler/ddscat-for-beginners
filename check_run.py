#!/usr/bin/env python3

from pathlib import Path
import re
import sys
import tomllib


data_pattern = re.compile(
    r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)[Ee][+-]?\d+$"
)


def load_config(filename):
    with open(filename, "rb") as file:
        return tomllib.load(file)


def count_qtable_rows(filename):
    count = 0

    if not filename.exists():
        return count

    with open(filename) as file:
        for line in file:
            values = line.split()

            if len(values) < 8:
                continue

            if data_pattern.match(values[0]) and data_pattern.match(values[1]):
                count += 1

    return count


def main(config_filename):
    config = load_config(config_filename)
    run_directory = Path(config["paths"]["run_directory"]).expanduser()

    nwav = int(config["wavelength"]["count"])
    nrad = int(config["effective_radius"]["count"])
    expected = nwav * nrad

    qtable = run_directory / "qtable"
    completed = count_qtable_rows(qtable)

    print(f"run directory: {run_directory}")
    print(f"qtable rows: {completed} / {expected}")

    log_files = sorted(run_directory.glob("ddscat.log_*"))

    if not log_files:
        print("no ddscat.log_* file found")
        return

    latest_log = log_files[-1]
    text = latest_log.read_text(errors="replace")

    if "DDSCAT normal termination" in text:
        print("status: DDSCAT normal termination")
    elif "FATAL ERROR" in text:
        print("status: fatal error reported")
        print("last log lines:")
        print("\n".join(text.splitlines()[-15:]))
    else:
        print("status: run may still be active or ended without normal termination")
        print("last log lines:")
        print("\n".join(text.splitlines()[-10:]))


if __name__ == "__main__":
    config_filename = sys.argv[1] if len(sys.argv) > 1 else "input.toml"
    main(config_filename)
