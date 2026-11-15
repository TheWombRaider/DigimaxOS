# Project status: durable checkpoint

Future sessions **resume from here**. Rewrite the current-state section at the end of every
session and add a log entry. Never delete log entries.

## Current state (as of 2026-11-15)

| Gate | State |
|---|---|
| G0 public repo + docs + host setup + device identification | **met**: repo public; device identified (EXP-0001) |
| G1 verified firmware identity, provenance, ISA | **not met**: no firmware image; version unknown; ISA unknown |
| G2 recovery | **not met**: see [recovery checklist](../recovery/README.md) (0/8) |
| G3–G5 | not started |

**Firmware status:** no original firmware image or update file exists anywhere in the project. The
official Samsung site offers none (F-030), and public searches found none (F-032). **Nothing has
been written to the camera.**

**Host tooling:** `digimax` CLI v0.1.0.dev0, stdlib only. 97 tests pass locally (unit, property-based
and fixture tests, including dosfstools cross-checks). CI is defined in `.github/workflows/ci.yml`.

## Highest-value next actions

1. **Firmware version** (owner approval needed): read the EXIF `Software`/`Make`/`Model` tags from
   one camera-made JPEG in place, or read the version from the camera's setup menu. This sets the
   search target for `MEGA536`.
2. **Firmware acquisition** (#issue "Locate MEGA536"): Wayback Machine captures of
   samsungcamera.com/service, samsungimaging.com, Korean Kenox support pages and driver CDs. Record
   the provenance of anything found, hash it and keep it private.
3. **Internal-memory LUN and boot sector** (owner approval needed): enumerate with no card
   inserted (H-007); read only sectors 0 and 32 of the card (formatter OEM name, F-022).
4. **Stock Night-mode baseline** (owner present, scratch card): Phase 1A of the
   [exposure test plan](../test-plans/exposure-baseline.md). It needs no captures, only menu
   observation, and gives the real shutter steps.
5. **Schematic transcription** (offline): S3 web pp. 52–56, the SD/NAND/EEPROM/strap net names.
6. **Test media** (owner decision / purchase): expendable SDSC 1 GB and 2 GB cards and an SDHC
   4 GB card for SD-01 and H-002.

## Blocked / waiting on the owner

| Item | Needs |
|---|---|
| EXIF firmware-version read | approval to read the metadata of one existing photo in place |
| Sector 0/32 read of the owner's card | approval (read-only, no personal data in those sectors) |
| No-card enumeration, Night-mode menu walk-through | someone physically at the camera |
| SD capacity tests | expendable cards (purchase decision is the owner's) |
| Donor camera for recovery work | purchase decision is the owner's |
| Durable SSH access to the Windows host | the owner authorising an SSH key, instead of sharing a password per session |

## Environment facts

- Dev host: Ubuntu 24.04 VM. The camera is on a separate Windows 11 laptop, reached over SSH.
  Read-only PowerShell is collected with `scripts/windows/Get-DigimaxInfo.ps1`.
- Private workspace: `~/.local/share/digimaxos-private` (OEM driver package S10, EXP-0001 raw
  report, reference copies of `sunplus.c` and `usb.ids`, all hashed in `SHA256SUMS`).

## Session log

### 2026-11-14/15: founding session

- Read the spec and inventoried the host (Ubuntu 24.04, Python 3.12, uv 0.13, gh authenticated,
  passwordless sudo, which was not used for any system change).
- Created the public repository `TheWombRaider/DigimaxOS`. An empty private
  `digimax-a402-firmware-hack` repo, auto-created by the environment, was left untouched.
- Research: Samsung UK support page (S9) has no firmware. Downloaded the official driver package
  (S10) privately and inspected it without executing it: VID/PID 0839:003C and the Kenox D402
  alias. Service manual (S3): MEGA536 procedure, test-mode entry, block-diagram parts, and the
  SPCA535/536 contradiction. Sunplus press release (S13), gspca table (S6), usb.ids (S11), gumpack
  teardown (S12).
- Searches with no result: `"MEGA536" firmware`, "Samsung Digimax A402 firmware update MEGA536",
  "Kenox D402 Samsung firmware download", "Samsung Digimax firmware archive A400 A402 A403 D402".
- EXP-0001: identified the camera over USB on the Windows host (read-only).
- Built the host CLI, the SD reference model and simulator, the FAT/DCF analyser, the firmware
  inspector, the exposure model and M-mode mock, the Windows collector, CI, the issue forms,
  labels, milestones and the initial issue backlog.
