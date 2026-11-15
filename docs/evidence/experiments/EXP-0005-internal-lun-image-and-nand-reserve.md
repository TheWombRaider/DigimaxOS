# EXP-0005: Read-only image of the internal-memory LUN; NAND reserve table

- **Date:** 2026-11-15
- **Operator:** AI agent (remote, read-only); owner present
- **Kind:** observed on stock
- **Device / profile:** `a402`, A402-REF-1, firmware `M4051S-0525`, no card inserted
- **Instrumentation:** Windows 11 laptop. Read-only `FileStream` on `\\.\PhysicalDrive<N>` after
  verifying exactly one USB disk named `SAMSUNG DIGITAL CAMERA` of 12,861,440 bytes. The image went to
  `%TEMP%`, was copied over SFTP to the private workspace and then deleted from the laptop. Analysed
  offline with `digimax card check`, `fsck.fat -n` (dosfstools 4.2, after extracting the partition
  to a temporary private copy, also deleted) and ad-hoc Python.
- **Approval:** the owner granted read access to the camera ("read whatever you want"). Nothing was
  written to the camera.

## Results

### Reproducible readback of the exposed LUN

| Pass | Bytes | SHA-256 |
|---|---|---|
| 1 | 12,861,440 | `b76a6504b98d2ab616e4f86de1562e7d96af933d55df07d6db725deb8708af8f` |
| 2 | 12,861,440 | `b76a6504b98d2ab616e4f86de1562e7d96af933d55df07d6db725deb8708af8f` |
| copy on Linux host | 12,861,440 | identical |

Two consecutive reads are byte-identical. This covers only the **user-visible LUN**, not the
firmware area (see below). It does not satisfy recovery item R2 (docs/recovery).

### Filesystem

- `digimax card check`: OK. FAT12, 782 × 16 KiB clusters, 88 free; `DCIM\100SSCAM` holds 27
  DCF-named files. Data area cluster-aligned.
- `fsck.fat -n`: consistent (32 files, 694/782 clusters used). It notes that the boot-sector volume
  label field is not a valid label (it is not space-padded), which is harmless.
- **Correction to EXP-0003:** the OEM-name field is **eight NUL bytes** (`00`), not spaces. The
  earlier decoder stripped the NULs. The formatter fingerprint in `digimax.fat` now matches NUL bytes
  specifically. A space-padded name is reported as "unknown".

### The pre-partition area (LBA 1–56): a NAND reserve table

Most of these sectors are zero. The non-zero sectors form two copies of one structure, with a period
of 32 sectors:

| LBA | Content |
|---|---|
| 8, 16, 40, 48 (identical) | 215 little-endian 16-bit values, **0x03FF down to 0x0329 in steps of 1** (blocks 1023…809), zero-padded |
| 24–31 (LBA 56 = copy of 24) | 32-bit little-endian words, all of the form **`0xAC05xxxx`**, increasing in steps of 8, arranged as pairs `(A, A+0x10)` |
| 32 | ASCII **`NAND RSV`**, then little-endian 16-bit fields `0xBEEF`, `0x0328` (808), `0x00D7` (215), `0xFF29`, `0x00A0` (160), then zeros |

The numbers agree with one another:

- 215 table entries = the header's `0x00D7`. The table runs from block 1023 down to block 809, which
  is the header's `0x0328` + 1.
- 809 + 215 = 1024 blocks. A 16 MiB small-page NAND with 16 KiB erase blocks (32 × 512-byte pages)
  has exactly 1024 blocks.
- The exposed LUN is exactly **785 × 16 KiB** blocks. Blocks 0–808 (809 blocks) would leave 24 blocks
  for flash-translation overhead and spares.
- 215 reserved blocks × 16 KiB = **3,522,560 bytes (3.36 MiB)**. The unexposed total from EXP-0002 is
  3,915,776 bytes (239 blocks), which would be the 215 reserved blocks plus the 24 overhead blocks.

## Interpretation and confidence

- **Observed (F-046):** the firmware writes a `NAND RSV` header and a duplicated reserved-block list
  before the partition, inside the user-visible LUN. Two copies suggest redundancy.
- **Inferred, moderately strong (F-047, refines H-010):** the NAND is 1024 blocks × 16 KiB. The top
  **215 blocks (809–1023) form a reserved region** that USB mass storage does not expose. It is
  the leading candidate for the firmware image and resources. The block size is inferred from the
  arithmetic; the NAND part number has not been read.
- **Weak ISA clue (H-013):** the table of `0xAC05xxxx` values looks like 32-bit memory addresses
  (an in-RAM linked structure saved with the table). 32-bit pointers are more natural for a 32-bit
  CPU than for an 8051 (16-bit data pointers), so this is *weak* evidence against H-008. In a MIPS
  memory map, `0xA0000000–0xBFFFFFFF` is the uncached KSEG1 window. That is suggestive, but not a
  determination (spec 7B requires several independent clues).
- **Recovery consequence:** USB mass storage can back up the user area and the FTL header, but **not**
  the reserved region. A firmware backup needs another path: the update mechanism, a boot ROM mode,
  or a donor NAND read (#4).

## Raw evidence

| File (private workspace) | SHA-256 |
|---|---|
| `dumps/A402-REF-1-internal-lun.img` | `b76a6504b98d2ab616e4f86de1562e7d96af933d55df07d6db725deb8708af8f` |
| `camera/EXP-0005-passes.txt` | `484df93642f1433751b71b2685cb7aacb951d5fffe95d8e447d901bd00d763e9` |

The image contains the owner's photos and is never published.
