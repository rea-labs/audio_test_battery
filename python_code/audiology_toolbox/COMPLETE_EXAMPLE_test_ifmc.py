"""
Complete Example: test_ifmc.py with participant ID prompt and manual threshold entry

This shows:
1. How to prompt for participant ID
2. How manual threshold entry works
3. Complete IFMC workflow
"""

from paradigms.paradigm_ifmc import ParadigmIFMC
from utils.varspec import VarSpec
from utils.result_loader import ResultLoader
from utils.standard_frequencies import IFMC_PROBE_FREQS, IFMC_MASKER_RATIOS


def get_participant_id(default="P001"):
    """Prompt user for participant ID with validation."""
    while True:
        pid = input(f"\nEnter Participant ID [{default}]: ").strip()
        
        if not pid:
            pid = default
            print(f"Using default: {pid}")
            return pid
        
        # Basic validation
        if len(pid) < 2:
            print("⚠ Participant ID too short. Please use at least 2 characters.")
            continue
        
        return pid


def main():
    print("=" * 70)
    print(" IFMC - FREQUENCY SELECTIVITY TEST")
    print("=" * 70)
    
    # STEP 1: Get participant ID
    participant_id = get_participant_id(default="P001")
    print(f"\nRunning IFMC for participant: {participant_id}")
    
    # STEP 2: Try to load PTA thresholds (with manual entry option)
    print("\nLooking for PTA results...")
    loader = ResultLoader()
    
    # allow_manual_entry=True means if no file found, user will be prompted
    thresholds = loader.get_pta_thresholds(
        participant_id, 
        IFMC_PROBE_FREQS,
        show_gui=True,           # Show GUI file picker if files exist
        allow_manual_entry=True   # Offer manual entry if no files
    )
    
    # STEP 3: Configure IFMC based on available thresholds
    if thresholds:
        print(f"\n✓ Thresholds available for {len(thresholds)} frequencies")
        
        # Calculate safe probe levels
        probe_levels = []
        test_freqs = []
        
        for freq in IFMC_PROBE_FREQS:
            if freq in thresholds:
                probe_amp = loader.get_ifmc_probe_level(participant_id, freq)
                probe_levels.append(probe_amp)
                test_freqs.append(freq)
                print(f"  {freq} Hz: {thresholds[freq]:.1f} dB threshold → {probe_amp:.3f} amplitude probe")
            else:
                print(f"  {freq} Hz: No threshold available, skipping")
        
        if not test_freqs:
            print("\n⚠ No valid frequencies to test. Exiting.")
            return
    
    else:
        # No thresholds (user cancelled manual entry or declined)
        print(f"\n⚠ No thresholds available for {participant_id}")
        print("Cannot run IFMC without probe levels.")
        print("\nOptions:")
        print("  1. Run PTA first for this participant")
        print("  2. Restart and enter thresholds manually when prompted")
        return
    
    # STEP 4: Configure IFMC paradigm
    params = {
        "inner": VarSpec(
            name="masker_level",
            data={
                'start': 20.0,
                'step_down_initial': -10,
                'step_down_final': -2,
                'step_up_initial': 10,
                'step_up_final': 2,
                'min': 0,
                'max': 100,
                'randomize_factor': 1.2
            }
        ),
        "outer_1": VarSpec(
            name="masker_freq_ratio",
            data=IFMC_MASKER_RATIOS
        ),
        "outer_2": VarSpec(
            name="probe_freq",
            data=test_freqs
        ),
        "outer_3": VarSpec(
            name="probe_level",
            data=probe_levels
        )
    }
    
    gui_config = {
        'question': "Did you hear the PROBE tone (short click at the end)?",
        'options': ['No (0)', 'Yes (1)'],
        'keys': ['0', '1'],
        'window_title': "IFMC Test - Frequency Selectivity",
        'font_size': 14
    }
    
    # STEP 5: Create and run paradigm
    ifmc = ParadigmIFMC(params, 
                        verbose=True, 
                        gui_config=gui_config,
                        participant_id=participant_id)
    
    print(f"\n{'='*70}")
    print(f"TEST CONFIGURATION:")
    print(f"  Participant: {participant_id}")
    print(f"  Probe frequencies: {test_freqs}")
    print(f"  Masker ratios: {IFMC_MASKER_RATIOS}")
    print(f"  Total configs: {ifmc.total_num_configs}")
    print(f"{'='*70}")
    
    input("\nPress ENTER to start test...")
    
    try:
        ifmc.main()
        print("\n>>> Test completed successfully!")
        print(f"Results saved: {participant_id}_IFMC_*.csv")
        
    except KeyboardInterrupt:
        print("\n\n!!! Test aborted by user")
    
    except Exception as e:
        print(f"\n!!! Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


"""
WORKFLOW EXAMPLES:

Scenario 1: PTA file exists
-----------------------------
1. User enters participant ID: P001
2. GUI shows PTA file selection (most recent auto-selected)
3. User clicks "Accept"
4. Thresholds loaded from file
5. IFMC runs with calculated probe levels

Scenario 2: No PTA file, manual entry
--------------------------------------
1. User enters participant ID: P002
2. No PTA file found
3. Dialog: "No PTA results found. Enter thresholds manually?"
4. User clicks "Yes"
5. GUI shows threshold entry form
6. User enters threshold for each frequency:
   - 500 Hz: 25 dB
   - 1000 Hz: 20 dB
   - 2000 Hz: 18 dB
   - 4000 Hz: 30 dB
   - 6000 Hz: 35 dB
7. User clicks "Submit"
8. IFMC runs with calculated probe levels

Scenario 3: No PTA file, decline manual entry
----------------------------------------------
1. User enters participant ID: P003
2. No PTA file found
3. Dialog: "No PTA results found. Enter thresholds manually?"
4. User clicks "No"
5. Program exits with message to run PTA first

Scenario 4: Cancel manual entry
--------------------------------
1. User enters participant ID: P004
2. No PTA file found  
3. User clicks "Yes" to manual entry
4. Threshold entry form appears
5. User realizes they don't have the data
6. User clicks "Cancel"
7. Program exits gracefully
"""
