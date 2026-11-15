# Roadmap

There are no dates. Order follows dependencies, and the SDHC and manual-mode tracks can move in
parallel. Each milestone maps to a GitHub milestone and to the evidence gates in the
specification (section 10).

```text
 v0.1 research toolkit ──► v0.2 recovery / first patch ──┬─► v0.3 manual mode ─┐
   (gate G0, G1)              (gate G2)                  └─► v0.4 SDHC ────────┴─► v1.0 tested release (G3–G5)
```

## v0.1 — research toolkit (in progress)

- [x] Public repository, governance, CI and public-safety scanning
- [x] Read-only `digimax` CLI: environment check, USB discovery (Linux sysfs + Windows import),
      firmware inspect/compare, card image check, SD register/address tools, exposure model
- [x] Host SD initialisation reference model and simulated SD/MMC card (SDSC v1/v2, SDHC, MMC)
- [x] Reference unit identified over USB (EXP-0001)
- [ ] Original firmware acquisition: locate `MEGA536` update file(s) with provenance (#issue)
- [ ] Exact SoC identification (SPCA535 vs SPCA536) and ISA determination
- [ ] Stock behaviour baselines: Night-mode exposure, SD card capacity (512 MB → 2 GB), USB modes
- [ ] Firmware version of the reference unit (EXIF `Software` tag or menu)

## v0.2 — recovery and first patch (gate G2)

- [ ] Reproducible full readback (NAND + boot ROM + EEPROM), confirmed by several independent reads
- [ ] Per-device calibration backup and verified restore
- [ ] Independent recovery path that works without functioning application firmware, proven on a
      donor unit
- [ ] Matching-base patcher: preimage hashes, bounds checks, dry run, reproducible output
- [ ] First tiny reversible patch (version string), only with owner approval

## v0.3 — manual mode (EXP-01, EXP-02)

- [ ] Measured shutter steps, aperture mechanism (iris vs ND) and ISO behaviour
- [ ] Locate the exposure routines and the Night-mode handler in firmware
- [ ] M mode built on the existing shutter/aperture/gain routines; advisory meter; correct EXIF
- [ ] Acceptance matrix: at least 3 captures per setting, shutter timing tolerance, regression of
      the stock modes

## v0.4 — SDHC (SD-01, SD-02)

- [ ] Locate the SD/MMC host controller: native SD bus or SPI, registers, DMA, clocks
- [ ] CMD8 + ACMD41(HCS) + CCS-aware addressing at a single transport boundary
- [ ] FAT32 support (BPB, FSInfo, cluster math) alongside FAT12/16; DCF numbering and free space
- [ ] Release acceptance: pattern tests across the whole address space on 2 vendors per capacity,
      10 cold starts, 100+ captures, full-card behaviour

## Later (P1–P3)

RAW capture and host DNG conversion (RAW-01) · histogram, clipping and grid overlays (UI-01) ·
intervalometer and bracketing (CAP-01) · host SDK and tethering, if a protocol is proven (USB-01) ·
NiMH battery indicator (POWER-01) · SDXC feasibility (SD-03) · video options (VIDEO-01) ·
profiles and menus (UI-02) · other models (PORT-01)

**Not promised:** higher resolution than the sensor provides, a continuously variable aperture,
optical zoom, modern video codecs, Wi-Fi.
