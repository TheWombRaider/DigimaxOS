# Licensing and provenance policy

| Material | Policy |
|---|---|
| Original DigimaxOS code and docs | MIT ([LICENSE](../../LICENSE)) |
| Samsung firmware, update files, drivers, manuals, calibration data | **Never committed or redistributed.** Referenced by URL and SHA-256 in `docs/evidence/sources.yaml` |
| Disassembly or decompilation output of OEM code | Private only. Public notes describe interfaces and behaviour in our own words (addresses, register roles, calling conventions) without reproducing code listings |
| Binary patches | Published only as *definitions* (offset, expected original bytes **hash**, replacement generated from original code). They are checked so they do not embed OEM bytes. The patch is built locally from the user's own base image |
| GPL code (Linux `gspca`, CHDK) | Reference only. Never copied into MIT files. If a GPL component is ever needed it is isolated in its own directory with its license, and that decision is recorded in an ADR |
| AGPL code (spca-fun) | Methodology reference only |
| Third-party libraries for firmware (for example a FAT library) | Permissive licenses only (MIT/BSD/zlib/FatFs-style). Recorded with version, license and footprint in an ADR before use |
| Photos in docs | Only non-private test targets, with EXIF stripped of owner fields |
| Trademarks | Use names only to identify hardware. Original branding only; no Samsung logos |

If you are unsure about the rights to something, do not commit it. Open an issue or a private
advisory and ask.
