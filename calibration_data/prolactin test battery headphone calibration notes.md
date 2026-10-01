# PROLACTIN TEST BATTERY HEADPHONE CALIBRATION NOTES
_2026 - 04 - 07_

## HARDWARE SETUP:
- interface: RME UCX II
	- headphone out (ch 7-8) --> gain = 0 dB
	- line in (ch 1) --> gain = +36 dB
- headphones: Beyerdynamic DT 250, 250 ohm
- artificial ear: B&K Type 4153 --> Type 4912 mic + Type 1708 amplifier + Type 4231 Sound Calibrator
	- mic calibration file = B&K_4912_3259602.cal
	- 1708  --> Vpol (200V); Filter = Linear; Gain = 1x
	- BNC --> 6.3 mm jack connection
- computer: project M3 Macbook Pro
	- macOS Sonoma 14.4.1

## SOFTWARE SETUP:
- REW: V5.31.3 running Azul Systems, Inc. JRE 1.8.0_422 64-bit on OS X 14.4.1
	- sweep level = -12 dB
	- ...
- RME TotalMix: 
	- headphone out = ch 7-8; level 0 dB



LEFT -20 --> 0 = 101.9
LEFT -20 --> -6 = 101.9



## AKG K271 MkII
- had to reduce sweep level from -12 dB to -18 dB to avoid clipping
- interaural distance was too small --> used a space to increase it to 16.5 cm


## LEVEL CALIBRATION
### AKG K271 MkII
#### LEFT
- FILE: 1 kHz sin at -20 dB_FS.wav (in reaper) --> channel gain = -11.30 dB --> ReaVerb (IR = AKG_K271_MkII_IR_LEFT_2026-04-16-48k.wav) --> hardware output @ 0 dB --> REW SPL meter = 94 dB
- ... --> hardware output @ +6 dB --> REW SPL meter = 100 dB
- ... --> hardware output @ -6 dB --> REW SPL meter = 88 dB
- FILE: white_noise.wav (in reaper) --> channel gain = -6.35 dB --> ReaVerb (IR = AKG_K271_MkII_IR_LEFT_2026-04-16-48k.wav) --> hardware output @ 0 dB --> REW SPL meter = 94 dB
- ... --> hardware output @ +6 dB --> REW SPL meter = 100 dB
- ... --> hardware output @ -6 dB --> REW SPL meter = 88 dB
#### RIGHT --> NOTE: 0.1 dB louder than left channel for sin (0.35 louder for white noise)
- FILE: 1 kHz sin at -20 dB_FS.wav (in reaper) --> channel gain = -11.40 dB --> ReaVerb (IR = AKG_K271_MkII_IR_RIGHT_2026-04-16-48k.wav) --> hardware output @ 0 dB --> REW SPL meter = 94 dB
- ... --> hardware output @ +6 dB --> REW SPL meter = 100 dB
- ... --> hardware output @ -6 dB --> REW SPL meter = 88 dB
- FILE: white_noise.wav (in reaper) --> channel gain = -6.70 dB --> ReaVerb (IR = AKG_K271_MkII_IR_RIGHT_2026-04-16-48k.wav) --> hardware output @ 0 dB --> REW SPL meter = 94 dB
- ... --> hardware output @ +6 dB --> REW SPL meter = 100 dB
- ... --> hardware output @ -6 dB --> REW SPL meter = 88 dB



## 18.05.26 NOTES
### beyerdynamic DT250 - headphones: X 
- PEQ target level LEFT = 107.8 dB; match range = 20 Hz - 16 kHz
- sweep level = -12 dB FS
#### LEFT
- FILE: 1 kHz sin at -20 dB_FS.wav (in reaper) --> channel gain = 0 dB --> ... --> hardware output @ 0 dB --> REW SPL meter = __ dB
- ... --> hardware output @ +6 dB --> REW SPL meter = __ dB
- ... --> hardware output @ -6 dB --> REW SPL meter = __ dB
- FILE: white_noise.wav (in reaper) --> channel gain = 0 dB --> ... --> hardware output @ 0 dB --> REW SPL meter = __ dB
- ... --> hardware output @ +6 dB --> REW SPL meter = __ dB
- ... --> hardware output @ -6 dB --> REW SPL meter = __ dB
#### RIGHT
- FILE: 1 kHz sin at -20 dB_FS.wav (in reaper) --> channel gain = 0 dB --> ... --> hardware output @ 0 dB --> REW SPL meter = __ dB
- ... --> hardware output @ +6 dB --> REW SPL meter = __ dB
- ... --> hardware output @ -6 dB --> REW SPL meter = __ dB
- FILE: white_noise.wav (in reaper) --> channel gain = 0 dB --> ... --> hardware output @ 0 dB --> REW SPL meter = __ dB
- ... --> hardware output @ +6 dB --> REW SPL meter = __ dB
- ... --> hardware output @ -6 dB --> REW SPL meter = __ dB



### AKG K271 MkII
- target level = 102.5
- reduced sweep level to -18
#### LEFT



## 04.06.26 NOTES
### "closing the loop" from dB FS --> dB SPL (and eventually dB HL)
- when using white noise, should probably use dB(Z) (unweighted) rather than dB(C) (C-weighted)
--> also may want to filter the noise down to 18 kHz or so?  (see chat w/ claude...)
