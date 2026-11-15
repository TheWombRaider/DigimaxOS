# Release process

## Host tooling (`digimax` Python package)

1. `scripts/verify.sh` passes on `main`; CI is green.
2. Update `CHANGELOG.md` and the version in `pyproject.toml` and `tools/digimax/__init__.py`.
3. Create a signed, annotated tag `vX.Y.Z` and a GitHub release with checksums of the sdist/wheel.

## Firmware patches (future; gates G2–G5)

A firmware-patch release must include:

- the exact supported model, profile and **base firmware SHA-256** (nothing else is accepted)
- status: *experimental* until the hardware acceptance plans pass; *stable* only per individually
  verified feature
- the rollback guide, which must be complete. If it is incomplete, no stable release is made.
- reproducibility inputs (tool versions and the patch-definition commit) and output hashes
- test provenance (experiment IDs), known issues and license information
- **no OEM bytes.** The user generates the patched image locally from their own base image.

The project never ships automatic updates or an installer that flashes automatically.
