# IFMC (Iso-Forward Masking Contour) - Complete Implementation Documentation

## Overview

IFMC measures **frequency selectivity** (cochlear tuning) using forward masking. It tracks how much a masker tone at different frequencies is needed to mask a fixed-level, fixed-frequency probe tone.

**Clinical Purpose:** Assess peripheral auditory frequency resolution / cochlear function

**Results:**
- Normal hearing: Sharp V-shaped contour (good frequency selectivity)
- Hearing loss: Broad/flat contour (poor frequency selectivity)

---

## Implementation Confirmed from Documentation

### MultiThreshold/UZH Approach (NOT Prague)

**✅ NO cue tones** - Single-interval yes/no paradigm  
**✅ WITH catch trials** - Per Lecluyse 2013: "One in five trials were catch trials"  
**✅ Random masker order** - "Masker frequencies were presented in random order between runs"  
**✅ Multiple probe frequencies** - Tested at 0.5, 1, 2, 4, 6 kHz (Lecluyse 2013)  

### Key Parameters from Lecluyse 2013

**Masker frequency ratios:**
```
fm/fp = [0.5, 0.7, 0.9, 1.0, 1.1, 1.3, 1.6]
```

**Probe frequencies:**
```
fp = [0.5, 1, 2, 4, 6] kHz (and sometimes 0.25 kHz)
```

**Timing:**
- Masker duration: 108 ms
- Gap: 10 ms
- Probe duration: 16 ms
- Ramps: 4 ms raised-cosine

**Probe level:** Fixed at **10 dB above absolute threshold** for that 16ms probe

---

## Stimulus Structure

```
Time sequence:
[Masker tone 108ms] → [Gap 10ms] → [Probe tone 16ms]
         fm                              fp

Normal trial:  BEEP (masker) ... click (probe)
Catch trial:   BEEP (masker) ... [no probe]
```

**Task:** "Did you hear the probe tone (the short click at the end)?"

---

## Adaptive Logic (REVERSED from typical)

### Standard Threshold Paradigm (e.g., PTA):
```
Heard → Make quieter (easier)
Not heard → Make louder (harder)
```

### IFMC (Masker Adaptation):
```
Probe heard → Masker too weak → INCREASE masker (harder)
Probe not heard → Masker masks probe → DECREASE masker (easier)
```

**Why reversed?**
- We're adapting the MASKER level, not the probe level
- Probe stays fixed
- Goal: Find masker threshold that just masks the probe

---

## Response Classification

### Catch Trials (20% of trials - probe absent):
- Response "No" (0) → **TN** (correct - no probe to hear)
- Response "Yes" (1) → **FP** (false alarm - claimed to hear absent probe)

### Normal Trials (probe present):
- Response "Yes" (1) → **TP** (detected probe)
- Response "No" (0) → **FN** (probe was masked)

**Note:** TP/FN classification tracks probe detection, used for adaptive logic

---

## Adaptive Step Sizes

**Linear steps in dB** (not multiplicative):

```python
Before first reversal:
  step_up = +10 dB   (increase masker)
  step_down = -10 dB (decrease masker)

After first reversal:
  step_up = +2 dB    (finer steps)
  step_down = -2 dB
```

**Midpoint reset:** After first reversal, set to arithmetic mean of last two presented levels

---

## Implementation Details

### Outer Variables

**randomize=True** for masker frequency ratios (per Lecluyse)

```python
"outer_1": VarSpec(
    name="masker_freq_ratio",
    data=[0.5, 0.7, 0.9, 1.0, 1.1, 1.3, 1.6],
    randomize=True  # CRITICAL: Random order
)

"outer_2": VarSpec(
    name="probe_freq",
    data=[500, 1000, 2000, 4000]  # Multiple frequencies
)

"outer_3": VarSpec(
    name="probe_level",
    data=[50]  # User-specified (threshold + 10 dB)
)
```

### Total Configurations

For 4 probe frequencies × 7 masker ratios = **28 configs**

Each config runs adaptive staircase to find masker threshold at that frequency combination.

---

## Expected Results

### Normal Hearing IFMC

```
Masker threshold (dB)
     ^
 80  |
     |           
 60  |        .     
     |      .   .   
 40  |    .       .
     |  .           .
 20  |.               .
     +-------------------→
    0.5  0.7  0.9  1.0  1.1  1.3  1.6
         Masker frequency ratio (fm/fp)
```

**Characteristics:**
- **V-shaped contour**
- Highest threshold at fm = fp (on-frequency masking)
- Sharp drop-off on both sides
- "Depth" = 20-40 dB typical

### Hearing Impaired IFMC

```
Masker threshold (dB)
     ^
 80  |
     |      ___________
 60  |   __/           \__
     | _/                 \_
 40  |/                     \
     |
 20  |
     +-------------------→
    0.5  0.7  0.9  1.0  1.1  1.3  1.6
```

**Characteristics:**
- **Broad, shallow contour**
- Less difference between on- and off-frequency
- "Depth" = 5-15 dB typical
- Poor frequency selectivity

---

## Probe Level Determination

### Current Implementation (User-Specified):

```python
# User must specify probe level
probe_level = 50  # dB SPL (should be threshold + 10 dB)
```

**Requirement:** User must run 16ms absolute threshold test FIRST, then add 10 dB

### Future Implementation:

Could integrate with PTA results:
```python
# Get 16ms threshold from prior test
threshold_16ms = get_threshold_from_pta(freq, duration=16)
probe_level = threshold_16ms + 10
```

---

## Catch Trial Details

Per Lecluyse 2013:

**Rate:** 1 in 5 trials (20%)

**Structure:** Masker + gap, NO probe

**Correct response:** "No" (probe not present)

**Purpose:**
- Detect false alarms (guessing)
- Ensure participant is attending
- Monitor response strategy

**Action on false alarm:**
- In Lecluyse: Run stopped and restarted after instructions
- Our implementation: Continue but monitor false alarm rate

**Special:** Trial 2 is always a catch trial (reminds participant what "no probe" sounds like)

---

## Data Output

```csv
unix_time,config_num,trial_num,is_catch_trial,trial_repeats,correct_answer,
masker_level,masker_freq,masker_freq_ratio,probe_freq,probe_level,
threshold_dB,slope_k
```

**Key measurements per config:**
- Final threshold: Masker level needed to just mask probe
- One threshold per (probe_freq, masker_ratio) combination

---

## Post-Processing

### Plot IFMC Contour:

```python
# For each probe frequency
for fp in [500, 1000, 2000, 4000]:
    # Get thresholds at all masker ratios
    ratios = [0.5, 0.7, 0.9, 1.0, 1.1, 1.3, 1.6]
    thresholds = [get_threshold(fp, ratio) for ratio in ratios]
    
    # Plot
    plt.plot(ratios, thresholds)
    plt.xlabel('Masker frequency ratio (fm/fp)')
    plt.ylabel('Masker threshold (dB SPL)')
```

### Calculate Metrics:

**Depth (dB):**
```python
# Difference between on-frequency and average off-frequency
depth = threshold[fm=fp] - mean([threshold[fm=0.7*fp], threshold[fm=1.3*fp]])
```

**Larger depth = better frequency selectivity**

---

## Clinical Interpretation

### Normal Profile:
- Absolute thresholds: <20 dB HL
- IFMC depth: 20-40 dB
- V-shaped contours at all frequencies

### Hearing Loss Profile:
- Raised absolute thresholds: >20 dB HL
- Reduced IFMC depth: 5-15 dB
- Broad, shallow contours
- Indicates cochlear dysfunction

### Example from Lecluyse 2013:
- Participant #IH75: Equal hearing loss, very shallow IFMCs (poor frequency selectivity)
- Participant #IH14: Equal hearing loss, better IFMCs (better residual selectivity)
- Shows that threshold alone doesn't predict function!

---

## Comparison: MultiThreshold vs Prague

| Feature | MultiThreshold/UZH | Prague (NOT USED) |
|---------|-------------------|-------------------|
| Cue tones | NO cue tones | Cue + test stimuli |
| Task | "Did you hear probe?" | "Count probe tones" |
| Intervals | Single-interval | Two-interval |
| Catch trials | YES (20%) | Implied in counting |
| Complexity | Simpler | More complex |

**We use MultiThreshold/UZH approach**

---

## Implementation Decisions (Confirmed)

1. **✅ Catch trials:** YES (20% rate per Lecluyse)
2. **✅ Probe level:** User-specified (will integrate with PTA later)
3. **✅ Multiple probe frequencies:** YES (500, 1000, 2000, 4000 Hz)
4. **✅ Randomize masker order:** YES (randomize=True on outer variable)

---

## Files Provided

1. **paradigm_ifmc.py** - IFMC paradigm implementation
2. **test_ifmc.py** - Test script with user instructions
3. **IFMC_IMPLEMENTATION_DOCS.md** - This file

---

## Usage Example

```python
from paradigms.paradigm_ifmc import ParadigmIFMC
from utils.varspec import VarSpec

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
            'max': 100
        }
    ),
    "outer_1": VarSpec(
        name="masker_freq_ratio",
        data=[0.5, 0.7, 0.9, 1.0, 1.1, 1.3, 1.6],
        randomize=True  # Random order
    ),
    "outer_2": VarSpec(
        name="probe_freq",
        data=[1000, 2000, 4000]
    ),
    "outer_3": VarSpec(
        name="probe_level",
        data=[50]  # User must set appropriately
    )
}

ifmc = ParadigmIFMC(params, verbose=True)
ifmc.main()
```

---

## Key Takeaways

**IFMC measures frequency selectivity**, not just threshold

**Reversed adaptive logic:** Probe heard → increase masker (opposite of PTA)

**V-shaped = normal**, flat = hearing loss

**Critical:** Probe level must be threshold + 10 dB

**Random order** for masker frequencies (important for unbiased results)

**Catch trials** monitor attention and false alarms

Ready for testing! 🎯


## IMPORTANT: Probe Level in Amplitude (NOT dB)

**For safety and simplicity**, probe level is specified as **amplitude (0-1)**, NOT dB SPL.

### Recommended Values:
- **0.3-0.5** - Typical safe range
- **0.4** - Default (clearly audible but not loud)

### Why Amplitude Instead of dB?
1. **Safety** - Prevents accidentally setting super loud levels
2. **Simplicity** - No calibration needed for initial testing
3. **Direct control** - Amplitude directly controls sound level

### Research Standard:
In formal research (e.g., Lecluyse 2013), probe level is set to:
- **Threshold + 10 dB** (in dB SPL)
- Requires calibrated system and prior threshold measurement

### Future Enhancement:
When integrated with PTA results:
```python
# Get 16ms threshold from PTA
threshold_16ms = get_threshold_from_pta(probe_freq, duration=16)
probe_level = amplitude_from_db(threshold_16ms + 10)
```

---

## Config Randomization

Masker frequency ratios are **randomized** per Lecluyse 2013.

**Implementation:**
- Configs shuffled in `__init__()` using `random.shuffle()`
- Each run presents masker ratios in random order
- Prevents order effects and bias

**Note:** VarSpec doesn't support `randomize` parameter - shuffling happens in paradigm class.
