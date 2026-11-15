# EXP-0003: Firmware version (EXIF) and internal-memory boot sectors

- **Date:** 2026-11-15
- **Operator:** AI agent, remote read-only queries; owner present
- **Kind:** observed on stock
- **Source revision:** `0dffb4b`
- **Device / profile:** `a402`, reference unit A402-REF-1, no card (internal memory LUN, EXP-0002)
- **Instrumentation:** Windows 11 laptop; PowerShell 5.1. EXIF read with
  `System.Drawing.Image.FromStream(stream, useEmbeddedColorManagement=false, validateImageData=false)`
  on a read-only `FileStream`. Raw read with a read-only `FileStream` on `\\.\PhysicalDrive<N>`.
- **Approval:** the owner approved continuing ("push forward") after being asked about (1) reading
  the firmware tags of one photo in place and (2) reading the boot sectors.

## Safeguards

- The script refused to run unless exactly one USB disk named `SAMSUNG DIGITAL CAMERA` existed, with
  the size seen in EXP-0002 (12,861,440 bytes).
- EXIF: only tags `0x010F` Make, `0x0110` Model, `0x0131` Software, `0x9000` ExifVersion,
  `0xA000` FlashPixVersion and the pixel dimensions were output, from the first JPEG by name. No
  date, owner, GPS or image data left the host. Only the first 4 characters of the file name were
  output.
- Raw read: sectors 0–57 were read into memory, and **only sectors 0 and 57** (MBR and volume boot
  sector) were output, plus one boolean for sectors 1–56. Nothing was written.

## Actual result

**EXIF**

| Tag | Value |
|---|---|
| Make | `Samsung Techwin co., Ltd.` |
| Model | `Digimax A402` |
| **Software** | **`M4051S-0525`** |
| ExifVersion | `0220` |
| FlashPixVersion | `0100` |
| Image size | 2272 × 1704 |
| File-name prefix | `S402` (DCF names `S402nnnn.JPG`) |

**MBR (sector 0):** signature `55AA`; boot-code area entirely zero; a single entry marked
**bootable (0x80)**, type `0x01`, LBA 57, 25,063 sectors. CHS start 0/1/26 and CHS end 3/19/32 are
consistent with a 255-head × 32-sector geometry.

**Volume boot sector (sector 57):**

| Field | Value |
|---|---|
| Jump | `E9 00 00` (no boot code follows; bytes 62–509 are all zero) |
| OEM name | 8 spaces (blank) |
| Bytes/sector, sectors/cluster | 512, 32 |
| Reserved sectors, FATs × size | 1, 2 × 3 sectors |
| Root entries | 512 |
| Total sectors | 25,063 (16-bit field) |
| Media descriptor | `0xF8` |
| Sectors/track, heads | 32, 255 |
| Hidden sectors | 57 |
| Drive number | `0x80` |
| Extended boot signature | `0x29`; label empty; FS type string `FAT12   `; volume ID (unit-specific, withheld) |
| Derived | 782 clusters ⇒ FAT12; first data sector = 57 + 1 + 6 + 32 = **96 = a multiple of 32** (cluster-aligned) |

**Sectors 1–56 (before the partition):** not all zero. The contents were not output (H-011).

## Raw evidence

| File (private workspace) | SHA-256 |
|---|---|
| `camera/EXP-0003-raw.txt` | `c70b72c8fdea1b6c476f26375302b6db9852cc4fa363a693e3497f705de004e6` |

## Interpretation

- **Verified (F-033):** the reference unit runs firmware **`M4051S-0525`**. Another A402 on Wikimedia
  Commons, from 2006, shows the same string (S16). A search-engine snippet reports `M4051S-0520` on a
  2005 photo (S17), which is unverified. If it is confirmed, at least two builds were released, and
  a Samsung update probably existed between them (relevant to #1).
- **Verified (F-028):** the internal memory was formatted by an embedded formatter with a distinctive
  fingerprint: blank OEM name, `E9 00 00`, no boot code, and the partition start chosen so that the
  data area is cluster-aligned. That is the SD File System Specification's approach.
  `digimax card check` now reports this fingerprint, so SD-01 tests can tell whether the camera
  formatted a card.
- **Inferred:** "M405" may be an internal platform code and "1S"/"-0525" a revision and build date
  (2005-05-25?). This is a hypothesis only (H-009).

## Follow-ups

- With approval, read sectors 1–56 to see whether they hold camera metadata (an NAND logical-map
  marker? a format record?). They are outside the filesystem and hold no photos.
- Search archives for `M4051S` update notes and files (#1).
