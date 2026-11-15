# Security and safety policy

## Reporting

Report security or safety problems privately through
[GitHub private vulnerability reporting](https://github.com/TheWombRaider/DigimaxOS/security/advisories/new).
Please do not open public issues for the following:

- a tool or script that could write to, format or erase a device or host disk unexpectedly
- a patch or procedure that could brick a camera, corrupt calibration data or damage hardware
  (electrical or flash-capacitor hazards, battery hazards)
- secrets, personal data, OEM binaries or other prohibited material committed to the repository
  or attached to issues
- supply-chain concerns, such as dependencies or CI workflows

We aim to acknowledge reports within 7 days. This is a volunteer project, so response times are
not guaranteed.

## Scope and supported versions

DigimaxOS is pre-release research software (0.x). Only the `main` branch is supported. No firmware
images are distributed. If a release ever includes a firmware patch, it will be marked
experimental and limited to the exact base-firmware hash it was verified on.

## Safety guarantees we maintain

- Every `digimax` command is read-only. Card analysis refuses device nodes, and pattern files are
  only ever created as new files.
- No command performs USB control/vendor requests, firmware updates or automatic flashing.
- Recovery, baseline and diagnostic documentation must exist before any experimental firmware
  release (spec gate G2).
- Public CI never has access to private firmware, device dumps or hardware.

## Physical safety

Do not open a camera because something in this repository suggests it. The xenon flash circuit
can hold a dangerous charge after the batteries are removed. Use healthy, matched NiMH AA cells
or alkaline AA cells as documented. Never use 3.7 V lithium cells in an AA form factor.
