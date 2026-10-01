"""
Test script for IFMC (Iso-Forward Masking Contour) paradigm.

Run order:
  1. test_pta.py   (generates PTA thresholds used to set probe level)
  2. test_ifmc.py  (this script)

Participant ID entry, frequency set selection, and threshold loading/editing
are all handled by ThresholdSetupDialog before the paradigm object is created.
"""

from pathlib import Path

from paradigms.paradigm_ifmc import ParadigmIFMC
from utils.varspec import VarSpec
from utils.calibration import CalibrationManager
from utils.paradigm_setup_dialog import ThresholdSetupDialog
from utils.standard_frequencies import (
    IFMC_MASKER_RATIOS,
    IFMC_DEFAULT_FREQ_SET,
)

# Path to the calibration config. Currently two directory levels up because
# calibration_data/ lives outside audiology_toolbox/. Update when the folder
# is moved into the toolbox (will become "calibration_data/calibration_config.json").
CALIBRATION_CONFIG_PATH = Path(__file__).resolve().parent / "../../calibration_data/calibration_config.json"


def main():
    print("=" * 70)
    print(" IFMC - FREQUENCY SELECTIVITY TEST")
    print("=" * 70)

    # Load calibration up front -- IFMC requires it (raises RuntimeError if
    # missing or partial). Loading here also covers demo trial playback
    # initiated by the setup dialog below.
    try:
        calibration = CalibrationManager(CALIBRATION_CONFIG_PATH)
    except Exception as e:
        print(f"\n!!! Failed to load calibration from {CALIBRATION_CONFIG_PATH}")
        print(f"!!! {type(e).__name__}: {e}")
        print("!!! IFMC requires a populated calibration_config.json with valid")
        print("!!! SPL calibration data. Aborting.")
        return
    if not calibration.spl_calibrated:
        print("\n!!! Calibration loaded but SPL data is null. Populate")
        print("!!! reference_amplitude / measured_spl_left / measured_spl_right")
        print("!!! in calibration_config.json before running IFMC. Aborting.")
        return
    if not calibration.fir_calibrated:
        print("\n!!! Warning: FIR inverse filters are not loaded. IFMC will run")
        print("!!! with SPL calibration only (no headphone frequency correction).")

    # Base params (probe_freq and probe_level filled in after dialog)
    params = {
        "inner": VarSpec(
            name="masker_level",
            label="Masker Level",
            units="dB SPL",
            data={
                "start":             20.0,
                "step_down_initial": -10,
                "step_down_final":   -2,
                "step_up_initial":   10,
                "step_up_final":     2,
                "min":               0,
                "max":               100,
            }
        ),
        "outer_1": VarSpec(name="masker_freq_ratio", data=IFMC_MASKER_RATIOS, label="Masker/Probe Frequency Ratio"),
        "outer_2": VarSpec(name="probe_freq",  data=[1000], label="Probe Frequency", units="Hz"),   # dummy for demo — overwritten by threshold data
    }

    ifmc = ParadigmIFMC(params, verbose=True)
    ifmc.set_calibration(calibration)

    dialog = ThresholdSetupDialog(
        paradigm_name="IFMC",
        params=params,
        paradigm=ifmc,
        default_freq_set_key=IFMC_DEFAULT_FREQ_SET,
        # NOTE: 24 dB SL is a transitional value to compensate for temporal
        # integration. PTA uses 500 ms tones; IFMC/TMC probe is 16 ms,
        # which has a higher detection threshold by ~10-15 dB. The Lecluyse
        # 2013 / MultiThreshold convention is "10 dB above the probe's OWN
        # threshold" (i.e. 16 ms threshold), but PROLACTIN currently lacks
        # a 16 ms PTA pretest. TODO: implement abs_threshold_16 paradigm
        # and revert this to db_above_threshold=10. See session changelog
        # 2026-05-01 for full discussion.
        db_above_threshold=24.0,
        max_amplitude=0.7,
        calibration=calibration,
    )
    participant_id, thresholds = dialog.show()

    if participant_id is None or not thresholds:
        print("\nSetup cancelled or no thresholds entered. Exiting.")
        return

    # The setup dialog owns the calibration for this run -- the operator may
    # have selected a different headphone profile from its dropdown. Re-read
    # it here so the run uses the chosen profile, not the startup default.
    calibration = dialog.selected_calibration

    # Build frequency list from dialog output
    test_freqs   = sorted(thresholds.keys())

    print(f"\nParticipant : {participant_id}")
    print(f"Frequencies : {test_freqs} Hz")
    for f in test_freqs:
        t = thresholds[f]
        print(f"  {f} Hz: {t['threshold_dB']:.1f} dB PTA -> {t['probe_amp']:.4f} amplitude")

    # Update params with confirmed values and re-init paradigm
    params["outer_2"].data = test_freqs

    ifmc = ParadigmIFMC(params, verbose=True, participant_id=participant_id)
    ifmc.set_calibration(calibration)
    # probe_level is derived from probe_freq, not swept as an outer var.
    ifmc.set_probe_levels({f: thresholds[f]["probe_amp"] for f in test_freqs})
    # Pass the dialog's setup metadata (db_above_threshold, max_amplitude,
    # source CSV) so it gets recorded in the CSV header.
    ifmc.set_session_metadata(dialog.setup_summary)

    # --- DEBUG: per-trial resource logging ("Test 2": memory-leak check) ---
    # Writes {participant}_IFMC_resource.csv alongside the results. Set
    # resource_logging = False to disable. resource_scan_every = 0 logs only
    # RSS/handles (zero overhead); set to e.g. 10 for a follow-up run that also
    # counts live Sound/ndarray objects every 10th trial ("what is leaking").
    ifmc.resource_logging = True
    ifmc.resource_scan_every = 0

    # # --- TEMP crash-handler smoke test. DELETE after verifying. ---
    # _orig_log = ifmc.log_data
    # def _boom():
    #     _orig_log()
    #     if ifmc.trial_num >= 5:
    #         raise RuntimeError("crash-handler smoke test")
    # ifmc.log_data = _boom
    # # --- END TEMP TEST ---

    print(f"\nTotal runs : {ifmc.total_num_configs}"
          f"  ({len(test_freqs)} freq x {len(IFMC_MASKER_RATIOS)} ratios)")

    try:
        ifmc.main()
        print(f"\n>>> Results saved: {participant_id}_IFMC_*.csv")
    except KeyboardInterrupt:
        print("\nTest aborted by user.")
    except Exception as e:
        print(f"\n!!! Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
