# Exposure architecture: native M mode (EXP-01, EXP-02)

## What the stock camera documents

- Program AE, multi/spot metering, EV ±2 in 0.5 steps, ISO Auto/100/200/400 (S1).
- **Night** scene mode: the user picks shutter (8 s–1/1000 s) and aperture (F3.5/F7.0) on a
  screen opened with **+/-**, using LEFT/RIGHT for shutter and UP/DOWN for aperture, then +/- to
  save (S2).
- Outside Night mode the slowest shutter is 2 s.
- The stock Night-mode menu offers **AUTO, 1/8, 1/2, 1, 2, 3, 4, 6 and 8 s** (EXP-0004; 1/4 s
  unconfirmed). Manual control covers only the slow end. 1/15 s to 1/1000 s exist only within the
  documented range, presumably reached by auto-exposure (H-012). `digimax exposure table` marks
  the menu values *observed* and the rest *candidate*.
- **Implication:** M mode needs the auto-exposure shutter routine for fast speeds, not just the
  Night-mode handler. Characterise the shutter (H-012) before offering those speeds.

## Proposal

A dedicated `M` mode next to Auto / Program / Scene. If adding a mode turns out to be unsafe, fall
back to a reversible overlay on Night mode. It should reuse the stock shutter, aperture/ND and
analog-gain routines rather than drive the hardware directly.

```text
+--------------------------------+
|  M    125   [|||]              |    top row: mode, shots left, battery
|                                |
| [1/60]  F3.5   ISO100          |    lower row: shutter / aperture / ISO; [ ] = selected while editing
|  meter -2.-1.0.+1.+2 (+0.7 EV) |    advisory meter only
|              ^                 |
+--------------------------------+
```

Run `uv run digimax exposure mock plusminus right down right plusminus --scene-ev 10` to drive
the state machine (`tools/digimax/exposure.py`).

| Key | Not editing | Editing |
|---|---|---|
| +/- | open the editor (draft = committed) | validate → commit and close, **or** stay open showing why the combination is invalid |
| UP / DOWN | — | select row (shutter → aperture → ISO) |
| LEFT / RIGHT | — | step the value; clamp at the ends, never wrap |
| MENU | stock menu | cancel and revert the draft |
| reset (TBD gesture) | restore defaults | restore defaults |
| shutter | capture with the committed settings, or refuse with a reason | — |

## Invariants

1. **No automatic override.** Metering never changes a selected value. Tested by
   `test_meter_is_advisory_and_never_changes_settings`.
2. **Invalid combinations are explained, not silently fixed.** The editor stays open and keeps the
   user's values. Tested by `test_invalid_combination_is_explained_not_silently_fixed`.
3. Only proven values are offered: shutter steps from the measured baseline, F3.5/F7.0 only,
   ISO 100/200/400. Do not call F7.0 a "diaphragm" until H-004 is resolved.
4. EXIF reports the **effective** settings (EXP-02), checked against optical measurements, because
   EXIF alone proves nothing.
5. Flash: explicit Off/On/Slow-sync choice using the stock flash timing. Never change charge
   control.
6. Persistence: a versioned, checksummed record in an isolated, verified configuration area. If no
   safe area is found, settings last for the session only. Never write undocumented EEPROM or
   calibration offsets.
7. All stock modes and factory reset keep working unchanged.

## Stretch (only after characterising CCD clocks, noise, thermal and shutter limits)

A/S priority modes, exposures longer than 8 s, more gain steps, and dark-frame subtraction for
long exposures.
