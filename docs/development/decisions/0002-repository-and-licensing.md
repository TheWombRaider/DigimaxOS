# ADR 0002: Public `DigimaxOS` repository, MIT, no OEM material

- **Status:** accepted, 2026-11-14

## Context

The spec asks for a public repository named `DigimaxOS` under the owner's account, holding
original material only. A private, empty repository (`digimax-a402-firmware-hack`) had already
been created automatically by the development environment.

## Decision

- Create `TheWombRaider/DigimaxOS` as a public repository. The local working copy's `origin`
  points to it. The empty private repository is left untouched, for the owner to delete or keep.
- License new original code and docs under MIT.
- Never commit OEM firmware, drivers, manuals, calibration data, dumps, photos or credentials.
  CI enforces this with `scripts/check_public_safety.py` (file types, binary content, size,
  secret patterns, e-mail addresses).
- Commits use the maintainer's GitHub noreply address.

## Consequences

- Contributors must hold any OEM files privately. Patch tooling must work from a user-supplied
  base image.
- Some evidence can only be described, not shown. Sources are cited by URL and hash.
