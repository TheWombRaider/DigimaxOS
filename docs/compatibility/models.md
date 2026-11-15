# Model compatibility

| Model | Relationship | USB ID | Firmware base hash | Status |
|---|---|---|---|---|
| Samsung Digimax A402 | reference | `0839:003C` (verified, EXP-0001) | firmware `M4051S-0525` (EXIF; image hash unknown) | research |
| Kenox D402 | shares the A402 driver package (S10); likely the Korean-market version | `0839:003C` per INF (documented) | unknown | not tested |
| Digimax A400 / A403 / A503 | possibly related Sunplus designs; **no evidence** | unknown | unknown | not started (PORT-01) |

Porting rules (PORT-01): each model needs its own profile, its own recovery path and its own
hardware tests. Never install one model's firmware on another.
