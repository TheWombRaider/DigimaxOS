# Project status: durable checkpoint

Future sessions **resume from here**. Rewrite the current-state section at the end of every
session and add a log entry. Never delete log entries.

## Current state (as of 2026-11-15)

| Gate | State |
|---|---|
| G0 public repo + docs + host setup + device identification | **met**: repo public; device identified (EXP-0001) |
| G1 verified firmware identity, provenance, ISA | **partly met**: firmware **version** known (`M4051S-0525`, EXP-0003); no firmware **image**; ISA unknown |
| G2 recovery | **not met**: see [recovery checklist](../recovery/README.md) (0/8) |
| G3–G5 | not started |

**Firmware status:** the reference unit runs **`M4051S-0525`** (F-033). No firmware image or update
file has been obtained (F-030, F-032). The camera's own `NAND RSV` table shows that NAND blocks
809–1023 (215 × 16 KiB, about 3.36 MiB) are reserved and never exposed over USB. That is the
leading candidate for the firmware (F-046, F-047). **USB mass storage cannot back up the firmware
region**, so recovery needs another path (#4). **Nothing has been written to the camera.**

**Storage facts:** a single USB LUN, either the card or internal memory (F-026). Internal memory is
785 × 16 KiB blocks of FAT12, laid out by the camera's own formatter (F-027, F-028), and reads back
byte-identically (F-050). A private, hashed image exists in the workspace (EXP-0005).

**Exposure facts:** Night is the only mode with user exposure control: shutter AUTO and 1/8–8 s
(including 1/4), aperture AUTO/F3.5/F7, no ISO control, and no persistence even across a mode
change (F-044, F-045, F-051). Program AE uses
continuously variable shutter times (F-048), which supports an M mode with fine shutter steps
(H-012). In all 44 Program shots (internal memory and card), AE used F3.5 and ISO 200 (F-054).

**Host tooling:** `digimax` CLI v0.1.0.dev0, stdlib only. 101 tests pass locally. CI
(`.github/workflows/ci.yml`) runs on Python 3.11/3.12/3.13.

**Repository:** https://github.com/TheWombRaider/DigimaxOS. Issues #1–#15 are the backlog and #16 is
the pinned rolling checkpoint. `main` is protected: required checks, linear history, no force-push.
Required reviews are off while there is a single maintainer; CODEOWNERS and the PR checklist cover
firmware and hardware-write review.

## Highest-value next actions

1. **Firmware acquisition** ([#1](https://github.com/TheWombRaider/DigimaxOS/issues/1)): targets
   `M4051S` / `MEGA536`, expected size up to about 3.4 MiB (215 blocks). Retry the Wayback CDX
   prefix queries, which failed because the archive was offline on 2026-11-15.
2. **Recovery path** ([#4](https://github.com/TheWombRaider/DigimaxOS/issues/4)): the mass-storage
   route is ruled out for firmware. Research a boot-ROM USB mode (strap pins, "TRAP" schematic
   page) and the update-file handshake. Plan donor NAND reads.
3. **ISA** ([#3](https://github.com/TheWombRaider/DigimaxOS/issues/3)): the `0xAC05xxxx` pointer
   table is a weak 32-bit clue (H-013). Obtain the SPCA536 datasheet.
4. **Controlled exposure series** ([#6](https://github.com/TheWombRaider/DigimaxOS/issues/6)):
   bright-scene Program shots (does AE ever pick F7, other ISOs, or speeds faster than 1/30?), and
   timed Night-mode captures at each menu value.
5. **Settle the card formatter** (F-052): format an *expendable* card in the camera and compare its
   fingerprint with F-028 and F-052. This needs test media (#8).
6. **Schematic transcription** ([#13](https://github.com/TheWombRaider/DigimaxOS/issues/13)), **test
   media** ([#8](https://github.com/TheWombRaider/DigimaxOS/issues/8)), **battery drain** (POWER-01).

## Blocked / waiting on the owner

| Item | Needs |
|---|---|
| Night-mode menu walk-through | someone physically at the camera |
| SD capacity tests | expendable cards (purchase decision is the owner's) |
| Donor camera for recovery work | purchase decision is the owner's |
| Durable SSH access to the Windows host | the owner authorising an SSH key, instead of sharing a password per session |
| Avoiding Windows host writes (System Volume Information) | optional: owner enables a read-only removable-storage policy on the Windows host |

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
  labels (spec section 9), milestones v0.1–v1.0 and issues #1–#16.

### 2026-11-15: internal memory and firmware version

- The owner replaced the drained batteries with rechargeables. With no card, the camera exposed its
  internal memory (EXP-0002): 25,120 sectors, FAT12 at LBA 57, about 3.73 MiB of NAND hidden.
- With the owner's go-ahead, the EXIF Make/Model/Software tags of one JPEG were read in place, along
  with raw sectors 0 and 57 (EXP-0003). Firmware is **`M4051S-0525`**, independently matched by a
  2006 Wikimedia Commons A402 photo. A `-0520` build is reported but unverified.
- Added a formatter fingerprint and cluster-alignment check to `digimax card check`, plus FAT12
  fixtures reproducing the camera's exact internal layout (3-sector FATs, 782 clusters).
- EXP-0004: the owner walked the Night-mode shutter menu. It offers only AUTO and 8 s to 1/8 s, so
  fast speeds are not user-selectable in stock (F-044, new H-012). The exposure model now marks
  those values *observed*.
- The owner confirmed that Night is the only mode with exposure controls (aperture AUTO/F3.5/F7,
  no ISO) and granted read access to the camera.
- EXP-0005: two byte-identical read-only images of the internal LUN. The pre-partition area holds a
  `NAND RSV` header and a list of 215 reserved blocks (809–1023), so the firmware region is not
  reachable over USB. The formatter OEM name is 8 NUL bytes (EXP-0003 corrected).
- EXP-0006: EXIF of 26 Program shots shows continuously variable shutter times, with F3.5 and ISO 200
  throughout.
- Added the privacy-preserving `digimax exif` command (identity and exposure tags only) with tests.
- The owner confirmed the 1/4 s Night step and that Night settings don't persist even across a mode
  change (F-051).
- EXP-0007 (card back in, read-only): the owner's card has an unidentified embedded format
  (`EB 00 90`, unaligned), unlike the camera's internal format. 4/18 card photos have EXIF rotation
  written elsewhere. Across 44 shots, AE always used F3.5 and ISO 200. `card check` fingerprints this
  second formatter.

