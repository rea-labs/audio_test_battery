"""
Test script for pan (L/R panning) functionality

Tests the new stereo control in trial_player and event_gen
"""

from trial_player import TrialPlayer
import time

def main():
    print("=" * 70)
    print(" STEREO PAN TEST")
    print("=" * 70)
    print("\nMake sure you're wearing HEADPHONES to hear the stereo effect!")
    print("\nThis will play 5 test tones with different pan settings:")
    print("  1. Center (pan=0)  - should sound centered")
    print("  2. Full Left (pan=-1) - should hear ONLY in left ear")
    print("  3. Full Right (pan=1) - should hear ONLY in right ear")
    print("  4. Favor Left (pan=-0.5) - louder in left")
    print("  5. Favor Right (pan=0.5) - louder in right")
    
    input("\nPress ENTER to start test...")
    
    tp = TrialPlayer()
    
    # Test 1: Center
    print("\n1. Playing CENTER (pan=0)...")
    tp.new_trial(
        wave_type="sin",
        fc=1000,
        durations=1.0,
        amp=0.3,
        pan=0,
        play_now=True
    )
    time.sleep(0.5)
    
    # Test 2: Full Left
    print("2. Playing FULL LEFT (pan=-1)...")
    tp.new_trial(
        wave_type="sin",
        fc=1000,
        durations=1.0,
        amp=0.3,
        pan=-1,
        play_now=True
    )
    time.sleep(0.5)
    
    # Test 3: Full Right
    print("3. Playing FULL RIGHT (pan=1)...")
    tp.new_trial(
        wave_type="sin",
        fc=1000,
        durations=1.0,
        amp=0.3,
        pan=1,
        play_now=True
    )
    time.sleep(0.5)
    
    # Test 4: Favor Left
    print("4. Playing FAVOR LEFT (pan=-0.5)...")
    tp.new_trial(
        wave_type="sin",
        fc=1000,
        durations=1.0,
        amp=0.3,
        pan=-0.5,
        play_now=True
    )
    time.sleep(0.5)
    
    # Test 5: Favor Right
    print("5. Playing FAVOR RIGHT (pan=0.5)...")
    tp.new_trial(
        wave_type="sin",
        fc=1000,
        durations=1.0,
        amp=0.3,
        pan=0.5,
        play_now=True
    )
    time.sleep(0.5)
    
    # Test 6: Multiple events with different pans
    print("\n6. Playing SEQUENCE: Left -> Center -> Right")
    tp.new_trial(
        wave_type=["sin", "sin", "sin"],
        fc=1000,
        durations=0.3,
        del_times=0.1,
        amp=0.3,
        pan=[-1, 0, 1],  # Array of pan values
        play_now=True
    )
    time.sleep(0.5)
    
    print("\n" + "=" * 70)
    print("Test complete!")
    print("\nIf you heard:")
    print("  - Test 2 only in LEFT ear")
    print("  - Test 3 only in RIGHT ear")
    print("  - Test 6 moving from left → center → right")
    print("Then stereo panning is working correctly!")
    print("=" * 70)


if __name__ == "__main__":
    main()
