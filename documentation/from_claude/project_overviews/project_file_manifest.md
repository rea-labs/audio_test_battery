# PROLACTIN — Project File Manifest

Purpose: tell the assistant what each project file is and **when it's worth
opening**, so it stops reading files it doesn't need. Default to NOT reading a
file unless the "read when" applies. `project_knowledge_search` (chunked) is
cheap; full `view`/fetch of a file is what burns context — be selective.

> Maintenance: when files are added/renamed, update this. The session-cleanup
> skill is a good place to remember to refresh it.

---

## Core code (read when working on that piece)

| File | What it is | Read when |
|------|-----------|-----------|
| `adaptive_paradigm.py` | Base class `AdaptiveParadigm` — adaptive logic, trial loop, data/CSV, pauses, WRV limits, metadata. The hub. | Any change to shared paradigm behavior, base-class methods, or anything subclasses inherit. |
| `trial_player.py` | `TrialPlayer` — builds/plays stereo trials; `per_channel_gain`, pan, calibration routing, PTB output. | Audio playback, per-ear gain, calibration integration, PTB/GC issues. |
| `event_gen.py` | `EventGen` — signal synthesis (sin, noise, FM, AM, fades). Configures audio device before importing `psychopy.sound`. | Stimulus synthesis, FM/AM math, fades, device-init ordering. |
| `calibration.py` | `CalibrationManager` — FIR inverse filters, `spl_to_amplitude`, optional dB HL via RETSPL. | Calibration, dB SPL/HL, IR loading, per-channel SPL. |
| `hl_converter.py` | `HLConverter` — SPL↔HL via RETSPL table (log-freq interp). stdlib+numpy only. | dB HL conversion, RETSPL tables. |
| `audio_devices.py` | Device find/configure by substring (Mac/Win). | Device selection, cross-OS device naming, circular-import issues. |
| `varspec.py` | `VarSpec` — inner/outer variable spec used everywhere. | Variable structure questions. |
| `event_gen` + `trial_player` together | synthesis → playback chain | Anything end-to-end about a stimulus. |

## Paradigms (read only the one(s) in scope)

| File | Paradigm | Notes |
|------|----------|-------|
| `paradigm_pta.py` | Pure-tone audiometry | dB SPL + optional HL reference pattern. |
| `paradigm_am.py` | Amplitude modulation | `mod_ind` percent. |
| `paradigm_fm.py` | Frequency modulation | **FM mod-index bug lives here / in event_gen — unresolved.** |
| `paradigm_gap.py` | Gap detection | needs `sample_accurate=True`; uniform-gain relaxation. |
| `paradigm_dli.py` | Difference limen (intensity) | |
| `paradigm_ild.py` | Interaural level diff | bypasses TrialPlayer? No — routes through it with TWO `spl_to_amplitude` calls. |
| `paradigm_itd.py` | Interaural time diff | **bypasses TrialPlayer by design** (per-channel timing). |
| `paradigm_ifmc.py` | Iso-forward masking curve | masker-only catch trials; yes/no simplification. |
| `paradigm_tmc.py` | Temporal masking curve | gap is an outer var. |
| `paradigm_ldl.py` | Loudness discomfort level | inherits AdaptiveParadigm; custom catch/cond logic. |
| `paradigm_srt.py` | Speech reception threshold | active version. |
| `paradigm_*_DEPRECATED.py` | old SRT | **don't read** — slated for deletion. |

## Tests / GUI / config

| File | What it is | Read when |
|------|-----------|-----------|
| `test_<paradigm>.py` | Per-paradigm entry script (constructs paradigm + calibration + dialog). | Running/wiring that paradigm; calibration injection pattern. |
| `operator_gui.py` | Real-time operator monitoring display. | Operator-GUI changes, WRV warning overlay, unit display. |
| `paradigm_setup_dialog.py` | tkinter setup dialogs (`ParadigmSetupDialog`, `ThresholdSetupDialog`). | Setup UI, editable params, demo mode, threshold loading, device label. |
| `result_loader.py` | `ResultLoader` — reads result CSVs (+ metadata header). | Reading/parsing saved data. |
| `rms_analyzer.py` | RMS/level analysis helper. | Level analysis. |
| `calibration_config.json` | Profiles (DT250 A/B/X, AKG), IR paths, SPL, RETSPL. | Calibration profiles/values. **All SPL currently null → re-measure.** |
| `DEFAULTS.py` / `config/DEFAULTS.py` | Global defaults (`fs`, device substrings). | Defaults, device substrings. |
| `standard_frequencies.py` | Frequency sets (e.g. ISO 389). | Frequency-set definitions. |
| `participant_id_helper.py` | PID formatting/validation. | Participant ID handling. |
| `version.py` | `__version__`. | Version bumps. |
| `hl_converter` / `audio_devices` | (see core) | |

## Docs — reference, usually DON'T full-read

| File | When (and only when) to open |
|------|------------------------------|
| `session_changelog_*.md` | **Latest one only**, at session start. Older ones only if the latest points to them. |
| `prd_*.md` | Only if revisiting that specific design decision. |
| `code_audit_*.md`, `audit_supplement_*.md` | Only when running/comparing an audit. |
| `phase_b_calibration_plan.md`, `phase_b_verification_checklist.md` | Calibration phase work. |
| `pta_db_spl_migration_plan.md` | dB SPL migration pattern reference. |
| `*_testing_plan*.md`, `*_checklists.md` | Test planning. |
| `rew_inverse_filter_instructions.md` | REW / IR generation workflow. |
| `overview.md`, `other_documentation_overview.md` | High-level orientation only. |
| `core_working_code.md` | Snapshot of working code — prefer the actual `.py` files. |
| `deprecated_code_for_major_refactoring.md` | Refactor planning only. |

## Reference PDFs / external — open ONLY for spec questions

| File | When |
|------|------|
| `MultiThreshold_Users_Manual_ZH.pdf` | Verifying a paradigm against MultiThreshold spec (e.g. §5.3 IFMC/TMC). |
| `Lecluyse2013IJAprofiles.pdf` | TMC/IFMC metrics, profile protocol. |
| `Documentation_multiThreshold_UZH_UPDATE.docx` | UZH-modified protocol details. |
| `PROLACTIN_audiometric_tests_prague.pdf`, `PROLACTIN_miro_block_diagrams.pdf`, `PROLACTIN_paradigm_plan_overview.csv` | Project planning/architecture overview. |
| `A_simple_sdis_R_.pdf` | Stats/analysis reference. |

**Rule of thumb:** if the answer is in the latest changelog or this manifest,
don't open the source. If it's a code change, open only the in-scope `.py`
file(s). Reach for PDFs only to settle a spec question against the primary source.
