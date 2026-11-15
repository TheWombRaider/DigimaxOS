# ADR 0001: Host tooling in Python, standard library only at runtime

- **Status:** accepted, 2026-11-14

## Context

The host tools sit next to private firmware images and real devices. Contributors range from
photographers to firmware engineers. The spec prefers Python 3 with `pyproject.toml`, pytest and
locked dependencies.

## Decision

- `digimax` is a Python ≥ 3.11 package (`tools/digimax`) with **zero runtime dependencies**. It
  uses `tomllib`, `argparse`, `hashlib` and other standard-library modules.
- USB discovery reads Linux sysfs instead of using libusb, so no USB transfers are ever issued.
- Development dependencies (pytest, hypothesis, ruff, mypy, PyYAML) are locked in `uv.lock`.
- `mypy --strict` covers `tools/` and `sim/`.

## Consequences

- The tool is easy to audit, and nothing is pulled in at runtime.
- Any future runtime dependency (for example a DNG library or pyusb for a *proven* protocol) needs
  a new ADR with a license and footprint review.
