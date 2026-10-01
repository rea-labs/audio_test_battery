"""
HLConverter - dB SPL <-> dB HL conversion for PROLACTIN.

Hearing Level (HL) is dB SPL minus a frequency-dependent reference offset
(RETSPL: Reference Equivalent Threshold Sound Pressure Level). RETSPL is
defined per transducer + coupler combination. This module is agnostic to
the source of the table; it just applies whatever offsets it is given.

    dB HL  = dB SPL - RETSPL(freq)
    dB SPL = dB HL  + RETSPL(freq)

Interpolation between tabulated frequencies is linear on a log-frequency
axis (audiometric convention). Frequencies outside the tabulated range are
linearly extrapolated (on the same log axis) and a warning is emitted -
extrapolation beyond the measured range is not trustworthy.

This module imports nothing from the rest of PROLACTIN (stdlib + numpy
only), so it is safe to import from anywhere without circular-import risk.

Construct it directly from a dict / config block, or from a CSV file:

    conv = HLConverter({125: 45.0, 250: 25.5, ...}, source="ISO 389-1 TDH-39")
    conv = HLConverter.from_csv("retspl_tdh39.csv", source="...")

CSV format (header row required, two columns):
    Freq (Hz), Intensity (0 dB SPL)
    125, 45.0
    250, 25.5
    ...
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Dict, Mapping, Optional, Union

import numpy as np


class HLConverter:
    """
    Convert between dB SPL and dB HL using a RETSPL offset table.

    Parameters
    ----------
    retspl : mapping of {frequency_hz: offset_dB}
        Reference offsets. Keys may be int, float, or numeric strings
        (e.g. "1000"); they are coerced to float. At least one entry is
        required; at least two are required for extrapolation outside the
        tabulated range (with a single point, the offset is treated as a
        frequency-independent constant).
    source : str, optional
        Human-readable provenance label for the table (e.g.
        "ISO 389-1 TDH-39 / IEC 60318-3"). Recorded in CSV headers and
        shown by describe(). Defaults to "unspecified".
    """

    def __init__(self,
                 retspl: Mapping[Union[str, int, float], float],
                 source: Optional[str] = None):
        if retspl is None or len(retspl) == 0:
            raise ValueError("HLConverter requires a non-empty RETSPL table.")

        # Coerce keys to float, sort by frequency, dedupe (last wins + warn).
        pairs: Dict[float, float] = {}
        for k, v in retspl.items():
            fk = float(k)
            if fk in pairs:
                warnings.warn(
                    "HLConverter: duplicate frequency {0:g} Hz in RETSPL "
                    "table; using last value.".format(fk),
                    stacklevel=2,
                )
            pairs[fk] = float(v)

        freqs = np.array(sorted(pairs.keys()), dtype=np.float64)
        offsets = np.array([pairs[f] for f in freqs], dtype=np.float64)

        if np.any(freqs <= 0.0):
            raise ValueError(
                "HLConverter: RETSPL frequencies must be positive "
                "(log-frequency interpolation)."
            )

        self._freqs = freqs
        self._offsets = offsets
        self._log_freqs = np.log10(freqs)
        self.source = source if source else "unspecified"

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_csv(cls,
                 csv_path: Union[str, Path],
                 source: Optional[str] = None) -> "HLConverter":
        """
        Build an HLConverter from a two-column CSV (header row required).

        First column = frequency in Hz, second column = RETSPL offset in dB.
        Lines that are blank or start with '#' are ignored.
        """
        path = Path(csv_path)
        if not path.is_file():
            raise FileNotFoundError("RETSPL CSV not found: {0}".format(path))

        retspl: Dict[float, float] = {}
        with open(path, "r", encoding="utf-8") as f:
            for lineno, raw in enumerate(f, start=1):
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) < 2:
                    continue
                # Skip a header row whose first field is non-numeric.
                try:
                    freq = float(parts[0])
                    offset = float(parts[1])
                except ValueError:
                    if lineno == 1:
                        continue  # header
                    warnings.warn(
                        "HLConverter.from_csv: skipping unparseable line "
                        "{0} in {1!s}: {2!r}".format(lineno, path.name, line),
                        stacklevel=2,
                    )
                    continue
                retspl[freq] = offset

        if source is None:
            source = "CSV: {0}".format(path.name)
        return cls(retspl, source=source)

    # ------------------------------------------------------------------
    # Core: RETSPL lookup with log-frequency interp / extrapolation
    # ------------------------------------------------------------------

    def retspl(self, freq_hz: float) -> float:
        """
        RETSPL offset (dB) at a given frequency.

        In-range: linear interpolation on log10(frequency).
        Out-of-range: linear extrapolation on log10(frequency), with a
        warning. With a single tabulated point, returns that point's
        offset for all frequencies.
        """
        if freq_hz <= 0.0:
            raise ValueError(
                "freq_hz must be positive, got {0!r}".format(freq_hz)
            )

        x = self._log_freqs
        y = self._offsets
        xq = float(np.log10(freq_hz))

        if x.size == 1:
            return float(y[0])

        f_min = float(self._freqs[0])
        f_max = float(self._freqs[-1])

        if xq < x[0]:
            warnings.warn(
                "HLConverter: {0:g} Hz is below the RETSPL table range "
                "({1:g}-{2:g} Hz); extrapolating. HL values here are "
                "unverified.".format(freq_hz, f_min, f_max),
                stacklevel=2,
            )
            slope = (y[1] - y[0]) / (x[1] - x[0])
            return float(y[0] + slope * (xq - x[0]))

        if xq > x[-1]:
            warnings.warn(
                "HLConverter: {0:g} Hz is above the RETSPL table range "
                "({1:g}-{2:g} Hz); extrapolating. HL values here are "
                "unverified.".format(freq_hz, f_min, f_max),
                stacklevel=2,
            )
            slope = (y[-1] - y[-2]) / (x[-1] - x[-2])
            return float(y[-1] + slope * (xq - x[-1]))

        return float(np.interp(xq, x, y))

    # ------------------------------------------------------------------
    # Conversions
    # ------------------------------------------------------------------

    def spl_to_hl(self, db_spl: float, freq_hz: float) -> float:
        """Convert dB SPL to dB HL at a given frequency."""
        return float(db_spl) - self.retspl(freq_hz)

    def hl_to_spl(self, db_hl: float, freq_hz: float) -> float:
        """Convert dB HL to dB SPL at a given frequency."""
        return float(db_hl) + self.retspl(freq_hz)

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    @property
    def freq_range_hz(self) -> "tuple[float, float]":
        """(min, max) tabulated frequency in Hz."""
        return float(self._freqs[0]), float(self._freqs[-1])

    def table(self) -> "list[tuple[float, float]]":
        """The RETSPL table as a sorted list of (freq_hz, offset_dB)."""
        return [(float(f), float(o))
                for f, o in zip(self._freqs, self._offsets)]

    def describe(self) -> str:
        """Multi-line human-readable summary."""
        lines = ["HLConverter (source: {0})".format(self.source),
                 "  freq (Hz)   RETSPL (dB)"]
        for f, o in self.table():
            lines.append("  {0:>9g}   {1:>8.1f}".format(f, o))
        lo, hi = self.freq_range_hz
        lines.append("  range: {0:g}-{1:g} Hz "
                     "(log-freq interp; extrapolation warns)".format(lo, hi))
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Smoke test: python hl_converter.py
# Uses the ISO 389-1 TDH-39 / IEC 60318-3 table (dev placeholder; NOT valid
# for the circumaural DT250 - see session notes).
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _TDH39 = {
        125: 45.0, 250: 25.5, 500: 11.5, 1000: 7.0, 1500: 6.5,
        2000: 9.0, 3000: 10.0, 4000: 9.5, 6000: 15.5, 8000: 13.0,
    }
    conv = HLConverter(_TDH39, source="ISO 389-1 TDH-39 / IEC 60318-3 (dev)")
    print(conv.describe())
    print()

    # Tabulated frequency: exact round-trip.
    for f in (250, 1000, 4000):
        hl = conv.spl_to_hl(60.0, f)
        back = conv.hl_to_spl(hl, f)
        print("  60.0 dB SPL @ {0:>5g} Hz -> {1:6.2f} dB HL "
              "-> {2:6.2f} dB SPL".format(f, hl, back))
    print()

    # Interpolated (non-tabulated, in-range) frequency.
    f = 750
    print("  RETSPL @ {0} Hz (interp): {1:.3f} dB".format(f, conv.retspl(f)))

    # Extrapolated (out-of-range) frequency: expect a warning.
    f = 12000
    print("  RETSPL @ {0} Hz (extrap, warns): {1:.3f} dB"
          .format(f, conv.retspl(f)))
