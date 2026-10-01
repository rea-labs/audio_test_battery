# PROLACTIN Human Test Protocols — Printable Checklists

*Print one copy per paradigm/session. Fill in by hand during testing.*

---

## H1 — Audio Quality Spot-Check

*~5 min per paradigm. Run demo mode, listen at low/mid/high parameter values.*

```
Paradigm: _______________    Tester: _______________    Date: ___________

ONSET/OFFSET
  [ ] No clicks or pops at stimulus start
  [ ] No clicks or pops at stimulus end
  [ ] Fades (ramp in/out) smooth

SIGNAL TYPE (check expected type for this paradigm)
  [ ] PTA:  pure tone
  [ ] GAP:  white noise with silent gap
  [ ] AM:   tone with volume fluctuation
  [ ] FM:   tone with pitch fluctuation
  [ ] DLI:  two sequential tones, one louder
  [ ] ILD:  tone louder in one ear
  [ ] ITD:  tone/noise shifted to one side
  [ ] IFMC: masker -> gap -> probe tone
  [ ] TMC:  masker -> gap -> probe tone
  [ ] LDL:  pure tone, ascending volume

PARAMETER RANGE
  [ ] Demo at LOW value:  stimulus barely perceptible
  [ ] Demo at MID value:  moderate
  [ ] Demo at HIGH value: clearly perceptible

CATCH TRIAL
  [ ] Catch trial is silent (or masker-only for IFMC/TMC)

SPATIAL / FREQUENCY
  [ ] Frequency sounds correct when changed
  [ ] Panning works (L ear / R ear / both) where applicable

PARADIGM-SPECIFIC (check applicable)
  [ ] AM:   at 50% mod depth, fluctuation obvious; at 5%, barely there
  [ ] FM:   pitch wobble audible (confirm it's pitch, not volume)
  [ ] DLI:  both tones same frequency, one clearly louder
  [ ] IFMC: masker -> gap -> probe structure clearly audible
  [ ] LDL:  gets louder each trial; comfortable -> loud -> uncomfortable

NOTES:



RESULT:  [ ] PASS    [ ] FAIL    [ ] NEEDS FOLLOW-UP
```

---

## H2 — Adaptive Tracking Verification

*~10 min per paradigm. Watch operator display while responding strategically.*

```
Paradigm: _______________    Tester: _______________    Date: ___________

PHASE 1: FORCED DESCENT (respond "Yes" to everything for 5-8 trials)
  [ ] Track descends on each step
  [ ] Steps are LARGE before any reversal
  [ ] FP warning appears when you say "Yes" to a catch trial
  [ ] FP marker visible on operator display
  [ ] Track does NOT reverse on false positive

PHASE 2: FORCE FIRST REVERSAL (respond "No" to next normal trial)
  [ ] Reversal detected (marker on plot)
  [ ] Track resets to midpoint of last two levels
  [ ] Steps switch to SMALL after reversal
  [ ] Trial countdown starts (visible in info panel)

PHASE 3: OSCILLATE (alternate Yes/No for ~8 trials)
  [ ] Track oscillates around a stable level
  [ ] Multiple reversals accumulate
  [ ] Countdown decrements on each non-catch trial
  [ ] Catch trials do NOT decrement countdown

PHASE 4: COMPLETION (let countdown reach 0)
  [ ] Config ends when countdown hits 0
  [ ] Threshold estimate appears (console + operator display)
  [ ] Next config starts with fresh track
  [ ] Previous threshold appears in "Previous Thresholds" plot
  [ ] Psychometric function plot updates

NOTES:



RESULT:  [ ] PASS    [ ] FAIL    [ ] NEEDS FOLLOW-UP
```

---

## H3 — Participant GUI / UX

*~5 min per paradigm. Act as a naive participant.*

```
Paradigm: _______________    Tester: _______________    Date: ___________

SETUP DIALOG
  [ ] Participant ID field clear and editable
  [ ] Parameter summary readable
  [ ] Demo button works; stimulus plays
  [ ] Accept / Cancel buttons work
  [ ] Enter confirms; Escape cancels
  [ ] Freq set dropdown works (if applicable)

DURING TEST
  [ ] Question text clear and appropriate
  [ ] Button labels match the task
  [ ] Buttons large enough to click
  [ ] Keyboard shortcuts work (0/1/etc.)
  [ ] "Playing stimulus..." shown during playback
  [ ] Buttons DISABLED during playback
  [ ] Buttons ENABLED after playback
  [ ] Repeat button works
  [ ] No double-click issues

FALSE POSITIVE WARNING
  [ ] Warning appears on catch trial FP
  [ ] Warning text readable
  [ ] Warning clears after ~2 seconds
  [ ] Test continues normally after

GENERAL
  [ ] Window stays on top
  [ ] No freezing or lag
  [ ] Font readable at arm's length

UX FRICTION POINTS:




RESULT:  [ ] PASS    [ ] FAIL    [ ] NEEDS FOLLOW-UP
```

---

## H4 — Operator GUI / UX

*~15 min total. Run 2-3 paradigms with honest responses.*

```
Paradigm(s): _______________    Tester: _______________    Date: ___________

PANEL 1 — STIMULUS WAVEFORM
  [ ] Updates each trial
  [ ] Correct shape (tone / noise / masker+probe)
  [ ] Catch trial shows silence
  [ ] Axis labels present

PANEL 2 — ADAPTIVE TRACK
  [ ] New point plotted each trial
  [ ] Y-axis values make sense
  [ ] Reversal points marked
  [ ] Midpoint reset visible after first reversal
  [ ] Large steps visible before reversal, small after

PANEL 3 — PREVIOUS THRESHOLDS
  [ ] Empty at start
  [ ] Threshold appears after config completes
  [ ] Accumulates across configs
  [ ] Labels correct

PANEL 4 — PSYCHOMETRIC FUNCTION
  [ ] Updates after config completes
  [ ] Fitted curve visible
  [ ] Data points plotted
  [ ] Theta / k values shown

INFO PANEL
  [ ] Paradigm name correct
  [ ] Config N/M counter updates
  [ ] Trial counter updates
  [ ] FP warning text on false positive

BEHAVIORAL
  [ ] Window persists across config changes
  [ ] No crashes during long runs
  [ ] No rendering artifacts
  [ ] No noticeable lag between trials

WRV LIMIT (optional: drive track to boundary intentionally)
  [ ] Warning appears when adaptive param hits min or max

NOTES:



RESULT:  [ ] PASS    [ ] FAIL    [ ] NEEDS FOLLOW-UP
```

---

## H5 — End-to-End Validation

*~1 hr. Requires someone with a recent clinical audiogram. Ideally run after calibration.*

```
Participant: _______________    Tester: _______________    Date: ___________
Clinical audiogram date: ___________
Calibration status:  [ ] Calibrated  [ ] Uncalibrated

PTA COMPARISON

Freq (Hz) | Clinical (dB HL) | PROLACTIN (dB) | Difference
----------|------------------|----------------|----------
250       |                  |                |
500       |                  |                |
1000      |                  |                |
2000      |                  |                |
4000      |                  |                |
8000      |                  |                |

Expected: |diff| < 10 dB uncalibrated, < 5 dB calibrated
  [ ] Frequency pattern matches (same audiogram shape)

GAP DETECTION
  Normal hearing expected: < 5 ms
  Result: _______ ms    [ ] Within expected range

IFMC AT 1 KHZ (if PTA run first)
  Normal hearing expected depth: ~20-30 dB (Lecluyse 2013)
  Result: _______ dB    [ ] Within expected range

NOTES:



RESULT:  [ ] PASS    [ ] FAIL    [ ] NEEDS FOLLOW-UP
```

---

## H6 — Cross-Platform (Windows)

*~1 hr. Requires a Windows machine with conda.*

```
Machine: _______________    OS: _______________    Date: ___________

ENVIRONMENT SETUP
  [ ] conda env created from environment.yml
  [ ] PsychoPy imports without error
  [ ] PTB audio backend initializes
  Errors encountered:


PTA RUN
  [ ] Setup dialog opens
  [ ] Demo plays audio
  [ ] Paradigm runs (1+ config)
  [ ] Operator display opens and updates
  [ ] CSV written to test_data/
  [ ] No path separator issues

GAP RUN
  [ ] Noise+gap plays correctly
  [ ] No audio glitches

AM RUN
  [ ] Modulated tone sounds correct

DATA FILES
  [ ] CSV readable by pandas on Windows
  [ ] Filenames valid
  [ ] ResultLoader finds files

NOTES:



RESULT:  [ ] PASS    [ ] FAIL    [ ] NEEDS FOLLOW-UP
```
