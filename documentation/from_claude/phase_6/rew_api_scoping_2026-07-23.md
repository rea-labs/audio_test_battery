# REW HTTP API — scoping + discovery checklist

_Pre-PRD. 2026-07-23. Tracks open issues **L42** (the work) and **T19** (the
licence decision). Not a PRD: no acceptance criteria, no file-by-file diff plan.
Purpose is to settle scope and the free-vs-Pro question so a real PRD can be
written._

---

## 1. Target workflow

Eric's laptop, artificial ear available, REW + PROLACTIN on the same machine.

**Wanted:** set the headphone on the coupler, then only ever re-seat or press
Enter. No cursor placement, no typing numbers, no manual save.

**Today**, per measurement (`measure_runner.py`):

1. Enter to play -> `subprocess.run(level_validator ...)` **blocks for `--dur`
   (default 30 s)**
2. operator watches the REW RTA and reads the band value off the cursor
3. process returns, operator types the number
4. runner writes the CSV via temp-file + atomic replace

**Cost of that loop, measured:** the 2026-07-23 unit X session was 131
measurements. At the 30 s default that is ~65 min of pure tone-playing before
counting any human time, and three doubled-keystroke typos occurred before
`--guard` existed to catch them.

**With the API:** step 2 becomes a GET, step 3 disappears, and the tone can be
terminated as soon as the reading settles instead of running its full duration.
Same 131 readings at ~4 s settling is ~9 min. The typo class is removed at
source rather than guarded.

---

## 2. Prerequisites

The API server is **off by default**. Not currently running on the lab PC and
presumably not on the laptop either.

```
# macOS, start REW with the API enabled
open -a REW.app --args -api
```

Or enable it in REW's API preferences, or tick "Start the API when REW starts".

- Default bind: `127.0.0.1:4735`. **Localhost only** unless started with
  `-host "0.0.0.0"`. For the laptop-with-ear setup localhost is correct and no
  network exposure is needed — the word "remote" in the original framing is
  misleading, this is same-machine IPC over HTTP.
- Custom port: `-port 4567`. Ports below 1024 ignored.
- `-nogui` exists but is **not** wanted here: the RTA display is the fallback
  sanity check while the integration is still being trusted.
- Version: project is on **v5.31.3 (25 Jul 2024), which is the current
  release** — no upgrade needed to have the API. Correcting an earlier claim in
  this project's notes that the API was beta-only; only the spl-logger endpoints
  were recent beta additions.

---

## 3. Discovery checklist

Desk task. Needs REW running, no artificial ear, no headphones. Roughly 30 min.
Do this before writing a PRD — several design choices below depend on the
answers.

REW serves its own OpenAPI spec, so the surface does not have to be guessed:

- swagger-ui: `http://localhost:4735`
- spec: `http://localhost:4735/doc.json` (or `/doc.yaml`)

### D1 — Confirm the API is up

```
curl -s localhost:4735/application/errors
```

Expect a JSON list (probably empty). Non-empty response of any kind = server up.

### D2 — RTA status and configuration

```
curl -s localhost:4735/rta/status
curl -s localhost:4735/rta/configuration
```

**Confirm:** whether the RTA is enabled and running, and what the current
resolution and averaging mode are. The 2026-07-23 protocol reads a
**1/12-octave** band, so the fractional-octave mode and its PPO value are what
matter.

### D3 — The decisive read: does captured data carry usable band values?

```
curl -s "localhost:4735/rta/captured-data?unit=SPL" > rta.json
```

**Confirm all five:**

1. `startFreq` present
2. `ppo` present (fractional-octave capture) — if a `freqStep` comes back
   instead, the RTA is in spectrum mode, not fractional-octave; switch it
3. `magnitude` present as a Base64 string
4. the decoded array length is plausible for the span
5. `unit=SPL` is honoured (default is SPL; `/rta/captured-data/units` lists the
   alternatives)

Decode — note the byte order, this is the easiest thing to get silently wrong:

```python
import base64, numpy as np
mag = np.frombuffer(base64.b64decode(s), dtype=">f4")   # BIG-endian float32
```

Frequency of index `i`:  `startFreq * 2 ** (i / ppo)`

### D4 — Freshness fields

Same response. **Confirm** the nanosecond `timestamp` and the running sample
count since the RTA was last started/restarted are both present and both
advancing between two successive GETs.

These are the whole staleness defence. Without them there is no way to know a
reading was captured after the tone started rather than before.

### D5 — Cross-check against the cursor

Play a known tone with `level_validator`, read the value off the RTA cursor by
hand, and compare with the value the decode picks for the same band.

**Pass = agreement to within ~0.05 dB.** This is the one step that actually
validates the whole chain, and it is cheap. Do it at 1 kHz and at 125 Hz (the
noisiest band on 2026-07-23).

### D6 — Which POSTs are free?

The docs say GET is always available and POST works for most endpoints, but that
**automated sweep measurements** require Pro. That wording does not say where
the line falls for the RTA. Test:

```
curl -s localhost:4735/rta/commands                       # list
curl -s -X POST localhost:4735/rta/command -H 'Content-Type: application/json' -d '{"command":"..."}'
```

**Confirm:** can the RTA be started, stopped, or its averaging reset by POST
without a Pro licence? A 4xx with a licence message answers T19 partly for free.

**If POST to `/rta/command` is gated**, Path A still works — see the
zero-POST design in section 4.

### D7 — SPL meter, for comparison only

```
curl -s localhost:4735/spl-meter/1/levels
curl -s localhost:4735/spl-meter/weightings
```

**Confirm** Z weighting is selectable (project convention, settled under H7) and
note whether the meter's broadband number tracks the RTA band value. 2026-07-23
found broadband and 1/12-octave agreeing to 0.03 dB at 1 kHz, so this is a
cross-check, not a second method.

### D8 — Subscriptions (optional, only if polling proves awkward)

`/rta/subscribe` accepts `{"url": "http://127.0.0.1:5374/..."}` and REW POSTs on
each update. **Confirm** it fires. Requires running a small HTTP server inside
the runner — only worth it if D4's polling turns out to be unreliable.

### D9 — Mic calibration file in use

```
curl -s localhost:4735/audio/input-cal
```

**Confirm** it reports the loaded cal file path. If it does, this is a
machine-readable answer to **L22** (4157 cal file unverified, 4153's reused) and
can be logged into the measurement CSV automatically — provenance for free.

### D10 — REW build version

**Confirm** whether the running build's version is exposed anywhere under
`/application`. If it is not, the fallback is the `rewVersion` field carried on
every measurement summary (`/measurements/:id`) — take one throwaway measurement
and read it from there, or accept recording it manually once per session.

Worth having because REW is part of the measurement chain: if a build changes
between unit X and units A/B, that should be visible in the data rather than
inferred later. Same argument as the "do not upgrade mid-campaign" caution in
section 2.



**This is the whole of Eric's stated workflow.** It needs no licence.

### Scope

One integration point. In `measure_runner.py`'s main loop, this:

```python
if subprocess.run(cmd).returncode != 0:
```

becomes: `Popen(cmd)` -> wait for the RTA reading to settle -> read the band ->
terminate the tone -> record. The `state` machine collapses from
`ready -> play -> value` to `ready -> play+read+record`.

Everything else stays: playback still goes through `level_validator` and
PROLACTIN's own calibration pipeline (that is the point — the API is on the
**measurement** side only), the CSV schema is unchanged, and the temp-file +
atomic-replace write is unchanged.

### Zero-POST design (preferred)

If the RTA is already running and free-running, the runner never needs to POST
anything — it only polls `/rta/captured-data`. That keeps Path A entirely inside
GET, which is unambiguously free, and sidesteps D6 completely.

Settling without a reset command:

1. note `sampleCount` before starting the tone
2. start the tone
3. poll every ~250 ms; discard any response whose sample count has not advanced
   past the pre-tone value
4. accept when the target band's value is stable within ~0.05 dB over N
   consecutive updates (N ~ 4), or fail out after a timeout
5. terminate the tone

If D6 shows RTA reset is free, use it — it makes settling faster and more
deterministic. Treat it as an optimisation, not a dependency.

### Seat handling — the "only occasionally hit Enter" part

The CSV already has a `seat` column. So:

- auto-advance through every row sharing a `seat`, no keypress at all
- stop at a seat boundary with "Re-seat the headphone, Enter when ready"
- on resume, run the **L41 seating gate automatically**: play 60 dB @ 1 kHz,
  read it, refuse to start the block if it is outside ~0.3 dB

That gate is currently a discipline nobody will remember. Automated, it would
have caught the two suspect mounts on 2026-07-23 at measurement zero instead of
after five.

### Guards that must survive

`--guard` exists because a human types. Removing the human does not remove
errors, it changes their shape. Keep the plausibility check and re-point it:

| old failure | new failure | defence |
|---|---|---|
| doubled keystroke | reading captured before the tone started | D4 sample-count check |
| transposed digits | RTA stopped, stale array returned | D4 timestamp not advancing |
| wrong row | wrong frequency band index | assert chosen bin centre is within half a band of `freq_hz` |
| — | tone never actually played | existing `level_validator` returncode check |
| — | reading during the fade | settle-stability check |

Plus: keep the `>15 dB from requested` rejection. It is cheap and it catches
everything above at once.

### Failure behaviour — decided: block, never fall back silently

**A failed or unreachable API stops the run.** No silent degradation to the
manual prompt. The rejected alternative was a quiet fallback, which would let a
session end up half automatic and half hand-typed with no record of which rows
were which — the exact invisible-state problem H11 is about, one layer up.

On first failure the runner halts and makes the operator choose explicitly:

```
  !! RTA read failed: <reason>
     [r] retry   [m] manual entry for the rest of this session   [q] quit
```

- the choice is **remembered for the session**, so a dead API does not re-prompt
  on every row
- picking `m` walks the full manual sequence as it works today — play, read the
  cursor, type, `--guard` check
- **every row records which mode produced it** (`read_method` below), so a mixed
  session is auditable afterwards instead of indistinguishable

Startup does the same: if the API is not reachable when the runner launches, say
so and require the operator to pick before any tone plays, rather than
discovering it at row 1.

---

### Provenance logging — decided: log broadly

If a machine produces the number, the record has to show how. Proposed columns,
appended to the existing measurement CSV:

| column | value | why |
|---|---|---|
| `read_method` | `api` / `manual` | the audit trail the blocking-failure design depends on |
| `band_center_hz` | bin centre actually read | catches a wrong-band / off-by-one pick; compare against `freq_hz` |
| `band_index` | array index chosen | reconstructs the pick from the raw response |
| `band_ppo` | RTA points-per-octave | 1/12-octave = 12; records the resolution the reading was taken at |
| `settle_span_db` | spread across the accepted window | per-reading quality metric, useful well beyond this feature |
| `settle_seconds` | time to settle | flags a marginal seal or a noisy band before the numbers are analysed |
| `rta_sample_count` | count at read | freshness evidence (D4) |
| `rta_timestamp_ns` | timestamp at read | freshness evidence (D4) |
| `mic_cal_file` | from `/audio/input-cal` | see D9 — retires the L22 guesswork per measurement |
| `rew_version` | see D10 | REW is part of the measurement chain; a build change should be visible in the data |

**This costs nothing downstream, verified.** `calibration_check.py` reads with
`csv.DictReader` and validates only a *minimum* set (`ear`, `requested_spl`,
`measured_spl`) — extra columns are ignored, so no change is needed there.

Two conventions keep the human-facing artifact clean:

- **`--template` keeps emitting only the existing columns.** The blank CSV
  doubles as the bench checklist; ten machine columns would wreck it. The runner
  adds the provenance columns when it first writes, mirroring how it already
  handles `measured_spl` (add-if-missing) and `timestamp` (write-if-present).
- **One file, not a sidecar.** A separate provenance log was considered and
  rejected: the CSV already has a temp-file + atomic-replace write, and a crash
  between two writes would desync the pair. 131 rows x ~19 columns is trivial
  data; integrity beats tidiness here.

Manual rows leave the API-specific columns blank, which is itself the signal.

### Risks

- REW and `level_validator` (PsychoPy/PTB) already share the interface
  concurrently today — REW on input, PROLACTIN on output. Proven on
  2026-07-23, not a new risk.
- Main residual risk is the settle logic accepting a reading too early. That is
  what `settle_span_db` and `settle_seconds` are for: if the logic is wrong, the
  evidence is in the data rather than invisible.

### Effort

Small. One function to fetch-and-decode, one settle loop, one call-site change,
the seat-block restructure, the failure-mode prompt and the extra columns. No
new dependencies beyond `urllib` and `numpy`, both already present.

---

## 5. Path B — Pro tier, scripted sweeps

### What it would be

Script the inverse-filter generation currently done by hand in
`rew_inverse_filter_instructions.md` rev 6: run the sweep, then drive
`/measurements/process-measurements` with the **Arithmetic** process —
`1 / A` with `maxGain`, `lowerLimit`/`upperLimit`, `targetLevel`, `autoTarget`,
`excludeNotches`. Those are exactly the rev-6 dialog settings, exposed as JSON.

Also reachable: `/measurements/:id/frequency-response` for automated flatness
verification, and `/spl-meter/{id}/command` `Calibrate` with the dB SPL figure
as a parameter — i.e. the B&K 4231 94 dB step becomes scriptable.

### The honest case for it

**Not time.** IR generation happens perhaps once per headphone unit for the life
of the project — call it 5-8 sessions total, including L39's unit X right-channel
regeneration. Automating that has poor ROI against Path A's 131-readings-per-unit.

**Reproducibility.** Every unit's IR would be generated with byte-identical
settings, scripted and diffable, instead of depending on operator recall of a
rev-6 document. For a clinical-adjacent battery that is a real provenance
argument, and it is the same class of concern as H11 (silent unit-specific
divergence that no current check would catch). It also bears on L11 and on the
re-measure the ER-2 splitter migration will force.

### Cost

- **One-time fee**, single user, valid on any computer they use.
- **Reported at USD 100** at launch (AV NIRVANA, Oct 2020). **The current figure
  did not render in the page fetch — verify on the purchase page before
  budgeting.** Fixed prices offered in USD, GBP and EUR.
- Requires V5.20+ (project is on 5.31.3, fine).

### The catch, and it is a real one

The upgrades page describes the Pro licence as unlocking **multi-input capture**
and **STI**. Both are worthless here: there is one coupler and one mic, so
multi-input has nothing to capture; STI is a room speech-intelligibility metric.

API sweep control is mentioned **only in the API help page**, not on the
upgrades page. So the purchase would be made for a capability that is not
advertised as part of what is being sold. The page also says the 30-day refund
covers the case where *multi-input capture* does not meet your needs — it says
nothing about API automation.

**Recommended before spending anything:** email `proupgrades@roomeqwizard.com`
and ask directly whether the Pro licence enables API-driven sweep measurements,
and what exactly is gated. Free, definitive, and removes the ambiguity. Also
worth asking whether an academic/research context changes anything.

### Verdict

**Do not buy yet.** Path A delivers the entire stated workflow for nothing.
Revisit Path B only when (a) Path A is working, (b) the email above has
confirmed what is actually gated, and (c) the remaining IR-generation volume is
known — which depends on the ER-2 splitter migration (L27) and on whether L39
gets done at all.

---

## 6. Sequencing

| # | Step | Needs ear? | Needs licence? |
|---|---|---|---|
| 1 | Section 3 discovery checklist | no | no |
| 2 | Email `proupgrades@` re: what Pro gates | no | no |
| 3 | Path A: fetch + decode + settle helper | no | no |
| 4 | Path A: runner integration, seat blocks, L41 gate | no | no |
| 5 | Validate against a manual run (D5 at scale) | **yes** | no |
| 6 | Decide T19 on evidence | — | — |

Steps 1-4 are all doable in the current no-ear window. Step 5 is the first thing
to do when the ear is back, and it should be done **before** the A/B campaign
(M23/M22), not after — the payoff scales with readings still to take, and at
least two more units are owed (blocks 2 and 3 from 2026-07-23).

---

## 7. Open questions

_Decided 2026-07-23, recorded here so the next chat does not re-open them:
**failure blocks** rather than falling back silently (section 4), and
**provenance is logged broadly** into the measurement CSV (section 4). What
remains:_

1. **Auto-advance granularity** — pause per seat block (proposed), per
   frequency, or per row? Per-seat is the least interaction but places the most
   trust in the settle logic before a human looks at anything. Worth starting
   stricter (per row) for the first live session and loosening once the settle
   logic has been watched working.
2. **Settle tolerance and timeout** — 0.05 dB over 4 updates with a 15 s timeout
   is a placeholder. Set it from the actual RTA averaging configuration found in
   D2, not in advance.
3. **Does the `--guard` threshold change?** It is currently 15 dB from requested,
   sized for typing errors. Machine failures land differently — a stale array or
   wrong band can be off by a plausible-looking amount. Consider tightening it
   for API reads, or leaning on `band_center_hz` and the freshness fields
   instead, which catch those cases directly.
4. **Retro-fit provenance columns to the existing unit X CSV?** The 131 rows from
   2026-07-23 were all manual. Leaving them blank is honest; back-filling
   `read_method = manual` makes the column non-null everywhere and easier to
   group by. Cosmetic either way.
5. **Anything else worth capturing while the API is open?** `/rta/configuration`
   is read once per session and could be logged whole, rather than picking out
   `band_ppo`. Cheap insurance against discovering later that some other RTA
   setting mattered.
