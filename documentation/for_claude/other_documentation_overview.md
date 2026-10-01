# Other documentation

this dump contains general documentation about the test battery, underlying theory, and a few specific python implementation details.  please let me know if there is anything missing that could be helping...

## Original MATLAB version documentation

`MultiThreshold User's Manual_ZH.pdf`
- the matlab version that is currently used and most of the new test battery should be based off of *especially the control flow* (catch trials, trials after reversals, etc.)

`Documentation_multiThreshold_UZH_UPDATE.docx`
- details some specific changes made from the original version

## Other documentation from prauge toolbox (with incorrect logic)

`PROLACTIN_audiometric_tests_prague.pdf`
- the control flow is wrong, but describes what the paradigms *should do* accurately

## Planning documentation for the test battery

`PROLACTIN_miro_block_diagrams.pdf`
- my original planning documentation
- things have evolved since i put this together, but it shows roughly how i think all the classes should be structured and interconnected

`PROLACTIN_paradigm_plan_overview.csv`
- IMPORTANT --> contains details about how specific paradigms should be structured, i.e. what frequencies, durations, levels, etc.

## Relevant papers

`Lecluyse-2013-IJA-profiles.pdf` 
- this paper discusses how to implement PTA, IFMC, and TMC

`A simple single-interval adaptive procedure for estimating thresholds in normal and impaired listeners - Lecluyse W. & Meddis R..pdf` 
- this paper discusses how to implement psychometric functions for threshold estimation

## Python configuration
`environment.yml`
- the current environment that works on my mac
    - getting this right caused A LOT of headaches b/c PTB Audio wouldn't work in certain configurations b/c of the Apple Silicon chipset
- use this to know what versions are used and if anything should be updated to run on windows...

`python_code/config/DEFAULTS.py`
- i would like to have a file like this (or something similar) to keep track of general default values and configuration params for the test battery
- it is VERY incomplete, and not connected, but please use as an example to build off of