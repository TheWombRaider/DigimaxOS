# Contributing to DigimaxOS

Thank you for helping. DigimaxOS is meant to be a long-lived, collaborative project, and you do
not need AI tools or prior firmware experience to contribute.

## Ground rules

1. **Evidence over claims.** Every statement about hardware or firmware is *documented* (cite a
   source ID from [`docs/evidence/sources.yaml`](docs/evidence/sources.yaml)), a *hypothesis*
   (file it in [`docs/evidence/hypotheses.md`](docs/evidence/hypotheses.md)) or *verified* (cite an
   experiment ID). A UI label or a test that passes in the simulator is not proof that something
   works on a camera.
2. **No OEM bytes in the repo.** Do not commit Samsung firmware, update files, manuals, drivers,
   calibration/EEPROM data, disassembly listings that reproduce OEM code, or binary diffs that
   embed OEM bytes. Describe interfaces and observations in your own words. Keep private artifacts
   in a workspace outside Git (see [docs/development/setup.md](docs/development/setup.md)).
3. **No private data.** No personal photos, unredacted serial numbers, names, GPS/EXIF owner fields,
   e-mail addresses or credentials. `scripts/check_public_safety.py` enforces part of this in CI.
4. **No hardware writes without the gates.** Any change that writes to a camera (flash, EEPROM,
   settings area or an internal memory format) needs gate G2 (see
   [docs/recovery/README.md](docs/recovery/README.md)), maintainer review and the device owner's
   explicit approval. Code that could write to a host block device must default to dry-run and must
   check that it has exactly the right target.
5. **Respect licenses.** Original code is MIT. Do not paste GPL code (for example from the Linux
   `gspca` driver or CHDK) into MIT files. Link to it, or write your own implementation of the
   documented interface. See [docs/development/licensing.md](docs/development/licensing.md).

## How to contribute

- **Compatibility reports.** Use the *Compatibility report* issue form. Run
  `digimax discover --json` (Linux) or `scripts/windows/Get-DigimaxInfo.ps1` (Windows) and paste the
  output after reviewing it.
- **Experiments.** Use the *Experiment report* form and follow the experiment template in
  [`docs/evidence/experiments/README.md`](docs/evidence/experiments/README.md). Record exactly what
  you ran, the power and media you used, what you expected and what actually happened. Results that
  are negative or inconclusive are valuable too.
- **Code.** Fork the repo, create a branch and open a PR. Keep each PR small and focused on one
  thing.

## Development setup

```bash
uv sync                      # Python >= 3.11; installs dev tools into .venv
scripts/verify.sh            # lint + format check + type check + tests + public-safety scan
```

The tool package lives in `tools/digimax`, simulators in `sim/digimax_sim`, tests in `tests/`.
Tests must not need hardware. Hardware tests get the `@pytest.mark.hardware` marker, need an
explicit device label and never run in CI.

## Pull request checklist

Every PR description must include (the template prompts you):

- the evidence or experiment IDs it relies on
- the tests you added or ran
- its scope, and what it deliberately does not do
- license and provenance of any non-original material
- hardware risk: none / host-only / reads device / **writes device** (writes require gate G2)
- before/after screenshots or ASCII mocks for UI changes
- whether AI assistance was used, and how you verified its output

Firmware, patch-format and hardware-write changes need review from a maintainer listed in
`.github/CODEOWNERS`. Maintainers record significant decisions as ADRs in
`docs/development/decisions/`.

## Style

- Python: `ruff` (lint and format) and `mypy --strict` for `tools/` and `sim/`. Standard library
  only for the runtime CLI unless an ADR approves a dependency.
- Docs: plain Markdown, sentence-case headings. Use dates in ISO 8601 format, and do not commit
  to deadlines.
- Commits: imperative mood ("Add CSD v2 decoder"), one logical change per commit.
