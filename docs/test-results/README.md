# Test results (sanitized)

Hardware evidence is published here only after sanitising it. That means no personal photos, no
serial numbers, no owner EXIF fields and no OEM bytes. Each result links to its experiment record in
[`../evidence/experiments/`](../evidence/experiments/).

| Date | Experiment | Summary |
|---|---|---|
| 2026-11-14 | [EXP-0001](../evidence/experiments/EXP-0001-usb-enumeration.md) | Reference unit is USB `0839:003C`, Bulk-Only mass storage; 512 MB-class card, MBR + FAT16, 16 KiB clusters |
| 2026-11-15 | [EXP-0002](../evidence/experiments/EXP-0002-internal-memory-lun.md) | With no card, the internal memory is the only LUN: 25,120 sectors, FAT12 at LBA 57; about 3.7 MiB of NAND hidden |
| 2026-11-15 | [EXP-0003](../evidence/experiments/EXP-0003-firmware-version-and-boot-sectors.md) | Firmware **M4051S-0525**; camera formatter fingerprint (blank OEM, `E9 00 00`, cluster-aligned data) |
