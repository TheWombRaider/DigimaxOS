<img src="assets/icon.svg" width="72" height="72" alt="DigimaxOS logo">

# DigimaxOS

**Open-source research and firmware enhancements for vintage Samsung Digimax cameras, starting with the A402.**

> [!WARNING]
> **Status: research only.** No custom firmware exists yet. Nothing in this repository can be flashed
> to a camera, and no SDHC or manual-exposure support has been shown to work on hardware. Claims
> are labelled *documented*, *hypothesis* or *verified*. Only *verified* claims have been observed on
> a real unit, and each one cites its experiment ID.
>
> DigimaxOS is an independent community project. It is not affiliated with, endorsed by or
> supported by Samsung. "Samsung", "Digimax" and "Kenox" are trademarks of their respective owners
> and are used only to identify compatible hardware.

## Why

The Digimax A402 (2005) is a 4 MP CCD compact with a distinctive look, but it has two big
limitations:

1. **Storage.** The manual guarantees SD/MMC cards only up to 512 MB. Cards that small are hard
   to find now.
2. **Exposure control.** Shutter and aperture can be set by hand only in the *Night* scene mode.
   There is no true manual (M) mode.

DigimaxOS has two flagship goals of equal priority:

| Goal | Target | Status |
|---|---|---|
| **SD-01 / SD-02** | Reliable SDSC 1–2 GB and SDHC 4–32 GB (FAT32) support, with full-address-space integrity | Research: host-side reference implementation and simulator done; camera behaviour not yet measured |
| **EXP-01 / EXP-02** | A dedicated M mode with independent shutter / aperture / ISO and honest EXIF | Research: capability model and UI state machine done; stock baseline measurement pending |

Later goals (RAW/DNG, histogram, intervalometer, tethering and others) are in [ROADMAP.md](ROADMAP.md).

## Safety first

Recovery comes before any modification. We will **not** flash, open, probe or run
calibration/diagnostic menus on anyone's camera until the gates in
[docs/recovery/README.md](docs/recovery/README.md) are met **and** the owner explicitly approves.
The first patch will be tiny and reversible, such as a version marker. It will never touch the
shutter, the SD driver or the bootloader. See [SECURITY.md](SECURITY.md) and
[docs/recovery/risk-register.md](docs/recovery/risk-register.md).

> [!CAUTION]
> Camera flash capacitors can hold a dangerous charge long after the batteries are removed. Do not
> open a camera because a document here suggests it. Hardware work is limited to donor units
> handled by qualified people.

## What works today (host-side only)

The `digimax` command-line tool is pure Python (standard library only) and read-only. Install it with
[uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/TheWombRaider/DigimaxOS && cd DigimaxOS
uv sync                       # creates .venv with dev tools; the CLI itself has no dependencies
uv run digimax env check      # host inventory
uv run digimax discover       # read-only USB discovery (Linux sysfs; no control transfers)
uv run digimax inspect        # A402 profile with the verification status of every field
```

| Command | What it does |
|---|---|
| `digimax discover [--import report.json]` | Finds the camera on Linux, or evaluates a report from [`scripts/windows/Get-DigimaxInfo.ps1`](scripts/windows/Get-DigimaxInfo.ps1) |
| `digimax firmware inspect FILE` | Hashes, entropy map, embedded JPEG/WAV/archives, ASCII and UTF-16 strings, *heuristic* ISA hints |
| `digimax firmware compare A B` | Byte-range diff of two dumps or update files |
| `digimax card check IMAGE` | MBR / FAT12/16/32 / FSInfo / DCF consistency check of a card **image file** (device nodes are refused) |
| `digimax card make-pattern` / `verify-pattern` | Address-unique sector patterns that detect wrap-around and aliasing (SD-02 acceptance method) |
| `digimax sd csd HEX` / `sd ocr HEX` | Decode SD registers: capacity class, addressing mode, warnings |
| `digimax sd address` / `sd frame` / `sd crc16` | Range-checked LBA→command argument conversion, CRC7 command frames, CRC16 |
| `digimax exposure table` | The documented A402 exposure space with EV values and status |
| `digimax exposure mock KEYS…` | Drives the proposed M-mode UI state machine and prints an ASCII screen |
| `digimax patch plan/build`, `digimax capture` | Present but **unsupported** (exit code 3): they explain which gate blocks them |

Add `--json` to any command for machine-readable output.

## What we know so far

The full register is in [docs/evidence/findings.md](docs/evidence/findings.md). Highlights:

- The reference unit enumerates as **USB `0839:003C`** (Samsung Techwin) and presents itself as a
  USB mass-storage device (class 08/06/50, Bulk-Only Transport, bcdDevice 1.00). Its SCSI identity
  is `SAMSUNG` / `DIGITAL CAMERA` / `1.00` ([EXP-0001](docs/evidence/experiments/EXP-0001-usb-enumeration.md)).
  This ID does not appear in the public `usb.ids` database.
- The reference unit runs firmware **`M4051S-0525`** (from its EXIF `Software` tag,
  [EXP-0003](docs/evidence/experiments/EXP-0003-firmware-version-and-boot-sectors.md)). With no card
  inserted, the camera shows its internal memory: 25,120 sectors of FAT12. About 3.7 MiB of the
  16 MB NAND stays hidden from USB and probably holds the firmware.
- The official Samsung driver package says the A402 and the **Kenox D402** are the same product
  family.
- The service manual names **Sunplus SPCA536** in its schematic section titles but **SPCA535** in its block
  diagram. The CPU architecture is *unknown*. A related chip, the SPCA533A, is documented with an
  8032 core, but we do not assume that for the SPCA536.
- No original firmware image or update file (labelled `MEGA536` in the service manual) has been
  found in public archives so far. **Help wanted.**

## Repository layout

```text
docs/        architecture, evidence (sources, findings, experiments), hardware, compatibility,
             recovery, development (setup, status, decisions), test plans and sanitized results
profiles/    per-model device profiles; every field has a verification status
tools/       the digimax Python package (host CLI); tools/dng is a placeholder for the DNG converter
sim/         host-only protocol models (simulated SD/MMC card)
firmware/    reserved for original firmware code once the CPU architecture is established (empty by design)
tests/       pytest suite: unit, property-based and fixture tests; hardware manifests
scripts/     dev setup, verification, public-safety scan, Windows collection script
```

## Contributing

We especially want to hear from you if you:

- own a **spare/donor** A402, D402 or another Sunplus-based Samsung compact
- know **Sunplus SPCA5xx** internals, or kept **archived Samsung camera update files**. Please
  share provenance (where it came from) and hashes, not redistributed OEM binaries.
- can run the stock-behaviour test plans with expendable SD cards

Start with [CONTRIBUTING.md](CONTRIBUTING.md) and the issues labelled
[`good first issue`](https://github.com/TheWombRaider/DigimaxOS/labels/good%20first%20issue). All
participants follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## License

Original code and documentation are released under the [MIT License](LICENSE). This repository
contains **no** Samsung firmware, manuals, drivers, calibration data or private photos, and will
not accept them. See [docs/development/licensing.md](docs/development/licensing.md).
