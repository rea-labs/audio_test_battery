
from dataclasses import dataclass, field

# -----------------------------------------------------------
# VarSpec container
# -----------------------------------------------------------
@dataclass
class VarSpec:
    """
    A simple container:
        name  : the attribute name the paradigm code will use
        data  : the list of values to iterate over
        label : human-readable name for display (axis labels, legends)
        units : physical unit string for display

    Display metadata (label / units) is OPTIONAL and additive. Both default
    to "", and every consumer must tolerate them being empty or absent
    (see axis_label() below). Paradigm/adaptive logic never reads them.

    IMPORTANT: `units` is a LABEL ONLY, never a conversion instruction.
    It must describe the unit the values are ALREADY stored in. E.g.
    gap_duration is stored in seconds, so it declares units="s" -- declaring
    units="ms" would mislabel the axis by 1000x. Any paradigm whose stored
    unit differs from its desired display unit must scale explicitly at the
    call site; scaling must NOT be inferred from this field.
    """
    name: str = ""
    data: list = field(default_factory=list) 
    # FYI - https://stackoverflow.com/questions/53632152/why-cant-dataclasses-have-mutable-defaults-in-their-class-attributes-declaratio
    label: str = ""   # human-readable axis label; falls back to name
    units: str = ""   # "dB SPL" | "Hz" | "ms" | "s" | "%" | "" (dimensionless)

    def print_all(self):
        for k,v in self.__dict__.items():
            print(f"{str(k)} = {str(v)}")


# -----------------------------------------------------------
# Display helpers
# -----------------------------------------------------------
def axis_label(vs, units_override=None) -> str:
    """
    Build a display string for a VarSpec: 'Frequency (Hz)',
    'Modulation Index (%)', 'Masker/Probe Frequency Ratio', 'trial_amp'.

    Falls back progressively and NEVER raises: a missing/empty `label`
    falls back to `name`; a missing/empty `units` yields no parenthetical;
    anything unusable yields "". Uses getattr() rather than bare attribute
    access so an older or duck-typed VarSpec cannot break a GUI redraw.

    Args:
        vs: a VarSpec (or any object exposing name / label / units)
        units_override: display unit to use INSTEAD of vs.units. Only for
            callers that have actually converted the values away from their
            stored unit -- e.g. the operator GUI's dB SPL -> dB HL path,
            where trial_amp is stored (and declared) in dB SPL but drawn in
            dB HL. Never a way to relabel unconverted data: the override
            must describe the numbers being plotted. Pass None (default) to
            use the VarSpec's own declared unit.

    Returns:
        str: display label, possibly empty.
    """
    try:
        text = str(getattr(vs, 'label', '') or getattr(vs, 'name', '') or '')
        unit = str(getattr(vs, 'units', '') or '')
    except Exception:
        return ""
    if units_override is not None:
        unit = str(units_override or '')
    if not text:
        return ""
    return f"{text} ({unit})" if unit else text
