# EXP-0002: USB enumeration with no card inserted (internal memory)

- **Date:** 2026-11-15
- **Operator:** TheWombRaider (owner) at the camera; queries run remotely by an AI agent
- **Kind:** observed on stock
- **Source revision:** `0dffb4b`
- **Device / profile:** `a402`, reference unit A402-REF-1
- **Firmware:** `M4051S-0525` (EXP-0003)
- **Instrumentation:** Windows 11 laptop, in-box `USBSTOR`; PowerShell PnP and storage cmdlets;
  `scripts/windows/Get-DigimaxInfo.ps1`; `digimax discover --import`
- **Power:** fresh rechargeable AA cells, inserted just before the test. The previous cells ran flat
  during the session, so the camera's high battery drain is noted for POWER-01.
- **Media:** none. The owner removed the SD card with the camera unplugged and switched off.
- **Approval:** the owner removed the card for this test and asked us to continue. Read-only
  metadata only.

## Procedure

As in EXP-0001: PnP identity, disk/partition/volume metadata, and directory names plus per-directory
file counts. No file was opened.

## Actual result

| Property | Value |
|---|---|
| USB identity | unchanged: `0839:003C` rev `0100`, class 08/06/50, `USBSTOR`, a single LUN |
| Disk size | **12,861,440 bytes = 25,120 × 512-byte sectors** (host CHS view: 16,065 sectors, an artefact) |
| Partition style | MBR, 1 partition |
| Partition 1 | offset 29,184 bytes (**LBA 57**), 12,832,256 bytes (25,063 sectors, ending exactly at the last sector), type **`0x01` (FAT12)** |
| Filesystem | FAT, 16,384-byte clusters, 12,812,288 bytes data area, 1,441,792 bytes free |
| Layout | `DCIM\100SSCAM\` with 26 `.JPG` and 1 `.AVI` (owner files, not opened); `System Volume Information` (created by Windows) |
| `digimax discover --import` | `MATCH verified profile a402`, mode mass_storage |

## Raw evidence

| File (private workspace) | SHA-256 |
|---|---|
| `camera/EXP-0002-nocard.txt` | `4be1882b65401061aeba6ba13592d4c4c8f84a80ba7c6e86bef76413cff19709` |
| `camera/EXP-0002-windows-report.json` | `d29ce0db064366de1c68943486961ec5c7dc2bc9d682b377b83cd1f99ae0b6e3` |

## Interpretation

- **Verified (F-026):** the camera exposes exactly one LUN. It is the card when one is present,
  otherwise the internal memory, with the same USB identity in both cases.
- **Verified (F-027):** the internal-memory LUN is 12,861,440 bytes. The documented NAND is 16 MB
  (16,777,216 bytes if binary), so about **3.73 MiB (3,915,776 bytes) is not exposed**. That region
  plausibly holds firmware, system data and spare/bad-block reserve (H-010). This is the first
  physical clue to where the firmware lives.
- Supports part of H-007: an update file copied "via the camera" with no card inserted would land
  in internal memory.
- Windows again created `System Volume Information`, this time in **internal flash** (F-025). It is
  harmless at the filesystem level, but it is a host write. A read-only mount policy would avoid
  it (see status.md).

## Follow-ups

- The free space is nearly exhausted (1.4 MB). Note this before any test that needs internal
  memory.
- Measure the camera's current draw (POWER-01). The owner reports that it "chews through batteries".
