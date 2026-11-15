# Test plan: stock exposure baseline and M-mode acceptance (EXP-01, EXP-02)

**Phase 1** (the stock baseline) runs on unmodified firmware. It needs only the owner's permission
to take pictures on a **scratch card**. **Phase 2** is the acceptance criteria for a future M mode.

## Setup (both phases)

| Item | Requirement |
|---|---|
| Camera | Reference unit, stock firmware, flash **off**, date imprint off, digital zoom 1.0×, macro switch on Normal |
| Power | Fresh matched NiMH (or new alkaline) cells; record the voltage before and after |
| Media | Expendable SD card ≤ 512 MB, formatted **in-camera** (not the owner's card) |
| Mounting | Tripod; camera position marked; self-timer 2 s to avoid shake |
| Target | Matte grey card plus a colour chart, filling about 60 % of the frame, at 1.5 m; nothing personal in frame |
| Light | Constant DC LED panel (no PWM flicker; check with another phone camera), measured with a light meter or calibrated app. Record EV100 at the target. Repeat the measurement at the end. |
| Shutter timing rig | Timed LED target: a microcontroller LED that steps through a 10×10 grid at 1 kHz (1 ms per cell), or a rotating-disc LED timer. The exposure time is read from the image. |
| Host | `uv run digimax exposure table --json > expected.json` for EV bookkeeping |

## Phase 1: stock baseline

### 1A. Menu discovery (no captures)
1. In Night mode, open +/- and step LEFT/RIGHT from end to end. **Record every shutter value
   shown**, in order. This replaces the candidate list in `tools/digimax/exposure.py`.
2. Step UP/DOWN and record every aperture value shown.
3. Is ISO selectable while in Night mode? Is EV compensation? White balance? Flash modes?
4. Leave Night mode and return. Power-cycle. Do the shutter and aperture persist? Record the
   answers.
5. Record which settings Program mode exposes, and whether ISO and EV coexist there.

### 1B. Exposure response (captures)
For each aperture (F3.5, F7.0) × ISO (100, 200, 400 *if selectable in Night mode*) × at least 6
shutter steps spaced over the range:
- take **3 captures** per setting
- save the original JPEG plus EXIF `ExposureTime`, `FNumber`, `ISOSpeedRatings`, `ExposureBiasValue`,
  `MeteringMode`, `Flash`, `Software`
- measure the mean of the linearised grey-patch luminance from the JPEG. Note that JPEG is
  tone-mapped, so build a response curve from known stops first.

Also, at a fixed shutter and ISO:
- F3.5 vs F7.0: is the brightness ratio exactly 2.0 EV? Does depth of field change? Photograph a
  slanted ruler. This tests H-004 (iris vs ND).

### 1C. Shutter timing
Photograph the timed LED target at each shutter step from 1/1000 to 1 s. Count lit cells to get
the effective exposure time. Use a stopwatch or audio recording for exposures ≥ 1 s. Report the
ratio of measured to nominal.

### 1D. Recording format
For each capture, record: run ID, nominal settings, EXIF settings, measured time, mean luminance,
clipping percentage and the SHA-256 of the file. Keep the images in the private workspace.
Publish sanitized results to `docs/test-results/` as `EXP-NNNN`.

## Phase 2: M-mode acceptance (future firmware)

| # | Criterion | Pass condition |
|---|---|---|
| A1 | Matrix coverage | Every exposed shutter × aperture × ISO combination is captured ≥ 3 times, or the combination is explicitly listed as unsupported with a reason |
| A2 | Monotonicity | Under fixed light, luminance changes monotonically and in the expected direction for each step (before saturation) |
| A3 | Step accuracy | Each 1-stop step measures 1.0 ± 0.3 EV (tolerance to be refined from the stock Phase 1 spread) |
| A4 | Shutter timing | Measured/nominal within the tolerance established for stock Night mode at the same setting, and no worse than stock |
| A5 | EXIF truth | EXIF `ExposureTime` / `FNumber` / `ISOSpeedRatings` equal the *effective* settings in 100 % of captures |
| A6 | No override | Across scenes from EV 2 to EV 15, the selected settings are never changed automatically (compare EXIF with the selection) |
| A7 | Invalid combinations | Every invalid combination shows a reason and does not capture with altered settings |
| A8 | Persistence | Behaviour matches the documented design (session-only or persisted) across mode change, power-cycle and factory reset |
| A9 | Flash | Off / On / Slow-sync behave as selected; no faster cycling than the stock flash |
| A10 | Repetition | 100 consecutive captures without a hang; low-battery warning still works |
| A11 | Stock regressions | Auto, Program, all Scene modes, movie, voice and playback unchanged against the Phase 1 baseline |

The automation (EXIF extraction, luminance analysis, report generation) will become
`digimax exposure analyse` (tracked issue).
