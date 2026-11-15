# Changelog

All notable changes are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow
[Semantic Versioning](https://semver.org/) for the host tooling. Firmware patches, if any ever
ship, will be versioned separately and scoped to exact base-firmware hashes.

## [Unreleased]

### Added
- Project specification, governance documents, CI and public-safety scanner.
- `digimax` host CLI (read-only): `env check`, `discover` (Linux sysfs and Windows-report import),
  `inspect`, `firmware inspect|compare`, `card check|make-pattern|verify-pattern`,
  `sd csd|ocr|address|frame|crc16`, `exposure table|mock`. The `patch plan|build` and `capture`
  commands are stubs that report as unsupported.
- SD reference model: CRC7/CRC16, OCR/CSD v1–v3 decoding, range-checked LBA→argument conversion,
  address-unique sector patterns, host initialisation sequence, simulated SD/MMC card.
- FAT12/16/32 + MBR + DCF image analyser with synthetic fixtures, cross-checked against dosfstools.
- Exposure capability model and proposed M-mode UI state machine with ASCII mock.
- A402 device profile and evidence register (EXP-0001: USB identification of the reference unit).
- `scripts/windows/Get-DigimaxInfo.ps1`: read-only collector for compatibility reports.
