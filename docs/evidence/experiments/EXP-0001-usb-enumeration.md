# EXP-0001: USB enumeration of the reference unit

- **Date:** 2026-11-14
- **Operator:** TheWombRaider (with an AI agent; commands below)
- **Kind:** observed on stock
- **Source revision:** pre-initial-commit tooling
- **Device / profile:** `a402`, reference unit "A402-REF-1" (owner's working camera; serial not recorded)
- **Firmware hash:** unknown (firmware version not yet read)
- **Instrumentation:** Windows 11 (NT 10.0.26200) laptop, in-box `USBSTOR` driver; queried
  remotely over SSH with PowerShell `Get-PnpDevice`, `Get-PnpDeviceProperty`, `Get-Disk`,
  `Get-Partition`, `Get-Volume`, `Win32_DiskDrive`; then `scripts/windows/Get-DigimaxInfo.ps1`
- **Power:** not recorded (camera on its own AA cells; USB power state unknown)
- **Media:** the owner's SD card, already in the camera (capacity class 512 MB). **Owner data:**
  file *contents* were not opened, copied or hashed.
- **Approval:** the owner asked for the camera to be enumerated and identified. No raw-disk read,
  no EXIF read, no writes.

## Purpose

Identify the attached device exactly (spec section 7A / first-session item 5). Establish its USB
identity and storage presentation without changing anything.

## Procedure

1. List present PnP devices whose instance ID matched `VID_0839` or `USBSTOR`.
2. Read hardware/compatible IDs, service, bus-reported description and location for the USB device.
3. Read disk, partition and volume metadata for the disk named `SAMSUNG DIGITAL CAMERA`.
4. Count files per directory and group them by extension on the mounted volume, using names
   only. No file was opened.
5. Run `Get-DigimaxInfo.ps1`, then `digimax discover --import <report>` on the Linux host.

## Expected result

A USB mass-storage device with a Samsung Techwin vendor ID, consistent with the 2005 driver INF
(S10).

## Actual result

| Property | Value |
|---|---|
| USB hardware IDs | `USB\VID_0839&PID_003C&REV_0100`, `USB\VID_0839&PID_003C` |
| Compatible IDs | `USB\Class_08&SubClass_06&Prot_50` (Mass Storage / SCSI / Bulk-Only) |
| Driver | `USBSTOR` (Windows in-box) |
| Bus-reported description | `DIGITAL CAMERA` (space padded) |
| SCSI vendor / product / revision | `SAMSUNG` / `DIGITAL CAMERA` / `1.00` |
| USB serial number | none (host-synthesised instance ID) |
| Disk size | 504,365,056 bytes = 985,088 × 512-byte sectors |
| Logical / physical sector | 512 / 512 |
| Partition style | MBR, 1 partition |
| Partition 1 | offset 16,384 bytes (LBA 32), size 504,233,984 bytes (984,832 sectors), type `0x06` |
| Filesystem | FAT (FAT16 by cluster count), 16,384-byte clusters, 504,086,528 bytes in data area, 495,468,544 free |
| Volume label | none |
| Layout | `DCIM\100SSCAM\` with 18 `.JPG`, 2 `.AVI`, 3 `.WAV` (owner files: not opened); `System Volume Information` (created by Windows) |
| `digimax discover --import` | `MATCH verified profile a402 (Samsung Digimax A402), mode mass_storage` |

## Raw evidence

| File (private workspace) | SHA-256 |
|---|---|
| `camera/EXP-0001-windows-report.json` | `254b72e7bcce3d367da88a76f07f27faaa9a632f1fbb73d9b7747c3368bab0b5` |

## Interpretation and confidence

- Verified: the device is the A402 family member described by S10. It needs no vendor driver on
  modern Windows and is presented as plain Bulk-Only mass storage (F-001, F-002).
- Verified: with a card inserted, only the card is exposed. Internal 16 MB flash was not visible
  (F-020). To be repeated with **no card** inserted (H-007).
- The 224 unpartitioned sectors at the end and the CHS-style geometry (255 heads × 63 sectors)
  reported by the host are typical of SD-Association-style formatting. Not conclusive (F-022).
- Not established: firmware version, PTP/PictBridge mode behaviour, behaviour with larger cards.

## Follow-ups

- With owner approval: read the `Software`/`Make`/`Model` EXIF tags of **one** camera-made JPEG in
  place, to get the firmware version string (not the image).
- With owner approval: read sectors 0 and 32 (MBR and boot sector, which contain no personal data)
  to learn the formatter's OEM name.
- Repeat enumeration with no card inserted (internal memory LUN) and in PictBridge/PTP mode, if
  the camera menu offers it.
