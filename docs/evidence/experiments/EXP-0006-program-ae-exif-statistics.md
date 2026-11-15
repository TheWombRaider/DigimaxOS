# EXP-0006: Exposure statistics from stock Program-AE captures (EXIF)

- **Date:** 2026-11-15
- **Kind:** observed on stock (existing captures, offline analysis)
- **Device / profile:** `a402`, A402-REF-1, firmware `M4051S-0525`
- **Data:** the 26 JPEGs in internal memory, read from the private EXP-0005 image with
  `digimax.exif` (identity and exposure tags only; no dates, GPS or owner fields; file names not
  published). Only aggregate statistics are given here.
- **Limitation:** these are the owner's casual shots, mostly indoors with flash. They are not a
  controlled test (see docs/test-plans/exposure-baseline.md).

## Results (n = 26)

| Tag | Values |
|---|---|
| Software | `M4051S-0525` × 26 |
| ExposureProgram | 2 "normal program" × 26 |
| FNumber | **3.5 × 26** (F7 never chosen) |
| ISOSpeedRatings | **200 × 26** |
| ExposureBiasValue | 0 × 26 |
| MeteringMode | 2 (centre-weighted average) × 26 |
| Flash fired | yes × 23, no × 3 |
| FocalLength | 146/25 = 5.84 mm; MaxApertureValue 18/5 (APEX 3.6 ≈ f/3.48) |
| WhiteBalance, ExposureMode, SceneCaptureType, ShutterSpeedValue, ApertureValue | absent |

**ExposureTime** (seconds, rational as written by the camera):

| Value | ≈ | Count |
|---|---|---|
| 1/30 | 0.0333 | 7 |
| 125/3046 | 0.0410 | 1 |
| 1000/18467 | 0.0542 | 1 |
| 1/15 | 0.0667 | 2 |
| 125/1237 | 0.1011 | 2 |
| 2/15 | 0.1333 | 1 |
| 1000/6529 | 0.1532 | 1 |
| 250/1237 | 0.2021 | 1 |
| 1000/4617 | 0.2166 | 2 |
| 250/1077 | 0.2321 | 2 |
| 4/15 | 0.2667 | 1 |
| 500/1421 | 0.3519 | 2 |
| 250/663 | 0.3771 | 1 |
| 250/577 | 0.4333 | 2 |

## Interpretation

- **Observed (F-048):** auto-exposure writes **continuously variable** exposure times (for example
  1000/18467 s). It does not quantise to stops, so the shutter is controlled in fine time units
  (probably the CCD electronic shutter, in line or clock periods). This **supports H-012**: the
  firmware's shutter routine accepts arbitrary durations, so an M mode could offer fine steps within
  the hardware range.
- **Observed (F-049):** in these 26 Program-mode shots, AE never chose F7 and always used ISO 200.
  This fits the owner's report that ISO and aperture cannot be set outside Night mode (F-045). It
  does not prove that AE never uses F7 or other ISOs, since these are dim scenes. A bright-light
  series is needed (H-004).
- 1/30 s is the most common value, and many slow values were used with flash. Whether 1/30 is a
  flash-mode limit or hand-holding limit needs a controlled test.
- The `Software` string is constant, confirming F-033 across 26 files.

## Raw evidence

| File (private workspace) | SHA-256 |
|---|---|
| `analysis/EXP-0006-internal-exif.json` (per-file tags, private) | `05b4d866f410d49c4e2cc2d13748025d4b526d621668ad26d7d29247d1eabdda` |
