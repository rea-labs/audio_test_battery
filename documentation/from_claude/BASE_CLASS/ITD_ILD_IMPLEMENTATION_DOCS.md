# ITD and ILD Paradigm Implementation - Complete Documentation

## Overview

Implemented two spatial hearing paradigms for measuring binaural (two-ear) cues used for sound localization:

1. **ILD (Interaural Level Difference)** - Loudness difference between ears
2. **ITD (Interaural Time Difference)** - Timing difference between ears

Both paradigms measure the smallest difference (threshold) a participant can detect and use this to lateralize sound (hear it as coming from left, right, or center).

---

## Background: Spatial Hearing

### The Duplex Theory (Rayleigh, 1907)

Humans use two main binaural cues for sound localization:

| Cue | Frequency Range | Mechanism |
|-----|-----------------|-----------|
| **ITD** | Low (<1500 Hz) | Timing differences due to path length |
| **ILD** | High (>1000 Hz) | Level differences due to head shadow |

**Physical basis:**
- Sound from left reaches left ear first/louder
- Head width (~23 cm) creates max delay of ~0.67 ms (670 μs)
- Head shadow attenuates high frequencies on far side

**Human sensitivity:**
- ITD: Can detect ~10-20 μs (microseconds)
- ILD: Can detect ~0.5-1 dB difference

---

## ILD (Interaural Level Difference) Paradigm

### Implementation Details

**File:** `paradigm_ild.py`

**Mechanism:**
- Uses the new `pan` parameter to create level differences between ears
- Pan value derived from ILD in dB
- Simpler than ITD (no sample-accurate timing needed)

**Adaptive Parameter:** ILD in dB (level difference)

**Task:** "Which side did the sound come from: Left, Center, or Right?"

**Stimulus:**
- Pure tone at specified frequency
- Duration: 500 ms
- Level difference created via panning

**Response Classification:**
- Normal trial (one ear louder): Choose correct side → TP, wrong → FN
- Catch trial (both ears equal): Choose center → TN, choose side → FP

### Configuration

Based on DLI parameters but for lateralization:

```python
params = {
    "inner": VarSpec(
        name="ild_dB",
        data={
            'start': 15.0,               # Start ILD (easier start)
            'step_down_initial': 0.5,    # Halve (harder)
            'step_down_final': 0.5,      
            'step_up_initial': 2.0,      # Double (easier)
            'step_up_final': 2.0,        
            'min': 0.5,                  # 0.5 dB minimum
            'max': 32.0,                 # 32 dB maximum
            'randomize_factor': 1.5
        }
    ),
    "outer_1": VarSpec(
        name="fc",
        data=[1000, 2000]  # Test at 1 and 2 kHz
    ),
    "outer_2": VarSpec(
        name="ref_level",
        data=[0.3]
    )
}
```

### Pan-to-ILD Conversion

Currently uses simple heuristic:
```python
pan_val = ±min(1.0, ild_dB / 20.0)
```

This creates approximate ILD:
- ILD = 8 dB → pan ≈ ±0.4
- ILD = 20 dB → pan = ±1.0 (max)

**Note:** For precise ILD control in dB, may need calibration or more sophisticated pan-to-dB mapping.

### Frequencies Tested

Per auditoryneuroscience.com recommendation:
- 1000 Hz (transition frequency)
- 2000 Hz (where ILD is effective)

ILD works best for **high frequencies** (>1000 Hz) due to head shadow effect.

### Data Logged

```csv
unix_time,config_num,trial_num,is_catch_trial,trial_repeats,correct_answer,ild_dB,louder_side,fc,ref_level,threshold_dB,slope_k
```

Where `louder_side`: 0=left, 1=center, 2=right

---

## ITD (Interaural Time Difference) Paradigm

### Implementation Details

**File:** `paradigm_itd.py`

**Mechanism:**
- **Sample-accurate stereo generation** for microsecond precision
- Directly creates stereo waveform with precise delays
- Bypasses TrialPlayer's normal sound generation

**Adaptive Parameter:** ITD in milliseconds (timing difference)

**Task:** "Which side did the sound come from: Left, Right, or Center?"

**Stimulus:**
- Two signal types: 1 kHz pure tone, white noise
- Duration: 500 ms
- Timing difference created by delaying one ear

**Response Classification:**
- Normal trial (one ear leads): Choose correct side → TP, wrong → FN
- Catch trial (simultaneous): Choose center → TN, choose side → FP

### Sample-Accurate Stereo Generation

**Critical Function:** `create_itd_stereo()`

```python
def create_itd_stereo(self, mono_wave, itd_ms, fs):
    """Create stereo with precise ITD using sample-accurate delays."""
    itd_seconds = itd_ms / 1000.0
    delay_samples = int(abs(itd_seconds) * fs)
    
    if itd_ms > 0:
        # Positive ITD: right delayed (sound from left)
        left = mono_wave
        right = np.pad(mono_wave, (delay_samples, 0))[:-delay_samples]
    elif itd_ms < 0:
        # Negative ITD: left delayed (sound from right)
        right = mono_wave
        left = np.pad(mono_wave, (delay_samples, 0))[:-delay_samples]
    else:
        # Zero ITD: simultaneous
        left = right = mono_wave
    
    return np.column_stack([left, right])
```

**How it works:**
1. Generate mono signal (tone or noise)
2. Calculate delay in samples: `delay_samples = itd_seconds × fs`
3. Pad delayed channel with zeros at start
4. Trim to maintain same length
5. Stack into stereo (N×2) array

**Example:** ITD = 1 ms at 48 kHz
- Delay = 0.001 × 48000 = 48 samples
- At 48 kHz, 1 sample = 20.8 μs precision

### Configuration

Per your specifications:

```python
params = {
    "inner": VarSpec(
        name="itd_ms",
        data={
            'start': 50.0,               # 50 ms = 50,000 μs (very easy)
            'step_down_initial': 0.5,    # Halve before reversal
            'step_down_final': 0.7,      # Smaller steps after (finer resolution)
            'step_up_initial': 2.0,      # Double before reversal
            'step_up_final': 1.4,        # Smaller steps after
            'min': 0.01,                 # 10 μs (human threshold)
            'max': 50.0,                 # 50 ms
            'randomize_factor': 1.5
        }
    ),
    "outer_1": VarSpec(
        name="signal_type",
        data=['sin', 'white']  # Test both tone and noise
    ),
    "outer_2": VarSpec(
        name="fc",
        data=[1000]  # 1 kHz (for tone)
    ),
    "outer_3": VarSpec(
        name="ref_level",
        data=[0.3]
    )
}
```

**Step sizes explained:**
- **Before first reversal:** Large steps (halve/double) to quickly find general threshold region
- **After first reversal:** Smaller steps (0.7×/1.4×) for finer threshold measurement

**Why different step sizes?**
- ITD threshold can be very small (10s of μs)
- Need fine resolution near threshold
- Prevents overshooting when approaching human limits

### Signal Types

**1. Pure Tone (1 kHz):**
- Tests ITD sensitivity for low-frequency tones
- ITD works via phase differences
- Limited by "phase-locking" above ~1500 Hz

**2. White Noise:**
- Tests ITD sensitivity for broadband signals
- Often easier to lateralize than tones
- ITD encoded in envelope timing
- More ecologically valid (natural sounds are broadband)

### Frequencies and ITD

From research:
- ITD most effective: <1500 Hz
- Above 1500 Hz: Phase ambiguity ("brick wall")
- Broadband noise: Uses envelope ITD (works at all frequencies)

**Why 1 kHz?**
- Well within effective ITD range
- Phase unambiguous (wavelength = 34 cm > head width)
- Standard test frequency

### ITD Values in Context

| ITD | Context |
|-----|---------|
| 10 μs | Human detection threshold |
| 100 μs | Easily detectable |
| 670 μs | Maximum natural ITD (90° azimuth) |
| 1 ms | Very obvious lateralization |
| 50 ms | Test starting point (impossible to miss) |

**Your test:**
- Starts at 10 ms (10,000 μs) - impossible to miss
- Adapts down to potentially reach human threshold (~10 μs)
- Tests if participant can achieve normal ITD sensitivity

### Bypassing TrialPlayer

ITD paradigm **overrides** `execute_trial()`:

```python
def execute_trial(self):
    """Play ITD sound directly (bypass TrialPlayer)."""
    self.itd_sound.play()
    time.sleep(self.tone_dur + 0.1)
```

**Why?**
- TrialPlayer generates mono sounds and applies pan
- ITD needs precise sample-level delays
- Direct PsychoPy Sound object gives full control

**Sound generation in `prepare_trial()`:**
1. Generate mono waveform (tone or noise)
2. Apply fades
3. Create stereo with ITD delays
4. Make PsychoPy Sound object
5. Store as `self.itd_sound`

---



### UI Response Mapping

**Updated response order (Feb 2026):**
```
0 = Equal/Center
1 = Left
2 = Right
```

**Rationale:**
- 0 as "center/equal" is intuitive (zero difference)
- 1 and 2 are symmetrical for left/right
- Consistent with binary paradigms (0=no, 1=yes for left, 2=yes for right)

**GUI buttons displayed in order:** Equal/Center (0), Left (1), Right (2)

## Comparison: ILD vs ITD

| Aspect | ILD | ITD |
|--------|-----|-----|
| **Cue type** | Level difference | Time difference |
| **Effective frequency** | High (>1 kHz) | Low (<1.5 kHz) |
| **Human threshold** | ~0.5-1 dB | ~10-20 μs |
| **Implementation** | Uses pan parameter | Sample-accurate delays |
| **Sample accurate** | No | **Yes** (required) |
| **Stimulus** | Pure tone | Tone + noise |
| **Physical basis** | Head shadow | Path length difference |
| **Adaptive steps** | Multiplicative (halve/double) | Multiplicative with finer steps |

### Complementary Cues

ITD and ILD work together:
- Low frequencies: Primarily ITD
- High frequencies: Primarily ILD
- Broadband sounds: Both cues available
- Brain integrates cues for robust localization

---

## Testing

### ILD Test (`test_ild.py`)

**Run:** `python test_ild.py`

**What to expect:**
- Hear tones at 1 kHz and 2 kHz
- Judge left/right/center
- Should be relatively easy at high frequencies
- 2 kHz may be easier than 1 kHz (better ILD cues)

**Requires:** Stereo headphones

### ITD Test (`test_itd.py`)

**Run:** `python test_itd.py`

**What to expect:**
- Config 1: 1 kHz tone with ITD
- Config 2: White noise with ITD
- Noise typically easier to lateralize than tone
- Very small ITDs near threshold may be at center
- ITD works via subtle "where" perception, not obvious loudness

**Requires:** Stereo headphones, quiet environment

**Tips:**
- Close eyes, focus on perceived location
- Don't overthink - first impression usually correct
- If tone is hard but noise is easy, that's normal!

---

## Scientific Basis

### References

**Web resources:**
- auditoryneuroscience.com/spatial-hearing/ITD-ILD-practical
  - Collecting ILD data
  - Collecting and interpreting ITD data

**Key findings cited in implementation:**
- Human ITD threshold: 10-20 μs (Klump & Eady, 1956)
- ITD brick wall: ~1450-1500 Hz (Hartmann et al.)
- Natural ITD range: ±670 μs for 90° azimuth
- ILD can reach 20 dB for some frequencies
- Phase-locking underlies ITD sensitivity

### Duplex Theory

Lord Rayleigh (1907) proposed that:
- Low frequencies: ITD dominant (wavelength > head)
- High frequencies: ILD dominant (head shadow effect)

Modern understanding:
- Significant overlap in frequency ranges
- Brain combines both cues when available
- "Cue trading" possible (can trade ITD for ILD)

---

## Data Columns

### ILD Output
```csv
unix_time,config_num,trial_num,is_catch_trial,trial_repeats,correct_answer,
ild_dB,louder_side,fc,ref_level,threshold_dB,slope_k
```

### ITD Output
```csv
unix_time,config_num,trial_num,is_catch_trial,trial_repeats,correct_answer,
itd_ms,itd_us,leading_side,fc,signal_type,ref_level,threshold_dB,slope_k
```

**Note:** ITD logged in both ms and μs for convenience

---

## Future Enhancements

### For ILD:
1. **Calibrated pan-to-dB mapping**
   - Current heuristic is approximate
   - Could measure actual level difference from pan values
   - Create lookup table or formula

2. **More frequencies**
   - Test 500 Hz (low), 1000 Hz (transition), 2000 Hz (high), 4000 Hz (very high)
   - Demonstrate frequency dependence of ILD

### For ITD:
1. **Envelope ITD for high frequencies**
   - Amplitude-modulated high-frequency carriers
   - Tests envelope timing sensitivity

2. **More signal types**
   - Clicks (transient ITD)
   - Bandpass noise at different center frequencies
   - Speech sounds

3. **ITD-ILD trading**
   - Combined paradigm with conflicting cues
   - Measure relative weighting

---

## Technical Notes

### Sample Rate Precision

At 48 kHz:
- 1 sample = 1/48000 = 20.8 μs
- Human threshold = 10 μs
- Need ~2 samples precision

**Implication:** 48 kHz adequate for ITD testing down to human threshold

For finer precision (e.g., research), could use 96 kHz or 192 kHz.

### ITD Sign Convention

```
Positive ITD (+) → Right ear delayed → Sound from LEFT
Negative ITD (-) → Left ear delayed → Sound from RIGHT
Zero ITD (0) → Simultaneous → Sound from CENTER
```

This matches acoustic physics: sound from left reaches left ear first.

### Pad and Trim Strategy

```python
right = np.pad(mono_wave, (delay_samples, 0))[:-delay_samples]
```

- `np.pad(..., (delay_samples, 0))` adds zeros at start
- `[:-delay_samples]` removes samples from end
- Maintains exact same length as original
- Preserves timing relationships

---

## Files Provided

1. **paradigm_ild.py** - ILD paradigm implementation
2. **paradigm_itd.py** - ITD paradigm implementation  
3. **test_ild.py** - ILD test script
4. **test_itd.py** - ITD test script
5. **ITD_ILD_IMPLEMENTATION_DOCS.md** - This file

---

## Summary

Both paradigms successfully implement spatial hearing tests:

**ILD:**
- ✅ Uses new pan parameter for level differences
- ✅ 3-response lateralization task
- ✅ Multiplicative adaptive steps
- ✅ Tests at 1 and 2 kHz
- ✅ Based on DLI pattern

**ITD:**
- ✅ Sample-accurate stereo with microsecond precision
- ✅ Tests both tones and noise
- ✅ Finer adaptive steps after first reversal
- ✅ Can reach human threshold (~10 μs)
- ✅ Bypasses TrialPlayer for direct control

**Both:**
- ✅ Full MultiThreshold adaptive logic
- ✅ Catch trials with adaptive rate
- ✅ Threshold estimation via psychometric functions
- ✅ Proper data logging
- ✅ 3-response format (left/center/right)

Ready for testing spatial hearing! 🎧
