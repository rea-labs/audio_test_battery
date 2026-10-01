"""
calibration_check.py
--------------------
Standalone analysis / plotting tool for PROLACTIN coupler measurements.

Reads a flat CSV of requested-vs-measured dB SPL readings taken on the B&K
artificial ear and reports:

  1. Level linearity      -- measured vs requested slope / intercept / residual,
                             per (unit, ear, frequency, stimulus type).
  2. Frequency flatness   -- deviation from requested SPL at each frequency, and
                             deviation relative to the 1 kHz anchor.
  3. Level-independence   -- how much the per-frequency residual moves when the
                             requested level changes. This is the go/no-go test
                             for a per-frequency "spot-check" correction table:
                             a single dB offset per frequency is only a valid
                             model if the residual is level-independent.
  4. Reseat variability   -- spread across remounts of the same headphone. Sets
                             the floor on how small a residual is worth
                             correcting at all.
  5. L/R asymmetry        -- per-frequency left-minus-right difference.
  6. Noise vs tone bias   -- mean residual difference between stimulus types at
                             matched level (PROLACTIN open issue M11).
  7. Candidate correction -- per-frequency mean residual plus an explicit
                             verdict (correctable / level-dependent / within
                             noise), optionally dumped as JSON.
  8. dB HL spot-check     -- optional; subtracts a profile's RETSPL table from
                             the measured SPL and reports the implied HL
                             (PROLACTIN open issue M10).

Deliberately has NO dependency on the PROLACTIN toolbox: stdlib csv + numpy +
matplotlib only, so it runs on a bare laptop with no PsychoPy and no conda env.
Runs identically on macOS and Windows (pathlib, Agg backend, ASCII-only output).

Usage
-----
    # 1. Generate a blank CSV pre-filled with today's planned measurement points
    python calibration_check.py --template lab_2026-07-23.csv --unit X

    # 2. Fill in the measured_spl column at the bench, then analyse
    python calibration_check.py lab_2026-07-23.csv

    # 3. Analyse + write plots + candidate correction table
    python calibration_check.py lab_2026-07-23.csv --outdir results/ \
        --correction correction_candidate.json

    # 4. Add the dB HL spot-check
    python calibration_check.py lab_2026-07-23.csv \
        --retspl-config calibration_config.json \
        --retspl-profile beyerdynamic_dt250_x_ucx2 --hl-target 20

CSV schema
----------
    unit           free text headphone unit id (X, A, B, K, C)
    profile        calibration profile name (optional, informational)
    ear            left | right
    stim_type      tone | sweep | noise
    requested_spl  float, dB SPL asked for
    freq_hz        float; blank / "broadband" for noise
    measured_spl   float, dB SPL read on the coupler. BLANK = not yet measured.
    seat           integer mount number; bump it after every remount
    notes          free text

Blank measured_spl rows are counted and skipped, so the same file works as the
bench checklist and as the analysis input.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


FIELDS = ["unit", "profile", "ear", "stim_type", "requested_spl",
          "freq_hz", "measured_spl", "seat", "timestamp", "notes"]

# Defaults for --template. Mirror the planned lab blocks.
TEMPLATE_LEVELS_ANCHOR = [30, 40, 50, 60, 70, 80, 90, 100, 105]
TEMPLATE_LEVELS_EXTRA = [40, 55, 70, 85, 100]
TEMPLATE_LINEARITY_FREQS = [250, 1000, 4000]
TEMPLATE_FREQS = [125, 250, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000, 8000]
TEMPLATE_FREQ_LEVELS = [40, 60, 85]
TEMPLATE_NOISE_LEVELS = [40, 60, 85]
TEMPLATE_RESEAT_FREQS = [500, 1000, 4000]

ANCHOR_HZ = 1000.0


# ======================================================================
# I/O
# ======================================================================

def _f(value):
    """Parse a float, returning None for blank / non-numeric cells."""
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text.lower() in ("na", "n/a", "none", "broadband", "-"):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def load_csv(path):
    """Return (measured_rows, n_pending, n_malformed)."""
    rows, pending, malformed = [], 0, 0
    with open(path, "r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = [f for f in ("ear", "requested_spl", "measured_spl")
                   if f not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(
                "CSV is missing required column(s): %s\nFound: %s"
                % (", ".join(missing), ", ".join(reader.fieldnames or []))
            )
        for raw in reader:
            measured = _f(raw.get("measured_spl"))
            requested = _f(raw.get("requested_spl"))
            if measured is None:
                pending += 1
                continue
            if requested is None:
                malformed += 1
                continue
            rows.append({
                "unit": (raw.get("unit") or "?").strip(),
                "profile": (raw.get("profile") or "").strip(),
                "ear": (raw.get("ear") or "?").strip().lower(),
                "stim_type": (raw.get("stim_type") or "tone").strip().lower(),
                "requested_spl": requested,
                "freq_hz": _f(raw.get("freq_hz")),
                "measured_spl": measured,
                "seat": int(_f(raw.get("seat")) or 1),
                "notes": (raw.get("notes") or "").strip(),
                "residual": measured - requested,
            })
    return rows, pending, malformed


def write_template(path, unit, profile, lin_freqs=None, freq_levels=None):
    """Write a blank CSV pre-populated with the planned measurement points.

    All stimuli are discrete gated tones read off a settled SPL meter -- the
    swept-sine shortcut was rejected because recovering calibrated SPL per
    frequency from a sweep requires deconvolution, and an un-deconvolved sweep
    smears energy across frequency (FIR ringout ~85 ms at 4096 taps / 48 kHz
    plus transducer and coupler decay).
    """
    out = []
    lin_freqs = lin_freqs or TEMPLATE_LINEARITY_FREQS
    freq_levels = freq_levels or TEMPLATE_FREQ_LEVELS

    for ear in ("left", "right"):
        # Block 1.1 -- level linearity. Full level list at the anchor, a
        # reduced but well-spread list at the extra frequencies.
        for f in lin_freqs:
            levels = (TEMPLATE_LEVELS_ANCHOR if abs(f - ANCHOR_HZ) < 1e-6
                      else TEMPLATE_LEVELS_EXTRA)
            for lvl in levels:
                out.append(dict(unit=unit, profile=profile, ear=ear,
                                stim_type="tone", requested_spl=lvl,
                                freq_hz=f, measured_spl="", seat=1,
                                timestamp="", notes="1.1 linearity"))
        # Blocks 1.3 / 1.4 -- SPL vs frequency at several levels. Three levels
        # (not two) so section 3 can regress the residual against level rather
        # than differencing two noisy readings.
        for lvl in freq_levels:
            for f in TEMPLATE_FREQS:
                out.append(dict(unit=unit, profile=profile, ear=ear,
                                stim_type="tone", requested_spl=lvl,
                                freq_hz=f, measured_spl="", seat=1,
                                timestamp="", notes="1.3/1.4 flatness"))
        # Block 1.5 -- reseat repeat. Sets the correction floor in section 7.
        for f in TEMPLATE_RESEAT_FREQS:
            out.append(dict(unit=unit, profile=profile, ear=ear,
                            stim_type="tone", requested_spl=60, freq_hz=f,
                            measured_spl="", seat=2, timestamp="",
                            notes="1.5 reseat"))
        # Block 1.6 -- noise vs tone.
        for lvl in TEMPLATE_NOISE_LEVELS:
            out.append(dict(unit=unit, profile=profile, ear=ear,
                            stim_type="noise", requested_spl=lvl, freq_hz="",
                            measured_spl="", seat=1, timestamp="",
                            notes="1.6 noise vs tone"))
            out.append(dict(unit=unit, profile=profile, ear=ear,
                            stim_type="tone", requested_spl=lvl, freq_hz=1000,
                            measured_spl="", seat=1, timestamp="",
                            notes="1.6 noise vs tone"))

    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in out:
            writer.writerow(row)
    print("Wrote template with %d blank rows -> %s" % (len(out), path))


# ======================================================================
# Analysis helpers
# ======================================================================

def _group(rows, keys):
    out = defaultdict(list)
    for row in rows:
        out[tuple(row[k] for k in keys)].append(row)
    return out


def _fit_line(x, y):
    """Least-squares slope/intercept/r2/rms-residual. None if under-determined."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(np.unique(x)) < 3:
        return None
    slope, intercept = np.polyfit(x, y, 1)
    pred = slope * x + intercept
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    rms = math.sqrt(ss_res / len(x))
    return slope, intercept, r2, rms


def _flag(ok):
    return "OK  " if ok else "FAIL"


def _fmt_freq(hz):
    return "broadband" if hz is None else "%g Hz" % hz


# ======================================================================
# Reports
# ======================================================================

def report_linearity(rows, slope_tol, level_tol, lines):
    lines.append("")
    lines.append("=" * 72)
    lines.append("1. LEVEL LINEARITY  (measured vs requested; slope target 1.000 +/- %.3f)"
                 % slope_tol)
    lines.append("=" * 72)
    groups = _group([r for r in rows if r["stim_type"] != "noise"],
                    ["unit", "ear", "freq_hz", "stim_type"])
    lines.append("%-6s %-6s %-11s %-6s %5s %7s %8s %7s %7s %6s"
                 % ("unit", "ear", "freq", "stim", "n", "slope", "intercept",
                    "r2", "rms", "flag"))
    for key in sorted(groups, key=lambda k: (k[0], k[1], k[2] or 0, k[3])):
        unit, ear, freq, stim = key
        grp = groups[key]
        fit = _fit_line([r["requested_spl"] for r in grp],
                        [r["measured_spl"] for r in grp])
        if fit is None:
            continue
        slope, intercept, r2, rms = fit
        ok = abs(slope - 1.0) <= slope_tol and rms <= level_tol
        lines.append("%-6s %-6s %-11s %-6s %5d %7.4f %8.2f %7.4f %7.2f %6s"
                     % (unit, ear, _fmt_freq(freq), stim, len(grp),
                        slope, intercept, r2, rms, _flag(ok)))
    lines.append("")
    lines.append("  rms = RMS of measured-minus-fit, in dB. A slope > 1 means the")
    lines.append("  chain gains more than requested as level rises (compression is")
    lines.append("  slope < 1). Check for clipping at the top of the range first.")


def report_flatness(rows, flat_tol, lines):
    lines.append("")
    lines.append("=" * 72)
    lines.append("2. FREQUENCY FLATNESS  (residual = measured - requested; tol +/- %.1f dB)"
                 % flat_tol)
    lines.append("=" * 72)
    tonal = [r for r in rows if r["freq_hz"] is not None
             and r["stim_type"] != "noise"]
    groups = _group(tonal, ["unit", "ear", "requested_spl"])
    for key in sorted(groups, key=lambda k: (k[0], k[1], k[2])):
        unit, ear, level = key
        # Collapse repeated readings (seats, stimulus types) to one row per
        # frequency so the table stays readable; n shows how many were pooled.
        per_freq = defaultdict(list)
        for r in groups[key]:
            per_freq[r["freq_hz"]].append(r["residual"])
        if len(per_freq) < 2:
            continue
        means = {f: float(np.mean(v)) for f, v in per_freq.items()}
        anchor_val = means.get(ANCHOR_HZ)
        resid = list(means.values())
        lines.append("")
        lines.append("  unit %s / %s ear / %.0f dB SPL requested   "
                     "(span %.2f dB, worst %+.2f dB)"
                     % (unit, ear, level, max(resid) - min(resid),
                        max(resid, key=abs)))
        lines.append("    %-10s %4s %10s %10s %6s"
                     % ("freq", "n", "residual", "re 1 kHz", "flag"))
        for freq in sorted(means):
            res = means[freq]
            re_anchor = ("%+10.2f" % (res - anchor_val)
                         if anchor_val is not None else "%10s" % "-")
            lines.append("    %-10s %4d %+10.2f %s %6s"
                         % (_fmt_freq(freq), len(per_freq[freq]), res,
                            re_anchor, _flag(abs(res) <= flat_tol)))


def _level_dependence(grp):
    """Return (n, mean_residual, spread, slope_per_10dB or None).

    With 3+ distinct requested levels a regression slope is far more
    trustworthy than max-minus-min, which on two points is just the
    difference of two noisy readings.
    """
    levels = np.array([r["requested_spl"] for r in grp], dtype=float)
    resid = np.array([r["residual"] for r in grp], dtype=float)
    mean_res = float(np.mean(resid))
    spread = float(np.ptp(resid)) if len(resid) > 1 else 0.0
    slope = None
    if len(np.unique(levels)) >= 3:
        slope = float(np.polyfit(levels, resid, 1)[0]) * 10.0
    return len(grp), mean_res, spread, slope


def _level_dependent(slope, spread, tol):
    """Reject the fixed-offset model? Slope test preferred when available."""
    if slope is not None:
        # tol is a total-drift budget; spread it over a nominal 45 dB span.
        return abs(slope) > tol / 4.5
    return spread > tol


def report_level_independence(rows, lines):
    """The spot-check go/no-go: does the per-frequency residual move with level?"""
    lines.append("")
    lines.append("=" * 72)
    lines.append("3. LEVEL-INDEPENDENCE OF THE RESIDUAL  (spot-check validity test)")
    lines.append("=" * 72)
    tonal = [r for r in rows if r["freq_hz"] is not None
             and r["stim_type"] != "noise"]
    groups = _group(tonal, ["unit", "ear", "freq_hz"])
    lines.append("%-6s %-6s %-10s %4s %9s %9s %14s"
                 % ("unit", "ear", "freq", "n", "mean res", "spread",
                    "slope/10dB"))
    any_rows = False
    for key in sorted(groups, key=lambda k: (k[0], k[1], k[2])):
        unit, ear, freq = key
        grp = groups[key]
        if len({r["requested_spl"] for r in grp}) < 2:
            continue
        any_rows = True
        n, mean_res, spread, slope = _level_dependence(grp)
        slope_txt = "%+14.3f" % slope if slope is not None else "%14s" % "(2 levels)"
        lines.append("%-6s %-6s %-10s %4d %+9.2f %9.2f %s"
                     % (unit, ear, _fmt_freq(freq), n, mean_res, spread,
                        slope_txt))
    if not any_rows:
        lines.append("  (needs the same frequency measured at 2+ requested levels)")
    lines.append("")
    lines.append("  A per-frequency dB correction table assumes the residual does")
    lines.append("  NOT move with level. With 3+ levels the slope (dB of residual")
    lines.append("  per 10 dB of level) is the test and should be ~0; with only 2")
    lines.append("  levels the tool falls back to spread (max minus min), which is")
    lines.append("  just the difference of two noisy readings -- measure a third")
    lines.append("  level to make this statistic worth reading.")


def report_reseat(rows, lines):
    """Section 4: within-seat repeatability, then between-seat variability.

    Kept separate on purpose. Repeated readings at the SAME seat measure the
    meter and the toolbox; readings across seats add the seal. Only the
    between-seat number belongs in the correction floor, because in real use
    the headphone is reseated on every participant -- but seeing the two
    side by side tells you whether a large floor is a seating problem or a
    measurement problem.
    """
    lines.append("")
    lines.append("=" * 72)
    lines.append("4. REPEATABILITY AND RESEAT VARIABILITY")
    lines.append("=" * 72)
    tonal = [r for r in rows if r["freq_hz"] is not None]

    # --- 4a: repeated readings within a single seat --------------------
    lines.append("")
    lines.append("  4a. Within-seat repeatability (duplicate rows, same seat)")
    within = _group(tonal, ["unit", "ear", "freq_hz", "requested_spl",
                            "seat", "stim_type"])
    pooled_within, shown = [], False
    lines.append("    %-6s %-6s %-10s %8s %5s %5s %9s"
                 % ("unit", "ear", "freq", "level", "seat", "n", "sd"))
    for key in sorted(within, key=lambda k: (k[0], k[1], k[2], k[3], k[4])):
        grp = within[key]
        if len(grp) < 2:
            continue
        shown = True
        vals = np.array([r["measured_spl"] for r in grp])
        sd = float(np.std(vals, ddof=1))
        pooled_within.append(sd)
        lines.append("    %-6s %-6s %-10s %8.0f %5d %5d %9.2f"
                     % (key[0], key[1], _fmt_freq(key[2]), key[3], key[4],
                        len(grp), sd))
    if not shown:
        lines.append("    (no duplicate readings found)")
    else:
        lines.append("    Pooled within-seat SD: %.2f dB  "
                     "(meter + toolbox repeatability)"
                     % float(np.mean(pooled_within)))

    # --- 4b: across seats, comparing SEAT MEANS ------------------------
    lines.append("")
    lines.append("  4b. Between-seat variability (SD of per-seat means)")
    groups = _group(tonal, ["unit", "ear", "freq_hz", "requested_spl"])
    pooled, any_rows = [], False
    per_freq_sd = {}
    lines.append("    %-6s %-6s %-10s %8s %5s %9s %9s"
                 % ("unit", "ear", "freq", "level", "seats", "spread", "sd"))
    for key in sorted(groups, key=lambda k: (k[0], k[1], k[2], k[3])):
        unit, ear, freq, level = key
        by_seat = defaultdict(list)
        for r in groups[key]:
            by_seat[r["seat"]].append(r["measured_spl"])
        if len(by_seat) < 2:
            continue
        any_rows = True
        # Collapse each seat to its mean FIRST, so duplicate readings at one
        # seat cannot masquerade as between-seat spread.
        means = np.array([float(np.mean(v)) for v in by_seat.values()])
        sd = float(np.std(means, ddof=1))
        pooled.append(sd)
        per_freq_sd.setdefault((unit, ear, freq), []).append(sd)
        lines.append("    %-6s %-6s %-10s %8.0f %5d %9.2f %9.2f"
                     % (unit, ear, _fmt_freq(freq), level, len(by_seat),
                        float(np.ptp(means)), sd))
    if not any_rows:
        lines.append("    (no repeated seats -- bump the 'seat' column after a remount)")
        return None, {}
    reseat_sd = float(np.mean(pooled))
    lines.append("")
    lines.append("  Between-seat SD varies strongly with frequency, so section 7")
    lines.append("  uses the PER-FREQUENCY value where seat data exists and falls")
    lines.append("  back to the pooled figure only where it does not.")
    lines.append("  Pooled between-seat SD: %.2f dB. Fallback correction floor:"
                 % reseat_sd)
    lines.append("  a per-frequency residual smaller than roughly 2x this is noise.")
    if pooled_within:
        lines.append("  If 4b is much larger than 4a the limit is the seal, not the")
        lines.append("  measurement -- reseat more carefully before trusting section 7.")
    floors = {k: float(np.mean(v)) for k, v in per_freq_sd.items()}
    return reseat_sd, floors


def report_asymmetry(rows, lines):
    lines.append("")
    lines.append("=" * 72)
    lines.append("5. L/R ASYMMETRY  (left minus right, dB)")
    lines.append("=" * 72)
    groups = _group([r for r in rows if r["freq_hz"] is not None],
                    ["unit", "freq_hz", "requested_spl", "stim_type"])
    lines.append("%-6s %-10s %8s %-6s %10s"
                 % ("unit", "freq", "level", "stim", "L - R"))
    for key in sorted(groups, key=lambda k: (k[0], k[1], k[2], k[3])):
        unit, freq, level, stim = key
        grp = groups[key]
        left = [r["measured_spl"] for r in grp if r["ear"] == "left"]
        right = [r["measured_spl"] for r in grp if r["ear"] == "right"]
        if not left or not right:
            continue
        lines.append("%-6s %-10s %8.0f %-6s %+10.2f"
                     % (unit, _fmt_freq(freq), level, stim,
                        float(np.mean(left) - np.mean(right))))


def report_noise_vs_tone(rows, lines):
    lines.append("")
    lines.append("=" * 72)
    lines.append("6. NOISE vs TONE BIAS  (open issue M11; tone term = %g Hz only)"
                 % ANCHOR_HZ)
    lines.append("=" * 72)
    groups = _group(rows, ["unit", "ear", "requested_spl"])
    any_rows = False
    lines.append("%-6s %-6s %8s %11s %11s %10s"
                 % ("unit", "ear", "level", "tone res", "noise res", "bias"))
    for key in sorted(groups, key=lambda k: (k[0], k[1], k[2])):
        unit, ear, level = key
        grp = groups[key]
        # Compare against the ANCHOR-frequency tone only. Pooling every
        # tone row at this level would average the whole frequency-response
        # spread into the "tone" term and contaminate the bias estimate.
        tone = [r["residual"] for r in grp
                if r["stim_type"] == "tone" and r["freq_hz"] is not None
                and abs(r["freq_hz"] - ANCHOR_HZ) < 1e-6]
        noise = [r["residual"] for r in grp if r["stim_type"] == "noise"]
        if not tone or not noise:
            continue
        any_rows = True
        bias = float(np.mean(noise) - np.mean(tone))
        lines.append("%-6s %-6s %8.0f %+11.2f %+11.2f %+10.2f"
                     % (unit, ear, level, float(np.mean(tone)),
                        float(np.mean(noise)), bias))
    if not any_rows:
        lines.append("  (needs a noise row and a %g Hz tone row at the same level)"
                     % ANCHOR_HZ)
    else:
        lines.append("")
        lines.append("  Positive bias = noise reads louder than a tone requested at the")
        lines.append("  same dB SPL. If the bias is constant across level it is a")
        lines.append("  convention/crest-factor offset; if it grows, suspect bandwidth")
        lines.append("  or the RMS normalisation in level_validator.")


def report_correction(rows, reseat_sd, flat_tol, level_dep_tol, lines,
                      freq_floors=None, materiality=None):
    """Per-frequency candidate correction plus an explicit verdict."""
    lines.append("")
    lines.append("=" * 72)
    lines.append("7. CANDIDATE SPOT-CHECK CORRECTION TABLE")
    lines.append("=" * 72)
    freq_floors = freq_floors or {}
    fallback = 2.0 * reseat_sd if reseat_sd else 0.5
    if materiality is None:
        materiality = flat_tol / 2.0
    lines.append("  Two independent gates must BOTH be passed before a")
    lines.append("  correction is proposed:")
    lines.append("    (a) noise gate       -- deviation > 2x the between-seat SD")
    lines.append("                            at THAT frequency (pooled %.2f dB"
                 % fallback)
    lines.append("                            where no seat data exists)")
    lines.append("    (b) materiality gate -- deviation > %.2f dB (flat-tol / 2)."
                 % materiality)
    lines.append("                            A deviation well inside the")
    lines.append("                            tolerance is real but not worth")
    lines.append("                            correcting.")
    lines.append("")
    tonal = [r for r in rows if r["freq_hz"] is not None
             and r["stim_type"] != "noise"]
    groups = _group(tonal, ["unit", "ear", "freq_hz"])
    table = defaultdict(dict)
    lines.append("%-6s %-6s %-10s %10s %8s %8s  %s"
                 % ("unit", "ear", "freq", "correction", "spread", "floor",
                    "verdict"))
    for key in sorted(groups, key=lambda k: (k[0], k[1], k[2])):
        unit, ear, freq = key
        grp = groups[key]
        n, mean_res, spread, slope = _level_dependence(grp)
        sd_here = freq_floors.get((unit, ear, freq))
        floor = 2.0 * sd_here if sd_here is not None else fallback
        if n > 1 and _level_dependent(slope, spread, level_dep_tol):
            verdict = "LEVEL-DEPENDENT - table model invalid"
        elif abs(mean_res) <= floor:
            verdict = "within seating noise - do not correct"
        elif abs(mean_res) <= materiality:
            verdict = "real but immaterial (< flat-tol/2)"
        else:
            verdict = "CORRECTABLE"
            table["%s/%s" % (unit, ear)]["%g" % freq] = round(-mean_res, 2)
        lines.append("%-6s %-6s %-10s %+10.2f %8.2f %8.2f  %s"
                     % (unit, ear, _fmt_freq(freq), -mean_res, spread, floor,
                        verdict))
    lines.append("")
    lines.append("  'correction' is the dB offset you would ADD to the requested")
    lines.append("  level, i.e. the negated residual. Before adopting any of this,")
    lines.append("  check whether regenerating the inverse filter fixes it instead -")
    lines.append("  a correction table on top of an FIR is two competing models of")
    lines.append("  the same error, and only earns its place if the FIR structurally")
    lines.append("  cannot capture the residual.")
    return dict(table)


def report_hl(rows, retspl, hl_target, lines):
    lines.append("")
    lines.append("=" * 72)
    lines.append("8. dB HL SPOT-CHECK  (open issue M10)")
    lines.append("=" * 72)
    lines.append("  Implied HL = measured SPL - RETSPL(f). For a requested level of")
    lines.append("  X dB SPL the implied HL should equal X - RETSPL(f) exactly;")
    lines.append("  deviation here is the same error as section 2, re-expressed.")
    lines.append("")
    lines.append("%-6s %-6s %-10s %8s %8s %9s %9s %8s"
                 % ("unit", "ear", "freq", "req SPL", "RETSPL", "exp HL",
                    "meas HL", "delta"))
    tonal = sorted([r for r in rows if r["freq_hz"] is not None
                    and r["stim_type"] != "noise"],
                   key=lambda r: (r["unit"], r["ear"], r["freq_hz"],
                                  r["requested_spl"]))
    missing = set()
    for r in tonal:
        key = "%g" % r["freq_hz"]
        if key not in retspl:
            missing.add(key)
            continue
        ref = retspl[key]
        expected = r["requested_spl"] - ref
        measured = r["measured_spl"] - ref
        lines.append("%-6s %-6s %-10s %8.1f %8.1f %9.1f %9.1f %+8.2f"
                     % (r["unit"], r["ear"], _fmt_freq(r["freq_hz"]),
                        r["requested_spl"], ref, expected, measured,
                        measured - expected))
    if missing:
        lines.append("")
        lines.append("  No RETSPL entry for: %s (not in the profile's table -- the"
                     % ", ".join(sorted(missing, key=float)))
        lines.append("  converter must interpolate or refuse; confirm which it does)")
    if hl_target is not None:
        lines.append("")
        lines.append("  Target %.0f dB HL corresponds to these SPL requests:" % hl_target)
        for key in sorted(retspl, key=float):
            lines.append("    %-8s Hz -> %6.1f dB SPL" % (key, hl_target + retspl[key]))


# ======================================================================
# Plots
# ======================================================================

def make_plots(rows, outdir):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    written = []
    for unit in sorted({r["unit"] for r in rows}):
        sub = [r for r in rows if r["unit"] == unit]
        fig, axes = plt.subplots(2, 2, figsize=(13, 9))
        fig.suptitle("PROLACTIN calibration check -- unit %s" % unit,
                     fontsize=13)

        # (a) linearity at the anchor frequency
        ax = axes[0][0]
        anchor = [r for r in sub if r["freq_hz"] is not None
                  and abs(r["freq_hz"] - ANCHOR_HZ) < 1e-6
                  and r["stim_type"] != "noise"]
        for ear, colour in (("left", "tab:blue"), ("right", "tab:red")):
            pts = sorted([r for r in anchor if r["ear"] == ear],
                         key=lambda r: r["requested_spl"])
            if not pts:
                continue
            ax.plot([r["requested_spl"] for r in pts],
                    [r["measured_spl"] for r in pts],
                    "o-", color=colour, label=ear)
        if anchor:
            lo = min(r["requested_spl"] for r in anchor)
            hi = max(r["requested_spl"] for r in anchor)
            ax.plot([lo, hi], [lo, hi], "k--", lw=1, label="unity")
        ax.set_xlabel("Requested (dB SPL)")
        ax.set_ylabel("Measured (dB SPL)")
        ax.set_title("Level linearity @ %g Hz" % ANCHOR_HZ)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)

        # (b) residual vs frequency, one series per level -- the money plot
        ax = axes[0][1]
        tonal = [r for r in sub if r["freq_hz"] is not None
                 and r["stim_type"] != "noise"]
        groups = _group(tonal, ["ear", "requested_spl"])
        # Colour encodes LEVEL, marker and line style encode EAR, so a left/
        # right pair at the same level shares a colour and overlap is obvious.
        levels = sorted({r["requested_spl"] for r in tonal})
        palette = plt.rcParams["axes.prop_cycle"].by_key()["color"]
        level_colour = {lv: palette[i % len(palette)]
                        for i, lv in enumerate(levels)}
        ear_style = {"left": ("o", "-"), "right": ("^", "--")}
        for key in sorted(groups, key=lambda k: (k[0], k[1])):
            ear, level = key
            per_freq = defaultdict(list)
            for r in groups[key]:
                per_freq[r["freq_hz"]].append(r["residual"])
            if len(per_freq) < 2:
                continue
            freqs = sorted(per_freq)
            marker, dash = ear_style.get(ear, ("s", ":"))
            colour = level_colour[level]
            ax.plot(freqs, [float(np.mean(per_freq[f])) for f in freqs],
                    marker=marker, linestyle=dash, color=colour,
                    markerfacecolor="none", markeredgecolor=colour,
                    # markerfacecolor=colour,   # <- solid markers: swap these
                    # markeredgecolor=colour,   #    two lines for the one above
                    label="%s %.0f dB" % (ear, level))
        ax.axhline(0, color="k", lw=1)
        ax.axhspan(-2, 2, color="tab:green", alpha=0.10)
        ax.set_xscale("log")
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("Residual: measured - requested (dB)")
        ax.set_title("Flatness; series overlap => level-independent")
        ax.grid(alpha=0.3, which="both")
        if groups:
            # handlelength must be generous or the centred marker hides the
            # dash pattern and left/right become indistinguishable in the key.
            ax.legend(fontsize=7, ncol=2, handlelength=4.0,
                      markerscale=0.9, columnspacing=1.2)

        # (c) L/R difference vs frequency
        ax = axes[1][0]
        groups = _group(tonal, ["freq_hz", "requested_spl"])
        by_level = defaultdict(list)
        for (freq, level), grp in groups.items():
            left = [r["measured_spl"] for r in grp if r["ear"] == "left"]
            right = [r["measured_spl"] for r in grp if r["ear"] == "right"]
            if left and right:
                by_level[level].append((freq, np.mean(left) - np.mean(right)))
        for level in sorted(by_level):
            pts = sorted(by_level[level])
            ax.plot([p[0] for p in pts], [p[1] for p in pts], "o-",
                    label="%.0f dB" % level)
        ax.axhline(0, color="k", lw=1)
        ax.set_xscale("log")
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("Left - Right (dB)")
        ax.set_title("Channel asymmetry")
        ax.grid(alpha=0.3, which="both")
        if by_level:
            ax.legend(fontsize=7)

        # (d) residual distribution by stimulus type
        ax = axes[1][1]
        types = sorted({r["stim_type"] for r in sub})
        data = [[r["residual"] for r in sub if r["stim_type"] == t]
                for t in types]
        if any(data):
            try:
                ax.boxplot(data, tick_labels=types)
            except TypeError:          # matplotlib < 3.9
                ax.boxplot(data, labels=types)
        ax.axhline(0, color="k", lw=1)
        ax.set_ylabel("Residual (dB)")
        ax.set_title("Residual by stimulus type")
        ax.grid(alpha=0.3, axis="y")

        fig.tight_layout(rect=(0, 0, 1, 0.96))
        path = outdir / ("calibration_check_unit_%s.png" % unit)
        fig.savefig(path, dpi=130)
        plt.close(fig)
        written.append(path)
    return written


# ======================================================================
# Entry point
# ======================================================================

def build_parser():
    p = argparse.ArgumentParser(
        description="Analyse PROLACTIN coupler SPL measurements.")
    p.add_argument("csv", nargs="?", help="Measurement CSV to analyse.")
    p.add_argument("--template", metavar="PATH",
                   help="Write a blank pre-populated CSV and exit.")
    p.add_argument("--unit", default="X",
                   help="Headphone unit id used by --template.")
    p.add_argument("--profile", default="",
                   help="Calibration profile name used by --template.")
    p.add_argument("--linearity-freqs", default=None,
                   help="Comma-separated Hz for the --template linearity "
                        "block (default %s)."
                        % ",".join(str(f) for f in TEMPLATE_LINEARITY_FREQS))
    p.add_argument("--freq-levels", default=None,
                   help="Comma-separated dB SPL for the --template flatness "
                        "block (default %s)."
                        % ",".join(str(v) for v in TEMPLATE_FREQ_LEVELS))
    p.add_argument("--outdir", default=None,
                   help="Directory for PNG plots (omit to skip plotting).")
    p.add_argument("--report", default=None,
                   help="Also write the text report to this path.")
    p.add_argument("--correction", default=None,
                   help="Write the candidate correction table as JSON.")
    p.add_argument("--flat-tol", type=float, default=2.0,
                   help="Flatness tolerance, dB (default 2.0).")
    p.add_argument("--level-tol", type=float, default=1.0,
                   help="Level accuracy tolerance, dB (default 1.0).")
    p.add_argument("--slope-tol", type=float, default=0.01,
                   help="Linearity slope tolerance (default 0.01).")
    p.add_argument("--level-dep-tol", type=float, default=1.0,
                   help="Residual spread across levels above which the "
                        "per-frequency table model is rejected, dB "
                        "(default 1.0).")
    p.add_argument("--materiality", type=float, default=None,
                   help="Deviations at or below this are reported as real but "
                        "not worth correcting (default: flat-tol / 2).")
    p.add_argument("--retspl-config", default=None,
                   help="calibration_config.json, for the dB HL spot-check.")
    p.add_argument("--retspl-profile", default=None,
                   help="Profile name whose RETSPL table to use.")
    p.add_argument("--hl-target", type=float, default=None,
                   help="Also print the SPL requests for this dB HL value.")
    return p


def load_retspl(config_path, profile_name):
    with open(config_path, "r", encoding="utf-8") as handle:
        cfg = json.load(handle)
    profiles = cfg.get("profiles", {})
    lookup = {k.lower(): k for k in profiles}
    key = lookup.get((profile_name or "").lower())
    if key is None:
        raise SystemExit("Profile '%s' not found. Available: %s"
                         % (profile_name, ", ".join(sorted(profiles))))
    retspl = profiles[key].get("retspl")
    if not retspl or not retspl.get("table"):
        raise SystemExit("Profile '%s' has no RETSPL table (SPL-only profile)."
                         % key)
    return {str(k): float(v) for k, v in retspl["table"].items()}


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.template:
        lin = ([float(v) for v in args.linearity_freqs.split(",")]
               if args.linearity_freqs else None)
        lvl = ([float(v) for v in args.freq_levels.split(",")]
               if args.freq_levels else None)
        write_template(args.template, args.unit, args.profile, lin, lvl)
        return 0

    if not args.csv:
        build_parser().print_help()
        return 2

    rows, pending, malformed = load_csv(args.csv)

    lines = []
    lines.append("PROLACTIN calibration check -- %s" % Path(args.csv).name)
    lines.append("%d measured rows, %d still blank, %d malformed"
                 % (len(rows), pending, malformed))
    units = sorted({r["unit"] for r in rows})
    lines.append("Units present: %s" % (", ".join(units) if units else "none"))

    if not rows:
        lines.append("")
        lines.append("Nothing to analyse yet -- fill in the measured_spl column.")
        print("\n".join(lines))
        return 0

    report_linearity(rows, args.slope_tol, args.level_tol, lines)
    report_flatness(rows, args.flat_tol, lines)
    report_level_independence(rows, lines)
    reseat_sd, freq_floors = report_reseat(rows, lines)
    report_asymmetry(rows, lines)
    report_noise_vs_tone(rows, lines)
    table = report_correction(rows, reseat_sd, args.flat_tol,
                              args.level_dep_tol, lines, freq_floors,
                              args.materiality)

    if args.retspl_config:
        retspl = load_retspl(args.retspl_config, args.retspl_profile)
        report_hl(rows, retspl, args.hl_target, lines)

    if args.outdir:
        written = make_plots(rows, args.outdir)
        lines.append("")
        lines.append("Plots written:")
        for path in written:
            lines.append("  %s" % path)

    if args.correction:
        with open(args.correction, "w", encoding="utf-8") as handle:
            json.dump({"_note": "CANDIDATE ONLY -- not wired into "
                                "CalibrationManager. Frequencies in Hz, values "
                                "in dB to ADD to the requested level.",
                       "corrections": table}, handle, indent=2)
        lines.append("")
        lines.append("Candidate correction table -> %s" % args.correction)

    text = "\n".join(lines)
    print(text)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
