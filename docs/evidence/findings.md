# Findings register

Each finding has an ID, a confidence level and its evidence. Do not delete entries. Mark them
**superseded** and link to the replacement.

| Confidence | Meaning |
|---|---|
| **verified** | Observed on the reference unit; experiment ID given |
| **documented** | Stated by an OEM or standards document; not yet observed |
| **inferred** | Follows from verified or documented facts by reasoning stated here |
| **contradicted** | Sources disagree; resolution pending |

## Device identity

| ID | Finding | Confidence | Evidence |
|---|---|---|---|
| F-001 | The reference unit enumerates as USB `0839:003C`, bcdDevice `0x0100`, single interface class 08/06/50 (Mass Storage, SCSI transparent, Bulk-Only Transport). Windows binds the in-box `USBSTOR` driver; no vendor driver is needed on modern hosts. | verified | EXP-0001 |
| F-002 | SCSI INQUIRY identity is vendor `SAMSUNG`, product `DIGITAL CAMERA`, revision `1.00`. The USB-reported device description is `DIGITAL CAMERA` padded with spaces. No USB serial number is reported (the host synthesises an instance ID). | verified | EXP-0001 |
| F-003 | The same VID:PID appears in Samsung's 2004–2005 Windows 98 driver INF ("Samsung Digital Camera", Samsung Techwin). | documented | S10 |
| F-004 | Product `003C` is not in the public `usb.ids` database. Vendor `0839` is Samsung Techwin. | documented | S11 |
| F-005 | The A402 and Kenox D402 share one driver package; Setup.ini names both. Kenox was Samsung's Korean-market brand, so D402 is very likely the same hardware, but this is not yet confirmed at board level. | documented / inferred | S10 |
| F-006 | No Samsung Techwin device appears in the Linux `gspca` Sunplus webcam driver. The A402 has not been shown to offer a webcam/streaming mode. | documented | S6 |

## SoC and memory

| ID | Finding | Confidence | Evidence |
|---|---|---|---|
| F-010 | The service manual's schematic section title names **SPCA536** ("2) SPCA536 DSP"), while its block diagram text shows **SPCA535**. The update file is labelled `MEGA536`. | contradicted | S3 |
| F-011 | The block diagram lists 256 Mbit SDRAM, 16 MB NAND, a 93C66 EEPROM labelled "SYSTEM", and 27 MHz and 32.768 kHz crystals. | documented | S3 |
| F-012 | One schematic section is titled "FlashROM-NandFlash-SD". This *suggests* a separate boot ROM or NOR flash besides the NAND, but the schematic image has not been transcribed. | documented (title only) | S3 |
| F-013 | The CPU core of the SPCA536 is **unknown**. Sunplus's own SPCA536 press material names no core. A related SPCA533A is reported to contain an 8032 (an 8051 variant), and an unrelated Sunplus camera's firmware disassembled plausibly as 8051. Neither fact transfers to the SPCA536 without evidence. | unknown | S12, S13 |
| F-014 | The SPCA536 was announced 2003-12-15 as a 16 MP DSC controller with JPEG and MPEG-4 codecs and a customer development environment. | documented | S13 |

## Storage

| ID | Finding | Confidence | Evidence |
|---|---|---|---|
| F-020 | With the owner's card inserted, the camera exposes **one** LUN: a 985,088-sector (504,365,056-byte) disk with 512-byte logical sectors. It does not expose internal flash as a second LUN while a card is present. | verified | EXP-0001 |
| F-021 | That card is partitioned MBR with one primary partition at LBA 32, 984,832 sectors, type `0x06` (FAT16 ≥ 32 MB, CHS-addressed), formatted FAT with 16 KiB clusters (30,767 clusters ⇒ FAT16 by cluster count). 224 sectors at the end of the disk are unpartitioned. | verified | EXP-0001 |
| F-022 | That layout (partition at sector 32, FAT16, 32 sectors per cluster) matches the SD Association's recommended format for 257–512 MB cards. *Who* formatted it (camera, PC, factory) is unknown until the boot sector's OEM name is read, which needs owner approval. | inferred | EXP-0001, S4 |
| F-023 | The card holds a DCF tree `DCIM\100SSCAM`. The firmware's DCF folder suffix is therefore probably `SSCAM`. This is to be confirmed by observing a folder the camera creates itself. | verified (presence) / inferred (creator) | EXP-0001 |
| F-024 | The manual guarantees cards only up to 512 MB. Larger SDSC cards have not been tested. The 512 MB figure is a guarantee, not a proven limit. | documented | S1 |
| F-025 | Windows created a `System Volume Information` folder on the owner's card **and in internal memory** (EXP-0002) when they were mounted read-write. Future sessions should avoid further host writes (eject safely; prefer read-only imaging or a read-only mount policy). | verified | EXP-0001, EXP-0002 |
| F-026 | The camera exposes a single USB LUN: the card when one is inserted, otherwise internal memory. The USB identity is the same in both cases. | verified | EXP-0001, EXP-0002 |
| F-027 | The internal-memory LUN is 25,120 sectors (12,861,440 bytes). Against the documented 16 MB NAND, about 3.73 MiB is not exposed to the host, which is the probable home of firmware and reserved blocks (H-010). | verified (size) / inferred (purpose) | EXP-0002, S3 |
| F-028 | The camera's own formatter (seen on internal memory) writes MBR + FAT12 (type 0x01, bootable flag set) at LBA 57, 16 KiB clusters, 2×3-sector FATs and 512 root entries. It leaves an OEM name of eight NUL bytes (corrected, EXP-0005), jump `E9 00 00` and no boot code, and aligns the data area to the cluster size (LBA 96). The MBR boot code is all zero. | verified | EXP-0003 |
| F-029 | DCF names on this unit: folder `100SSCAM`, files `S402nnnn.JPG`. EXIF 2.20 and FlashPix 1.00. | verified | EXP-0003 |

## Firmware acquisition

| ID | Finding | Confidence | Evidence |
|---|---|---|---|
| F-030 | The official Samsung support page for the A402 offers **no firmware**, only a 2008-dated USB driver and the manual. | documented | S9 |
| F-031 | The service manual's upgrade procedure: download "MEGA536" from the Samsung service site, format the card in the camera, copy the file onto the camera's removable disk over USB (not a card reader), then check the file name. No extension, folder or key combination is given. That the file must be copied *through the camera* (not with a reader) is notable. Why is unknown. | documented | S3 |
| F-032 | A public web search (2026-11-14) found no copy of `MEGA536` or any A402/D402 firmware file. The driver package contains no firmware. | negative result | S9, S10, searches recorded in the 2026-11-14 entry of docs/development/status.md |
| F-033 | The reference unit's firmware identifies itself as **`M4051S-0525`** (EXIF Software tag). The same string appears on another A402's 2006 photo. A `-0520` variant is reported by a search snippet but is unverified, so more than one build may have been released. | verified (own unit) / documented (S16) / unverified (S17) | EXP-0003, S16, S17 |

## Exposure

| ID | Finding | Confidence | Evidence |
|---|---|---|---|
| F-040 | Documented exposure space: shutter 2–1/1000 s (8–1/1000 s in Night mode), F3.5 and F7.0, ISO Auto/100/200/400, EV ±2 in 0.5 steps, multi/spot metering. | documented | S1 |
| F-041 | Night mode lets the user choose shutter (LEFT/RIGHT) and aperture (UP/DOWN) from a +/- screen. The individual shutter steps are **not documented** in the text we have. | documented | S2 |
| F-044 | The stock Night-mode shutter menu offers **AUTO, 1/8, 1/2, 1, 2, 3, 4, 6, 8 s** (1/4 s unconfirmed). Manual shutter control is limited to slow speeds; nothing faster than 1/8 s is user-selectable. | observed (UI, owner report) | EXP-0004 |
| F-045 | In Night mode the aperture screen offers AUTO, F3.5 and F7. Night is the only mode in which the owner could change any exposure setting. **ISO cannot be changed** in Night mode, and the owner could not find an ISO control in other modes either (S1 documents ISO Auto/100/200/400, so Program mode needs checking). Flash and self-timer remain adjustable. | observed (UI, owner report) | EXP-0004 |
| F-042 | The lens is fixed focus with a two-position mechanical switch. There is no focus motor to control. | documented | S1 |
| F-043 | The block diagram includes a motor driver (Sanyo LB1846M). On a fixed-focus, fixed-focal-length camera this probably drives the shutter and/or the aperture/ND mechanism, so "F7" may be an aperture plate or ND rather than an iris. This is a hypothesis (H-004). | inferred | S3 |

## NAND layout (from EXP-0005)

| ID | Finding | Confidence | Evidence |
|---|---|---|---|
| F-046 | Before the partition (LBA 1–56), the firmware keeps a duplicated `NAND RSV` header (`0xBEEF`, 808, 215, …) and a list of 215 block numbers, 1023 down to 809. It also stores a table of 32-bit `0xAC05xxxx` values. | observed | EXP-0005 |
| F-047 | The NAND is 1024 × 16 KiB blocks. Blocks 809–1023 (215 blocks, 3.36 MiB) are a reserved region that USB never exposes, the leading candidate for the firmware. The visible LUN is exactly 785 blocks; about 24 blocks are FTL overhead. | inferred (arithmetic consistent; NAND part not read) | EXP-0002, EXP-0005 |
| F-048 | Auto-exposure writes continuously variable exposure times (e.g. 1000/18467 s). The shutter is controlled in fine time units, not stops. | observed | EXP-0006 |
| F-049 | In 26 Program-mode captures: F3.5 and ISO 200 every time; centre-weighted metering; EV 0; flash fired 23×. | observed (casual scenes) | EXP-0006 |
| F-050 | Two consecutive raw reads of the internal-memory LUN are byte-identical (SHA-256 `b76a6504…`). The **user area** reads back reproducibly over USB; the reserved/firmware region does not appear in it. | verified | EXP-0005 |
