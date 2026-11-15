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

**Firmware status:** the reference unit runs **`M4051S-0525`** (EXIF Software tag, F-033). No
original firmware image or update file exists anywhere in the project. The official Samsung site
offers none (F-030), and public searches found none (F-032). About 3.73 MiB of the 16 MB NAND is
hidden from USB and is the likely firmware region (H-010). **Nothing has been written to the
camera.**

**Storage facts:** a single USB LUN, either the card or internal memory (F-026). Internal memory is
25,120 sectors of FAT12, laid out by the camera's own formatter (F-027, F-028). `digimax card check`
recognises that formatter's fingerprint.

**Host tooling:** `digimax` CLI v0.1.0.dev0, stdlib only. 101 tests pass locally. CI
(`.github/workflows/ci.yml`) runs on Python 3.11/3.12/3.13.

**Repository:** https://github.com/TheWombRaider/DigimaxOS. Issues #1–#15 are the backlog and #16 is
the pinned rolling checkpoint. `main` is protected: required checks, linear history, no force-push.
Required reviews are off while there is a single maintainer; CODEOWNERS and the PR checklist cover
firmware and hardware-write review.

## Highest-value next actions

1. **Firmware acquisition** ([#1](https://github.com/TheWombRaider/DigimaxOS/issues/1)): search
   with the concrete target `M4051S` / `MEGA536`. Use Wayback captures of samsungcamera.com/service
   and samsungimaging.com, Kenox (Korea) support, and driver CDs. Also gather `Software` tags from
   public A402/D402 photos to enumerate the builds (H-009).
2. **Finish the Night-mode walk-through** ([#5](https://github.com/TheWombRaider/DigimaxOS/issues/5)):
   the shutter steps are recorded (EXP-0004: AUTO, 1/8 to 8 s; 1/4 to be confirmed). Still to do:
   aperture values, ISO/EV/WB availability in Night mode, and persistence.
3. **Sectors 1–56 of internal memory** (H-011): owner approval needed. They are outside the
   filesystem and hold no photos.
4. **Card boot sector** (F-022): when the SD card is back in, read sectors 0 and 32 (owner
   approval). This tells us whether the camera formatted it, by comparing with the F-028
   fingerprint.
5. **Schematic transcription** ([#13](https://github.com/TheWombRaider/DigimaxOS/issues/13), offline).
6. **Test media** ([#8](https://github.com/TheWombRaider/DigimaxOS/issues/8)): expendable SDSC
   1 GB / 2 GB and SDHC 4 GB cards (purchase is the owner's decision).
7. **Battery drain** (POWER-01): the owner reports heavy battery use. Measure the current draw
   later.

## Blocked / waiting on the owner

| Item | Needs |
|---|---|
| Sectors 1–56 read (internal memory) | approval (read-only, no user data) |
| Sector 0/32 read of the owner's card | the card reinserted, plus approval |
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

