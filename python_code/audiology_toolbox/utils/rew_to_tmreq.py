#!/usr/bin/env python3
"""
rew_to_tmreq.py
Convert REW parametric EQ text exports to TotalMix FX Room EQ preset (.tmreq).

Both ears are written into a single file with separate <Room EQ L> and <Room EQ R> sections.

Usage:
    python rew_to_tmreq.py --left left_filters.txt --right right_filters.txt --out headphones.tmreq

    # With per-ear level offset (e.g. if L ear needs -2.5 dB to match R):
    python rew_to_tmreq.py --left left_filters.txt --right right_filters.txt \
        --chan-gain-left -2.5 --out headphones.tmreq

REW export procedure:
    1. Select the LEFT measurement in REW's EQ window
    2. File > Export > Export filter settings as text -> save as left_filters.txt
    3. Repeat for RIGHT -> save as right_filters.txt
    4. Run this script

Level matching (recommended):
    Before exporting, set the same Target Level (dB SPL) for both ears in REW's
    EQ window. Use "Calculate target level from response" on one ear, note the
    value, then manually enter that same value for the other ear. This causes
    REW to embed the level correction into the filter gains. Chan Gain can then
    remain 0.0 dB, or be used for any residual trim.

TotalMix import procedure:
    Open Room EQ on the headphone output channel and import headphones.tmreq.
    TotalMix applies the <Room EQ L> and <Room EQ R> sections to their
    respective sides automatically.
"""

import re
import argparse
from pathlib import Path


# Regex matches lines like:
#   Filter  1: ON  PK       Fc    69.0 Hz  Gain  -6.30 dB  Q  2.15
# Handles optional spaces and sign on gain.
_FILTER_RE = re.compile(
    r'Filter\s+\d+:\s+ON\s+PK\s+Fc\s+([\d.]+)\s+Hz\s+Gain\s+([-+]?[\d.]+)\s+dB\s+Q\s+([\d.]+)',
    re.IGNORECASE
)


def parse_rew_text(filepath):
    """Parse REW 'Export filter settings as text' output.

    Returns a list of dicts {'freq', 'gain', 'q'} for each ON peaking band,
    up to 9 bands.
    """
    bands = []
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            m = _FILTER_RE.search(line)
            if m:
                bands.append({
                    'freq': float(m.group(1)),
                    'gain': float(m.group(2)),
                    'q':    float(m.group(3)),
                })

    if not bands:
        raise ValueError(
            f"No enabled peaking filter lines found in {filepath}.\n"
            "Expected lines like: 'Filter  1: ON  PK  Fc  500 Hz  Gain  -3.00 dB  Q  2.00'"
        )
    if len(bands) > 9:
        print(f"  Warning: {len(bands)} bands found in {filepath}, truncating to 9.")
        bands = bands[:9]

    return bands


def _bands_to_xml_block(bands, channel, chan_gain=0.0):
    """Build the <Room EQ L/R> XML block for up to 9 bands.

    Format follows the SoundID export convention observed in TotalMix forum posts:
    - REQ Band1Type  (no space before Type for band 1)
    - REQ BandN Type (space before Type for bands 2-9)
    - Chan Gain set to 0.00 (SPL calibration handled separately in PROLACTIN)
    - All filter types 0.00 = peaking
    """
    tag = f"Room EQ {channel}"
    lines = [
        f"  <{tag}>",
        "    <Params>",
        '      <val e="REQ Delay" v="0.00,"/>',
    ]

    for i, b in enumerate(bands, start=1):
        lines.append(f'      <val e="REQ Band{i} Freq" v="{b["freq"]:.0f},"/>')
        lines.append(f'      <val e="REQ Band{i} Q"    v="{b["q"]:.2f},"/>')
        lines.append(f'      <val e="REQ Band{i} Gain" v="{b["gain"]:.2f},"/>')

    # Band type entries: band 1 has no space (follows observed SoundID format)
    lines.append('      <val e="REQ Band1Type" v="0.00,"/>')
    for i in range(2, len(bands) + 1):
        lines.append(f'      <val e="REQ Band{i} Type" v="0.00,"/>')

    lines.append(f'      <val e="Chan Gain" v="{chan_gain:.2f},"/>')
    lines.append("    </Params>")
    lines.append(f"  </{tag}>")
    return "\n".join(lines)


def generate_tmreq(left_bands, right_bands, out_path,
                   chan_gain_left=0.0, chan_gain_right=0.0):
    """Write a TotalMix .tmreq file containing both L and R filter sets."""
    l_block = _bands_to_xml_block(left_bands,  "L", chan_gain=chan_gain_left)
    r_block = _bands_to_xml_block(right_bands, "R", chan_gain=chan_gain_right)
    content = (
        "<Preset>\n"
        f"{l_block}\n"
        f"{r_block}\n"
        "</Preset>\n"
    )
    Path(out_path).write_text(content, encoding='utf-8')
    print(f"Written: {out_path}")


def _print_bands(label, bands):
    print(f"\n  {label} ({len(bands)} bands):")
    print(f"  {'Band':>4}  {'Freq (Hz)':>10}  {'Gain (dB)':>10}  {'Q':>6}")
    print(f"  {'-'*4}  {'-'*10}  {'-'*10}  {'-'*6}")
    for i, b in enumerate(bands, start=1):
        print(f"  {i:>4}  {b['freq']:>10.1f}  {b['gain']:>10.2f}  {b['q']:>6.2f}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert REW PEQ text exports to TotalMix .tmreq"
    )
    parser.add_argument("--left",  required=True, metavar="FILE",
                        help="REW text export for left ear")
    parser.add_argument("--right", required=True, metavar="FILE",
                        help="REW text export for right ear")
    parser.add_argument("--out",   required=True, metavar="FILE",
                        help="Output .tmreq path (e.g. headphones.tmreq)")
    parser.add_argument("--chan-gain-left",  type=float, default=0.0, metavar="DB",
                        help="Overall gain offset for left channel in dB (default: 0.0)")
    parser.add_argument("--chan-gain-right", type=float, default=0.0, metavar="DB",
                        help="Overall gain offset for right channel in dB (default: 0.0)")
    args = parser.parse_args()

    print("Parsing REW exports...")
    left_bands  = parse_rew_text(args.left)
    right_bands = parse_rew_text(args.right)

    _print_bands("LEFT",  left_bands)
    _print_bands("RIGHT", right_bands)

    if args.chan_gain_left != 0.0 or args.chan_gain_right != 0.0:
        print(f"\n  Chan Gain: L={args.chan_gain_left:+.2f} dB  R={args.chan_gain_right:+.2f} dB")

    print(f"\nGenerating {args.out} ...")
    generate_tmreq(left_bands, right_bands, args.out,
                   chan_gain_left=args.chan_gain_left,
                   chan_gain_right=args.chan_gain_right)

    print("\nDone. Import the .tmreq file via TotalMix Room EQ on the headphone output channel.")


if __name__ == "__main__":
    main()
