"""
Standard audiometric frequencies used across paradigms.

Ensures consistency between PTA, IFMC, TMC, and other frequency-based tests.

FREQUENCY_SETS provides named sets for use in ThresholdSetupDialog dropdown.
IFMC_DEFAULT_FREQ_SET and TMC_DEFAULT_FREQ_SET define the pre-selected defaults.
"""

# ---------------------------------------------------------------------------
# Individual frequency / ratio / gap lists
# ---------------------------------------------------------------------------

# Standard audiometric frequencies (Hz)  — ISO 389
AUDIOMETRIC_FREQS      = [250, 500, 1000, 2000, 4000, 8000]

# Extended set (includes inter-octave frequencies)
EXTENDED_FREQS         = [250, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000, 8000]

# Subset for quick testing / development
QUICK_TEST_FREQS       = [500, 1000, 2000, 4000]

# IFMC probe frequencies (per Lecluyse 2013) — excludes 250 Hz and 8 kHz
IFMC_PROBE_FREQS       = [500, 1000, 2000, 4000, 6000]

# IFMC masker frequency ratios (fm/fp)
# Per Lecluyse 2013 and Lopez-Poveda et al 2003
IFMC_MASKER_RATIOS     = [0.5, 0.7, 0.9, 1.0, 1.1, 1.3, 1.6]

# TMC gap durations — Lecluyse 2013 original set (seconds)
TMC_GAPS               = [0.020, 0.040, 0.050, 0.060, 0.080]

# TMC gaps for PROLACTIN battery (seconds)
# Source: paradigm_tinnoice_TMC.m (UZH), betweenRuns.variableList1
TMC_PROLACTIN_GAPS     = [0.005, 0.010, 0.020, 0.040]

# TMC probe frequencies for PROLACTIN battery (Hz)
TMC_PROLACTIN_FREQS    = [500, 1000]

# Ultra-fast single-frequency sets for development / debugging
ULTRA_PTA_FREQS        = [500]
ULTRA_IFMC_PROBE_FREQS = [500]
ULTRA_TMC_FREQS        = [500]

# ---------------------------------------------------------------------------
# Named frequency sets for ThresholdSetupDialog dropdown
# ---------------------------------------------------------------------------
# Keys are the human-readable labels shown in the GUI.
# Values are the corresponding frequency lists (Hz).
#
# TODO: Consider folding this into DEFAULTS.py as part of a broader
#       paradigm-defaults dictionary once calibration is implemented.

FREQUENCY_SETS = {
    "IFMC — Lecluyse 2013":       IFMC_PROBE_FREQS,
    "TMC — PROLACTIN":            TMC_PROLACTIN_FREQS,
    "Audiometric — ISO 389":      AUDIOMETRIC_FREQS,
    "Extended audiometric":       EXTENDED_FREQS,
    "Quick test (4 freqs)":       QUICK_TEST_FREQS,
    "Ultra-fast (500 Hz only)":   ULTRA_IFMC_PROBE_FREQS,
}

# Default frequency set keys used by each paradigm's ThresholdSetupDialog.
# Must match a key in FREQUENCY_SETS exactly.
IFMC_DEFAULT_FREQ_SET = "IFMC — Lecluyse 2013"
TMC_DEFAULT_FREQ_SET  = "TMC — PROLACTIN"
