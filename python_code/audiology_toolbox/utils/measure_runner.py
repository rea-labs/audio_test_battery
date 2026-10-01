"""
measure_runner.py
-----------------
Interactive bench driver for PROLACTIN coupler measurements.

Walks the pending rows of a calibration_check CSV, plays each stimulus via
level_validator, prompts for the value read off the REW RTA cursor, and writes
it straight back to the file. The CSV is rewritten after every entry, so an
interrupted session loses nothing.

Rows are visited in file order, which is ear-major in the generated template --
work straight down and each side is mounted once.

Usage
-----
    # from python_code/audiology_toolbox/
    python utils/measure_runner.py tests/lab_2026-07-23_unit_X.csv \
        --profile beyerdynamic_dt250_x_ucx2 --dur 30

    # one ear at a time
    python utils/measure_runner.py tests/lab_2026-07-23_unit_X.csv \
        --profile beyerdynamic_dt250_x_ucx2 --dur 30 --ear left

    # just the reseat rows after a remount
    python utils/measure_runner.py tests/lab_2026-07-23_unit_X.csv \
        --profile beyerdynamic_dt250_x_ucx2 --dur 30 --only reseat

    # group the queue by frequency, so the RTA cursor moves once per frequency
    # instead of once per row (the template is level-major)
    python utils/measure_runner.py tests/lab_2026-07-23_unit_X.csv \
        --profile beyerdynamic_dt250_x_ucx2 --dur 30 --order freq

    # re-measure rows that already have a value
    python utils/measure_runner.py tests/lab_2026-07-23_unit_X.csv \
        --profile beyerdynamic_dt250_x_ucx2 --dur 30 --redo --ear right

    # see what would run without playing anything
    python utils/measure_runner.py tests/lab_2026-07-23_unit_X.csv --dry-run

Keys
----
    At "ready" :  Enter = play      number = record directly
                  s = skip          q = quit
    At "value" :  number = record   r = replay immediately
                  s = skip          q = quit

Notes
-----
Entries more than --guard dB from the requested level (default 15) must be
confirmed before they are written. Doubled keystrokes -- 5555.40 for 55.40 --
are the common failure mode and are otherwise invisible until analysis.

If the CSV has a 'timestamp' column it is filled in automatically, so an odd
reading can later be checked against what was happening in the room.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import os
import subprocess
import sys
from pathlib import Path


def find_config(explicit):
    """Locate calibration_config.json: explicit path, else walk up for it."""
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_file():
            raise SystemExit("Config not found: %s" % path)
        return str(path.resolve())
    here = Path.cwd().resolve()
    for base in [here] + list(here.parents):
        candidate = base / "calibration_data" / "calibration_config.json"
        if candidate.is_file():
            return str(candidate.resolve())
    raise SystemExit(
        "Could not auto-locate calibration_data/calibration_config.json.\n"
        "Pass it explicitly with --config."
    )


def find_validator(explicit):
    """level_validator.py, defaulting to the copy beside this script."""
    path = Path(explicit) if explicit else Path(__file__).resolve().parent / "level_validator.py"
    if not path.is_file():
        raise SystemExit("level_validator.py not found: %s" % path)
    return str(path.resolve())


def describe(row):
    freq = (row.get("freq_hz") or "").strip()
    freq_txt = "%8s Hz" % freq if freq else "  broadband"
    return ("%-5s ear | %-5s | %s | %5s dB SPL | seat %s | %s"
            % (row.get("ear", "?"), row.get("stim_type", "tone"), freq_txt,
               (row.get("requested_spl") or "?").strip(),
               (row.get("seat") or "1").strip(),
               (row.get("notes") or "").strip()))


def build_command(row, config, validator, profile, dur, fade):
    cmd = [sys.executable, validator, "--config", config,
           "--no-gui", "--play",
           "--type", (row.get("stim_type") or "tone").strip(),
           "--level", (row.get("requested_spl") or "").strip(),
           "--ear", (row.get("ear") or "left").strip(),
           "--dur", str(dur)]
    if profile:
        cmd += ["--profile", profile]
    freq = (row.get("freq_hz") or "").strip()
    if freq:
        cmd += ["--freq", freq]
    if fade is not None:
        cmd += ["--fade", str(fade)]
    return cmd


def save(path, fieldnames, rows):
    """Rewrite the CSV via a temp file so an interrupt cannot truncate it."""
    tmp = Path(str(path) + ".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)


def parse_value(text, requested, guard):
    """Parse a reading, confirming anything implausibly far from the request."""
    try:
        value = float(text)
    except ValueError:
        print("  ?? not a number")
        return None
    if guard > 0 and abs(value - requested) > guard:
        answer = input("  !! %.2f is %.1f dB from the requested %.1f. "
                       "Type it again to confirm: "
                       % (value, value - requested, requested)).strip()
        try:
            if abs(float(answer) - value) > 1e-9:
                print("  ?? did not match, discarded")
                return None
        except ValueError:
            print("  ?? discarded")
            return None
    return value


def sort_key(row):
    """Group by ear, then frequency, then level. Broadband rows go last."""
    try:
        freq = float(row.get("freq_hz"))
    except (TypeError, ValueError):
        freq = float("inf")
    try:
        level = float(row.get("requested_spl"))
    except (TypeError, ValueError):
        level = 0.0
    return ((row.get("ear") or "").lower(), freq, level)


def wanted(row, args):
    if (row.get("measured_spl") or "").strip() and not args.redo:
        return False
    if args.ear and (row.get("ear") or "").strip().lower() != args.ear:
        return False
    if args.only and args.only.lower() not in (row.get("notes") or "").lower():
        return False
    if args.level is not None:
        try:
            if float(row.get("requested_spl")) != args.level:
                return False
        except (TypeError, ValueError):
            return False
    return True


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[3],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("csv", help="Measurement CSV to fill in.")
    p.add_argument("--config", default=None,
                   help="calibration_config.json (auto-located if omitted).")
    p.add_argument("--validator", default=None,
                   help="Path to level_validator.py (default: beside this script).")
    p.add_argument("--profile", default=None, help="Calibration profile name.")
    p.add_argument("--dur", type=float, default=30.0,
                   help="Stimulus duration, s (default 30 -- must outlast the "
                        "RTA average count).")
    p.add_argument("--fade", type=float, default=None, help="Fade time, s.")
    p.add_argument("--ear", default=None, choices=["left", "right"],
                   help="Restrict to one ear.")
    p.add_argument("--only", default=None,
                   help="Only rows whose notes contain this substring.")
    p.add_argument("--level", type=float, default=None,
                   help="Only rows at this requested level.")
    p.add_argument("--order", default="file", choices=["file", "freq"],
                   help="Queue order. 'freq' groups by ear then frequency so "
                        "the RTA cursor moves once per frequency.")
    p.add_argument("--guard", type=float, default=15.0,
                   help="Confirm any entry more than this many dB from the "
                        "requested level (0 disables).")
    p.add_argument("--redo", action="store_true",
                   help="Include rows that already have a value.")
    p.add_argument("--dry-run", action="store_true",
                   help="List what would run; play nothing.")
    args = p.parse_args(argv)

    path = Path(args.csv)
    with open(path, "r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    if "measured_spl" not in fieldnames:
        raise SystemExit("CSV has no measured_spl column.")

    todo = [i for i, r in enumerate(rows) if wanted(r, args)]
    if args.order == "freq":
        todo.sort(key=lambda i: sort_key(rows[i]))
    done_already = sum(1 for r in rows if (r.get("measured_spl") or "").strip())
    print("%s: %d rows, %d already measured, %d queued this run"
          % (path.name, len(rows), done_already, len(todo)))

    if args.dry_run:
        for n, i in enumerate(todo, 1):
            print("  %3d. %s" % (n, describe(rows[i])))
        return 0
    if not todo:
        print("Nothing queued. Use --redo to re-measure filled rows.")
        return 0

    config = find_config(args.config)
    validator = find_validator(args.validator)
    print("config    : %s" % config)
    print("validator : %s" % validator)
    print("profile   : %s" % (args.profile or "(config default)"))
    print("duration  : %.0f s\n" % args.dur)

    recorded = 0
    try:
        for n, i in enumerate(todo, 1):
            row = rows[i]
            print("-" * 70)
            print("[%d/%d]  %s" % (n, len(todo), describe(row)))
            try:
                requested = float(row.get("requested_spl"))
            except (TypeError, ValueError):
                requested = 0.0
            cmd = build_command(row, config, validator, args.profile,
                                args.dur, args.fade)
            state = "ready"
            while True:
                if state == "play":
                    if subprocess.run(cmd).returncode != 0:
                        print("  !! level_validator failed -- not recording.")
                        state = "ready"
                        continue
                    state = "value"
                    continue

                if state == "ready":
                    key = input("  Enter to play (s skip, q quit): ").strip().lower()
                else:
                    key = input("  dB SPL from RTA cursor "
                                "(r replay, s skip, q quit): ").strip().lower()

                if key == "q":
                    raise KeyboardInterrupt
                if key == "s":
                    break
                if key == "r" or (key == "" and state == "ready"):
                    state = "play"
                    continue
                if key == "":
                    continue

                value = parse_value(key, requested, args.guard)
                if value is None:
                    continue
                row["measured_spl"] = "%.2f" % value
                if "timestamp" in fieldnames:
                    row["timestamp"] = datetime.datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S")
                save(path, fieldnames, rows)
                recorded += 1
                print("  recorded %s dB SPL  (saved)" % row["measured_spl"])
                break
    except KeyboardInterrupt:
        print("\nStopped.")

    save(path, fieldnames, rows)
    remaining = sum(1 for r in rows if not (r.get("measured_spl") or "").strip())
    print("\n%d recorded this run. %d rows still blank." % (recorded, remaining))
    return 0


if __name__ == "__main__":
    sys.exit(main())
