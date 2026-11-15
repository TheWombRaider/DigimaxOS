# EXP-0004: Stock Night-mode shutter menu (walk-through)

- **Date:** 2026-11-15
- **Operator:** TheWombRaider (owner), at the camera; reported verbally and transcribed
- **Kind:** observed on stock (UI only, no captures)
- **Device / profile:** `a402`, reference unit A402-REF-1, firmware `M4051S-0525`
- **Power:** fresh rechargeable AA cells
- **Media:** none needed (no captures)
- **Procedure:** Phase 1A of [docs/test-plans/exposure-baseline.md](../../test-plans/exposure-baseline.md):
  Night scene mode, then press +/- and step through the shutter values with LEFT/RIGHT.

## Actual result

Shutter values offered in the stock Night-mode +/- screen, as reported by the owner:

`AUTO`, **1/8, 1/2, 1, 2, 3, 4, 6, 8 s**

**1/4 s is unconfirmed.** The transcription of the spoken report is ambiguous between "1/8, 1/2" and
"1/8, 1/4, 1/2". It has been put to the owner for confirmation.

Not yet recorded: the aperture values (UP/DOWN), whether ISO, EV and WB can be changed in Night
mode, and whether the settings persist across a mode change or power-cycle.

## Interpretation

- **Observed (F-044):** stock manual shutter control is limited to **slow speeds (8 s to 1/8 s)**
  plus AUTO. The documented 1/1000 s fastest speed (S1) is presumably reached only by
  auto-exposure. Faster values are not user-selectable anywhere in the stock UI that we know of.
- Consequence for EXP-01: an M mode cannot simply re-expose the Night-mode list. Shutter speeds of
  1/15 s and faster need the auto-exposure path's shutter-setting routine, called with a
  user-chosen value. Whether that routine accepts arbitrary values is unknown (H-012). Until it is
  measured, those steps stay *candidates* in `digimax exposure table`.
- The step pattern 8-6-4-3-2-1 is a half-to-third-stop sequence at the slow end, followed by full
  stops (1, 1/2, [1/4], 1/8). EXIF of Night-mode captures will show whether the camera records these
  values exactly.
