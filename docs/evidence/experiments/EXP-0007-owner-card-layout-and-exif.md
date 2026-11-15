# EXP-0007: Owner's SD card: boot area, formatter and EXIF statistics

- **Date:** 2026-11-15
- **Operator:** AI agent (remote, read-only); owner present
- **Kind:** observed on stock
- **Device / profile:** `a402`, A402-REF-1, firmware `M4051S-0525`, with the owner's 512 MB-class SD
  card (the same card as EXP-0001)
- **Approval:** owner read permission (2026-11-15). Nothing was written to the camera or the card.
- **Method:** a read-only `FileStream` on the verified camera disk (refused unless it was 504,365,056
  bytes). (a) The first 1024 raw sectors (MBR, boot sector, FATs, root directory and the first
  directory clusters). (b) The first 128 KiB of each JPEG (the EXIF headers only). Both were copied to
  the private workspace and deleted from the laptop. Analysed with `digimax card check` on a sparse
  full-size image made from (a), and with `digimax exif --summary` on (b).

## Results

### Layout

| Field | Value |
|---|---|
| MBR | one partition, **not** bootable, type `0x06`, LBA 32, 984,832 sectors; MBR boot code all zero; LBA 1–31 all zero |
| Boot sector jump / OEM | **`EB 00 90`** / 8 **spaces** |
| Boot code | none (all zero) |
| BPB | 512 B/sector, 32 sectors/cluster, 1 reserved, 2 FATs × 121 sectors, 512 root entries, 984,832 sectors, media `F8` |
| Hidden sectors / sectors-per-track / heads | **0 / 0 / 0** (although the partition starts at 32) |
| FAT type | FAT16 (30,767 clusters); 30,241 free |
| Data area | starts at LBA 307: **not** cluster-aligned |
| DCF | `DCIM\100SSCAM`, 23 DCF-named files |

### EXIF (n = 18 JPEGs on the card)

Make/Model/Software `Samsung Techwin co., Ltd.` / `Digimax A402` / `M4051S-0525` × 18. Program AE ×
18, **F3.5 × 18, ISO 200 × 18**, EV 0, centre-weighted. Flash fired × 12. Exposure times: 1/30 × 12,
then 200/1723, 1000/6529, 125/1237, 125/1421, 8/15 and 1000/1077 s (up to **0.93 s**).
**Orientation:** 1 × 14, **6 × 3, 8 × 1**. All 26 internal-memory photos have Orientation 1.

## Interpretation

- **Observed (F-052):** this card was **not** formatted the way the camera formats internal memory
  (F-028), nor by Windows (`MSDOS5.0` with boot code), Linux dosfstools (`mkfs.fat`) or the SD
  Association formatter (which aligns the data area). It carries a second, unidentified embedded
  formatter's fingerprint. It could be the camera's *card* format routine (if it differs from the
  internal one), another device, or a factory format. `digimax card check` now labels this signature.
  **To settle it:** format an expendable card in the camera (SD-01, #8) and compare.
- **Inferred (F-053):** the A402 has no documented orientation sensor, so Orientation 6/8 on four card
  photos means they were rotated by a host or other device that rewrote EXIF. The card's metadata has
  therefore been modified outside the camera. Treat card-side EXIF as possibly host-altered;
  internal-memory EXIF (all Orientation 1) is a cleaner baseline.
- Combined with EXP-0006 (n = 44 shots): AE always chose **F3.5 and ISO 200**. Exposure times are
  continuous, from 1/30 to 0.93 s. No shot faster than 1/30 s has been observed yet, but the
  shots are mostly indoors.

## Raw evidence

| File (private workspace) | SHA-256 |
|---|---|
| `dumps/A402-REF-1-card-head-1024s.bin` | `4af2e9f3d374e8eb63107ffaaac93a7e108e7d68710cdf44026125d58a7360ef` |
| `analysis/EXP-0007-card-exif.json` | `1989118cf4461ebba85faa75ff04ec11a9cf113dc612d097a139fb6914ecc610` |
| `camera/EXP-0007-run.txt` | `6f153e5992b4439d4db3bb21ebffffe20e35edaadf25b4f75c8ce81147f1050d` |
