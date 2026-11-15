# Storage architecture (SD-01, SD-02)

## Layers

Each layer must be identified in the stock firmware and proven to work independently. A newer
filesystem cannot make an SDSC-only transport speak SDHC.

| # | Layer | Responsibility | SDHC change needed? | Host reference |
|---|---|---|---|---|
| 1 | Electrical / host controller | Pins, clock, bus width, native SD vs **SPI** mode | No (SDHC uses the same 3.3 V signalling and default speed) | — |
| 2 | Card initialisation | CMD0, **CMD8**, CMD55+**ACMD41(HCS)**, OCR **CCS**, CMD2/3/9/7, CMD16 | **Yes**: CMD8 + HCS are mandatory for SDHC | `digimax.sd.host.initialize` |
| 3 | Block transport | CMD17/18/24/25, stop/busy, CRC, retries, DMA | **Yes**: argument is LBA for SDHC, LBA×512 for SDSC | `digimax.sd.host.BlockTransport` |
| 4 | Capacity math | CSD v1 vs **v2** decoding, 32-bit overflow | **Yes**: CSD v2 C_SIZE; byte counts > 4 GiB need 64-bit or sector units | `digimax.sd.registers` |
| 5 | Partition parsing | MBR, partition types 0x0B/0x0C | Probably (type 0x0C, LBA-only) | `digimax.fat.parse_mbr` |
| 6 | Filesystem | FAT12/16 → **FAT32** (BPB, FSInfo, 28-bit cluster numbers, root dir as a cluster chain) | **Yes** | `digimax.fat` |
| 7 | DCF / indexing / free space | Folder and file numbering, free-space display, "shots left" estimate | Probably (cluster counts > 65,524, free space > 2 GiB) | `digimax.fat._dcf` |

## Addressing rule

```text
           logical sector (LBA, 512 B) — used everywhere above layer 3
                          │
          ┌───────────────┴────────────────┐
     SDSC / MMC                       SDHC / SDXC (OCR.CCS = 1)
   arg = LBA × 512 (≤ 0xFFFFFFFF)       arg = LBA
```

- Validate `lba + count ≤ capacity_sectors` **before** issuing any command. Reject the request;
  never wrap.
- The classic failure is aliasing. A transport that computes `lba * 512` in 32 bits wraps at
  4 GiB, so writes to LBA 8,388,608 land on LBA 0 (the MBR). `tests/test_sd_addressing.py` and
  `digimax card verify-pattern` exist to detect this.
- CMD16 is sent only to byte-addressed cards. SDHC block length is fixed at 512.

## Initialisation (reference sequence)

```text
CMD0 ─► CMD8(0x1AA) ─┬─ echo ok ──► v2 card: ACMD41(HCS=1) until ready ─► CCS? SDHC : SDSC v2
                     └─ no reply ─► v1 card or MMC: ACMD41(HCS=0) ─┬─ ready ─► SDSC v1
                                                                    └─ rejected ─► CMD1 loop ─► MMC
then CMD2 ─► CMD3 (RCA) ─► CMD9 (CSD) ─► CMD7 (select) ─► [CMD16 512 if byte-addressed]
```

An SDHC card stays **busy forever** if the host omits CMD8 or HCS. That is what `HostPolicy.legacy()`
models, and it is the leading hypothesis for stock behaviour (H-002).

## What the sibling SPCA533A tells us (S22, F-058)

The SPCA533A's SD block is a *command engine*. Firmware writes the command index and a full 32-bit
argument into a command buffer, the hardware adds CRC7/CRC16, and responses, data, block length
(1–1023), bus width (1/4) and clock (375 kHz–24 MHz) are all under software control. If the
SPCA536 is the same (H-015), then everything in layers 2–7 above is firmware. The CMD8/HCS
handshake, CCS-aware addressing, CSD v2 parsing and FAT32 can all be added without hardware
changes, which makes the `digimax.sd.host` reference model directly portable in design.

## Open questions (tracked as issues)

- Does the SPCA536 have a native SD controller, or does the firmware bit-bang SPI? Find the
  register map, DMA engine, clock divider and card-detect/write-protect lines (schematic p.55 not
  yet transcribed).
- Where does the firmware keep the CSD/capacity, and with what integer width?
- Is the filesystem code a licensed third-party FAT library? Its strings may say.
- How do the internal 16 MB NAND and the card share the FAT layer (drive letters, LUN switching)?
- Footprint budget: how much ROM/RAM is free for FAT32 code?

## FAT32 implementation options (decide by ADR once the ISA is known)

1. Extend the stock FAT code (smallest footprint; needs complete understanding of it).
2. Port a permissively licensed small FAT library (for example FatFs, BSD-style 1-clause license).
   Measure ROM/RAM before deciding.
3. Never: auto-format, a silent destructive fallback, or advertising capacities not proven by
   the acceptance tests ([test plan](../test-plans/sd-capacity.md)).
