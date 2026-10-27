# Audio Test Battery

Python-based audiometry and auditory psychophysics, with additional tinnitus-matching tools.

**Main developer: Eric Larrieux**

Developed at [REA.lab](https://realab.science/), University of Zurich.

## Features

- Pure-tone audiometry, loudness discomfort levels, and speech recognition thresholds.
- Gap detection, intensity discrimination, amplitude/frequency modulation detection, and interaural time/level discrimination.
- Iso-forward masking curves (IFMC) and temporal masking curves (TMC).
- Adaptive testing with PsychoPy, participant responses, live operator plots, and CSV results.
- Separate Max/MSP tools for tinnitus matching, minimum masking level, and residual inhibition in [`tinnitus_matching/`](tinnitus_matching/).

## Getting started

Install [Conda](https://docs.conda.io/projects/conda/en/stable/user-guide/install/index.html), then:

```bash
git clone https://github.com/rea-labs/audio_test_battery.git
cd audio_test_battery
conda env create -f environment_310.yml
conda activate audio_toolbox_310
cd python_code/audiology_toolbox
python audio_devices.py
```

Configure your output device using [`config/DEFAULTS_local.example.py`](python_code/audiology_toolbox/config/DEFAULTS_local.example.py): copy it to `DEFAULTS_local.py` in the same folder and edit the device-name substrings.

**Before participant testing, verify the audio hardware, headphone calibration, and sound-level limits.** PTA requires a populated SPL calibration profile in [`calibration_data/`](calibration_data/); calibration values must match your setup.

Launch a paradigm from `python_code/audiology_toolbox`, for example:

```bash
python test_pta.py
```

Other `test_*.py` scripts launch the corresponding paradigms. The Python environment does not run the separate Max/MSP patches.

## Credit

Please acknowledge **Eric Larrieux, main developer**, and REA.lab when using this software in research, and cite the [repository](https://github.com/rea-labs/audio_test_battery) with the version or commit used.
