# PROLACTIN Session Changelog — 2026-03-26

## How to verify at session start

For each entry, check that the listed **key signature** is present in the project file.
If it's missing, the project file is out of date and needs to be replaced before starting work.

---

## Phase A1 — completed this session (prd_2026-03-26.md)

### `event_gen.py`
- **Change:** Wrap module-level `eg = EventGen()` in `if __name__ == "__main__":` guard
- **Key signature:** `if __name__ == "__main__":\n    eg = EventGen()`

### `paradigm_ifmc.py`
- **Change 1:** Deleted dead `update_streaks_and_difficulty()` method
- **Key signature:** method is ABSENT — `grep update_streaks_and_difficulty paradigm_ifmc.py` returns nothing
- **Change 2:** Garbage character cleanup (→, θ, μ, ± now correct UTF-8)
- **Key signature:** `[Masker tone 108ms] → [Gap 10ms] → [Probe tone 16ms]`

### `paradigm_tmc.py`
- **Change:** Deleted dead `update_streaks_and_difficulty()` method
- **Key signature:** method is ABSENT — `grep update_streaks_and_difficulty paradigm_tmc.py` returns nothing

### `adaptive_paradigm.py`
- **Change 1 (A5):** Replace O(n²) pd.concat with list accumulator
- **Key signature:** `self._data_rows = []` in `__init__`
- **Change 2 (A5):** Threshold write-back keeps `_data_rows` in sync
- **Key signature:** `self._data_rows[last_idx]['threshold_dB'] = self.threshold_dB`
- **Change 3 (A6):** Gate TP/FN/FP/TN performance summary on verbose flag
- **Key signature:** `if self.verbose:\n                print(f"Performance Summary:")`
- **Change 4 (A6):** Move `import random` to top level; remove inline import
- **Key signature:** `import random` in top-level imports (line ~17)
- **Change 5 (A2):** Add `randomize_config_order=True` param; shuffle unwrapped_params
- **Key signature:** `if self.randomize_config_order and len(self.unwrapped_params) > 1:`
- **Change 6 (A3):** Add `_at_wrv_limit`, `_aborted_by_operator` flags
- **Key signature:** `self._at_wrv_limit = False       # Flag: adaptive param hit min/max this trial`
- **Change 7 (A3):** Add `_clip_adaptive_param()` and `notify_wrv_limit()` methods
- **Key signature:** `def _clip_adaptive_param(self):`
- **Change 8 (A3):** `notify_wrv_limit()` handles abort_paradigm / abort_config / continue
- **Key signature:** `if choice == 'abort_paradigm':`
- **Change 9 (A3):** Gate `write_data_to_disk()` on `_aborted_by_operator`
- **Key signature:** `if self._aborted_by_operator:`
- **Change 10 (A2.3):** Add `_write_temp_data()`, `_delete_temp_data()`, `_temp_data_path()` 
- **Key signature:** `def _write_temp_data(self):`
- **Change 11 (A2.3):** Call `_write_temp_data()` after each config completes
- **Key signature:** `# Write temp CSV after each config (crash recovery)\n            self._write_temp_data()`
- **Change 12 (A2.3):** Call `_delete_temp_data()` on clean paradigm completion
- **Key signature:** `self._delete_temp_data()`
- **Change 13 (A2.5):** Garbage character cleanup (θ, — now correct UTF-8)
- **Key signature:** `"least-squares, best-fit procedure, with θ and k as free parameters."`

### `operator_gui.py`
- **Change 1 (A3):** Replace `show_wrv_warning()` with blocking overlay version
- **Key signature:** `overlay = tk.Frame(self.plot_frame, bg="#922b21")`
- **Change 2 (A3):** Three options: abort paradigm (default), abort config, continue
- **Key signature:** `result = {'choice': 'abort_paradigm'}`
- **Change 3 (A2.5):** Garbage character cleanup (— now correct UTF-8)
- **Key signature:** `Operator GUI — Real-time monitoring display for paradigm execution.`

### `paradigm_dli.py`
- **Change:** Garbage character cleanup (→ now correct UTF-8)
- **Key signature:** `- Answer matches louder_tone → TP (correct discrimination)`

### `paradigm_pta.py`
- **Change:** Garbage character cleanup (± now correct UTF-8)
- **Key signature:** `- Small steps (±2 dB) after first reversal`

### `paradigm_itd.py`
- **Change 1 (A2.2):** Fix `create_itd_stereo()` — onset-aligned, offset-aligned, no trimming of delayed channel signal
- **Key signature:** `delayed = np.concatenate([np.zeros(delay_samples), mono_wave[:-delay_samples]])`
- **Change 2 (A2.2):** Fade-out applied per-channel after truncation inside `create_itd_stereo()`
- **Key signature:** `def create_itd_stereo(self, mono_wave, itd_ms, fs, fade_samples=0):`
- **Change 3 (A2.2):** Only fade-in applied to mono_wave before stereo split
- **Key signature:** `# Apply fade-in only here. Fade-out is applied per-channel inside`
- **Change 4 (A2.5):** Garbage character cleanup (μ, × now correct UTF-8)
- **Key signature:** `min_itd = self.inner_var.data.get('min', 0.01)   # 0.01 ms = 10 μs (human threshold)`

---

## Files changed this session (need to be re-uploaded to project)

| File | Changes |
|------|---------|
| `event_gen.py` | A1 |
| `paradigm_ifmc.py` | A1, A2.5 |
| `paradigm_tmc.py` | A1 |
| `adaptive_paradigm.py` | A2, A3, A5, A6, A2.3, A2.5 |
| `operator_gui.py` | A3, A2.5 |
| `paradigm_dli.py` | A2.5 |
| `paradigm_pta.py` | A2.5 |
| `paradigm_itd.py` | A2.2, A2.5 |

---

## Documentation added this session

- `prd_2026-03-26_second_pass.md` — updated PRD with Phase A2 items and revised Phase B

---

## Remaining Phase A2 items (next session)

| # | Task | Priority |
|---|------|----------|
| A2.1 | Editable params in setup dialog | High — **start here** |
| A2.4 | IFMC/TMC fade verification | Medium — deferred |
| A2.6 | Operator GUI label fixes | Medium — deferred |
| A2.7 | Keyboard nav in setup dialog | Medium — blocked by A2.1 |
| A2.8 | Demo mode | Low |
| A2.9 | ITD independent noise | Low |
