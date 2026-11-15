# CLAUDE.md

Follow [AGENTS.md](AGENTS.md). It is binding for Claude Code sessions in this repository.

Session checklist:

1. Read `docs/development/status.md` (the durable checkpoint) and the open issues
   (`gh issue list --repo TheWombRaider/DigimaxOS`).
2. Do the highest-value independent safe work. If a task needs the camera, the owner's data,
   hardware writes or a purchase, stop at that gate and ask.
3. Run `scripts/verify.sh` and commit in small logical steps.
4. Update `docs/development/status.md`, `docs/evidence/findings.md` and the affected issues
   before ending the session.

Project facts that are easy to get wrong:

- The reference camera is attached by USB to a separate Windows machine, not to this Linux host.
  Collect read-only data with `scripts/windows/Get-DigimaxInfo.ps1` and then
  `digimax discover --import`.
- The SoC is *unknown* (SPCA535 vs SPCA536 conflict), and so is the ISA. Do not write firmware-target
  code until an ADR establishes both.
- The shutter steps are *candidates*, not documented values.
