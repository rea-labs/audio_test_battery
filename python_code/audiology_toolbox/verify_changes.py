#!/usr/bin/env python3
"""
Verification script to check that all changes were applied correctly.

Run this to verify:
1. All paradigms have paradigm_code set
2. Filename format works correctly
3. ResultLoader can be imported
4. Standard frequencies are available
"""

import sys
from pathlib import Path

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from utils.result_loader import ResultLoader, get_pta_threshold
        print("  ✓ ResultLoader imported")
    except Exception as e:
        print(f"  ✗ ResultLoader import failed: {e}")
        return False
    
    try:
        from utils.standard_frequencies import AUDIOMETRIC_FREQS, IFMC_PROBE_FREQS
        print("  ✓ Standard frequencies imported")
    except Exception as e:
        print(f"  ✗ Standard frequencies import failed: {e}")
        return False
    
    return True

def test_paradigm_codes():
    """Test that all paradigms have paradigm_code set."""
    print("\nTesting paradigm codes...")
    
    paradigms = [
        ('paradigms.paradigm_pta', 'ParadigmPTA', 'PTA'),
        ('paradigms.paradigm_fm', 'ParadigmFM', 'FM'),
        ('paradigms.paradigm_am', 'ParadigmAM', 'AM'),
        ('paradigms.paradigm_gap', 'ParadigmGAP', 'GAP'),
        ('paradigms.paradigm_dli', 'ParadigmDLI', 'DLI'),
        ('paradigms.paradigm_ild', 'ParadigmILD', 'ILD'),
        ('paradigms.paradigm_itd', 'ParadigmITD', 'ITD'),
        ('paradigms.paradigm_ifmc', 'ParadigmIFMC', 'IFMC'),
    ]
    
    all_ok = True
    
    for module_name, class_name, expected_code in paradigms:
        try:
            # Import the module
            module = __import__(module_name, fromlist=[class_name])
            ParadigmClass = getattr(module, class_name)
            
            # Create minimal params
            from utils.varspec import VarSpec
            params = {
                "inner": VarSpec(name="test", data={'start': 0.5}),
            }
            
            # Try to create instance
            instance = ParadigmClass(params, participant_id="TEST")
            
            # Check paradigm_code
            if hasattr(instance, 'paradigm_code') and instance.paradigm_code == expected_code:
                print(f"  ✓ {class_name}: paradigm_code = '{instance.paradigm_code}'")
            else:
                actual = getattr(instance, 'paradigm_code', None)
                print(f"  ✗ {class_name}: Expected '{expected_code}', got '{actual}'")
                all_ok = False
                
        except Exception as e:
            print(f"  ✗ {class_name}: Error - {e}")
            all_ok = False
    
    return all_ok

def test_participant_id():
    """Test that participant_id parameter works."""
    print("\nTesting participant_id parameter...")
    
    try:
        from paradigms.paradigm_pta import ParadigmPTA
        from utils.varspec import VarSpec
        
        params = {
            "inner": VarSpec(name="trial_amp", data={'start': 0.5}),
        }
        
        pta = ParadigmPTA(params, participant_id="P999")
        
        if pta.participant_id == "P999":
            print(f"  ✓ participant_id set correctly: {pta.participant_id}")
            return True
        else:
            print(f"  ✗ participant_id incorrect: {pta.participant_id}")
            return False
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_filename_format():
    """Test that filename format is correct."""
    print("\nTesting filename format...")
    
    try:
        from paradigms.paradigm_pta import ParadigmPTA
        from utils.varspec import VarSpec
        import pandas as pd
        
        params = {
            "inner": VarSpec(name="trial_amp", data={'start': 0.5}),
        }
        
        pta = ParadigmPTA(params, participant_id="PTEST")
        
        # Create minimal data
        pta.data = pd.DataFrame({'test': [1, 2, 3]})
        
        # Call write_data_to_disk
        filename = pta.write_data_to_disk()
        
        # Check format
        expected_pattern = "PTEST_PTA_"
        if expected_pattern in str(filename):
            print(f"  ✓ Filename format correct: {filename.name}")
            
            # Clean up test file
            if filename.exists():
                filename.unlink()
                print(f"  ✓ Test file cleaned up")
            
            return True
        else:
            print(f"  ✗ Filename format incorrect: {filename.name}")
            return False
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all verification tests."""
    print("=" * 60)
    print("VERIFICATION TESTS")
    print("=" * 60)
    
    results = {
        'imports': test_imports(),
        'paradigm_codes': test_paradigm_codes(),
        'participant_id': test_participant_id(),
        'filename_format': test_filename_format(),
    }
    
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    
    for test, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED!")
        print("\nYou can now:")
        print("  1. Run paradigms with participant IDs")
        print("  2. Use ResultLoader to load previous results")
        print("  3. Use standard frequencies in configurations")
        print("=" * 60)
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        print("\nPlease check the errors above and fix them.")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
