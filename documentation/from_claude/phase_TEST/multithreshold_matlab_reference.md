# MultiThreshold 1.46 — MATLAB Source Reference

Reference document for the PROLACTIN project. Summarizes the architecture, key data
structures, adaptive logic, and paradigm definitions from the original MATLAB MultiThreshold
1.46 toolbox (Ray Meddis, University of Essex) and its UZH modification (Nuno Prates de Matos,
2017). Use this to verify correct implementation of adaptive logic in Python/PROLACTIN.

---

## 1. Repository Structure

**GitHub:** https://github.com/rmeddis/MAP (folder `multiThreshold 1.46`)

### Root-level .m files (original)
| File | Role |
|---|---|
| `multiThreshold.m` | Experimenter GUI — top-level entry point |
| `nextStimulus.m` | Stimulus crafting + catch trial logic (called from subjGUI) |
| `subjGUI_MT.m` | Subject (participant) GUI — owns response handling and trial loop |
| `Levitt2.m` | Levitt adaptive staircase helper |
| `psychometricFunction.m` | Logistic/psychometric function fitting |
| `bestFitPsychometicFunctions.m` | Exhaustive search for best-fit psychometric params |
| `profile2mFile.m` | Save/load experiment profile |
| `plotProfile.m` | Plot threshold profile |
| `printReport.m` | End-of-experiment report |
| `addToMsg.m` | Append to experimenter message log |

### UZH-modified versions (local copy, not on GitHub)
| File | Notes |
|---|---|
| `USZmultiThreshold.m` | Replaces `multiThreshold.m`; adds calibration file selection, language (DE/EN), catch trial continue option |
| `USZnextStimulus.m` | Replaces `nextStimulus.m`; adds per-channel calibration interpolation |
| `USZsubjGUI_MT.m` | Replaces `subjGUI_MT.m` |
| `multi_threshold_v1_4.m` | Version history artifact; not the active entry point |

### Paradigm files (`paradigms/` subfolder)
Each paradigm file sets `stimulusParameters` and `experiment` fields, then returns.
The experimenter GUI loads these dynamically via `eval(['paradigm_' paradigm '(handles);'])`.

Key paradigm files relevant to PROLACTIN:
| File | PROLACTIN equivalent |
|---|---|
| `paradigm_absThreshold.m` | PTA |
| `paradigm_absThreshold_16.m` | PTA (16ms target — prerequisite for IFMC/TMC) |
| `paradigm_IFMC.m` | IFMC |
| `paradigm_TMC.m` | TMC |
| `paradigm_forwardMasking.m` | TMC variant |
| `paradigm_discomfort.m` | LDL |
| `paradigm_GOM.m` | (not in PROLACTIN) |
| `paradigm_SRT.m` | (not in PROLACTIN) |
| `paradigmBase.m` | Base template — defines all fields with default values |
| `paradigm_tEAS_*.m` | UZH tinnitus study variants |
| `paradigm_tinnoice_*.m` | UZH tinnitus+noise variants (PTA, IFMC, TMC, LDL) |

---

## 2. Key Global Data Structures

All state is stored in MATLAB globals. Python equivalents are instance attributes.

### `stimulusParameters` — stimulus config (set by paradigm file, modified by GUI)
```
stimulusParameters.WRVname          % name of within-run variable (e.g. 'maskerLevel')
stimulusParameters.WRVstartValues   % starting value(s) of the adaptive variable
stimulusParameters.WRVsteps         % step sizes [coarse fine] in dB
stimulusParameters.WRVlimits        % [min max] allowed range

stimulusParameters.targetFrequency  % Hz
stimulusParameters.targetDuration   % seconds
stimulusParameters.targetLevel      % dB SPL (fixed component; WRV is on top)
stimulusParameters.targetType       % 'tone' | 'noise' | etc.

stimulusParameters.maskerType       % 'tone' | 'noise' | etc.
stimulusParameters.maskerDuration   % seconds
stimulusParameters.maskerLevel      % dB SPL
stimulusParameters.maskerRelativeFrequency  % maskerFreq = this * targetFrequency

stimulusParameters.gapDuration      % seconds (gap between masker and target)
stimulusParameters.rampDuration     % onset/offset ramp, seconds
stimulusParameters.stimulusDelay    % pre-stimulus silence, seconds
stimulusParameters.cueTestDifference % dB; how much more audible is the cue

stimulusParameters.catchTrialRate   % [initialRate baseRate] or [r0 r1 r2 r3]
stimulusParameters.catchTrialBaseRate
stimulusParameters.catchTrialTimeConstant

stimulusParameters.includeCue       % 0 or 1
stimulusParameters.backgroundType   % 'none' | 'noise' | etc.
stimulusParameters.backgroundLevel  % dB SPL
stimulusParameters.calibrationdB    % scalar correction (used when no cal file)

stimulusParameters.subjectText      % string shown on participant GUI
stimulusParameters.targetLevels     % vector; targetLevel can vary across outer runs
```

### `experiment` — paradigm/experiment-level config
```
experiment.paradigm             % string name, e.g. 'IFMC', 'absThreshold'
experiment.ear                  % 'left' | 'right' | 'diotic' | 'dichoticLeft' | ...
experiment.threshEstMethod      % 'oneIntervalUpDown' | 'MaxLikelihood' | '2I2AFC++' | ...
experiment.maskerInUse          % 0 or 1
experiment.allowCatchTrials     % 0 or 1
experiment.psyFunSlope          % +1 (harder=more signal) or -1 (harder=less signal)
experiment.singleIntervalMaxTrials  % stopping criterion for oneIntervalUpDown
experiment.stopCriteria2IFC     % [targetPct nReversals nTrials] for 2AFC
experiment.functionEstMethod    % 'logisticLS' | 'logisticML' | 'rareEvent'
experiment.useCalibrationFile   % 1=use file, 2=manual dB entry
experiment.status               % state machine: 'waitingForGO' | 'presentingStimulus' |
                                %   'waitingForResponse' | 'runCompleted' | 'endOfExperiment'
```

### `betweenRuns` — outer loop state (across configs/frequencies)
```
betweenRuns.variableName1       % name of outer variable 1 (e.g. 'maskerRelativeFrequency')
betweenRuns.variableList1       % vector of values for variable 1
betweenRuns.variableName2       % name of outer variable 2 (e.g. 'targetFrequency')
betweenRuns.variableList2       % vector of values for variable 2
betweenRuns.var1Sequence        % randomized/fixed presentation sequence for var1
betweenRuns.var2Sequence        % same for var2
betweenRuns.runNumber           % current outer-loop index (1-based)
betweenRuns.randomizeSequence   % 'randomize within blocks' | 'fixed sequence'

betweenRuns.thresholds          % vector of estimated thresholds (one per run)
betweenRuns.thresholds_mean
betweenRuns.thresholds_median
betweenRuns.forceThresholds     % NaN if aborted
betweenRuns.observationCount    % number of trials per run
betweenRuns.timesOfFirstReversals  % trial index of first reversal per run
betweenRuns.catchTrials         % catch trial count per run
betweenRuns.caughtOut           % total false positives across all runs
betweenRuns.bestThresholdTracks % cell array of threshold estimate tracks
betweenRuns.levelTracks         % cell array of level tracks (phase 2 only)
betweenRuns.responseTracks      % cell array of response tracks (phase 2 only)
```

### `withinRuns` — inner loop state (within a single adaptive run)
```
withinRuns.trialNumber          % current trial index (1-based)
withinRuns.variableValue        % current value of the adaptive variable (WRV)
withinRuns.catchTrial           % 1 if this is a catch trial
withinRuns.catchTrialCount      % number of catch trials so far this run
withinRuns.thisIsRepeatTrial    % 1 if trial is being repeated

withinRuns.levelList            % full history of WRV values presented
withinRuns.responseList         % full history of responses (0/1)
withinRuns.thresholdEstimateTrack  % running threshold estimate per trial

withinRuns.beginningOfPhase2    % trial index where phase 2 starts (after 1st reversal)
                                % 0 = phase 2 not yet reached

withinRuns.forceThreshold       % set to NaN to abort run early; numeric to override
```

---

## 3. Adaptive Logic — `oneIntervalUpDown`

This is the core algorithm PROLACTIN must implement. Source: `subjGUI_MT.m` response
callbacks + `nextStimulus.m` / `USZnextStimulus.m`.

### Phase 1 (startup): large steps until first reversal
- Uses `WRVsteps(1)` (coarse step, e.g. 10 dB)
- Correct response -> decrease WRV (harder)
- Incorrect response -> increase WRV (easier), marks reversal
- After first reversal: enter Phase 2, record `beginningOfPhase2`

### Phase 2 (measurement): fine steps, collect reversals
- Uses `WRVsteps(2)` (fine step, e.g. 2 dB)
- Correct -> decrease; Incorrect -> increase
- Reversal = direction change
- Threshold estimated from mean of phase-2 reversals (or logistic fit)
- Run ends after `singleIntervalMaxTrials` trials total

### Catch trial logic (`USZnextStimulus.m`, lines 18-50)
```
Trial 1:  never a catch trial; reset catchTrialCount = 0
Trial 2:  always a catch trial (if no catch trials have occurred yet)
Otherwise: catch trial with probability catchTrialRate
```
- Catch trial: targetLevel = -100 (effectively silent)
- UZH modification: false positive on catch trial -> show red feedback, log count, continue
  (original behavior was to stop and restart the run)
- `catchTrialRate` decays toward `catchTrialBaseRate` between runs:
  `rate = baseRate + (rate - baseRate) * (1 - exp(-timeConstant))`

### WRV step direction
The `psyFunSlope` field controls direction:
- `psyFunSlope = +1`: correct -> WRV decreases (e.g. masker level down = harder to hear)
- `psyFunSlope = -1`: correct -> WRV increases (e.g. gap duration up = harder to detect)

### Stopping criterion
- `oneIntervalUpDown`: stop after `experiment.singleIntervalMaxTrials` total trials
- `2I2AFC`: stop after `stopCriteria2IFC` = [targetPct nReversals nTrials]

---

## 4. Stimulus Architecture (`USZnextStimulus.m / stimulusMakeAndPlay`)

### Two-stimulus structure (cue + test)
Every trial has a cue and a test stimulus. The cue is more audible:
- For absThreshold paradigms: `cueTargetLevel = targetLevel + cueTestDifference`
- For masking paradigms (IFMC/TMC): `cueMaskerLevel = maskerLevel - cueTestDifference`
  (weaker masker makes the probe more audible in the cue)
- `includeCue = 0` suppresses the cue (used in LDL/discomfort, some masking paradigms)

### WRV injection
The within-run variable is injected into the stimulus just before construction:
```matlab
cmd = [stimulusParameters.WRVname '= withinRuns.variableValue;'];
eval(cmd);
% e.g.: maskerLevel = withinRuns.variableValue;
```

### Outer variable injection
Between-run variables are set at the start of each run:
```matlab
stimulusParameters.targetFrequency = betweenRuns.var1Sequence(thisRunNumber);
```

### Calibration (UZH extension)
Two modes:
1. `useCalibrationFile = 1` (default): loads `CalibrationFileL/R/Diotic.mat`
   - Fields: `calibrationFrequency` (vector), `calibrationAttenuation` (vector)
   - Separate corrections for target and masker frequencies
   - Linear interpolation for frequencies not in the calibration table
   - Applied as: `audioOutCorrectionTarget = 10^(fT/20)`
2. `useCalibrationFile = 2`: manual scalar dB entry (`editcalibrationdB`)

### Audio output
- `audioplayer(audio, FS, 24)` + `playblocking(y)` — 24-bit depth
- Stimulus is a 2-column matrix [left; right]
- For 2I2AFC: two intervals played sequentially with random order; order stored in
  `withinRuns.stimulusOrder`

---

## 5. Paradigm Configurations

### `paradigmBase` — defaults inherited by all paradigms
(Source: `multiThreshold 1.46/paradigms/paradigmBase.m`)
```matlab
experiment.threshEstMethod = 'oneIntervalUpDown'
experiment.singleIntervalMaxTrials = 10
experiment.allowCatchTrials = 1
stimulusParameters.includeCue = 1
stimulusParameters.cueTestDifference = 10   % dB
stimulusParameters.WRVname = 'targetLevel'
stimulusParameters.WRVstartValues = 30
stimulusParameters.WRVsteps = [10 2]        % [coarse fine] dB
stimulusParameters.WRVlimits = [-30 110]
experiment.psyFunSlope = 1                  % correct -> level down
betweenRuns.variableName1 = 'targetFrequency'
betweenRuns.variableList1 = 1000
betweenRuns.variableName2 = 'targetDuration'
betweenRuns.variableList2 = 0.1
betweenRuns.randomizeSequence = 'randomize within blocks'
stimulusParameters.stimulusDelay = 0.3      % s
experiment.maskerInUse = 0
stimulusParameters.maskerDuration = 0.0
stimulusParameters.maskerLevel = -50
stimulusParameters.maskerRelativeFrequency = 1
stimulusParameters.gapDuration = 0.0
stimulusParameters.targetType = 'tone'
stimulusParameters.targetPhase = 'cos'
stimulusParameters.targetFrequency = 1000
stimulusParameters.targetDuration = 0.1
stimulusParameters.targetLevel = 30         % = WRVstartValues(1)
stimulusParameters.rampDuration = 0.004     % s
stimulusParameters.backgroundType = 'none'
stimulusParameters.backgroundLevel = -100
stimulusParameters.subjectSampleRate = 44100
```

### `paradigm_absThreshold` (PTA)
(Source: `multithreshold 1.46/paradigms/paradigm_absThreshold.m`)
```matlab
% Inherits all paradigmBase defaults, then overrides:
betweenRuns.variableName1 = 'targetFrequency'
betweenRuns.variableList1 = [250 500 1000 2000 4000 8000]
betweenRuns.variableName2 = 'targetDuration'
betweenRuns.variableList2 = 0.25           % s
experiment.maskerInUse = 0
stimulusParameters.targetDuration = 0.25
% WRVname='targetLevel', WRVstartValues=30, WRVsteps=[10 2] — from base
% psyFunSlope=1 (correct -> level down) — from base
```
Note: `targetLevel = NaN` is NOT set here — it inherits `WRVstartValues(1) = 30`.

### `paradigm_absThreshold_16` (16ms absolute threshold — prerequisite for IFMC/TMC)
(Source: `multithreshold 1.46/paradigms/paradigm_absThreshold_16.m`)
```matlab
betweenRuns.variableName1 = 'targetFrequency'
betweenRuns.variableList1 = str2num(handles.edittargetFrequency)  % read from GUI
betweenRuns.variableName2 = 'targetDuration'
betweenRuns.variableList2 = 0.016          % s  ← key difference from absThreshold
experiment.maskerInUse = 0
stimulusParameters.targetType = 'tone'
stimulusParameters.targetPhase = 'sin'
stimulusParameters.targetDuration = 0.016
stimulusParameters.rampDuration = 0.004
experiment.singleIntervalMaxTrials = 20    % more trials than base (10)
% WRVname='targetLevel', WRVstartValues=30, WRVsteps=[10 2] — from base
```
The resulting thresholds are then passed as `targetLevel = threshold + 10` dB to IFMC/TMC
(set manually in the GUI or via the `profile` paradigm automation).

### `paradigm_IFMC`
(Source: `multithreshold 1.46/paradigms/paradigm_IFMC.m`)
```matlab
stimulusParameters.WRVname = 'maskerLevel'
stimulusParameters.WRVstartValues = 10     % dB SPL starting masker level
stimulusParameters.WRVsteps = [-10 -2]     % NEGATIVE: steps go down first (harder)
stimulusParameters.WRVlimits = [-30 110]
experiment.psyFunSlope = -1                % correct -> masker level goes UP

betweenRuns.variableName1 = 'maskerRelativeFrequency'
betweenRuns.variableList1 = [1 0.5 1.6 0.9 0.7 1.1 1.3]  % 7 masker freqs
betweenRuns.variableName2 = 'targetFrequency'
betweenRuns.variableList2 = str2num(handles.edittargetFrequency)  % from GUI

experiment.maskerInUse = 1
stimulusParameters.maskerType = 'tone'
stimulusParameters.maskerPhase = 'sin'
stimulusParameters.maskerDuration = 0.108  % s
stimulusParameters.maskerRelativeFrequency = [1 0.5 1.6 0.9 0.7 1.1 1.3]
stimulusParameters.gapDuration = 0.01      % s (masker-to-probe gap)

stimulusParameters.targetType = 'tone'
stimulusParameters.targetPhase = 'sin'
stimulusParameters.targetDuration = 0.016  % s (16ms probe)
stimulusParameters.targetLevel = NaN       % ← must be set from absThreshold_16 result
stimulusParameters.rampDuration = 0.004    % s
% includeCue=1, cueTestDifference=10 from base → cue has weaker masker by 10 dB
```
**Important:** `WRVsteps = [-10 -2]` — negative values mean the variable *increases*
on a correct response (masker level goes up = harder). This is the IFMC direction
convention — opposite sign to absThreshold. `psyFunSlope = -1` flags this inversion.

### `paradigm_TMC` (temporal masking curve)
(Source: `multithreshold 1.46/paradigms/paradigm_TMC.m`)
```matlab
stimulusParameters.WRVname = 'maskerLevel'
stimulusParameters.WRVstartValues = 50     % dB SPL
stimulusParameters.WRVsteps = [-10 -4]     % NEGATIVE: same convention as IFMC
stimulusParameters.WRVlimits = [-30 110]
stimulusParameters.cueTestDifference = 10  % explicit (same as base)
experiment.psyFunSlope = -1

betweenRuns.variableName1 = 'gapDuration'
betweenRuns.variableList1 = [0.05 0.09 0.01 0.07 0.03]  % s (5 gap durations)
betweenRuns.variableName2 = 'targetFrequency'
betweenRuns.variableList2 = str2num(handles.edittargetFrequency)  % from GUI

experiment.maskerInUse = 1
stimulusParameters.maskerType = 'tone'
stimulusParameters.maskerPhase = 'sin'
stimulusParameters.maskerDuration = 0.108  % s
stimulusParameters.maskerRelativeFrequency = 1  % on-frequency masker
stimulusParameters.gapDuration = [0.05 0.09 0.01 0.07 0.03]  % s

stimulusParameters.targetType = 'tone'
stimulusParameters.targetPhase = 'sin'
stimulusParameters.targetDuration = 0.016  % s (16ms probe)
stimulusParameters.targetLevel = NaN       % ← must be set from absThreshold_16 result
stimulusParameters.rampDuration = 0.004    % s
```
Note: TMC fine step is `-4` dB vs IFMC's `-2` dB.

### `paradigm_discomfort` (LDL)
(Source: `multithreshold 1.46/paradigms/paradigm_discomfort.m`)
```matlab
stimulusParameters.WRVname = 'targetLevel'
stimulusParameters.WRVstartValues = 75     % dB SPL — starts at moderate-high level
stimulusParameters.WRVsteps = [3 3]        % always 3 dB, both phases
stimulusParameters.WRVlimits = [-30 110]

betweenRuns.variableName1 = 'targetFrequency'
betweenRuns.variableList1 = [1000]         % single frequency default
betweenRuns.variableName2 = 'targetDuration'
betweenRuns.variableList2 = 0.5            % s
betweenRuns.randomizeSequence = 'fixed sequence'

stimulusParameters.stimulusDelay = 0       % no pre-stimulus silence
experiment.maskerInUse = 0
stimulusParameters.targetType = 'tone'
stimulusParameters.targetPhase = 'sin'
stimulusParameters.targetDuration = 0.5   % s
stimulusParameters.targetLevel = 75       % = WRVstartValues(1)
% includeCue forced to 0 in aResetPopupMenus (no cue for LDL)
% psyFunSlope=1 from base (but LDL ends on first "uncomfortable", not reversal count)
```
**Key LDL notes:**
- `WRVsteps = [3 3]` — same step size in both phases; level always ascends
- No catch trials in practice (though `allowCatchTrials=1` in base; LDL logic overrides)
- Run terminates on first "uncomfortable" response (1 reversal = end), not trial count
- `jitterStartdB = 0` set explicitly in `aReadAndCheckParameterBoxes` for discomfort paradigm

---

## 6. Control Flow Summary

```
USZmultiThreshold (experimenter GUI)
  -> initializeGUI()             loads paradigm, sets up GUI
  -> RUN button callback
       -> startNewRun() in USZsubjGUI_MT
            loop:
              -> USZnextStimulus()    catch trial? -> stimulusMakeAndPlay()
              -> wait for response
              -> response callback (pushbutton0/1/2/3)
                   -> updateAdaptiveVariable()   [Levitt logic]
                   -> check stopping criterion
                   -> if run complete: runCompleted()
       -> runCompleted() in USZsubjGUI_MT
            -> estimate threshold (logistic or mean-of-reversals)
            -> return to USZmultiThreshold
  -> plotProgress() + update betweenRuns
  -> if more runs: prompt GO for next run
  -> if all runs done: printReport(), endOfExperiment
```

---

## 7. UZH Modifications (from `Documentation_multiThreshold_UZH_UPDATE.docx`)

1. **Catch trial behavior**: changed from stop-and-restart to log-and-continue.
   Red visual feedback shown; count recorded in `betweenRuns.caughtOut`.

2. **Calibration per channel**: `CalibrationFileL.mat`, `CalibrationFileR.mat`,
   `CalibrationFileDiotic.mat` replace single `calibrationFile.mat`.
   Separate corrections for target and masker frequencies with linear interpolation.

3. **GUI**: Color scheme (`USZcolorExpGUI`), language toggle (DE/EN), calibration file
   selection dropdown added to experimenter GUI.

4. **`multi_threshold_v1_4.m`**: contains version history; not the active entry point.

---

## 8. Key Implementation Notes for PROLACTIN

- **WRV (within-run variable)** maps to `step_mode` / adaptive variable in PROLACTIN's
  `AdaptiveParadigm`. In MATLAB it is always named explicitly (e.g. `'maskerLevel'`).
- **Phase 1 / Phase 2 boundary** = first reversal. PROLACTIN: `self._phase` or
  `self._reversal_count == 0`.
- **`betweenRuns`** = outer variable loop = PROLACTIN's config/VarSpec iteration.
- **`withinRuns`** = single adaptive run = one PROLACTIN config execution.
- **Calibration** in MATLAB is a simple lookup table with linear interpolation. PROLACTIN
  Phase B replaces this with per-channel FIR convolution (better for broadband stimuli).
- **`psyFunSlope`** is implicit in PROLACTIN via how `_update_level` interprets correct/
  incorrect responses. Must be verified per paradigm.
- **`targetLevels` (plural)**: IFMC/TMC use different fixed `targetLevel` values per
  outer `targetFrequency` loop iteration. This is set via `stimulusParameters.targetLevels`
  vector indexed by `floor(runNumber / len(variableList1))`. PROLACTIN equivalent:
  per-frequency threshold offsets loaded from previous PTA/absThreshold_16 results.
- **Stimulus construction is NOT in the paradigm file** — paradigm only sets params.
  All audio generation is in `nextStimulus / stimulusMakeAndPlay`. PROLACTIN equivalent:
  paradigm calls `TrialPlayer` / `prepare_trial()`.
